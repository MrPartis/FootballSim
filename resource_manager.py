"""
Unified Resource Manager for Mini Football Game

This module provides a centralized, optimized way to handle asset loading
for development environments.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

def _get_base_path() -> Path:
    """
    Get the base path for resources in development mode.
    
    Returns:
        Path object pointing to the application directory
    """
    return Path(__file__).parent.absolute()

def get_asset_path(filename: str) -> str:
    """
    Get full path to an asset file as string.
    
    Args:
        filename: Asset filename (e.g., 'bg.png', 'menu.mp3')
        
    Returns:
        String path to the asset file
    """
    base_path = _get_base_path()
    assets_path = base_path / "assets"
    asset_path = assets_path / filename
    return str(asset_path)

def get_resource_path(relative_path: str) -> str:
    """
    Legacy function for getting resource paths.
    
    Args:
        relative_path: Relative path to resource
        
    Returns:
        Absolute path as string
    """
    base_path = _get_base_path()
    
    if relative_path.startswith("assets/") or relative_path.startswith("assets\\"):
        # Extract filename from assets path
        filename = relative_path.replace("assets/", "").replace("assets\\", "")
        return get_asset_path(filename)
    else:
        # Handle other paths
        return str(base_path / relative_path)

def asset_exists(filename: str) -> bool:
    """
    Check if an asset file exists.
    
    Args:
        filename: Asset filename
        
    Returns:
        True if asset exists, False otherwise
    """
    return os.path.exists(get_asset_path(filename))

def find_asset_variant(base_name: str, extensions: List[str]) -> Optional[str]:
    """
    Find the first existing variant of an asset with different extensions.
    
    Args:
        base_name: Base name without extension (e.g., 'collision')
        extensions: List of extensions to try (e.g., ['.mp3', '.wav', '.ogg'])
        
    Returns:
        String path to first found variant, or None if none exist
    """
    for ext in extensions:
        filename = f"{base_name}{ext}"
        if asset_exists(filename):
            return get_asset_path(filename)
    return None

def list_assets() -> List[str]:
    """
    List all available asset files.
    
    Returns:
        List of asset filenames
    """
    base_path = _get_base_path()
    assets_path = base_path / "assets"
    
    if not assets_path.exists():
        return []
    
    return [f.name for f in assets_path.iterdir() if f.is_file()]



def get_assets_dir() -> str:
    """
    Get the assets directory path as string.
    
    Returns:
        String path to assets directory
    """
    base_path = _get_base_path()
    return str(base_path / "assets")

def debug_info() -> dict:
    """
    Get debug information about the resource manager state.
    
    Returns:
        Dictionary with debug information
    """
    base_path = _get_base_path()
    assets_path = base_path / "assets"
    
    return {
        "base_path": str(base_path),
        "assets_path": str(assets_path),
        "assets_exists": assets_path.exists(),
        "available_assets": list_assets(),
        "python_executable": sys.executable,
        "working_directory": os.getcwd()
    }

# Backward compatibility aliases
get_asset_path_str = get_asset_path  # For any code expecting this function name

class ResourceManager:
    """
    Class-based interface for resource management (for advanced usage).
    Most code should use the simple function-based interface above.
    """
    
    def __init__(self):
        self._base_path = _get_base_path()
        self._assets_path = self._base_path / "assets"
    
    @property
    def base_path(self) -> Path:
        """Return the base application path."""
        return self._base_path
    
    @property
    def assets_path(self) -> Path:
        """Return the assets folder path."""
        return self._assets_path
    
    def get_asset_path(self, filename: str) -> str:
        """Get asset path as string."""
        return get_asset_path(filename)
    
    def asset_exists(self, filename: str) -> bool:
        """Check if asset exists."""
        return asset_exists(filename)
    
    def find_asset_variant(self, base_name: str, extensions: List[str]) -> Optional[str]:
        """Find asset variant."""
        return find_asset_variant(base_name, extensions)
    
    def list_assets(self) -> List[str]:
        """List all assets."""
        return list_assets()
    
    def debug_info(self) -> dict:
        """Get debug info."""
        return debug_info()

# Global instance for advanced usage
resource_manager = ResourceManager()