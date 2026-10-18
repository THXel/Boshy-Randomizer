#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
typedef uint32_t U;typedef int I;typedef const char*S;typedef void*H;
#define W
struct Shared {U a,enabled,scene;};static struct Shared shared,*q=&shared;
static U now,pressed,guardOn,removed,added,killed,moved,loaded;static H foreground=(H)123;
static U GetTickCount(void){return now;}
static short oldAsync(int k){return pressed==(U)k?0x8000:0;}
static H GetForegroundWindow(void){return foreground;}
static I receipt_init(void){return 1;}
#define CreateFileA(...) ((H)-1)
#define ReadFile(...) 0
#define CloseHandle(...) 0
static I samebytes(const unsigned char*a,const unsigned char*b,U n){return !memcmp(a,b,n);}
#include "../spider_randomizer.c"
static I load_image(U out,S path,I*settings){*(U*)(uintptr_t)out=100+(++loaded);return 1;}
static U add(U manager,I x,I y,U image,U layer,U z,U flags,U extra,U data){added++;return 77;}
static void remove_sprite(U manager,U sprite){assert(sprite==77);removed++;}
static void move_sprite(U manager,U sprite,I x,I y,U image){assert(sprite==77);moved++;}
static void play(S path,U flags,I loops,I channel){assert(channel==8);}
static void die(void*action){killed++;}
static void map(U address,U size){assert(mmap((void*)(uintptr_t)address,size,7,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);}
static void jump(U address,void*target){unsigned char*p=(void*)(uintptr_t)address;p[0]=0x48;p[1]=0xb8;*(uintptr_t*)(p+2)=(uintptr_t)target;p[10]=0xff;p[11]=0xe0;}
static U r=0x1000000,p=0x2000000,scene;
static void tick(void){now+=16;(*(U*)(uintptr_t)(r+0xd0))++;spider_tick(r,scene);}
static void reset(void){
 memset((void*)(uintptr_t)r,0,0x3000);memset((void*)(uintptr_t)p,0,0x1000);memset(SpiderState,0,sizeof SpiderState);
 SpiderState[0]=0x42525331;SpiderState[1]=1;SpiderState[3]=123;spiderLoaded=1;spiderImage=1;memset(spiderImages,0,sizeof spiderImages);loaded=0;spiderSprite=spiderPlayer=spiderRun=spiderTick=spiderNow=0;
 scene=3;U oi=0;for(U i=0;i<sizeof(spiderPlayers)/sizeof(*spiderPlayers);i++)if(spiderPlayers[i].scene==scene)oi=spiderPlayers[i].oi;assert(oi);
 *(U*)(uintptr_t)(r+0x1278)=r+0x2000;*(U*)(uintptr_t)(r+0x40)=1;*(U*)(uintptr_t)(r+0x2000)=p;*(H*)(uintptr_t)(r+0x10)=(H)123;
 *(unsigned short*)(uintptr_t)(p+18)=oi;*(unsigned short*)(uintptr_t)(p+24)=2;*(I*)(uintptr_t)(p+0x4c)=320;*(I*)(uintptr_t)(p+0x54)=240;
 q->a=8192|32;q->enabled=1;foreground=(H)123;guardOn=pressed=removed=added=killed=moved=0;now=1000;tick();SpiderState[9]=0;
}
int main(void){
 map(0x42b000,0x1000);jump(0x42b8a0,load_image);
 map(r,0x3000);map(p,0x1000);map(0x450000,0x2000);map(0x41f000,0x1000);map(0x415000,0x1000);
 jump(0x450a08,add);jump(0x450a1a,remove_sprite);jump(0x451926,move_sprite);jump(0x41f9a0,play);jump(0x415140,die);
 reset();tick();assert(added==1&&SpiderState[6]&&SpiderState[2]>=300000&&SpiderState[2]<=1800000);U remaining=SpiderState[2];
 *(U*)(uintptr_t)(r+0x178)=1;tick();assert(removed==1&&!SpiderState[6]&&SpiderState[2]==remaining);tick();assert(removed==1);*(U*)(uintptr_t)(r+0x178)=0;tick();assert(SpiderState[2]<remaining);
 reset();tick();foreground=0;remaining=SpiderState[2];tick();assert(removed==1&&SpiderState[2]==remaining);
 reset();tick();pressed=82;tick();assert(removed==1&&!SpiderState[6]);pressed=0;*(U*)(uintptr_t)(r+0xd0)=0;tick();assert(SpiderState[9]>14000);
 reset();tick();assert(loaded>=1&&spiderImage>=101);scene=4;tick();assert(!SpiderState[6]&&!removed&&SpiderState[9]>14000&&spiderImage==0);scene=3;tick();SpiderState[9]=0;SpiderState[2]=0;tick();assert(loaded>=2&&spiderImage>=102); /* Old scene owns and disposes its sprites. */
 reset();tick();*(U*)(uintptr_t)(r+0x2000)=0;tick();assert(removed==1&&SpiderState[9]==15000&&!spiderPlayer);
 reset();tick();spiderX=320000;spiderY=240000;spiderDX=spiderDY=0;tick();assert(killed==0&&SpiderState[5]==0);q->a=8192;tick();assert(killed==1&&SpiderState[5]==1&&removed==1);tick();assert(killed==1);
 reset();q->a=0;tick();assert(!added);q->a=8192;SpiderState[9]=15000;tick();assert(!added);
 unsigned sides=0,angles=0;for(U seed=1;seed<=256;seed++){
  SpiderState[3]=seed;spider_begin(1320,2240,1000,2000);sides|=1U<<SpiderVisual[1];
  I x=spiderX/1000-1000,y=spiderY/1000-2000;
  assert((x==-112||x==752||y==-112||y==592));
  assert(spiderDX*spiderDX+spiderDY*spiderDY>=472*472&&spiderDX*spiderDX+spiderDY*spiderDY<=477*477);
  assert((1320000-spiderX)*spiderDX+(2240000-spiderY)*spiderDY>0);
  angles|=1U<<spider_facing(1320-spiderX/1000,2240-spiderY/1000);
 }
 assert(sides==15);printf("angle coverage %08x\n",angles);
 for(U i=0;i<32;i++)assert(spider_facing(spiderDirections[i][0],spiderDirections[i][1])==i);
 assert(spider_facing(0,100)==0&&spider_facing(100,0)==8&&spider_facing(0,-100)==16&&spider_facing(-100,0)==24);
 puts("Native spider: timer, pause, focus, reset, scene disposal, stale player, God Mode and one lethal hit passed");
}
