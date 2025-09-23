# Mini Football - Turn-Based Football Simulation

A turn-based football (soccer) simulation game built with Python and Pygame. Control your team of 5 players in strategic gameplay with realistic physics, custom tactics, and both single-player (vs AI) and multiplayer modes.

## Features

- **Turn-based gameplay**: Strategic football where each player takes turns
- **Realistic physics**: Ball and player interactions with proper collision detection
- **Custom tactics**: Create and modify team formations and strategies
- **Single-player mode**: Play against AI with three difficulty levels (Easy, Medium, Hard)
- **Multiplayer mode**: Local 2-player gameplay
- **Dynamic AI**: Adaptive bot behavior that adjusts based on game state
- **Sound effects**: Immersive audio including goal sounds, collisions, and background music
- **Pause system**: Game pause with animated overlay
- **Goal celebrations**: Cinematic goal sequences with zoom effects

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
- **Delete Tactic**: X (on custom tactics)
- **Reset All Tactics**: R

### Global Controls
- **Pause/Resume**: ESC (during gameplay)
- **Restart Game**: R (when game is over)
- **Quit**: ESC (when game is over) or close window

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Method 1: Run from Source

   ```bash
   git clone https://github.com/MrPartis/FootballSim.git
   cd FootballSim
   pip install -r requirements.txt
   python main.py
   ```

### Method 2: Build Executable (Windows)

1. **Follow Method 1**

2. **Run the build script**:
   ```bash
   build.bat
   ```
   
   Or manually build with PyInstaller:
   ```bash
   pyinstaller --onefile --windowed --name="MiniFootball" --add-data="assets;assets" main.py
   ```

3. **Find the executable** in the `dist` folder: `dist/MiniFootball.exe`

4. **Distribute** the executable - it can run on any Windows computer without Python installed

## Dependencies

The game requires the following Python packages:

- **pygame** (>= 2.0.0) - Game engine and graphics
- **pillow** (>= 8.0.0) - Image processing (for animated GIFs)
- **pyinstaller** (>= 5.0.0) - For building standalone executables

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

## Configuration

Game settings can be modified in `constants.py`:

- **Screen resolution**: `SCREEN_WIDTH`, `SCREEN_HEIGHT`
- **Physics parameters**: Friction, force multipliers, collision settings
- **Game balance**: Player speeds, ball physics, AI difficulty
- **Controls**: Key bindings for both players
- **Audio settings**: Sound file paths and volume

## Development

### Adding New Features
1. **Sound Effects**: Add audio files to the `assets/` folder and update `SOUND_FILES` in `constants.py`
2. **Custom Tactics**: Modify `tactics.py` to add new formations
3. **AI Improvements**: Enhance bot behavior in `game_manager.py`
4. **Visual Effects**: Update rendering in respective class files

### Building for Distribution
Use the provided `build.bat` script on Windows, or refer to `build_instructions.txt` for detailed PyInstaller commands for other platforms.

## Troubleshooting

### Common Issues

**Game won't start:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.7+ required)

**No sound:**
- Verify audio files exist in the `assets/` folder
- Check system audio settings
- Install pygame with audio support

**Performance issues:**
- Reduce `FPS` in `constants.py`
- Lower screen resolution
- Disable sound effects temporarily

**Build fails:**
- Ensure PyInstaller is installed: `pip install pyinstaller`
- Check that all assets are in the correct folder
- Try building without the `--windowed` flag to see error messages

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