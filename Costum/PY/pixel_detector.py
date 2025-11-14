import numpy as np
from PIL import ImageGrab
import pygetwindow as gw
from .logger import log
from .config import window_title

# --- Pixel-Erkennungsparameter ---
STABILITY_FRAMES = 2  # Anzahl stabiler Frames, bevor Trigger auslöst

def hex_to_rgb(h):
    """Convert hex color (0xRRGGBB) to RGB tuple."""
    h = h.replace("0x", "")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def check_pixel_regions(pixel_regions, state):
    """
    Überprüft definierte Pixelregionen auf exakte Farbtreffer.
    Gibt (triggered, region_id) zurück.
    """
    if not pixel_regions:
        return False, None

    wins = gw.getWindowsWithTitle(window_title)
    if not wins:
        return False, None

    w = wins[0]
    win_left, win_top = w.left, w.top
    triggered = False
    region_id = None
    matched_any = False

    for region in pixel_regions:
        region_id = region.get("Region", None)
        cx, cy = region["center"]["x"], region["center"]["y"]
        is_rel = region.get("relative", False)
        cx_abs = win_left + cx if is_rel else cx
        cy_abs = win_top + cy if is_rel else cy

        try:
            img = ImageGrab.grab(bbox=(cx_abs, cy_abs, cx_abs + 1, cy_abs + 1))
            pixel_color = img.getpixel((0, 0))
        except Exception:
            continue

        ref_colors = [hex_to_rgb(region["avg_color"])] + [
            hex_to_rgb(c) for c in region.get("samples", [])
        ]

        if any(pixel_color == ref for ref in ref_colors):
            matched_any = True

            # Wenn derselbe Pixelbereich wie vorher erkannt wurde → Streak erhöhen
            if state.get("last_region_id") == region_id and state.get("last_pixel_color") == pixel_color:
                state["pixel_streak"] += 1
            else:
                state["pixel_streak"] = 1

            state["last_region_id"] = region_id
            state["last_pixel_color"] = pixel_color

            log(f"Pixel match [{region_id}]: pixel={pixel_color}, streak={state['pixel_streak']}/{STABILITY_FRAMES}")

            # Trigger auslösen, wenn genug stabile Frames erkannt wurden
            if state["pixel_streak"] >= STABILITY_FRAMES:
                state["pixel_streak"] = 0
                triggered = True
                log(f"✅ Stable pixel trigger (region {region_id})")
                break
        else:
            # Nur zurücksetzen, wenn derselbe Pixelbereich nicht mehr matched
            if state.get("last_region_id") == region_id:
                state["pixel_streak"] = 0

    # Komplett resetten, wenn kein einziger Bereich mehr matched
    if not matched_any:
        state["pixel_streak"] = 0
        state["last_region_id"] = None
        state["last_pixel_color"] = None

    return triggered, region_id
