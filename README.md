# ✍️ InkClone AI — AI Handwriting Notes Generator

> *"Your handwriting. Your notes. Powered by AI."*

**InkClone AI** is a complete, hackathon-ready full-stack web application that takes an uploaded photograph or scanned image of a user's handwriting, extracts its physical stylistic properties (slant angle, stroke thickness, word and character spacing, baseline wobble, and ink hue), and synthesizes multi-page realistic handwritten notes on customizable notebook paper.

The generated documents are downloadable as **high-resolution PNG images** and unified **multi-page PDF documents**.

---

## 🌟 Key Features

1. **Handwriting Reference Upload & Computer Vision Analysis**:
   - Drag-and-drop upload for `JPG`, `JPEG`, and `PNG`.
   - Automated preprocessing with OpenCV (Otsu thresholding, Gaussian blur, contour moments, and Euclidean distance transform).
   - Real-time extraction of:
     - **Slant Angle** (degrees from vertical)
     - **Stroke Thickness** (distance transform radius)
     - **Word & Character Spacing** (inter-contour bounding gaps)
     - **Baseline Drift / Wobble** (local vertical variance across lines)
     - **Sampled Ink Color** (dominant foreground color in original image)

2. **Rich Text Formatting & Multi-Page Pagination**:
   - Full support for `# Headings`, `## Subheadings`, bullet points (`- `, `* `), and indented lists.
   - Intelligent word wrapping preventing text clipping or overflow.
   - Automatic multi-page pagination splitting long notes cleanly across A4 pages.

3. **Notebook Page Customization**:
   - **Paper Types**: Ruled notebook paper (with faint blue rules, red vertical margin, and binder hole punches), clean white/cream parchment, and grid graph paper.
   - **Ink Palette**: Royal Blue, Deep Navy, Classic Black, Charcoal, or the **✨ Analyzed Sample Ink** automatically extracted from the user's uploaded image.
   - **Typography Controls**: Letter size, line spacing, margins, and optional title with authentic handwritten underline.

4. **Modular AI & Synthesis Architecture**:
   - **Style-Conditioned Dynamic Engine (Active Fallback)**: Runs 100% locally on CPU without requiring an external GPU or multi-gigabyte checkpoints. Applies stochastic micro-jitter, affine shear slant, baseline drift, and stroke dilation.
   - **Neural Model Plugin Interface**: Built-in architecture supporting deep learning models (such as CONSTANT or ScrabbleGAN). Automatically detects PyTorch, CUDA, and weights in `models/`.
   - **Transparency & Safety**: The app clearly distinguishes style-conditioned font modulation from biometric generative neural models, never making false claims about exact glyph cloning in fallback mode.

5. **Export & Sharing**:
   - Single-page high-resolution PNG download.
   - Combined multi-page PDF compilation.
   - In-memory processing preserving user privacy (no permanent disk storage of uploaded handwriting).

---

## 📁 Project Structure

```
inkclone-ai/
├── app.py                      # Main Streamlit web application
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation & setup instructions
├── .gitignore                  # Python ignore rules
├── config.py                   # Global layout, dimensions, paper and ink settings
├── pytest.ini                  # Pytest configuration
├── services/
│   ├── __init__.py
│   ├── handwriting_analyzer.py # OpenCV & PIL style feature extraction
│   ├── handwriting_generator.py# Modular handwriting synthesis (Style-Conditioned + Neural)
│   ├── page_renderer.py        # Realistic notebook paper renderer and pagination
│   └── pdf_exporter.py         # Multi-page PDF and PNG byte generation
├── models/
│   └── README.md               # Technical survey of CONSTANT, ScrabbleGAN, HWT, and GPU setup
├── assets/
│   └── fonts/                  # Bundled open-source handwriting fonts (Caveat, Kalam, Homemade Apple)
└── tests/
    ├── test_renderer.py        # Unit tests for analyzer, generator, and layout
    ├── test_pdf_exporter.py    # Unit tests for PDF & PNG export
    └── test_e2e_integration.py # Full end-to-end integration test
```

---

## 🚀 Quickstart & Setup Instructions

### Prerequisites
- Python 3.11+
- `uv` (recommended) or standard `pip`

---

### Windows (PowerShell)

1. **Clone or enter the project directory**:
   ```powershell
   cd c:\handnoo
   ```

2. **Create and activate the virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the unit tests**:
   ```powershell
   pytest -v
   ```

5. **Start the application**:
   ```powershell
   streamlit run app.py
   ```
   Open your browser to: [http://localhost:8501](http://localhost:8501)

---

### macOS / Linux (Bash / Zsh)

1. **Enter directory**:
   ```bash
   cd inkclone-ai
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run unit tests**:
   ```bash
   pytest -v
   ```

5. **Start application**:
   ```bash
   streamlit run app.py
   ```
   Open your browser to: [http://localhost:8501](http://localhost:8501)

---

## 🧪 Running Automated Tests

InkClone AI includes a full test suite with 14 automated tests covering image validation, OpenCV style extraction, multi-page pagination, paper layouts, PDF compilation, and end-to-end workflows:

```bash
pytest -v
```

All 14 tests pass with 100% success rate:
- `test_complete_e2e_workflow`: PASSED
- `test_export_png`: PASSED
- `test_export_pdf_single_page`: PASSED
- `test_export_pdf_multi_page`: PASSED
- `test_export_pdf_empty_raises`: PASSED
- `test_validate_image_valid`: PASSED
- `test_validate_image_empty`: PASSED
- `test_validate_image_bad_extension`: PASSED
- `test_analyze_synthetic_sample`: PASSED
- `test_style_conditioned_engine_info`: PASSED
- `test_render_line_output`: PASSED
- `test_render_single_page`: PASSED
- `test_multi_page_pagination`: PASSED
- `test_paper_types`: PASSED

---

## 🧠 Pretrained Neural Model (GPU Integration)

The application features a modular architecture designed to support reference-conditioned neural models (such as CONSTANT or ScrabbleGAN) when run in a GPU environment.

- To connect a pretrained model checkpoint, place the weight file at:
  ```
  models/constant_handwriting.pth
  ```
- Install PyTorch with CUDA support:
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  ```
- Detailed architecture, licensing, and configuration details are documented in [`models/README.md`](models/README.md).

---

## 🔒 Privacy & Safety Notice

- Uploaded handwriting samples are processed strictly in-memory during the active browser session and are never saved to permanent storage or sent to external servers.
- Users are advised to only upload handwriting samples they own or have explicit permission to use.

---

## 📄 License

MIT License. Designed and built for hackathons, educational note generation, and human-centered AI research.
