"""Generate a structured 5-panel comic outline using Gemini.

Uses the new ``google.genai`` SDK with ``gemini-3.8-flash`` by default.
Falls back to a deterministic local outline so the app runs without a key
(demo / offline mode).
"""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
# New users are blocked from 1.5/2.5 -> use 3.8-flash (strip "models/" for new SDK).
_raw_flash = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.8-flash").strip()
FLASH_MODEL = _raw_flash.replace("models/", "")

_client = None
_client_kind = None  # "new" (google.genai) or "old" (google.generativeai)
_old_model = None

if GEMINI_API_KEY:
    # Preferred: new SDK (google-genai package)
    try:
        from google import genai as new_genai

        _client = new_genai.Client(api_key=GEMINI_API_KEY)
        _client_kind = "new"
    except Exception as exc:
        print(f"[gemini_flash] new SDK init failed ({exc}), trying old SDK.")
        _client = None
    # Legacy fallback: old SDK
    if _client is None:
        try:
            import google.generativeai as old_genai

            old_genai.configure(api_key=GEMINI_API_KEY)
            _old_model = old_genai.GenerativeModel(FLASH_MODEL)
            _client_kind = "old"
        except Exception as exc:
            print(f"[gemini_flash] Gemini init failed, using fallback: {exc}")
            _client_kind = None


def _generate_text(prompt: str) -> str:
    """Generate text via new SDK, else old SDK."""
    if _client_kind == "new" and _client is not None:
        resp = _client.models.generate_content(model=FLASH_MODEL, contents=prompt)
        return resp.text.strip()
    if _client_kind == "old" and _old_model is not None:
        resp = _old_model.generate_content(prompt)
        return resp.text.strip()
    raise RuntimeError("Gemini client not configured.")


def _fallback_outline(user_prompt: str) -> list:
    """Build a deterministic 5-panel outline without calling the API."""
    base = (user_prompt or "A brave hero on an adventure").strip()
    short = base if len(base) <= 140 else base[:137] + "..."
    beats = [
        ("The Beginning", "Introduce the hero and the world; set up the quest."),
        ("Into the Adventure", "The hero leaves comfort behind and enters the unknown."),
        ("The Challenge", "An obstacle or villain tests the hero's courage."),
        ("The Twist", "A surprising discovery changes everything."),
        ("Triumph", "The hero resolves the story with heart and humor."),
    ]
    outline = []
    for i, (title, beat) in enumerate(beats, start=1):
        outline.append(
            {
                "panel": i,
                "title": title,
                "scene_description": f"{beat} Context: {short}",
                "image_prompt": (
                    f"comic panel illustration, {beat} "
                    f"Story: {short}, vivid colors, dynamic composition"
                ),
            }
        )
    return outline


def generate_outline(user_prompt: str) -> list:
    """Generate a 5-panel comic layout based on the user's story idea.

    Args:
        user_prompt (str): The user's comic idea prompt (already combined
            with character / setting / tone / art style by the route).

    Returns:
        list: A list of dictionaries, one for each panel.
    """
    if not user_prompt or not user_prompt.strip():
        user_prompt = "A brave fox exploring an enchanted forest."

    if _client_kind is None:
        print("[gemini_flash] No API key -> using local fallback outline.")
        return _fallback_outline(user_prompt)

    prompt = f"""You are a professional AI comic planner.

Your task is to generate a *strictly formatted* JSON array containing 5 panel descriptions for a comic based on the story idea below:

STORY: "{user_prompt}"

Each JSON object must include:
- "panel" (integer)
- "title" (string)
- "scene_description" (string)
- "image_prompt" (string)

Respond ONLY in this valid JSON format, without any explanations or markdown:
[
  {{{{
    "panel": 1,
    "title": "Title here",
    "scene_description": "Scene description here",
    "image_prompt": "Image prompt for Stable Diffusion"
  }}}},
  ...
]
"""
    output_text = ""
    try:
        output_text = _generate_text(prompt)

        print("\n🔥 RAW GEMINI RESPONSE 🔥\n", output_text)

        # Remove any markdown formatting if present
        if output_text.startswith("```json"):
            output_text = output_text.replace("```json", "").replace("```", "").strip()
        elif output_text.startswith("```"):
            output_text = output_text.replace("```", "").strip()
        # Sometimes the model wraps JSON in extra prose; extract the array.
        if not output_text.startswith("["):
            match = re.search(r"\[.*\]", output_text, re.DOTALL)
            if match:
                output_text = match.group(0)

        panel_data = json.loads(output_text)

        # Additional structure validation
        if not isinstance(panel_data, list):
            raise ValueError("Gemini response is not a list.")

        for panel in panel_data:
            if not isinstance(panel, dict) or not all(
                key in panel
                for key in ("panel", "title", "scene_description", "image_prompt")
            ):
                raise ValueError(f"Invalid panel format or missing keys: {panel}")

        return panel_data

    except json.JSONDecodeError as e:
        print("❌ JSON Decode Error:", e)
        print("❌ Full Text Received:\n", output_text)
        return [{"error": f"JSON parsing failed: {str(e)}"}]
    except Exception as e:
        print("❌ Unexpected Error:", e)
        # Graceful degradation: still return a usable outline.
        print("[gemini_flash] Falling back to local outline.")
        return _fallback_outline(user_prompt)
