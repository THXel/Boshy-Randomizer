/* Cosmetic scene-1 frame replacement through MMF's own resource loader.
 * Movement, event banks, animation timing and gameplay objects are untouched. */
typedef struct {U oi,anim,direction,frame,width,height;I hx,hy;char path[96];} IntroFrame;
typedef struct {U magic,count;IntroFrame frames[32];} IntroPlan;
_Static_assert(sizeof(IntroPlan)==4104,"Intro plan ABI");
U IntroState[4]; /* status: 1 applied, 2 refused, 3 missing; frame count, run, scene */
static U introRun;
static U intro_object(U run,U oi){
 U table=*(U*)(run+0x1278),count=*(U*)(run+0x40);
 if(table<0x10000||count<1||count>20000)return 0;
 for(U i=0;i<count;i++){U o=*(U*)(table+i*8);if(o>=0x10000&&*(unsigned short*)(o+0x12)==oi&&*(unsigned short*)(o+0x18)==2)return o;}return 0;
}
static U intro_frame(U object,IntroFrame*f){
 if(*(U*)(object+0xb8)!=462)return 0;
 U c=*(U*)(object+0x44);if(c<0x10000)return 0;
 U size=*(U*)c,offset=*(unsigned short*)(c+6);
 if((f->oi==18?size!=542:size!=226)||offset<70||offset+36>size)return 0;
 U bank=c+offset,bytes=*(unsigned short*)bank;
 if(bytes!=size-offset||*(unsigned short*)(bank+2)!=16)return 0;
 if(f->anim!=0&&f->anim!=1&&f->anim!=7&&f->anim!=8)return 0;
 if(f->direction!=0&&f->direction!=16)return 0;
 U anim=*(unsigned short*)(bank+4+2*f->anim);
 if(anim<36||anim+64>bytes)return 0;
 U dir=*(unsigned short*)(bank+anim+2*f->direction);
 if(dir<64||anim+dir+8>bytes)return 0;
 U expected=f->oi==18?(f->anim==0?2:f->anim==1?8:f->anim==7?3:2):1;
 if(f->oi!=18&&(f->anim||f->direction))return 0;
 U n=*(unsigned short*)(bank+anim+dir+6);
 if(n!=expected||f->frame>=n||anim+dir+8+2*n>bytes)return 0;
 return *(unsigned short*)(bank+anim+dir+8+2*f->frame);
}
static void intro_cast(U run,U scene){
 IntroState[3]=scene;
 if(scene!=1){introRun=0;return;}if(introRun==run)return;
 U targets[3]={intro_object(run,18),intro_object(run,21),intro_object(run,23)};
 if(!targets[0]||!targets[1]||!targets[2])return;
 introRun=run;IntroState[0]=2;IntroState[1]=0;IntroState[2]=run;
 if(!receipt_init()||*(U*)0x42bec0!=0x5318ec83)return;
 static IntroPlan p;U got=0;
 H file=CreateFileA("..\\menu-runtime\\intro.bin",0x80000000,1,0,3,0,0);
 if(file==(H)-1){IntroState[0]=3;return;}
 I ok=ReadFile(file,&p,sizeof(p),&got,0);unsigned char extra;U more=0;
 ok=ok&&ReadFile(file,&extra,1,&more,0);CloseHandle(file);
 if(!ok||got!=sizeof(p)||more||p.magic!=0x31495242||p.count!=32)return;
 I(W*info)(U,U,U,U,U,H)=(void*)0x450de6;
 U seen[3]={0,0,0};
 /* Validate every frame and file before the first native mutation. */
 for(U i=0;i<32;i++){
  IntroFrame*f=&p.frames[i];U t=f->oi==18?0:f->oi==21?1:f->oi==23?2:3;if(t==3)return;
  U image=intro_frame(targets[t],f);if(!image||image>=32768)return;
  for(U j=0;j<i;j++)if(p.frames[j].oi==f->oi&&p.frames[j].anim==f->anim&&p.frames[j].direction==f->direction&&p.frames[j].frame==f->frame)return;
  unsigned char data[64]={0};if(!info(*(U*)(*(U*)(targets[t]+8)+8),image,0,0x3f800000,0x3f800000,data))return;
  if(f->width!=*(unsigned short*)(data+12)||f->height!=*(unsigned short*)(data+14)||f->hx!=*(short*)(data+20)||f->hy!=*(short*)(data+22))return;
  S prefix="..\\menu-runtime\\intro\\";U j=0;for(;prefix[j];j++)if(f->path[j]!=prefix[j])return;
  if(f->path[j]<'0'||f->path[j]>'9'||f->path[j+1]<'0'||f->path[j+1]>'9'||f->path[j+2]!='.'||f->path[j+3]!='p'||f->path[j+4]!='n'||f->path[j+5]!='g'||f->path[j+6])return;
  H png=CreateFileA(f->path,0x80000000,1,0,3,0,0);if(png==(H)-1)return;CloseHandle(png);seen[t]++;
 }
 if(seen[0]!=30||seen[1]!=1||seen[2]!=1)return;
 void(*load)(U,S,I,I,I,I,I,I,I,I)=(void*)0x42bec0;
 for(U i=0;i<32;i++){
  IntroFrame*f=&p.frames[i];U o=targets[f->oi==18?0:f->oi==21?1:2];U before=intro_frame(o,f);
  load(o,f->path,f->anim,f->direction,f->frame,f->hx,f->hy,0,0,-1);
  U after=intro_frame(o,f);if(!after||before==after)return;IntroState[1]++;
 }
 IntroState[0]=1;
}
