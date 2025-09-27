import pygame
import sys
import os
try:
    from PIL import Image  # For animated GIF support in pause screen
except Exception:
    Image = None
from constants import *
from game_manager import GameManager
from resource_manager import get_resource_path, get_asset_path

class MiniFootballGame:
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        
        # Enable key repeat for smooth menu navigation
        # First arg: delay before repeating (ms), Second arg: repeat interval (ms)
        pygame.key.set_repeat(300, 50)  # 300ms initial delay, then 50ms between repeats
        
        # Set up display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mini Football - Turn Based")
        
        # Set up clock
        self.clock = pygame.time.Clock()
        
        # Initialize game manager
        self.game_manager = GameManager()
        
        # Sync initial volume settings
        self.game_manager.sync_volume_settings()
        
        # Game running flag
        self.running = True

        # Pause animation state
        self.pause_frames = []           # list[Surface]
        self.pause_frame_durations = []  # list[int ms]
        self.pause_frame_index = 0
        self.pause_last_tick = 0
        self._load_pause_animation()
        
        # Pause menu state for volume controls
        self.pause_menu_index = 0  # 0=Master Volume, 1=SFX Volume, 2=BGM Volume
        self.show_pause_volume_controls = False
        
        # Key repeat timing for pause menu (matches main menu behavior)
        self._pause_last_key_time = {'navigation': 0, 'value_change': 0}
        self._pause_key_repeat_delay = {'navigation': 200, 'value_change': 50}  # ms

    def _can_repeat_pause_key(self, key_type: str) -> bool:
        """Check if enough time has passed to allow key repeat for pause menu"""
        now = pygame.time.get_ticks()
        return now - self._pause_last_key_time[key_type] >= self._pause_key_repeat_delay[key_type]
    
    def _update_pause_key_repeat_time(self, key_type: str):
        """Update the last key press time for pause menu"""
        self._pause_last_key_time[key_type] = pygame.time.get_ticks()

    def _reload_audio_config(self):
        """Reload audio configuration from storage to ensure synchronization (non-blocking)"""
        try:
            from config_manager import get_audio_config
            from constants import DEFAULT_MASTER_VOLUME, DEFAULT_SFX_VOLUME, DEFAULT_BGM_VOLUME
            
            audio_config = get_audio_config()
            self.game_manager.master_volume = audio_config.get('master_volume', DEFAULT_MASTER_VOLUME)
            self.game_manager.sfx_volume = audio_config.get('sfx_volume', DEFAULT_SFX_VOLUME)
            self.game_manager.bgm_volume = audio_config.get('bgm_volume', DEFAULT_BGM_VOLUME)
            
            # Apply the reloaded settings immediately
            self.game_manager.sync_volume_settings()
        except Exception as e:
            # Silently continue - pause functionality shouldn't be affected by sync issues
            print(f"Warning: Failed to reload audio configuration: {e}")

    def _save_pause_config(self):
        """Save current pause menu configuration for persistence (isolated from resume logic)"""
        try:
            # Save audio configuration to ensure persistence
            self.game_manager.save_audio_configuration()
            print(f"Configuration saved: Master={int(self.game_manager.master_volume*100)}%, SFX={int(self.game_manager.sfx_volume*100)}%, BGM={int(self.game_manager.bgm_volume*100)}%")
        except Exception as e:
            # Silently continue - resume functionality shouldn't be affected by save issues
            print(f"Warning: Failed to save pause configuration: {e}")

    def _adjust_pause_volume(self, delta):
        """Adjust volume based on current pause menu selection - matches main menu behavior"""
        if self.pause_menu_index == 0:  # Master Volume
            self.game_manager.master_volume = max(0.0, min(1.0, self.game_manager.master_volume + delta))
            # Apply changes immediately
            self.game_manager.sync_volume_settings()
            self.game_manager.save_audio_configuration()
        elif self.pause_menu_index == 1:  # SFX Volume  
            self.game_manager.sfx_volume = max(0.0, min(1.0, self.game_manager.sfx_volume + delta))
            # Apply changes immediately
            self.game_manager.sync_volume_settings()
            self.game_manager.save_audio_configuration()
        elif self.pause_menu_index == 2:  # BGM Volume
            self.game_manager.bgm_volume = max(0.0, min(1.0, self.game_manager.bgm_volume + delta))
            # Apply changes immediately
            self.game_manager.sync_volume_settings()
            self.game_manager.save_audio_configuration()

    def _load_pause_animation(self):
        """Load animated GIF for pause screen with memory optimizations.
        Looks for pause.gif in assets folder. If PIL isn't available or file missing,
        falls back to no animation (text-only overlay).
        """
        gif_path = get_asset_path('pause.gif')
        if not os.path.exists(gif_path) or Image is None:
            return
        try:
            with Image.open(gif_path) as im:  # Use context manager for better memory management
                # Load all frames for complete loop animation
                total_frames = getattr(im, 'n_frames', 1)
                
                self.pause_frames = []
                self.pause_frame_durations = []
                
                for frame_idx in range(total_frames):
                    im.seek(frame_idx)
                    frame = im.convert('RGBA')
                    
                    # Optimize frame size for memory (limit to reasonable dimensions)
                    max_size = 200  # Maximum dimension for memory efficiency
                    if frame.width > max_size or frame.height > max_size:
                        ratio = min(max_size / frame.width, max_size / frame.height)
                        new_size = (int(frame.width * ratio), int(frame.height * ratio))
                        frame = frame.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Convert to pygame surface
                    data = frame.tobytes()
                    surf = pygame.image.fromstring(data, frame.size, 'RGBA')
                    self.pause_frames.append(surf)
                    
                    # Get frame duration with optimization
                    dur = frame.info.get('duration', im.info.get('duration', 100))
                    if not isinstance(dur, int) or dur <= 0:
                        dur = 100
                    # Cap duration to prevent too slow animations
                    self.pause_frame_durations.append(min(dur, 300))
                    
                self.pause_frame_index = 0
                self.pause_last_tick = pygame.time.get_ticks()
        except Exception:
            # On any failure, just skip animation
            self.pause_frames = []
            self.pause_frame_durations = []
    
    def handle_events(self):
        """Handle all pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                # Global controls
                if event.key == pygame.K_ESCAPE:
                    if self.game_manager.game_state == GAME_STATE_GAME_OVER:
                        self.running = False
                    elif self.game_manager.game_state == GAME_STATE_PLAYING:
                        # Toggle pause - Pause existing sounds first, then play pause audio
                        try:
                            # First pause all currently playing sound effects
                            self.game_manager.sounds.pause_all_sounds()
                            # Then play pause SFX and start pause audio loop
                            self.game_manager.sounds.play_pause()
                            self.game_manager.sounds.start_pause_audio()
                        except Exception:
                            pass
                        # Start tracking pause time for animations
                        self.game_manager.start_pause_timing()
                        self.game_manager.game_state = GAME_STATE_PAUSED
                        self.game_manager.update_music()
                        # Reset pause menu to first option
                        self.pause_menu_index = 0
                        # Reload audio configuration after pause state is set (isolated from core logic)
                        self._reload_audio_config()
                    elif self.game_manager.game_state == GAME_STATE_PAUSED:
                        # Save current configuration before resuming
                        self._save_pause_config()
                        # Resume game - Stop pause audio and resume game (moved from ESC handler)
                        try:
                            self.game_manager.sounds.stop_pause_audio()
                            # Resume all sounds including goal effects
                            self.game_manager.sounds.resume_all_sounds()
                        except Exception:
                            pass
                        # End tracking pause time for animations
                        self.game_manager.end_pause_timing()
                        self.game_manager.game_state = GAME_STATE_PLAYING
                        self.game_manager.update_music()
                    elif self.game_manager.game_state == GAME_STATE_COIN_FLIP:
                        # Skip coin flip animation or result display
                        if self.game_manager.coin_flip_active:
                            self.game_manager.complete_coin_flip()
                        elif self.game_manager.coin_flip_winner_determined:
                            self.game_manager._actually_start_game()
                    else:
                        # For other states (MENU, TACTICS, CUSTOM_TACTICS), let game manager handle ESC
                        self.game_manager.handle_keypress(event.key)
                
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    if self.game_manager.game_state == GAME_STATE_PAUSED:
                        if self._can_repeat_pause_key('navigation'):
                            self.pause_menu_index = (self.pause_menu_index - 1) % 3
                            self._update_pause_key_repeat_time('navigation')
                    else:
                        self.game_manager.handle_keypress(event.key)
                        
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    if self.game_manager.game_state == GAME_STATE_PAUSED:
                        if self._can_repeat_pause_key('navigation'):
                            self.pause_menu_index = (self.pause_menu_index + 1) % 3
                            self._update_pause_key_repeat_time('navigation')
                    else:
                        self.game_manager.handle_keypress(event.key)
                        
                elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    if self.game_manager.game_state == GAME_STATE_PAUSED:
                        # All menu items are volume controls now
                        if self._can_repeat_pause_key('value_change'):
                            self._adjust_pause_volume(-0.01)  # Fine increment like main menu
                            self._update_pause_key_repeat_time('value_change')
                    else:
                        self.game_manager.handle_keypress(event.key)
                        
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    if self.game_manager.game_state == GAME_STATE_PAUSED:
                        # All menu items are volume controls now
                        if self._can_repeat_pause_key('value_change'):
                            self._adjust_pause_volume(0.01)  # Fine increment like main menu
                            self._update_pause_key_repeat_time('value_change')
                    else:
                        self.game_manager.handle_keypress(event.key)
                        
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if self.game_manager.game_state == GAME_STATE_PAUSED:
                        # Save current configuration before resuming
                        self._save_pause_config()
                        # Resume game - Stop pause audio and resume game
                        try:
                            self.game_manager.sounds.stop_pause_audio()
                            self.game_manager.sounds.resume_all_sounds()
                        except Exception:
                            pass
                        self.game_manager.end_pause_timing()
                        self.game_manager.game_state = GAME_STATE_PLAYING
                        self.game_manager.update_music()
                    else:
                        self.game_manager.handle_keypress(event.key)
                        
                elif event.key == pygame.K_r:
                    if self.game_manager.game_state == GAME_STATE_GAME_OVER:
                        self.game_manager.restart_game()
                    else:
                        self.game_manager.handle_keypress(event.key)
                
                # Game-specific controls
                else:
                    # During pause, don't pass keys to game manager (handled above)
                    if self.game_manager.game_state == GAME_STATE_PAUSED:
                        pass  # Already handled by specific key handlers above
                    # During coin flip, any key skips the animation or result display
                    elif self.game_manager.game_state == GAME_STATE_COIN_FLIP:
                        if self.game_manager.coin_flip_active:
                            self.game_manager.complete_coin_flip()
                        elif self.game_manager.coin_flip_winner_determined:
                            self.game_manager._actually_start_game()
                    else:
                        self.game_manager.handle_keypress(event.key)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Handle mouse events for custom tactics editor
                if self.game_manager.game_state == GAME_STATE_CUSTOM_TACTICS:
                    if event.button == 1:  # Left click
                        self.game_manager.custom_tactics_editor.handle_mouse_click(event.pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                # Handle mouse release for custom tactics editor
                if self.game_manager.game_state == GAME_STATE_CUSTOM_TACTICS:
                    if event.button == 1:  # Left click release
                        self.game_manager.custom_tactics_editor.handle_mouse_release()
            
            elif event.type == pygame.MOUSEMOTION:
                # Handle mouse drag for custom tactics editor
                if self.game_manager.game_state == GAME_STATE_CUSTOM_TACTICS:
                    self.game_manager.custom_tactics_editor.handle_mouse_drag(event.pos)
                    self.game_manager.custom_tactics_editor.handle_mouse_move(event.pos)
    
    def update(self):
        """Update game state"""
        # Initialize music on first frame (after pygame is fully ready)
        if not self.game_manager._music_initialized:
            self.game_manager.update_music()
            self.game_manager._music_initialized = True
        
        # Only update game logic if not paused
        if self.game_manager.game_state != GAME_STATE_PAUSED:
            self.game_manager.update()
        else:
            # Ensure pause audio keeps playing during pause
            try:
                self.game_manager.sounds.ensure_pause_audio_playing()
            except Exception:
                pass
    
    def draw(self):
        """Draw everything to the screen"""
        # Clear screen
        self.screen.fill(BLACK)
        
        # Draw game
        self.game_manager.draw(self.screen)
        
        # Draw pause overlay if paused
        if self.game_manager.game_state == GAME_STATE_PAUSED:
            self.draw_pause_overlay()
        
        # Update display
        pygame.display.flip()
    
    def pause_loop(self):
        """Infinite loop that runs while game is paused - freezes all game logic"""
        while self.game_manager.game_state == GAME_STATE_PAUSED and self.running:
            # Handle pause-specific events only
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Resume game - Stop pause audio and resume game
                        try:
                            self.game_manager.sounds.stop_pause_audio()
                            # Resume all sounds including goal effects
                            self.game_manager.sounds.resume_all_sounds()
                        except Exception:
                            pass
                        # End tracking pause time for animations
                        self.game_manager.end_pause_timing()
                        self.game_manager.game_state = GAME_STATE_PLAYING
                        self.game_manager.update_music()
                        return  # Exit pause loop
            
            # Draw the frozen game state with pause overlay
            self.screen.fill(BLACK)
            
            # Draw the game world exactly as it was when paused
            self.game_manager.draw(self.screen)
            
            # Draw pause overlay on top
            self.draw_pause_overlay()
            
            # Update display
            pygame.display.flip()
            
            # Control frame rate during pause
            self.clock.tick(FPS)
            
            # Ensure pause audio keeps playing
            try:
                self.game_manager.sounds.ensure_pause_audio_playing()
            except Exception:
                pass
    
    def draw_pause_overlay(self):
        """Draw pause overlay with volume controls"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 170, 250))
        self.screen.blit(overlay, (0, 0))
        
        # Fonts
        font = pygame.font.Font(None, 72)
        item_font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 28)
        
        # PAUSED title
        pause_text = font.render("PAUSED", True, WHITE)
        pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, 120))
        self.screen.blit(pause_text, pause_rect)
        
        # Notify for resume
        instruction_text = small_font.render("Press Esc to resume", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, 160))
        self.screen.blit(instruction_text, instruction_rect)
        
        # Menu items
        menu_items = [
            f"Master Volume: {int(self.game_manager.master_volume * 100)}%",
            f"SFX Volume: {int(self.game_manager.sfx_volume * 100)}%", 
            f"BGM Volume: {int(self.game_manager.bgm_volume * 100)}%"
        ]
        
        start_y = 220
        gap = 45
        
        for i, item in enumerate(menu_items):
            color = YELLOW if i == self.pause_menu_index else WHITE
            text = item_font.render(item, True, color)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * gap))
            self.screen.blit(text, text_rect)
            
            # Add selection indicator
            if i == self.pause_menu_index:
                indicator = item_font.render(">", True, YELLOW)
                indicator_rect = indicator.get_rect(right=text_rect.left - 20, centery=text_rect.centery)
                self.screen.blit(indicator, indicator_rect)
        
        # Draw animated GIF if available
        if self.pause_frames and self.pause_frame_durations:
            now = pygame.time.get_ticks()
            if now - self.pause_last_tick >= self.pause_frame_durations[self.pause_frame_index]:
                self.pause_last_tick = now
                self.pause_frame_index = (self.pause_frame_index + 1) % len(self.pause_frames)

            frame = self.pause_frames[self.pause_frame_index]
            gif_y = start_y + len(menu_items) * gap + 30
            fx = (SCREEN_WIDTH - frame.get_width()) // 2
            fy = gif_y
            if fy + frame.get_height() <= SCREEN_HEIGHT:
                self.screen.blit(frame, (fx, fy))
            self.screen.blit(frame, (fx, gif_y))
    
    def run(self):        
        while self.running:
            # Handle events
            self.handle_events()
            
            # Update (game manager handles pause state internally)
            self.update()
            
            # Draw
            self.draw()
            
            # Control frame rate
            self.clock.tick(FPS)
        
        # Clean up
        try:
            # Stop any playing pause audio
            self.game_manager.sounds.stop_pause_audio()
        except Exception:
            pass
        pygame.quit()

def main():
    """Main function"""
    try:
        print("Creating MiniFootballGame instance...")
        game = MiniFootballGame()
        print("MiniFootballGame created successfully, starting run...")
        game.run()
    except RecursionError as e:
        print(f"Recursion error: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
    except Exception as e:
        print(f"Error running game: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()