"""
Configuration for train-bookara-maker-v2
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
RESOURCES_DIR = PROJECT_ROOT / 'resources'
TEMP_DIR = PROJECT_ROOT / 'temp'
OUTPUT_DIR = PROJECT_ROOT / 'output'

# Create directories if they don't exist
for directory in [RESOURCES_DIR, TEMP_DIR, OUTPUT_DIR]:
    directory.mkdir(exist_ok=True)

# Audio settings
SAMPLE_RATE = 22050
AUDIO_FORMAT = 'wav'

# Demucs model settings
DEMUCS_MODEL = 'htdemucs'  # 4-track model

# Video settings
VIDEO_CODEC = 'libx264'
AUDIO_CODEC = 'aac'

# LRC settings
LRC_ENCODING = 'utf-8-sig'
TIME_FORMAT = 'mm:ss.xx'

# ASS settings
ASS_DEFAULT_FONTNAME = 'Arial'
ASS_DEFAULT_FONTSIZE = 20
ASS_DEFAULT_PRIMARY_COLOR = '#FFFFFF'
ASS_DEFAULT_SECONDARY_COLOR = '#000000'

# UI settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
