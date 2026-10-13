"""Stable, independent pixel probes; each point advances at most once per frame."""
import time
from functools import lru_cache
from PY import platform_windows as gw
from .logger import log
from .config import window_title, pixel_stability_frames

DEFAULT_STABILITY_FRAMES = max(1, int(pixel_stability_frames))
MAX_SAMPLE_GAP_S = 0.5


def _required_frames(state):
    try:
        return max(1, int(state.get('pixel_required_frames', DEFAULT_STABILITY_FRAMES)))
    except (TypeError, ValueError):
        return DEFAULT_STABILITY_FRAMES


@lru_cache(maxsize=512)
def hex_to_rgb(value):
    value = str(value).removeprefix('0x').removeprefix('#')
    if len(value) != 6:
        raise ValueError('Expected a six-digit RGB color')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def reset_pixel_state(state):
    for key in ('_pixel_streaks', '_pixel_context', '_pixel_sample_time'):
        state.pop(key, None)
    state.update(pixel_streak=0, last_region_id=None, last_pixel_color=None)


def check_pixel_regions(pixel_regions, state, current_stage=None):
    if not pixel_regions:
        reset_pixel_state(state)
        return False, None
    try:
        pinned = state.get('force_hwnd')
        if pinned:
            w = gw.get_window(pinned)
        else:
            wins = gw.getWindowsWithTitle(window_title)
            w = wins[0] if wins else None
        if w is None or not w.isVisible or not w.isActive:
            reset_pixel_state(state)
            return False, None
        rect = gw.window_rect(w)
        left, top, width, height = rect
        probes = {}
        for region in pixel_regions:
            try:
                name = str(region['Region'])
                x, y = int(region['center']['x']), int(region['center']['y'])
                if not region.get('relative', False):
                    x, y = x-left, y-top
                if not (0 <= x < width and 0 <= y < height):
                    continue
                colors = tuple(hex_to_rgb(c) for c in [region['avg_color']] + region.get('samples', []))
                # Duplicate entries must not increment one point twice in a frame.
                key = (name, x, y, colors)
                probes[key] = (x, y)
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        pixels = gw.sample_pixels(w, tuple(set(probes.values())), rect=rect)
        # Focus may change during capture. Never combine samples across that gap.
        if not w.isActive:
            reset_pixel_state(state)
            return False, None
    except Exception:
        reset_pixel_state(state)
        return False, None

    now = time.monotonic()
    context = (w._hWnd, current_stage, rect)
    if (state.get('_pixel_context') != context or
            now - state.get('_pixel_sample_time', 0) > MAX_SAMPLE_GAP_S):
        reset_pixel_state(state)
    previous = state.get('_pixel_streaks', {})
    current = {}
    required = _required_frames(state)
    trigger = None
    for key, point in probes.items():
        color = pixels.get(point)
        if color is None or color not in key[3]:
            continue
        count, last_color = previous.get(key, (0, None))
        count = count+1 if last_color == color else 1
        current[key] = (count, color)
        if trigger is None and count >= required:
            trigger = key[0]
    state['_pixel_context'] = context
    state['_pixel_sample_time'] = now
    state['_pixel_streaks'] = current
    if current:
        best = max(current, key=lambda k: current[k][0])
        state['pixel_streak'], state['last_pixel_color'] = current[best]
        state['last_region_id'] = best[0]
    else:
        state.update(pixel_streak=0, last_region_id=None, last_pixel_color=None)
    if trigger is not None:
        # A continued match needs another complete set of stable frames.
        state['_pixel_streaks'] = {}
        state['pixel_streak'] = 0
        log(f'✅ Stable pixel trigger (region {trigger})')
        return True, trigger
    return False, None
