#include <assert.h>
#include <stdint.h>
#include <sys/mman.h>
#include <stdio.h>
typedef uint32_t U;typedef int I;typedef const char*S;typedef void*H;
struct Shared {U scene,enabled;};static struct Shared memory[300];static struct Shared*q=memory;
static U guardRun,guardScene,guardPause,guardSince,guardOn,now,pressed;
static U GetTickCount(void){return now;}
static short oldAsync(int k){return pressed==(U)k?0x8000:0;}
static I hook(U a,H b){(void)a;(void)b;return 1;}
#include "../fast_exit.c"
static U r=0x1000000,command=1,dest=0;
static void original(U action){(void)action;*(unsigned short*)(uintptr_t)(r+0x30)=command;*(U*)(uintptr_t)(r+0x38)=dest;}
static void arm(void){
 q->scene=3;q->enabled=1;*(U*)(uintptr_t)(r+0xd0)=20;
 exit_tick(r,3);volatile U*c=exit_control();c[1]=1<<4;c[2]=0;c[3]=1;exit_tick(r,3);
}
int main(void){
 assert(mmap((void*)0x459000,4096,3,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 assert(mmap((void*)(uintptr_t)r,4096,3,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 *(U*)0x459a9c=r;exitOriginal=original;volatile U*c=exit_control();
 arm();exit_action(0);assert(c[3]==260&&exitWaiting&&guardOn&&*(unsigned short*)(uintptr_t)(r+0x30)==0);
 exit_action(0);assert(*(unsigned short*)(uintptr_t)(r+0x30)==0);
 now=500;exit_tick(r,3);assert(exitWaiting);
 now=1600;exit_tick(r,3);assert(!exitWaiting&&c[3]==0&&*(unsigned short*)(uintptr_t)(r+0x30)==1&&*(U*)(uintptr_t)(r+0x178)==0);
 *(unsigned short*)(uintptr_t)(r+0x30)=0;arm();command=3;dest=0x8004;exit_action(0);assert(c[3]==260);
 c[3]=3;*(unsigned short*)(uintptr_t)(r+0x30)=3;*(U*)(uintptr_t)(r+0x38)=0x802d;exit_tick(r,3);assert(*(U*)(uintptr_t)(r+0x38)==0x802d&&!exitWaiting);
 *(unsigned short*)(uintptr_t)(r+0x30)=0;arm();pressed=82;exit_action(0);assert(!exitWaiting);pressed=0;
 arm();exit_tick(r,4);assert(c[3]==0);arm();*(U*)(uintptr_t)(r+0xd0)=0;exit_tick(r,3);assert(c[3]==0);
 arm();command=2;exit_action(0);assert(!exitWaiting);command=3;dest=0x8007;exit_action(0);assert(!exitWaiting);
 arm();U app=r+512,table=r+1024;*(U*)0x459a94=app;*(U*)(uintptr_t)(app+0xcc)=table;*(unsigned short*)(uintptr_t)(app+0xc8)=10;*(unsigned short*)(uintptr_t)(table+14)=4;
 command=3;dest=7;exit_action(0);assert(c[3]==260&&exitWaiting);c[3]=2;exit_tick(r,3);assert(!exitWaiting);
 puts("Native exit: capture, jump, timeout, commit, reset, wrong room and R checks passed");
}
