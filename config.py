"""Configuration settings for InkClone AI."""

from dataclasses import dataclass
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
SERVICES_DIR = BASE_DIR / "services"
MODELS_DIR = BASE_DIR / "models"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
TESTS_DIR = BASE_DIR / "tests"

# Page Dimensions (A4 format at 150 DPI for crisp export & smooth rendering)
PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754

# Margins (pixels)
DEFAULT_MARGIN_TOP = 140
DEFAULT_MARGIN_BOTTOM = 120
DEFAULT_MARGIN_LEFT = 140
DEFAULT_MARGIN_RIGHT = 100

# Ruled Paper Settings
DEFAULT_LINE_HEIGHT = 44
DEFAULT_RULE_COLOR = (205, 217, 230, 180)     # Subtle notebook blue rule
DEFAULT_MARGIN_COLOR = (235, 120, 120, 190)   # Notebook red left margin rule
MARGIN_LINE_X = 140                           # Position of red vertical margin line

# Graph Paper Settings
GRAPH_GRID_SIZE = 32
GRAPH_GRID_COLOR = (215, 225, 235, 150)

# Paper Colors
PAPER_BG_WHITE = (255, 255, 255)
PAPER_BG_OFFWHITE = (252, 251, 247)
PAPER_BG_CREAM = (248, 246, 238)

# Ink Colors (RGB)
INK_COLORS = {
    "Royal Blue": (26, 62, 138),
    "Deep Navy": (16, 37, 77),
    "Classic Black": (28, 28, 28),
    "Charcoal Ink": (45, 45, 48),
}

# Upload Constraints
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# Synthesis Engine Modes
ENGINE_STYLE_CONDITIONED = "Style-Conditioned Dynamic Engine"
ENGINE_AI_NEURAL = "Pretrained Neural Reference Model (GPU Required)"

@dataclass
class HandwritingStyleMetrics:
    """Extracted handwriting metrics from sample image."""
    slant_angle: float = 0.0          # Degrees (-30 to +30, positive is forward slant)
    stroke_thickness: float = 2.0     # Pixels (1.0 to 5.0)
    word_spacing: float = 20.0        # Pixels (10 to 40)
    char_spacing: float = 2.0         # Pixels (-2 to 8)
    line_spacing: float = 44.0        # Pixels (30 to 70)
    baseline_variance: float = 1.5    # Wobble / jitter variance in pixels (0.0 to 4.0)
    dominant_ink_color: tuple = (26, 62, 138)  # Detected ink RGB
    confidence_score: float = 0.85    # Quality / confidence of extraction (0 to 1)
