/* Non-activating, click-through notice owned by the game's native window.
 * It never pauses the engine or consumes keyboard/mouse input. */
API(I, DrawTextA, (H, S, I, Rect *, U));
API(I, SetBkMode, (H, I));
API(U, SetTextColor, (H, U));
API(H, CreateFontA, (I, I, I, I, I, U, U, U, U, U, U, U, U, S));
static H noticeWindow;
static U noticeShown, noticePainted;
static I W notice_proc(H w, U msg, U a, I b) {
    if (msg == 0x84)
        return -1; /* HTTRANSPARENT */
    if (msg == 0x21)
        return 3; /* MA_NOACTIVATE */
    if (msg == 0x14)
        return 1;
    if (msg == 0xf) {
        Paint p;
        Rect r;
        H dc = BeginPaint(w, &p);
        GetClientRect(w, &r);
        FillRect(dc, &r, GetStockObject(4));
        I height = r.b * 19 / 38;
        H font = CreateFontA(-height, 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 4, 0, "Arial"),
          old = font ? SelectObject(dc, font) : 0;
        SetBkMode(dc, 1);
        SetTextColor(dc, 0x00d8f4ff);
        r.l += r.b / 4;
        DrawTextA(dc, "Not allowed - try again", -1, &r,
                  0x24); /* single line, vertically centered */
        if (font) {
            SelectObject(dc, old);
            DeleteObject(font);
        }
        EndPaint(w, &p);
        return 0;
    }
    return DefWindowProcA(w, msg, a, b);
}
static I notice_init(H user, H gdi) {
    GET(user, DrawTextA);
    GET(gdi, SetBkMode);
    GET(gdi, SetTextColor);
    GET(gdi, CreateFontA);
    Class c = {0};
    c.proc = notice_proc;
    c.instance = instance;
    c.name = "BoshyPortalNotice";
    return RegisterClassA(&c) != 0;
}
static void notice_tick(U scene) {
    I focused = GetForegroundWindow() == parent;
    if (!hubNoticeActive || scene <= 1 || (U)(GetTickCount() - hubNoticeStarted) >= 4000 ||
        !focused) {
        if (noticeShown) {
            ShowWindow(noticeWindow, 0);
            noticeShown = 0;
        }
        if ((U)(GetTickCount() - hubNoticeStarted) >= 4000)
            hubNoticeActive = 0;
        return;
    }
    if (!noticeWindow || !IsWindow(noticeWindow)) {
        noticeWindow = CreateWindowExA(0x080800a0, "BoshyPortalNotice", "", 0x80000000, 0, 0, 320,
                                       38, parent, 0, instance, 0);
        if (!noticeWindow)
            return;
        SetLayeredWindowAttributes(noticeWindow, 0, 225, 2);
    }
    Rect r;
    I xy[2] = {0, 0};
    GetClientRect(parent, &r);
    ClientToScreen(parent, xy);
    MoveWindow(noticeWindow, xy[0] + r.r * 10 / 880, xy[1] + r.b * 10 / 660, r.r * 320 / 880,
               r.b * 38 / 660, 0);
    if (!noticeShown) {
        ShowWindow(noticeWindow, 4);
        noticeShown = 1;
    }
    if (noticePainted != hubNoticeSerial) {
        InvalidateRect(noticeWindow, 0, 0);
        noticePainted = hubNoticeSerial;
    }
}
