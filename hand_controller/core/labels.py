from __future__ import annotations


def canonicalize_label(label: str | None) -> str:
    raw = (label or "idle").strip().lower()
    raw = raw.replace("-", " ").replace("__", "_")
    raw = " ".join(raw.split())

    special = {
        "left click": "left_click",
        "right click": "right_click",
        "double click": "left_click",
        "double left click": "left_click",
        "2 fast left click": "left_click",
        "2_fast_left_click": "left_click",
        "leftclick": "left_click",
        "rightclick": "right_click",
        "redo": "redo",
        "undo": "undo",
        "toggle": "toggle",
        "hold": "hold",
        "idle": "idle",
    }
    if raw in special:
        return special[raw]

    raw = raw.replace(" ", "_")
    if raw in special:
        return special[raw]
    if "left" in raw and "click" in raw:
        return "left_click"
    if "right" in raw and "click" in raw:
        return "right_click"
    return raw
