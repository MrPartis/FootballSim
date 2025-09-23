import pygame
from constants import *

class Field:
    def __init__(self):
        self.width = FIELD_WIDTH
        self.height = FIELD_HEIGHT
        self.x = FIELD_X
        self.y = FIELD_Y
        
    def draw(self, screen):
        """Draw the football field"""
        # Background
        screen.fill(DARK_GREEN)

        # Field base
        pygame.draw.rect(screen, GREEN, (self.x, self.y, self.width, self.height))

        # Grass stripes
        stripe_count = 10
        stripe_width = self.width // stripe_count
        for i in range(stripe_count):
            if i % 2 == 0:
                stripe_rect = pygame.Rect(self.x + i * stripe_width, self.y, stripe_width, self.height)
                pygame.draw.rect(screen, (30, 180, 30), stripe_rect)

        # Border
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 3)

        # Center line
        center_x = self.x + self.width // 2
        pygame.draw.line(screen, WHITE, (center_x, self.y), (center_x, self.y + self.height), 3)

        # Center circle and kickoff mark - scaled for larger objects
        center_y = self.y + self.height // 2
        pygame.draw.circle(screen, WHITE, (center_x, center_y), 80, 3)  # Increased from 60
        pygame.draw.circle(screen, WHITE, (center_x, center_y), 15, 2)  # Increased from 10
        pygame.draw.circle(screen, WHITE, (center_x, center_y), 5)      # Increased from 3

        # Penalty areas - scaled proportionally
        penalty_width = 200  # Increased for larger goals
        penalty_height = 320  # Increased proportionally
        left_penalty_x = self.x
        left_penalty_y = self.y + (self.height - penalty_height) // 2
        pygame.draw.rect(screen, WHITE, (left_penalty_x, left_penalty_y, penalty_width, penalty_height), 3)
        right_penalty_x = self.x + self.width - penalty_width
        right_penalty_y = self.y + (self.height - penalty_height) // 2
        pygame.draw.rect(screen, WHITE, (right_penalty_x, right_penalty_y, penalty_width, penalty_height), 3)

        # Goal boxes (small) - scaled for larger goals
        goal_area_width = 100  # Increased from 60
        goal_area_height = 200  # Increased from 120
        left_goal_x = self.x
        left_goal_y = self.y + (self.height - goal_area_height) // 2
        pygame.draw.rect(screen, WHITE, (left_goal_x, left_goal_y, goal_area_width, goal_area_height), 3)
        right_goal_x = self.x + self.width - goal_area_width
        right_goal_y = self.y + (self.height - goal_area_height) // 2
        pygame.draw.rect(screen, WHITE, (right_goal_x, right_goal_y, goal_area_width, goal_area_height), 3)

        # Goals last
        self.draw_goals(screen)
    
    def draw_goals(self, screen):
        """Draw the goals"""
        goal_width = GOAL_WIDTH
        goal_depth = GOAL_DEPTH
        
        # Left goal (Team 1 defends)
        left_goal_x = self.x - goal_depth
        left_goal_y = self.y + (self.height - goal_width) // 2
        # Visual goal area rectangle (behind goal line) - ball only zone
        left_area = pygame.Surface((goal_depth, goal_width), pygame.SRCALPHA)
        left_area.fill((200, 200, 200, 60))  # light translucent gray
        screen.blit(left_area, (self.x - goal_depth, left_goal_y))
        
        # Goal posts
        pygame.draw.rect(screen, WHITE, 
                        (left_goal_x, left_goal_y, goal_depth, GOAL_HEIGHT), 3)
        pygame.draw.rect(screen, WHITE, 
                        (left_goal_x, left_goal_y + goal_width - GOAL_HEIGHT, 
                         goal_depth, GOAL_HEIGHT), 3)
        # Goal back
        pygame.draw.line(screen, WHITE, 
                        (left_goal_x, left_goal_y), 
                        (left_goal_x, left_goal_y + goal_width), 3)
        
        # Right goal (Team 2 defends)
        right_goal_x = self.x + self.width
        right_goal_y = self.y + (self.height - goal_width) // 2
        # Visual goal area rectangle (behind goal line) - ball only zone
        right_area = pygame.Surface((goal_depth, goal_width), pygame.SRCALPHA)
        right_area.fill((200, 200, 200, 60))
        screen.blit(right_area, (self.x + self.width, right_goal_y))
        
        # Goal posts
        pygame.draw.rect(screen, WHITE, 
                        (right_goal_x, right_goal_y, goal_depth, GOAL_HEIGHT), 3)
        pygame.draw.rect(screen, WHITE, 
                        (right_goal_x, right_goal_y + goal_width - GOAL_HEIGHT, 
                         goal_depth, GOAL_HEIGHT), 3)
        # Goal back
        pygame.draw.line(screen, WHITE, 
                        (right_goal_x + goal_depth, right_goal_y), 
                        (right_goal_x + goal_depth, right_goal_y + goal_width), 3)
    
    def draw_scaled(self, screen, zoom, offset_x, offset_y):
        """Draw the field with camera transformations applied"""
        # Create a temporary surface to draw the field on
        temp_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Draw the field on the temporary surface at original position
        self.draw(temp_surface)
        
        # Calculate scaled dimensions
        scaled_width = int(SCREEN_WIDTH * zoom)
        scaled_height = int(SCREEN_HEIGHT * zoom)
        
        # Scale the surface
        if zoom != 1.0:
            scaled_surface = pygame.transform.scale(temp_surface, (scaled_width, scaled_height))
        else:
            scaled_surface = temp_surface
        
        # Apply offset and blit to screen
        screen.blit(scaled_surface, (offset_x, offset_y))
    
    def is_in_bounds(self, x, y, radius=0):
        """Check if a point is within the field boundaries"""
        return (self.x + radius <= x <= self.x + self.width - radius and 
                self.y + radius <= y <= self.y + self.height - radius)