"""End-to-end integration test for InkClone AI full pipeline."""

import io
from PIL import Image, ImageDraw

from config import HandwritingStyleMetrics, INK_COLORS, PAGE_HEIGHT, PAGE_WIDTH
from services.handwriting_analyzer import HandwritingAnalyzer
from services.page_renderer import PageRenderer
from services.pdf_exporter import PDFExporter


def test_complete_e2e_workflow():
    # 1. Create a simulated realistic handwriting reference image
    img = Image.new("RGB", (800, 400), (245, 242, 235))
    draw = ImageDraw.Draw(img)
    ink_color = (20, 50, 110)

    # Draw simulated handwriting lines with slant and thickness
    for row_y in [80, 160, 240, 320]:
        for x_start in range(60, 700, 120):
            # Draw slanted word strokes
            draw.line([(x_start, row_y + 10), (x_start + 15, row_y - 25)], fill=ink_color, width=3)
            draw.ellipse([(x_start + 15, row_y - 15), (x_start + 65, row_y + 8)], outline=ink_color, width=3)
            draw.line([(x_start + 65, row_y - 20), (x_start + 75, row_y + 10)], fill=ink_color, width=2)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    raw_sample_bytes = buf.getvalue()

    # 2. Analyze the uploaded sample
    analyzer = HandwritingAnalyzer()
    is_valid, err = analyzer.validate_image(raw_sample_bytes, "reference_handwriting.jpg")
    assert is_valid is True, f"Validation failed: {err}"

    metrics = analyzer.analyze(raw_sample_bytes)
    assert isinstance(metrics, HandwritingStyleMetrics)
    assert metrics.confidence_score > 0.3
    assert len(metrics.dominant_ink_color) == 3

    # 3. Render multi-page text notes with title, headings, and bullet points
    renderer = PageRenderer()
    sample_notes = (
        "# Quantum Computing Architecture\n\n"
        "Quantum computing harnesses the phenomena of superposition and entanglement.\n\n"
        "Fundamental Principles:\n"
        "- Qubits exist in linear combinations of |0> and |1> basis states\n"
        "- Unitary transformations preserve quantum state norm\n"
        "- Quantum decoherence limits gate fidelity in NISQ devices\n\n"
        + "\n\n".join([f"Supplementary Topic {i}: Error correction algorithms and surface codes." for i in range(25)])
    )

    pages = renderer.render_document(
        text=sample_notes,
        style=metrics,
        paper_type="Ruled",
        ink_color=metrics.dominant_ink_color,
        letter_size=32,
        title="Physics 301: Quantum Mechanics",
    )

    assert len(pages) >= 2, f"Expected multiple pages, got {len(pages)}"
    for p in pages:
        assert p.size == (PAGE_WIDTH, PAGE_HEIGHT)

    # 4. Export to PNG and PDF
    for i, p in enumerate(pages):
        png_data = PDFExporter.export_png(p)
        assert len(png_data) > 1000
        assert png_data.startswith(b"\x89PNG\r\n\x1a\n")

    pdf_data = PDFExporter.export_pdf(pages)
    assert len(pdf_data) > 5000
    assert pdf_data.startswith(b"%PDF-")
