"""
Tactical System for Mini Football Game
Manages player formations and tactical setups
"""
import pygame
import math
import json
import os
from constants import *

class TacticsManager:
    def __init__(self):
        # Define 4 prebuilt tactics/formations
        self.prebuilt_tactics = {
            'defensive': {
                'name': 'Defensive',
                'positions': [
                    (FIELD_WIDTH * 0.08, FIELD_HEIGHT * 0.5),   # Goalkeeper (closer to goal)
                    (FIELD_WIDTH * 0.22, FIELD_HEIGHT * 0.2),  # Defender 1 (wide)
                    (FIELD_WIDTH * 0.22, FIELD_HEIGHT * 0.5),  # Defender 2 (center)
                    (FIELD_WIDTH * 0.22, FIELD_HEIGHT * 0.8),  # Defender 3 (wide)
                    (FIELD_WIDTH * 0.35, FIELD_HEIGHT * 0.5),  # Lone Forward
                ]
            },
            'offensive': {
                'name': 'Offensive',
                'positions': [
                    (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
                    (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.3),  # Defender 1
                    (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.7),  # Defender 2
                    (FIELD_WIDTH * 0.425, FIELD_HEIGHT * 0.25), # Forward 1 (adjusted to stay in own half)
                    (FIELD_WIDTH * 0.425, FIELD_HEIGHT * 0.75), # Forward 2 (adjusted to stay in own half)
                ]
            },
            'balanced': {
                'name': 'Balanced',
                'positions': [
                    (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
                    (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.25), # Defender 1
                    (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.75), # Defender 2
                    (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.35),  # Midfielder
                    (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.65),  # Forward
                ]
            },
            'wide': {
                'name': 'Wide',
                'positions': [
                    (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
                    (FIELD_WIDTH * 0.3, FIELD_HEIGHT * 0.3),   # Center Back
                    (FIELD_WIDTH * 0.45, FIELD_HEIGHT * 0.15), # Right Wing
                    (FIELD_WIDTH * 0.45, FIELD_HEIGHT * 0.85), # Left Wing
                    (FIELD_WIDTH * 0.3, FIELD_HEIGHT * 0.7), # Center Forward (moved off center line)
                ]
            }
        }
        
        # Custom tactics slots (will be loaded from files or created by user)
        self.custom_tactics = {
            'custom1': None,
            'custom2': None,
            'custom3': None,
            'custom4': None,
            'custom5': None,
            'custom6': None
        }  # type: dict[str, dict | None]
        
        # Currently selected tactics
        self.team1_selected_tactic = 'balanced'  # Default
        self.team2_selected_tactic = 'balanced'  # Default
        
        # Load custom tactics from file if they exist
        self.load_custom_tactics()
    
    def get_available_tactics(self):
        """Get list of all available tactics (prebuilt + custom)"""
        tactics_list = []
        
        # Add prebuilt tactics
        for key, tactic in self.prebuilt_tactics.items():
            tactics_list.append({
                'key': key,
                'name': tactic['name'],
                'type': 'prebuilt'
            })
        
        # Add custom tactics
        for key, tactic in self.custom_tactics.items():
            if tactic is not None:
                tactics_list.append({
                    'key': key,
                    'name': tactic['name'],
                    'type': 'custom'
                })
            else:
                slot_number = key[-1]
                tactics_list.append({
                    'key': key,
                    'name': 'Empty',
                    'type': 'empty_custom'
                })
        
        return tactics_list
    
    def mirror_positions_for_team2(self, team1_positions):
        """Mirror team1 positions to create team2 positions"""
        team2_positions = []
        for x, y in team1_positions:
            # Mirror horizontally across the center of the field
            mirrored_x = FIELD_WIDTH - x
            team2_positions.append((mirrored_x, y))
        return team2_positions

    def get_tactic_positions(self, tactic_key, team):
        """Get player positions for a specific tactic and team"""
        # Check prebuilt tactics first
        if tactic_key in self.prebuilt_tactics:
            tactic = self.prebuilt_tactics[tactic_key]
            base_positions = tactic['positions']
            if team == 1:
                return base_positions
            else:
                return self.mirror_positions_for_team2(base_positions)
        
        # Check custom tactics
        if tactic_key in self.custom_tactics and self.custom_tactics[tactic_key] is not None:
            tactic = self.custom_tactics[tactic_key]
            if tactic is not None:  # Additional safety check
                # For custom tactics, maintain old structure for now but check if they have 'positions' key
                if 'positions' in tactic:
                    base_positions = tactic['positions']
                    if team == 1:
                        return base_positions
                    else:
                        return self.mirror_positions_for_team2(base_positions)
                else:
                    # Legacy custom tactics with team1_positions and team2_positions
                    if team == 1:
                        return tactic['team1_positions'] if 'team1_positions' in tactic else []
                    else:
                        return tactic['team2_positions'] if 'team2_positions' in tactic else []
        
        # Fallback to balanced formation
        return self.get_tactic_positions('balanced', team)
    
    def select_random_tactic(self, exclude_custom=True):
        """Select a random tactic (used for bots)"""
        import random
        
        if exclude_custom:
            # Only select from prebuilt tactics
            tactics = list(self.prebuilt_tactics.keys())
        else:
            # Include custom tactics that exist
            tactics = list(self.prebuilt_tactics.keys())
            for key, tactic in self.custom_tactics.items():
                if tactic is not None:
                    tactics.append(key)
        
        return random.choice(tactics)
    
    def set_team_tactic(self, team, tactic_key):
        """Set the selected tactic for a team"""
        if team == 1:
            self.team1_selected_tactic = tactic_key
        else:
            self.team2_selected_tactic = tactic_key
    
    def get_team_tactic(self, team):
        """Get the currently selected tactic for a team"""
        if team == 1:
            return self.team1_selected_tactic
        else:
            return self.team2_selected_tactic
    
    def is_custom_tactic(self, tactic_key):
        """Check if a tactic is a custom tactic"""
        return tactic_key in ['custom1', 'custom2', 'custom3', 'custom4', 'custom5', 'custom6']
    
    def create_custom_tactic(self, slot_key, name, positions):
        """Create a new custom tactic"""
        if slot_key not in ['custom1', 'custom2', 'custom3', 'custom4', 'custom5', 'custom6']:
            return False
        
        self.custom_tactics[slot_key] = {
            'name': name,
            'positions': positions.copy()
        }
        
        # Save to file
        self.save_custom_tactics()
        return True
    
    def reset_all_custom_tactics(self):
        """Clear all custom tactics and reset them to empty"""
        for slot in ['custom1', 'custom2', 'custom3', 'custom4', 'custom5', 'custom6']:
            self.custom_tactics[slot] = None
        
        # Save the empty state to file
        self.save_custom_tactics()
        return True
    
    def delete_custom_tactic(self, slot_key):
        """Delete a specific custom tactic"""
        if slot_key not in ['custom1', 'custom2', 'custom3', 'custom4', 'custom5', 'custom6']:
            return False
        
        if self.custom_tactics[slot_key] is None:
            return False  # Already empty
        
        # Clear the slot
        self.custom_tactics[slot_key] = None
        
        # Save the updated state to file
        self.save_custom_tactics()
        return True
    
    def save_custom_tactics(self):
        """Save custom tactics to file"""
        try:
            tactics_data = {}
            for key, tactic in self.custom_tactics.items():
                if tactic is not None:
                    tactics_data[key] = tactic
            
            with open('custom_tactics.json', 'w') as f:
                json.dump(tactics_data, f, indent=2)
        except Exception as e:
            print(f"Error saving custom tactics: {e}")
    
    def load_custom_tactics(self):
        """Load custom tactics from file"""
        try:
            if os.path.exists('custom_tactics.json'):
                with open('custom_tactics.json', 'r') as f:
                    tactics_data = json.load(f)
                
                for key, tactic in tactics_data.items():
                    if key in self.custom_tactics:
                        self.custom_tactics[key] = tactic
        except Exception as e:
            print(f"Error loading custom tactics: {e}")
    
    def validate_positions(self, positions):
        """Validate that positions are within field bounds and reasonable"""
        if len(positions) != 5:
            return False
        
        for pos in positions:
            x, y = pos
            # Check if position is within field bounds (with some margin)
            if not (0 <= x <= FIELD_WIDTH and 0 <= y <= FIELD_HEIGHT):
                return False
        
        return True
    
    def get_ball_positions(self):
        """Get all critical ball positions that players shouldn't overlap"""
        # Ball starting position (center of field)
        ball_start = (FIELD_WIDTH * 0.5, FIELD_HEIGHT * 0.5)
        
        # Post-goal reset positions (offset from center toward each team's half)
        # These match the kickoff positions used in game_manager.py score_goal()
        center_x = FIELD_WIDTH * 0.5
        center_y = FIELD_HEIGHT * 0.5
        
        # Team 1 lost goal - ball positioned toward their half
        ball_reset_team1_lost = (center_x - KICKOFF_OFFSET, center_y)
        
        # Team 2 lost goal - ball positioned toward their half  
        ball_reset_team2_lost = (center_x + KICKOFF_OFFSET, center_y)
        
        # Return list of critical ball positions with descriptions
        return [
            {
                'position': ball_start,
                'radius': BALL_RADIUS + PLAYER_RADIUS + 10  # Safe distance
            },
            {
                'position': ball_reset_team1_lost,
                'radius': BALL_RADIUS + PLAYER_RADIUS + 10  # Safe distance
            },
            {
                'position': ball_reset_team2_lost,
                'radius': BALL_RADIUS + PLAYER_RADIUS + 10  # Safe distance
            }
        ]
    
    def check_player_ball_conflicts(self, team1_positions, team2_positions):
        """Check if any player positions conflict with ball positions"""
        ball_positions = self.get_ball_positions()
        conflicts = []
        
        all_positions = [(pos, 1, i+1) for i, pos in enumerate(team1_positions)] + \
                       [(pos, 2, i+1) for i, pos in enumerate(team2_positions)]
        
        # Track which players have conflicts to avoid duplicates
        conflicted_players = set()
        
        for player_pos, team, player_num in all_positions:
            px, py = player_pos
            player_key = (team, player_num)
            
            # Skip if this player already has a conflict recorded
            if player_key in conflicted_players:
                continue
            
            # Check if this player conflicts with any ball zone
            min_distance = float('inf')
            max_required_distance = 0
            player_has_conflict = False
            
            for ball_info in ball_positions:
                bx, by = ball_info['position']
                warning_zone_radius = ball_info['radius']
                
                # Calculate distance between player center and ball position center
                distance_AB = math.sqrt((px - bx)**2 + (py - by)**2)
                required_distance = PLAYER_RADIUS + warning_zone_radius
                
                # Check if Ra + Rb > AB (player radius + warning zone radius > distance between centers)
                if required_distance > distance_AB:
                    player_has_conflict = True
                    min_distance = min(min_distance, distance_AB)
                    max_required_distance = max(max_required_distance, required_distance)
            
            # If player has any conflicts, add one entry with the worst case
            if player_has_conflict:
                conflicts.append({
                    'team': team,
                    'player': player_num,
                    'distance': min_distance,
                    'required_distance': max_required_distance
                })
                conflicted_players.add(player_key)
        
        return conflicts
    
    
    def check_player_collisions(self, team1_positions, team2_positions):
        """Check if any players are colliding with each other"""
        collisions = []
        
        # Check collisions within team 1
        for i in range(len(team1_positions)):
            for j in range(i + 1, len(team1_positions)):
                pos1 = team1_positions[i]
                pos2 = team1_positions[j]
                distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                total_radius = PLAYER_RADIUS + PLAYER_RADIUS  # Both players' radii
                
                if distance < total_radius:
                    collisions.append({
                        'team': 1,
                        'players': sorted([i + 1, j + 1]),  # 1-indexed and sorted
                        'distance': distance,
                        'required_distance': total_radius
                    })
        
        # Check collisions within team 2
        for i in range(len(team2_positions)):
            for j in range(i + 1, len(team2_positions)):
                pos1 = team2_positions[i]
                pos2 = team2_positions[j]
                distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                total_radius = PLAYER_RADIUS + PLAYER_RADIUS
                
                if distance < total_radius:
                    collisions.append({
                        'team': 2,
                        'players': sorted([i + 1, j + 1]),  # 1-indexed and sorted
                        'distance': distance,
                        'required_distance': total_radius
                    })
        
        return collisions
    
    def validate_tactic(self, tactic_key):
        """Validate a tactic according to editor rules"""
        tactic = None
        
        if tactic_key in self.prebuilt_tactics:
            tactic = self.prebuilt_tactics[tactic_key]
        elif tactic_key in self.custom_tactics and self.custom_tactics[tactic_key] is not None:
            tactic = self.custom_tactics[tactic_key]
        
        if tactic is None:
            return False, ["Tactic not found"]
        
        # Get positions for both teams
        if 'positions' in tactic:
            # New structure - generate team2 positions by mirroring
            team1_pos = tactic['positions']
            team2_pos = self.mirror_positions_for_team2(team1_pos)
        else:
            # Legacy structure for custom tactics
            team1_pos = tactic.get('team1_positions', [])
            team2_pos = tactic.get('team2_positions', [])
        
        errors = []
        
        # Check ball conflicts
        ball_conflicts = self.check_player_ball_conflicts(team1_pos, team2_pos)
        if ball_conflicts:
            for conflict in ball_conflicts:
                errors.append(f"Player {conflict['player']} overlaps ball zone")
        
        # Check player collisions
        player_collisions = self.check_player_collisions(team1_pos, team2_pos)
        if player_collisions:
            for collision in player_collisions:
                players_str = ", ".join(map(str, collision['players']))
                errors.append(f"Players {players_str} collision")
        
        # Check field bounds
        for team, positions in [(1, team1_pos), (2, team2_pos)]:
            for i, pos in enumerate(positions):
                x, y = pos
                if not (PLAYER_RADIUS <= x <= FIELD_WIDTH - PLAYER_RADIUS and 
                       PLAYER_RADIUS <= y <= FIELD_HEIGHT - PLAYER_RADIUS):
                    errors.append(f"Player {i+1} out of bounds")
        
        return len(errors) == 0, errors
    
    def validate_all_tactics(self):
        """Validate all prebuilt and custom tactics"""
        invalid_tactics = []
        
        # Check prebuilt tactics
        for tactic_key in self.prebuilt_tactics.keys():
            is_valid, errors = self.validate_tactic(tactic_key)
            if not is_valid:
                invalid_tactics.append({
                    'key': tactic_key,
                    'name': self.prebuilt_tactics[tactic_key]['name'],
                    'type': 'prebuilt',
                    'errors': errors
                })
        
        # Check custom tactics
        for tactic_key, tactic in self.custom_tactics.items():
            if tactic is not None:
                is_valid, errors = self.validate_tactic(tactic_key)
                if not is_valid:
                    invalid_tactics.append({
                        'key': tactic_key,
                        'name': tactic['name'],
                        'type': 'custom',
                        'errors': errors
                    })
        
        return invalid_tactics
    
    def remove_invalid_custom_tactics(self, invalid_tactics):
        """Remove invalid custom tactics"""
        removed_count = 0
        for invalid in invalid_tactics:
            if invalid['type'] == 'custom':
                self.custom_tactics[invalid['key']] = None
                removed_count += 1
        
        if removed_count > 0:
            self.save_custom_tactics()
        
        return removed_count
    
    def get_formation_preview_positions(self, tactic_key, team, preview_scale=0.3, preview_offset=(50, 50)):
        """Get scaled positions for formation preview in UI"""
        positions = self.get_tactic_positions(tactic_key, team)
        preview_positions = []
        
        for pos in positions:
            preview_x = preview_offset[0] + pos[0] * preview_scale
            preview_y = preview_offset[1] + pos[1] * preview_scale
            preview_positions.append((preview_x, preview_y))
        
        return preview_positions
    
    def draw_formation_preview(self, screen, tactic_key, team, x, y, scale=0.9375):
        """Draw a formation preview showing half field rotated 90 degrees left"""
        positions = self.get_tactic_positions(tactic_key, team)
        
        # Preview dimensions (125% bigger than 0.75, showing half field)
        preview_width = FIELD_HEIGHT * scale  # Width becomes height due to 90° rotation
        preview_height = (FIELD_WIDTH // 2) * scale  # Height becomes half width
        
        # Draw field background (rotated)
        field_rect = pygame.Rect(x, y, preview_width, preview_height)
        pygame.draw.rect(screen, DARK_GREEN, field_rect)
        pygame.draw.rect(screen, WHITE, field_rect, 2)
        
        # Determine which half to show based on team
        if team == 1:
            # Show left half for team 1 (their defensive half)
            x_offset = 0
            show_left_goal = True
        else:
            # Show right half for team 2 (their defensive half) 
            x_offset = FIELD_WIDTH // 2
            show_left_goal = False
        
        # Draw center line (now horizontal due to rotation)
        if team == 1:
            # For team 1, center line is at the right edge
            center_line_x = x + preview_width - 2
            pygame.draw.line(screen, WHITE, (center_line_x, y), (center_line_x, y + preview_height), 2)
        else:
            # For team 2, center line is at the left edge
            center_line_x = x + 2
            pygame.draw.line(screen, WHITE, (center_line_x, y), (center_line_x, y + preview_height), 2)
        
        # Draw goal
        goal_width = GOAL_WIDTH * scale
        goal_depth = GOAL_DEPTH * scale
        
        if show_left_goal:
            # Left goal (team 1's goal) - now at bottom due to rotation
            goal_x = x + (preview_width - goal_width) // 2
            goal_y = y + preview_height
            pygame.draw.rect(screen, WHITE, (goal_x, goal_y, goal_width, goal_depth), 2)
        else:
            # Right goal (team 2's goal) - now at bottom due to rotation  
            goal_x = x + (preview_width - goal_width) // 2
            goal_y = y - goal_depth
            pygame.draw.rect(screen, WHITE, (goal_x, goal_y, goal_width, goal_depth), 2)
        
        # Draw players with rotation and filtering
        team_color = TEAM1_COLOR if team == 1 else TEAM2_COLOR
        player_radius = max(10, int(PLAYER_RADIUS * scale * 0.8))  # Slightly bigger for better visibility
        
        for i, pos in enumerate(positions):
            orig_x, orig_y = pos
            
            # Filter to only show players in the relevant half
            if team == 1 and orig_x > FIELD_WIDTH // 2:
                continue  # Skip players in opponent's half
            elif team == 2 and orig_x < FIELD_WIDTH // 2:
                continue  # Skip players in opponent's half
            
            # Apply 90 degree rotation to the left: (x,y) -> (-y, x)
            # But we need to adjust for the coordinate system and centering
            rotated_x = (orig_y) * scale  # y becomes x
            rotated_y = ((FIELD_WIDTH // 2) - (orig_x - x_offset)) * scale  # x becomes y (flipped)
            
            # Position in preview area
            player_x = x + rotated_x
            player_y = y + rotated_y
            
            # Only draw if within preview bounds
            if (x <= player_x <= x + preview_width and 
                y <= player_y <= y + preview_height):
                
                pygame.draw.circle(screen, team_color, (int(player_x), int(player_y)), player_radius)
                pygame.draw.circle(screen, WHITE, (int(player_x), int(player_y)), player_radius, 2)
                
                # Player number
                font = pygame.font.Font(None, 28)  # Bigger font for better visibility
                text = font.render(str(i + 1), True, WHITE)
                text_rect = text.get_rect(center=(int(player_x), int(player_y)))
                screen.blit(text, text_rect)

class CustomTacticsEditor:
    """Editor for creating custom tactics"""
    def __init__(self, tactics_manager):
        self.tactics_manager = tactics_manager
        self.editing_slot = None  # 'custom1' through 'custom6'
        self.positions = [(FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5)] + [(FIELD_WIDTH * 0.25, FIELD_HEIGHT * (0.2 + i * 0.15)) for i in range(4)]
        self.selected_player = 0
        self.dragging = False
        self.tactic_name = ""
        
        # Save/Reset button states
        self.save_button_rect = None
        self.reset_button_rect = None
        self.save_button_hovered = False
        self.reset_button_hovered = False
        
        # Track unsaved changes
        self.has_unsaved_changes = False
        self.original_positions = []
        self.original_name = ""
        
        # Consolidated warning system
        self.show_consolidated_warning = False
        self.consolidated_warning_start_time = 0
        self.consolidated_warning_duration = 5000  # 5 seconds in milliseconds
        self.consolidated_warning_fade_alpha = 255  # Start fully opaque
        
        # Ball conflict validation
        self.ball_conflicts = []
        
        # Player collision tracking
        self.player_collisions = []
    
    def start_editing(self, slot_key):
        """Start editing a custom tactic slot"""
        self.editing_slot = slot_key
        self.selected_player = 0
        self.dragging = False
        self.has_unsaved_changes = False
        
        # Load existing tactic if it exists
        if self.tactics_manager.custom_tactics[slot_key] is not None:
            tactic = self.tactics_manager.custom_tactics[slot_key]
            # Handle both new and legacy tactic formats
            if 'positions' in tactic:
                self.positions = tactic['positions'].copy()
            elif 'team1_positions' in tactic:
                # Legacy format - use team1_positions
                self.positions = tactic['team1_positions'].copy()
            else:
                self.reset_to_default_positions()
            self.tactic_name = tactic['name']
        else:
            # Set default positions
            self.reset_to_default_positions()
            slot_number = slot_key[-1]
            self.tactic_name = f"Custom Tactics #{slot_number}"
        
        # Store original state for unsaved changes detection
        self.original_positions = self.positions.copy()
        self.original_name = self.tactic_name
        
        # Check for initial ball conflicts
        self.check_realtime_ball_conflicts()
        
        # Check for initial player collisions
        self.check_realtime_player_collisions()
    
    def reset_to_default_positions(self):
        """Reset to default balanced formation"""
        self.positions = [
            (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
            (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.25), # Defender 1
            (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.75), # Defender 2
            (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.35),  # Midfielder
            (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.65),  # Forward
        ]
        self.mark_unsaved_changes()
        
        # Check for ball conflicts after reset
        self.check_realtime_ball_conflicts()
        
        # Check for player collisions after reset
        self.check_realtime_player_collisions()
    
    def mark_unsaved_changes(self):
        """Mark that there are unsaved changes"""
        self.has_unsaved_changes = True
    
    def check_unsaved_changes(self):
        """Check if there are unsaved changes"""
        return (self.positions != self.original_positions or
                self.tactic_name != self.original_name)
    
    def handle_mouse_move(self, mouse_pos):
        """Handle mouse movement for button hover effects"""
        if self.save_button_rect:
            self.save_button_hovered = self.save_button_rect.collidepoint(mouse_pos)
        if self.reset_button_rect:
            self.reset_button_hovered = self.reset_button_rect.collidepoint(mouse_pos)
    
    def handle_mouse_click(self, mouse_pos):
        """Handle mouse click in editor"""
        # Check button clicks first
        if hasattr(self, 'save_button_rect') and self.save_button_rect and self.save_button_rect.collidepoint(mouse_pos):
            return self.save_tactic()
        
        if hasattr(self, 'reset_button_rect') and self.reset_button_rect and self.reset_button_rect.collidepoint(mouse_pos):
            self.reset_to_default_positions()
            return True
        
        mx, my = mouse_pos
        
        # Check if click is within field area
        if (hasattr(self, 'field_x') and hasattr(self, 'field_y') and hasattr(self, 'field_width') and hasattr(self, 'field_height') and
            self.field_x <= mx <= self.field_x + self.field_width and 
            self.field_y <= my <= self.field_y + self.field_height):
            
            # Check if clicking on a player
            for i, pos in enumerate(self.positions):
                orig_x, orig_y = pos
                
                # Skip players not in team1's half (only edit team1 positions)
                if orig_x > FIELD_WIDTH // 2:
                    continue
                
                # Transform to screen coordinates
                rotated_x = orig_y
                rotated_y = (FIELD_WIDTH // 2) - orig_x
                
                screen_x = self.field_x + rotated_x * self.field_scale
                screen_y = self.field_y + rotated_y * self.field_scale
                
                # Check distance to mouse click
                distance = math.sqrt((mx - screen_x)**2 + (my - screen_y)**2)
                player_radius = max(8, int(PLAYER_RADIUS * self.field_scale * 0.8))
                
                if distance <= player_radius + 5:  # Small tolerance for easier clicking
                    self.selected_player = i
                    self.dragging = True
                    return True
        
        return False
    
    def handle_mouse_drag(self, mouse_pos):
        """Handle mouse drag in editor"""
        if not self.dragging or not hasattr(self, 'field_scale'):
            return
        
        mx, my = mouse_pos
        
        # Convert screen coordinates back to field coordinates
        field_mx = (mx - self.field_x) / self.field_scale
        field_my = (my - self.field_y) / self.field_scale
        
        # Transform back to original field coordinates (reverse the rotation)
        orig_x = (FIELD_WIDTH // 2) - field_my
        orig_y = field_mx
        
        # Clamp to team 1's half and field bounds
        orig_x = max(PLAYER_RADIUS, min(FIELD_WIDTH // 2 - PLAYER_RADIUS, orig_x))
        orig_y = max(PLAYER_RADIUS, min(FIELD_HEIGHT - PLAYER_RADIUS, orig_y))
        
        # Update player position
        self.positions[self.selected_player] = (orig_x, orig_y)
        
        self.mark_unsaved_changes()
        
        # Check for ball conflicts in real-time
        self.check_realtime_ball_conflicts()
        
        # Check for player collisions in real-time
        self.check_realtime_player_collisions()
    
    def handle_mouse_release(self):
        """Handle mouse release in editor"""
        self.dragging = False
    
    def dismiss_consolidated_warning(self):
        """Dismiss the consolidated warning"""
        self.show_consolidated_warning = False
        self.consolidated_warning_start_time = 0
        self.consolidated_warning_fade_alpha = 255
    
    def update_consolidated_warning(self):
        """Update consolidated warning fade and auto-dismiss"""
        if not self.show_consolidated_warning:
            return
        
        # Check if there are still any violations
        has_ball_conflicts = len(self.ball_conflicts) > 0
        has_player_collisions = len(self.player_collisions) > 0
        
        if not has_ball_conflicts and not has_player_collisions:
            # No violations - start fading
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.consolidated_warning_start_time
            
            if elapsed >= self.consolidated_warning_duration:
                # Auto-dismiss after duration
                self.dismiss_consolidated_warning()
            else:
                # Calculate fade alpha (linear fade from 255 to 0)
                fade_progress = elapsed / self.consolidated_warning_duration
                self.consolidated_warning_fade_alpha = max(0, int(255 * (1.0 - fade_progress)))
        else:
            # Violations still exist - keep warning fully visible
            self.consolidated_warning_fade_alpha = 255
            # Update the warning start time to prevent premature fading
            self.consolidated_warning_start_time = pygame.time.get_ticks()
    
    def check_realtime_ball_conflicts(self):
        """Check for ball conflicts in real-time and trigger warnings"""
        # Generate team2 positions by mirroring team1 positions
        team2_positions = self.tactics_manager.mirror_positions_for_team2(self.positions)
        
        # Get current ball conflicts
        current_conflicts = self.tactics_manager.check_player_ball_conflicts(
            self.positions, team2_positions
        )
        
        # Check if conflicts have changed
        conflicts_changed = (
            len(current_conflicts) != len(self.ball_conflicts) or
            any(c1 != c2 for c1, c2 in zip(current_conflicts, self.ball_conflicts))
        )
        
        # Update conflicts list
        self.ball_conflicts = current_conflicts
        
        # Trigger consolidated warning if needed
        if (current_conflicts or self.player_collisions) and (not self.show_consolidated_warning or conflicts_changed):
            self.show_consolidated_warning = True
            self.consolidated_warning_start_time = pygame.time.get_ticks()
            self.consolidated_warning_fade_alpha = 255
        elif not current_conflicts and not self.player_collisions and self.show_consolidated_warning:
            # No violations - dismiss warning
            self.dismiss_consolidated_warning()
    
    def check_realtime_player_collisions(self):
        """Check for player collisions in real-time and trigger warnings"""
        # Generate team2 positions by mirroring team1 positions
        team2_positions = self.tactics_manager.mirror_positions_for_team2(self.positions)
        
        # Get current collisions for all players
        current_collisions = self.tactics_manager.check_player_collisions(
            self.positions, team2_positions
        )
        
        # Check if collisions have changed
        collisions_changed = (
            len(current_collisions) != len(self.player_collisions) or
            any(c1 != c2 for c1, c2 in zip(current_collisions, self.player_collisions))
        )
        
        # Update collisions list
        self.player_collisions = current_collisions
        
        # Trigger consolidated warning if needed
        if (current_collisions or self.ball_conflicts) and (not self.show_consolidated_warning or collisions_changed):
            self.show_consolidated_warning = True
            self.consolidated_warning_start_time = pygame.time.get_ticks()
            self.consolidated_warning_fade_alpha = 255
        elif not current_collisions and not self.ball_conflicts and self.show_consolidated_warning:
            # No violations - dismiss warning
            self.dismiss_consolidated_warning()

    def save_tactic(self):
        """Save the current custom tactic"""
        if not self.editing_slot or not self.tactic_name.strip():
            return False
        
        # Generate team2 positions by mirroring team1 positions
        team2_positions = self.tactics_manager.mirror_positions_for_team2(self.positions)
        
        # Check for player collisions
        collisions = self.tactics_manager.check_player_collisions(
            self.positions, team2_positions
        )
        
        if collisions:
            # Store collisions and show warning
            self.player_collisions = collisions
            self.show_consolidated_warning = True
            self.consolidated_warning_start_time = pygame.time.get_ticks()
            self.consolidated_warning_fade_alpha = 255
            return False
        
        # Check for ball position conflicts
        conflicts = self.tactics_manager.check_player_ball_conflicts(
            self.positions, team2_positions
        )
        
        if conflicts:
            # Store conflicts and show warning with timestamp
            self.ball_conflicts = conflicts
            self.show_consolidated_warning = True
            self.consolidated_warning_start_time = pygame.time.get_ticks()
            self.consolidated_warning_fade_alpha = 255
            return False
        
        # No conflicts, proceed with save
        success = self.tactics_manager.create_custom_tactic(
            self.editing_slot,
            self.tactic_name.strip(),
            self.positions
        )
        
        if success:
            # Update original state to current state
            self.original_positions = self.positions.copy()
            self.original_name = self.tactic_name
            self.has_unsaved_changes = False
            self.show_consolidated_warning = False
            self.ball_conflicts = []
            self.player_collisions = []
        
        return success
    
    def draw(self, screen):
        """Draw the custom tactics editor"""
        # Check for real-time ball conflicts
        self.check_realtime_ball_conflicts()
        
        # Check for real-time player collisions
        self.check_realtime_player_collisions()
        
        # Update consolidated warning state
        self.update_consolidated_warning()
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw instructions
        font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)
        slot_name = self.editing_slot.capitalize() if self.editing_slot else "Unknown"
        
        # Unsaved changes indicator
        if self.check_unsaved_changes():
            changes_text = small_font.render("Unsaved changes", True, YELLOW)
            screen.blit(changes_text, (10, 75))
        
        # Draw field background (rotated half-field view)
        # Calculate dimensions for rotated half field
        half_field_width = FIELD_WIDTH // 2
        half_field_height = FIELD_HEIGHT
        
        # After 90-degree left rotation: width becomes height, height becomes width
        rotated_width = half_field_height
        rotated_height = half_field_width
        
        # Scale to fit window with margins
        margin = 100
        max_width = SCREEN_WIDTH - margin * 2
        max_height = SCREEN_HEIGHT - 200  # Leave space for UI elements
        
        scale_x = max_width / rotated_width
        scale_y = max_height / rotated_height
        self.field_scale = min(scale_x, scale_y, 1.5)  # Cap at 1.5x for readability
        
        # Calculate field dimensions and position
        self.field_width = int(rotated_width * self.field_scale)
        self.field_height = int(rotated_height * self.field_scale)
        self.field_x = (SCREEN_WIDTH - self.field_width) // 2
        self.field_y = 150  # Below UI text
        
        # Draw field background
        field_rect = pygame.Rect(self.field_x, self.field_y, self.field_width, self.field_height)
        pygame.draw.rect(screen, GREEN, field_rect)
        
        # Draw grass stripes (rotated)
        stripe_count = 8
        stripe_height = self.field_height // stripe_count
        for i in range(stripe_count):
            if i % 2 == 0:
                stripe_rect = pygame.Rect(self.field_x, self.field_y + i * stripe_height, self.field_width, stripe_height)
                pygame.draw.rect(screen, (30, 180, 30), stripe_rect)
        
        # Border
        pygame.draw.rect(screen, WHITE, field_rect, 3)
        
        # Draw field markings for team 1's half (only team we edit)
        # Team 1's half (left side) - goal at bottom after rotation
        # Center line at top
        pygame.draw.line(screen, WHITE, (self.field_x, self.field_y), (self.field_x + self.field_width, self.field_y), 3)
        
        # Goal area at bottom
        goal_area_width = int(200 * self.field_scale)  # Original penalty area width
        goal_area_height = int(100 * self.field_scale)  # Original goal area width becomes height
        goal_x = self.field_x + (self.field_width - goal_area_width) // 2
        goal_y = self.field_y + self.field_height - goal_area_height
        pygame.draw.rect(screen, WHITE, (goal_x, goal_y, goal_area_width, goal_area_height), 3)
        
        # Penalty area
        penalty_area_width = int(320 * self.field_scale)  # Original penalty area height
        penalty_area_height = int(200 * self.field_scale)  # Original penalty area width
        penalty_x = self.field_x + (self.field_width - penalty_area_width) // 2
        penalty_y = self.field_y + self.field_height - penalty_area_height
        pygame.draw.rect(screen, WHITE, (penalty_x, penalty_y, penalty_area_width, penalty_area_height), 3)
        
        # Goal posts
        goal_post_width = int(GOAL_WIDTH * self.field_scale)
        goal_post_depth = int(GOAL_DEPTH * self.field_scale)
        goal_post_x = self.field_x + (self.field_width - goal_post_width) // 2
        goal_post_y = self.field_y + self.field_height
        pygame.draw.rect(screen, WHITE, (goal_post_x, goal_post_y, goal_post_width, goal_post_depth), 3)
        
        # Draw players (always team 1 colors since we only edit team 1)
        current_time = pygame.time.get_ticks()
        blink_interval = 250  # Blink every 250ms
        is_blink_white = (current_time // blink_interval) % 2 == 0
        
        team_color = TEAM1_COLOR
        
        for i, pos in enumerate(self.positions):
            orig_x, orig_y = pos
            
            # Only show players in team 1's half (left half)
            if orig_x > FIELD_WIDTH // 2:
                continue
                
            # Transform coordinates to rotated half-field view
            rotated_x = orig_y
            rotated_y = (FIELD_WIDTH // 2) - orig_x
            
            # Scale and position on screen
            screen_x = self.field_x + rotated_x * self.field_scale
            screen_y = self.field_y + rotated_y * self.field_scale
            
            # Check if this player has violations
            has_ball_conflict = any(c['team'] == 1 and c['player'] == i+1 for c in self.ball_conflicts)
            has_player_collision = any(1 == coll['team'] and i+1 in coll['players'] for coll in self.player_collisions)
            
            # Determine player color with blinking effect
            is_selected = (i == self.selected_player)
            if (has_ball_conflict or has_player_collision) and self.show_consolidated_warning:
                if has_player_collision:
                    # Player collision: blink between orange and white
                    color = (255, 165, 0) if is_blink_white else WHITE  # Orange
                    border_color = WHITE if is_blink_white else (255, 165, 0)
                else:
                    # Ball conflict: blink between black and white
                    color = WHITE if is_blink_white else BLACK
                    border_color = BLACK if is_blink_white else WHITE
            elif is_selected:
                color = YELLOW
                border_color = WHITE
            else:
                color = team_color
                border_color = BLACK
            
            # Draw player
            player_radius = max(8, int(PLAYER_RADIUS * self.field_scale * 0.8))
            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), player_radius)
            pygame.draw.circle(screen, border_color, (int(screen_x), int(screen_y)), player_radius, 2)
            
            # Player number
            font_size = max(20, int(24 * self.field_scale))
            number_font = pygame.font.Font(None, font_size)
            text = number_font.render(str(i + 1), True, WHITE)
            text_rect = text.get_rect(center=(int(screen_x), int(screen_y)))
            screen.blit(text, text_rect)
        
        # Draw ball starting position and safe zones (rotated view)
        ball_positions = self.tactics_manager.get_ball_positions()
        for ball_info in ball_positions:
            bx, by = ball_info['position']
            
            # Only show ball in team 1's half for clarity
            if bx > FIELD_WIDTH // 2:
                continue
                
            # Transform ball position to rotated coordinates
            rotated_bx = by
            rotated_by = (FIELD_WIDTH // 2) - bx
            
            # Scale and position on screen
            ball_screen_x = self.field_x + rotated_bx * self.field_scale
            ball_screen_y = self.field_y + rotated_by * self.field_scale
            warning_zone_radius = ball_info['radius'] * self.field_scale
            
            # Draw warning zone (semi-transparent)
            if warning_zone_radius > 5:  # Only draw if visible
                warning_zone_surface = pygame.Surface((warning_zone_radius * 2, warning_zone_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(warning_zone_surface, (255, 255, 0, 60), (int(warning_zone_radius), int(warning_zone_radius)), int(warning_zone_radius))
                screen.blit(warning_zone_surface, (ball_screen_x - warning_zone_radius, ball_screen_y - warning_zone_radius))
            
            # Draw ball position
            ball_radius = max(5, int(BALL_RADIUS * self.field_scale))
            pygame.draw.circle(screen, WHITE, (int(ball_screen_x), int(ball_screen_y)), ball_radius)
            pygame.draw.circle(screen, BLACK, (int(ball_screen_x), int(ball_screen_y)), ball_radius, 2)
            
            # Ball label
            label_font_size = max(16, int(20 * self.field_scale))
            ball_font = pygame.font.Font(None, label_font_size)
            ball_text = ball_font.render("BALL", True, WHITE)
            ball_text_rect = ball_text.get_rect(center=(int(ball_screen_x), int(ball_screen_y - 25 * self.field_scale)))
            screen.blit(ball_text, ball_text_rect)
        
        # Draw Save and Reset buttons
        button_y = FIELD_Y + FIELD_HEIGHT + 20
        button_width = 100
        button_height = 40
        button_gap = 20
        
        # Save button
        save_x = FIELD_X + (FIELD_WIDTH - (button_width * 2 + button_gap)) // 2
        self.save_button_rect = pygame.Rect(save_x, button_y, button_width, button_height)
        save_color = (100, 150, 100) if self.save_button_hovered else (60, 120, 60)
        pygame.draw.rect(screen, save_color, self.save_button_rect)
        pygame.draw.rect(screen, WHITE, self.save_button_rect, 2)
        
        save_text = small_font.render("Save (S)", True, WHITE)
        save_text_rect = save_text.get_rect(center=self.save_button_rect.center)
        screen.blit(save_text, save_text_rect)
        
        # Reset button
        reset_x = save_x + button_width + button_gap
        self.reset_button_rect = pygame.Rect(reset_x, button_y, button_width, button_height)
        reset_color = (150, 100, 100) if self.reset_button_hovered else (120, 60, 60)
        pygame.draw.rect(screen, reset_color, self.reset_button_rect)
        pygame.draw.rect(screen, WHITE, self.reset_button_rect, 2)
        
        reset_text = small_font.render("Reset (R)", True, WHITE)
        reset_text_rect = reset_text.get_rect(center=self.reset_button_rect.center)
        screen.blit(reset_text, reset_text_rect)
        
        # Instructions
        instructions = [
            "Click and drag players to position them",
            "Press T to switch between teams",
            "Click buttons or use keyboard shortcuts",
            "ESC to exit (prompts if unsaved changes)",
            "Yellow zones show ball positions - keep players clear!"
        ]
        
        y_offset = button_y + button_height + 20
        for instruction in instructions:
            inst_text = small_font.render(instruction, True, WHITE)
            screen.blit(inst_text, (10, y_offset))
            y_offset += 25
        
        # Draw consolidated warning text if needed
        if self.show_consolidated_warning:
            self.draw_consolidated_warning_text(screen)
    
    def draw_consolidated_warning_text(self, screen):
        """Draw consolidated warning as fading text with list of issues"""
        if self.consolidated_warning_fade_alpha <= 0:
            return
        
        # Build consolidated warning message
        warning_lines = ["Cannot save:"]
        
        # Add ball conflicts (group by editing team)
        ball_players = []
        for conflict in self.ball_conflicts:
            if conflict['team'] == 1:  # Only show team 1 conflicts since we only edit team 1
                ball_players.append(conflict['player'])
        
        if ball_players:
            ball_players.sort()  # Ascending order
            if len(ball_players) == 1:
                warning_lines.append(f"Player {ball_players[0]} in ball zone")
            else:
                players_str = ", ".join(map(str, ball_players))
                warning_lines.append(f"Players {players_str} in ball zone")
        
        # Add player collisions (group by editing team)
        collision_players = set()
        for collision in self.player_collisions:
            if collision['team'] == 1:  # Only show team 1 collisions since we only edit team 1
                collision_players.update(collision['players'])
        
        if collision_players:
            collision_list = sorted(list(collision_players))  # Ascending order
            if len(collision_list) == 1:
                warning_lines.append(f"Player {collision_list[0]} conflicted in position")
            else:
                players_str = ", ".join(map(str, collision_list))
                warning_lines.append(f"Players {players_str} conflicted in their position")
        
        warning_y = SCREEN_HEIGHT // 2 - int(SCREEN_HEIGHT * 0.40)
        
        # Font size reduced by 20% (from 48 to 38)
        font_size = int(25)
        font = pygame.font.Font(None, font_size)
        
        # Draw each line
        line_height = font_size + 5
        total_height = len(warning_lines) * line_height
        start_y = warning_y - total_height // 2
        
        for i, line in enumerate(warning_lines):
            # Create text with current alpha
            text_surface = font.render(line, True, RED)
            faded_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
            faded_surface.fill((255, 255, 255, self.consolidated_warning_fade_alpha))
            faded_surface.blit(text_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            # Center and draw the text
            text_rect = faded_surface.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * line_height))
            screen.blit(faded_surface, text_rect)