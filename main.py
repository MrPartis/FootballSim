import pygame
import sys
import os
try:
    from PIL import Image  # Optional for animated GIF support
except Exception:
    Image = None
from constants import *
from game_manager import GameManager

class MiniFootballGame:
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        
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
        """Try to load an animated GIF for the pause screen.
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
            im = Image.open(gif_path)
            # Extract frames
            self.pause_frames = []
            self.pause_frame_durations = []
            for frame_idx in range(0, getattr(im, 'n_frames', 1)):
                im.seek(frame_idx)
                frame = im.convert('RGBA')
                size = frame.size
                data = frame.tobytes()
                # Pygame expects a literal format string; we always convert to RGBA
                surf = pygame.image.fromstring(data, size, 'RGBA')
                self.pause_frames.append(surf)
                # Duration per frame in ms; default 80 if missing
                dur = frame.info.get('duration', im.info.get('duration', 80))
                if not isinstance(dur, int) or dur <= 0:
                    dur = 80
                self.pause_frame_durations.append(dur)
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
                        # Toggle pause - Play pause SFX (if available) and start looping pause audio
                        try:
                            self.game_manager.sounds.play_pause()
                            self.game_manager.sounds.start_pause_audio()
                        except Exception:
                            pass
                        self.game_manager.game_state = GAME_STATE_PAUSED
                        self.game_manager.update_music()
                    elif self.game_manager.game_state == GAME_STATE_PAUSED:
                        # Resume game - Stop pause audio and resume game
                        try:
                            self.game_manager.sounds.stop_pause_audio()
                        except Exception:
                            pass
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
        
        if self.game_manager.game_state == GAME_STATE_PAUSED:
            # Ensure pause audio keeps playing
            self.game_manager.sounds.ensure_pause_audio_playing()
    
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
    
    def draw_pause_overlay(self):
        """Draw pause overlay"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 170, 250))
        self.screen.blit(overlay, (0, 0))
        
        # Pause text
        font = pygame.font.Font(None, 72)
        pause_text = font.render("PAUSED", True, WHITE)
        pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(pause_text, pause_rect)
        
        # Instructions
        small_font = pygame.font.Font(None, 36)
        instruction_text = small_font.render("Press ESC to resume", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(instruction_text, instruction_rect)

        # Animated GIF if available
        if self.pause_frames:
            now = pygame.time.get_ticks()
            # Advance frame based on duration while paused
            if now - self.pause_last_tick >= self.pause_frame_durations[self.pause_frame_index]:
                self.pause_last_tick = now
                self.pause_frame_index = (self.pause_frame_index + 1) % len(self.pause_frames)

            frame = self.pause_frames[self.pause_frame_index]
            # Scale frame to a reasonable size if too big
            max_w, max_h = SCREEN_WIDTH // 3, SCREEN_HEIGHT // 3
            fw, fh = frame.get_width(), frame.get_height()
            scale = min(max_w / fw, max_h / fh, 1.0)
            if scale < 1.0:
                frame = pygame.transform.smoothscale(frame, (int(fw * scale), int(fh * scale)))
            # Center under the PAUSED text
            fx = (SCREEN_WIDTH - frame.get_width()) // 2
            fy = pause_rect.bottom + 20
            self.screen.blit(frame, (fx, fy))
    
    def run(self):        
        while self.running:
            # Handle events
            self.handle_events()
            
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