"""All FastAPI routing logic for ComicCraft (routes.py)."""
import traceback
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .exporters import save_pdf
from .gemini_flash import generate_outline
from .gemini_pro import generate_story
from .image_generator import generate_image
from .layout_builder import build_comic_layout

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


class PromptRequest(BaseModel):
    prompt: str
    character_name: str = "Hero"
    setting: str = "forest"
    tone: str = "dramatic"
    style: str = "comic book"


def _run_pipeline(prompt: str, character_name: str, setting: str, tone: str, style: str):
    """Shared comic-generation pipeline used by form + JSON routes."""
    # Combine user input into a single full prompt
    full_prompt = (
        f"{prompt}\n"
        f"The main character is {character_name}. "
        f"The setting is a {setting}. "
        f"The tone is {tone}. The art style is {style}."
    )

    # Step 1: Generate panel outline
    outline = generate_outline(full_prompt)

    if not isinstance(outline, list) or not all(
        "image_prompt" in panel for panel in outline if isinstance(panel, dict)
    ):
        raise ValueError("Invalid outline structure from Gemini response.")

    # Step 2: Generate story
    full_story = generate_story(outline)

    # Step 3: Generate images
    images = [generate_image(panel["image_prompt"]) for panel in outline]

    # Step 4: Build layout
    layout = build_comic_layout(images, full_story, outline)

    # Step 5: Export to PDF
    pdf_path = save_pdf(layout)
    web_pdf_path = "/" + pdf_path.replace("\\", "/").split(":/")[-1].lstrip("/")
    # Keep a path safe for web: prefer static-relative path.
    # e.g. C:/.../static/exports/x.pdf -> /static/exports/x.pdf
    if "/static/" in web_pdf_path:
        web_pdf_path = web_pdf_path[web_pdf_path.index("/static/") :]
    else:  # pragma: no cover
        web_pdf_path = "/" + pdf_path.replace("\\", "/")  # Make path safe for web

    # Web-friendly image URLs (templates serve from /static).
    for item in layout:
        p = str(item.get("image_path", "")).replace("\\", "/")
        if "/static/" in p:
            item["image_path"] = p[p.index("/static/") :]

    return layout, full_story, outline, pdf_path, web_pdf_path


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/generate", response_class=HTMLResponse)
async def generate_comic(
    request: Request,
    prompt: str = Form(...),
    character_name: str = Form(...),
    setting: str = Form(...),
    tone: str = Form(...),
    style: str = Form(...),
):
    try:
        layout, full_story, outline, pdf_path, web_pdf_path = _run_pipeline(
            prompt, character_name, setting, tone, style
        )
        return templates.TemplateResponse(
            request,
            "comic_preview.html",
            {
                "layout": layout,
                "pdf_path": web_pdf_path,
            },
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-comic/json")
async def generate_comic_json(data: PromptRequest):
    try:
        layout, full_story, outline, pdf_path, web_pdf_path = _run_pipeline(
            data.prompt, data.character_name, data.setting, data.tone, data.style
        )
        return {"layout": layout, "pdf_path": web_pdf_path, "story": full_story}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-success", response_class=HTMLResponse)
async def export_success(request: Request, pdf_path: str = ""):
    return templates.TemplateResponse(
        request, "export_success.html", {"pdf_path": pdf_path}
    )


@router.get("/test-image")
async def test_image(prompt: str = "A futuristic city at sunset, sci-fi, cinematic, artstation"):
    try:
        image_path = generate_image(prompt)
        return {"message": "Image generated successfully", "path": image_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
