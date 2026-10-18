"""Small window API shared by Windows and Linux/X11. No global monkeypatches."""
import os
if os.name == 'nt':
    from pygetwindow import Win32Window
    import pygetwindow
    from windows_api import user,pid
    class Window(Win32Window):
        pid=property(lambda self:pid(self._hWnd))
        isVisible=property(lambda self:bool(user.IsWindowVisible(self._hWnd)))
    def getAllWindows():return [Window(w._hWnd) for w in pygetwindow.getAllWindows()]
    def getWindowsWithTitle(title):return [w for w in getAllWindows() if title.casefold() in w.title.casefold()]
    def getAllTitles():return [w.title for w in getAllWindows()]
else:
    import threading
    from Xlib import display, X
    _local = threading.local()

    def connection():
        if not hasattr(_local, 'display'):
            _local.display = display.Display()
        return _local.display

    def _property(window, name, default=None):
        d = connection()
        cache = getattr(_local, 'atoms', None)
        if cache is None:
            cache = _local.atoms = {}
        if name not in cache:
            cache[name] = d.intern_atom(name)
        result = window.get_full_property(cache[name], X.AnyPropertyType)
        return result.value if result is not None else default

    class Window:
        def __init__(self, xid):
            self._hWnd = int(xid)
            self._window = connection().create_resource_object('window', self._hWnd)

        @property
        def title(self):
            value = _property(self._window, '_NET_WM_NAME')
            if value is None:
                return self._window.get_wm_name() or ''
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else str(value)

        @property
        def pid(self):
            value = _property(self._window, '_NET_WM_PID', [])
            return int(value[0]) if len(value) else None

        @property
        def isVisible(self):
            if self._window.get_attributes().map_state != X.IsViewable:
                return False
            # Wine windows may stay mapped while Cinnamon marks them iconic.
            state = _property(self._window, 'WM_STATE', [])
            return not (len(state) and state[0] == 3)

        @property
        def isActive(self):
            active = _property(connection().screen().root, '_NET_ACTIVE_WINDOW', [])
            return bool(len(active) and active[0] == self._hWnd)

        def _rect(self):
            # Match pygetwindow's outer-window origin including WM decorations.
            root = connection().screen().root
            xy = root.translate_coords(self._window, 0, 0)
            g = self._window.get_geometry()
            e = list(_property(self._window, '_NET_FRAME_EXTENTS', [0, 0, 0, 0]))
            return xy.x-e[0], xy.y-e[2], g.width+e[0]+e[1], g.height+e[2]+e[3]

        left = property(lambda self: self._rect()[0])
        top = property(lambda self: self._rect()[1])
        width = property(lambda self: self._rect()[2])
        height = property(lambda self: self._rect()[3])

        def activate(self):
            from PY.platform_runtime import focus_hwnd
            focus_hwnd(self._hWnd)

    def getAllWindows():
        root = connection().screen().root
        ids = _property(root, '_NET_CLIENT_LIST', [])
        windows = []
        for xid in ids:
            try:
                w = Window(xid)
                if w.isVisible:
                    windows.append(w)
            except Exception:
                continue
        return windows

    def getWindowsWithTitle(title):
        return [w for w in getAllWindows() if title.casefold() in w.title.casefold()]

    def getAllTitles():
        return [w.title for w in getAllWindows()]


def grab_frame(w, rect=None):
    """Read only the game-sized rectangle, not every monitor for each pixel check."""
    from PIL import Image, ImageGrab
    left, top, width, height = rect or window_rect(w)
    if os.name == 'nt':
        return ImageGrab.grab(bbox=(left, top, left+width, top+height))
    d = connection()
    formats = d.display.info.pixmap_formats
    depth = d.screen().root_depth
    fmt = next((f for f in formats if f.depth == depth), None)
    if depth == 24 and fmt and fmt.bits_per_pixel == 32 and d.display.info.image_byte_order == 0:
        reply = d.screen().root.get_image(left, top, width, height, X.ZPixmap, 0xffffffff)
        return Image.frombytes('RGB', (width, height), reply.data, 'raw', 'BGRX')
    return ImageGrab.grab(bbox=(left, top, left+width, top+height))


def get_window(hwnd):
    if os.name == 'nt':
        from pygetwindow import Win32Window
        return Window(hwnd)
    return Window(hwnd)


def window_rect(w):
    if os.name != 'nt':
        return w._rect()
    return w.left, w.top, w.width, w.height


def sample_pixels(w, points, rect=None):
    """Sample exact points; keep legacy outer-window coordinates unchanged."""
    rect = rect or window_rect(w)
    left, top, width, height = rect
    points = {p for p in points if 0 <= p[0] < width and 0 <= p[1] < height}
    if not points:
        return {}
    if os.name != 'nt':
        d = connection()
        screen = d.screen()
        fmt = next((f for f in d.display.info.pixmap_formats if f.depth == screen.root_depth), None)
        if screen.root_depth == 24 and fmt and fmt.bits_per_pixel == 32 and d.display.info.image_byte_order == 0:
            # A handful of direct reads is cheapest; many probes share one read.
            visible = {(x, y) for x, y in points
                       if 0 <= left+x < screen.width_in_pixels and 0 <= top+y < screen.height_in_pixels}
            if len(visible) > 4:
                from PIL import Image
                x0, y0 = min(p[0] for p in visible), min(p[1] for p in visible)
                x1, y1 = max(p[0] for p in visible), max(p[1] for p in visible)
                width, height = x1-x0+1, y1-y0+1
                reply = screen.root.get_image(left+x0, top+y0, width, height, X.ZPixmap, 0xffffffff)
                frame = Image.frombytes('RGB', (width, height), reply.data, 'raw', 'BGRX')
                return {p: frame.getpixel((p[0]-x0, p[1]-y0)) for p in visible}
            result = {}
            for x, y in visible:
                sx, sy = left+x, top+y
                if not (0 <= sx < screen.width_in_pixels and 0 <= sy < screen.height_in_pixels):
                    continue
                reply = screen.root.get_image(sx, sy, 1, 1, X.ZPixmap, 0xffffffff)
                b, g, r = reply.data[:3]
                result[(x, y)] = (r, g, b)
            return result
    frame = grab_frame(w, rect=rect)
    return {p: frame.getpixel(p)[:3] for p in points}
