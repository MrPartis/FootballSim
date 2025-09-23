"""
Debug version of main.py to find recursion source
"""
import pygame
import sys
import os

print("Starting imports...")

try:
    from PIL import Image  # For animated GIF support in pause screen
    print("PIL imported successfully")
except Exception as e:
    print(f"PIL import failed: {e}")
    Image = None

print("Importing constants...")
from constants import *
print("Constants imported successfully")

print("Importing simple_resource_manager...")
from resource_manager import get_resource_path, get_asset_path
print("Simple resource manager imported successfully")

print("Testing resource manager...")
test_path = get_asset_path("bg.png")
print(f"Test path: {test_path}")

print("Importing game_manager...")
from game_manager import GameManager
print("GameManager imported successfully")

print("All imports complete, starting game...")