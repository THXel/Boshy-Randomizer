/* Separate MMF sprite, never a replacement of the mouse or a gameplay object.
 * All simulation, collision and disposal run on the game's own thread. */
#include "spider_players.h"
U SpiderState[10]={0x42525331,0,0,0,0,0,0,0,0,0};
static U spiderLoaded,spiderImage,spiderRun,spiderScene,spiderTick,spiderNow,spiderSprite,spiderPlayer,spiderSlot;
static I spiderX,spiderY,spiderDX,spiderDY;static U spiderAge;
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
 I settings[6]={24,64,64,0,0,-1};I(*load)(U,S,I*)=(void*)0x42b8a0;
 if(!load((U)&spiderImage,"..\\menu-runtime\\spider.png",settings)||!spiderImage){SpiderState[7]=4;return 0;}
 SpiderState[3]=*(U*)(plan+36);SpiderState[2]=*(U*)(plan+40);SpiderState[4]=*(U*)(plan+44);SpiderState[5]=*(U*)(plan+48);SpiderState[1]=1;return 1;
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
 if(spiderRun!=run||spiderScene!=scene||tick<spiderTick){spiderSprite=0;spiderPlayer=0;spiderRun=run;spiderScene=scene;SpiderState[6]=0;SpiderState[9]=15000;}
 if(tick==spiderTick)return;spiderTick=tick;
 if(scene<=1||scene==20||q->enabled!=1||guardOn||*(U*)(run+0x178)||*(unsigned short*)(run+0x30)||GetForegroundWindow()!=*(H*)(run+0x10)||(oldAsync(82)&0x8000)||(oldAsync(81)&0x8000)){spider_remove(run);return;}
 U p=spider_player(run,scene);if(!p){spider_remove(run);SpiderState[9]=15000;return;}
 U rel=*(U*)(p+0x80);if(rel>0&&rel<4096&&(*(U*)(p+rel+0x68)&(1U<<5))){spider_remove(run);return;}
 if(!spider_load())return;
 SpiderState[8]+=dt;
 if(SpiderState[9]){SpiderState[9]=SpiderState[9]>dt?SpiderState[9]-dt:0;return;}
 I px=*(I*)(p+0x4c),py=*(I*)(p+0x54),sx=*(I*)(run+0xb0),sy=*(I*)(run+0xb4);
 if(!spiderSprite){
  if(SpiderState[2]>dt){SpiderState[2]-=dt;return;}
  SpiderState[2]=300000+spider_random()%1500001;
  I left=spider_random()&1;spiderX=(sx+(left?-64:704))*1000;spiderY=(py-80+(I)(spider_random()%161))*1000;
  spiderDX=left?380:-380;I distance=(px*1000-spiderX)/spiderDX;if(distance<400)distance=400;spiderDY=(py*1000-spiderY)/distance;
  U(W*add)(U,I,I,U,U,U,U,U,U)=(void*)0x450a08;
  U layer=*(U*)(p+0x84);spiderSprite=add(*(U*)run,spiderX/1000-sx,spiderY/1000-sy,spiderImage,layer,0x7fffffff,0,0,0);
  if(!spiderSprite){SpiderState[7]=5;return;}
  void(*play)(S,U,I,I)=(void*)0x41f9a0;play("..\\menu-runtime\\spider.ogg",0x10000,0,8);
  SpiderState[4]++;SpiderState[6]=1;spiderAge=0;
 }
 spiderAge+=dt;spiderX+=spiderDX*(I)dt;spiderY+=spiderDY*(I)dt;
 void(W*move)(U,U,I,I,U)=(void*)0x451926;move(*(U*)run,spiderSprite,spiderX/1000-sx,spiderY/1000-sy,spiderImage);
 I dx=px-spiderX/1000,dy=py-spiderY/1000;
 if(!(q->a&32)&&dx>-32&&dx<32&&dy>-32&&dy<32){spider_remove(run);SpiderState[5]++;SpiderState[9]=15000;spider_kill(run);return;}
 if(spiderAge>3500||spiderX/1000<sx-180||spiderX/1000>sx+820)spider_remove(run);
}
