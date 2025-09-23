import pygame
import sys
import os
try:
    from PIL import Image  # For animated GIF support in pause screen
except Exception:
    Image = None
from constants import *
from game_manager import GameManager

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
        
        # Game running flag
        self.running = True

        # Pause animation state
        self.pause_frames = []           # list[Surface]
        self.pause_frame_durations = []  # list[int ms]
        self.pause_frame_index = 0
        self.pause_last_tick = 0
        self._load_pause_animation()

    def _load_pause_animation(self):
        """Load animated GIF for pause screen with memory optimizations.
        Looks for assets/pause.gif or pause.gif. If PIL isn't available or file missing,
        falls back to no animation (text-only overlay).
        """
        candidates = [
            os.path.join(os.path.dirname(__file__), 'assets', 'pause.gif'),
            os.path.join(os.path.dirname(__file__), 'pause.gif'),
        ]
        gif_path = next((p for p in candidates if os.path.exists(p)), None)
        if not gif_path or Image is None:
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
                    elif self.game_manager.game_state == GAME_STATE_PAUSED:
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
                    elif self.game_manager.game_state == GAME_STATE_COIN_FLIP:
                        # Skip coin flip animation or result display
                        if self.game_manager.coin_flip_active:
                            self.game_manager.complete_coin_flip()
                        elif self.game_manager.coin_flip_winner_determined:
                            self.game_manager._actually_start_game()
                    else:
                        # For other states (MENU, TACTICS, CUSTOM_TACTICS), let game manager handle ESC
                        self.game_manager.handle_keypress(event.key)
                
                elif event.key == pygame.K_r:
                    if self.game_manager.game_state == GAME_STATE_GAME_OVER:
                        self.game_manager.restart_game()
                    else:
                        # For other states, let game manager handle R key
                        self.game_manager.handle_keypress(event.key)
                
                # Game-specific controls
                else:
                    # During coin flip, any key skips the animation or result display
                    if self.game_manager.game_state == GAME_STATE_COIN_FLIP:
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
            
        # Always update the game manager (it handles state internally)
        self.game_manager.update()
    
    def draw(self):
        """Draw everything to the screen"""
        # Clear screen
        self.screen.fill(BLACK)
        
        # Draw game
        self.game_manager.draw(self.screen)
        
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
        """Draw pause overlay with optimized GIF animation"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 170, 250))
        self.screen.blit(overlay, (0, 0))
        
        # Calculate total height needed for centering the entire complex
        font = pygame.font.Font(None, 72)
        small_font = pygame.font.Font(None, 36)
        
        pause_text = font.render("PAUSED", True, WHITE)
        instruction_text = small_font.render("Press ESC to resume", True, WHITE)
        
        # Calculate total complex height
        total_height = pause_text.get_height()  # PAUSED text
        total_height += 20  # Gap between PAUSED and instructions
        total_height += instruction_text.get_height()  # Instructions text
        
        # Add GIF height if available
        gif_height = 0
        if self.pause_frames and self.pause_frame_durations:
            gif_height = self.pause_frames[0].get_height()
            total_height += 30  # Gap between instructions and GIF
            total_height += gif_height
        
        # Calculate starting Y position to center the entire complex
        start_y = (SCREEN_HEIGHT - total_height) // 2
        
        # Draw PAUSED text
        pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, start_y + pause_text.get_height() // 2))
        self.screen.blit(pause_text, pause_rect)
        
        # Draw instructions
        instruction_y = pause_rect.bottom + 20
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, instruction_y + instruction_text.get_height() // 2))
        self.screen.blit(instruction_text, instruction_rect)

        # Draw optimized animated GIF if available
        if self.pause_frames and self.pause_frame_durations:
            now = pygame.time.get_ticks()
            # Advance frame based on duration while paused
            if now - self.pause_last_tick >= self.pause_frame_durations[self.pause_frame_index]:
                self.pause_last_tick = now
                self.pause_frame_index = (self.pause_frame_index + 1) % len(self.pause_frames)

            frame = self.pause_frames[self.pause_frame_index]
            # Center the GIF below the instructions
            gif_y = instruction_rect.bottom + 30
            fx = (SCREEN_WIDTH - frame.get_width()) // 2
            self.screen.blit(frame, (fx, gif_y))
    
    def run(self):        
        while self.running:
            # Handle events
            self.handle_events()
            
            # Check if we need to enter pause loop
            if self.game_manager.game_state == GAME_STATE_PAUSED:
                self.pause_loop()
                continue
            
            # Update
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
        game = MiniFootballGame()
        game.run()
    except Exception as e:
        print(f"Error running game: {e}")
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()