/* Cosmetic-only static backdrops: no Active objects, events or collision masks.
 * All object identities and scene masks are reviewed against the verified EXE. */
typedef struct {U oi,width,height,low,high;} SceneryObject;
#include "sprite_scenery_catalogue.h"
#define SCENERY_COUNT (sizeof(sceneryObjects)/sizeof(*sceneryObjects))
U SceneryState[8]={1,0,0,0,0,0,0,0}; /* version, enabled, plan, total, scene, changed, error, skipped */
static U sceneryLoaded,sceneryRun,sceneryScene=~0U,sceneryTick;
static U sceneryHandles[SCENERY_COUNT],sceneryApplied[SCENERY_COUNT];
static void scenery_path(char*out,U i,I original){
 S prefix="..\\menu-runtime\\scenery\\";U n=0;for(;prefix[n];n++)out[n]=prefix[n];
 if(original)out[n++]='o';out[n++]='0'+i/10;out[n++]='0'+i%10;out[n++]='.';out[n++]='p';out[n++]='n';out[n++]='g';out[n]=0;
}
static I scenery_plan(void){
 if(sceneryLoaded)return SceneryState[2]==1;sceneryLoaded=1;
 if(!receipt_init()||*(U*)0x42b8a0!=0x1468ff6a){SceneryState[6]=1;return 0;}
 unsigned char plan[40],extra;U got=0,more=0;
 H f=CreateFileA("..\\menu-runtime\\scenery.bin",0x80000000,1,0,3,0,0);if(f==(H)-1){SceneryState[6]=2;return 0;}
 I ok=ReadFile(f,plan,40,&got,0);ok=ok&&ReadFile(f,&extra,1,&more,0);CloseHandle(f);
 if(!ok||got!=40||more||!samebytes(plan,(const unsigned char*)"BRV1",4)||!samebytes(plan+4,(const unsigned char*)q-304284+64,32)||*(U*)(plan+36)!=SCENERY_COUNT){SceneryState[6]=3;return 0;}
 SceneryState[2]=1;return 1;
}
static I scenery_in_scene(const SceneryObject*r,U scene){return scene<32?((r->low>>scene)&1):scene<64?((r->high>>(scene-32))&1):0;}
static void scenery_tick(U run,U scene){
 SceneryState[1]=(q->a&16384)!=0;SceneryState[4]=scene;
 if(!SceneryState[1]||scene<2||scene>=64)return;
 U tick=*(U*)(run+0xd0);
 if(run==sceneryRun&&scene==sceneryScene&&tick>=sceneryTick){sceneryTick=tick;return;}
 sceneryRun=run;sceneryScene=scene;sceneryTick=tick;SceneryState[5]=0;SceneryState[7]=0;
 if(!scenery_plan())return;
 U app=*(U*)0x459a94;if(app<0x10000){SceneryState[6]=4;return;}
 U bank=*(U*)(app+0x1c4);if(bank<0x10000){SceneryState[6]=4;return;}
 I(W*getinfo)(U,U,U,U,U,H)=(void*)0x450de6;
 for(U i=0;i<SCENERY_COUNT;i++){
  const SceneryObject*r=&sceneryObjects[i];if(!scenery_in_scene(r,scene))continue;
  U definition=theme_definition(r->oi),common=definition?*(U*)(definition+20):0;
  if(!definition||*(unsigned short*)(definition+2)!=1||common<0x10000||*(U*)common!=18||*(U*)(common+4)!=0||*(U*)(common+8)!=r->width||*(U*)(common+12)!=r->height){SceneryState[7]++;continue;}
  U pointer=common+16,before=*(unsigned short*)pointer;
  if((GraphicsDebug[1]&1)&&before!=sceneryHandles[i]){sceneryHandles[i]=before;sceneryApplied[i]=1;continue;}
  if(before&&before==sceneryHandles[i]&&sceneryApplied[i]==(GraphicsDebug[1]&1))continue;
  unsigned char info[64]={0};
  if(!before||before>=32768||!getinfo(bank,before,0,0x3f800000,0x3f800000,info)||*(unsigned short*)(info+12)!=r->width||*(unsigned short*)(info+14)!=r->height){SceneryState[7]++;continue;}
  char path[96],original[96];scenery_path(path,i,(GraphicsDebug[1]&1)!=0);scenery_path(original,i,1);
  if(!theme_png(path,r->width,r->height)||!theme_png(original,r->width,r->height)){SceneryState[6]=5;continue;}
  I settings[6]={24,*(short*)(info+20),*(short*)(info+22),0,0,-1};I(*load)(U,S,I*)=(void*)0x42b8a0;
  if(!load(pointer,path,settings)||!*(unsigned short*)pointer){load(pointer,original,settings);SceneryState[6]=6;}
  else{sceneryHandles[i]=*(unsigned short*)pointer;sceneryApplied[i]=GraphicsDebug[1]&1;SceneryState[3]++;SceneryState[5]++;}
  *(U*)(definition+28)|=0x20;*(unsigned char*)(run+0x1a7)|=2;
 }
}
