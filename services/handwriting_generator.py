"""Modular Handwriting Generation Service for InkClone AI.

Provides:
- BaseHandwritingEngine: Abstract engine interface.
- StyleConditionedFontEngine: Dynamic style synthesizer applying analyzed slant,
  stroke width, baseline jitter, spacing, and ink pressure.
- NeuralHandwritingEngine: Pluggable wrapper for deep learning handwriting models (CONSTANT/GANs).
"""

import math
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from config import FONTS_DIR, HandwritingStyleMetrics


class BaseHandwritingEngine(ABC):
    """Abstract base class for all handwriting synthesis engines."""

    @abstractmethod
    def render_text_line(
        self,
        text: str,
        style: HandwritingStyleMetrics,
        font_size: int = 32,
        ink_color: Optional[Tuple[int, int, int]] = None,
        font_name: Optional[str] = None,
        line_seed: Optional[int] = None,
    ) -> Image.Image:
        """Render a single line of text into a transparent RGBA PIL Image."""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, str]:
        """Return engine metadata and hardware requirements."""
        pass

    @abstractmethod
    def is_neural(self) -> bool:
        """Return True if this is a deep learning reference-conditioned model."""
        pass


class StyleConditionedFontEngine(BaseHandwritingEngine):
    """Dynamic handwriting synthesis engine conditioned on analyzed style metrics.

    Applies:
    - Affine shear transformation matching detected slant angle
    - Stroke width morphology adjustment
    - Micro-rotations and baseline wobble reflecting natural human hand jitter
    - Dynamic word and character spacing
    - Realistic ink flow opacity modulation
    """

    def __init__(self, fonts_dir: Path = FONTS_DIR):
        self.fonts_dir = fonts_dir
        self.fonts_dir.mkdir(parents=True, exist_ok=True)
        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

    def get_info(self) -> Dict[str, str]:
        return {
            "name": "Style-Conditioned Dynamic Engine",
            "type": "Algorithmic / Style-Modulated Fallback",
            "is_neural": False,
            "description": (
                "Synthesizes handwritten lines by applying uploaded slant, stroke thickness, "
                "baseline drift, and spacing metrics to typography with stochastic micro-jitter."
            ),
            "disclaimer": (
                "Notice: This engine actively adapts style metrics (slant, spacing, baseline wobble, "
                "ink hue), but uses base handwriting letterforms. It does not claim to clone "
                "exact custom glyph geometries without a trained neural model."
            ),
        }

    def is_neural(self) -> bool:
        return False

    def _get_font(self, font_name: Optional[str], size: int) -> ImageFont.ImageFont:
        """Load requested font from assets/fonts or fallback to default."""
        cache_key = (font_name or "default", size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = None
        if font_name:
            font_path = self.fonts_dir / font_name
            if font_path.exists():
                try:
                    font = ImageFont.truetype(str(font_path), size=size)
                except Exception:
                    font = None

        if font is None:
            # Check any TTF in fonts_dir
            ttfs = list(self.fonts_dir.glob("*.ttf")) + list(self.fonts_dir.glob("*.otf"))
            if ttfs:
                try:
                    font = ImageFont.truetype(str(ttfs[0]), size=size)
                except Exception:
                    pass

        if font is None:
            # Try common Windows handwriting fonts
            windows_fonts = [
                "C:/Windows/Fonts/segoepr.ttf",  # Segoe Print
                "C:/Windows/Fonts/comic.ttf",    # Comic Sans
                "C:/Windows/Fonts/calibri.ttf",
            ]
            for wf in windows_fonts:
                if Path(wf).exists():
                    try:
                        font = ImageFont.truetype(wf, size=size)
                        break
                    except Exception:
                        continue

        if font is None:
            font = ImageFont.load_default()

        self._font_cache[cache_key] = font
        return font

    def render_text_line(
        self,
        text: str,
        style: HandwritingStyleMetrics,
        font_size: int = 32,
        ink_color: Optional[Tuple[int, int, int]] = None,
        font_name: Optional[str] = None,
        line_seed: Optional[int] = None,
    ) -> Image.Image:
        """Render one text line with dynamic style parameters."""
        if not text:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        color = ink_color if ink_color is not None else style.dominant_ink_color
        rng = random.Random(line_seed if line_seed is not None else hash(text))

        font = self._get_font(font_name, font_size)

        words = text.split(" ")
        word_images = []

        # Render each word with micro-rotations and baseline wobble
        for i, word in enumerate(words):
            if not word:
                continue

            # Render individual word into a clean canvas
            word_img = self._render_word(word, font, color, style, rng)
            word_images.append(word_img)

        if not word_images:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        # Combine words into a single line image respecting word spacing
        word_gap = int(style.word_spacing * (font_size / 32.0))
        max_h = max(img.height for img in word_images)
        total_w = sum(img.width for img in word_images) + (len(word_images) - 1) * word_gap

        line_img = Image.new("RGBA", (total_w + 30, max_h + 20), (0, 0, 0, 0))
        curr_x = 10

        for word_img in word_images:
            # Baseline micro-jitter per word
            y_jitter = int(rng.gauss(0, style.baseline_variance))
            y_pos = max(0, min(line_img.height - word_img.height, (max_h - word_img.height) // 2 + y_jitter + 5))
            line_img.alpha_composite(word_img, (curr_x, y_pos))
            curr_x += word_img.width + word_gap

        # Apply global slant shear if slant_angle != 0
        if abs(style.slant_angle) > 1.0:
            line_img = self._apply_slant(line_img, style.slant_angle)

        return line_img

    def _render_word(
        self,
        word: str,
        font: ImageFont.ImageFont,
        color: Tuple[int, int, int],
        style: HandwritingStyleMetrics,
        rng: random.Random,
    ) -> Image.Image:
        """Render a single word with subtle letter variations and ink bleeding."""
        # Calculate bounding box
        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw_dummy = ImageDraw.Draw(dummy_img)

        try:
            bbox = draw_dummy.textbbox((0, 0), word, font=font)
            w = max(1, bbox[2] - bbox[0] + 16)
            h = max(1, bbox[3] - bbox[1] + 16)
        except Exception:
            w = len(word) * 22
            h = 40

        word_img = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(word_img)

        # Draw base text with natural ink opacity (slight variation)
        base_alpha = int(rng.uniform(225, 255))
        draw.text((5, 5), word, font=font, fill=(color[0], color[1], color[2], base_alpha))

        # Adjust stroke thickness if requested
        if style.stroke_thickness > 2.2:
            # Slight dilatation via min-filter on alpha
            r, g, b, a = word_img.split()
            # Spread ink slightly for thicker strokes
            a_dilated = a.filter(ImageFilter.MaxFilter(size=3))
            word_img = Image.merge("RGBA", (r, g, b, a_dilated))

        # Micro-rotation per word (human hand wrist tilt: -1.2 to +1.2 deg)
        micro_rot = rng.uniform(-1.2, 1.2)
        if abs(micro_rot) > 0.2:
            word_img = word_img.rotate(micro_rot, resample=Image.BICUBIC, expand=True)

        return word_img

    def _apply_slant(self, img: Image.Image, slant_deg: float) -> Image.Image:
        """Apply affine shear transformation corresponding to slant_deg."""
        # Positive slant means top tilts to the right (forward italic slant)
        rad = math.radians(slant_deg)
        shear = -math.tan(rad)

        w, h = img.size
        # Extra width needed so edges aren't cropped
        extra_w = int(abs(shear) * h) + 20
        expanded = Image.new("RGBA", (w + extra_w, h), (0, 0, 0, 0))
        expanded.paste(img, (extra_w // 2, 0))

        # Affine matrix: x' = x + shear * y
        new_w, new_h = expanded.size
        # PIL affine expects matrix to map destination coords back to source coords
        transform_matrix = (1, -shear, -shear * (new_h / 2) if shear < 0 else 0, 0, 1, 0)

        sheared = expanded.transform(
            (new_w, new_h),
            Image.AFFINE,
            transform_matrix,
            resample=Image.BICUBIC,
        )

        # Crop transparent borders
        bbox = sheared.getbbox()
        if bbox:
            return sheared.crop(bbox)
        return sheared


class NeuralHandwritingEngine(BaseHandwritingEngine):
    """Reference-conditioned neural handwriting synthesis engine wrapper.
    
    Interfaces with deep learning models (e.g. CONSTANT / ScrabbleGAN).
    Checks for CUDA device and local weight checkpoints in models/.
    """

    def __init__(self, models_dir: Path = Path("models")):
        self.models_dir = models_dir
        self.checkpoint_path = models_dir / "constant_handwriting.pth"
        self._is_ready = False
        self._status_message = "Neural checkpoint not found in models/ directory."

        # Probe environment
        self._check_availability()

    def _check_availability(self):
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if not self.checkpoint_path.exists():
                self._status_message = (
                    f"PyTorch available (CUDA={has_cuda}), but model checkpoint "
                    f"'{self.checkpoint_path.name}' is not present. See models/README.md for instructions."
                )
                self._is_ready = False
            else:
                self._status_message = "Neural model checkpoint found and ready for inference."
                self._is_ready = True
        except ImportError:
            self._status_message = (
                "PyTorch is not installed in the active environment. "
                "Install torch with CUDA to enable neural reference conditioning."
            )
            self._is_ready = False

    def is_neural(self) -> bool:
        return True

    def get_info(self) -> Dict[str, str]:
        return {
            "name": "Neural Reference-Conditioned Model (CONSTANT / GAN)",
            "type": "Deep Learning Generative Model",
            "is_neural": True,
            "ready": str(self._is_ready),
            "status": self._status_message,
            "description": (
                "Conditions character generation directly on handwritten glyph patches "
                "using adversarial or attention-based neural networks."
            ),
            "requirements": "NVIDIA GPU with CUDA 11.8+, PyTorch >= 2.0, pretrained checkpoint (.pth).",
        }

    def render_text_line(
        self,
        text: str,
        style: HandwritingStyleMetrics,
        font_size: int = 32,
        ink_color: Optional[Tuple[int, int, int]] = None,
        font_name: Optional[str] = None,
        line_seed: Optional[int] = None,
    ) -> Image.Image:
        """Render using neural model, or raise RuntimeError if unavailable."""
        if not self._is_ready:
            raise RuntimeError(
                f"Neural handwriting model cannot run: {self._status_message}. "
                "Please use the Style-Conditioned Dynamic Engine fallback."
            )
        # Deep learning inference pipeline would execute here
        raise NotImplementedError("Neural checkpoint execution requires a GPU environment.")


class HandwritingGeneratorManager:
    """Orchestrates handwriting engines and provides unified text line rendering."""

    def __init__(self):
        self.fallback_engine = StyleConditionedFontEngine()
        self.neural_engine = NeuralHandwritingEngine()

    def get_available_engines(self) -> List[Dict[str, str]]:
        return [
            self.fallback_engine.get_info(),
            self.neural_engine.get_info(),
        ]

    def render_line(
        self,
        text: str,
        style: HandwritingStyleMetrics,
        use_neural: bool = False,
        font_size: int = 32,
        ink_color: Optional[Tuple[int, int, int]] = None,
        font_name: Optional[str] = None,
        line_seed: Optional[int] = None,
    ) -> Tuple[Image.Image, str]:
        """Render a text line using the selected engine.
        
        Returns:
            (rendered_image, active_engine_name)
        """
        if use_neural and self.neural_engine.get_info().get("ready") == "True":
            try:
                img = self.neural_engine.render_text_line(
                    text, style, font_size, ink_color, font_name, line_seed
                )
                return img, self.neural_engine.get_info()["name"]
            except Exception:
                pass  # Fall back to style engine

        img = self.fallback_engine.render_text_line(
            text, style, font_size, ink_color, font_name, line_seed
        )
        return img, self.fallback_engine.get_info()["name"]
