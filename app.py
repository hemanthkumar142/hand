"""InkClone AI — AI Handwriting Notes Generator.

Your handwriting. Your notes. Powered by AI.
A hackathon-ready Streamlit web application.
"""

import io
from pathlib import Path
from typing import List, Optional
import streamlit as st
from PIL import Image

from config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_LINE_HEIGHT,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_TOP,
    FONTS_DIR,
    INK_COLORS,
    MAX_FILE_SIZE_MB,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    HandwritingStyleMetrics,
)
from services.handwriting_analyzer import HandwritingAnalyzer
from services.handwriting_generator import HandwritingGeneratorManager
from services.page_renderer import PageRenderer
from services.pdf_exporter import PDFExporter

# Page Configuration
st.set_page_config(
    page_title="InkClone AI — AI Handwriting Notes Generator",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Academic Notebook CSS Styling
st.markdown(
    """
    <style>
    /* Main container styling */
    .main {
        background-color: #F8FAFC;
    }
    
    /* Academic Notebook Header */
    .notebook-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
        color: white;
        padding: 1.8rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.15);
    }
    .notebook-header h1 {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
        margin-bottom: 0.3rem;
        font-size: 2.2rem;
    }
    .notebook-header p {
        color: #E0E7FF;
        font-size: 1.05rem;
        margin-bottom: 0;
    }
    
    /* Feature Card */
    .metric-card {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Badges */
    .badge-info {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-warning {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        background-color: #FEF3C7;
        color: #B45309;
        border: 1px solid #FDE68A;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Privacy Banner */
    .privacy-notice {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.85rem;
        color: #475569;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_services():
    """Cache service instances across app reruns."""
    return {
        "analyzer": HandwritingAnalyzer(),
        "generator_mgr": HandwritingGeneratorManager(),
        "renderer": PageRenderer(),
    }


def init_session_state():
    """Initialize session variables."""
    if "metrics" not in st.session_state:
        st.session_state.metrics = HandwritingStyleMetrics()
    if "sample_image_bytes" not in st.session_state:
        st.session_state.sample_image_bytes = None
    if "sample_filename" not in st.session_state:
        st.session_state.sample_filename = None
    if "generated_pages" not in st.session_state:
        st.session_state.generated_pages = []
    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None
    if "content_text" not in st.session_state:
        st.session_state.content_text = (
            "# Artificial Intelligence & Neural Networks\n\n"
            "Machine learning enables computational systems to discover latent structures within data without explicit rule programming.\n\n"
            "Key Foundations:\n"
            "- Empirical Risk Minimization and loss optimization\n"
            "- Backpropagation via the multivariable chain rule\n"
            "- Attention mechanisms in transformer architectures\n\n"
            "Handwritten notes bridge the kinesthetic cognitive loop, reinforcing mental retention through deliberate spatial-motor synthesis."
        )


def main():
    services = get_services()
    init_session_state()

    # App Header
    st.markdown(
        """
        <div class="notebook-header">
            <h1>✍️ InkClone AI</h1>
            <p>Your handwriting. Your notes. Powered by AI.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Privacy & Safety Notice
    st.markdown(
        """
        <div class="privacy-notice">
            🔒 <strong>Privacy & Responsible AI:</strong> Uploaded handwriting samples are analyzed in-memory 
            to extract geometric style metrics (slant, spacing, stroke width, ink hue) and are never permanently stored 
            or sent to third-party endpoints. Please only use handwriting samples that you own or have permission to use.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar: Paper & Styling Controls
    with st.sidebar:
        st.header("⚙️ Notebook Settings")

        st.subheader("Paper Appearance")
        paper_type = st.selectbox(
            "Paper Type",
            ["Ruled", "Plain", "Graph"],
            index=0,
            help="Choose between classic ruled notebook lines with red margin, plain paper, or grid graph paper.",
        )

        st.subheader("Ink Palette")
        ink_options = list(INK_COLORS.keys())
        # Add sampled ink if available
        if st.session_state.sample_image_bytes is not None:
            ink_options.insert(0, "✨ Analyzed Sample Ink")

        selected_ink_name = st.selectbox("Ink Color", ink_options, index=0)
        if selected_ink_name == "✨ Analyzed Sample Ink":
            active_ink_color = st.session_state.metrics.dominant_ink_color
        else:
            active_ink_color = INK_COLORS[selected_ink_name]

        # Preview of ink color
        ink_hex = f"#{active_ink_color[0]:02x}{active_ink_color[1]:02x}{active_ink_color[2]:02x}"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:0.85rem;color:#4B5563;'>"
            f"Active Ink: <span style='display:inline-block;width:20px;height:20px;border-radius:50%;background-color:{ink_hex};border:1px solid #D1D5DB;'></span> {ink_hex}</div>",
            unsafe_allow_html=True,
        )

        st.subheader("Typography & Geometry")
        # List available fonts in assets/fonts
        font_files = [f.name for f in FONTS_DIR.glob("*.ttf")] + [f.name for f in FONTS_DIR.glob("*.otf")]
        if not font_files:
            font_files = ["Caveat.ttf", "Kalam.ttf", "HomemadeApple.ttf"]

        selected_font = st.selectbox("Base Letterform", font_files, index=0)

        letter_size = st.slider("Letter Size (pt)", min_value=22, max_value=46, value=32, step=2)
        line_spacing = st.slider(
            "Line Spacing (px)",
            min_value=36,
            max_value=64,
            value=int(st.session_state.metrics.line_spacing),
            step=2,
        )

        margin_left = st.slider("Left Margin (px)", min_value=80, max_value=220, value=DEFAULT_MARGIN_LEFT, step=10)
        margin_top = st.slider("Top Margin (px)", min_value=80, max_value=220, value=DEFAULT_MARGIN_TOP, step=10)

        st.subheader("Synthesis Engine Mode")
        engine_infos = services["generator_mgr"].get_available_engines()
        engine_choice = st.radio(
            "Active Synthesis Engine",
            [e["name"] for e in engine_infos],
            index=0,
            help="Style-Conditioned Dynamic Engine operates on CPU with extracted style metrics. Neural Model requires GPU and checkpoint.",
        )
        use_neural = "Neural" in engine_choice

        if use_neural:
            st.info("ℹ️ Neural model mode selected. If checkpoint is absent, system will use dynamic style fallback.")

    # Main Body: 2-Column Responsive Layout
    col_left, col_right = st.columns([1, 1], gap="medium")

    # Left Column: Upload & Input Text
    with col_left:
        st.subheader("1. Reference Handwriting Upload")
        uploaded_file = st.file_uploader(
            "Upload a clear photo or scan of your handwriting (JPG, JPEG, PNG)",
            type=list(ALLOWED_EXTENSIONS),
            help="Upload a sample of handwritten text on clean paper.",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            # If a new image is uploaded, analyze it
            if st.session_state.sample_filename != uploaded_file.name or st.session_state.sample_image_bytes != file_bytes:
                is_valid, err_msg = services["analyzer"].validate_image(file_bytes, uploaded_file.name)
                if not is_valid:
                    st.error(f"⚠️ {err_msg}")
                else:
                    st.session_state.sample_image_bytes = file_bytes
                    st.session_state.sample_filename = uploaded_file.name
                    with st.spinner("Analyzing handwriting style metrics..."):
                        metrics = services["analyzer"].analyze(file_bytes)
                        st.session_state.metrics = metrics
                    st.success("✅ Style analysis complete!")

        # Display Sample & Style Card if loaded
        if st.session_state.sample_image_bytes is not None:
            with st.expander("🔍 Analyzed Style Profile", expanded=True):
                m_cols = st.columns([1, 2])
                with m_cols[0]:
                    try:
                        sample_img = Image.open(io.BytesIO(st.session_state.sample_image_bytes))
                        st.image(sample_img, caption="Reference Sample", use_container_width=True)
                    except Exception:
                        pass
                with m_cols[1]:
                    m = st.session_state.metrics
                    c_hex = f"#{m.dominant_ink_color[0]:02x}{m.dominant_ink_color[1]:02x}{m.dominant_ink_color[2]:02x}"
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <div style="font-weight:600;margin-bottom:6px;">Extracted Handwriting Metrics</div>
                            <div style="font-size:0.88rem;color:#334155;line-height:1.6;">
                                • <strong>Slant Angle:</strong> {m.slant_angle:+.1f}°<br/>
                                • <strong>Stroke Thickness:</strong> {m.stroke_thickness:.1f} px<br/>
                                • <strong>Word Spacing:</strong> {m.word_spacing:.1f} px<br/>
                                • <strong>Baseline Wobble:</strong> ±{m.baseline_variance:.1f} px<br/>
                                • <strong>Sampled Ink Hue:</strong> <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:{c_hex};vertical-align:middle;"></span> {c_hex}<br/>
                                • <strong>Confidence Score:</strong> <span class="badge-info">{int(m.confidence_score * 100)}%</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("💡 Tip: Upload a handwriting sample above to automatically match slant, stroke width, baseline wobble, and ink color.")

        st.subheader("2. Note Content")
        note_title = st.text_input("Document Title (Optional)", placeholder="e.g. CS229: Deep Learning Lecture 4")

        # Preset buttons for convenience
        p_col1, p_col2, p_col3 = st.columns(3)
        if p_col1.button("📝 Study Cheatsheet"):
            st.session_state.content_text = (
                "# Biology: Cellular Respiration\n\n"
                "The biochemical process by which organisms combine oxygen with foodstuff molecules.\n\n"
                "Four Major Stages:\n"
                "- Glycolysis in the cytoplasm (yields 2 ATP + 2 NADH)\n"
                "- Pyruvate Oxidation forming Acetyl-CoA\n"
                "- Krebs Citric Acid Cycle in the mitochondrial matrix\n"
                "- Oxidative Phosphorylation via ATP synthase complex\n\n"
                "Total stoichiometric yield approximates 30 to 32 ATP per glucose molecule."
            )
        if p_col2.button("💼 Meeting Minutes"):
            st.session_state.content_text = (
                "# Product Strategy Sync — Q4 Roadmap\n\n"
                "Attendees: Engineering, Design, AI Product Ops\n\n"
                "Key Decisions:\n"
                "- Finalize prototype release for hackathon demo showcase\n"
                "- Implement modular engine interface for neural model checkpoints\n"
                "- Support multi-page export in both PNG and PDF formats\n\n"
                "Action Items:\n"
                "- Verify responsive mobile layout and touch preview\n"
                "- Complete documentation and testing instructions"
            )
        if p_col3.button("📄 Multi-Page Essay"):
            st.session_state.content_text = (
                "# On the Origin and Evolution of Modern Computing\n\n"
                "The history of computation stretches back centuries before silicon semiconductors. Early mechanical calculation devices like Charles Babbage's Difference Engine laid conceptual foundations for automated calculation.\n\n"
                "In 1936, Alan Turing introduced the concept of a Universal Machine, defining algorithmic procedure through a formal mathematical framework that underpins every modern digital computer today.\n\n"
                "The Post-War Architectural Leap:\n"
                "- John von Neumann formalized the stored-program computer architecture\n"
                "- Claude Shannon connected Boolean algebra with electronic switching circuits\n"
                "- Transistors replaced vacuum tubes, leading to exponential scaling as described by Moore's Law\n\n"
                "The Rise of Artificial Intelligence:\n"
                "From symbolic logic systems in the 1950s to modern deep neural networks with billions of parameters, artificial intelligence represents the culmination of algorithmic reasoning.\n\n"
                "Modern deep learning architectures leverage massive parallel matrix multiplications, high-bandwidth memory hierarchies, and automated differentiation to learn representations directly from data.\n\n"
                "Summary and Future Outlook:\n"
                "As we move towards distributed edge devices and personalized neural models, the synthesis between human handwriting and digital intelligence creates intuitive interfaces for lifelong learning and human-computer symbiosis."
            )

        content_input = st.text_area(
            "Enter or paste English text (supports # headings and - bullet points):",
            value=st.session_state.content_text,
            height=280,
        )
        st.session_state.content_text = content_input

        # Metrics overview
        words_count = len(content_input.split())
        chars_count = len(content_input)
        est_pages = max(1, (words_count // 160) + 1)
        st.caption(f"📊 {words_count} words | {chars_count} characters | Estimated: ~{est_pages} page(s)")

        # Generate Button
        btn_generate = st.button("🚀 Generate Handwritten Notes", type="primary", use_container_width=True)

    # Trigger Generation
    if btn_generate:
        if not content_input.strip():
            st.warning("Please enter some text in the note content editor before generating.")
        else:
            progress_bar = st.progress(0, text="Initializing handwriting layout engine...")
            try:
                progress_bar.progress(25, text="Applying handwriting style parameters (slant, stroke, wobble)...")
                rendered_pages = services["renderer"].render_document(
                    text=content_input,
                    style=st.session_state.metrics,
                    paper_type=paper_type,
                    ink_color=active_ink_color,
                    font_name=selected_font,
                    letter_size=letter_size,
                    line_spacing=line_spacing,
                    margin_left=margin_left,
                    margin_top=margin_top,
                    title=note_title if note_title.strip() else None,
                    use_neural=use_neural,
                )
                progress_bar.progress(70, text="Compiling multi-page high-resolution PDF and PNG documents...")
                pdf_bytes = PDFExporter.export_pdf(rendered_pages)

                st.session_state.generated_pages = rendered_pages
                st.session_state.pdf_bytes = pdf_bytes

                progress_bar.progress(100, text="Generation complete!")
                st.toast(f"Generated {len(rendered_pages)} handwritten page(s) successfully!", icon="✅")
            except Exception as e:
                st.error(f"Error during note generation: {str(e)}")
            finally:
                progress_bar.empty()

    # Right Column: Document Preview & Downloads
    with col_right:
        st.subheader("3. Document Preview & Export")

        if st.session_state.generated_pages:
            pages: List[Image.Image] = st.session_state.generated_pages
            total_pages = len(pages)

            # Page navigation controls
            nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
            with nav_col1:
                page_idx = st.number_input(
                    "Page",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    step=1,
                    key="page_selector",
                ) - 1

            with nav_col2:
                st.markdown(
                    f"<div style='text-align:center;padding-top:28px;font-weight:600;color:#1E3A8A;'>"
                    f"Showing Page {page_idx + 1} of {total_pages}</div>",
                    unsafe_allow_html=True,
                )

            with nav_col3:
                # Regenerate button
                if st.button("🔄 Regenerate", help="Re-run rendering with new random baseline jitter"):
                    with st.spinner("Regenerating..."):
                        rendered_pages = services["renderer"].render_document(
                            text=st.session_state.content_text,
                            style=st.session_state.metrics,
                            paper_type=paper_type,
                            ink_color=active_ink_color,
                            font_name=selected_font,
                            letter_size=letter_size,
                            line_spacing=line_spacing,
                            margin_left=margin_left,
                            margin_top=margin_top,
                            title=note_title if note_title.strip() else None,
                            use_neural=use_neural,
                        )
                        pdf_bytes = PDFExporter.export_pdf(rendered_pages)
                        st.session_state.generated_pages = rendered_pages
                        st.session_state.pdf_bytes = pdf_bytes
                    st.rerun()

            # Render active page preview
            current_page_img = pages[page_idx]
            st.image(
                current_page_img,
                caption=f"InkClone AI — Page {page_idx + 1} of {total_pages} ({paper_type} Paper, A4 format)",
                use_container_width=True,
            )

            # Download Action Bar
            st.markdown("### 📥 Download Options")
            d_col1, d_col2 = st.columns(2)

            with d_col1:
                curr_png_bytes = PDFExporter.export_png(current_page_img)
                st.download_button(
                    label=f"🖼️ Download Page {page_idx + 1} (PNG)",
                    data=curr_png_bytes,
                    file_name=f"inkclone_page_{page_idx + 1}.png",
                    mime="image/png",
                    use_container_width=True,
                )

            with d_col2:
                if st.session_state.pdf_bytes:
                    st.download_button(
                        label=f"📑 Download All {total_pages} Page(s) (PDF)",
                        data=st.session_state.pdf_bytes,
                        file_name="inkclone_notes.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
        else:
            # Placeholder mockup when no document has been generated yet
            st.markdown(
                """
                <div style="border: 2px dashed #CBD5E1; border-radius: 12px; padding: 3.5rem 1.5rem; text-align: center; background-color: #F8FAFC;">
                    <div style="font-size: 3rem; margin-bottom: 0.8rem;">📝</div>
                    <div style="font-weight: 600; font-size: 1.15rem; color: #334155; margin-bottom: 0.4rem;">No Notes Generated Yet</div>
                    <div style="color: #64748B; font-size: 0.9rem; max-width: 380px; margin: 0 auto 1.5rem auto;">
                        Upload a sample handwriting reference image or adjust settings, enter your text on the left, and click <strong>Generate Handwritten Notes</strong>.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
