"""Unit tests for handwriting analysis, style synthesis, and page rendering."""

import io
import pytest
from PIL import Image, ImageDraw

from config import HandwritingStyleMetrics, PAGE_HEIGHT, PAGE_WIDTH
from services.handwriting_analyzer import HandwritingAnalyzer
from services.handwriting_generator import HandwritingGeneratorManager, StyleConditionedFontEngine
from services.page_renderer import PageRenderer


def create_synthetic_handwriting_sample() -> bytes:
    """Generate a synthetic handwriting sample image for testing."""
    img = Image.new("RGB", (600, 300), (250, 248, 245))
    draw = ImageDraw.Draw(img)
    # Draw dark blue handwritten-like strokes
    color = (25, 55, 120)
    for y in [60, 130, 200]:
        draw.line([(50, y), (550, y)], fill=(220, 225, 230), width=1)
        # Draw some word blobs
        for x in range(70, 500, 80):
            draw.ellipse([(x, y - 18), (x + 60, y + 6)], outline=color, width=3)
            draw.line([(x + 20, y - 25), (x + 20, y + 10)], fill=color, width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestHandwritingAnalyzer:
    def test_validate_image_valid(self):
        analyzer = HandwritingAnalyzer()
        sample_bytes = create_synthetic_handwriting_sample()
        is_valid, err = analyzer.validate_image(sample_bytes, "sample.png")
        assert is_valid is True
        assert err is None

    def test_validate_image_empty(self):
        analyzer = HandwritingAnalyzer()
        is_valid, err = analyzer.validate_image(b"", "sample.png")
        assert is_valid is False
        assert "empty" in err.lower()

    def test_validate_image_bad_extension(self):
        analyzer = HandwritingAnalyzer()
        sample_bytes = create_synthetic_handwriting_sample()
        is_valid, err = analyzer.validate_image(sample_bytes, "sample.gif")
        assert is_valid is False
        assert "unsupported" in err.lower()

    def test_analyze_synthetic_sample(self):
        analyzer = HandwritingAnalyzer()
        sample_bytes = create_synthetic_handwriting_sample()
        metrics = analyzer.analyze(sample_bytes)
        assert isinstance(metrics, HandwritingStyleMetrics)
        assert -25.0 <= metrics.slant_angle <= 25.0
        assert metrics.stroke_thickness >= 1.0
        assert metrics.word_spacing >= 10.0
        assert len(metrics.dominant_ink_color) == 3


class TestHandwritingGenerator:
    def test_style_conditioned_engine_info(self):
        engine = StyleConditionedFontEngine()
        info = engine.get_info()
        assert info["is_neural"] is False
        assert "Style-Conditioned" in info["name"]

    def test_render_line_output(self):
        engine = StyleConditionedFontEngine()
        metrics = HandwritingStyleMetrics(slant_angle=8.0, stroke_thickness=2.5)
        img = engine.render_text_line("Hello InkClone AI", style=metrics, font_size=32)
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
        assert img.mode == "RGBA"


class TestPageRenderer:
    def test_render_single_page(self):
        renderer = PageRenderer()
        metrics = HandwritingStyleMetrics()
        sample_text = (
            "# Lecture 1: Machine Learning\n\n"
            "This is an introductory lecture note on neural networks.\n"
            "- Concept A: Gradient descent optimization\n"
            "- Concept B: Backpropagation through time\n\n"
            "End of introductory summary."
        )
        pages = renderer.render_document(
            text=sample_text,
            style=metrics,
            paper_type="Ruled",
            letter_size=32,
            title="CS229 Study Notes",
        )
        assert len(pages) == 1
        assert pages[0].size == (PAGE_WIDTH, PAGE_HEIGHT)
        assert pages[0].mode == "RGB"

    def test_multi_page_pagination(self):
        renderer = PageRenderer()
        metrics = HandwritingStyleMetrics(line_spacing=44.0)
        # Create enough content to exceed 1 page (A4 holds approx 32 lines)
        long_text = "\n".join([f"Line {i}: Detailed notes on distributed system theory and consistency models." for i in range(50)])
        pages = renderer.render_document(
            text=long_text,
            style=metrics,
            paper_type="Ruled",
            letter_size=30,
            line_spacing=44,
        )
        assert len(pages) >= 2, f"Expected multiple pages, got {len(pages)}"
        for page in pages:
            assert page.size == (PAGE_WIDTH, PAGE_HEIGHT)

    def test_paper_types(self):
        renderer = PageRenderer()
        metrics = HandwritingStyleMetrics()
        for ptype in ["Ruled", "Plain", "Graph"]:
            pages = renderer.render_document(text="Test note.", style=metrics, paper_type=ptype)
            assert len(pages) == 1
            assert pages[0].size == (PAGE_WIDTH, PAGE_HEIGHT)
