#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
typedef uint32_t U;
typedef int I;
typedef const char *S;
typedef void *H;
struct Shared {
    U a, scene;
};
static struct Shared shared, *q = &shared;
#define CreateFileA(...) ((H) - 1)
#define ReadFile(...) 0
#define CloseHandle(...) 0
static U GetTickCount(void) {
    return 1;
}
static I receipt_init(void) {
    return 1;
}
static I samebytes(const unsigned char *a, const unsigned char *b, U n) {
    return !memcmp(a, b, n);
}
#include "../soundpack.c"
static U played, gotflags, locked, stopped, stopMask;
static I gotchannel;
static void play(S path, U flags, I loops, I channel) {
    assert(!strcmp(path, "test.wav"));
    assert(loops == 0);
    played++;
    gotflags = flags;
    gotchannel = channel;
}
static void reserve(I channel, I enabled) {
    assert((channel == 2 && enabled == 1) || channel == 32);
    locked += enabled;
}
static void stop(I channel) {
    assert(channel >= 1 && channel <= 32);
    stopMask |= 1U << (channel - 1);
    stopped++;
}
static U a = 0x1000000;
static void setup(U code, U kind, S name) {
    memset((void *)(uintptr_t)a, 0, 128);
    *(unsigned short *)(uintptr_t)a = code == 0 ? 88 : code == 12 ? 128 : 108;
    *(unsigned short *)(uintptr_t)(a + 4) = code;
    strcpy((char *)(uintptr_t)(a + 22), name);
    strcpy(packRows[0].name, name);
    strcpy(packRows[0].path, "test.wav");
    packRows[0].kind = kind;
    packCount = 1;
    U *p = (U *)(uintptr_t)(a + 88);
    p[0] = 0x00160014;
    p[1] = 0xffff0000;
    p[2] = 0x000a0000;
    p[3] = 2;
}
int main(void) {
    assert(mmap((void *)0x41f000, 4096, 7, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0) !=
           (void *)-1);
    assert(mmap((void *)(uintptr_t)a, 4096, 3, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0) !=
           (void *)-1);
    assert(mmap((void *)0x459000, 4096, 3, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0) !=
           (void *)-1);
    unsigned char *j = (void *)0x41fab0;
    j[0] = 0x48;
    j[1] = 0xb8;
    *(uintptr_t *)(j + 2) = (uintptr_t)stop;
    j[10] = 0xff;
    j[11] = 0xe0;
    j = (void *)0x41f9a0;
    j[0] = 0x48;
    j[1] = 0xb8;
    *(uintptr_t *)(j + 2) = (uintptr_t)play;
    j[10] = 0xff;
    j[11] = 0xe0;
    j = (void *)0x41fe30;
    j[0] = 0x48;
    j[1] = 0xb8;
    *(uintptr_t *)(j + 2) = (uintptr_t)reserve;
    j[10] = 0xff;
    j[11] = 0xe0;
    q->scene = 1;
    q->a = 0;
    setup(11, 1, "opening");
    assert(pack_action(a));
    assert(gotflags == 0x10010 && gotchannel == 2 && locked == 1);
    setup(0, 2, "Death 3");
    assert(!pack_action(a));
    assert(played == 1 && stopped == 0);
    setup(11, 2, "Death 3");
    assert(!pack_action(a));
    assert(played == 1 && stopped == 0);
    setup(11, 2, "Dead");
    *(U *)(uintptr_t)(a + 100) = 5;
    assert(!pack_action(a));
    setup(11, 2, "Death 3");
    *(U *)(uintptr_t)(a + 100) = 5;
    assert(pack_action(a));
    assert(gotflags == 0x10000 && gotchannel == 32 && locked == 2);
    assert(stopped == 32 && stopMask == 0xffffffffU);
    setup(0, 2, "Death 3");
    assert(pack_action(a));
    assert(played == 2);
    setup(0, 1, "boss voice");
    assert(pack_action(a));
    assert(played == 2);
    pack_death_clear();
    assert(stopped == 33 && !packDeathPlaying);
    pack_death_clear();
    assert(stopped == 33);
    setup(12, 1, "select");
    q->scene = 2;
    assert(!pack_action(a));
    q->scene = 19;
    assert(pack_action(a));
    assert(gotflags & 0x10);
    setup(11, 2, "Death 3");
    *(U *)(uintptr_t)(a + 96) = 0xDEAD;
    assert(!pack_action(a));
    for (U code = 1; code < 4; code++) {
        setup(code, 2, "Death 3");
        assert(!pack_action(a));
    }
    setup(11, 2, "Death 3");
    strcpy((char *)(uintptr_t)(a + 22), "boss voice");
    assert(!pack_action(a));
    packCount = 0;
    assert(!pack_action(a));
    pack_death_clear();
    assert(stopped == 33 && !packDeathPlaying);
    assert(played == 3);
    puts("Sound pack music, one-shot death, menu scope, dynamic channel and original fallback "
         "passed");
}
