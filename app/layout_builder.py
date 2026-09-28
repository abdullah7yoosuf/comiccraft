"""Assemble images + story text + outline into a render-ready layout."""


def build_comic_layout(image_paths, full_story, outline):
    """Organize generated images and story into a structured layout.

    Args:
        image_paths: list of saved image file paths (one per panel).
        full_story: single formatted story string containing ``**Panel`` markers.
        outline: list of panel dicts with title / scene_description.

    Returns:
        list of dicts: {panel, title, image_path, text, scene_description}.
    """
    # Split the full story into individual panel segments
    story_panels = full_story.split("**Panel")
    story_panels = [f"**Panel{panel}" for panel in story_panels if panel.strip()]

    # Fallback: if the model did not emit **Panel markers, chunk by outline.
    if not story_panels:
        story_panels = [str(full_story)] * max(1, len(outline or image_paths or [1]))

    # Build layout panel by panel
    layout = []
    outline = outline or []
    for idx, (image, text, panel_info) in enumerate(
        zip(image_paths, story_panels, outline), start=1
    ):
        panel_info = panel_info if isinstance(panel_info, dict) else {}
        layout.append(
            {
                "panel": idx,
                "title": panel_info.get("title", f"Panel {idx}"),
                "image_path": image,
                "text": "\n".join(text.strip().splitlines()[1:]).strip(),  # remove panel title
                "scene_description": panel_info.get("scene_description", ""),
            }
        )

    # If counts mismatch (e.g. more images than story chunks), pad gracefully.
    if len(layout) < len(image_paths):
        for idx in range(len(layout) + 1, len(image_paths) + 1):
            info = outline[idx - 1] if idx - 1 < len(outline) else {}
            if not isinstance(info, dict):
                info = {}
            layout.append(
                {
                    "panel": idx,
                    "title": info.get("title", f"Panel {idx}"),
                    "image_path": image_paths[idx - 1],
                    "text": "",
                    "scene_description": info.get("scene_description", ""),
                }
            )
    return layout
