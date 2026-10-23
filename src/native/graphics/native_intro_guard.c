/* Patch only the two native beta-boss damage gates. The original menu DLL and
 * synchronous reward receipts are delegated unchanged. No HP restoration loop. */
typedef unsigned int U;
typedef unsigned short H;
typedef unsigned char B;
#define W __attribute__((stdcall))
static U rd(U p) {
    return *(volatile U *)p;
}
static H h(const B *p) {
    return *(const H *)p;
}
static U u(const B *p) {
    return *(const U *)p;
}
static int condition(const B *p, U oi, U value, U comparison) {
    return h(p) == 46 && h(p + 2) == 2 && (short)h(p + 4) == -27 && h(p + 6) == oi && p[12] == 2 &&
           h(p + 16) == 10 && h(p + 18) == 50 && u(p + 20) == 0 && h(p + 26) == 20 &&
           h(p + 28) == 23 && h(p + 30) == comparison && h(p + 32) == 65535 && h(p + 34) == 0 &&
           h(p + 36) == 10 && u(p + 38) == value;
}
int GuardPatch(B *bank, U oi) {
    if (oi != 2372 && oi != 2380)
        return 0;
    B *a = bank + 230244, *b = bank + 230478, *skip = bank + 234664, *fight = bank + 235138;
    /* Verify the original S shortcut and actual fight-start event as well. */
    if ((short)h(skip) != -286 || skip[2] != 2 || skip[3] != 6 || h(skip + 14) != 24 ||
        (short)h(skip + 16) != -6 || (short)h(skip + 18) != -1 || h(skip + 34) != 83 ||
        h(skip + 228) != 44 || h(skip + 230) != 2 || h(skip + 232) != 31 || h(skip + 234) != oi ||
        u(skip + 246) != 0 || u(skip + 264) != 779)
        return 0;
    if ((short)h(fight) != -312 || fight[2] != 1 || fight[3] != 5 ||
        !condition(fight + 14, oi, 780, 0))
        return 0;
    for (U n = 0; n < 2; n++) {
        B *e = n ? b : a;
        U old = u(e + 80);
        B *damage = e + (n ? 176 : 190);
        if ((short)h(e) != -234 || e[2] != 2 || e[3] != 3 || h(e + 14) != 28 || h(e + 16) != 2 ||
            (short)h(e + 18) != -14 || h(e + 20) != (n ? 273 : 106) ||
            !condition(e + 42, oi, old, 5) || (old != 400 && old != 779))
            return 0;
        if (h(damage) != 44 || h(damage + 2) != 2 || h(damage + 4) != 33 || h(damage + 6) != oi ||
            u(damage + 18) != 3 || u(damage + 36) != 1)
            return 0;
    }
    /* >779 means damage begins with fight phase 780, including an S skip. */
    *(U *)(a + 80) = 779;
    *(U *)(b + 80) = 779;
    return 1;
}
int OfflinePatch(B *bank) {
    B *e = bank + 4712;
    static const B condition[] = {50,  0,   2,   0,   220, 255, 46,  0,   23, 0, 32, 0, 2,
                                  0,   23,  128, 10,  0,   61,  0,   0,   0,  0, 0,  0, 0,
                                  24,  0,   46,  0,   0,   0,   255, 255, 3,  0, 14, 0, 79,
                                  110, 108, 105, 110, 101, 0,   0,   0,   0,  0, 0};
    static const B action[] = {22, 0, 253, 255, 2, 0,  0, 0,  0, 0, 0,
                               0,  1, 0,   8,   0, 26, 0, 17, 0, 0, 0};
    if ((short)h(e) != -258 || e[2] != 1 || e[3] != 7)
        return 0;
    for (U i = 0; i < 50; i++) {
        B expected = condition[i];
        if (i == 38 && e[14 + i] == 'X')
            continue;
        if (e[14 + i] != expected)
            return 0;
    }
    for (U i = 0; i < 22; i++) {
        if (i == 18 && e[236 + i] == 1)
            continue;
        if (e[236 + i] != action[i])
            return 0;
    }
    /* Impossible selector value, plus offline-menu fallback instead of scene 17. */
    e[52] = 'X';
    *(U *)(e + 254) = 1;
    return 1;
}
static U find(U run, U oi) {
    U table = rd(run + 0x1278), count = rd(run + 0x40);
    if (table < 0x10000 || count > 20000)
        return 0;
    for (U i = 0; i < count; i++) {
        U p = rd(table + i * 8);
        if (p >= 0x10000 && *(H *)(p + 18) == oi && *(H *)(p + 24) == 33)
            return p;
    }
    return 0;
}
static U tree(U head, const char *key) {
    if (head < 0x10000)
        return 0;
    U node = rd(head + 4);
    for (U i = 0; i < 128 && node >= 0x10000 && node != head; i++) {
        U len = rd(node + 20), str = rd(node + 16);
        if (len > 127 || str < 0x10000)
            return 0;
        int cmp = 0;
        for (U j = 0; j <= len; j++) {
            B a = key[j], b = j < len ? *(B *)(str + j) : 0;
            if (a != b) {
                cmp = (int)a - b;
                break;
            }
            if (!a)
                break;
        }
        if (!cmp)
            return node;
        node = rd(node + (cmp < 0 ? 0 : 8));
    }
    return 0;
}
static int same_session(U shared, U run) {
    /* Exact layout from the unchanged mixed reward context. */
    const char *session = (const char *)(shared - 304284 + 64);
    for (U i = 0; i < 32; i++)
        if (!((session[i] >= '0' && session[i] <= '9') || (session[i] >= 'a' && session[i] <= 'f')))
            return 0;
    if (session[32])
        return 0;
    U ini = find(run, 312);
    if (!ini)
        return 0;
    U state = rd(ini + 0x168);
    if (state < 0x10000)
        return 0;
    U group = tree(rd(state + 20), "randochecks");
    if (!group)
        return 0;
    U node = tree(rd(group + 32), "sessionid");
    if (!node || rd(node + 52) != 32)
        return 0;
    U value = rd(node + 48);
    if (value < 0x10000)
        return 0;
    for (U i = 0; i < 32; i++)
        if (*(char *)(value + i) != session[i])
            return 0;
    return 1;
}
static void (*original_tick)(void *, U, U);
static int (*original_commit)(const char *, const char *);
static int load_original(void) {
    if (original_tick && original_commit)
        return 1;
    void *(W * load)(const char *) = (void *)rd(0x45314c);
    void *(W * get)(void *, const char *) = (void *)rd(0x453128);
    void *m = load("..\\native_menu_polished.dll");
    if (!m)
        return 0;
    original_tick = get(m, "MenuTick");
    original_commit = get(m, "RewardCommit");
    return original_tick && original_commit;
}
void MenuTick(void *shared, U run, U scene) {
    U *s = shared;
    if (!load_original()) {
        s[12] = 30;
        return;
    }
    if (scene == 1) {
        U bank = rd(run + 0x88);
        if (bank >= 0x10000 && !OfflinePatch((B *)bank)) {
            s[12] = 32;
            *(U *)(run + 0x178) = 1;
            return;
        }
    }
    if ((scene == 43 || scene == 44) && same_session((U)shared, run)) {
        U bank = rd(run + 0x88);
        if (bank >= 0x10000 && !GuardPatch((B *)bank, scene == 43 ? 2372 : 2380)) {
            s[12] = 31;
            *(U *)(run + 0x178) = 1;
            return;
        }
    }
    original_tick(shared, run, scene);
}
int RewardCommit(const char *session, const char *key) {
    return load_original() ? original_commit(session, key) : 0;
}
int W DllMain(void *h, U reason, void *unused) {
    (void)h;
    (void)reason;
    (void)unused;
    return 1;
}
