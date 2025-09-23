import json
from constants import *

invalid_tactics = {
    'custom1': {
        'name': 'Ball Overlap Test',
        'team1_positions': [
            (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
            (FIELD_WIDTH * 0.5, FIELD_HEIGHT * 0.5),   # Player overlapping ball start position!
            (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.75), # Defender 2
            (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.35),  # Midfielder
            (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.65),  # Forward
        ],
        'team2_positions': [
            (FIELD_WIDTH * 0.9, FIELD_HEIGHT * 0.5),   # Goalkeeper
            (FIELD_WIDTH * 0.75, FIELD_HEIGHT * 0.25), # Defender 1
            (FIELD_WIDTH * 0.75, FIELD_HEIGHT * 0.75), # Defender 2
            (FIELD_WIDTH * 0.6, FIELD_HEIGHT * 0.35),  # Midfielder
            (FIELD_WIDTH * 0.6, FIELD_HEIGHT * 0.65),  # Forward
        ]
    },
    'custom2': {
        'name': 'Player Collision Test',
        'team1_positions': [
            (FIELD_WIDTH * 0.1, FIELD_HEIGHT * 0.5),   # Goalkeeper
            (FIELD_WIDTH * 0.25, FIELD_HEIGHT * 0.25), # Defender 1
            (FIELD_WIDTH * 0.25 + 5, FIELD_HEIGHT * 0.25 + 5), # Defender 2 - OVERLAPPING!
            (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.35),  # Midfielder
            (FIELD_WIDTH * 0.4, FIELD_HEIGHT * 0.65),  # Forward
        ],
        'team2_positions': [
            (FIELD_WIDTH * 0.9, FIELD_HEIGHT * 0.5),   # Goalkeeper
            (FIELD_WIDTH * 0.75, FIELD_HEIGHT * 0.25), # Defender 1
            (FIELD_WIDTH * 0.75, FIELD_HEIGHT * 0.75), # Defender 2
            (FIELD_WIDTH * 0.6, FIELD_HEIGHT * 0.35),  # Midfielder
            (FIELD_WIDTH * 0.6, FIELD_HEIGHT * 0.65),  # Forward
        ]
    }
}

with open('custom_tactics.json', 'w') as f:
    json.dump(invalid_tactics, f, indent=2)
print("Created invalid tactics for game testing")
print("Now run 'python main.py' and go to tactics selection!")