import pygame
import math
from constants import *
from physics_utils import clamp_velocity, apply_corner_repulsion

class Player:
    def __init__(self, x, y, team, player_id):
        self.x = x
        self.y = y
        self.team = team  # 1 or 2
        self.player_id = player_id  # 0-4
        self.radius = PLAYER_RADIUS
        self.mass = PLAYER_MASS
        self.selected = False
        self.can_move = True
        
        # Movement and physics
        self.vx = 0  # Velocity X
        self.vy = 0  # Velocity Y
        self.moving = False
        
        # Direction indication
        self.aim_direction = 0  # Angle in radians
        self.aim_force = 0
        
        # Visual properties
        self.color = TEAM1_COLOR if team == 1 else TEAM2_COLOR
        self.outline_color = BLACK
        self.selected_color = YELLOW
        
    def get_position(self):
        """Return current position as tuple"""
        return (self.x, self.y)
    
    def set_position(self, x, y):
        """Set player position"""
        self.x = x
        self.y = y
    
    def set_aim_direction(self, dx, dy):
        """Set the aiming direction based on input - smooth 360 degree control"""
        # Normalize input for consistent speed
        if dx != 0 or dy != 0:
            length = math.sqrt(dx*dx + dy*dy)
            dx /= length
            dy /= length
            
            # Smooth direction change
            target_angle = math.atan2(dy, dx)
            
            # Calculate shortest angular distance
            angle_diff = target_angle - self.aim_direction
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # Smoothly interpolate to target angle
            self.aim_direction += angle_diff * DIRECTION_CHANGE_SPEED

    def set_aim_direction_instant(self, dx, dy):
        """Set aiming direction immediately without smoothing (used on selection/seeding)."""
        if dx != 0 or dy != 0:
            self.aim_direction = math.atan2(dy, dx)
    
    def update_aim_continuous(self, keys, controls):
        """Update aim direction continuously based on held keys"""
        dx, dy = 0, 0
        if keys[controls['up']]:
            dy -= 1
        if keys[controls['down']]:
            dy += 1
        if keys[controls['left']]:
            dx -= 1
        if keys[controls['right']]:
            dx += 1
        
        if dx != 0 or dy != 0:
            self.set_aim_direction(dx, dy)
    
    def start_movement(self, force):
        """Start player movement with given force and current aim direction"""
        self.vx = math.cos(self.aim_direction) * force * PLAYER_FORCE_MULTIPLIER
        self.vy = math.sin(self.aim_direction) * force * PLAYER_FORCE_MULTIPLIER
        self.moving = True
    
    def update(self, speed_multiplier=1.0):
        """Update player physics when moving"""
        if not self.moving:
            # Gentle corner repulsion even when idle
            apply_corner_repulsion(self)
            return
        
        # Apply movement with speed multiplier
        self.x += self.vx * speed_multiplier
        self.y += self.vy * speed_multiplier
        
        # Apply friction proportional to speed multiplier for consistent physics
        friction_factor = 1.0 - (1.0 - FRICTION) * speed_multiplier
        self.vx *= friction_factor
        self.vy *= friction_factor
        
        # Clamp velocity to prevent noclipping
        clamp_velocity(self)
        
        # Stop if velocity is too small (increased threshold)
        if abs(self.vx) < 1.2 and abs(self.vy) < 1.2:
            self.vx = 0
            self.vy = 0
            self.moving = False
        
        # Bounce off field boundaries with proper vector reflection
        if self.x - self.radius <= FIELD_X:
            self.x = FIELD_X + self.radius
            self.vx = abs(self.vx) * BOUNCE_FACTOR
        elif self.x + self.radius >= FIELD_X + FIELD_WIDTH:
            self.x = FIELD_X + FIELD_WIDTH - self.radius
            self.vx = -abs(self.vx) * BOUNCE_FACTOR
        
        if self.y - self.radius <= FIELD_Y:
            self.y = FIELD_Y + self.radius
            self.vy = abs(self.vy) * BOUNCE_FACTOR
        elif self.y + self.radius >= FIELD_Y + FIELD_HEIGHT:
            self.y = FIELD_Y + FIELD_HEIGHT - self.radius
            self.vy = -abs(self.vy) * BOUNCE_FACTOR
        
        # Bounce off goals and apply unified corner repulsion
        self.check_goal_bounce()
        apply_corner_repulsion(self)


    
    def check_goal_bounce(self):
        """Bounce player back from goals"""
        goal_y_min = FIELD_Y + (FIELD_HEIGHT - GOAL_WIDTH) // 2
        goal_y_max = FIELD_Y + (FIELD_HEIGHT + GOAL_WIDTH) // 2
        
        # Left goal bounce
        if (self.x - self.radius <= FIELD_X - GOAL_DEPTH and 
            goal_y_min <= self.y <= goal_y_max):
            self.x = FIELD_X - GOAL_DEPTH + self.radius
            self.vx = abs(self.vx) * BOUNCE_FACTOR
        
        # Right goal bounce
        elif (self.x + self.radius >= FIELD_X + FIELD_WIDTH + GOAL_DEPTH and 
              goal_y_min <= self.y <= goal_y_max):
            self.x = FIELD_X + FIELD_WIDTH + GOAL_DEPTH - self.radius
            self.vx = -abs(self.vx) * BOUNCE_FACTOR
    
    def reset_turn(self):
        """Reset player state for new turn"""
        self.can_move = True
        self.selected = False
        self.vx = 0
        self.vy = 0
        self.moving = False
    
    def end_turn(self):
        """End player's turn"""
        self.can_move = False
        self.selected = False
    
    def distance_to(self, other_x, other_y):
        """Calculate distance to a point"""
        return math.sqrt((self.x - other_x)**2 + (self.y - other_y)**2)
    
    def distance_to_player(self, other_player):
        """Calculate distance to another player"""
        return self.distance_to(other_player.x, other_player.y)
    
    def collides_with(self, other_x, other_y, other_radius):
        """Check collision with another circular object"""
        distance = self.distance_to(other_x, other_y)
        return distance < (self.radius + other_radius)
    
    def collides_with_player(self, other_player):
        """Check collision with another player"""
        return self.collides_with(other_player.x, other_player.y, other_player.radius)
    
    def bounce_off_player(self, other_player):
        """Handle collision with another player - proper vector-based collision physics"""
        # Calculate collision vector (from this player to other player)
        dx = other_player.x - self.x
        dy = other_player.y - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Prevent division by zero
        if distance < 0.01:
            import random
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
            distance = 1.0
        
        # Normalize collision normal vector
        nx = dx / distance
        ny = dy / distance
        
        # Calculate tangent vector (perpendicular to normal)
        tx = -ny
        ty = nx
        
        # Separate overlapping players
        overlap = (self.radius + other_player.radius) - distance
        if overlap > 0:
            # Since both players have equal mass, separate equally
            separation = overlap * 0.5
            self.x -= nx * separation
            self.y -= ny * separation
            other_player.x += nx * separation
            other_player.y += ny * separation
        
        # Get velocities before collision
        v1_x, v1_y = self.vx, self.vy
        v2_x, v2_y = other_player.vx, other_player.vy
        
        # Project velocities onto collision normal and tangent
        # Normal components (along collision line)
        v1_normal = v1_x * nx + v1_y * ny
        v2_normal = v2_x * nx + v2_y * ny
        
        # Tangential components (perpendicular to collision line) - these don't change
        v1_tangent = v1_x * tx + v1_y * ty
        v2_tangent = v2_x * tx + v2_y * ty
        
        # For equal masses, normal velocities are simply exchanged
        # Apply coefficient of restitution
        v1_normal_new = v2_normal * RESTITUTION
        v2_normal_new = v1_normal * RESTITUTION
        
        # Convert back to x,y components
        self.vx = v1_normal_new * nx + v1_tangent * tx
        self.vy = v1_normal_new * ny + v1_tangent * ty
        
        other_player.vx = v2_normal_new * nx + v2_tangent * tx
        other_player.vy = v2_normal_new * ny + v2_tangent * ty
        
        # Apply damping
        self.vx *= COLLISION_DAMPING
        self.vy *= COLLISION_DAMPING
        other_player.vx *= COLLISION_DAMPING
        other_player.vy *= COLLISION_DAMPING
        
        # Ensure both players are marked as moving if they have significant velocity
        speed1 = math.sqrt(self.vx*self.vx + self.vy*self.vy)
        speed2 = math.sqrt(other_player.vx*other_player.vx + other_player.vy*other_player.vy)
        
        if speed1 > 0.5:
            self.moving = True
        if speed2 > 0.5:
            other_player.moving = True
    
    def draw(self, screen):
        """Draw the player on the screen"""
        # Draw player
        color = self.selected_color if self.selected else self.color
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, self.outline_color, (int(self.x), int(self.y)), self.radius, 2)
        
        # Draw player number
        font = pygame.font.Font(None, 24)
        text = font.render(str(self.player_id + 1), True, WHITE)
        text_rect = text.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(text, text_rect)
    
    def draw_direction_arrow(self, screen):
        """Draw direction arrow when aiming"""
        if not self.selected:
            return
        
        # Calculate arrow end point
        end_x = self.x + math.cos(self.aim_direction) * DIRECTION_ARROW_LENGTH
        end_y = self.y + math.sin(self.aim_direction) * DIRECTION_ARROW_LENGTH
        
        # Draw arrow line
        pygame.draw.line(screen, WHITE, (int(self.x), int(self.y)), 
                        (int(end_x), int(end_y)), 3)
        
        # Draw arrow head
        arrow_size = 10
        arrow_angle = self.aim_direction + math.pi
        
        # Left arrow point
        left_x = end_x + math.cos(arrow_angle + 0.5) * arrow_size
        left_y = end_y + math.sin(arrow_angle + 0.5) * arrow_size
        
        # Right arrow point
        right_x = end_x + math.cos(arrow_angle - 0.5) * arrow_size
        right_y = end_y + math.sin(arrow_angle - 0.5) * arrow_size
        
        # Draw arrow head
        pygame.draw.polygon(screen, WHITE, [
            (int(end_x), int(end_y)),
            (int(left_x), int(left_y)),
            (int(right_x), int(right_y))
        ])