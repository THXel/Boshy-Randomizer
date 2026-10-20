#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
typedef uint32_t U;typedef int I;typedef const char*S;typedef void*H;
#define W
#define CreateFileA(...) ((H)-1)
#define ReadFile(...) 0
#define CloseHandle(...) 0
static U GetTickCount(void){return 1;}
static I receipt_init(void){return 1;}
static I hexchar(char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}
static I theme_png(S p,U w,U h){return 0;}
static U theme_definition(U o){return 0;}
static I hook(U a,void*f){return 1;}
static U spider_player(U r,U s){return 0;}
static void pack_death_clear(void){}
static U packDeathSerial,packDeathRun,packDeathTick;
static void*q=(void*)1;
#include "../death_visuals.c"
static U changed,delegated,opacityUpdates,object=0x1000000;
static U selected(U a){return object;}
static void scale(U o,U x,U y,I quality){assert(o==object&&x==0x3f800000&&y==x&&quality==0);changed++;}
static void original(U a){delegated++;}
static void opacity(U o){assert(o==object);opacityUpdates++;}
static void jump(U address,void*fn){unsigned char*p=(void*)(uintptr_t)address;p[0]=0x48;p[1]=0xb8;*(uintptr_t*)(p+2)=(uintptr_t)fn;p[10]=0xff;p[11]=0xe0;}
int main(void){
 for(U i=0;i<1000;i++){assert(death_index(i,10,40,32)<40);if(i>=200)assert(death_index(i,10,40,32)>=32);}
 deathPlan.screenFps=0;deathPlan.screenCount=4;deathPlan.screenLoop=2;
 deathDurations[0]=5;deathDurations[1]=1;deathDurations[2]=1;deathDurations[3]=5;
 assert(death_screen_index(4)==0&&death_screen_index(5)==1&&death_screen_index(6)==2&&death_screen_index(7)==3&&death_screen_index(12)==2&&death_screen_index(13)==3);
 assert(mmap((void*)0x411000,4096,7,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 assert(mmap((void*)0x449000,4096,7,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 assert(mmap((void*)(uintptr_t)object,8192,3,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 assert(mmap((void*)0x412000,4096,7,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 jump(0x4127a0,opacity);jump(0x412d10,original);jump(0x449500,selected);jump(0x4113e0,scale);jump(0x4114c0,original);
 U action=object+4096;*(unsigned short*)(uintptr_t)(action+6)=161;*(unsigned short*)(uintptr_t)(object+0x12)=161;*(U*)(uintptr_t)(object+0x44)=0x2000000;deathCommon[0]=0x2000000;
 deathReady=0;death_scale_action(action);assert(delegated==1&&!changed);
 deathReady=1;death_scale_action(action);assert(changed==1&&delegated==1);
 *(unsigned short*)(uintptr_t)(action+6)=93;death_scale_action(action);assert(delegated==2&&changed==1);
 *(unsigned short*)(uintptr_t)(action+6)=161;deathCommon[0]=0x2001000;death_scale_action(action);assert(delegated==3&&changed==1);
 deathCommon[0]=0x2000000;*(U*)(uintptr_t)(object+0xbc)=0x300;*(U*)(uintptr_t)(object+0x318)=0x1000;*(U*)(uintptr_t)(object+0x31c)=0x00ffffff;
 death_alpha_action(action);assert(opacityUpdates==1&&delegated==3&&*(U*)(uintptr_t)(object+0x31c)==0xffffffff);
 death_alpha_action(action);assert(opacityUpdates==1&&delegated==3);
 deathReady=0;death_alpha_action(action);assert(delegated==4);
 deathReady=1;*(unsigned short*)(uintptr_t)(action+6)=93;death_alpha_action(action);assert(delegated==5);
 *(unsigned short*)(uintptr_t)(action+6)=161;*(U*)(uintptr_t)(object+0x318)=13;death_alpha_action(action);assert(delegated==6);
 puts("Variable death timing and isolated no-bounce action passed");
}
