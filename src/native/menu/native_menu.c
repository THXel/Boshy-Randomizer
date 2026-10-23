/* Owned native dialogs in the Boshy process, aligned with its client window. */
typedef unsigned int U;
typedef int I;
typedef void *H;
typedef const char *S;
#define W __attribute__((stdcall))
typedef struct {
    I l, t, r, b;
} Rect;
typedef struct {
    H dc;
    I erase;
    Rect r;
    I restore, update;
    char reserve[32];
} Paint;
typedef struct {
    U style;
    I(W *proc)(H, U, U, I);
    I clsExtra, winExtra;
    H instance, icon, cursor, brush;
    S menu, name;
} Class;
typedef struct {
    volatile U magic, version, status, window, shown, write, ack, type, a, b, generation, rendered,
        error, scene, run, enabled;
    char path[260];
    U events[64][4];
} Shared;
static Shared *q;
static H child, parent, bitmap, instance;
static U lastRun, savedPause, menuLayer = 99, menuSlot = 1, keysBefore, logoRun;
static H(W *library)(S);
static H(W *symbol)(H, S);
#define API(ret, name, args) static ret(W *name) args
API(U, RegisterClassA, (Class *));
API(H, CreateWindowExA, (U, S, S, U, I, I, I, I, H, H, H, H));
API(I, DefWindowProcA, (H, U, U, I));
API(I, GetClientRect, (H, Rect *));
API(I, ShowWindow, (H, I));
API(H, SetFocus, (H));
API(I, MoveWindow, (H, I, I, I, I, I));
API(H, BeginPaint, (H, Paint *));
API(I, EndPaint, (H, Paint *));
API(I, InvalidateRect, (H, Rect *, I));
API(H, LoadImageA, (H, S, U, I, I, U));
API(I, FillRect, (H, Rect *, H));
API(H, CreateCompatibleDC, (H));
API(H, SelectObject, (H, H));
API(I, DeleteObject, (H));
API(I, DeleteDC, (H));
API(I, StretchBlt, (H, I, I, I, I, H, I, I, I, I, U));
API(H, GetStockObject, (I));
API(I, IsWindow, (H));
API(I, VirtualProtect, (H, U, U, U *));
API(H, CreateRectRgn, (I, I, I, I));
API(I, SetWindowRgn, (H, H, I));
API(H, GetForegroundWindow, (void));
API(I, GetWindowLongA, (H, I));
API(I, SetWindowLongA, (H, I, I));
API(I, SetStretchBltMode, (H, I));
API(I, SetLayeredWindowAttributes, (H, U, unsigned char, U));
API(I, ClientToScreen, (H, void *));
static short(W *oldAsync)(I);
static short(W *oldKey)(I);
static I(W *oldKeyboard)(unsigned char *);
static I blocked(I key) {
    return q &&
           (((q->a & 1) && key == 0x72) || ((q->a & 2) && q->enabled && q->scene > 1 && key == 9) ||
            (q->enabled && q->scene == 1 && menuLayer == 0 &&
             (key == 13 || key == 46 || key == 84 || key == 38 || key == 40 || key == 9)));
}
static short W lockedAsync(I key) {
    return blocked(key) ? 0 : oldAsync(key);
}
static short W lockedKey(I key) {
    return blocked(key) ? 0 : oldKey(key);
}
static I W lockedKeyboard(unsigned char *keys) {
    I ok = oldKeyboard(keys);
    if (ok) {
        for (I k = 0; k < 256; k++)
            if (blocked(k))
                keys[k] = 0;
    }
    return ok;
}
static I hook(U address, H replacement) {
    U old;
    if (!VirtualProtect((H)address, 4, 4, &old))
        return 0;
    *(H *)address = replacement;
    U ignored;
    return VirtualProtect((H)address, 4, old, &ignored);
}
static void event(U type, U a, U b) {
    if (!q)
        return;
    U n = q->write;
    if (n - q->ack >= 64) {
        q->error = 4;
        return;
    }
    q->events[n % 64][0] = type;
    q->events[n % 64][1] = a;
    q->events[n % 64][2] = b;
    q->events[n % 64][3] = 0;
    __asm__ volatile("" ::: "memory");
    q->write = n + 1;
}
static I W proc(H w, U msg, U a, I b) {
    if (msg == 0x14)
        return 1;
    if (msg == 0xf) {
        Paint p;
        H dc = BeginPaint(w, &p);
        Rect r;
        GetClientRect(w, &r);
        FillRect(dc, &r, GetStockObject(4));
        if (bitmap) {
            H mem = CreateCompatibleDC(dc), old = SelectObject(mem, bitmap);
            SetStretchBltMode(dc, 4);
            StretchBlt(dc, 0, 0, r.r, r.b, mem, 0, 0, 880, 660, 0xcc0020);
            SelectObject(mem, old);
            DeleteDC(mem);
        }
        EndPaint(w, &p);
        return 0;
    }
    if (msg == 0x100) {
        if ((oldKey(17) & 0x8000) && (a == 65 || a == 86 || a == 67)) {
            if (!(b & (1 << 30)))
                event(1, a == 65 ? 4097 : (a == 86 ? 4098 : 4099), 0);
            return 0;
        }
        if (!(b & (1 << 30)) &&
            (a == 8 || a == 9 || a == 13 || a == 27 || a == 46 || (a >= 37 && a <= 40)))
            event(1, a, 0);
        return 0;
    }
    if (msg == 0x101 || msg == 0x104 || msg == 0x105)
        return 0;
    if (msg == 0x102) {
        if (a >= 32 && a <= 126)
            event(2, a, 0);
        return 0;
    }
    if (msg == 0x202) {
        Rect r;
        GetClientRect(w, &r);
        if (r.r && r.b)
            event(3, ((U)b & 65535) * 880 / r.r, ((U)b >> 16) * 660 / r.b);
        SetFocus(w);
        return 0;
    }
    if (msg == 0x20)
        return 1;
    return DefWindowProcA(w, msg, a, b);
}
#define GET(mod, name)                                                                             \
    name = (void *)symbol(mod, #name);                                                             \
    if (!name)                                                                                     \
    return 0
#include "reward_receipt.c"
static I init(void) {
    library = *(void **)0x45314c;
    symbol = *(void **)0x453128;
    H user = library("user32.dll"), gdi = library("gdi32.dll");
    if (!user || !gdi)
        return 0;
    GET(user, RegisterClassA);
    GET(user, CreateWindowExA);
    GET(user, DefWindowProcA);
    GET(user, GetClientRect);
    GET(user, ShowWindow);
    GET(user, SetFocus);
    GET(user, MoveWindow);
    GET(user, BeginPaint);
    GET(user, EndPaint);
    GET(user, InvalidateRect);
    GET(user, LoadImageA);
    GET(user, FillRect);
    GET(user, IsWindow);
    GET(user, SetWindowRgn);
    GET(user, GetForegroundWindow);
    GET(user, GetWindowLongA);
    GET(user, SetWindowLongA);
    GET(user, SetLayeredWindowAttributes);
    GET(user, ClientToScreen);
    GET(gdi, CreateCompatibleDC);
    GET(gdi, SelectObject);
    GET(gdi, DeleteObject);
    GET(gdi, DeleteDC);
    GET(gdi, StretchBlt);
    GET(gdi, GetStockObject);
    GET(gdi, CreateRectRgn);
    GET(gdi, SetStretchBltMode);
    H kernel = library("kernel32.dll");
    GET(kernel, VirtualProtect);
    oldAsync = *(H *)0x453384;
    oldKey = *(H *)0x453398;
    oldKeyboard = *(H *)0x453410;
    if (!hook(0x453384, lockedAsync) || !hook(0x453398, lockedKey) ||
        !hook(0x453410, lockedKeyboard))
        return 0;
    Class c = {0};
    c.proc = proc;
    c.instance = instance;
    c.name = "BoshyNativeRandomizerMenu";
    return RegisterClassA(&c) != 0;
}
void MenuTick(Shared *s, U run, U scene) {
    if (s->magic != 0x424d4e31 || s->version != 1)
        return;
    q = s;
    q->scene = scene;
    q->run = run;
    if (!q->status) {
        if (!init()) {
            q->error = 1;
            q->status = 3;
            return;
        }
        q->status = 1;
    }
    if (q->status == 3 || run < 0x10000)
        return;
    H h = *(H *)(run + 0x10);
    if (!IsWindow(h))
        return;
    if (!child || !IsWindow(child) || h != parent) {
        parent = h;
        SetWindowLongA(parent, -16, GetWindowLongA(parent, -16) | 0x02000000);
        Rect r;
        GetClientRect(h, &r);
        child = CreateWindowExA(0x80080, "BoshyNativeRandomizerMenu", "", 0x80000000, 0, 0, r.r,
                                r.b, h, 0, instance, 0);
        if (!child) {
            q->error = 2;
            return;
        }
        SetLayeredWindowAttributes(child, 0, 255, 2);
        q->window = (U)child;
    }
    U previousLayer = menuLayer;
    menuLayer = 99;
    if (scene == 1) {
        U table = *(U *)(run + 0x1278), n = *(U *)(run + 0x40);
        if (table >= 0x10000 && n > 0 && n <= 20000)
            for (U i = 0; i < n; i++) {
                U o = *(U *)(table + i * 8);
                if (o < 0x10000 || *(unsigned short *)(o + 0x18) != 2)
                    continue;
                U oi = *(unsigned short *)(o + 0x12);
                if (oi == 46) {
                    U off = *(U *)(o + 0x80);
                    if (off > 0 && off < 1024) {
                        U v = *(U *)(o + off);
                        if (v >= 0x10000) {
                            menuLayer = *(U *)(v + 24);
                            U slot = *(U *)(v + 8);
                            if (menuLayer == 0 && slot < 3 &&
                                (menuSlot != slot + 1 || previousLayer != 0)) {
                                menuSlot = slot + 1;
                                event(4, menuSlot, 0);
                            }
                        }
                    }
                }
                if (oi == 41 && logoRun != run && *(U *)0x42bec0 == 0x5318ec83) {
                    void (*load)(U, S, I, I, I, I, I, I, I, I) = (void *)0x42bec0;
                    unsigned char info[64] = {0};
                    U dir = *(U *)(o + 0x1ee);
                    U before = dir >= 0x10000 ? *(unsigned short *)(dir + 8) : 0;
                    I(W * getinfo)(U, U, U, U, U, H) = (void *)0x450de6;
                    if (before && getinfo(*(U *)(*(U *)(o + 8) + 8), before, 0, 0x3f800000,
                                          0x3f800000, info)) {
                        event(6, *(unsigned short *)(info + 12), *(unsigned short *)(info + 14));
                    }
                    load(o, "..\\menu-runtime\\logo.png", 0, 0, 0, 151, 60, 0, 0, -1);
                    logoRun = run;
                }
            }
    }
    q->type = menuLayer;
    q->b = menuSlot;
    U down = 0;
    {
        if (oldAsync(13) & 0x8000)
            down |= 1;
        if (oldAsync(46) & 0x8000)
            down |= 2;
        if (oldAsync(84) & 0x8000)
            down |= 4;
        if (oldAsync(9) & 0x8000)
            down |= 8;
        if (oldAsync(38) & 0x8000)
            down |= 16;
        if (oldAsync(40) & 0x8000)
            down |= 32;
    }
    U pressed = down & ~keysBefore;
    keysBefore = down;
    if (GetForegroundWindow() == parent && scene == 1 && q->enabled == 1 && menuLayer == 0) {
        if (pressed & 1)
            event(4, menuSlot, 1);
        else if (pressed & 2)
            event(4, menuSlot, 2);
        else if (pressed & 4)
            event(4, menuSlot, 3);
        else if (pressed & 16)
            event(1, 38, 0);
        else if (pressed & 32)
            event(1, 40, 0);
        else if (pressed & 8)
            event(1, 9, 0);
    }
    if (GetForegroundWindow() == parent && scene > 1 && (q->a & 2) && q->enabled == 1 &&
        (pressed & 8)) {
        event(7, 0, 0);
    }
    I modal = q->enabled >= 2, show = (scene == 1 && q->enabled && (modal || menuLayer == 0)) ||
                                      (scene > 1 && (q->a & 2) && q->enabled == 3);
    static U shownMode;
    if (show) {
        if (modal) {
            if (lastRun != run) {
                lastRun = run;
                savedPause = *(U *)(run + 0x178);
            }
            *(U *)(run + 0x178) = 1;
        } else if (lastRun == run) {
            *(U *)(run + 0x178) = savedPause;
            lastRun = 0;
        }
        Rect r;
        GetClientRect(parent, &r);
        I origin[2] = {0, 0};
        ClientToScreen(parent, origin);
        MoveWindow(child, origin[0], origin[1], r.r, r.b, 0);
        if (!q->shown || shownMode != q->enabled) {
            H region = modal ? CreateRectRgn(r.r * 235 / 880, r.b * 252 / 660, r.r * 868 / 880,
                                             r.b * 652 / 660)
                             : CreateRectRgn(0, r.b * 266 / 660, r.r * 310 / 880, r.b);
            SetWindowRgn(child, region, 1);
            ShowWindow(child, modal ? 5 : 4);
            SetFocus(modal ? child : parent);
            q->shown = 1;
            shownMode = q->enabled;
        }
        if (q->generation != q->rendered) {
            H next = LoadImageA(0, q->path, 0, 0, 0, 0x2010);
            if (next) {
                H old = bitmap;
                bitmap = next;
                if (old)
                    DeleteObject(old);
                q->rendered = q->generation;
                InvalidateRect(child, 0, 0);
            } else
                q->error = 3;
        }
    } else if (q->shown) {
        ShowWindow(child, 0);
        q->shown = 0;
        if (lastRun == run)
            *(U *)(run + 0x178) = savedPause;
        lastRun = 0;
        SetFocus(parent);
    }
    q->status = 2;
}
I W DllMain(H h, U reason, H unused) {
    (void)unused;
    if (reason == 1)
        instance = h;
    return 1;
}
