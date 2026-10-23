/* Extend only verified Options-frame numeric literals, on the engine thread.
 * The original INI writer, Window Control sizing and fullscreen actions remain. */
#include "resolution_policy.h"
API(H, MonitorFromWindow, (H, U));
typedef struct {
    U size;
    Rect monitor, work;
    U flags;
} ResolutionMonitor;
API(I, GetMonitorInfoA, (H, ResolutionMonitor *));
API(I, GetWindowRect, (H, Rect *));
U ResolutionState[6] = {1, 0, 0, 0, 0, 0};
static U resolutionRun, resolutionBank, resolutionLimit, resolutionWidth, resolutionHeight;
API(I, SetWindowPos, (H, H, I, I, I, I, U));
static I resolution_verify(unsigned char *b) {
    const U offsets[] = {120318, 120932, 121564, 121826};
    const short lengths[] = {-614, -632, -262, -296};
    for (U i = 0; i < 4; i++) {
        unsigned char *p = b + offsets[i];
        if (*(short *)p != lengths[i] || *(unsigned short *)(p + 14) != 24 ||
            *(short *)(p + 16) != -6 || *(unsigned short *)(p + 38) != 28 ||
            *(unsigned short *)(p + 44) != 1173)
            return 0;
        if (*(U *)(p + 168) != (i ? 1280U : 320U) || *(unsigned short *)(p + 164) != 0 ||
            *(unsigned short *)(p + 166) != 10)
            return 0;
    }
    return *(U *)(b + 120318 + 354) == 160 && *(U *)(b + 120932 + 338) == 160;
}
static void resolution_tick(U run, U scene, H window) {
    resolutionSelected = 0;
    if (!MonitorFromWindow) {
        H user = library("user32.dll");
        MonitorFromWindow = (void *)symbol(user, "MonitorFromWindow");
        GetMonitorInfoA = (void *)symbol(user, "GetMonitorInfoA");
        GetWindowRect = (void *)symbol(user, "GetWindowRect");
        SetWindowPos = (void *)symbol(user, "SetWindowPos");
    }
    if (!MonitorFromWindow || !GetMonitorInfoA || !GetWindowRect)
        return;
    ResolutionMonitor monitor = {0};
    monitor.size = sizeof(monitor);
    Rect wr;
    if (!GetMonitorInfoA(MonitorFromWindow(window, 2), &monitor) || !GetWindowRect(window, &wr))
        return;
    U height = wr.b - wr.t;
    if (SetWindowPos && !(GetWindowLongA(window, -16) & 0x01000000) &&
        (resolutionWidth != (U)(wr.r - wr.l) || resolutionHeight != height)) {
        I x = wr.l, y = wr.t, width = wr.r - wr.l;
        if (x + width > monitor.work.r)
            x = monitor.work.r - width;
        if (x < monitor.work.l)
            x = monitor.work.l;
        if (y + (I)height > monitor.work.b)
            y = monitor.work.b - height;
        if (y < monitor.work.t)
            y = monitor.work.t;
        if (x != wr.l || y != wr.t)
            SetWindowPos(window, 0, x, y, 0, 0, 0x15);
    }
    resolutionWidth = wr.r - wr.l;
    resolutionHeight = height;
    if (scene != 19) {
        resolutionRun = resolutionBank = 0;
        ResolutionState[1] = 0;
        return;
    }
    U bank = *(U *)(run + 0x88);
    if (bank < 0x10000)
        return;
    if (run != resolutionRun || bank != resolutionBank) {
        if (!resolution_verify((void *)bank)) {
            ResolutionState[1] = 2;
            return;
        }
        resolutionRun = run;
        resolutionBank = bank;
    }
    U limit = resolution_limit(monitor.work.r - monitor.work.l, monitor.work.b - monitor.work.t),
      width = wr.r - wr.l;
    if (limit != resolutionLimit) {
        resolutionLimit = limit;
        event(8, limit, limit * 3 / 4);
    }
    unsigned char *b = (void *)bank;
    *(U *)(b + 120932 + 168) = *(U *)(b + 121564 + 168) = *(U *)(b + 121826 + 168) = limit;
    U lower = resolution_next(width, limit, -1), upper = resolution_next(width, limit, 1);
    *(U *)(b + 120318 + 354) = width > lower ? width - lower : 160;
    *(U *)(b + 120932 + 338) = upper > width ? upper - width : 160;
    ResolutionState[1] = 1;
    ResolutionState[2] = limit;
    ResolutionState[3] = width;
    ResolutionState[4] = monitor.monitor.r - monitor.monitor.l;
    ResolutionState[5] = monitor.monitor.b - monitor.monitor.t;
    U table = *(U *)(run + 0x1278), n = *(U *)(run + 0x40);
    if (table < 0x10000 || !n || n > 20000)
        return;
    I x = -1, y = -1, tx = -1000, ty = -1000;
    for (U i = 0; i < n; i++) {
        U o = *(U *)(table + i * 8);
        if (o < 0x10000 || *(unsigned short *)(o + 24) != 2)
            continue;
        U oi = *(unsigned short *)(o + 18);
        if (oi == 1173) {
            x = *(I *)(o + 76);
            y = *(I *)(o + 84);
        }
        if (oi == 1363) {
            tx = *(I *)(o + 76);
            ty = *(I *)(o + 84);
        }
    }
    resolutionSelected = x >= tx - 40 && x <= tx + 120 && y >= ty && y <= ty + 49;
}
