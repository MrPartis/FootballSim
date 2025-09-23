import io
import math
import struct
import time
from typing import Optional

import pygame
import os
from constants import SOUND_DIR_NAME, SOUND_FILES


class SoundManager:
    """Lightweight sound helper that generates small WAV tones at runtime.

    - No external files or numpy required.
    - Fails safe if audio device/mixer is not available.
    - Simple rate-limiting to avoid spam on physics iterations.
    """

    def __init__(self):
        self.enabled = False
        self.sample_rate = 44100
        self._last_collision_ms = 0
        self._collision_cooldown_ms = 80

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)
            self.enabled = True
        except Exception:
            # No audio device or mixer failed; keep sounds disabled
            self.enabled = False

        # Try load external assets first, else synthesize
        self._collision_sound = self._try_load_external("collision")
        self._goal_sound = self._try_load_external("goal")
        self._pause_sound = self._try_load_external("pause")
        self._pause_audio = self._try_load_external("pause_audio")
        
        # Load background music files
        self._menu_music = self._try_load_music_file("menu.mp3")
        self._ingame_music = self._try_load_music_file("ingame.mp3")
        
        # Load ending music files
        self._end_music = self._try_load_music_file("end.mp3")  # Generic ending
        self._end_win_music = self._try_load_music_file("end_win.mp3")  # Singleplayer win
        self._end_lose_music = self._try_load_music_file("end_lose.mp3")  # Singleplayer lose
        self._end_tie_music = self._try_load_music_file("end_tie.mp3")  # Tie game
        self._end_2p_music = self._try_load_music_file("end_2p.mp3")  # Multiplayer ending
        
        # Track pause audio channel for stopping
        self._pause_audio_channel = None
        
        # Track which sound channels are paused by us (to avoid pausing pause audio)
        self._paused_channels = set()
        
        # Track current music state
        self._current_music_type = None  # 'menu', 'ingame', or None
        self._music_paused = False

        # Generate fallback tones only if external sounds are missing
        if not self._collision_sound:
            self._collision_tone_soft = self._build_tone(freq=420, ms=55, volume=0.45)
            self._collision_tone_hard = self._build_tone(freq=700, ms=45, volume=0.55)
        else:
            self._collision_tone_soft = self._collision_tone_hard = None

        self._goal_fanfare = None if self._goal_sound else self._build_fanfare()
        self._pause_tone = None if self._pause_sound else self._build_tone(freq=520, ms=90, volume=0.5)

    def _sine_wave(self, freq: float, length_ms: int, volume: float = 0.5) -> bytes:
        """Generate 16-bit PCM mono sine wave bytes."""
        sr = self.sample_rate
        total_samples = int(sr * (length_ms / 1000.0))
        max_amp = int(32767 * max(0.0, min(volume, 1.0)))

        frames = bytearray()
        for n in range(total_samples):
            t = n / sr
            # Simple sine
            sample = int(max_amp * math.sin(2 * math.pi * freq * t))
            frames += struct.pack('<h', sample)
        return bytes(frames)

    def _apply_linear_fade(self, pcm: bytearray, fade_out_ms: int) -> None:
        """Apply a quick linear fade-out to avoid clicks at the end."""
        if fade_out_ms <= 0:
            return
        bytes_per_sample = 2  # 16-bit mono
        total_samples = len(pcm) // bytes_per_sample
        fade_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        fade_samples = min(fade_samples, total_samples)
        for i in range(fade_samples):
            idx = (total_samples - 1 - i) * bytes_per_sample
            val = struct.unpack_from('<h', pcm, idx)[0]
            scale = (fade_samples - i) / fade_samples
            new_val = int(val * scale)
            struct.pack_into('<h', pcm, idx, new_val)

    def _wav_bytes(self, pcm_bytes: bytes) -> io.BytesIO:
        """Wrap raw PCM bytes into a minimal WAV in-memory file-like object."""
        num_channels = 1
        bits_per_sample = 16
        byte_rate = self.sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = len(pcm_bytes)
        fmt_chunk_size = 16
        riff_chunk_size = 4 + (8 + fmt_chunk_size) + (8 + data_size)

        buf = io.BytesIO()
        # RIFF header
        buf.write(b'RIFF')
        buf.write(struct.pack('<I', riff_chunk_size))
        buf.write(b'WAVE')
        # fmt chunk
        buf.write(b'fmt ')  # chunk id
        buf.write(struct.pack('<I', fmt_chunk_size))  # chunk size
        buf.write(struct.pack('<H', 1))  # PCM
        buf.write(struct.pack('<H', num_channels))
        buf.write(struct.pack('<I', self.sample_rate))
        buf.write(struct.pack('<I', byte_rate))
        buf.write(struct.pack('<H', block_align))
        buf.write(struct.pack('<H', bits_per_sample))
        # data chunk
        buf.write(b'data')
        buf.write(struct.pack('<I', data_size))
        buf.write(pcm_bytes)
        buf.seek(0)
        return buf

    def _build_tone(self, freq: float, ms: int, volume: float = 0.5) -> Optional[pygame.mixer.Sound]:
        if not self.enabled:
            return None
        pcm = bytearray(self._sine_wave(freq=freq, length_ms=ms, volume=volume))
        self._apply_linear_fade(pcm, fade_out_ms=18)
        wav_file = self._wav_bytes(bytes(pcm))
        try:
            return pygame.mixer.Sound(file=wav_file)
        except Exception:
            return None

    def _concat_pcm(self, parts: list[bytes]) -> bytes:
        return b''.join(parts)

    def _build_fanfare(self) -> Optional[pygame.mixer.Sound]:
        if not self.enabled:
            return None
        # Simpler, shorter fanfare to reduce memory usage
        notes = [(784, 120, 0.5), (988, 120, 0.5), (1175, 180, 0.5)]  # Shorter durations
        pcm_concat = self._concat_pcm([
            self._sine_wave(f, d, v) for f, d, v in notes
        ])
        try:
            return pygame.mixer.Sound(file=self._wav_bytes(pcm_concat))
        except Exception:
            return None

    def play_collision(self):
        if not self.enabled:
            return
        now = pygame.time.get_ticks() if pygame.get_init() else int(time.time() * 1000)
        if now - self._last_collision_ms < self._collision_cooldown_ms:
            return
        self._last_collision_ms = now
        snd = self._collision_sound or self._collision_tone_hard or self._collision_tone_soft
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_goal(self):
        if not self.enabled:
            return
        snd = self._goal_sound or self._goal_fanfare or self._collision_tone_hard or self._collision_tone_soft
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_pause(self):
        if not self.enabled:
            return
        snd = self._pause_sound or self._pause_tone or self._collision_tone_soft
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def start_pause_audio(self):
        """Start playing pause audio in a loop."""
        if not self.enabled:
            return
        # Stop any currently playing pause audio first
        self.stop_pause_audio()
        
        if self._pause_audio is not None:
            try:
                # Play with infinite loop (-1)
                self._pause_audio_channel = self._pause_audio.play(-1)
            except Exception:
                pass
    
    def ensure_pause_audio_playing(self):
        """Ensure pause audio is still playing, restart if needed."""
        if not self.enabled or self._pause_audio is None:
            return
        
        # Check if the channel is still playing
        if self._pause_audio_channel is None or not self._pause_audio_channel.get_busy():
            # Channel stopped or was never started, restart it
            try:
                self._pause_audio_channel = self._pause_audio.play(-1)
            except Exception:
                pass
    
    def stop_pause_audio(self):
        """Stop the looping pause audio."""
        if not self.enabled:
            return
        if self._pause_audio_channel is not None:
            try:
                self._pause_audio_channel.stop()
            except Exception:
                pass
            finally:
                self._pause_audio_channel = None

    def _try_load_external(self, key: str) -> Optional[pygame.mixer.Sound]:
        """Attempt to load a sound from the music folder with several name candidates."""
        if not self.enabled:
            return None
        candidates = SOUND_FILES.get(key, [])
        # Search in multiple likely roots: current working dir, script dir
        roots = [os.getcwd(), os.path.dirname(__file__), os.path.dirname(os.path.abspath(__file__))]
        for root in roots:
            music_dir = os.path.join(os.path.dirname(root), SOUND_DIR_NAME)
            # Also try sibling and same-level music dir
            for base in [music_dir, os.path.join(root, SOUND_DIR_NAME)]:
                for name in candidates:
                    path = os.path.join(base, name)
                    if os.path.isfile(path):
                        try:
                            return pygame.mixer.Sound(path)
                        except Exception:
                            continue
        return None

    def _try_load_music_file(self, filename: str) -> Optional[str]:
        """Try to find a music file and return its path, or None if not found."""
        if not self.enabled:
            return None
        # Search in multiple likely roots: current working dir, script dir
        roots = [os.getcwd(), os.path.dirname(__file__), os.path.dirname(os.path.abspath(__file__))]
        for root in roots:
            music_dir = os.path.join(os.path.dirname(root), SOUND_DIR_NAME)
            # Also try sibling and same-level music dir
            for base in [music_dir, os.path.join(root, SOUND_DIR_NAME)]:
                path = os.path.join(base, filename)
                if os.path.isfile(path):
                    return path
        return None

    def play_menu_music(self):
        """Start playing menu background music in a loop."""
        if not self.enabled or self._menu_music is None:
            return
        
        # Stop any currently playing music
        self.stop_music()
        
        try:
            pygame.mixer.music.load(self._menu_music)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            self._current_music_type = 'menu'
            self._music_paused = False
        except Exception:
            pass

    def play_ingame_music(self):
        """Start playing ingame background music in a loop."""
        if not self.enabled or self._ingame_music is None:
            return
        
        # Stop any currently playing music
        self.stop_music()
        
        try:
            pygame.mixer.music.load(self._ingame_music)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            self._current_music_type = 'ingame'
            self._music_paused = False
        except Exception:
            pass

    def play_ending_music(self, music_type='end'):
        """Start playing ending music based on type.
        
        Args:
            music_type: Type of ending music to play:
                - 'end': Generic ending music
                - 'end_win': Singleplayer win
                - 'end_lose': Singleplayer lose  
                - 'end_tie': Tie game
                - 'end_2p': Multiplayer ending
        """
        if not self.enabled:
            return
            
        # Map music type to file
        music_file_map = {
            'end': self._end_music,
            'end_win': self._end_win_music,
            'end_lose': self._end_lose_music,
            'end_tie': self._end_tie_music,
            'end_2p': self._end_2p_music
        }
        
        music_file = music_file_map.get(music_type)
        if music_file is None:
            # Fall back to generic ending or menu music
            music_file = self._end_music or self._menu_music
            if music_file is None:
                return
        
        # Stop any currently playing music
        self.stop_music()
        
        try:
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            self._current_music_type = music_type
            self._music_paused = False
        except Exception:
            pass

    def pause_music(self):
        """Pause the currently playing music."""
        if not self.enabled or self._current_music_type is None:
            return
        
        try:
            pygame.mixer.music.pause()
            self._music_paused = True
        except Exception:
            pass

    def resume_music(self):
        """Resume the paused music."""
        if not self.enabled or self._current_music_type is None or not self._music_paused:
            return
        
        try:
            pygame.mixer.music.unpause()
            self._music_paused = False
        except Exception:
            pass

    def stop_music(self):
        """Stop all background music."""
        if not self.enabled:
            return
        
        try:
            pygame.mixer.music.stop()
            self._current_music_type = None
            self._music_paused = False
        except Exception:
            pass

    def is_music_playing(self):
        """Check if music is currently playing (not paused)."""
        if not self.enabled or self._current_music_type is None:
            return False
        return pygame.mixer.music.get_busy() and not self._music_paused

    def pause_all_sounds(self):
        """Pause all sound effects except pause audio and background music."""
        if not self.enabled:
            return
        
        # Store currently playing channels that we want to pause
        # This captures the state before any new sounds (like pause audio) start
        try:
            # Get all currently playing channels
            num_channels = pygame.mixer.get_num_channels()
            for i in range(num_channels):
                channel = pygame.mixer.Channel(i)
                if channel.get_busy():
                    # Pause this channel and track it for later resume
                    channel.pause()
                    self._paused_channels.add(channel)
        except Exception:
            pass
    
    def resume_all_sounds(self):
        """Resume all sound effects that were paused by us."""
        if not self.enabled:
            return
        
        try:
            # Resume only the channels we paused, but skip pause audio channel
            channels_to_resume = []
            for channel in self._paused_channels:
                # Don't resume the pause audio channel
                if channel != self._pause_audio_channel:
                    channels_to_resume.append(channel)
                    channel.unpause()
            
            # Update our tracking to only include channels we actually resumed
            self._paused_channels.clear()
        except Exception:
            pass

    def get_current_music_type(self):
        """Get the type of music currently loaded ('menu', 'ingame', or None)."""
        return self._current_music_type
