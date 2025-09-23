"""
Optimized Configuration Manager for Mini Football Game

This module handles all configuration saving/loading operations
with support for both development and PyInstaller environments.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from resource_manager import _get_base_path

class ConfigManager:
    """Manages game configuration with support for PyInstaller environments."""
    
    def __init__(self):
        self._config_file = "game_config.json"
        self._base_path = _get_base_path()
        self._is_frozen = hasattr(sys, '_MEIPASS')
        self._config_data = {}
        
        # Initialize configuration paths
        if self._is_frozen:
            # In PyInstaller, save to user's documents or temp directory
            self._config_dir = Path.home() / "Documents" / "MiniFootball"
        else:
            # In development, save next to the executable
            self._config_dir = self._base_path
            
        self._config_path = self._config_dir / self._config_file
        
        # Ensure config directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            else:
                # Initialize with defaults from constants
                self._initialize_defaults()
        except Exception as e:
            print(f"Warning: Failed to load config from {self._config_path}: {e}")
            self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize configuration with default values."""
        try:
            # Import constants to get defaults
            import constants
            
            self._config_data = {
                'audio': {
                    'master_volume': getattr(constants, 'DEFAULT_MASTER_VOLUME', 1.0),
                    'sfx_volume': getattr(constants, 'DEFAULT_SFX_VOLUME', 1.0),
                    'bgm_volume': getattr(constants, 'DEFAULT_BGM_VOLUME', 1.0),
                },
                'custom_tactics': getattr(constants, 'DEFAULT_CUSTOM_TACTICS', {}),
                'game_settings': {
                    'difficulty': getattr(constants, 'BOT_DEFAULT_DIFFICULTY', 'medium'),
                    'singleplayer': getattr(constants, 'DEFAULT_SINGLEPLAYER', True),
                }
            }
        except Exception as e:
            print(f"Warning: Failed to load defaults from constants: {e}")
            # Fallback hardcoded defaults
            self._config_data = {
                'audio': {'master_volume': 1.0, 'sfx_volume': 1.0, 'bgm_volume': 1.0},
                'custom_tactics': {},
                'game_settings': {'difficulty': 'medium', 'singleplayer': True}
            }
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save config to {self._config_path}: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config_data.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any, auto_save: bool = True):
        """Set a configuration value."""
        if section not in self._config_data:
            self._config_data[section] = {}
        
        self._config_data[section][key] = value
        
        if auto_save:
            self.save_config()
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section."""
        return self._config_data.get(section, {})
    
    def set_section(self, section: str, data: Dict[str, Any], auto_save: bool = True):
        """Set an entire configuration section."""
        self._config_data[section] = data
        
        if auto_save:
            self.save_config()
    
    def get_config_path(self) -> Path:
        """Get the path where configuration is stored."""
        return self._config_path
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self._initialize_defaults()
        self.save_config()

# Global instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

# Convenience functions
def get_audio_config() -> Dict[str, float]:
    """Get audio configuration."""
    return get_config_manager().get_section('audio')

def set_audio_config(volume_type: str, value: float):
    """Set audio configuration."""
    get_config_manager().set('audio', volume_type, value)

def get_custom_tactics() -> Dict[str, Any]:
    """Get custom tactics configuration."""
    return get_config_manager().get_section('custom_tactics')

def set_custom_tactics(tactics_data: Dict[str, Any]):
    """Set custom tactics configuration."""
    get_config_manager().set_section('custom_tactics', tactics_data)

def get_game_settings() -> Dict[str, Any]:
    """Get game settings."""
    return get_config_manager().get_section('game_settings')

def set_game_setting(key: str, value: Any):
    """Set a game setting."""
    get_config_manager().set('game_settings', key, value)