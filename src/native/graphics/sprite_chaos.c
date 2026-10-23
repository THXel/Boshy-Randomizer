/* Revision 2: fixed masks, hotspots, action points and original animation timing.
 * Imports are budgeted across ticks. Legacy scenery keeps its original path. */
typedef struct {
    U oi, type, category, size, obstacle, width, height;
    I hx, hy, ax, ay;
    U anim, direction, frame, offset, bankSize, animCount, nframes, low, high;
} ChaosRecord;
#include "sprite_chaos_catalogue.h"
#define CHAOS_COUNT (sizeof(chaosRecords) / sizeof(*chaosRecords))
U ChaosState[14] = {
    2, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0}; /* revision, enabled, plan, total, scene, changed, error, refused,
                          background/decor/floor/actor imports, max/last batch ms */
U ChaosRefused[16 * 12];
static void chaos_refused(U reason, U index, U value, unsigned char *info) {
    U at = (ChaosState[7] % 16) * 12;
    const ChaosRecord *r = &chaosRecords[index];
    ChaosRefused[at] = r->oi;
    ChaosRefused[at + 1] = reason;
    ChaosRefused[at + 2] = index;
    ChaosRefused[at + 3] = value;
    for (U n = 0; n < 6; n++)
        ChaosRefused[at + 4 + n] = info ? (n < 2 ? *(unsigned short *)(info + 12 + n * 2)
                                                 : (U)(I) * (short *)(info + 16 + n * 2))
                                        : 0;
    ChaosRefused[at + 10] = (U)r->ax;
    ChaosRefused[at + 11] = (U)r->ay;
    ChaosState[7]++;
}
static U chaosClouds, chaosCloudReady;
static U chaosLoaded, chaosMask, chaosRun, chaosScene = ~0U, chaosTick, chaosDone[CHAOS_COUNT],
                                           chaosHandles[CHAOS_COUNT], chaosApplied[CHAOS_COUNT];
static void chaos_path(char *out, U i, I original) {
    S p = "..\\menu-runtime\\chaos\\";
    U n = 0;
    for (; p[n]; n++)
        out[n] = p[n];
    if (original)
        out[n++] = 'o';
    out[n++] = '0' + i / 100;
    out[n++] = '0' + i / 10 % 10;
    out[n++] = '0' + i % 10;
    out[n++] = '.';
    out[n++] = 'p';
    out[n++] = 'n';
    out[n++] = 'g';
    out[n] = 0;
}
static I chaos_plan(void) {
    if (chaosLoaded)
        return ChaosState[2] == 1;
    chaosLoaded = 1;
    if (!receipt_init() || *(U *)0x42b8a0 != 0x1468ff6a || *(U *)0x42bec0 != 0x5318ec83) {
        ChaosState[6] = 1;
        return 0;
    }
    unsigned char plan[44], extra;
    U got = 0, more = 0;
    H f = CreateFileA("..\\menu-runtime\\scenery.bin", 0x80000000, 1, 0, 3, 0, 0);
    if (f == (H)-1) {
        ChaosState[6] = 2;
        return 0;
    }
    I ok = ReadFile(f, plan, 44, &got, 0);
    ok = ok && ReadFile(f, &extra, 1, &more, 0);
    CloseHandle(f);
    if (!ok || got != 44 || more || !samebytes(plan, (const unsigned char *)"BRV2", 4) ||
        !samebytes(plan + 4, (const unsigned char *)q - 304284 + 64, 32) ||
        *(U *)(plan + 36) != CHAOS_COUNT || *(U *)(plan + 40) > 15) {
        ChaosState[6] = 3;
        return 0;
    }
    chaosMask = *(U *)(plan + 40);
    ChaosState[2] = 1;
    /* Host-side display policy also applies to archived seeds. Missing or stale
     * policy keeps the original layer visible. */
    unsigned char cloud[40];
    got = more = 0;
    f = CreateFileA("..\\menu-runtime\\clouds.bin", 0x80000000, 1, 0, 3, 0, 0);
    if (f != (H)-1) {
        ok = ReadFile(f, cloud, 40, &got, 0);
        ok = ok && ReadFile(f, &extra, 1, &more, 0);
        CloseHandle(f);
        if (ok && got == 40 && !more && samebytes(cloud, (const unsigned char *)"BRC1", 4) &&
            samebytes(cloud + 4, plan + 4, 32) && *(U *)(cloud + 36) == 1)
            chaosClouds = 1;
    }
    return 1;
}
static U chaos_pointer(U c, const ChaosRecord *r) {
    if (*(U *)c != r->size)
        return 0;
    if (r->type == 1) {
        if (*(U *)(c + 4) != r->obstacle || *(U *)(c + 8) != r->width ||
            *(U *)(c + 12) != r->height)
            return 0;
        return c + 16;
    }
    U offset = *(unsigned short *)(c + 6);
    if (offset != r->offset || offset + 4 > r->size)
        return 0;
    U bank = c + offset, bytes = r->size - offset;
    if (*(unsigned short *)bank != r->bankSize || r->bankSize != bytes ||
        *(unsigned short *)(bank + 2) != r->animCount || r->anim >= r->animCount)
        return 0;
    U anim = *(unsigned short *)(bank + 4 + 2 * r->anim);
    if (anim < 4 + 2 * r->animCount || anim + 64 > bytes)
        return 0;
    U dir = *(unsigned short *)(bank + anim + 2 * r->direction);
    if (dir < 64 || anim + dir + 8 + 2 * r->nframes > bytes ||
        *(unsigned short *)(bank + anim + dir + 6) != r->nframes || r->frame >= r->nframes)
        return 0;
    return bank + anim + dir + 8 + 2 * r->frame;
}
/* The renderer's deferred 0x86 pass only rebuilds layers marked dirty.
 * Importing a backdrop invalidates its image but does not mark those layers.
 * Mirror the engine's layer-edit notification, once per import batch; leave
 * scrolling, collision flags and frame generation unchanged. */
static void chaos_redraw(U run) {
    U frame = *(U *)0x459a98;
    if (frame < 0x10000 || *(U *)0x459a9c != run)
        return;
    U count = *(U *)(frame + 0x2c), layers = *(U *)(frame + 0x30);
    if (!count || count > 64 || layers < 0x10000)
        return;
    for (U i = 0; i < count; i++)
        *(U *)(layers + i * 0x5c + 0x2c) |= 0x10000;
    *(unsigned char *)(run + 0x1a7) |= 2;
}
/* World 3's Parallaxer draws independently of MMF's sprite Hide flag.
 * Remove only this cosmetic instance via the deferred destruction queue, so
 * its own renderer/resources are cleaned up by the engine at frame end. */
U ChaosCloudState[3]; /* policy, removal requested, last object */
static void chaos_clouds(U run, U scene) {
    ChaosCloudState[0] = chaosClouds;
    if ((GraphicsDebug[1] & 1) || background_owns(scene, 681) || scene != 7 || !chaosClouds ||
        !chaosCloudReady)
        return;
    if (*(U *)0x41f730 != 0x04244c8b || *(U *)0x411ecb != 0x7c468b66)
        return;
    U table = *(U *)(run + 0x1278), count = *(U *)(run + 0x40);
    if (table < 0x10000 || !count || count > 20000)
        return;
    for (U i = 0; i < count; i++) {
        U o = *(U *)(table + i * 8);
        if (o < 0x10000 || *(unsigned short *)(o + 0x12) != 681 ||
            *(unsigned short *)(o + 0x18) != 48)
            continue;
        U c = *(U *)(o + 0x44);
        if (c < 0x10000 || *(U *)c != 174 || *(U *)(c + 46) != 0x70616c78 ||
            *(U *)(o + 0xbc) != 0x1ce || *(U *)(o + 0x60) != 639 || *(U *)(o + 0x64) != 213 ||
            *(short *)o != (I)i)
            continue;
        if (!(*(unsigned short *)(o + 0x7c) & 1)) {
            *(unsigned short *)(o + 0x7c) |= 1;
            *(U *)(table + i * 8 + 4) = 0;
            void (*destroy)(I) = (void *)0x41f730;
            destroy((I)i);
            ChaosCloudState[1] = 1;
            ChaosCloudState[2] = o;
        }
    }
}
static void chaos_tick(U run, U scene) {
    ChaosState[1] = (q->a & 32768) != 0;
    ChaosState[4] = scene;
    if (!ChaosState[1] || scene < 2 || scene >= 64)
        return;
    U tick = *(U *)(run + 0xd0);
    if (run != chaosRun || scene != chaosScene || tick < chaosTick) {
        for (U i = 0; i < CHAOS_COUNT; i++)
            chaosDone[i] = chaosHandles[i] = chaosApplied[i] = 0;
        chaosRun = run;
        chaosScene = scene;
        ChaosState[5] = 0;
        chaosCloudReady = 0;
        ChaosCloudState[1] = ChaosCloudState[2] = 0;
    }
    if (tick == chaosTick)
        return;
    chaosTick = tick;
    if (!chaos_plan())
        return;
    U app = *(U *)0x459a94;
    if (app < 0x10000) {
        ChaosState[6] = 4;
        return;
    }
    U bank = *(U *)(app + 0x1c4);
    if (bank < 0x10000) {
        ChaosState[6] = 4;
        return;
    }
    I(W * info)(U, U, U, U, U, H) = (void *)0x450de6;
    U start = GetTickCount(), changed = 0, redraw = 0, lastOI = ~0U, object = 0;
    for (U i = 0; i < CHAOS_COUNT; i++) {
        const ChaosRecord *r = &chaosRecords[i];
        if (chaosDone[i])
            continue;
        if (background_owns(scene, r->oi)) {
            chaosDone[i] = 1;
            continue;
        }
        if (!(chaosMask & r->category) ||
            !(scene < 32 ? ((r->low >> scene) & 1) : ((r->high >> (scene - 32)) & 1))) {
            chaosDone[i] = 1;
            continue;
        }
        /* These Castlevania skeletons share source images with four other types,
         * including lazily loaded enemies. MMF's active-image replacement can free
         * an original handle still needed by a future spawn, yielding missing
         * skeletons or a background image in their animation. Keep their original
         * banks intact; other actor palettes and scenery remain independent. */
        if (r->oi == 1088 || r->oi == 1089) {
            chaosDone[i] = 1;
            continue;
        }
        /* Sonic and Old Sonic share this shrinking arena floor. The legacy
         * catalogue labels it as background, but its grass edge is the landing
         * cue above additive flames. Landscape replacement/dimming erases that
         * cue during animation 12. Keep all 38 frames native, including frozen
         * seeds, so the platform remains readable through the fire transition. */
        if (r->oi == 1054) {
            chaosDone[i] = 1;
            continue;
        }
        U definition = theme_definition(r->oi), c = definition ? *(U *)(definition + 20) : 0;
        if (!definition || *(unsigned short *)(definition + 2) != r->type || c < 0x10000) {
            continue;
        }
        /* Active instances can own rebased common data while their definition
         * still contains source image numbers. Always inspect the live bank. */
        if (r->type == 2) {
            if (lastOI != r->oi) {
                lastOI = r->oi;
                object = intro_object(run, r->oi);
            }
            if (!object)
                continue;
            if (*(U *)(object + 0xb8) != 462) {
                chaos_refused(2, i, *(U *)(object + 0xb8), 0);
                chaosDone[i] = 1;
                continue;
            }
            c = *(U *)(object + 0x44);
            if (c < 0x10000)
                continue;
        }
        U pointer = chaos_pointer(c, r);
        if (!pointer) {
            chaos_refused(1, i, *(U *)c, 0);
            chaosDone[i] = 1;
            continue;
        }
        U before = *(unsigned short *)pointer;
        if ((GraphicsDebug[1] & r->category) && before != chaosHandles[i]) {
            chaosHandles[i] = before;
            chaosApplied[i] = GraphicsDebug[1] & r->category;
            chaosDone[i] = 1;
            continue;
        }
        if (before && before == chaosHandles[i] &&
            chaosApplied[i] == (GraphicsDebug[1] & r->category)) {
            if (r->oi == 617)
                chaosCloudReady = 1;
            chaosDone[i] = 1;
            continue;
        }
        unsigned char v[64] = {0};
        if (!before || before >= 32768 || !info(bank, before, 0, 0x3f800000, 0x3f800000, v) ||
            *(unsigned short *)(v + 12) != r->width || *(unsigned short *)(v + 14) != r->height ||
            *(short *)(v + 20) != r->hx || *(short *)(v + 22) != r->hy ||
            *(short *)(v + 24) != r->ax || *(short *)(v + 26) != r->ay) {
            chaos_refused(3, i, before, v);
            chaosDone[i] = 1;
            continue;
        }
        char path[96], original[96];
        chaos_path(path, i, (GraphicsDebug[1] & r->category) != 0);
        chaos_path(original, i, 1);
        if (!theme_png(path, r->width, r->height) || !theme_png(original, r->width, r->height)) {
            ChaosState[6] = 5;
            chaosDone[i] = 1;
            continue;
        }
        I settings[6] = {24, r->hx, r->hy, r->ax, r->ay, -1};
        I (*load)(U, S, I *) = (void *)0x42b8a0;
        void (*active)(U, S, I, I, I, I, I, I, I, I) = (void *)0x42bec0;
        if (r->type == 1)
            load(pointer, path, settings);
        else
            active(object, path, r->anim, r->direction, r->frame, r->hx, r->hy, r->ax, r->ay, -1);
        /* MMF may copy-on-write the common bank inside its animation action.
         * Never dereference the pointer cached before that call. */
        if (r->type == 2) {
            c = *(U *)(object + 0x44);
            pointer = c >= 65536 ? chaos_pointer(c, r) : 0;
        }
        U after = pointer ? *(unsigned short *)pointer : 0;
        if (!after) {
            ChaosState[6] = 6;
        } else {
            if (r->oi == 617)
                chaosCloudReady = 1;
            chaosHandles[i] = after;
            chaosApplied[i] = GraphicsDebug[1] & r->category;
            ChaosState[3]++;
            ChaosState[5]++;
            ChaosState[r->category == 1 ? 8 : r->category == 2 ? 9 : r->category == 4 ? 10 : 11]++;
        }
        chaosDone[i] = 1;
        changed++;
        if (r->type == 1) {
            *(U *)(definition + 28) |= 0x20;
            redraw = 1;
        }
        if (changed >= 4 || GetTickCount() - start >= 8)
            break;
    }
    chaos_clouds(run, scene);
    if (redraw)
        chaos_redraw(run);
    ChaosState[13] = GetTickCount() - start;
    if (ChaosState[13] > ChaosState[12])
        ChaosState[12] = ChaosState[13];
}
