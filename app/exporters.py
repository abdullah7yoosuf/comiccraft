"""Compile the comic layout into a multi-page PDF with FPDF."""
import os
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_FOLDER = BASE_DIR / "static" / "exports"
EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)

# Optional bundled unicode font; falls back to Helvetica when missing.
FONT_PATH = BASE_DIR / "static" / "fonts" / "DejaVuSans.ttf"


def save_pdf(layout) -> str:
    """Save each panel (image + narration) to its own PDF page.

    Args:
        layout: list of dicts with keys panel / title / image_path / text.

    Returns:
        Filesystem path of the saved PDF.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Add Unicode font
    use_dejavu = FONT_PATH.exists()
    if use_dejavu:
        pdf.add_font("Dejavu", "", str(FONT_PATH), uni=True)
        pdf.set_font("Dejavu", "", 12)
    else:
        pdf.set_font("Helvetica", "", 12)

    def _font(style="", size=12):
        pdf.set_font("Dejavu" if use_dejavu else "Helvetica", style, size)

    for panel in layout:
        image_path = panel["image_path"]
        story_text = panel["text"]

        pdf.add_page()

        # Panel title (no bold)
        _font("", 14)
        pdf.cell(0, 10, f"Panel {panel['panel']}", ln=True, align="C")
        if panel.get("title"):
            _font("", 12)
            pdf.cell(0, 8, str(panel["title"])[:90], ln=True, align="C")
        _font("", 12)

        # Image placement
        y_image = 30
        image_height = 100
        spacing_after_image = 15

        if os.path.exists(image_path):
            pdf.image(image_path, x=10, y=y_image, w=pdf.w - 20, h=image_height)
        else:
            pdf.set_y(y_image)
            pdf.multi_cell(0, 10, f"Image missing: {image_path}")

        # Text placement below image
        pdf.set_y(y_image + image_height + spacing_after_image)
        story_lines = story_text.strip().splitlines()
        # Remove title line like "**Panel 1: Title**" if present
        if story_lines and story_lines[0].strip().lower().startswith("**panel"):
            story_lines = story_lines[1:]
        cleaned_text = "\n".join(story_lines).strip()
        if panel.get("scene_description"):
            cleaned_text = f"{panel['scene_description']}\n\n{cleaned_text}".strip()
        # fpdf latin-1 safety when using Helvetica core font
        if not use_dejavu:
            cleaned_text = cleaned_text.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 10, cleaned_text or "(no text)")

    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"comic_{timestamp}.pdf"
    pdf_path = os.path.join(str(EXPORT_FOLDER), filename)
    pdf.output(pdf_path)

    return pdf_path
