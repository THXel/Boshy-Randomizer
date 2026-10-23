#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
typedef uint32_t U;
typedef int I;
typedef const char *S;
typedef void *H;
#define W
#define CreateFileA(...) ((H) - 1)
#define ReadFile(...) 0
#define CloseHandle(...) 0
struct Shared {
    U a;
};
static struct Shared shared, *q = &shared;
static U GraphicsDebug[4];
static U run = 0x1000000, object = 0x1002000, definition = 0x1003000, common = 0x1010000, imports,
         skeletonLookups, arenaLookups;
static U GetTickCount(void) {
    return 1;
}
static I receipt_init(void) {
    return 1;
}
static I samebytes(const unsigned char *a, const unsigned char *b, U n) {
    return !memcmp(a, b, n);
}
static I background_owns(U s, U o) {
    return 0;
}
static U theme_definition(U oi) {
    if (oi == 1054) {
        arenaLookups++;
        return definition;
    }
    if (oi == 1088 || oi == 1089) {
        skeletonLookups++;
        return definition;
    }
    return oi == 153 ? definition : 0;
}
static U intro_object(U r, U oi) {
    return oi == 153 ? object : 0;
}
static I theme_png(S p, U w, U h) {
    return 1;
}
#include "../sprite_chaos.c"
static const ChaosRecord *row;
static I info(U bank, U image, U angle, U sx, U sy, H output) {
    unsigned char *v = output;
    *(unsigned short *)(v + 12) = row->width;
    *(unsigned short *)(v + 14) = row->height;
    *(short *)(v + 20) = row->hx;
    *(short *)(v + 22) = row->hy;
    *(short *)(v + 24) = row->ax;
    *(short *)(v + 26) = row->ay;
    return 1;
}
static void active(U o, S path, I anim, I direction, I frame, I hx, I hy, I ax, I ay, I color) {
    assert(o == object);
    U old = *(U *)(o + 0x44), next = old + 4096;
    memcpy((void *)(uintptr_t)next, (void *)(uintptr_t)old, row->size);
    /* The engine can release the old allocation inside its own action. */
    assert(!mprotect((void *)(uintptr_t)old, 4096, PROT_NONE));
    *(U *)(o + 0x44) = next;
    ChaosRecord r = *row;
    r.anim = anim;
    r.direction = direction;
    r.frame = frame;
    *(unsigned short *)(uintptr_t)chaos_pointer(next, &r) = 500 + imports++;
}
static void jump(U addr, void *fn) {
    unsigned char *p = (void *)(uintptr_t)addr;
    p[0] = 0x48;
    p[1] = 0xb8;
    *(uintptr_t *)(p + 2) = (uintptr_t)fn;
    p[10] = 0xff;
    p[11] = 0xe0;
}
static void setup(void) {
    assert(!mprotect((void *)(uintptr_t)common, 4096 * 6, 3));
    memset((void *)(uintptr_t)common, 0, 4096 * 6);
    *(U *)(object + 0x44) = common;
    *(U *)(object + 0xb8) = 462;
    *(U *)common = row->size;
    *(unsigned short *)(common + 6) = row->offset;
    U bank = common + row->offset;
    *(unsigned short *)bank = row->bankSize;
    *(unsigned short *)(bank + 2) = row->animCount;
    *(unsigned short *)(bank + 4) = 36;
    *(unsigned short *)(bank + 36) = 64;
    *(unsigned short *)(bank + 36 + 64 + 6) = row->nframes;
    for (U n = 0; n < row->nframes; n++)
        *(unsigned short *)(bank + 36 + 64 + 8 + 2 * n) = 100 + n;
}
int main(void) {
    assert(mmap((void *)(uintptr_t)run, 0x20000, 3, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1,
                0) != (void *)-1);
    for (U a = 0x42b000; a <= 0x459000; a += 4096)
        assert(mmap((void *)(uintptr_t)a, 4096, 7, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1,
                    0) != (void *)-1);
    jump(0x450de6, info);
    jump(0x42bec0, active);
    for (U i = 0; i < CHAOS_COUNT; i++)
        if (chaosRecords[i].oi == 153) {
            row = &chaosRecords[i];
            break;
        }
    assert(row && row->nframes == 2);
    *(U *)0x459a94 = run + 0x4000;
    *(U *)(run + 0x4000 + 0x1c4) = run + 0x5000;
    *(unsigned short *)(definition + 2) = 2;
    *(U *)(definition + 20) = run + 0x6000; /* Deliberately stale definition. */
    setup();
    q->a = 32768;
    chaosLoaded = 1;
    chaosMask = 8;
    ChaosState[2] = 1;
    *(U *)(run + 0xd0) = 5;
    chaos_tick(run, 2);
    assert(imports == 2 && ChaosState[6] == 0 && ChaosState[7] == 0);
    /* Same-room resets can reuse numerical handles and RunHeader addresses. */
    setup();
    *(U *)(run + 0xd0) = 1;
    chaos_tick(run, 2);
    assert(imports == 4 && ChaosState[6] == 0 && ChaosState[7] == 0);
    /* Lazy skeleton types share original images with enemies outside the
     * palette catalogue. Neither first entry nor a same-scene reset may touch
     * those banks: later native spawns still need their original image handles. */
    setup();
    *(U *)(run + 0xd0) = 5;
    chaos_tick(run, 14);
    assert(imports == 4 && skeletonLookups == 0 && ChaosState[6] == 0 && ChaosState[7] == 0);
    setup();
    *(U *)(run + 0xd0) = 1;
    chaos_tick(run, 14);
    assert(imports == 4 && skeletonLookups == 0 && ChaosState[6] == 0 && ChaosState[7] == 0);
    /* The animated arena is a gameplay cue, despite its legacy background
     * category. All categories, both encounters and reused-room resets must
     * preserve the original bank without attempting an image import. */
    chaosMask = 15;
    for (U encounter = 0; encounter < 2; encounter++) {
        U scene = encounter ? 59 : 13;
        for (U pass = 0; pass < 2; pass++) {
            setup();
            *(U *)(run + 0xd0) = pass ? 1 : 5;
            chaos_tick(run, scene);
            assert(imports == 4 && arenaLookups == 0 && ChaosState[6] == 0 && ChaosState[7] == 0);
        }
    }
    puts("Live animation banks, copy-on-write pointers and reused scene handles passed");
}
