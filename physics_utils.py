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
    ENABLE_CCD,
    CCD_MAX_SUBDIVISIONS,
    CCD_MIN_STEP_SIZE,
    CCD_VELOCITY_THRESHOLD,
)

# Reduced cache sizes for memory optimization
_velocity_cache = {}
_MAX_CACHE_SIZE = 50  # Smaller cache to reduce memory usage

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
        # Clear cache if it gets too large (optimized size)
        if len(_velocity_cache) > _MAX_CACHE_SIZE:
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


def swept_circle_collision(obj1, obj2, dt=1.0):
    """
    Continuous Collision Detection using swept circles.
    Returns the time of impact (0-1) if collision occurs, None otherwise.
    """
    # Calculate relative movement
    rel_vx = obj1.vx - obj2.vx
    rel_vy = obj1.vy - obj2.vy
    rel_x = obj1.x - obj2.x
    rel_y = obj1.y - obj2.y
    
    # Combined radius
    combined_radius = obj1.radius + obj2.radius
    
    # Quadratic equation coefficients for circle-circle collision
    # |pos + vel*t|² = r²
    a = rel_vx * rel_vx + rel_vy * rel_vy
    b = 2.0 * (rel_x * rel_vx + rel_y * rel_vy)
    c = rel_x * rel_x + rel_y * rel_y - combined_radius * combined_radius
    
    # Check if already overlapping
    if c < 0:
        return 0.0
    
    # No relative movement
    if abs(a) < 1e-6:
        return None
    
    discriminant = b * b - 4 * a * c
    
    if discriminant < 0:
        return None  # No collision
    
    # Find the earliest collision time
    sqrt_discriminant = math.sqrt(discriminant)
    t1 = (-b - sqrt_discriminant) / (2 * a)
    t2 = (-b + sqrt_discriminant) / (2 * a)
    
    # Return the earliest valid time (between 0 and dt)
    valid_times = [t for t in [t1, t2] if 0 <= t <= dt]
    
    return min(valid_times) if valid_times else None


def adaptive_movement_with_ccd(obj, target_x, target_y, nearby_objects):
    """
    Move object to target position using CCD to prevent tunneling.
    Returns True if movement completed, False if collision occurred.
    """
    if not ENABLE_CCD:
        # Fallback to direct movement
        obj.x = target_x
        obj.y = target_y
        return True
    
    # Calculate movement distance and velocity
    dx = target_x - obj.x
    dy = target_y - obj.y
    distance = math.sqrt(dx * dx + dy * dy)
    
    # If movement is small, use direct movement
    if distance <= CCD_MIN_STEP_SIZE:
        obj.x = target_x
        obj.y = target_y
        return True
    
    # Calculate number of substeps based on distance and max step size
    max_step = min(obj.radius * 0.8, CCD_MIN_STEP_SIZE)
    num_steps = min(CCD_MAX_SUBDIVISIONS, math.ceil(distance / max_step))
    
    step_x = dx / num_steps
    step_y = dy / num_steps
    
    # Move in substeps, checking for collisions
    for step in range(num_steps):
        next_x = obj.x + step_x
        next_y = obj.y + step_y
        
        # Check for collision at this substep
        collision_detected = False
        
        for other in nearby_objects:
            if other is obj:
                continue
                
            # Check if moving to next position would cause collision
            dx_check = next_x - other.x
            dy_check = next_y - other.y
            dist_sq = dx_check * dx_check + dy_check * dy_check
            min_dist_sq = (obj.radius + other.radius) ** 2
            
            if dist_sq < min_dist_sq:
                # Collision detected - stop movement and resolve
                collision_detected = True
                
                # Use swept collision to find exact impact time
                impact_time = swept_circle_collision(obj, other, 1.0)
                
                if impact_time is not None and impact_time > 0:
                    # Move to just before impact
                    safe_factor = max(0.1, impact_time - 0.02)
                    obj.x += step_x * safe_factor
                    obj.y += step_y * safe_factor
                else:
                    # Fallback: don't move further
                    pass
                
                # Apply collision response
                resolve_circle_circle(obj, other)
                return False
        
        if collision_detected:
            break
        
        # No collision - move to next position
        obj.x = next_x
        obj.y = next_y
    
    return True


def enhanced_separation_enforcement(obj1, obj2):
    """
    Aggressively enforce separation between overlapping objects.
    This is a safety net for when objects are already penetrating.
    """
    dx = obj2.x - obj1.x
    dy = obj2.y - obj1.y
    distance = math.sqrt(dx * dx + dy * dy)
    min_distance = obj1.radius + obj2.radius
    
    if distance < min_distance:
        if distance < 1e-6:  # Avoid division by zero
            # Objects are exactly on top of each other - separate arbitrarily
            dx, dy = 1.0, 0.0
            distance = 1.0
        
        overlap = min_distance - distance
        
        # Normalize separation direction
        nx = dx / distance
        ny = dy / distance
        
        # Calculate mass-based separation (if masses available)
        mass1 = getattr(obj1, 'mass', 1.0)
        mass2 = getattr(obj2, 'mass', 1.0)
        total_mass = mass1 + mass2
        
        # Ensure complete separation with small buffer
        buffer = 1.0  # Small buffer to prevent immediate re-collision
        total_separation = overlap + buffer
        
        # Separate based on inverse mass ratio
        separation1 = total_separation * (mass2 / total_mass)
        separation2 = total_separation * (mass1 / total_mass)
        
        obj1.x -= nx * separation1
        obj1.y -= ny * separation1
        obj2.x += nx * separation2
        obj2.y += ny * separation2
        
        # Dampen velocities along collision normal to prevent jittering
        rel_vx = obj2.vx - obj1.vx
        rel_vy = obj2.vy - obj1.vy
        vel_along_normal = rel_vx * nx + rel_vy * ny
        
        if vel_along_normal < 0:  # Moving toward each other
            # Apply velocity dampening
            impulse = vel_along_normal * 0.4  # Damping factor
            obj1.vx -= nx * impulse * (mass2 / total_mass)
            obj1.vy -= ny * impulse * (mass2 / total_mass)
            obj2.vx += nx * impulse * (mass1 / total_mass)
            obj2.vy += ny * impulse * (mass1 / total_mass)
        
        return True
    
    return False
