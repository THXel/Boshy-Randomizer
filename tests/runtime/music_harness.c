#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
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
static I receipt_init(void) {
    return 1;
}
static I samebytes(const unsigned char *a, const unsigned char *b, U n) {
    return !memcmp(a, b, n);
}
static I hook(U a, H b) {
    return 1;
}
static void pack_observe(U action) {}
static I pack_action(U action) {
    return 0;
}
#include "../music_randomizer.c"
static U played, originals, gotflags, locks;
static I gotloops, gotchannel;
static void play(S path, U flags, I loops, I channel) {
    assert(!strcmp(path, "replacement.ogg"));
    played++;
    gotflags = flags;
    gotloops = loops;
    gotchannel = channel;
}
static void reserve(I channel, I enabled) {
    assert(channel == 2 && enabled == 1);
    locks++;
}
static void original(U action) {
    originals++;
}
static U a = 0x1000000;
static void setup(U code) {
    memset((void *)(uintptr_t)a, 0, 128);
    *(unsigned short *)(uintptr_t)a = code == 11 ? 108 : 128;
    *(unsigned short *)(uintptr_t)(a + 4) = code;
    strcpy((char *)(uintptr_t)(a + 22), "known background");
    U *p = (U *)(uintptr_t)(a + 88);
    p[0] = 0x00160014;
    p[1] = 0xffff0000;
    p[2] = 0x000a0000;
    p[3] = 2;
    p[5] = 0x001b0014;
    p[6] = 0xffff0000;
    p[7] = 0x000a0000;
}
int main(void) {
    assert(mmap((void *)0x41f000, 4096, 7, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0) !=
           (void *)-1);
    assert(mmap((void *)(uintptr_t)a, 4096, 3, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0) !=
           (void *)-1);
    unsigned char *j = (void *)0x41f9a0;
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
    q->a = 4096;
    q->scene = 36;
    musicCount = 1;
    musicOriginal = original;
    strcpy(musicRows[0].name, "known background");
    strcpy(musicRows[0].path, "replacement.ogg");
    for (U code = 11; code <= 12; code++)
        for (U priority = 0; priority <= 1; priority++) {
            setup(code);
            *(unsigned char *)(uintptr_t)(a + 20) = priority;
            music_action(a);
            assert(gotflags == (0x10010 | (priority ? 2 : 0)) && gotloops == 0 && gotchannel == 2);
        }
    assert(played == 4 && originals == 0);
    setup(11);
    strcpy((char *)(uintptr_t)(a + 22), "jingle");
    music_action(a);
    setup(12);
    *(U *)(uintptr_t)(a + 120) = 3;
    music_action(a);
    setup(11);
    *(U *)(uintptr_t)(a + 100) = 8;
    music_action(a);
    setup(11);
    q->a = 0;
    music_action(a);
    q->a = 4096;
    setup(11);
    *(unsigned short *)(uintptr_t)(a + 4) = 4;
    music_action(a); /* stop/pause: untouched */
    assert(played == 4 && originals == 5 && locks == 4);
    puts("Music loop, priority, channel, jingles and stop delegation passed");
}
