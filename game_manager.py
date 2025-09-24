import pygame
import math
import random
import sys
import os
from constants import *
from player import Player
from ball import Ball
from physics_utils import resolve_circle_circle
from field import Field
from sound_manager import SoundManager
from tactics import TacticsManager, CustomTacticsEditor
from resource_manager import get_asset_path
from config_manager import get_audio_config, set_audio_config

class GameManager:
    def __init__(self):
        self.field = Field()
        self.ball = Ball(FIELD_X + BALL_START_POS[0], FIELD_Y + BALL_START_POS[1])
        self.sounds = SoundManager()
        
        # Music state tracking
        self._last_music_state = None  # Track what music should be playing
        
        # Initialize tactics manager
        self.tactics_manager = TacticsManager()
        self.custom_tactics_editor = CustomTacticsEditor(self.tactics_manager)
        
        # Initialize teams with default formations
        self.team1_players = []
        self.team2_players = []
        self.init_players()
        
        # Game state
        self.current_team = 1  # 1 or 2
        self.current_player_index = 0
        self.current_phase = PHASE_SELECT_PLAYER
        # Start at menu to let user pick singleplayer & difficulty
        self.game_state = GAME_STATE_MENU
        self.goal_banner_until = 0  # timestamp for goal notification display
        
        # Modes (can be adjusted in menu)
        self.singleplayer = DEFAULT_SINGLEPLAYER
        self.bot_team = BOT_TEAM
        self.bot_difficulty = BOT_DEFAULT_DIFFICULTY
        
        # Game configuration options
        self.game_mode = 'goals_only'  # 'goals_only', 'turns_only', 'both'
        self.max_goals = 5  # First to reach this many goals wins (1-50)
        self.max_turns_limit = 50  # Game ends after this many turns (10-200)
        
        # Volume configuration (0.0 to 1.0) - load from config manager
        audio_config = get_audio_config()
        self.master_volume = audio_config.get('master_volume', DEFAULT_MASTER_VOLUME)
        self.sfx_volume = audio_config.get('sfx_volume', DEFAULT_SFX_VOLUME)
        self.bgm_volume = audio_config.get('bgm_volume', DEFAULT_BGM_VOLUME)
        
        # Load background image and create gradient surface
        try:
            self.bg_image = pygame.image.load(get_asset_path("bg.png"))
            self.bg_image = pygame.transform.scale(self.bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error:
            self.bg_image = None
        
        self.gradient_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Audio configuration save debouncing
        self._audio_save_timer = 0
        self._audio_save_delay = 1000  # Save after 1 second of no changes

        # Scores
        self.team1_score = 0
        self.team2_score = 0
        
        # Force meter
        self.force_power = 0
        self.force_increasing = True
        self.force_meter_active = False
        
        # Turn management - Queue-based system
        self.turn_number = 1
        self.max_turns = self.max_turns_limit  # Game ends based on configuration
        self.turn_queue = [1, 2]  # Teams in order they should play
        self.queue_index = 0  # Current position in queue
        self.teams_played_this_turn = set()  # Track who has played in current turn
        
        # Collision sound tracking
        self.active_collisions = set()
        
        # Bot optimization cache
        self._bot_cache = {
            'last_frame': -1,
            'context': None,
            'opponent_distances': None,
            'team_distances': None
        }
        
        # Enhanced bot state tracking and prediction
        self._bot_ball_history = []  # Track ball positions for velocity prediction
        self._bot_player_positions = {}  # Track opponent player positions
        self._bot_anticipation_mode = False  # Whether bot is in anticipation mode
        self._bot_defensive_formation = False  # Whether bot should prioritize defense
        self._bot_last_opponent_action = 0  # Time of last opponent action
        self._bot_pattern_detection = {}  # Track opponent patterns
        self._bot_pressure_zones = []  # Areas where bot applies pressure
        
        # Text rendering cache
        self._text_cache = {}  # Track active collision pairs to prevent sound spam
        
        # Goal Animation System
        self.goal_animation_active = False
        self.goal_animation_start_time = 0
        self.goal_animation_ball_pos = (0, 0)  # Ball position when goal was scored
        self.camera_zoom = 1.0  # Current zoom level
        self.camera_center_x = SCREEN_WIDTH // 2  # Camera center X
        self.camera_center_y = SCREEN_HEIGHT // 2  # Camera center Y
        
        # Pause-aware timing for animations
        self.pause_start_time = 0  # When pause started
        self.total_pause_duration = 0  # Total time spent paused for current animation
        
        # Animation phases and timings (in milliseconds)
        self.ZOOM_IN_DURATION = 50      # Zoom to 500% in 50ms
        self.ZOOM_OUT_DURATION = 1950   # Zoom back to 100% in 1950ms  
        self.RESET_DURATION = 1500      # Reset positions with ease-in-out in 1500ms
        self.ZOOM_IN_SCALE = 5.0        # 500% zoom
        
        # Animation state tracking
        self.animation_phase = 0  # 0: none, 1: zoom in, 2: zoom out, 3: reset positions
        
        # Store goal-moment positions for smooth reset animation
        self.goal_moment_player_positions = []  # Where players were when goal was scored
        self.goal_moment_ball_position = (0, 0)  # Where ball was when goal was scored
        self.target_player_positions = []  # Where players should end up (kickoff positions)
        self.target_ball_position = (0, 0)  # Where ball should end up (kickoff position)
        
        # UI elements
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Custom tactics UI state
        self._show_save_confirmation = False
        self._show_unsaved_changes_dialog = False
        
        # Tactics validation state
        self._show_invalid_tactics_dialog = False
        self._invalid_tactics_list = []
        self._validation_performed = False
        self._show_reset_all_confirmation = False
        self._show_delete_confirmation = False
        
        # AI timers
        self._bot_action_cooldown_ms = BOT_THINK_MS.get(self.bot_difficulty, 350)
        self._last_bot_action = 0

        # Menu state
        self._menu_items = [
            ("Mode", None),
            ("Bot Team", None), 
            ("Difficulty", None),
            ("Game Mode", None),
            ("Goal Limit", None),
            ("Turn Limit", None),
            ("Audio Settings", None)
        ]
        self._menu_index = 0
        
        # Key repeat delay system for menu navigation
        # Note: pygame.key.set_repeat() handles the basic repeat, these delays prevent excessive speed
        self._key_repeat_delay = 60  # Milliseconds between key repeats (reduced since pygame handles initial delay)
        self._fast_key_repeat_delay = 40  # Faster repeat for value changes
        self._last_navigation_time = 0  # Last time a navigation key was pressed
        self._last_value_change_time = 0  # Last time a value change key was pressed
        
        # Audio settings menu state
        self._audio_menu_items = [
            ("Master Volume", None),
            ("SFX Volume", None),
            ("BGM Volume", None)
        ]
        self._audio_menu_index = 0
        
        # Tactics selection state
        self._tactics_phase = 'select'  # 'select' or 'custom'
        self._tactics_team = 1
        self._tactics_index = 0
        self._available_tactics = []

        # UI/aim state
        self._aim_seeded = False  # ensures arrow initially points to ball before deciding
        
        # Flag to start music on first update
        self._music_initialized = False
        
        # Coin flip system
        self.coin_flip_active = False
        self.coin_flip_start_time = 0
        self.coin_flip_result = random.randint(1, 2)  # Default value, will be properly randomized when coin flip starts
        self.coin_flip_rotation = 0  # Current rotation angle
        self.coin_flip_winner_determined = False
        self.coin_flip_result_display_time = 0  # When to stop showing result
        
    def start_pause_timing(self):
        """Called when game enters pause state during animations"""
        self.pause_start_time = pygame.time.get_ticks()
        # Note: Sound pausing is handled in main.py to ensure correct order
    
    def end_pause_timing(self):
        """Called when game exits pause state during animations"""
        if self.pause_start_time > 0:
            pause_duration = pygame.time.get_ticks() - self.pause_start_time
            
            # Add to goal animation pause tracking
            if self.goal_animation_active:
                self.total_pause_duration += pause_duration
            
            # Note: goal_banner_until is now handled directly in banner display logic
            # to freeze the banner during pause without time manipulation
                
            self.pause_start_time = 0
            
        # Note: Sound resuming is handled in main.py to ensure correct order
    
    def get_animation_elapsed_time(self):
        """Get elapsed time for animations, excluding pause time"""
        current_time = pygame.time.get_ticks()
        raw_elapsed = current_time - self.goal_animation_start_time
        
        # Subtract total pause duration
        adjusted_elapsed = raw_elapsed - self.total_pause_duration
        
        # If currently paused, also subtract current pause duration
        if self.pause_start_time > 0:
            current_pause_duration = current_time - self.pause_start_time
            adjusted_elapsed -= current_pause_duration
            
        return max(0, adjusted_elapsed)  # Never negative
    
    def update_music(self):
        """Update background music based on current game state."""
        # Determine what music should be playing
        if self.game_state in [GAME_STATE_MENU, GAME_STATE_AUDIO, GAME_STATE_TACTICS, GAME_STATE_CUSTOM_TACTICS, GAME_STATE_COIN_FLIP]:
            target_music = 'menu'
        elif self.game_state == GAME_STATE_GAME_OVER:
            target_music = self.get_ending_music_type()
        elif self.game_state in [GAME_STATE_PLAYING, GAME_STATE_FORCE_SELECT]:
            target_music = 'ingame'
        elif self.game_state == GAME_STATE_PAUSED:
            # Keep current music but pause it
            if self.sounds.is_music_playing():
                self.sounds.pause_music()
            return
        else:
            target_music = None
        
        # Handle music state changes
        if target_music != self._last_music_state:
            if target_music == 'menu':
                self.sounds.play_menu_music()
            elif target_music == 'ingame':
                self.sounds.play_ingame_music()
            elif target_music in ['end', 'end_win', 'end_lose', 'end_tie', 'end_2p']:
                self.sounds.play_ending_music(target_music)
            elif target_music is None:
                self.sounds.stop_music()
            
            self._last_music_state = target_music
        
        # Resume music if we're leaving pause state
        if self.game_state != GAME_STATE_PAUSED and self.sounds._music_paused:
            self.sounds.resume_music()
        
    def render_multicolor_text(self, screen, segments, y, center_x=None):
        """
        Render text with multiple colors with caching.
        segments: list of (text, color) tuples
        y: vertical position
        center_x: if provided, centers the entire text at this x position
        Returns the total width of the rendered text
        """
        # Create cache key from segments
        cache_key = tuple((text, tuple(color) if isinstance(color, (list, tuple)) else color) for text, color in segments)
        
        if cache_key in self._text_cache:
            rendered_segments, total_width = self._text_cache[cache_key]
        else:
            # Pre-render all segments to calculate total width
            rendered_segments = []
            total_width = 0
            
            for text, color in segments:
                surface = self.font.render(text, True, color)
                rendered_segments.append(surface)
                total_width += surface.get_width()
            
            # Cache for future use (limit cache size to prevent memory leaks)
            if len(self._text_cache) < 20:  # Reduced cache size for memory optimization
                self._text_cache[cache_key] = (rendered_segments, total_width)
        
        # Calculate starting x position
        if center_x is not None:
            start_x = center_x - total_width // 2
        else:
            start_x = 0
        
        # Render each segment
        current_x = start_x
        for surface in rendered_segments:
            screen.blit(surface, (current_x, y))
            current_x += surface.get_width()
        
        return total_width
    
    def ease_in_out_cubic(self, t):
        """Cubic ease-in-out function for smooth animations"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            p = 2 * t - 2
            return 1 + p * p * p / 2
    
    def ease_in_cubic(self, t):
        """Cubic ease-in function for reset animation"""
        return t * t * t
    
    def linear(self, t):
        """Linear interpolation"""
        return t
    
    def start_goal_animation(self, ball_x, ball_y):
        """Start the goal zoom animation sequence"""
        self.goal_animation_active = True
        self.goal_animation_start_time = pygame.time.get_ticks()
        self.goal_animation_ball_pos = (ball_x, ball_y)
        self.animation_phase = 1  # Start with zoom in
        
        # Reset pause timing for new animation
        self.total_pause_duration = 0
        self.pause_start_time = 0
        
        # Store goal-moment positions (where objects are when goal was scored)
        self.goal_moment_player_positions = []
        for player in self.team1_players + self.team2_players:
            self.goal_moment_player_positions.append((player.x, player.y))
        self.goal_moment_ball_position = (self.ball.x, self.ball.y)
        
        # Calculate kickoff target positions using current tactics (not default positions)
        self.target_player_positions = []
        
        # Team 1 kickoff positions from current tactic
        team1_tactic_positions = self.tactics_manager.get_tactic_positions(
            self.tactics_manager.get_team_tactic(1), 1
        )
        for pos in team1_tactic_positions:
            target_x = FIELD_X + pos[0]
            target_y = FIELD_Y + pos[1]
            self.target_player_positions.append((target_x, target_y))
        
        # Team 2 kickoff positions from current tactic
        team2_tactic_positions = self.tactics_manager.get_tactic_positions(
            self.tactics_manager.get_team_tactic(2), 2
        )
        for pos in team2_tactic_positions:
            target_x = FIELD_X + pos[0]
            target_y = FIELD_Y + pos[1]
            self.target_player_positions.append((target_x, target_y))
        
        # Calculate ball kickoff position (will be set in score_goal)
        self.target_ball_position = (ball_x, ball_y)  # Will be updated by score_goal
        
        # Calculate camera center to focus on ball
        self.camera_center_x = ball_x
        self.camera_center_y = ball_y
    
    def update_goal_animation(self):
        """Update the goal animation state"""
        if not self.goal_animation_active:
            return
        
        # Use pause-aware elapsed time
        elapsed = self.get_animation_elapsed_time()
        
        if self.animation_phase == 1:  # Zoom in phase
            if elapsed <= self.ZOOM_IN_DURATION:
                t = elapsed / self.ZOOM_IN_DURATION
                self.camera_zoom = 1.0 + (self.ZOOM_IN_SCALE - 1.0) * self.linear(t)
            else:
                self.camera_zoom = self.ZOOM_IN_SCALE
                self.animation_phase = 2  # Move to zoom out
                
        elif self.animation_phase == 2:  # Zoom out phase
            zoom_out_start = self.ZOOM_IN_DURATION
            if elapsed <= zoom_out_start + self.ZOOM_OUT_DURATION:
                t = (elapsed - zoom_out_start) / self.ZOOM_OUT_DURATION
                self.camera_zoom = self.ZOOM_IN_SCALE - (self.ZOOM_IN_SCALE - 1.0) * self.ease_in_out_cubic(t)
            else:
                self.camera_zoom = 1.0
                self.animation_phase = 3  # Move to reset
                
        elif self.animation_phase == 3:  # Reset positions phase
            reset_start = self.ZOOM_IN_DURATION + self.ZOOM_OUT_DURATION
            if elapsed <= reset_start + self.RESET_DURATION:
                t = (elapsed - reset_start) / self.RESET_DURATION
                # Handle smooth position resets with physics disabled
                self.update_position_reset_animation(t)
            else:
                # Animation complete - ensure final positions are exact
                self.complete_position_reset()
                self.goal_animation_active = False
                self.animation_phase = 0
                self.camera_zoom = 1.0
                self.camera_center_x = SCREEN_WIDTH // 2
                self.camera_center_y = SCREEN_HEIGHT // 2
                # Reset pause timing for next animation
                self.total_pause_duration = 0
                self.pause_start_time = 0
    
    def update_position_reset_animation(self, t):
        """Smoothly animate all objects from goal-moment positions to kickoff positions with physics disabled"""
        # Use ease-in-out for smoother reset animation  
        eased_t = self.ease_in_out_cubic(t)
        
        # Animate players from goal-moment positions to kickoff positions
        all_players = self.team1_players + self.team2_players
        for i, player in enumerate(all_players):
            if i < len(self.goal_moment_player_positions) and i < len(self.target_player_positions):
                # Start position: where player was when goal was scored
                start_x, start_y = self.goal_moment_player_positions[i]
                # Target position: where player should end up (kickoff position)
                target_x, target_y = self.target_player_positions[i]
                
                # Interpolate from goal-moment position to kickoff position
                current_x = start_x + (target_x - start_x) * eased_t
                current_y = start_y + (target_y - start_y) * eased_t
                
                # Set position directly (physics disabled)
                player.x = current_x
                player.y = current_y
                # Stop all movement during animation
                player.vx = 0
                player.vy = 0
        
        # Animate ball from goal-moment position to kickoff position
        start_ball_x, start_ball_y = self.goal_moment_ball_position
        target_ball_x, target_ball_y = self.target_ball_position
        
        current_ball_x = start_ball_x + (target_ball_x - start_ball_x) * eased_t
        current_ball_y = start_ball_y + (target_ball_y - start_ball_y) * eased_t
        
        # Set ball position directly (physics disabled)
        self.ball.x = current_ball_x
        self.ball.y = current_ball_y
        # Stop all ball movement during animation
        self.ball.vx = 0
        self.ball.vy = 0
    
    def complete_position_reset(self):
        """Ensure exact final positions after animation completes"""
        # Set all players to exact kickoff positions
        all_players = self.team1_players + self.team2_players
        for i, player in enumerate(all_players):
            if i < len(self.target_player_positions):
                target_x, target_y = self.target_player_positions[i]
                player.set_position(target_x, target_y)
                player.vx = 0
                player.vy = 0
        
        # Set ball to exact kickoff position
        target_ball_x, target_ball_y = self.target_ball_position
        self.ball.set_position(target_ball_x, target_ball_y)
        self.ball.set_velocity(0, 0)
        self.ball.moving = False
    
    def get_camera_transform(self):
        """Get the camera transformation parameters for rendering"""
        if not self.goal_animation_active:
            return 1.0, 0, 0  # No transformation
        
        # Calculate screen center for usable area (excluding scoreboard)
        usable_height = SCREEN_HEIGHT - SCOREBOARD_HEIGHT
        screen_center_x = SCREEN_WIDTH // 2
        screen_center_y = SCOREBOARD_HEIGHT + usable_height // 2  # Center of usable area
        
        # Apply boundary constraints to keep camera within playground
        constrained_center_x, constrained_center_y = self.constrain_camera_to_playground(
            self.camera_center_x, self.camera_center_y, self.camera_zoom
        )
        
        # Calculate offset to center the camera on the constrained target
        offset_x = screen_center_x - constrained_center_x * self.camera_zoom
        offset_y = screen_center_y - constrained_center_y * self.camera_zoom
        
        return self.camera_zoom, offset_x, offset_y
    
    def get_speed_multiplier(self):
        """Get the current speed multiplier for physics calculations"""
        if self.goal_animation_active:
            return GOAL_ZOOM_SLOW_MOTION_SPEED
        return 1.0
    
    def constrain_camera_to_playground(self, center_x, center_y, zoom):
        """Constrain camera center to keep the view within playground boundaries"""
        # Calculate the visible area size at current zoom (using usable area)
        usable_height = SCREEN_HEIGHT - SCOREBOARD_HEIGHT
        visible_width = SCREEN_WIDTH / zoom
        visible_height = usable_height / zoom
        
        # Define playground boundaries (field + some padding for goals)
        playground_left = FIELD_X - GOAL_DEPTH
        playground_right = FIELD_X + FIELD_WIDTH + GOAL_DEPTH
        playground_top = FIELD_Y
        playground_bottom = FIELD_Y + FIELD_HEIGHT
        
        # Calculate constraints for camera center to keep view within playground
        min_center_x = playground_left + visible_width / 2
        max_center_x = playground_right - visible_width / 2
        min_center_y = playground_top + visible_height / 2
        max_center_y = playground_bottom - visible_height / 2
        
        # Handle cases where playground is smaller than visible area
        if min_center_x > max_center_x:
            # Playground width is smaller than visible width, center horizontally
            constrained_x = (playground_left + playground_right) / 2
        else:
            # Normal case: clamp camera center within bounds
            constrained_x = max(min_center_x, min(max_center_x, center_x))
        
        if min_center_y > max_center_y:
            # Playground height is smaller than visible height, center vertically
            constrained_y = (playground_top + playground_bottom) / 2
        else:
            # Normal case: clamp camera center within bounds
            constrained_y = max(min_center_y, min(max_center_y, center_y))
        
        return constrained_x, constrained_y
        
    def init_players(self):
        """Initialize all players for both teams using current tactics"""
        # Get positions from tactics manager
        team1_tactic = self.tactics_manager.get_team_tactic(1)
        team2_tactic = self.tactics_manager.get_team_tactic(2)
        team1_positions = self.tactics_manager.get_tactic_positions(team1_tactic, 1)
        team2_positions = self.tactics_manager.get_tactic_positions(team2_tactic, 2)
        
        # Clear existing players
        self.team1_players.clear()
        self.team2_players.clear()
        
        # Team 1 players
        for i, pos in enumerate(team1_positions):
            player = Player(FIELD_X + pos[0], FIELD_Y + pos[1], 1, i)
            self.team1_players.append(player)
        
        # Team 2 players
        for i, pos in enumerate(team2_positions):
            player = Player(FIELD_X + pos[0], FIELD_Y + pos[1], 2, i)
            self.team2_players.append(player)
    
    def get_current_team_players(self):
        """Get players for the current team"""
        return self.team1_players if self.current_team == 1 else self.team2_players
    
    def get_current_player(self):
        """Get the currently selected player"""
        players = self.get_current_team_players()
        if 0 <= self.current_player_index < len(players):
            return players[self.current_player_index]
        return None
    
    def select_player(self, player_index):
        """Select a player for the current team"""
        players = self.get_current_team_players()
        
        # Deselect all players
        for player in self.team1_players + self.team2_players:
            player.selected = False
        
        # Select new player if valid
        if 0 <= player_index < len(players) and players[player_index].can_move:
            self.current_player_index = player_index
            players[player_index].selected = True
            # Default aim toward the ball for immediate visual cue
            dx = self.ball.x - players[player_index].x
            dy = self.ball.y - players[player_index].y
            if dx != 0 or dy != 0:
                players[player_index].set_aim_direction_instant(dx, dy)
            # On switching player, always return to aim phase and reset force meter state
            self.current_phase = PHASE_AIM_DIRECTION
            self._aim_seeded = True  # seeded toward ball
            self.force_meter_active = False
            self.force_power = MIN_FORCE
            self.force_increasing = True
            return True
        return False
    
    def update_aim_direction(self, dx, dy):
        """Update the aiming direction for current player"""
        if self.current_phase != PHASE_AIM_DIRECTION:
            return
        
        current_player = self.get_current_player()
        if current_player and current_player.can_move:
            current_player.set_aim_direction(dx, dy)
    
    def confirm_aim_direction(self):
        """Confirm aim direction and move to force selection"""
        if self.current_phase != PHASE_AIM_DIRECTION:
            return
        
        self.current_phase = PHASE_SELECT_FORCE
        self.force_meter_active = True
        self.force_power = MIN_FORCE
        self.force_increasing = True  # start building up from minimum on every entry
    
    def execute_player_movement(self):
        """Execute player movement with current force and direction"""
        if self.current_phase != PHASE_SELECT_FORCE:
            return
        
        current_player = self.get_current_player()
        if not current_player:
            return
        
        # Safety: ensure only the selected player moves this turn initially
        for p in self.get_current_team_players():
            if p is not current_player:
                p.vx = 0
                p.vy = 0
                p.moving = False
        
        # Start player movement
        current_player.start_movement(self.force_power)
        
        # End turn setup
        self.force_meter_active = False
        self.current_phase = PHASE_PLAYER_MOVING
        current_player.end_turn()
    
    def update_force_meter(self):
        """Update the force meter animation"""
        if not self.force_meter_active:
            return
        
        if self.force_increasing:
            self.force_power += 5
            if self.force_power >= MAX_FORCE:
                self.force_power = MAX_FORCE
                self.force_increasing = False
        else:
            self.force_power -= 5
            if self.force_power <= MIN_FORCE:
                self.force_power = MIN_FORCE
                self.force_increasing = True
    
    def kick_ball(self):
        """Kick the ball if player is close enough"""
        current_player = self.get_current_player()
        if not current_player:
            return
        
        # Check if player is close enough to ball
        distance_to_ball = current_player.distance_to(self.ball.x, self.ball.y)
        if distance_to_ball <= (current_player.radius + self.ball.radius + 10):
            # Calculate kick angle (from player to ball)
            dx = self.ball.x - current_player.x
            dy = self.ball.y - current_player.y
            if dx != 0 or dy != 0:
                angle = math.atan2(dy, dx)
                # Apply force to ball with reduced multiplier, pass player ID for immunity
                self.ball.kick(self.force_power * 0.05, angle, id(current_player))
                self.current_phase = PHASE_BALL_MOVING
        
        self.force_meter_active = False

    def _cleanup_collision_tracking(self, all_players):
        """Remove collision pairs that are no longer touching to allow sound to play again"""
        import math
        
        # Check all active collision pairs
        pairs_to_remove = []
        for pair_id in self.active_collisions:
            obj1_id, obj2_id = pair_id
            
            # Find the objects by their IDs
            obj1, obj2 = None, None
            
            # Check if one is the ball
            if id(self.ball) == obj1_id:
                obj1 = self.ball
            elif id(self.ball) == obj2_id:
                obj2 = self.ball
            
            # Find in players
            for p in all_players:
                if id(p) == obj1_id:
                    obj1 = p
                elif id(p) == obj2_id:
                    obj2 = p
            
            # If we found both objects, check if they're still touching
            if obj1 and obj2:
                dx = obj2.x - obj1.x
                dy = obj2.y - obj1.y
                distance_sq = dx * dx + dy * dy
                min_distance = obj1.radius + obj2.radius
                
                # Add small buffer (10% extra) before removing from active collisions
                if distance_sq > (min_distance * 1.1) ** 2:
                    pairs_to_remove.append(pair_id)
            else:
                # One of the objects doesn't exist anymore, remove the pair
                pairs_to_remove.append(pair_id)
        
        # Remove the pairs that are no longer colliding
        for pair_id in pairs_to_remove:
            self.active_collisions.discard(pair_id)
    
    def update(self):
        """Update game state"""
        # Audio automatic saving (debounced)
        if self._audio_save_timer > 0 and pygame.time.get_ticks() >= self._audio_save_timer:
            self.save_audio_configuration()
            self._audio_save_timer = 0
            
        # CRITICAL: No game logic should run during pause
        if self.game_state == GAME_STATE_PAUSED:
            return
            
        # CRITICAL: No game logic should run during game over
        if self.game_state == GAME_STATE_GAME_OVER:
            return
            
        if self.game_state == GAME_STATE_MENU:
            return
        elif self.game_state == GAME_STATE_TACTICS:
            return
        elif self.game_state == GAME_STATE_CUSTOM_TACTICS:
            return
        elif self.game_state == GAME_STATE_COIN_FLIP:
            self.update_coin_flip()
            return
            
        # Update goal animation if active (only when not paused)
        self.update_goal_animation()
        
        # Block all other operations during goal animation
        if self.goal_animation_active:
            return
            
        # Handle transient goal banner pause
        if self.goal_banner_until:
            # Don't update banner timing during pause - freeze the banner
            if self.game_state != GAME_STATE_PAUSED:
                if pygame.time.get_ticks() >= self.goal_banner_until:
                    self.goal_banner_until = 0
                    # After banner, resume normal play
                else:
                    return
            else:
                # During pause, keep the banner frozen
                return

        if self.game_state != GAME_STATE_PLAYING:
            return
        
        # Update bot tracking systems (when playing)
        if self.singleplayer:
            self._update_bot_tracking()
        
        # Seed aim arrow once toward the current ball for both human and bot turns
        if self.current_phase == PHASE_AIM_DIRECTION and not self._aim_seeded:
            current_player = self.get_current_player()
            if current_player:
                dx = self.ball.x - current_player.x
                dy = self.ball.y - current_player.y
                if dx != 0 or dy != 0:
                    current_player.set_aim_direction_instant(dx, dy)
                self._aim_seeded = True

        # Handle continuous aim input for human teams
        if self.current_phase == PHASE_AIM_DIRECTION and not self._is_bot_turn():
            current_player = self.get_current_player()
            if current_player:
                keys = pygame.key.get_pressed()
                # In singleplayer, always use P1 controls for the human regardless of team
                if self.singleplayer:
                    controls = P1_CONTROLS
                else:
                    controls = P1_CONTROLS if self.current_team == 1 else P2_CONTROLS
                current_player.update_aim_continuous(keys, controls)

        # Bot decision-making
        if self.singleplayer and self._is_bot_turn():
            self._update_bot()
        
        # Update all players (but skip physics during reset animation)
        all_players = self.team1_players + self.team2_players
        speed_multiplier = self.get_speed_multiplier()
        
        # Disable physics during position reset animation
        if not (self.goal_animation_active and self.animation_phase == 3):
            for player in all_players:
                player.update(speed_multiplier)
                # Ensure players stay within field boundaries (safety net)
                player.x = max(FIELD_X + player.radius, min(FIELD_X + FIELD_WIDTH - player.radius, player.x))
                player.y = max(FIELD_Y + player.radius, min(FIELD_Y + FIELD_HEIGHT - player.radius, player.y))
        
            # Iterative collision resolution: players <-> players
            # Pre-calculate collision pairs for spatial optimization
            collision_pairs = []
            for i, p1 in enumerate(all_players):
                for p2 in all_players[i+1:]:
                    # Skip distant players (early exit optimization)
                    max_collision_dist = (p1.radius + p2.radius) * 2
                    dx = p1.x - p2.x
                    dy = p1.y - p2.y
                    if dx*dx + dy*dy <= max_collision_dist*max_collision_dist:
                        collision_pairs.append((p1, p2))
            
            for _ in range(PHYSICS_SOLVER_ITERATIONS):
                for p1, p2 in collision_pairs:
                    if resolve_circle_circle(p1, p2):
                        # Efficient collision tracking with size limit
                        pair_id = (min(id(p1), id(p2)), max(id(p1), id(p2)))
                        if len(self.active_collisions) < 20:  # Limit collision tracking
                            if pair_id not in self.active_collisions:
                                self.active_collisions.add(pair_id)
                                self.sounds.play_collision()
        
            # Update ball physics FIRST (with boundary checking)
            self.ball.update(speed_multiplier)

            # Iterative collision resolution: ball <-> players (with multiple passes)
            # Pre-filter players within reasonable distance of ball
            nearby_players = []
            max_ball_collision_dist = (self.ball.radius + PLAYER_RADIUS) * 3  # Increased safety margin
            for p in all_players:
                dx = self.ball.x - p.x
                dy = self.ball.y - p.y
                if dx*dx + dy*dy <= max_ball_collision_dist*max_ball_collision_dist:
                    nearby_players.append(p)
            
            # Increased iterations for ball-player collisions to prevent noclipping
            for iteration in range(PHYSICS_SOLVER_ITERATIONS * 2):  # Double iterations for ball
                collision_resolved = False
                for p in nearby_players:
                    # Skip collision resolution if ball has kick immunity against this player
                    if self.ball.has_kick_immunity(id(p)):
                        continue
                        
                    if resolve_circle_circle(self.ball, p):
                        collision_resolved = True
                        # Optimized collision tracking with size limit
                        if len(self.active_collisions) < 20:  # Limit collision tracking for memory
                            pair_id = (id(self.ball), id(p))
                            if pair_id not in self.active_collisions:
                                self.active_collisions.add(pair_id)
                                self.sounds.play_collision()
                        
                        # Additional safety: ensure ball doesn't clip through player
                        dx = self.ball.x - p.x
                        dy = self.ball.y - p.y
                        dist = math.sqrt(dx*dx + dy*dy)
                        min_dist = self.ball.radius + p.radius
                        
                        if dist < min_dist and dist > 0:
                            # Force minimum separation
                            overlap = min_dist - dist
                            nx = dx / dist
                            ny = dy / dist
                            # Move ball away from player
                            self.ball.x += nx * overlap * 0.6  # Ball takes more correction
                            p.x -= nx * overlap * 0.4  # Player takes less correction
                            self.ball.y += ny * overlap * 0.6
                            p.y -= ny * overlap * 0.4
                
                # If no collisions in this iteration, we can break early
                if not collision_resolved:
                    break
        
            # Clean up collision tracking - remove pairs that are no longer colliding
            self._cleanup_collision_tracking(all_players)
        
        # Removed per-frame corner-stuck handoff to prevent infinite team flipping.

        # Check for goals
        goal_team = self.ball.check_goal()
        if goal_team > 0:
            self.score_goal(goal_team)
        
        # Update force meter
        if self.force_meter_active:
            self.update_force_meter()
        
        # Check if player stopped moving
        if self.current_phase == PHASE_PLAYER_MOVING:
            current_player = self.get_current_player()
            if current_player and not current_player.moving:
                # Try to kick ball if close enough
                self.kick_ball()
                if self.current_phase != PHASE_BALL_MOVING:
                    self.end_current_turn()
        
        # Check if ball stopped moving
        elif self.current_phase == PHASE_BALL_MOVING and not self.ball.moving:
            self.end_current_turn()
    
    def score_goal(self, scoring_team):
        """Handle goal scoring - reset turn and give possession to the team that lost the goal"""
        # Start the zoom animation first, centered on ball's current position
        self.start_goal_animation(self.ball.x, self.ball.y)
        
        # Play sound first
        self.sounds.play_goal()
        if scoring_team == 1:
            self.team1_score += 1
        else:
            self.team2_score += 1
        
        # Calculate kickoff ball position and store as target (don't move yet - animation will handle it)
        conceding_team = 2 if scoring_team == 1 else 1
        center_x = FIELD_X + FIELD_WIDTH // 2
        center_y = FIELD_Y + FIELD_HEIGHT // 2
        if conceding_team == 1:
            kickoff_x = center_x - KICKOFF_OFFSET
        else:
            kickoff_x = center_x + KICKOFF_OFFSET
        
        # Store target ball position for animation (don't set immediately)
        self.target_ball_position = (kickoff_x, center_y)
        
        # DON'T reset player positions immediately - let animation handle it
        # Players will be moved by the reset animation from goal-moment to kickoff positions
        
        # Reset player states (but not positions)
        for player in self.team1_players + self.team2_players:
            player.reset_turn()  # All players can move again
            player.vx = 0  # Stop movement
            player.vy = 0
        
        # Reset ball state (but not position)
        self.ball.set_velocity(0, 0)
        self.ball.moving = False

        # Goal scored: reorder queue so conceding team goes first, reset turn iteration
        conceding_team = 2 if scoring_team == 1 else 1
        
        # Reorder queue: conceding team first, then other team
        self.turn_queue = [conceding_team, 3 - conceding_team]  # 3-team gives other team
        self.queue_index = 0
        self.teams_played_this_turn.clear()  # Reset iteration - no one has played yet
        
        # Set current team to first in queue (conceding team)
        self.current_team = self.turn_queue[self.queue_index]
        self.current_player_index = 0
        self.current_phase = PHASE_SELECT_PLAYER
        self._aim_seeded = False
        self.force_meter_active = False

        # Show goal banner for a short time
        self.goal_banner_until = pygame.time.get_ticks() + GOAL_BANNER_MS
        
        # Check for game end based on configured game mode
        goal_limit_reached = (self.team1_score >= self.max_goals or self.team2_score >= self.max_goals)
        
        if self.game_mode == 'goals_only' and goal_limit_reached:
            self.game_state = GAME_STATE_GAME_OVER
            # Stop any ongoing animations when game ends, but keep the winning goal banner
            self.goal_animation_active = False
            # Don't clear goal_banner_until - let the winning goal banner show
            self.force_meter_active = False
            self.update_music()
        elif self.game_mode == 'both' and goal_limit_reached:
            self.game_state = GAME_STATE_GAME_OVER
            # Stop any ongoing animations when game ends, but keep the winning goal banner
            self.goal_animation_active = False
            # Don't clear goal_banner_until - let the winning goal banner show
            self.force_meter_active = False
            self.update_music()
    
    def end_current_turn(self):
        """End the current team's turn and advance in the queue"""
        current_player = self.get_current_player()
        if current_player:
            current_player.end_turn()
        
        # Mark current team as having played this turn
        self.teams_played_this_turn.add(self.current_team)
        
        # Move to next team in queue
        self.queue_index += 1
        
        # Check if queue is fully iterated (all teams have played)
        if self.queue_index >= len(self.turn_queue):
            # Queue complete - increment turn counter and reset
            self.turn_number += 1
            self.queue_index = 0
            self.teams_played_this_turn.clear()
            
            # Check for game end based on configured game mode
            turn_limit_reached = self.turn_number > self.max_turns
            
            if self.game_mode == 'turns_only' and turn_limit_reached:
                self.game_state = GAME_STATE_GAME_OVER
                # Stop any ongoing animations when game ends
                self.goal_animation_active = False
                # Don't clear goal_banner_until - preserve any active banner
                self.force_meter_active = False
                self.update_music()
                return
            elif self.game_mode == 'both' and turn_limit_reached:
                self.game_state = GAME_STATE_GAME_OVER
                # Stop any ongoing animations when game ends
                self.goal_animation_active = False
                # Don't clear goal_banner_until - preserve any active banner
                self.force_meter_active = False
                self.update_music()
                return
        
        # Set next team from queue
        self.current_team = self.turn_queue[self.queue_index]
        self.current_player_index = 0
        self.current_phase = PHASE_SELECT_PLAYER
        self._aim_seeded = False
        self.force_meter_active = False

        # Reset availability for the team that is about to play
        incoming_team_players = self.team1_players if self.current_team == 1 else self.team2_players
        for player in incoming_team_players:
            player.reset_turn()

        # Corner-stuck normal unstucking removed; magnetic corner repulsion handles this now.
    
    def handle_keypress(self, key):
        """Handle keyboard input"""
        if self.game_state == GAME_STATE_MENU:
            self.handle_menu_keypress(key)
            return
        elif self.game_state == GAME_STATE_AUDIO:
            self.handle_audio_menu_keypress(key)
            return
        elif self.game_state == GAME_STATE_TACTICS:
            self.handle_tactics_keypress(key)
            return
        elif self.game_state == GAME_STATE_CUSTOM_TACTICS:
            self.handle_custom_tactics_keypress(key)
            return
        elif self.game_state == GAME_STATE_COIN_FLIP:
            # Skip coin flip animation or result display
            if self.coin_flip_active:
                self.complete_coin_flip()
            elif self.coin_flip_winner_determined:
                self._actually_start_game()
            return
        elif self.game_state == GAME_STATE_GAME_OVER:
            # Handle game over state - only allow specific keys
            if key == pygame.K_m:  # M key to return to menu with preserved config
                self.return_to_menu_with_config()
            return
        
        if self.game_state != GAME_STATE_PLAYING:
            return
        
        # Ignore human input during bot's turn in singleplayer
        if self.singleplayer and self._is_bot_turn():
            return

        # In singleplayer, always map the human player's input to P1 controls,
        # even when the human is playing as Team 2. In multiplayer, keep team-based mapping.
        if self.singleplayer:
            controls = P1_CONTROLS
        else:
            controls = P1_CONTROLS if self.current_team == 1 else P2_CONTROLS
        
        # Player selection (allowed during select, aim, and force phases)
        if self.current_phase in (PHASE_SELECT_PLAYER, PHASE_AIM_DIRECTION, PHASE_SELECT_FORCE):
            for i, select_key in enumerate(controls['select_players']):
                if key == select_key:
                    # select_player() already handles returning to aim and resetting force meter
                    self.select_player(i)
                    break
        
        # Aim direction - now only handles action key, direction is continuous
        if self.current_phase == PHASE_AIM_DIRECTION:
            if key == controls['action']:
                self.confirm_aim_direction()
        
        # Force selection
        elif self.current_phase == PHASE_SELECT_FORCE:
            if key == controls['action']:
                self.execute_player_movement()

    def _can_repeat_key(self, key_type='navigation'):
        """Check if enough time has passed since last key repeat for smooth but not spammy navigation"""
        current_time = pygame.time.get_ticks()
        if key_type == 'navigation':
            return current_time - self._last_navigation_time >= self._key_repeat_delay
        elif key_type == 'value_change':
            return current_time - self._last_value_change_time >= self._fast_key_repeat_delay
        return True
    
    def _update_key_repeat_time(self, key_type='navigation'):
        """Update the last key repeat time for the specified key type"""
        current_time = pygame.time.get_ticks()
        if key_type == 'navigation':
            self._last_navigation_time = current_time
        elif key_type == 'value_change':
            self._last_value_change_time = current_time

    def handle_menu_keypress(self, key):
        # Navigate with key repeat delay
        if key in (pygame.K_UP, pygame.K_w):
            if self._can_repeat_key('navigation'):
                self._menu_index = self._prev_enabled_index(self._menu_index)
                self._update_key_repeat_time('navigation')
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            if self._can_repeat_key('navigation'):
                self._menu_index = self._next_enabled_index(self._menu_index)
                self._update_key_repeat_time('navigation')
            return

        # Adjust values for current selection with faster key repeat delay
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
            if not self._can_repeat_key('value_change'):
                return  # Too soon, ignore this key press
            
            self._update_key_repeat_time('value_change')
            
            if self._menu_index == 0:  # Mode
                self.singleplayer = not self.singleplayer
                return
            elif self._menu_index == 1 and self.singleplayer:  # Bot Team
                self.bot_team = 1 if self.bot_team == 2 else 2
                return
            elif self._menu_index == 2 and self.singleplayer:  # Difficulty
                order = ["easy", "medium", "hard", "insane", "extreme"]
                idx = order.index(self.bot_difficulty) if self.bot_difficulty in order else 1
                if key in (pygame.K_LEFT, pygame.K_a):
                    idx = (idx - 1) % len(order)
                else:
                    idx = (idx + 1) % len(order)
                self.bot_difficulty = order[idx]
                # Adjust bot think time according to difficulty
                self._bot_action_cooldown_ms = BOT_THINK_MS.get(self.bot_difficulty, self._bot_action_cooldown_ms)
                return
            elif self._menu_index == 3:  # Game Mode
                modes = ["goals_only", "turns_only", "both"]
                idx = modes.index(self.game_mode) if self.game_mode in modes else 0
                if key in (pygame.K_LEFT, pygame.K_a):
                    idx = (idx - 1) % len(modes)
                else:
                    idx = (idx + 1) % len(modes)
                self.game_mode = modes[idx]
                return
            elif self._menu_index == 4 and self.game_mode in ['goals_only', 'both']:  # Goal Limit
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.max_goals = max(1, self.max_goals - 1)
                else:
                    self.max_goals = min(50, self.max_goals + 1)
                return
            elif self._menu_index == 5 and self.game_mode in ['turns_only', 'both']:  # Turn Limit
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.max_turns_limit = max(10, self.max_turns_limit - 10)
                else:
                    self.max_turns_limit = min(200, self.max_turns_limit + 10)
                # Update the current max_turns as well
                self.max_turns = self.max_turns_limit
                return

        # Handle Enter/Space - start game or enter audio settings
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._menu_index == 6:  # Audio Settings
                self.game_state = GAME_STATE_AUDIO
                self.update_music()
                return
            else:
                # Go to tactics selection instead of directly to playing
                self.game_state = GAME_STATE_TACTICS
                self.update_music()
                self._start_tactics_selection()
                return

    def handle_audio_menu_keypress(self, key):
        """Handle keyboard input for audio settings menu"""
        # ESC key to return to main menu
        if key == pygame.K_ESCAPE:
            self.game_state = GAME_STATE_MENU
            self.update_music()
            return

        # Navigate with key repeat delay
        if key in (pygame.K_UP, pygame.K_w):
            if self._can_repeat_key('navigation'):
                self._audio_menu_index = self._prev_audio_enabled_index(self._audio_menu_index)
                self._update_key_repeat_time('navigation')
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            if self._can_repeat_key('navigation'):
                self._audio_menu_index = self._next_audio_enabled_index(self._audio_menu_index)
                self._update_key_repeat_time('navigation')
            return

        # Adjust values for current selection with faster key repeat delay
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
            if not self._can_repeat_key('value_change'):
                return  # Too soon, ignore this key press
            
            self._update_key_repeat_time('value_change')
            
            if self._audio_menu_index == 0:  # Master Volume
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.master_volume = max(0.0, self.master_volume - 0.01)
                else:
                    self.master_volume = min(1.0, self.master_volume + 0.01)
                self.sync_volume_settings()
                return
            elif self._audio_menu_index == 1:  # SFX Volume
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.sfx_volume = max(0.0, self.sfx_volume - 0.01)
                else:
                    self.sfx_volume = min(1.0, self.sfx_volume + 0.01)
                self.sync_volume_settings()
                return
            elif self._audio_menu_index == 2:  # BGM Volume
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.bgm_volume = max(0.0, self.bgm_volume - 0.01)
                else:
                    self.bgm_volume = min(1.0, self.bgm_volume + 0.01)
                self.sync_volume_settings()
                return

        # Note: No Enter/Space handling needed since we removed Return to Main Menu option
        # ESC key is the only way to return to main menu

    def _next_audio_enabled_index(self, current: int) -> int:
        n = len(self._audio_menu_items)
        for step in range(1, n + 1):
            cand = (current + step) % n
            return cand  # All audio menu items are always enabled
        return current

    def _prev_audio_enabled_index(self, current: int) -> int:
        n = len(self._audio_menu_items)
        for step in range(1, n + 1):
            cand = (current - step) % n
            return cand  # All audio menu items are always enabled
        return current

    def _menu_item_enabled(self, idx: int) -> bool:
        # idx: 0 Mode, 1 Bot Team, 2 Difficulty, 3 Game Mode, 4 Goal Limit, 5 Turn Limit, 6 Audio Settings
        if idx == 0:  # Mode
            return True
        elif idx in (1, 2):  # Bot Team, Difficulty
            return self.singleplayer
        elif idx == 3:  # Game Mode
            return True
        elif idx == 4:  # Goal Limit
            return self.game_mode in ['goals_only', 'both']
        elif idx == 5:  # Turn Limit
            return self.game_mode in ['turns_only', 'both']
        elif idx == 6:  # Audio Settings
            return True
        return True

    def _next_enabled_index(self, current: int) -> int:
        n = len(self._menu_items)
        for step in range(1, n + 1):
            cand = (current + step) % n
            if self._menu_item_enabled(cand):
                return cand
        return current

    def _prev_enabled_index(self, current: int) -> int:
        n = len(self._menu_items)
        for step in range(1, n + 1):
            cand = (current - step) % n
            if self._menu_item_enabled(cand):
                return cand
        return current
    
    def _start_tactics_selection(self):
        """Start the tactics selection phase"""
        self._tactics_phase = 'select'
        self._tactics_team = 1
        self._tactics_index = 0
        self._available_tactics = self.tactics_manager.get_available_tactics()
        
        # Perform tactics validation on first access
        if not self._validation_performed:
            self._validate_all_tactics()
            self._validation_performed = True
        
        # Bot auto-selects tactics if it's their turn
        if self.singleplayer and self.bot_team == 1:
            # Bot goes first, so pick a random tactic (human will choose after)
            tactic_key = self.tactics_manager.select_bot_tactic()
            self.tactics_manager.set_team_tactic(1, tactic_key)
            self._tactics_team = 2  # Move to human's turn
            self._tactics_team = 2  # Move to next team
    
    def _validate_all_tactics(self):
        """Validate all tactics and handle invalid ones.
        
        This method will:
        1. Check all tactics for validation issues
        2. Remove invalid custom tactics that can't be fixed
        """
        invalid_tactics = self.tactics_manager.validate_all_tactics()
        
        if invalid_tactics:
            # Remove invalid custom tactics
            removed_count = self.tactics_manager.remove_invalid_custom_tactics(invalid_tactics)
            
            # Update available tactics list
            self._available_tactics = self.tactics_manager.get_available_tactics()
            
            # Store invalid tactics for dialog display
            self._invalid_tactics_list = invalid_tactics
            self._show_invalid_tactics_dialog = True
    

    
    def handle_tactics_keypress(self, key):
        """Handle keyboard input during tactics selection"""
        if self._tactics_phase == 'select':
            self.handle_tactics_selection_keypress(key)
    
    def handle_tactics_selection_keypress(self, key):
        """Handle tactics selection navigation"""
        # Check for invalid tactics dialog
        if self._show_invalid_tactics_dialog:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                # Dismiss dialog
                self._show_invalid_tactics_dialog = False
                self._invalid_tactics_list = []
            return
        
        # Check for reset all confirmation dialog
        if self._show_reset_all_confirmation:
            if key == pygame.K_y:
                # Confirm reset all
                self.tactics_manager.reset_all_custom_tactics()
                self._available_tactics = self.tactics_manager.get_available_tactics()
                self._show_reset_all_confirmation = False
                # Reset selection to first item
                self._tactics_index = 0
            elif key == pygame.K_n or key == pygame.K_ESCAPE:
                # Cancel reset
                self._show_reset_all_confirmation = False
            return

        # Check for delete confirmation dialog
        if self._show_delete_confirmation:
            if key == pygame.K_y:
                # Confirm delete
                if hasattr(self, '_delete_tactic_key'):
                    self.tactics_manager.delete_custom_tactic(self._delete_tactic_key)
                    self._available_tactics = self.tactics_manager.get_available_tactics()
                    # Keep selection index but ensure it's valid
                    if self._tactics_index >= len(self._available_tactics):
                        self._tactics_index = len(self._available_tactics) - 1
                self._show_delete_confirmation = False
                if hasattr(self, '_delete_tactic_key'):
                    delattr(self, '_delete_tactic_key')
            elif key == pygame.K_n or key == pygame.K_ESCAPE:
                # Cancel delete
                self._show_delete_confirmation = False
                if hasattr(self, '_delete_tactic_key'):
                    delattr(self, '_delete_tactic_key')
            return
        
        # Grid navigation (5x2 layout) with key repeat delay
        if key in (pygame.K_UP, pygame.K_w):
            if self._can_repeat_key('navigation'):
                self._tactics_index = self._get_grid_navigation(self._tactics_index, 'up')
                self._update_key_repeat_time('navigation')
        elif key in (pygame.K_DOWN, pygame.K_s):
            if self._can_repeat_key('navigation'):
                self._tactics_index = self._get_grid_navigation(self._tactics_index, 'down')
                self._update_key_repeat_time('navigation')
        elif key in (pygame.K_LEFT, pygame.K_a):
            if self._can_repeat_key('navigation'):
                self._tactics_index = self._get_grid_navigation(self._tactics_index, 'left')
                self._update_key_repeat_time('navigation')
        elif key in (pygame.K_RIGHT, pygame.K_d):
            if self._can_repeat_key('navigation'):
                self._tactics_index = self._get_grid_navigation(self._tactics_index, 'right')
                self._update_key_repeat_time('navigation')
        
        # Selection
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if 0 <= self._tactics_index < len(self._available_tactics):
                selected_tactic = self._available_tactics[self._tactics_index]
                
                if selected_tactic['type'] == 'empty_custom':
                    # Start custom tactics editor
                    self.custom_tactics_editor.start_editing(selected_tactic['key'])
                    self.game_state = GAME_STATE_CUSTOM_TACTICS
                else:
                    # Select this tactic for current team
                    self.tactics_manager.set_team_tactic(self._tactics_team, selected_tactic['key'])
                    self._advance_tactics_selection()
        
        # Customize custom tactics
        elif key == pygame.K_c:
            if 0 <= self._tactics_index < len(self._available_tactics):
                selected_tactic = self._available_tactics[self._tactics_index]
                
                # Only allow customizing custom tactics (not empty ones)
                if selected_tactic['type'] == 'custom':
                    self.custom_tactics_editor.start_editing(selected_tactic['key'])
                    self.game_state = GAME_STATE_CUSTOM_TACTICS
                    self.update_music()
        
        # Reset all custom tactics
        elif key == pygame.K_r:
            self._show_reset_all_confirmation = True
        
        # Delete current custom tactic
        elif key == pygame.K_x:
            if 0 <= self._tactics_index < len(self._available_tactics):
                selected_tactic = self._available_tactics[self._tactics_index]
                
                # Only allow deleting non-empty custom tactics
                if selected_tactic['type'] == 'custom':
                    self._delete_tactic_key = selected_tactic['key']
                    self._show_delete_confirmation = True
        
        # Back to menu
        elif key == pygame.K_ESCAPE:
            self.game_state = GAME_STATE_MENU
            self.update_music()
    
    def _get_grid_navigation(self, current_index, direction):
        """Calculate new index for 2x5 grid navigation with ring wrapping"""
        if not self._available_tactics:
            return 0
        
        total_items = len(self._available_tactics)
        rows = 5
        cols = 2
        
        # Convert index to grid coordinates (row, col)
        row = current_index // cols
        col = current_index % cols
        
        if direction == 'up':
            row = (row - 1) % rows  # Ring wrap vertically
        elif direction == 'down':
            row = (row + 1) % rows  # Ring wrap vertically
        elif direction == 'left':
            col = (col - 1) % cols  # Ring wrap horizontally
        elif direction == 'right':
            col = (col + 1) % cols  # Ring wrap horizontally
        
        # Convert back to index
        new_index = row * cols + col
        
        # Ensure the new index is within bounds
        if new_index >= total_items:
            # If we're past the end, wrap to the beginning of the same row
            new_index = row * cols
            if new_index >= total_items:
                # If even that's too much, go to the last valid index
                new_index = total_items - 1
        
        return new_index
    
    def _advance_tactics_selection(self):
        """Advance to next team or start game"""
        if self._tactics_team == 1:
            # Move to team 2
            self._tactics_team = 2
            self._tactics_index = 0
            
            # Bot auto-selects if it's team 2 (ensure different from human choice)
            if self.singleplayer and self.bot_team == 2:
                # Select bot tactic while avoiding human's choice for variety
                bot_tactic = self.tactics_manager.select_bot_tactic(opponent_team_number=1)
                self.tactics_manager.set_team_tactic(2, bot_tactic)
                self._start_game()
        else:
            # Both teams selected, start game
            self._start_game()
    
    def _start_game(self):
        """Start the coin flip to determine which team goes first"""
        # Start coin flip animation
        self.start_coin_flip()
    
    def handle_custom_tactics_keypress(self, key):
        """Handle keyboard input during custom tactics editing"""
        if self._show_save_confirmation:
            # Handle save confirmation dialog
            if key == pygame.K_y:
                # Yes, save the tactic
                if self.custom_tactics_editor.save_tactic():
                    self._show_save_confirmation = False
                    self.game_state = GAME_STATE_TACTICS
                    self._available_tactics = self.tactics_manager.get_available_tactics()
            elif key == pygame.K_n or key == pygame.K_ESCAPE:
                # No, don't save / Cancel
                self._show_save_confirmation = False
                self.game_state = GAME_STATE_TACTICS
            return
        
        # Normal custom tactics editing
        if key == pygame.K_r:
            # Reset positions
            self.custom_tactics_editor.reset_to_default_positions()
        elif key == pygame.K_s:
            # Save directly (no confirmation for keyboard shortcut)
            if self.custom_tactics_editor.save_tactic():
                self.game_state = GAME_STATE_TACTICS
                self._available_tactics = self.tactics_manager.get_available_tactics()
        elif key == pygame.K_ESCAPE:
            # Check for unsaved changes before exiting
            if self.custom_tactics_editor.check_unsaved_changes():
                # Show confirmation dialog for unsaved changes
                self._show_unsaved_changes_dialog = True
            else:
                # No unsaved changes, exit normally
                self.game_state = GAME_STATE_TACTICS
                self.update_music()

    def _is_bot_turn(self):
        # Inline optimization for frequently called method
        return self.singleplayer and self.current_team == self.bot_team

    def _bot_context(self):
        """Return enhanced context with threat assessment and predictive analysis."""
        score_diff = (self.team1_score - self.team2_score) if self.bot_team == 1 else (self.team2_score - self.team1_score)
        turns_left = max(0, self.max_turns - self.turn_number)
        endgame = turns_left <= BOT_ENDGAME_TURNS
        leading = score_diff > 0
        trailing = score_diff < 0
        tied = score_diff == 0
        risk = BOT_BASE_RISK.get(self.bot_difficulty, 0.6)
        
        # Enhanced context with predictive elements
        ball_velocity = self._calculate_ball_velocity()
        predicted_ball_pos = self._predict_ball_position(1.5)  # Predict 1.5 seconds ahead
        threat_level = self._assess_threat_level()
        defensive_pressure = self._calculate_defensive_pressure()
        
        return {
            "score_diff": score_diff,
            "turns_left": turns_left,
            "endgame": endgame,
            "leading": leading,
            "trailing": trailing,
            "tied": tied,
            "risk": risk,
            "ball_velocity": ball_velocity,
            "predicted_ball_pos": predicted_ball_pos,
            "threat_level": threat_level,
            "defensive_pressure": defensive_pressure,
            "anticipation_mode": self._bot_anticipation_mode
        }

    def _bot_pick_player_index(self):
        players = self.get_current_team_players()
        opponents = self._opponent_players()
        
        # Use cached calculations if available for current frame
        frame_id = pygame.time.get_ticks() // 16  # ~60fps granularity
        if self._bot_cache['last_frame'] == frame_id:
            ctx = self._bot_cache['context']
            cached_team_dists = self._bot_cache['team_distances']
            cached_opp_dists = self._bot_cache['opponent_distances']
        else:
            ctx = self._bot_context()
            # Pre-calculate all distances for caching
            bx, by = self.ball.x, self.ball.y
            cached_team_dists = [p.distance_to(bx, by) for p in players]
            cached_opp_dists = [o.distance_to(bx, by) for o in opponents]
            
            # Cache for this frame
            self._bot_cache.update({
                'last_frame': frame_id,
                'context': ctx,
                'team_distances': cached_team_dists,
                'opponent_distances': cached_opp_dists
            })

        # Quick state assessment using cached distances
        bx, by = self.ball.x, self.ball.y
        field_mid_x = FIELD_X + FIELD_WIDTH / 2
        ball_on_our_side = (bx < field_mid_x) if self.current_team == 1 else (bx > field_mid_x)

        # Nearest distances to ball using cached values
        my_nearest = min((d for i, d in enumerate(cached_team_dists) if players[i].can_move), default=1e9)
        opp_nearest = min(cached_opp_dists, default=1e9)

        # Any of our players can kick now?
        any_can_kick = any(cached_team_dists[i] <= (players[i].radius + self.ball.radius + KICK_RANGE_BONUS) and players[i].can_move 
                          for i in range(len(players)))

        # Enhanced intent decision with predictive analysis
        predicted_ball_x, predicted_ball_y = ctx.get('predicted_ball_pos', (bx, by))
        threat_level = ctx.get('threat_level', 0.0)
        defensive_pressure = ctx.get('defensive_pressure', 0.0)
        anticipation_mode = ctx.get('anticipation_mode', False)
        
        # Decide intent with enhanced logic
        if any_can_kick:
            intent = 'shoot'
        elif threat_level > 0.6 or (ball_on_our_side and defensive_pressure > 0.5):
            intent = 'defend'
        elif anticipation_mode and opp_nearest < my_nearest * 0.8:
            # In anticipation mode, be more defensive when opponents are closer
            intent = 'intercept'
        else:
            # Use predicted ball position for attack positioning
            pred_my_nearest = min((math.hypot(p.x - predicted_ball_x, p.y - predicted_ball_y) 
                                 for p in players if p.can_move), default=1e9)
            pred_opp_nearest = min((math.hypot(o.x - predicted_ball_x, o.y - predicted_ball_y) 
                                  for o in opponents), default=1e9)
            
            if pred_my_nearest < pred_opp_nearest * 1.2:
                intent = 'attack'
            else:
                intent = 'defend'

        # Weighting by difficulty
        # Difficulty-based jitter; shrink in endgame if trailing to be sharper
        base_jitter = BOT_AIM_JITTER.get(self.bot_difficulty, 6.0)
        if ctx["endgame"] and ctx["trailing"]:
            base_jitter *= 0.6
        jitter = base_jitter
        # Lane tightness scales with risk
        base_lane = 56
        lane_thresh = int(base_lane - ctx["risk"] * 18)

        gx_opp, gy_opp = self._opponent_goal_center()
        gx_own, gy_own = self._own_goal_center()

        best_i, best_score = 0, -1e12
        for i, p in enumerate(players):
            if not p.can_move:
                continue
            px, py = p.x, p.y
            d_ball = max(cached_team_dists[i], 1.0)  # Use cached distance
            can_kick = d_ball <= (p.radius + self.ball.radius + KICK_RANGE_BONUS)

            score = 0.0
            # Mild penalty to avoid always choosing GK (assume id 0 is GK per formation)
            if i == 0:
                score -= 25

            if intent == 'shoot':
                # Prefer those who can kick, with clear lane to goal
                lane = self._line_pressure(bx, by, gx_opp, gy_opp, opponents, lane_thresh)
                score += (1500 if can_kick else 0) + (400.0 / d_ball) - (lane * (28 + (1.0 - ctx["risk"]) * 20))
                # Favor being closer to opponent goal when not kickable yet
                if not can_kick:
                    score += 120.0 / (math.hypot(px - gx_opp, py - gy_opp) + 1)
            elif intent == 'defend':
                # Prefer those who can quickly block the ball-to-goal line
                block_x = bx * 0.7 + gx_own * 0.3
                block_y = by * 0.7 + gy_own * 0.3
                d_block = math.hypot(px - block_x, py - block_y)
                # If leading late game, increase defensive weight; if trailing, reduce it
                def_weight = 1.25 if (ctx["endgame"] and ctx["leading"]) else (0.9 if ctx["trailing"] else 1.0)
                score += def_weight * (520.0 / (d_block + 1)) + 220.0 / (d_ball)
                # Slightly favor deeper players on our half
                if self.current_team == 1:
                    score += (FIELD_X + FIELD_WIDTH * 0.25 - px) * 0.05
                else:
                    score += (px - (FIELD_X + FIELD_WIDTH * 0.75)) * 0.05
            elif intent == 'intercept':
                # New intercept mode: position to intercept predicted ball path
                d_predicted = math.hypot(px - predicted_ball_x, py - predicted_ball_y)
                # High score for being close to predicted ball position
                score += 600.0 / (d_predicted + 1)
                # Bonus for being between current ball and predicted position
                intercept_factor = self._calculate_intercept_position_score(px, py, bx, by, predicted_ball_x, predicted_ball_y)
                score += intercept_factor * 200
                # Penalty for being too far from our goal (don't abandon defense completely)
                d_own_goal = math.hypot(px - gx_own, py - gy_own)
                if d_own_goal > FIELD_WIDTH * 0.6:
                    score -= 100
            else:  # attack
                # Get to ball fast with less opposition on the route
                lane = self._line_pressure(px, py, bx, by, opponents, lane_thresh)
                # If trailing late, value aggression more (less penalty for pressure)
                lane_pen = 35
                if ctx["endgame"] and ctx["trailing"]:
                    lane_pen *= 0.6
                score += 520.0 / d_ball - (lane * lane_pen)
                # Favor forward positions toward opponent goal
                score += 100.0 / (math.hypot(px - gx_opp, py - gy_opp) + 1)

            # Enhanced difficulty-based jitter with anticipation adjustment
            final_jitter = jitter
            if anticipation_mode:
                final_jitter *= 0.5  # More precise in anticipation mode
            score += random.uniform(-final_jitter, final_jitter)

            if score > best_score:
                best_score = score
                best_i = i
        return best_i

    def _bot_assess_intent_and_target(self, player):
        """Return (intent, tx, ty) for the acting team based on ball side and immediate kick chance.
        intent in {'shoot','attack','defend'}.
        """
        bx, by = self.ball.x, self.ball.y
        px, py = player.x, player.y
        field_mid_x = FIELD_X + FIELD_WIDTH / 2
        acting_team = self.current_team
        # Ball on our side?
        ball_on_our_side = (bx < field_mid_x) if acting_team == 1 else (bx > field_mid_x)
        # Can we kick immediately?
        can_kick = player.distance_to(bx, by) <= (player.radius + self.ball.radius + KICK_RANGE_BONUS)
        ctx = self._bot_context()

        # Enhanced intent assessment with predictive analysis
        predicted_ball_x, predicted_ball_y = ctx.get('predicted_ball_pos', (bx, by))
        threat_level = ctx.get('threat_level', 0.0)
        anticipation_mode = ctx.get('anticipation_mode', False)
        
        if can_kick:
            # Shoot: pick opponent goal corner nearest to player
            targets = self._bot_goal_targets(acting_team)
            tx, ty = min(targets, key=lambda t: (t[0] - px) ** 2 + (t[1] - py) ** 2)
            return 'shoot', tx, ty

        # Enhanced decision logic
        if threat_level > 0.7 or ball_on_our_side:
            # High threat or defensive situation: block the line from ball to our goal center
            gx, gy = self._own_goal_center(acting_team)
            tx = bx * 0.65 + gx * 0.35
            ty = by * 0.65 + gy * 0.35
            return 'defend', tx, ty
        elif anticipation_mode:
            # Anticipation mode: move to intercept predicted ball position
            tx, ty = predicted_ball_x, predicted_ball_y
            return 'intercept', tx, ty
        else:
            # Attack: enhanced prediction-based positioning
            lead = 18 if self.bot_difficulty == 'hard' else 10 if self.bot_difficulty == 'medium' else 0
            if hasattr(self.ball, 'vx') and hasattr(self.ball, 'vy'):
                tx = bx + (self.ball.vx * lead * 0.02)
                ty = by + (self.ball.vy * lead * 0.02)
            else:
                # Use predicted position if no velocity data
                tx, ty = predicted_ball_x, predicted_ball_y
            return 'attack', tx, ty

    def _own_goal_center(self, team=None):
        if team is None:
            team = self.current_team
        if team == 1:
            return FIELD_X - GOAL_DEPTH - 10, FIELD_Y + FIELD_HEIGHT / 2
        return FIELD_X + FIELD_WIDTH + GOAL_DEPTH + 10, FIELD_Y + FIELD_HEIGHT / 2

    def _opponent_goal_center(self, team=None):
        if team is None:
            team = self.current_team
        if team == 1:
            return FIELD_X + FIELD_WIDTH + GOAL_DEPTH + 10, FIELD_Y + FIELD_HEIGHT / 2
        return FIELD_X - GOAL_DEPTH - 10, FIELD_Y + FIELD_HEIGHT / 2

    def _opponent_players(self):
        return self.team2_players if self.current_team == 1 else self.team1_players

    def _line_pressure(self, ax, ay, bx, by, players, thresh):
        """Count opponents near the segment A->B to estimate blocking pressure."""
        cnt = 0
        abx, aby = bx - ax, by - ay
        ab_len2 = abx * abx + aby * aby
        if ab_len2 <= 1e-6:
            return 0
        for op in players:
            px, py = op.x, op.y
            apx, apy = px - ax, py - ay
            t = (apx * abx + apy * aby) / ab_len2
            if t < 0:
                sx, sy = ax, ay
            elif t > 1:
                sx, sy = bx, by
            else:
                sx, sy = ax + t * abx, ay + t * aby
            dist = math.hypot(px - sx, py - sy)
            if dist <= thresh:
                cnt += 1
        return cnt

    def _bot_goal_targets(self, team=None):
        # Return two corners inside the opponent goal area for smarter shots
        opp_left_x = FIELD_X - GOAL_DEPTH - 5
        opp_right_x = FIELD_X + FIELD_WIDTH + GOAL_DEPTH + 5
        gy_top = FIELD_Y + (FIELD_HEIGHT - GOAL_WIDTH) // 2 + 15
        gy_bot = FIELD_Y + (FIELD_HEIGHT + GOAL_WIDTH) // 2 - 15
        if team is None:
            team = self.current_team
        if team == 1:
            # shoot to the right
            return [(opp_right_x, gy_top), (opp_right_x, gy_bot)]
        else:
            # shoot to the left
            return [(opp_left_x, gy_top), (opp_left_x, gy_bot)]

    def _bot_aim_at_target(self, player):
        px, py = player.x, player.y
        intent, tx, ty = self._bot_assess_intent_and_target(player)
        # Difficulty-based jitter
        # Base jitter by difficulty, trimmed in endgame if trailing
        ctx = self._bot_context()
        jitter = BOT_AIM_JITTER.get(self.bot_difficulty, 6.0)
        if ctx["endgame"] and ctx["trailing"]:
            jitter *= 0.6
        tx += random.uniform(-jitter, jitter)
        ty += random.uniform(-jitter, jitter)
        player.set_aim_direction(tx - px, ty - py)

    def _bot_force_choice(self):
        # Choose force dynamically based on intent and distance to target
        current = self.get_current_player()
        if not current:
            return int((MIN_FORCE + MAX_FORCE) * 0.5)

        intent, tx, ty = self._bot_assess_intent_and_target(current)
        px, py = current.x, current.y
        dist = math.hypot(tx - px, ty - py)
        ctx = self._bot_context()

        if intent == 'shoot':
            # Choose force based on risk and distance; higher risk pushes stronger shots
            base = min(MAX_FORCE, max(MIN_FORCE, dist * (0.9 + ctx["risk"] * 0.4)))
        elif intent == 'defend':
            # Safer movement when leading late; bolder when trailing
            mult = 0.8 if (ctx["endgame"] and ctx["leading"]) else (1.1 if ctx["trailing"] else 0.95)
            base = dist * mult
        else:  # attack toward ball/lead
            # More aggressive closing when trailing
            mult = 1.25 if (ctx["endgame"] and ctx["trailing"]) else 1.05
            base = dist * mult

        # Difficulty-based randomness
        noise_ratio = BOT_FORCE_NOISE.get(self.bot_difficulty, 0.12)
        base *= (1.0 + random.uniform(-noise_ratio, noise_ratio))

        # Clamp to allowed range
        return int(max(MIN_FORCE, min(MAX_FORCE, base)))

    def _update_bot(self):
        now = pygame.time.get_ticks()
        if now - self._last_bot_action < self._bot_action_cooldown_ms:
            return
        self._last_bot_action = now

        if self.current_phase in (PHASE_SELECT_PLAYER, PHASE_AIM_DIRECTION, PHASE_SELECT_FORCE):
            # Ensure a player is selected
            if self.current_phase == PHASE_SELECT_PLAYER:
                idx = self._bot_pick_player_index()
                self.select_player(idx)
                return

            # Aim
            if self.current_phase == PHASE_AIM_DIRECTION:
                player = self.get_current_player()
                if player:
                    # Seed arrow toward current ball once, then act on next tick
                    if not self._aim_seeded:
                        dx = self.ball.x - player.x
                        dy = self.ball.y - player.y
                        if dx != 0 or dy != 0:
                            player.set_aim_direction(dx, dy)
                        self._aim_seeded = True
                        return
                    # Decide and confirm aim
                    self._bot_aim_at_target(player)
                    self.confirm_aim_direction()
                return

            # Select force and execute quickly (no oscillating meter for bot)
            if self.current_phase == PHASE_SELECT_FORCE:
                self.force_power = self._bot_force_choice()
                self.execute_player_movement()

    def _calculate_ball_velocity(self):
        """Calculate ball velocity from recent position history."""
        if len(self._bot_ball_history) < 2:
            return (0, 0)
        
        # Use last two positions to estimate velocity
        pos1 = self._bot_ball_history[-2]
        pos2 = self._bot_ball_history[-1]
        dt = pos2[2] - pos1[2]  # time difference
        
        if dt <= 0:
            return (0, 0)
        
        vx = (pos2[0] - pos1[0]) / dt * 1000  # Convert to pixels per second
        vy = (pos2[1] - pos1[1]) / dt * 1000
        return (vx, vy)

    def _predict_ball_position(self, seconds_ahead):
        """Predict ball position based on current velocity and friction."""
        vx, vy = self._calculate_ball_velocity()
        
        # Account for friction decay
        friction_factor = FRICTION ** (seconds_ahead * 60)  # Assume 60 FPS
        
        predicted_x = self.ball.x + vx * seconds_ahead * friction_factor
        predicted_y = self.ball.y + vy * seconds_ahead * friction_factor
        
        # Clamp to field bounds
        predicted_x = max(FIELD_X, min(FIELD_X + FIELD_WIDTH, predicted_x))
        predicted_y = max(FIELD_Y, min(FIELD_Y + FIELD_HEIGHT, predicted_y))
        
        return (predicted_x, predicted_y)

    def _assess_threat_level(self):
        """Assess threat level from opponent positions and ball location."""
        if not self.singleplayer:
            return 0.0
        
        bx, by = self.ball.x, self.ball.y
        our_goal_x, our_goal_y = self._own_goal_center()
        opponents = self._opponent_players()
        
        threat = 0.0
        
        # Distance threat: closer ball to our goal = higher threat
        ball_goal_dist = math.hypot(bx - our_goal_x, by - our_goal_y)
        max_dist = math.hypot(FIELD_WIDTH, FIELD_HEIGHT)
        threat += (1.0 - ball_goal_dist / max_dist) * 0.4
        
        # Opponent threat: opponents close to ball and between ball and our goal
        for opp in opponents:
            if not opp.can_move:
                continue
            
            opp_ball_dist = opp.distance_to(bx, by)
            if opp_ball_dist < 100:  # Within threatening distance
                # Check if opponent is between ball and our goal
                opp_goal_dist = math.hypot(opp.x - our_goal_x, opp.y - our_goal_y)
                if opp_goal_dist < ball_goal_dist:
                    threat += (100 - opp_ball_dist) / 100 * 0.3
        
        return min(1.0, threat)

    def _calculate_defensive_pressure(self):
        """Calculate how much defensive pressure bot should apply."""
        # Avoid circular dependency with _bot_context
        threat = self._assess_threat_level()
        
        pressure = threat * 0.5
        
        # Increase pressure when leading and in endgame based on direct calculation
        score_diff = self.team1_score - self.team2_score
        turns_left = max(0, self.max_turns - self.turn_number)
        endgame = turns_left <= 10
        leading = score_diff > 0
        trailing = score_diff < 0
        
        if leading and endgame:
            pressure += 0.3
        
        # Decrease pressure when trailing (more aggressive)
        if trailing:
            pressure *= 0.7
        
        return min(1.0, pressure)

    def _update_bot_tracking(self):
        """Update bot tracking systems each frame."""
        now = pygame.time.get_ticks()
        
        # Update ball history for velocity prediction
        self._bot_ball_history.append((self.ball.x, self.ball.y, now))
        # Keep only last 5 positions
        if len(self._bot_ball_history) > 5:
            self._bot_ball_history.pop(0)
        
        # Update opponent position tracking
        opponents = self._opponent_players()
        for i, opp in enumerate(opponents):
            self._bot_player_positions[f'opp_{i}'] = (opp.x, opp.y, now)
        
        # Detect if opponent just made an action
        if self.current_team != self.bot_team and now - self._bot_last_opponent_action > 100:
            self._bot_last_opponent_action = now
            self._bot_anticipation_mode = True
        
        # Disable anticipation mode after some time
        if self._bot_anticipation_mode and now - self._bot_last_opponent_action > 2000:
            self._bot_anticipation_mode = False

    def _calculate_intercept_position_score(self, px, py, ball_x, ball_y, pred_x, pred_y):
        """Calculate how good a position is for intercepting ball movement."""
        # Vector from current ball to predicted position
        ball_vec_x = pred_x - ball_x
        ball_vec_y = pred_y - ball_y
        ball_vec_len = math.hypot(ball_vec_x, ball_vec_y)
        
        if ball_vec_len < 1:
            return 0.0  # Ball not moving much
        
        # Normalize ball movement vector
        ball_unit_x = ball_vec_x / ball_vec_len
        ball_unit_y = ball_vec_y / ball_vec_len
        
        # Vector from current ball to player
        to_player_x = px - ball_x
        to_player_y = py - ball_y
        
        # Project player position onto ball movement line
        dot_product = to_player_x * ball_unit_x + to_player_y * ball_unit_y
        
        # Player is ahead of ball movement = good intercept position
        if 0 < dot_product < ball_vec_len:
            # Calculate perpendicular distance to ball path
            perp_dist = abs(to_player_x * ball_unit_y - to_player_y * ball_unit_x)
            # Good intercept if close to the path and ahead of ball
            return max(0, 1.0 - perp_dist / 50.0)  # 50 pixel tolerance
        
        return 0.0
    
    def draw_scoreboard(self, screen):
        """Draw the scoreboard"""
        # Background
        scoreboard_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCOREBOARD_HEIGHT)
        pygame.draw.rect(screen, BLACK, scoreboard_rect)
        pygame.draw.rect(screen, WHITE, scoreboard_rect, 2)
        
        # Team scores with colored team names
        score_segments = [
            ("Team 1   ", TEAM1_COLOR),  # Blue
            (str(self.team1_score), WHITE),
            (" - ", WHITE),
            (str(self.team2_score), WHITE),
            ("   Team 2", TEAM2_COLOR)   # Red
        ]
        self.render_multicolor_text(screen, score_segments, SCOREBOARD_HEIGHT // 2 - 10, SCREEN_WIDTH // 2)
        
        # Turn indicator with colored current team
        # Show turn number and team, with turn limit if applicable
        if self.game_mode in ['turns_only', 'both']:
            turn_segments = [
            (f"Turn: {min(self.turn_number, self.max_turns_limit)}/{self.max_turns_limit} | ", WHITE),
            (f"Team {self.current_team}'s turn", WHITE)
            ]
        else:
            turn_segments = [
            (f"Turn: {self.turn_number} | ", WHITE),
            (f"Team {self.current_team}'s turn", WHITE)
            ]
        current_x = 10
        for text, color in turn_segments:
            turn_surface = self.small_font.render(text, True, color)
            screen.blit(turn_surface, (current_x, 10))
            current_x += turn_surface.get_width()
        
        # Phase indicator
        phase_texts = {
            PHASE_SELECT_PLAYER: "Select Player (1-5)",
            PHASE_AIM_DIRECTION: "Aim Direction (WASD/Arrows + Space/Enter)",
            PHASE_SELECT_FORCE: "Set Force (Space/Enter to move)",
            PHASE_PLAYER_MOVING: "Player Moving...",
            PHASE_BALL_MOVING: "Ball Moving..."
        }
        phase_text = self.small_font.render(phase_texts.get(self.current_phase, ""), True, WHITE)
        phase_rect = phase_text.get_rect(topright=(SCREEN_WIDTH - 10, 10))
        screen.blit(phase_text, phase_rect)
    
    def draw_force_meter(self, screen):
        """Draw the force meter"""
        if not self.force_meter_active:
            return
        
        current_player = self.get_current_player()
        if not current_player:
            return
        
        # Position above player
        meter_x = current_player.x - FORCE_METER_WIDTH // 2
        meter_y = current_player.y - current_player.radius - 30
        
        # Background
        pygame.draw.rect(screen, BLACK, 
                        (meter_x, meter_y, FORCE_METER_WIDTH, FORCE_METER_HEIGHT))
        
        # Force bar
        force_width = (self.force_power - MIN_FORCE) / (MAX_FORCE - MIN_FORCE) * FORCE_METER_WIDTH
        
        # Color based on force (green to red)
        force_ratio = (self.force_power - MIN_FORCE) / (MAX_FORCE - MIN_FORCE)
        red = int(255 * force_ratio)
        green = int(255 * (1 - force_ratio))
        force_color = (red, green, 0)
        
        pygame.draw.rect(screen, force_color, 
                        (meter_x, meter_y, force_width, FORCE_METER_HEIGHT))
        
        # Border
        pygame.draw.rect(screen, WHITE, 
                        (meter_x, meter_y, FORCE_METER_WIDTH, FORCE_METER_HEIGHT), 2)
    
    def draw_game_over(self, screen):
        """Draw game over screen"""
        if self.game_state != GAME_STATE_GAME_OVER:
            return
        
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Winner text
        if self.team1_score > self.team2_score:
            winner_text = "Team 1 Wins!"
            winner_color = TEAM1_COLOR
        elif self.team2_score > self.team1_score:
            winner_text = "Team 2 Wins!"
            winner_color = TEAM2_COLOR
        else:
            winner_text = "It's a Tie!"
            winner_color = WHITE
        
        # Large winner text
        big_font = pygame.font.Font(None, 72)
        winner_surface = big_font.render(winner_text, True, winner_color)
        winner_rect = winner_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(winner_surface, winner_rect)
        
        # Final score
        final_score = self.font.render(f"Final Score: {self.team1_score} - {self.team2_score}", 
                                      True, WHITE)
        score_rect = final_score.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(final_score, score_rect)
        
        # Restart instruction
        restart_text = self.small_font.render("Press R to restart • M for menu • ESC to quit", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        screen.blit(restart_text, restart_rect)
    
    def get_ending_music_type(self):
        """Determine the appropriate ending music based on game mode and result."""
        # Check for tie first
        if self.team1_score == self.team2_score:
            return 'end_tie'
        
        if self.singleplayer:
            # In singleplayer, determine if human won or lost
            if self.bot_team == 1:
                # Human is team 2, bot is team 1
                human_won = self.team2_score > self.team1_score
            else:
                # Human is team 1, bot is team 2  
                human_won = self.team1_score > self.team2_score
            
            return 'end_win' if human_won else 'end_lose'
        else:
            # Multiplayer game
            return 'end_2p'
    
    def restart_game(self):
        """Restart the game while preserving user configuration settings and starting from coin flip"""
        # Save current configuration settings
        saved_config = {
            'singleplayer': self.singleplayer,
            'bot_team': self.bot_team,
            'bot_difficulty': self.bot_difficulty,
            'game_mode': self.game_mode,
            'max_goals': self.max_goals,
            'max_turns_limit': self.max_turns_limit,
            'team1_tactic': self.tactics_manager.get_team_tactic(1),
            'team2_tactic': self.tactics_manager.get_team_tactic(2),
            'master_volume': self.master_volume,
            'sfx_volume': self.sfx_volume,
            'bgm_volume': self.bgm_volume
        }
        
        # Reset game state
        self.__init__()
        
        # Restore user configuration
        self.singleplayer = saved_config['singleplayer']
        self.bot_team = saved_config['bot_team']
        self.bot_difficulty = saved_config['bot_difficulty']
        self.game_mode = saved_config['game_mode']
        self.max_goals = saved_config['max_goals']
        self.max_turns_limit = saved_config['max_turns_limit']
        
        # Restore team tactics
        self.tactics_manager.set_team_tactic(1, saved_config['team1_tactic'])
        self.tactics_manager.set_team_tactic(2, saved_config['team2_tactic'])
        
        # Restore volume settings
        self.master_volume = saved_config['master_volume']
        self.sfx_volume = saved_config['sfx_volume']
        self.bgm_volume = saved_config['bgm_volume']
        self.sync_volume_settings()
        
        # Update dependent settings
        self.max_turns = self.max_turns_limit
        self._bot_action_cooldown_ms = BOT_THINK_MS.get(self.bot_difficulty, self._bot_action_cooldown_ms)
        
        # Start directly from coin flip phase (skip menu and tactics selection)
        self._start_game()
        
        # Note: _music_initialized is set to False in __init__, 
        # music will be updated by start_coin_flip() call
    
    def save_audio_configuration(self):
        """Save current audio settings to config manager for persistence"""
        try:
            set_audio_config('master_volume', self.master_volume)
            set_audio_config('sfx_volume', self.sfx_volume)
            set_audio_config('bgm_volume', self.bgm_volume)
        except Exception as e:
            print(f"Failed to save audio configuration: {e}")

    def sync_volume_settings(self):
        """Synchronize volume settings from GameManager to SoundManager"""
        self.sounds.set_volume_levels(
            self.master_volume,
            self.sfx_volume,
            self.bgm_volume
        )
        # Schedule audio configuration save (debounced)
        self._audio_save_timer = pygame.time.get_ticks() + self._audio_save_delay
    
    def return_to_menu_with_config(self):
        """Return to menu while preserving user configuration settings"""
        # Save current configuration settings
        saved_config = {
            'singleplayer': self.singleplayer,
            'bot_team': self.bot_team,
            'bot_difficulty': self.bot_difficulty,
            'game_mode': self.game_mode,
            'max_goals': self.max_goals,
            'max_turns_limit': self.max_turns_limit,
            'team1_tactic': self.tactics_manager.get_team_tactic(1),
            'team2_tactic': self.tactics_manager.get_team_tactic(2),
            'master_volume': self.master_volume,
            'sfx_volume': self.sfx_volume,
            'bgm_volume': self.bgm_volume
        }
        
        # Reset game state
        self.__init__()
        
        # Restore user configuration
        self.singleplayer = saved_config['singleplayer']
        self.bot_team = saved_config['bot_team']
        self.bot_difficulty = saved_config['bot_difficulty']
        self.game_mode = saved_config['game_mode']
        self.max_goals = saved_config['max_goals']
        self.max_turns_limit = saved_config['max_turns_limit']
        
        # Restore team tactics
        self.tactics_manager.set_team_tactic(1, saved_config['team1_tactic'])
        self.tactics_manager.set_team_tactic(2, saved_config['team2_tactic'])
        
        # Restore volume settings
        self.master_volume = saved_config['master_volume']
        self.sfx_volume = saved_config['sfx_volume']
        self.bgm_volume = saved_config['bgm_volume']
        self.sync_volume_settings()
        
        # Update dependent settings
        self.max_turns = self.max_turns_limit
        self._bot_action_cooldown_ms = BOT_THINK_MS.get(self.bot_difficulty, self._bot_action_cooldown_ms)
        
        # Set game state to menu
        self.game_state = GAME_STATE_MENU
        self.update_music()
    
    def draw(self, screen):
        """Draw everything"""
        if self.game_state == GAME_STATE_MENU:
            # Draw background image with gradient overlay
            self._draw_menu_background(screen)
            self.draw_menu(screen)
            return
        elif self.game_state == GAME_STATE_AUDIO:
            # Draw background image with gradient overlay
            self._draw_menu_background(screen)
            self.draw_audio_menu(screen)
            return
        elif self.game_state == GAME_STATE_TACTICS:
            # Draw background image with gradient overlay
            self._draw_menu_background(screen)
            self.draw_tactics_selection(screen)
            
            # Draw invalid tactics dialog if needed (highest priority)
            if self._show_invalid_tactics_dialog:
                self.draw_invalid_tactics_dialog(screen)
            # Draw reset all confirmation dialog if needed
            elif self._show_reset_all_confirmation:
                self.draw_reset_all_confirmation(screen)
            return
        elif self.game_state == GAME_STATE_CUSTOM_TACTICS:
            # Draw background image with gradient overlay
            self._draw_menu_background(screen)
            # Custom tactics editor handles its own drawing
            self.custom_tactics_editor.draw(screen)
            
            # Draw confirmation dialogs if needed
            if self._show_save_confirmation:
                self.draw_save_confirmation(screen)
            elif self._show_unsaved_changes_dialog:
                self.draw_unsaved_changes_dialog(screen)
            return
        elif self.game_state == GAME_STATE_COIN_FLIP:
            # Draw background image with gradient overlay
            self._draw_menu_background(screen)
            self.draw_coin_flip(screen)
            return
        elif self.game_state == GAME_STATE_GAME_OVER:
            # Game over state - keep playground rendered to show how the winning goal was scored
            # Get camera transformation
            zoom, offset_x, offset_y = self.get_camera_transform()
            
            if zoom != 1.0:
                # Create a temporary surface for zoom transformation
                temp_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                temp_surface.fill(BLACK)
                
                # Draw everything to temp surface with camera transformation
                self.draw_game_world(temp_surface, zoom, offset_x, offset_y)
                
                # Blit the transformed surface to the main screen
                screen.blit(temp_surface, (0, 0))
            else:
                # No zoom, draw normally
                self.draw_game_world(screen, 1.0, 0, 0)
            
            # Always draw UI elements (scoreboard, etc.) without camera transformation
            self.draw_scoreboard(screen)
            
            # Show goal banner if it was active when the game ended
            if self.goal_banner_until and pygame.time.get_ticks() < self.goal_banner_until:
                # Remove backlit background - no overlay
                banner_font = pygame.font.Font(None, 72)
                text = banner_font.render("GAME!!!", True, YELLOW)
                rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 200))
                screen.blit(text, rect)
            
            # Draw game over overlay on top of the playground
            self.draw_game_over(screen)
            return
            
        # Get camera transformation
        zoom, offset_x, offset_y = self.get_camera_transform()
        
        if zoom != 1.0:
            # Create a temporary surface for zoom transformation
            temp_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            temp_surface.fill(BLACK)
            
            # Draw everything to temp surface with camera transformation
            self.draw_game_world(temp_surface, zoom, offset_x, offset_y)
            
            # Blit the transformed surface to the main screen
            screen.blit(temp_surface, (0, 0))
        else:
            # No zoom, draw normally
            self.draw_game_world(screen, 1.0, 0, 0)
        
        # Always draw UI elements (scoreboard, etc.) without camera transformation
        self.draw_scoreboard(screen)
        self.draw_force_meter(screen)
        
        # Goal notification banner overlay
        if self.goal_banner_until and (
            (self.game_state != GAME_STATE_PAUSED and pygame.time.get_ticks() < self.goal_banner_until) or
            (self.game_state == GAME_STATE_PAUSED)  # Always show during pause
        ):
            # Remove backlit background - no overlay
            banner_font = pygame.font.Font(None, 72)
            text = banner_font.render("GOAL!!!", True, YELLOW)
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 200))
            screen.blit(text, rect)
    
    def draw_game_world(self, surface, zoom, offset_x, offset_y):
        """Draw the game world (field, players, ball) with camera transformation"""
        if zoom == 1.0:
            # No transformation needed
            self.field.draw(surface)
            
            # Draw players
            for player in self.team1_players + self.team2_players:
                player.draw(surface)
            
            # Draw direction arrow for selected player
            current_player = self.get_current_player()
            if (current_player and self.current_phase == PHASE_AIM_DIRECTION):
                current_player.draw_direction_arrow(surface)
            
            # Draw ball
            self.ball.draw(surface)
        else:
            # Apply zoom transformation using scaled drawing
            self.draw_scaled_game_world(surface, zoom, offset_x, offset_y)
    
    def draw_scaled_game_world(self, surface, zoom, offset_x, offset_y):
        """Draw game world elements with scaled coordinates and offset"""
        # Draw field with scaling
        self.field.draw_scaled(surface, zoom, offset_x, offset_y)
        
        # Draw players with scaled positions
        for player in self.team1_players + self.team2_players:
            scaled_x = player.x * zoom + offset_x
            scaled_y = player.y * zoom + offset_y
            scaled_radius = player.radius * zoom
            
            # Draw player circle with scaled position and size
            color = TEAM1_COLOR if player.team == 1 else TEAM2_COLOR
            if scaled_x + scaled_radius > 0 and scaled_x - scaled_radius < SCREEN_WIDTH and \
               scaled_y + scaled_radius > 0 and scaled_y - scaled_radius < SCREEN_HEIGHT:
                pygame.draw.circle(surface, color, (int(scaled_x), int(scaled_y)), int(scaled_radius))
                if player.selected:
                    pygame.draw.circle(surface, WHITE, (int(scaled_x), int(scaled_y)), int(scaled_radius), 2)
        
        # Draw ball with scaled position
        scaled_ball_x = self.ball.x * zoom + offset_x
        scaled_ball_y = self.ball.y * zoom + offset_y
        scaled_ball_radius = self.ball.radius * zoom
        
        if scaled_ball_x + scaled_ball_radius > 0 and scaled_ball_x - scaled_ball_radius < SCREEN_WIDTH and \
           scaled_ball_y + scaled_ball_radius > 0 and scaled_ball_y - scaled_ball_radius < SCREEN_HEIGHT:
            pygame.draw.circle(surface, WHITE, (int(scaled_ball_x), int(scaled_ball_y)), int(scaled_ball_radius))
            pygame.draw.circle(surface, BLACK, (int(scaled_ball_x), int(scaled_ball_y)), int(scaled_ball_radius), 1)
        
        # Draw direction arrow for selected player with scaling
        current_player = self.get_current_player()
        if (current_player and self.current_phase == PHASE_AIM_DIRECTION):
            scaled_player_x = current_player.x * zoom + offset_x
            scaled_player_y = current_player.y * zoom + offset_y
            scaled_arrow_length = DIRECTION_ARROW_LENGTH * zoom
            
            end_x = scaled_player_x + math.cos(current_player.aim_direction) * scaled_arrow_length
            end_y = scaled_player_y + math.sin(current_player.aim_direction) * scaled_arrow_length
            
            if scaled_player_x > 0 and scaled_player_x < SCREEN_WIDTH and \
               scaled_player_y > 0 and scaled_player_y < SCREEN_HEIGHT:
                pygame.draw.line(surface, YELLOW, 
                               (int(scaled_player_x), int(scaled_player_y)), 
                               (int(end_x), int(end_y)), 3)

    def _draw_menu_background(self, screen):
        """Draw background image with gradient overlay for menu states"""
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
            # Create and draw gradient overlay
            self._create_gradient_overlay()
            screen.blit(self.gradient_surface, (0, 0))
        else:
            screen.fill(BLACK)

    def _reduce_rgb(self, color, amount=20):
        """Reduce each RGB component by the specified amount, clamping to 0"""
        return tuple(max(0, c - amount) for c in color[:3])
    
    def _create_gradient_overlay(self):
        """Create gradient overlay based on current difficulty"""
        # Get current and next difficulty colors
        difficulties = ["easy", "medium", "hard", "insane", "extreme"]
        current_idx = difficulties.index(self.bot_difficulty.lower())
        
        current_color = DIFFICULTY_COLORS[self.bot_difficulty.lower()]
        
        # Determine end color for gradient
        if current_idx < len(difficulties) - 1:
            next_color = DIFFICULTY_COLORS[difficulties[current_idx + 1]]
        else:
            # Extreme difficulty goes to black
            next_color = BLACK
        
        # Reduce RGB values by 20
        start_color = self._reduce_rgb(current_color, 20)
        end_color = self._reduce_rgb(next_color, 20)
        
        # Create vertical gradient surface
        self.gradient_surface.fill((0, 0, 0, 0))  # Clear with transparency
        
        for y in range(SCREEN_HEIGHT):
            # Calculate interpolation factor (0.0 at top, 1.0 at bottom)
            factor = y / SCREEN_HEIGHT
            
            # Interpolate between start and end colors
            r = int(start_color[0] + (end_color[0] - start_color[0]) * factor)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * factor)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * factor)
            
            # Draw horizontal line with interpolated color (semi-transparent)
            color = (r, g, b, 100)  # 100/255 alpha for soft overlay
            pygame.draw.line(self.gradient_surface, color, (0, y), (SCREEN_WIDTH, y))

    def draw_menu(self, screen):
        title_font = pygame.font.Font(None, 64)
        item_font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Mini Football", True, MENU_TEXT_COLOR)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 120))
        screen.blit(title, title_rect)

        # Compose values
        mode_val = "Singleplayer" if self.singleplayer else "Multiplayer"
        bot_team_val = f"Team {self.bot_team}"
        difficulty_val = self.bot_difficulty.capitalize()
        
        # Game mode descriptions
        game_mode_names = {
            'goals_only': 'Goals Only',
            'turns_only': 'Turns Only', 
            'both': 'Goals & Turns'
        }
        game_mode_val = game_mode_names.get(self.game_mode, 'Goals Only')
        
        goal_limit_val = f"{self.max_goals} goal{'s' if self.max_goals != 1 else ''}"
        turn_limit_val = f"{self.max_turns_limit} turns"
        
        # Volume values (displayed as percentages)
        master_vol_val = f"{int(self.master_volume * 100)}%"
        sfx_vol_val = f"{int(self.sfx_volume * 100)}%"
        bgm_vol_val = f"{int(self.bgm_volume * 100)}%"

        items = [
            ("Mode", mode_val),
            ("Bot Team", bot_team_val),
            ("Difficulty", difficulty_val),
            ("Game Mode", game_mode_val),
            ("Goal Limit", goal_limit_val),
            ("Turn Limit", turn_limit_val),
            ("Audio Settings", ""),
        ]

        start_y = 180
        gap = 40
        for i, (label, val) in enumerate(items):
            is_sel = (i == self._menu_index)
            enabled = self._menu_item_enabled(i)
            base_color = MENU_TEXT_COLOR if enabled else LIGHT_GRAY
            color = LIGHT_BLUE if (is_sel and enabled) else base_color
            
            # Special handling for Audio Settings - center it
            if i == 6:  # Audio Settings
                label_surf = item_font.render(f"{label}", True, color)
                label_rect = label_surf.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * gap))
                screen.blit(label_surf, label_rect)
            # Special handling for Difficulty - color-coded
            elif i == 2 and label == "Difficulty":  # Difficulty
                # Get difficulty color - ensure lowercase key lookup
                diff_color = DIFFICULTY_COLORS.get(self.bot_difficulty.lower(), MENU_TEXT_COLOR)
                
                # For difficulty, always use difficulty color, never override with selection color
                label_color = LIGHT_BLUE if is_sel else MENU_TEXT_COLOR
                val_color = diff_color  # Always use difficulty color
                
                label_surf = item_font.render(f"{label}", True, label_color)
                val_surf = item_font.render(f"{val}", True, val_color)
                
                lx = SCREEN_WIDTH // 2 - 200
                vx = SCREEN_WIDTH // 2 + 80
                y = start_y + i * gap
                
                # If selected, draw a subtle background highlight to show selection
                if is_sel:
                    # Create a subtle background rectangle
                    highlight_rect = pygame.Rect(lx - 5, y - 2, 400, 32)
                    # Use a very transparent white overlay
                    highlight_surface = pygame.Surface((highlight_rect.width, highlight_rect.height))
                    highlight_surface.set_alpha(30)  # Very subtle
                    highlight_surface.fill(WHITE)
                    screen.blit(highlight_surface, highlight_rect)
                
                screen.blit(label_surf, (lx, y))
                screen.blit(val_surf, (vx, y))
            else:
                label_surf = item_font.render(f"{label}", True, color)
                val_surf = item_font.render(f"{val}", True, color)
                lx = SCREEN_WIDTH // 2 - 200
                vx = SCREEN_WIDTH // 2 + 80
                y = start_y + i * gap
                screen.blit(label_surf, (lx, y))
                screen.blit(val_surf, (vx, y))

        # Game mode descriptions
        desc_y = start_y + len(items) * gap + 20
        if self.game_mode == 'goals_only':
            desc = "First team to reach the goal limit wins"
        elif self.game_mode == 'turns_only':
            desc = "Team with most goals after turn limit wins"
        elif self.game_mode == 'both':
            desc = "First to reach goal limit OR most goals after turn limit"
        else:
            desc = ""
        
        # Add difficulty description when singleplayer and difficulty is selected
        if self.singleplayer and self._menu_index == 2:
            difficulty_descriptions = {
                "easy": "Relaxed pace, forgiving AI",
                "medium": "Balanced challenge",
                "hard": "Quick decisions, smart AI",
                "insane": "Lightning fast, aggressive AI",
                "extreme": "Inhuman precision and speed"
            }
            desc = difficulty_descriptions.get(self.bot_difficulty, desc)
        
        if desc:
            desc_surf = small_font.render(desc, True, LIGHT_GRAY)
            desc_rect = desc_surf.get_rect(center=(SCREEN_WIDTH // 2, desc_y))
            screen.blit(desc_surf, desc_rect)

        hint = small_font.render("Up/Down to navigate • Left/Right to change • Press Enter to start", True, LIGHT_GRAY)
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, desc_y + 40))
        screen.blit(hint, hint_rect)

    def draw_audio_menu(self, screen):
        """Draw the audio settings menu"""
        title_font = pygame.font.Font(None, 64)
        item_font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Audio Settings", True, MENU_TEXT_COLOR)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 120))
        screen.blit(title, title_rect)

        # Volume values (displayed as percentages)
        master_vol_val = f"{int(self.master_volume * 100)}%"
        sfx_vol_val = f"{int(self.sfx_volume * 100)}%"
        bgm_vol_val = f"{int(self.bgm_volume * 100)}%"

        items = [
            ("Master Volume", master_vol_val),
            ("SFX Volume", sfx_vol_val),
            ("BGM Volume", bgm_vol_val),
        ]

        start_y = 200
        gap = 50
        for i, (label, val) in enumerate(items):
            is_sel = (i == self._audio_menu_index)
            color = LIGHT_BLUE if is_sel else WHITE
            label_surf = item_font.render(f"{label}", True, color)
            val_surf = item_font.render(f"{val}", True, color)
            lx = SCREEN_WIDTH // 2 - 200
            vx = SCREEN_WIDTH // 2 + 80
            y = start_y + i * gap
            screen.blit(label_surf, (lx, y))
            screen.blit(val_surf, (vx, y))

        # ESC instruction as subtitle
        subtitle_y = start_y + len(items) * gap + 30
        subtitle = small_font.render("Press ESC to return to main menu", True, LIGHT_GRAY)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, subtitle_y))
        screen.blit(subtitle, subtitle_rect)

        # Instructions
        instruction_y = subtitle_y + 40
        instruction = "Up/Down to navigate • Left/Right to adjust volume"
        hint = small_font.render(instruction, True, LIGHT_GRAY)
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, instruction_y))
        screen.blit(hint, hint_rect)
    
    def draw_save_confirmation(self, screen):
        """Draw save confirmation dialog for custom tactics"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Dialog box
        dialog_width = 500
        dialog_height = 200
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2
        
        # Dialog background
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 3)
        
        # Title
        font = pygame.font.Font(None, 36)
        title_text = font.render("Save Custom Tactics?", True, MENU_TEXT_COLOR)
        title_rect = title_text.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 40))
        screen.blit(title_text, title_rect)
        
        # Tactic name
        name_font = pygame.font.Font(None, 28)
        name_text = name_font.render(f'"{self.custom_tactics_editor.tactic_name}"', True, YELLOW)
        name_rect = name_text.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 80))
        screen.blit(name_text, name_rect)
        
        # Options - centered on same line
        small_font = pygame.font.Font(None, 24)
        options_text = "Y - Yes          N - No"
        options_surface = small_font.render(options_text, True, WHITE)
        options_rect = options_surface.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 140))
        screen.blit(options_surface, options_rect)
        
        # Color the Y and N parts
        y_text = small_font.render("Y - Yes", True, RED)
        n_text = small_font.render("N - No", True, GREEN)
        
        # Position Y and N options
        y_x = dialog_x + dialog_width // 2 - 60
        n_x = dialog_x + dialog_width // 2 + 20
        screen.blit(y_text, (y_x, dialog_y + 140))
        screen.blit(n_text, (n_x, dialog_y + 140))
    
    def draw_reset_all_confirmation(self, screen):
        """Draw reset all custom tactics confirmation dialog"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Dialog box
        dialog_width = 600
        dialog_height = 220
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2
        
        # Dialog background
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
        pygame.draw.rect(screen, RED, dialog_rect, 3)
        
        # Title
        font = pygame.font.Font(None, 36)
        title_text = font.render("Reset All Custom Tactics?", True, MENU_TEXT_COLOR)
        title_rect = title_text.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 40))
        screen.blit(title_text, title_rect)
        
        # Warning message
        warning_font = pygame.font.Font(None, 24)
        warning_text = warning_font.render("This will permanently delete all custom tactics!", True, YELLOW)
        warning_rect = warning_text.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 80))
        screen.blit(warning_text, warning_rect)
        
        # Confirmation message
        
        # Options - centered on same line
        small_font = pygame.font.Font(None, 24)
        # Color the Y and N parts
        y_text = small_font.render("Y - Yes", True, GREEN)
        n_text = small_font.render("N - No", True, RED)
        
        # Position Y and N options centered
        y_x = dialog_x + dialog_width // 2 - 60
        n_x = dialog_x + dialog_width // 2 + 20
        screen.blit(y_text, (y_x, dialog_y + 160))
        screen.blit(n_text, (n_x, dialog_y + 160))
    
    def draw_delete_confirmation(self, screen):
        """Draw delete custom tactic confirmation dialog"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Dialog box
        dialog_width = 500
        dialog_height = 200
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2
        
        # Dialog background
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
        pygame.draw.rect(screen, RED, dialog_rect, 3)
        
        # Title
        font = pygame.font.Font(None, 36)
        title_text = font.render("Delete Custom Tactic?", True, MENU_TEXT_COLOR)
        title_rect = title_text.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 40))
        screen.blit(title_text, title_rect)
        
        # Warning message
        warning_font = pygame.font.Font(None, 24)
        if hasattr(self, '_delete_tactic_key'):
            tactic_name = self._delete_tactic_key.replace('custom', 'Custom Slot ')
            warning_text = warning_font.render(f"This will permanently delete '{tactic_name}'!", True, YELLOW)
        else:
            warning_text = warning_font.render("This will permanently delete the selected tactic!", True, YELLOW)
        warning_rect = warning_text.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 80))
        screen.blit(warning_text, warning_rect)
        
        # Options - centered on same line
        small_font = pygame.font.Font(None, 24)
        # Color the Y and N parts
        y_text = small_font.render("Y - Yes", True, GREEN)
        n_text = small_font.render("N - No", True, RED)

        # Position Y and N options centered
        y_x = dialog_x + dialog_width // 2 - 60
        n_x = dialog_x + dialog_width // 2 + 20
        screen.blit(y_text, (y_x, dialog_y + 150))
        screen.blit(n_text, (n_x, dialog_y + 150))
    
    def draw_tactics_selection(self, screen):
        """Draw the tactics selection screen"""
        title_font = pygame.font.Font(None, 64)
        item_font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 24)
        
        # Title
        title = title_font.render("Select Tactics", True, MENU_TEXT_COLOR)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title, title_rect)
        
        # Current team indicator
        team_color = TEAM1_COLOR if self._tactics_team == 1 else TEAM2_COLOR
        team_text = item_font.render(f"Team {self._tactics_team} - Choose Formation", True, team_color)
        team_rect = team_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(team_text, team_rect)
        
        # 2x5 Grid layout for tactics
        start_y = 160
        row_height = 80
        col_width = 280
        left_margin = 60
        cols = 2
        rows = 5
        
        # Draw grid background
        grid_background = pygame.Rect(left_margin - 10, start_y - 10, cols * col_width + 20, rows * row_height + 20)
        pygame.draw.rect(screen, (30, 30, 30), grid_background)
        pygame.draw.rect(screen, WHITE, grid_background, 2)
        
        for i, tactic in enumerate(self._available_tactics):
            is_selected = (i == self._tactics_index)
            
            # Calculate grid position
            row = i // cols
            col = i % cols
            x_pos = left_margin + col * col_width
            y_pos = start_y + row * row_height
            
            # Draw selection highlight
            if is_selected:
                highlight_rect = pygame.Rect(x_pos - 5, y_pos - 5, col_width - 10, row_height - 10)
                pygame.draw.rect(screen, YELLOW, highlight_rect, 3)
            
            # Determine colors based on tactic type
            if tactic['type'] == 'prebuilt':
                name_color = LIGHT_BLUE
                type_color = LIGHT_GRAY
            elif tactic['type'] == 'custom':
                name_color = GREEN
                type_color = LIGHT_GRAY
            else:  # empty_custom
                name_color = LIGHT_GRAY
                type_color = GRAY
            
            # Tactic name
            name_text = item_font.render(tactic['name'], True, name_color if not is_selected else YELLOW)
            screen.blit(name_text, (x_pos, y_pos))
            
            # Tactic type indicator
            type_label = {
                'prebuilt': 'Built-in',
                'custom': 'Custom',
                'empty_custom': 'Empty Slot'
            }.get(tactic['type'], 'Unknown')
            
            type_text = small_font.render(type_label, True, type_color if not is_selected else GRAY)
            screen.blit(type_text, (x_pos, y_pos + 25))
            
            # Show additional info for custom tactics
            if tactic['type'] == 'custom':
                delete_hint = small_font.render("(X to delete)", True, RED if is_selected else (150, 0, 0))
                screen.blit(delete_hint, (x_pos, y_pos + 40))
        
        # Instructions at the bottom
        instructions_y = start_y + rows * row_height + 30
        instructions = [
            "Arrow keys/WASD - Navigate grid","ENTER/SPACE - Select","C - Customize custom tactics",
            "X - Delete selected custom tactic","R - Reset all custom tactics","ESC - Back to menu"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = small_font.render(instruction, True, LIGHT_GRAY)
            # Left-align instructions to match the tactics grid alignment
            screen.blit(inst_text, (left_margin, instructions_y + i * 20))
        
        # Draw tactic preview if a valid tactic is selected
        selected_tactic = self._available_tactics[self._tactics_index]
        if selected_tactic['type'] in ['prebuilt', 'custom']:
            preview_x = left_margin + cols * col_width + 60  # Position to the right of the grid with more space
            preview_y = start_y + 20  # Slightly below the grid start
            self.tactics_manager.draw_formation_preview(screen, selected_tactic['key'], self._tactics_team, 
                                                       preview_x, preview_y, scale=0.8)
            
            # Preview label
            preview_label = small_font.render("Formation Preview:", True, MENU_TEXT_COLOR)
            screen.blit(preview_label, (preview_x, preview_y - 25))

        # Draw delete confirmation dialog if needed
        if self._show_delete_confirmation:
            self.draw_delete_confirmation(screen)
        
        # Draw invalid tactics dialog if needed (highest priority)
        if self._show_invalid_tactics_dialog:
            self.draw_invalid_tactics_dialog(screen)
        # Draw reset all confirmation dialog if needed  
        elif self._show_reset_all_confirmation:
            self.draw_reset_all_confirmation(screen)
    
    def draw_unsaved_changes_dialog(self, screen):
        """Draw unsaved changes confirmation dialog"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Dialog box
        dialog_width = 450
        dialog_height = 180
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2
        
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 2)
        
        # Text
        font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 24)
        
        title_text = font.render("Unsaved Changes Detected!", True, YELLOW)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, dialog_y + 40))
        screen.blit(title_text, title_rect)
        
        question_text = small_font.render("Do you want to save before exiting?", True, WHITE)
        question_rect = question_text.get_rect(center=(SCREEN_WIDTH // 2, dialog_y + 80))
        screen.blit(question_text, question_rect)
        
        # Options - centered on same line
        small_font = pygame.font.Font(None, 24)
        # Color the Y and N parts
        y_text = small_font.render("Y - Yes", True, RED)
        n_text = small_font.render("N - No", True, GREEN)
        
        # Position Y and N options centered
        y_x = dialog_x + dialog_width // 2 - 60
        n_x = dialog_x + dialog_width // 2 + 20
        screen.blit(y_text, (y_x, dialog_y + 120))
        screen.blit(n_text, (n_x, dialog_y + 120))
    
    def draw_invalid_tactics_dialog(self, screen):
        """Draw invalid tactics notification dialog"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Dialog box (larger to accommodate list)
        dialog_width = 600
        max_dialog_height = 400
        base_height = 150
        item_height = 25
        total_items = len(self._invalid_tactics_list)
        dialog_height = min(max_dialog_height, base_height + total_items * item_height)
        
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2
        
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, (40, 40, 40), dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 2)
        
        # Text
        font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 24)
        
        title_text = font.render("Invalid Tactics Removed", True, RED)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, dialog_y + 30))
        screen.blit(title_text, title_rect)
        
        # List of removed tactics
        y_offset = dialog_y + 70
        if self._invalid_tactics_list:
            header_text = small_font.render("The following tactics were removed due to invalidity:", True, WHITE)
            header_rect = header_text.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            screen.blit(header_text, header_rect)
            y_offset += 30
            
            for invalid in self._invalid_tactics_list:
                tactic_text = small_font.render(f"• {invalid['name']} ({invalid['type']})", True, LIGHT_GRAY)
                screen.blit(tactic_text, (dialog_x + 20, y_offset))
                y_offset += item_height
        
        # Instructions
        instruction_y = dialog_y + dialog_height - 40
        instruction_text = small_font.render("Press any key to continue", True, YELLOW)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, instruction_y))
        screen.blit(instruction_text, instruction_rect)
    
    def start_coin_flip(self):
        """Start the coin flip animation with enhanced randomness"""
        import random
        import time
        
        # Use multiple entropy sources for better randomness
        current_time = pygame.time.get_ticks()
        system_time = time.time()
        
        # Combine multiple random sources to ensure divergent results
        # Use current game time, system time, and random state for maximum entropy
        random.seed(int(current_time * system_time) % 1000000)
        
        # Generate random result with additional entropy from timing
        base_random = random.randint(1, 2)
        time_entropy = int((current_time + system_time * 1000) % 10)
        
        # Use both random choice and time-based entropy for final decision
        if time_entropy % 2 == 0:
            self.coin_flip_result = base_random
        else:
            self.coin_flip_result = 3 - base_random  # Flip the result (1->2, 2->1)
        
        # Reset random state to avoid affecting other game randomness
        random.seed(None)
        
        # Initialize animation state
        self.coin_flip_active = True
        self.coin_flip_start_time = current_time
        self.coin_flip_rotation = 0
        self.coin_flip_winner_determined = False
        self.coin_flip_result_display_time = 0
        
        # Set game state to coin flip
        self.game_state = GAME_STATE_COIN_FLIP
        self.update_music()
    
    def update_coin_flip(self):
        """Update coin flip animation"""
        if not self.coin_flip_active and not self.coin_flip_winner_determined:
            return
        
        current_time = pygame.time.get_ticks()
        
        if self.coin_flip_active:
            # Animation phase
            elapsed = current_time - self.coin_flip_start_time
            
            # Update rotation
            self.coin_flip_rotation += COIN_FLIP_ROTATION_SPEED
            if self.coin_flip_rotation >= 360:
                self.coin_flip_rotation = 0
            
            # Check if animation should end
            if elapsed >= COIN_FLIP_DURATION:
                self.complete_coin_flip()
        elif self.coin_flip_winner_determined and hasattr(self, 'coin_flip_result_display_time'):
            # Result display phase
            if current_time >= self.coin_flip_result_display_time:
                self._actually_start_game()
    
    def complete_coin_flip(self):
        """Complete the coin flip and start the actual game"""
        if not self.coin_flip_winner_determined:
            # First time completing - show result for 2 seconds
            self.coin_flip_active = False
            self.coin_flip_winner_determined = True
            # Add a 2-second delay to show the result
            self.coin_flip_result_display_time = pygame.time.get_ticks() + 2000  # Show result for 2 seconds
        else:
            # Result already shown, now start the game
            self._actually_start_game()
    
    def _actually_start_game(self):
        """Actually start the game after coin flip"""
        # Set the winning team to go first
        self.current_team = self.coin_flip_result
        
        # Reinitialize players with selected tactics
        self.init_players()
        
        # Set game state to playing
        self.game_state = GAME_STATE_PLAYING
        self.update_music()
        self.current_phase = PHASE_SELECT_PLAYER
        
        # Ensure players are reset
        for p in self.team1_players + self.team2_players:
            p.reset_turn()
        
        # Set up the turn queue with winning team first
        self.turn_queue = [self.coin_flip_result, 3 - self.coin_flip_result]  # 3-team gives other team
        self.queue_index = 0
        self.teams_played_this_turn.clear()
    
    def draw_coin_flip(self, screen):
        """Draw the coin flip animation"""
        # First, render the playground in the background
        self.draw_game_world(screen, 1.0, 0, 0)
        
        # Add semi-transparent overlay with LIGHT_BLUE color at 40% opacity
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        light_blue_with_alpha = (*LIGHT_BLUE, int(255 * 0.4))  # 40% opacity
        overlay.fill(light_blue_with_alpha)
        screen.blit(overlay, (0, 0))
        
        # Title
        title_font = pygame.font.Font(None, 64)
        title_text = title_font.render("COIN FLIP", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
        screen.blit(title_text, title_rect)
        
        # Subtitle
        subtitle_font = pygame.font.Font(None, 36)
        if self.coin_flip_active:
            subtitle_text = subtitle_font.render("Determining who goes first...", True, LIGHT_GRAY)
        else:
            subtitle_text = subtitle_font.render("Result:", True, LIGHT_GRAY)
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
        screen.blit(subtitle_text, subtitle_rect)
        
        # Draw coin
        coin_center_x = SCREEN_WIDTH // 2
        coin_center_y = SCREEN_HEIGHT // 2 - 50  # Moved up to make room for text
        
        if self.coin_flip_active:
            # Animate the coin flipping
            # Use sine wave to create a flipping effect
            flip_scale = abs(math.sin(math.radians(self.coin_flip_rotation * 4)))
            current_coin_width = int(COIN_SIZE * flip_scale)
            
            # Determine which side to show based on rotation
            show_heads = (self.coin_flip_rotation % 180) < 90
            
            # Draw coin shadow
            shadow_offset = 5
            pygame.draw.ellipse(screen, GRAY, 
                              (coin_center_x - current_coin_width//2 + shadow_offset, 
                               coin_center_y - COIN_SIZE//2 + shadow_offset, 
                               current_coin_width, COIN_SIZE))
            
            # Draw coin
            if show_heads:
                # Heads - Team 1 color (Blue)
                pygame.draw.ellipse(screen, TEAM1_COLOR, 
                                  (coin_center_x - current_coin_width//2, 
                                   coin_center_y - COIN_SIZE//2, 
                                   current_coin_width, COIN_SIZE))
                pygame.draw.ellipse(screen, WHITE, 
                                  (coin_center_x - current_coin_width//2, 
                                   coin_center_y - COIN_SIZE//2, 
                                   current_coin_width, COIN_SIZE), 3)
                
                # Draw "1" in center
                if current_coin_width > 20:  # Only draw if coin is wide enough
                    coin_font = pygame.font.Font(None, int(48 * flip_scale))
                    coin_text = coin_font.render("1", True, WHITE)
                    coin_text_rect = coin_text.get_rect(center=(coin_center_x, coin_center_y))
                    screen.blit(coin_text, coin_text_rect)
            else:
                # Tails - Team 2 color (Red)
                pygame.draw.ellipse(screen, TEAM2_COLOR, 
                                  (coin_center_x - current_coin_width//2, 
                                   coin_center_y - COIN_SIZE//2, 
                                   current_coin_width, COIN_SIZE))
                pygame.draw.ellipse(screen, WHITE, 
                                  (coin_center_x - current_coin_width//2, 
                                   coin_center_y - COIN_SIZE//2, 
                                   current_coin_width, COIN_SIZE), 3)
                
                # Draw "2" in center
                if current_coin_width > 20:  # Only draw if coin is wide enough
                    coin_font = pygame.font.Font(None, int(48 * flip_scale))
                    coin_text = coin_font.render("2", True, WHITE)
                    coin_text_rect = coin_text.get_rect(center=(coin_center_x, coin_center_y))
                    screen.blit(coin_text, coin_text_rect)
        else:
            # Show final result - paused for 2 seconds
            winner_color = TEAM1_COLOR if self.coin_flip_result == 1 else TEAM2_COLOR
            
            # Draw coin shadow
            shadow_offset = 5
            pygame.draw.ellipse(screen, GRAY, 
                              (coin_center_x - COIN_SIZE//2 + shadow_offset, 
                               coin_center_y - COIN_SIZE//2 + shadow_offset, 
                               COIN_SIZE, COIN_SIZE))
            
            # Draw final coin
            pygame.draw.ellipse(screen, winner_color, 
                              (coin_center_x - COIN_SIZE//2, 
                               coin_center_y - COIN_SIZE//2, 
                               COIN_SIZE, COIN_SIZE))
            pygame.draw.ellipse(screen, WHITE, 
                              (coin_center_x - COIN_SIZE//2, 
                               coin_center_y - COIN_SIZE//2, 
                               COIN_SIZE, COIN_SIZE), 4)  # Thicker border for final result
            
            # Draw winning team number
            coin_font = pygame.font.Font(None, 60)  # Larger font for final result
            coin_text = coin_font.render(str(self.coin_flip_result), True, WHITE)
            coin_text_rect = coin_text.get_rect(center=(coin_center_x, coin_center_y))
            screen.blit(coin_text, coin_text_rect)
            
            # Show result text in team color
            result_font = pygame.font.Font(None, 52)  # Larger and more prominent
            result_text = result_font.render(f"Team {self.coin_flip_result} goes first!", True, winner_color)
            result_rect = result_text.get_rect(center=(SCREEN_WIDTH // 2, coin_center_y + 120))
            screen.blit(result_text, result_rect)
            
            # Add a subtle glow effect around the result text
            glow_font = pygame.font.Font(None, 54)
            for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
                glow_text = glow_font.render(f"Team {self.coin_flip_result} goes first!", True, (winner_color[0]//3, winner_color[1]//3, winner_color[2]//3))
                glow_rect = glow_text.get_rect(center=(SCREEN_WIDTH // 2 + offset[0], coin_center_y + 120 + offset[1]))
                screen.blit(glow_text, glow_rect)
            
            # Redraw the main text on top
            screen.blit(result_text, result_rect)
        
        # Instructions
        instruction_font = pygame.font.Font(None, 24)
        if self.coin_flip_active:
            instruction_text = instruction_font.render("Press any key to skip animation", True, LIGHT_GRAY)
        else:
            instruction_text = instruction_font.render("Match starting soon", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        screen.blit(instruction_text, instruction_rect)