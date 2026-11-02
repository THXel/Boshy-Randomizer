"""Owned Win32 geometry with a focus-aware backing; no monitor-mode changes."""

from platform_support import windows_api as api


def release(window):
    backing = getattr(window, "presentation_backing", None)
    if backing:
        window.presentation_backing = None
        backing.close()


def tick(window):
    backing = getattr(window, "presentation_backing", None)
    if backing:
        if window.owned():
            backing.tick()
        else:
            release(window)


def apply(window, settings):
    if not window.owned():
        raise RuntimeError("Owned display window disappeared")
    release(window)
    monitor, work = api.monitor(window.window)
    x, y, w, h = monitor if settings.fullscreen else work
    area = (w, h) if settings.fullscreen else (max(1, w - 32), max(1, h - 88))
    width, height = settings.fit(area)
    api.geometry(
        window,
        x + (w - width) // 2,
        y + (h - height) // 2,
        width,
        height,
        settings.fullscreen,
    )
    if settings.fullscreen:
        window.presentation_backing = api.Backing(window, monitor)
        window.presentation_backing.tick()
    return dict(
        requested=list(settings.size),
        applied=[width, height],
        monitor=list(monitor),
        aspect=settings.aspect,
        fullscreen=settings.fullscreen,
    )
