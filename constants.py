# Constants for Mini Football Game
import pygame

# Screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 150, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LIGHT_BLUE = (0,255,255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)

# Difficulty colors
LIME = (0, 255, 0)
LEMON = (255, 255, 0)
DIFFICULTY_RED = (255, 0, 0)
DARK_RED = (127, 0, 0)
# UI Colors for better contrast
MENU_TEXT_COLOR = (240, 240, 240)  # Light gray, better than pure white for contrast

# Field dimensions - adjusted for larger goals
FIELD_WIDTH = 1100  # Reduced from 1220 to accommodate larger goals
FIELD_HEIGHT = 670  # Reduced by scoreboard height (720-50=670)
FIELD_X = 90  # Increased margin for larger goal space
FIELD_Y = 50  # Start below scoreboard

# Goal dimensions - doubled scale for better visibility
GOAL_WIDTH = 160  # Doubled from 80 for better visibility
GOAL_HEIGHT = 40  # Doubled from 20
GOAL_DEPTH = 50   # Doubled from 25

# Player and ball dimensions - doubled scale for simulation world
PLAYER_RADIUS = 24  # Doubled from 12 for better visibility
BALL_RADIUS = 12    # Doubled from 6 for better visibility

# Physics - unified and optimized for smaller objects
FRICTION = 0.955  # Universal friction coefficient
MAX_FORCE = 350  # Maximum force for players
MIN_FORCE = 25   # Minimum force for players
FORCE_MULTIPLIER = 0.35  # Increased for smaller objects
PLAYER_FORCE_MULTIPLIER = 0.14  # Increased for smaller players

# Collision physics - consolidated
RESTITUTION = 0.68   # Universal bounce coefficient
BOUNCE_FACTOR = 0.7  # Simplified bounce factor
BALL_MASS = 0.5      # Optimized ball mass
PLAYER_MASS = 2.0    # Optimized player mass
COLLISION_DAMPING = 0.985  # Universal collision damping

# Advanced physics solver
POSITION_CORRECTION_PERCENT = 0.8  # Increased for better separation
POSITION_CORRECTION_SLOP = 0.1  # Reduced to apply correction more aggressively
PHYSICS_SOLVER_ITERATIONS = 8  # Increased for better collision resolution
MAX_VELOCITY = 300.0  # Further reduced to prevent noclipping

# Continuous Collision Detection (CCD) settings
ENABLE_CCD = True
CCD_MAX_SUBDIVISIONS = 10  # Maximum movement subdivisions
CCD_MIN_STEP_SIZE = 0.5  # Minimum step size for CCD (pixels)
CCD_VELOCITY_THRESHOLD = 75.0  # Velocity above which CCD activates

# Team colors
TEAM1_COLOR = BLUE
TEAM2_COLOR = RED

# Player positions (relative to field)
# Team 1 (Blue) - Left side
TEAM1_POSITIONS = [
    (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
    (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.25), # Defender 1
    (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.75), # Defender 2
    (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.35),  # Midfielder
    (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.65),  # Forward
]

# Team 2 (Red) - Right side
TEAM2_POSITIONS = [
    (FIELD_WIDTH * 0.9, FIELD_HEIGHT * 0.5),   # Goalkeeper
    (FIELD_WIDTH * 0.75, FIELD_HEIGHT * 0.25), # Defender 1
    (FIELD_WIDTH * 0.75, FIELD_HEIGHT * 0.75), # Defender 2
    (FIELD_WIDTH * 0.6, FIELD_HEIGHT * 0.35),  # Midfielder
    (FIELD_WIDTH * 0.6, FIELD_HEIGHT * 0.65),  # Forward
]

# Ball starting position
BALL_START_POS = (FIELD_WIDTH * 0.5, FIELD_HEIGHT * 0.5)

# Controls
# Player 1 (WASD for movement)
P1_CONTROLS = {
    'up': pygame.K_w,
    'down': pygame.K_s,
    'left': pygame.K_a,
    'right': pygame.K_d,
    'select_players': [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5],
    'action': pygame.K_SPACE
}

# Player 2 (Arrow keys for movement)
P2_CONTROLS = {
    'up': pygame.K_UP,
    'down': pygame.K_DOWN,
    'left': pygame.K_LEFT,
    'right': pygame.K_RIGHT,
    'select_players': [pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4, pygame.K_KP5],
    'action': pygame.K_KP_ENTER
}

# Game states
GAME_STATE_MENU = 0
GAME_STATE_TACTICS = 1
GAME_STATE_COIN_FLIP = 2
GAME_STATE_PLAYING = 3
GAME_STATE_FORCE_SELECT = 4
GAME_STATE_PAUSED = 5
GAME_STATE_GAME_OVER = 6
GAME_STATE_CUSTOM_TACTICS = 7
GAME_STATE_AUDIO = 8

# Turn phases
PHASE_SELECT_PLAYER = 0
PHASE_AIM_DIRECTION = 1
PHASE_SELECT_FORCE = 2
PHASE_PLAYER_MOVING = 3
PHASE_BALL_MOVING = 4

# Movement settings - optimized
DIRECTION_ARROW_LENGTH = 100
DIRECTION_CHANGE_SPEED = 0.05
COLLISION_SEPARATION_FORCE = 1.2
MIN_COLLISION_VELOCITY = 2.0

# UI
SCOREBOARD_HEIGHT = 50
FORCE_METER_WIDTH = 100
FORCE_METER_HEIGHT = 10

# Goal sequence
GOAL_BANNER_MS = 1500  # time to show GOAL notification
KICKOFF_OFFSET = 80    # offset from center toward losing team's half

# Modes and AI
DEFAULT_SINGLEPLAYER = True  # start in singleplayer by default
BOT_TEAM = 2                 # which team the bot controls in singleplayer
BOT_DEFAULT_DIFFICULTY = "medium"  # easy | medium | hard | insane | extreme

# Bot global tuning (Mario Party-like adaptive behavior)
# Thinking delay per difficulty (ms between bot decisions)
BOT_THINK_MS = {
    "easy": 800,
    "medium": 500,
    "hard": 350,
    "insane": 250,
    "extreme": 150,
}

# Aim jitter magnitude by difficulty (higher = sloppier aim)
BOT_AIM_JITTER = {
    "easy": 15.0,
    "medium": 10.0,
    "hard": 5.0,
    "insane": 2.0,
    "extreme": 0.5,
}

# Force noise ratio by difficulty (multiplicative +/- noise)
BOT_FORCE_NOISE = {
    "easy": 0.20,
    "medium": 0.15,
    "hard": 0.10,
    "insane": 0.05,
    "extreme": 0.01,
}

# Baseline risk-taking (0=very safe, 1=very risky)
BOT_BASE_RISK = {
    "easy": 0.3,
    "medium": 0.55,
    "hard": 0.8,
    "insane": 0.9,
    "extreme": 0.99,
}

# Difficulty colors for UI display
DIFFICULTY_COLORS = {
    "easy": LIME,
    "medium": LEMON,
    "hard": ORANGE,
    "insane": RED,
    "extreme": DARK_RED
}

# How many turns left considered as endgame to ramp behavior
BOT_ENDGAME_TURNS = 8

# Audio settings
SOUND_DIR_NAME = "assets"  # folder at project root or next to main scripts
SOUND_FILES = {
    "collision": ["collision.wav", "collision.ogg", "collision.mp3"],
    "goal": ["goal.wav", "goal.ogg", "goal.mp3"],
    "pause": ["pause.wav", "pause.ogg", "pause.mp3"],
    "pause_audio": ["pause_audio.mp3", "pause_audio.wav", "pause_audio.ogg"]
}

# Default audio configuration (saved/loaded via config_manager.py)
DEFAULT_MASTER_VOLUME = 1.00  # Master volume (0.0 to 1.0)
DEFAULT_SFX_VOLUME = 1.00     # Sound effects volume (0.0 to 1.0)
DEFAULT_BGM_VOLUME = 1.00     # Background music volume (0.0 to 1.0)

# Custom tactics configuration (saved/loaded via config_manager.py)
DEFAULT_CUSTOM_TACTICS = {
    'custom1': None,
    'custom2': None,
    'custom3': None,
    'custom4': None,
    'custom5': None,
    'custom6': None,
}

# Corner/unstuck mechanics - doubled for scaled objects
CORNER_STUCK_RADIUS = 60  # Doubled from 30 for larger players
CORNER_REPEL_MIN_DIST = 80  # Doubled from 40 for larger objects
CORNER_REPEL_IMPULSE = 1.0  # Keep physics unchanged

# Player interaction ranges - doubled for larger objects
KICK_RANGE_BONUS = 20  # Doubled from 10 for larger player/ball sizes

# Cinematic animation settings
GOAL_ZOOM_SLOW_MOTION_SPEED = 0.3  # Speed multiplier during goal zoom animation (0.3x = 30% normal speed)

# Coin flip animation settings
COIN_FLIP_DURATION = 1000  # Total animation duration in ms
COIN_FLIP_ROTATION_SPEED = 10  # Rotation speed (degrees per frame)
COIN_SIZE = 100  # Coin radius in pixels
COIN_FLIPS = 9  # Number of visual flips during animation