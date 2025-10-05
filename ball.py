import pygame
import math
from constants import *
from physics_utils import clamp_velocity, apply_corner_repulsion, adaptive_movement_with_ccd


class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.radius = BALL_RADIUS
        self.mass = BALL_MASS
        self.moving = False
    # internal: may track last unstick tick if needed later

    def get_position(self):
        return (self.x, self.y)

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def set_velocity(self, vx, vy):
        self.vx = vx
        self.vy = vy
        self.moving = abs(vx) > 1 or abs(vy) > 1

    def kick(self, force, angle, kicking_player_id=None):
        import pygame
        self.vx = math.cos(angle) * force
        self.vy = math.sin(angle) * force
        self.moving = True
        
        # Set kick immunity to prevent collision resolution from interfering
        if kicking_player_id is not None:
            self.kick_immunity_player = kicking_player_id
            self.kick_immunity_until = pygame.time.get_ticks() + 100  # 100ms immunity

    def has_kick_immunity(self, player_id):
        """Check if ball has kick immunity against a specific player"""
        import pygame
        current_time = pygame.time.get_ticks()
        
        # Return False if immunity attributes not set
        if not hasattr(self, 'kick_immunity_player') or not hasattr(self, 'kick_immunity_until'):
            return False
            
        return (self.kick_immunity_player == player_id and 
                current_time < self.kick_immunity_until)
    
    def update(self, speed_multiplier=1.0):
        if not self.moving:
            # Even when idle, apply gentle corner repulsion to avoid sticking
            apply_corner_repulsion(self)
            # Ensure ball stays within boundaries even when stationary
            self._enforce_boundaries()
            return

        # Clamp velocity FIRST to prevent excessive speeds
        clamp_velocity(self)
        
        # Store previous position for rollback if needed
        prev_x, prev_y = self.x, self.y
        
        # Calculate target position
        new_x = self.x + self.vx * speed_multiplier
        new_y = self.y + self.vy * speed_multiplier
        
        # Use CCD if velocity is high enough
        velocity_magnitude = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        
        if ENABLE_CCD and velocity_magnitude > CCD_VELOCITY_THRESHOLD:
            # Use CCD for high-speed movement (pass empty list since ball boundary checks are separate)
            adaptive_movement_with_ccd(self, new_x, new_y, [])
        else:
            # Use direct movement for low speeds
            self.x = new_x
            self.y = new_y
        
        # Check if new position would cause boundary collision
        goal_y_min = FIELD_Y + (FIELD_HEIGHT - GOAL_WIDTH) // 2
        goal_y_max = FIELD_Y + (FIELD_HEIGHT + GOAL_WIDTH) // 2
        
        # Predict and prevent boundary violations with collision response
        collision_occurred = False
        
        # Check left boundary
        if new_x - self.radius <= FIELD_X:
            if not (goal_y_min <= new_y <= goal_y_max):  # Not in goal area
                new_x = FIELD_X + self.radius
                self.vx = abs(self.vx) * BOUNCE_FACTOR
                collision_occurred = True
        
        # Check right boundary
        elif new_x + self.radius >= FIELD_X + FIELD_WIDTH:
            if not (goal_y_min <= new_y <= goal_y_max):  # Not in goal area
                new_x = FIELD_X + FIELD_WIDTH - self.radius
                self.vx = -abs(self.vx) * BOUNCE_FACTOR
                collision_occurred = True
        
        # Check top boundary
        if new_y - self.radius <= FIELD_Y:
            new_y = FIELD_Y + self.radius
            self.vy = abs(self.vy) * BOUNCE_FACTOR
            collision_occurred = True
        
        # Check bottom boundary
        elif new_y + self.radius >= FIELD_Y + FIELD_HEIGHT:
            new_y = FIELD_Y + FIELD_HEIGHT - self.radius
            self.vy = -abs(self.vy) * BOUNCE_FACTOR
            collision_occurred = True
        
        # Update position to corrected values
        self.x = new_x
        self.y = new_y
        
        # Apply friction proportional to speed multiplier for consistent physics
        friction_factor = 1.0 - (1.0 - FRICTION) * speed_multiplier
        self.vx *= friction_factor
        self.vy *= friction_factor
        
        # Additional velocity clamping after friction
        clamp_velocity(self)

        # Stop threshold
        if abs(self.vx) < 1.5 and abs(self.vy) < 1.5:
            self.vx = 0
            self.vy = 0
            self.moving = False

        # Final boundary enforcement (safety net)
        self._enforce_boundaries()
        
        # Unified corner repulsion
        apply_corner_repulsion(self)
    
    def _enforce_boundaries(self):
        """Ensure ball never goes outside field boundaries (safety net)"""
        goal_y_min = FIELD_Y + (FIELD_HEIGHT - GOAL_WIDTH) // 2
        goal_y_max = FIELD_Y + (FIELD_HEIGHT + GOAL_WIDTH) // 2
        
        # Force ball within left boundary (unless in goal)
        if self.x - self.radius < FIELD_X:
            if not (goal_y_min <= self.y <= goal_y_max):
                self.x = FIELD_X + self.radius
                if self.vx < 0:
                    self.vx = 0  # Stop leftward movement
        
        # Force ball within right boundary (unless in goal)
        elif self.x + self.radius > FIELD_X + FIELD_WIDTH:
            if not (goal_y_min <= self.y <= goal_y_max):
                self.x = FIELD_X + FIELD_WIDTH - self.radius
                if self.vx > 0:
                    self.vx = 0  # Stop rightward movement
        
        # Force ball within top boundary
        if self.y - self.radius < FIELD_Y:
            self.y = FIELD_Y + self.radius
            if self.vy < 0:
                self.vy = 0  # Stop upward movement
        
        # Force ball within bottom boundary
        elif self.y + self.radius > FIELD_Y + FIELD_HEIGHT:
            self.y = FIELD_Y + FIELD_HEIGHT - self.radius
            if self.vy > 0:
                self.vy = 0  # Stop downward movement

    def is_stuck_corner(self) -> bool:
        """Return True if the ball is idle and positioned in a field corner region."""
        if self.moving:
            return False
        # Only consider in-field corners, not space behind goal lines
        if (self.x + self.radius < FIELD_X) or (self.x - self.radius > FIELD_X + FIELD_WIDTH):
            return False
        tol = CORNER_STUCK_RADIUS
        near_left = (self.x - self.radius) <= (FIELD_X + tol)
        near_right = (self.x + self.radius) >= (FIELD_X + FIELD_WIDTH - tol)
        near_top = (self.y - self.radius) <= (FIELD_Y + tol)
        near_bottom = (self.y + self.radius) >= (FIELD_Y + FIELD_HEIGHT - tol)
        # Corner: near one vertical side AND one horizontal side
        return (near_left or near_right) and (near_top or near_bottom)

    def check_goal(self):
        """Return scoring team if ball is 50% through the goal line."""
        goal_y_min = FIELD_Y + (FIELD_HEIGHT - GOAL_WIDTH) // 2
        goal_y_max = FIELD_Y + (FIELD_HEIGHT + GOAL_WIDTH) // 2

        # Left goal (Team 2 scores) - trigger when ball center + 50% radius crosses goal line
        if self.x - self.radius * 0.5 <= FIELD_X and goal_y_min <= self.y <= goal_y_max:
            return 2

        # Right goal (Team 1 scores) - trigger when ball center + 50% radius crosses goal line
        if self.x + self.radius * 0.5 >= FIELD_X + FIELD_WIDTH and goal_y_min <= self.y <= goal_y_max:
            return 1

        return 0

    def reset_to_center(self):
        self.x = FIELD_X + FIELD_WIDTH // 2
        self.y = FIELD_Y + FIELD_HEIGHT // 2
        self.vx = 0
        self.vy = 0
        self.moving = False

    def distance_to(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def draw(self, screen):
        # Shadow
        pygame.draw.circle(screen, GRAY, (int(self.x + 2), int(self.y + 2)), self.radius)
        # Ball
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.radius, 2)
        # Simple pattern
        pygame.draw.line(screen, BLACK, (int(self.x - self.radius + 2), int(self.y)), (int(self.x + self.radius - 2), int(self.y)), 1)
        pygame.draw.line(screen, BLACK, (int(self.x), int(self.y - self.radius + 2)), (int(self.x), int(self.y + self.radius - 2)), 1)