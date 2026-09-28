"""Generate full comic narration/dialogue using Gemini.

Uses the new ``google.genai`` SDK with ``gemini-3.8-flash`` by default,
otherwise returns a deterministic local story so the app works offline.
"""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_raw_pro = os.getenv("GEMINI_PRO_MODEL", "gemini-3.8-flash").strip()
PRO_MODEL = _raw_pro.replace("models/", "")

_client = None
_client_kind = None
_old_model = None

if GEMINI_API_KEY:
    try:
        from google import genai as new_genai

        _client = new_genai.Client(api_key=GEMINI_API_KEY)
        _client_kind = "new"
    except Exception as exc:
        print(f"[gemini_pro] new SDK init failed ({exc}), trying old SDK.")
        _client = None
    if _client is None:
        try:
            import google.generativeai as old_genai

            old_genai.configure(api_key=GEMINI_API_KEY)
            _old_model = old_genai.GenerativeModel(PRO_MODEL)
            _client_kind = "old"
        except Exception as exc:  # pragma: no cover
            print(f"[gemini_pro] Gemini init failed, using fallback: {exc}")
            _client_kind = None


def _generate_text(prompt: str) -> str:
    if _client_kind == "new" and _client is not None:
        resp = _client.models.generate_content(model=PRO_MODEL, contents=prompt)
        return resp.text
    if _client_kind == "old" and _old_model is not None:
        resp = _old_model.generate_content(prompt)
        return resp.text
    raise RuntimeError("Gemini client not configured.")


def _fallback_story(outline: list) -> str:
    """Deterministic panel-by-panel story (offline/demo mode)."""
    parts = []
    for i, item in enumerate(outline, start=1):
        if isinstance(item, dict):
            title = item.get("title", f"Panel {i}")
            scene = item.get("scene_description", "")
        else:
            title = f"Panel {i}"
            scene = str(item)
        parts.append(
            f"**Panel {i}: {title}**\n"
            f"**CAPTION:** {scene}\n"
            f"**NARRATION:** Our hero pushes forward, heart pounding with "
            f"determination in '{title}'.\n"
            f'Hero: "I won\'t give up — this is my story to finish!"\n'
        )
    return "\n".join(parts)


def generate_story(outline: list) -> str:
    """Generate a detailed comic story with narration and character dialogue.

    Args:
        outline (list): A list of strings or dicts representing each panel.

    Returns:
        str: The generated comic story text or an error message.
    """
    if not outline:
        return "Error generating story: empty outline."

    if _client_kind is None:
        print("[gemini_pro] No API key -> using local fallback story.")
        return _fallback_story(outline)

    # Format the panel outline as a numbered list for clarity
    def _fmt(i, item):
        if isinstance(item, dict):
            t = item.get("title", "")
            s = item.get("scene_description", "")
            return f"{i + 1}. {t} — {s}"
        return f"{i + 1}. {item}"

    formatted_outline = "\n".join(_fmt(i, item) for i, item in enumerate(outline))

    # Construct the prompt
    prompt = f"""You're a comic book writer.

Given the following panel breakdown, write a comic-style story with engaging narration and character dialogues for each panel.

Panel Outline:
{formatted_outline}

Guidelines:
- Use a fun and engaging tone, like an actual comic book.
- Include narration and clearly marked character lines.
- Keep each panel self-contained but part of a cohesive story.
- Start EVERY panel with a heading exactly like: **Panel N: Title**
- Inside each panel include lines starting with **CAPTION:** and **NARRATION:**.
"""

    try:
        return _generate_text(prompt)
    except Exception as e:
        return f"Error generating story: {str(e)}"
