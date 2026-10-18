/* Separate MMF sprite, never a replacement of the mouse or a gameplay object.
 * All simulation, collision and disposal run on the game's own thread. */
#include "spider_players.h"
U SpiderState[10]={0x42525331,0,0,0,0,0,0,0,0,0};
static U spiderLoaded,spiderImage,spiderRun,spiderScene,spiderTick,spiderNow,spiderSprite,spiderPlayer,spiderSlot;
static I spiderX,spiderY,spiderDX,spiderDY;static U spiderAge,spiderFacing,spiderImages[32];
/* Visual-only diagnostics, separate from the saved timer/state layout. */
U SpiderVisual[8]={2,0,0,0,0,0,0,475};
static const I spiderDirections[32][2]={{0,1000},{195,981},{383,924},{556,831},{707,707},{831,556},{924,383},{981,195},{1000,0},{981,-195},{924,-383},{831,-556},{707,-707},{556,-831},{383,-924},{195,-981},{0,-1000},{-195,-981},{-383,-924},{-556,-831},{-707,-707},{-831,-556},{-924,-383},{-981,-195},{-1000,0},{-981,195},{-924,383},{-831,556},{-707,707},{-556,831},{-383,924},{-195,981}};
static U spider_facing(I dx,I dy){
 if(!dx&&!dy)return spiderFacing;
 I best=-2147483647;U result=0;
 for(U i=0;i<32;i++){I dot=dx*spiderDirections[i][0]+dy*spiderDirections[i][1];if(dot>best){best=dot;result=i;}}
 return result;
}
static U spider_sqrt(U n){U result=0,bit=1U<<30;while(bit>n)bit>>=2;while(bit){if(n>=result+bit){n-=result+bit;result=(result>>1)+bit;}else result>>=1;bit>>=2;}return result;}

static U spider_random(void){U x=SpiderState[3];x^=x<<13;x^=x>>17;x^=x<<5;return SpiderState[3]=x?x:1;}
static void spider_remove(U run){
 if(spiderSprite&&run==spiderRun){void(W*remove)(U,U)=(void*)0x450a1a;remove(*(U*)run,spiderSprite);}
 spiderSprite=0;SpiderState[6]=0;
}
static I spider_load(void){
 if(spiderLoaded)return SpiderState[1]==1;spiderLoaded=1;
 if(!receipt_init()||*(U*)0x42b8a0!=0x1468ff6a||*(unsigned short*)0x450a08!=0x25ff||*(U*)(0x450a08+2)!=0x459400||*(unsigned short*)0x450a1a!=0x25ff||*(U*)(0x450a1a+2)!=0x459404){SpiderState[7]=1;return 0;}
 unsigned char plan[56];U got=0,more=0;unsigned char extra;
 H f=CreateFileA("..\\menu-runtime\\spider.bin",0x80000000,1,0,3,0,0);if(f==(H)-1){SpiderState[7]=2;return 0;}
 I ok=ReadFile(f,plan,56,&got,0);ok=ok&&ReadFile(f,&extra,1,&more,0);CloseHandle(f);
 if(!ok||got!=56||more||!samebytes(plan,(const unsigned char*)"BRS1",4)||!samebytes(plan+4,(const unsigned char*)q-304284+64,32)||!*(U*)(plan+36)||*(U*)(plan+40)>1800000||*(U*)(plan+52)!=1){SpiderState[7]=3;return 0;}
 SpiderState[3]=*(U*)(plan+36);SpiderState[2]=*(U*)(plan+40);SpiderState[4]=*(U*)(plan+44);SpiderState[5]=*(U*)(plan+48);SpiderState[1]=1;return 1;
}
static I spider_image(U facing){
 /* Lazy, per-scene cache. Rotations keep the same body-centred hotspot. */
 if(spiderImages[facing]){spiderImage=spiderImages[facing];return 1;}
 char path[]="..\\menu-runtime\\spider-00.png";
 U n=sizeof(path)-7;path[n]='0'+facing/10;path[n+1]='0'+facing%10;
 I settings[6]={24,96,96,0,0,-1};I(*load)(U,S,I*)=(void*)0x42b8a0;
 if(!load((U)&spiderImages[facing],path,settings)||!spiderImages[facing]){SpiderState[7]=4;return 0;}
 spiderImage=spiderImages[facing];return 1;
}
static void spider_begin(I px,I py,I sx,I sy){
 U side=spider_random()%4,along=spider_random();I x,y;
 if(side<2){x=side?752:-112;y=(I)(along%481);}else{x=(I)(along%641);y=side==2?-112:592;}
 spiderX=(sx+x)*1000;spiderY=(sy+y)*1000;
 I dx=px-sx-x,dy=py-sy-y;U length=spider_sqrt((U)(dx*dx+dy*dy));if(!length)length=1;
 /* Fixed 475 pixels/s in every direction; flight stays dodgeable and straight. */
 spiderDX=dx*475/(I)length;spiderDY=dy*475/(I)length;
 SpiderVisual[1]=side;SpiderVisual[5]=(U)spiderDX;SpiderVisual[6]=(U)spiderDY;
}
static U spider_player(U run,U scene){
 U oi=0;for(U i=0;i<sizeof(spiderPlayers)/sizeof(*spiderPlayers);i++)if(spiderPlayers[i].scene==scene){oi=spiderPlayers[i].oi;break;}if(!oi)return 0;
 U table=*(U*)(run+0x1278),n=*(U*)(run+0x40);if(table<0x10000||n>20000)return 0;
 if(spiderPlayer){U slot=spiderSlot;if(slot<n&&*(U*)(table+slot*8)==spiderPlayer&&*(unsigned short*)(spiderPlayer+18)==oi&&!( *(unsigned short*)(spiderPlayer+0x7c)&1))return spiderPlayer;}
 spiderPlayer=0;
 for(U i=0;i<n;i++){U o=*(U*)(table+i*8);if(o>=0x10000&&*(unsigned short*)(o+18)==oi&&*(unsigned short*)(o+24)==2&&!(*(unsigned short*)(o+0x7c)&1)){spiderPlayer=o;spiderSlot=i;break;}}
 return spiderPlayer;
}
static void spider_kill(U run){
 /* Original Q action: run the game's Die fastloop once. It handles saves,
  * death count, animation and reset normally. God Mode is checked by caller. */
 static unsigned char die[]={54,0,255,255,14,0,0,0,0,0,0,0,2,0,20,0,45,0,0,0,255,255,3,0,10,0,68,105,101,0,0,0,0,0,20,0,22,0,0,0,255,255,0,0,10,0,1,0,0,0,0,0,0,0};
 U saved=*(U*)(run+0x404);*(U*)(run+0x404)=(U)die;void(*call)(void*)=(void*)0x415140;call(die);*(U*)(run+0x404)=saved;
}
static void spider_tick(U run,U scene){
 U now=GetTickCount(),dt=spiderNow?now-spiderNow:0;spiderNow=now;if(dt>100)dt=100;
 if(!(q->a&8192))return;
 U tick=*(U*)(run+0xd0);
 if(spiderRun!=run||spiderScene!=scene||tick<spiderTick){spiderSprite=0;spiderImage=0;for(U i=0;i<32;i++)spiderImages[i]=0;spiderPlayer=0;spiderRun=run;spiderScene=scene;SpiderState[6]=0;SpiderState[9]=15000;}
 if(tick==spiderTick)return;spiderTick=tick;
 if(scene<=1||scene==20||q->enabled!=1||guardOn||*(U*)(run+0x178)||*(unsigned short*)(run+0x30)||GetForegroundWindow()!=*(H*)(run+0x10)||(oldAsync(82)&0x8000)||(oldAsync(81)&0x8000)){spider_remove(run);return;}
 U p=spider_player(run,scene);if(!p){spider_remove(run);SpiderState[9]=15000;return;}
 U rel=*(U*)(p+0x80);if(rel>0&&rel<4096&&(*(U*)(p+rel+0x68)&(1U<<5))){spider_remove(run);return;}
 if(!spider_load())return;
 SpiderState[8]+=dt;
 if(SpiderState[9]){SpiderState[9]=SpiderState[9]>dt?SpiderState[9]-dt:0;return;}
 I px=*(I*)(p+0x4c),py=*(I*)(p+0x54),sx=*(I*)(run+0xb0),sy=*(I*)(run+0xb4);
 /* Ignore invalid/off-map player coordinates before vector arithmetic. */
 if(px-sx>8192||px-sx< -8192||py-sy>8192||py-sy< -8192){spider_remove(run);return;}
 if(!spiderSprite){
  if(SpiderState[2]>dt){SpiderState[2]-=dt;return;}
  SpiderState[2]=300000+spider_random()%1500001;
  spider_begin(px,py,sx,sy);
  spiderFacing=spider_facing(px-spiderX/1000,py-spiderY/1000);
  if(!spider_image(spiderFacing))return;
  U(W*add)(U,I,I,U,U,U,U,U,U)=(void*)0x450a08;
  U layer=*(U*)(p+0x84);spiderSprite=add(*(U*)run,spiderX/1000-sx,spiderY/1000-sy,spiderImage,layer,0x7fffffff,0,0,0);
  if(!spiderSprite){SpiderState[7]=5;return;}
  void(*play)(S,U,I,I)=(void*)0x41f9a0;play("..\\menu-runtime\\spider.ogg",0x10000,0,8);
  SpiderState[4]++;SpiderState[6]=1;spiderAge=0;
 }
 spiderAge+=dt;spiderX+=spiderDX*(I)dt;spiderY+=spiderDY*(I)dt;
 spiderFacing=spider_facing(px-spiderX/1000,py-spiderY/1000);
 if(!spider_image(spiderFacing)){spider_remove(run);return;}
 SpiderVisual[2]=spiderFacing;SpiderVisual[3]=(U)(spiderX/1000-sx);SpiderVisual[4]=(U)(spiderY/1000-sy);
 void(W*move)(U,U,I,I,U)=(void*)0x451926;move(*(U*)run,spiderSprite,spiderX/1000-sx,spiderY/1000-sy,spiderImage);
 I dx=px-spiderX/1000,dy=py-spiderY/1000;
 if(!(q->a&32)&&dx>-32&&dx<32&&dy>-32&&dy<32){spider_remove(run);SpiderState[5]++;SpiderState[9]=15000;spider_kill(run);return;}
 if(spiderAge>3500||spiderX/1000<sx-180||spiderX/1000>sx+820||spiderY/1000<sy-180||spiderY/1000>sy+660)spider_remove(run);
}
