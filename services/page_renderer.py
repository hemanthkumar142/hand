"""Page Layout and Realistic Notebook Paper Renderer for InkClone AI.

Renders realistic multi-page handwritten notes on:
- Ruled notebook paper (with red vertical margin rule & binder rings)
- Plain white / warm parchment paper
- Graph / grid paper

Handles dynamic word wrapping, headings, bullet points, margins, and multi-page pagination.
"""

import math
import random
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import (
    DEFAULT_LINE_HEIGHT,
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_COLOR,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_RIGHT,
    DEFAULT_MARGIN_TOP,
    DEFAULT_RULE_COLOR,
    GRAPH_GRID_COLOR,
    GRAPH_GRID_SIZE,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    PAPER_BG_CREAM,
    PAPER_BG_OFFWHITE,
    PAPER_BG_WHITE,
    HandwritingStyleMetrics,
)
from services.handwriting_generator import HandwritingGeneratorManager


class PageRenderer:
    """Renders formatted multi-page handwritten documents on realistic notebook paper."""

    def __init__(self):
        self.generator = HandwritingGeneratorManager()

    def render_document(
        self,
        text: str,
        style: HandwritingStyleMetrics,
        paper_type: str = "Ruled",
        ink_color: Optional[Tuple[int, int, int]] = None,
        font_name: str = "Caveat.ttf",
        letter_size: int = 32,
        line_spacing: Optional[int] = None,
        margin_left: int = DEFAULT_MARGIN_LEFT,
        margin_top: int = DEFAULT_MARGIN_TOP,
        margin_right: int = DEFAULT_MARGIN_RIGHT,
        margin_bottom: int = DEFAULT_MARGIN_BOTTOM,
        title: Optional[str] = None,
        use_neural: bool = False,
    ) -> List[Image.Image]:
        """Render complete document into a list of PIL Images (one per page)."""
        color = ink_color if ink_color is not None else style.dominant_ink_color
        effective_line_spacing = line_spacing if line_spacing is not None else int(style.line_spacing)
        effective_line_spacing = max(34, effective_line_spacing)

        # 1. Parse text into structured lines (headings, bullets, body, empty lines)
        structured_lines = self._parse_and_wrap_text(
            text=text,
            max_width=PAGE_WIDTH - margin_left - margin_right,
            style=style,
            font_size=letter_size,
            font_name=font_name,
        )

        pages: List[Image.Image] = []
        page_num = 1

        # Prepare first page
        curr_page = self._create_paper_background(paper_type, effective_line_spacing, margin_top, margin_left)
        draw = ImageDraw.Draw(curr_page)
        curr_y = margin_top

        # Render optional title on Page 1
        if title and title.strip():
            title_text = title.strip()
            title_size = int(letter_size * 1.4)
            title_img, _ = self.generator.render_line(
                text=title_text,
                style=style,
                use_neural=use_neural,
                font_size=title_size,
                ink_color=color,
                font_name=font_name,
                line_seed=101,
            )
            curr_page.alpha_composite(title_img, (margin_left, curr_y - 20))

            # Handwritten style underline
            underline_y = curr_y + title_img.height - 15
            underline_w = min(title_img.width + 10, PAGE_WIDTH - margin_left - margin_right)
            self._draw_handwritten_line(
                curr_page,
                start=(margin_left, underline_y),
                end=(margin_left + underline_w, underline_y + 1),
                color=color,
                thickness=int(style.stroke_thickness),
            )
            curr_y += title_img.height + int(effective_line_spacing * 0.7)

        line_index = 0
        total_items = len(structured_lines)

        while line_index < total_items:
            item = structured_lines[line_index]
            item_type = item["type"]
            item_text = item["text"]
            item_size = item["font_size"]
            indent = item["indent"]

            # Compute height needed for this line
            line_height_needed = effective_line_spacing if item_type != "empty" else int(effective_line_spacing * 0.5)

            # Check for page overflow
            if curr_y + line_height_needed > (PAGE_HEIGHT - margin_bottom):
                # Save current page and start a new one
                pages.append(curr_page.convert("RGB"))
                page_num += 1
                curr_page = self._create_paper_background(paper_type, effective_line_spacing, margin_top, margin_left)
                curr_y = margin_top

            if item_type == "empty":
                curr_y += int(effective_line_spacing * 0.5)
                line_index += 1
                continue

            # Render text line
            line_x = margin_left + indent
            line_seed = (page_num * 1000) + line_index

            line_img, _ = self.generator.render_line(
                text=item_text,
                style=style,
                use_neural=use_neural,
                font_size=item_size,
                ink_color=color,
                font_name=font_name,
                line_seed=line_seed,
            )

            # If bullet point, draw bullet symbol
            if item_type == "bullet":
                bullet_x = margin_left + 10
                bullet_y = curr_y + (letter_size // 2) - 2
                self._draw_handwritten_bullet(curr_page, (bullet_x, bullet_y), color, int(style.stroke_thickness))

            # Paste text onto page
            curr_page.alpha_composite(line_img, (line_x, curr_y - 10))

            curr_y += effective_line_spacing
            line_index += 1

        # Add the final page
        pages.append(curr_page.convert("RGB"))

        # Add subtle handwritten page numbers (e.g. "Page 1 / 3")
        total_pages = len(pages)
        for i, page_img in enumerate(pages):
            self._add_page_number(page_img, i + 1, total_pages, color, font_name)

        return pages

    def _parse_and_wrap_text(
        self,
        text: str,
        max_width: int,
        style: HandwritingStyleMetrics,
        font_size: int,
        font_name: str,
    ) -> List[dict]:
        """Split user text into headings, paragraphs, bullet points, and wrap lines cleanly."""
        raw_lines = text.splitlines() if text else [""]
        structured: List[dict] = []

        # Average char width estimation based on font size
        est_char_w = font_size * 0.52

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                structured.append({"type": "empty", "text": "", "font_size": font_size, "indent": 0})
                continue

            # Heading 1: starts with '#'
            if stripped.startswith("# "):
                h_text = stripped[2:].strip()
                h_size = int(font_size * 1.25)
                wrapped = self._wrap_line(h_text, max_width, h_size, est_char_w * 1.25)
                for w in wrapped:
                    structured.append({"type": "heading1", "text": w, "font_size": h_size, "indent": 0})
                continue

            # Heading 2: starts with '## '
            if stripped.startswith("## "):
                h_text = stripped[3:].strip()
                h_size = int(font_size * 1.12)
                wrapped = self._wrap_line(h_text, max_width, h_size, est_char_w * 1.12)
                for w in wrapped:
                    structured.append({"type": "heading2", "text": w, "font_size": h_size, "indent": 0})
                continue

            # Bullet points: starts with '- ', '* ', or '• '
            if stripped.startswith(("- ", "* ", "• ")):
                bullet_text = stripped[2:].strip()
                bullet_max_w = max_width - 35
                wrapped = self._wrap_line(bullet_text, bullet_max_w, font_size, est_char_w)
                for i, w in enumerate(wrapped):
                    structured.append({
                        "type": "bullet" if i == 0 else "bullet_cont",
                        "text": w,
                        "font_size": font_size,
                        "indent": 35,
                    })
                continue

            # Regular body text
            wrapped = self._wrap_line(stripped, max_width, font_size, est_char_w)
            for w in wrapped:
                structured.append({"type": "body", "text": w, "font_size": font_size, "indent": 0})

        return structured

    def _wrap_line(self, text: str, max_width: int, font_size: int, est_char_w: float) -> List[str]:
        """Wrap text into lines fitting within max_width."""
        words = text.split(" ")
        lines = []
        current_words = []
        current_len = 0

        for word in words:
            word_len = len(word) * est_char_w
            if current_len + word_len + (est_char_w if current_words else 0) <= max_width:
                current_words.append(word)
                current_len += word_len + (est_char_w if len(current_words) > 1 else 0)
            else:
                if current_words:
                    lines.append(" ".join(current_words))
                    current_words = [word]
                    current_len = word_len
                else:
                    lines.append(word)
                    current_words = []
                    current_len = 0

        if current_words:
            lines.append(" ".join(current_words))

        return lines if lines else [""]

    def _create_paper_background(
        self, paper_type: str, line_spacing: int, margin_top: int, margin_left: int
    ) -> Image.Image:
        """Create high-resolution notebook paper texture and rulings."""
        bg_color = PAPER_BG_WHITE if paper_type == "Plain" else PAPER_BG_OFFWHITE
        img = Image.new("RGBA", (PAGE_WIDTH, PAGE_HEIGHT), (*bg_color, 255))
        draw = ImageDraw.Draw(img)

        # 1. Subtle tactile paper noise
        rng = np.random.default_rng(42)
        noise = rng.integers(-4, 4, size=(PAGE_HEIGHT, PAGE_WIDTH), dtype=np.int16)
        base_arr = np.array(img, dtype=np.int16)
        base_arr[:, :, 0] = np.clip(base_arr[:, :, 0] + noise, 0, 255)
        base_arr[:, :, 1] = np.clip(base_arr[:, :, 1] + noise, 0, 255)
        base_arr[:, :, 2] = np.clip(base_arr[:, :, 2] + noise, 0, 255)
        img = Image.fromarray(base_arr.astype(np.uint8), "RGBA")
        draw = ImageDraw.Draw(img)

        # 2. Draw rulings based on paper type
        if paper_type == "Ruled":
            # Horizontal ruling lines
            y = margin_top
            while y < PAGE_HEIGHT - DEFAULT_MARGIN_BOTTOM:
                draw.line([(0, y), (PAGE_WIDTH, y)], fill=DEFAULT_RULE_COLOR, width=1)
                y += line_spacing

            # Vertical red margin line
            margin_x = margin_left - 15
            draw.line([(margin_x, 0), (margin_x, PAGE_HEIGHT)], fill=DEFAULT_MARGIN_COLOR, width=2)

            # Left binder hole punches (faint gray circles)
            for hole_y in [PAGE_HEIGHT // 4, PAGE_HEIGHT // 2, (3 * PAGE_HEIGHT) // 4]:
                draw.ellipse(
                    [(margin_left // 3 - 12, hole_y - 12), (margin_left // 3 + 12, hole_y + 12)],
                    fill=(220, 222, 225, 230),
                    outline=(195, 198, 202, 255),
                    width=2,
                )

        elif paper_type == "Graph":
            # Grid paper
            for gx in range(0, PAGE_WIDTH, GRAPH_GRID_SIZE):
                draw.line([(gx, 0), (gx, PAGE_HEIGHT)], fill=GRAPH_GRID_COLOR, width=1)
            for gy in range(0, PAGE_HEIGHT, GRAPH_GRID_SIZE):
                draw.line([(0, gy), (PAGE_WIDTH, gy)], fill=GRAPH_GRID_COLOR, width=1)

        return img

    def _draw_handwritten_line(
        self,
        img: Image.Image,
        start: Tuple[int, int],
        end: Tuple[int, int],
        color: Tuple[int, int, int],
        thickness: int = 2,
    ):
        """Draw a slightly uneven, natural handwritten line."""
        draw = ImageDraw.Draw(img)
        x1, y1 = start
        x2, y2 = end
        steps = max(5, int(abs(x2 - x1) / 10))
        pts = [(x1, y1)]
        rng = random.Random(42)

        for s in range(1, steps):
            t = s / steps
            px = int(x1 + t * (x2 - x1))
            py = int(y1 + t * (y2 - y1) + rng.uniform(-0.8, 0.8))
            pts.append((px, py))
        pts.append((end[0], end[1]))

        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=(color[0], color[1], color[2], 220), width=thickness)

    def _draw_handwritten_bullet(
        self,
        img: Image.Image,
        pos: Tuple[int, int],
        color: Tuple[int, int, int],
        thickness: int = 2,
    ):
        """Draw an authentic handwritten filled circular dot or dash."""
        draw = ImageDraw.Draw(img)
        x, y = pos
        radius = max(2, thickness + 1)
        draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)], fill=(color[0], color[1], color[2], 230))

    def _add_page_number(
        self,
        img: Image.Image,
        page_num: int,
        total_pages: int,
        color: Tuple[int, int, int],
        font_name: str,
    ):
        """Add page count at the bottom-right of the page."""
        draw = ImageDraw.Draw(img)
        label = f"{page_num} / {total_pages}"
        x = PAGE_WIDTH - DEFAULT_MARGIN_RIGHT - 40
        y = PAGE_HEIGHT - (DEFAULT_MARGIN_BOTTOM // 2) - 10
        faint_color = (color[0], color[1], color[2])
        try:
            draw.text((x, y), label, fill=faint_color)
        except Exception:
            pass
