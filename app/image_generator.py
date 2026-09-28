"""Comic illustration generation.

Primary (spec) path: Hugging Face Diffusers Stable Diffusion
``runwayml/stable-diffusion-v1-5`` — enabled only when
``USE_STABLE_DIFFUSION=1`` to avoid heavy torch downloads on small machines.

Default path: lightweight Pillow placeholder panel so the whole pipeline
(text -> images -> layout -> PDF) works offline with zero GPU.
"""
import hashlib
import os
import re
import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PANEL_DIR = BASE_DIR / "static" / "panels"
PANEL_DIR.mkdir(parents=True, exist_ok=True)

USE_SD = os.getenv("USE_STABLE_DIFFUSION", "0") == "1"
SD_MODEL = os.getenv("SD_MODEL", "runwayml/stable-diffusion-v1-5")

_pipe = None
if USE_SD:  # lazy-load heavy deps only on demand
    try:
        import torch
        from diffusers import StableDiffusionPipeline

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        _pipe = StableDiffusionPipeline.from_pretrained(SD_MODEL, torch_dtype=dtype)
        if torch.cuda.is_available():
            _pipe = _pipe.to("cuda")
        print(f"[image_generator] Stable Diffusion loaded: {SD_MODEL}")
    except Exception as exc:
        print(f"[image_generator] SD load failed ({exc}); using placeholders.")
        _pipe = None


def sanitize_filename(prompt: str) -> str:
    """Create a filesystem-safe filename from a prompt."""
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", (prompt or "panel").strip().lower())
    name = name.strip("_")[:60] or "panel"
    digest = hashlib.md5((prompt or "").encode("utf-8")).hexdigest()[:8]
    return f"{name}_{digest}.png"


def _placeholder(prompt: str, path: Path) -> str:
    """Draw a comic-style placeholder image with Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    digest = hashlib.md5(prompt.encode("utf-8")).digest()
    r, g, b = 60 + digest[0] % 160, 90 + digest[1] % 120, 120 + digest[2] % 110
    img = Image.new("RGB", (512, 512), (r, g, b))
    draw = ImageDraw.Draw(img)
    # panel border + caption boxes (comic feel)
    draw.rectangle([8, 8, 504, 504], outline=(255, 255, 255), width=6)
    draw.rectangle([8, 8, 504, 110], fill=(20, 20, 20))
    try:
        font_big = ImageFont.truetype("arial.ttf", 26)
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_big = ImageFont.load_default()
        font = ImageFont.load_default()
    draw.text((24, 28), "COMICCRAFT", fill=(255, 210, 63), font=font_big)
    draw.text((24, 62), "AI panel (demo image)", fill=(255, 255, 255), font=font)
    wrapped = textwrap.fill(prompt, width=38)
    draw.multiline_text((24, 140), wrapped[:600], fill=(255, 255, 255), font=font, spacing=6)
    draw.rectangle([8, 440, 504, 504], fill=(255, 255, 255))
    draw.text((24, 458), "Replace with Stable Diffusion", fill=(30, 30, 30), font=font)
    img.save(path)
    return str(path)


def generate_image(prompt: str, filename: str | None = None) -> str:
    """Create a comic-style image for *prompt* and return its saved path."""
    if not filename:
        filename = sanitize_filename(prompt)
    path = PANEL_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    if _pipe is not None:
        try:
            image = _pipe(prompt).images[0]
            image.save(str(path))
            return str(path)
        except Exception as exc:
            print(f"[image_generator] SD inference failed ({exc}); placeholder used.")

    _placeholder(prompt, path)
    return str(path)
