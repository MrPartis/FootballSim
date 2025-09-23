import math
from constants import (
    RESTITUTION,
    COLLISION_DAMPING,
    POSITION_CORRECTION_PERCENT,
    POSITION_CORRECTION_SLOP,
    MAX_VELOCITY,
    FIELD_X,
    FIELD_Y,
    FIELD_WIDTH,
    FIELD_HEIGHT,
    CORNER_REPEL_MIN_DIST,
    CORNER_REPEL_IMPULSE,
)

# Cache for expensive calculations
_distance_cache = {}
_velocity_cache = {}

def clamp_velocity(obj):
    """
    Clamp an object's velocity to prevent noclipping from excessive speed.
    Optimized with caching for repeated calls.
    """
    # Use cached calculation if velocity hasn't changed
    vel_key = (obj.vx, obj.vy)
    if vel_key in _velocity_cache:
        speed_sq = _velocity_cache[vel_key]
    else:
        speed_sq = obj.vx * obj.vx + obj.vy * obj.vy
        _velocity_cache[vel_key] = speed_sq
        # Clear cache if it gets too large
        if len(_velocity_cache) > 100:
            _velocity_cache.clear()
    
    if speed_sq > MAX_VELOCITY * MAX_VELOCITY:
        speed = math.sqrt(speed_sq)
        obj.vx = (obj.vx / speed) * MAX_VELOCITY
        obj.vy = (obj.vy / speed) * MAX_VELOCITY


def apply_corner_repulsion(obj):
    """
    Unified corner repulsion logic for both ball and players.
    Apply a small outward push when the object is too close to a field corner.
    """
    # Skip if outside play area behind goals
    if (obj.x + obj.radius < FIELD_X) or (obj.x - obj.radius > FIELD_X + FIELD_WIDTH):
        return
    
    corners = [
        (FIELD_X, FIELD_Y),
        (FIELD_X + FIELD_WIDTH, FIELD_Y),
        (FIELD_X, FIELD_Y + FIELD_HEIGHT),
        (FIELD_X + FIELD_WIDTH, FIELD_Y + FIELD_HEIGHT),
    ]
    
    # Find nearest corner with optimized distance calculation
    nearest = None
    min_d_sq = float('inf')
    for cx, cy in corners:
        dx = obj.x - cx
        dy = obj.y - cy
        d_sq = dx * dx + dy * dy  # Skip sqrt for comparison
        if d_sq < min_d_sq:
            min_d_sq = d_sq
            nearest = (cx, cy)
    
    if nearest is None:
        return
        
    min_d = math.sqrt(min_d_sq)
    threshold = CORNER_REPEL_MIN_DIST + obj.radius
    
    if min_d <= threshold:
        cx, cy = nearest
        dx = obj.x - cx
        dy = obj.y - cy
        
        if min_d < 1e-6:  # Avoid division by zero
            # Push toward field center
            dx = (FIELD_X + FIELD_WIDTH / 2) - obj.x
            dy = (FIELD_Y + FIELD_HEIGHT / 2) - obj.y
            min_d = math.sqrt(dx * dx + dy * dy)
        
        if min_d > 0:
            # Normalize and apply impulse
            nx = dx / min_d
            ny = dy / min_d
            obj.vx += nx * CORNER_REPEL_IMPULSE
            obj.vy += ny * CORNER_REPEL_IMPULSE
            obj.moving = True


def resolve_circle_circle(a, b):
    """
    Resolve collision between two circular dynamic bodies a and b.
    Bodies must have: x, y, vx, vy, radius, mass, and optional 'moving' flag.
    Uses impulse resolution and positional correction (Baumgarte-like).

    Returns True if a collision was resolved; False otherwise.
    """
    # Vector from A to B
    nx = b.x - a.x
    ny = b.y - a.y
    dist2 = nx * nx + ny * ny
    r = a.radius + b.radius

    # Early out if far apart
    if dist2 >= r * r:
        return False

    distance = math.sqrt(dist2) if dist2 > 0 else 0.0

    # Normalized collision normal
    if distance > 1e-6:
        nx /= distance
        ny /= distance
    else:
        # Prevent divide-by-zero: pick an arbitrary normal
        nx, ny = 1.0, 0.0
        distance = 0.0

    # Penetration (how much they overlap)
    penetration = r - distance

    # Relative velocity
    rvx = b.vx - a.vx
    rvy = b.vy - a.vy

    # Relative velocity along the normal
    vel_along_normal = rvx * nx + rvy * ny

    # Compute inverse masses
    inv_mass_a = 0.0 if getattr(a, 'mass', 0) == 0 else 1.0 / a.mass
    inv_mass_b = 0.0 if getattr(b, 'mass', 0) == 0 else 1.0 / b.mass
    inv_mass_sum = inv_mass_a + inv_mass_b
    if inv_mass_sum == 0.0:
        # Both static, only positional correction
        inv_mass_sum = 1.0

    # If they are moving apart, we still want to correct penetration, but skip impulse
    apply_impulse = vel_along_normal < 0

    if apply_impulse:
        # Impulse scalar (1D)
        j = -(1.0 + RESTITUTION) * vel_along_normal
        j /= inv_mass_sum

        # Impulse vector
        jx = j * nx
        jy = j * ny

        # Apply impulse
        a.vx -= jx * inv_mass_a
        a.vy -= jy * inv_mass_a
        b.vx += jx * inv_mass_b
        b.vy += jy * inv_mass_b

        # Damping to reduce unrealistic energy
        a.vx *= COLLISION_DAMPING
        a.vy *= COLLISION_DAMPING
        b.vx *= COLLISION_DAMPING
        b.vy *= COLLISION_DAMPING
        
        # Clamp velocities to prevent noclipping
        clamp_velocity(a)
        clamp_velocity(b)

    # Positional correction (to avoid sinking and jitter)
    correction_mag = max(penetration - POSITION_CORRECTION_SLOP, 0.0) * (POSITION_CORRECTION_PERCENT / inv_mass_sum)
    cx = correction_mag * nx
    cy = correction_mag * ny
    a.x -= cx * inv_mass_a
    a.y -= cy * inv_mass_a
    b.x += cx * inv_mass_b
    b.y += cy * inv_mass_b

    # Mark as moving if they have meaningful speed (optional)
    if hasattr(a, 'moving'):
        if abs(a.vx) + abs(a.vy) > 0.5:
            a.moving = True
    if hasattr(b, 'moving'):
        if abs(b.vx) + abs(b.vy) > 0.5:
            b.moving = True

    return True
