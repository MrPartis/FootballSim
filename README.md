# Mini Football - Turn-Based Football Simulation

A turn-based football (soccer) simulation game built with Python and Pygame. Control your team of 5 players in strategic gameplay with realistic physics, custom tactics, and both single-player (vs AI) and multiplayer modes.

## Features

- **Turn-based gameplay**: Strategic football where each player takes turns
- **Realistic physics**: Ball and player interactions with proper collision detection
- **Custom tactics system**: Create, modify, and save team formations and strategies
- **Persistent configuration**: Audio settings and custom tactics automatically saved and restored
- **Single-player mode**: Play against AI with three difficulty levels (Easy, Medium, Hard)
- **Multiplayer mode**: Local 2-player gameplay
- **Dynamic AI**: Adaptive bot behavior that adjusts based on game state
- **Immersive audio**: Sound effects, background music, and pause audio with volume controls
- **Advanced pause system**: Game pause with animated GIF overlay and audio management
- **Goal celebrations**: Cinematic goal sequences with zoom effects
- **Configuration persistence**: All settings automatically saved to maintain user preferences

## Game Controls

### Player 1 (Blue Team)
- **Movement**: WASD keys
- **Player Selection**: Number keys 1-5
- **Action/Kick**: Spacebar

### Player 2 (Red Team)
- **Movement**: Arrow keys (↑↓←→)
- **Player Selection**: Numpad 1-5
- **Action/Kick**: Enter

### Menu & Tactics Screen Controls
- **Navigate**: Arrow keys or WASD
- **Select**: Enter or Spacebar
- **Back to Menu**: ESC
- **Customize Tactic**: C (on custom tactics)
- **Delete Tactic**: X (on custom tactics) - Safely removes tactics and sets slot to empty
- **Reset All Tactics**: R (removes all custom tactics with confirmation)
- **Audio Controls**: +/- keys to adjust Master, SFX, and BGM volume levels

### Global Controls
- **Pause/Resume**: ESC (during gameplay) - Pauses all audio and game state
- **Restart Game**: R (when game is over)
- **Quit**: ESC (when game is over) or close window

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Installation & Running

   ```bash
   git clone https://github.com/MrPartis/FootballSim.git
   cd FootballSim
   pip install -r requirements.txt
   python main.py
   ```

## Dependencies

The game requires the following Python packages:

- **pygame** (>= 2.0.0) - Game engine and graphics
- **pillow** (>= 8.0.0) - Image processing (for animated GIFs)

All dependencies are listed in `requirements.txt` and will be installed automatically.

## Game Mechanics

### Gameplay Flow
1. **Team Selection**: Choose between single-player (vs AI) or multiplayer mode
2. **Tactics Setup**: Select formations and strategies for your team
3. **Turn-Based Play**: 
   - Select a player from your team
   - Aim the direction of movement/action
   - Set the force power using the power meter
   - Watch the physics simulation play out
4. **Goal Scoring**: Score by getting the ball into the opponent's goal
5. **Win Condition**: First team to score wins the match

### Physics System
- Realistic ball physics with momentum and friction
- Player-to-player and player-to-ball collisions
- Bounce mechanics off field boundaries
- Advanced physics solver with position correction

### AI Behavior
The AI adapts its strategy based on:
- Current score difference
- Time remaining in the game
- Difficulty level selected
- Risk assessment for different moves

## Configuration & Persistence

The game automatically saves and restores user preferences:

### Audio Configuration
- **Master Volume**: Overall game volume (0-100%)
- **SFX Volume**: Sound effects volume (0-100%) 
- **BGM Volume**: Background music volume (0-100%)
- **Auto-save**: Volume settings are automatically saved and restored on game restart
- **Debounced saving**: Frequent volume changes are efficiently batched to prevent file system stress

### Custom Tactics Persistence
- **Automatic saving**: Custom formations are automatically saved when created or modified
- **Cross-session persistence**: All custom tactics are preserved between game sessions
- **Safe deletion**: Removing tactics properly sets slots to empty without data corruption
- **Robust file handling**: Enhanced save system with fallback mechanisms for data integrity

### Configuration Files
Game settings are stored in `constants.py` and automatically managed:
- **DEFAULT_MASTER_VOLUME**: Persistent master volume setting
- **DEFAULT_SFX_VOLUME**: Persistent sound effects volume setting  
- **DEFAULT_BGM_VOLUME**: Persistent background music volume setting
- **DEFAULT_CUSTOM_TACTICS**: Persistent custom formations storage

## Configuration

Game settings can be modified in `constants.py`:

- **Screen resolution**: `SCREEN_WIDTH`, `SCREEN_HEIGHT`
- **Physics parameters**: Friction, force multipliers, collision settings
- **Game balance**: Player speeds, ball physics, AI difficulty
- **Controls**: Key bindings for both players
- **Audio settings**: Sound file paths and default volumes
- **Persistence settings**: Auto-save configuration and custom tactics storage

## Version History

### Version 1.0.1 (Latest)
- ✅ **Enhanced Audio System**: Added persistent volume controls with real-time adjustment
- ✅ **Custom Tactics Persistence**: All custom formations now automatically save and restore
- ✅ **Improved Deletion System**: Safe removal of custom tactics with proper None handling
- ✅ **Robust File I/O**: Enhanced save system with better error handling and fallback mechanisms
- ✅ **Audio Configuration**: Master, SFX, and BGM volume controls with debounced saving
- ✅ **Better Data Integrity**: Improved regex patterns and validation for file operations

### Version 1.0.0
- 🎮 Initial release with core gameplay mechanics
- ⚽ Turn-based football simulation with physics
- 🤖 AI opponents with multiple difficulty levels  
- 🎵 Basic audio system with sound effects and music
- 📋 Custom tactics creation and editing
- 🏆 Goal celebration system with cinematic effects

## Development

### Adding New Features
1. **Sound Effects**: Add audio files to the `assets/` folder and update `SOUND_FILES` in `constants.py`
2. **Custom Tactics**: Modify `tactics.py` to add new formations (auto-saved to `constants.py`)
3. **AI Improvements**: Enhance bot behavior in `game_manager.py`
4. **Visual Effects**: Update rendering in respective class files
5. **Configuration Options**: Add new persistent settings in `constants.py` with auto-save support



## Troubleshooting

### Common Issues

**Game won't start:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.7+ required)

**No sound:**
- Verify audio files exist in the `assets/` folder
- Check system audio settings and volume levels
- Install pygame with audio support
- Try adjusting volume using +/- keys in the game menu

**Settings not saving:**
- Ensure `constants.py` is writable
- Check file permissions in the game directory
- Verify the game has write access to save configuration changes

**Custom tactics not appearing:**
- Restart the game to reload saved tactics from `constants.py`
- Check that custom tactics were saved properly in the constants file
- Use the tactics deletion/reset feature if tactics appear corrupted

**Performance issues:**
- Reduce `FPS` in `constants.py`
- Lower screen resolution
- Disable sound effects temporarily



## License

This project is developed as part of a game programming course. Feel free to use and modify for educational purposes.

## Contributing

This is an educational project, but suggestions and improvements are welcome! Feel free to:
- Report bugs
- Suggest new features
- Improve documentation
- Optimize performance

## Acknowledgments

- Built with Python and Pygame
- Physics simulation inspired by real football mechanics
- AI behavior designed for engaging single-player experience