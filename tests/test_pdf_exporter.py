"""Unit tests for PDF and PNG export functionality."""

import pytest
from PIL import Image

from config import PAGE_HEIGHT, PAGE_WIDTH
from services.pdf_exporter import PDFExporter


class TestPDFExporter:
    def test_export_png(self):
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), (255, 255, 255))
        png_bytes = PDFExporter.export_png(page)
        assert isinstance(png_bytes, bytes)
        assert len(png_bytes) > 0
        # PNG signature: 89 50 4E 47 0D 0A 1A 0A
        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    def test_export_pdf_single_page(self):
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), (255, 255, 255))
        pdf_bytes = PDFExporter.export_pdf([page])
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF signature: %PDF-
        assert pdf_bytes.startswith(b"%PDF-")

    def test_export_pdf_multi_page(self):
        page1 = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), (255, 255, 255))
        page2 = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), (250, 250, 250))
        pdf_bytes = PDFExporter.export_pdf([page1, page2])
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF-")

    def test_export_pdf_empty_raises(self):
        with pytest.raises(ValueError):
            PDFExporter.export_pdf([])
