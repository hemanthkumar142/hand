"""PDF and High-Resolution Image Exporter for InkClone AI.

Converts multi-page handwritten notes into:
- Combined multi-page PDF document
- High-resolution individual PNG images
"""

import io
from typing import List
from PIL import Image


class PDFExporter:
    """Exports rendered pages to PDF and PNG formats."""

    @staticmethod
    def export_pdf(pages: List[Image.Image]) -> bytes:
        """Convert a list of PIL Images into a multi-page PDF document in-memory."""
        if not pages:
            raise ValueError("No pages provided for PDF export.")

        pdf_buffer = io.BytesIO()

        # Convert all pages to RGB (PDF format does not support RGBA transparency)
        rgb_pages = [page.convert("RGB") if page.mode != "RGB" else page for page in pages]

        # Use PIL's high-fidelity PDF exporter
        first_page = rgb_pages[0]
        other_pages = rgb_pages[1:] if len(rgb_pages) > 1 else []

        first_page.save(
            pdf_buffer,
            format="PDF",
            save_all=True,
            append_images=other_pages,
            resolution=150.0,
            quality=95,
        )

        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    @staticmethod
    def export_png(page: Image.Image) -> bytes:
        """Convert a single PIL Image into a high-resolution PNG in-memory."""
        png_buffer = io.BytesIO()
        rgb_page = page.convert("RGB") if page.mode != "RGB" else page
        rgb_page.save(png_buffer, format="PNG", dpi=(150, 150), optimize=True)
        png_buffer.seek(0)
        return png_buffer.getvalue()
