/* Scene-1 textures only. Exact object identities, dimensions and hotspots.
 * MMF owns import/reference counting; static tiles use the same importer as
 * Active action 89, followed by MMF's deferred background redraw. */
typedef struct {U oi,direction,width,height;I hx,hy;char path[96];} ThemeFrame;
typedef struct {U magic,count,theme;ThemeFrame frames[13];} ThemePlan;
_Static_assert(sizeof(ThemePlan)==1572,"Theme plan ABI");
U ThemeState[5]; /* applied/refused/missing/rollback, changed frames, run, scene, theme */
static U themeRun;
static const U themeOI[13]={30,38,38,38,38,22,24,32,33,34,35,36,37};
static const U themeDirection[13]={0,0,8,16,24,0,0,0,0,0,0,0,0};
static U theme_definition(U oi){
 U app=*(U*)0x459a94;if(app<0x10000||oi>=*(U*)(app+0x194))return 0;
 U map=*(U*)(app+0x198),table=*(U*)(app+0x19c);if(map<0x10000||table<0x10000)return 0;
 U index=*(unsigned short*)(map+oi*2);if(index>=*(U*)(app+0x194))return 0;
 U info=*(U*)(table+index*4);if(info<0x10000||*(unsigned short*)info!=oi)return 0;return info;
}
static U theme_handle(U run,ThemeFrame*f){
 U info=theme_definition(f->oi);if(!info)return 0;U c=*(U*)(info+20);if(c<0x10000)return 0;
 if(f->oi!=30&&f->oi!=38){
  if(*(unsigned short*)(info+2)!=1||*(U*)c!=18||*(U*)(c+4)!=0||*(U*)(c+8)!=f->width||*(U*)(c+12)!=f->height)return 0;
  return c+16;
 }
 U o=intro_object(run,f->oi);if(!o||*(U*)(o+0x44)!=c||*(U*)(o+0xb8)!=462)return 0;
 U size=*(U*)c,offset=*(unsigned short*)(c+6);if(size!=(f->oi==30?226:256)||offset!=116)return 0;
 U bank=c+offset,bytes=size-offset;
 if(*(unsigned short*)bank!=bytes||*(unsigned short*)(bank+2)!=16||*(unsigned short*)(bank+4)!=36)return 0;
 U dir=*(unsigned short*)(bank+36+2*f->direction);
 if(dir<64||36+dir+10>bytes||*(unsigned short*)(bank+36+dir+6)!=1)return 0;
 return bank+36+dir+8;
}
static I theme_png(S path,U width,U height){
 H file=CreateFileA(path,0x80000000,1,0,3,0,0);if(file==(H)-1)return 0;
 unsigned char h[24];U got=0;I ok=ReadFile(file,h,24,&got,0);CloseHandle(file);
 if(!ok||got!=24||*(U*)h!=0x474e5089||*(U*)(h+4)!=0x0a1a0a0d||*(U*)(h+12)!=0x52444849)return 0;
 U w=((U)h[16]<<24)|((U)h[17]<<16)|((U)h[18]<<8)|h[19];U v=((U)h[20]<<24)|((U)h[21]<<16)|((U)h[22]<<8)|h[23];return w==width&&v==height;
}
static void theme_path(char*out,U i,I original){
 S prefix="..\\menu-runtime\\theme\\";U n=0;for(;prefix[n];n++)out[n]=prefix[n];
 if(original)out[n++]='o';out[n++]='0'+i/10;out[n++]='0'+i%10;out[n++]='.';out[n++]='p';out[n++]='n';out[n++]='g';out[n]=0;
}
static I theme_load(U run,ThemeFrame*f,S path){
 U pointer=theme_handle(run,f);if(!pointer)return 0;U before=*(unsigned short*)pointer;
 if(f->oi==30||f->oi==38){
  void(*load)(U,S,I,I,I,I,I,I,I,I)=(void*)0x42bec0;
  load(intro_object(run,f->oi),path,0,f->direction,0,f->hx,f->hy,0,0,-1);
 }else{
  I settings[6]={24,f->hx,f->hy,0,0,-1};I(*load)(U,S,I*)=(void*)0x42b8a0;
  if(!load(pointer,path,settings))return 0;
  U definition=theme_definition(f->oi);*(U*)(definition+28)|=0x20;
 }
 pointer=theme_handle(run,f);return pointer&&*(unsigned short*)pointer&&*(unsigned short*)pointer!=before;
}
static void intro_theme(U run,U scene){
 ThemeState[3]=scene;if(scene!=1){themeRun=0;return;}if(themeRun==run)return;
 if(!intro_object(run,30)||!intro_object(run,38))return;
 themeRun=run;ThemeState[0]=2;ThemeState[1]=0;ThemeState[2]=run;
 if(!receipt_init()||*(U*)0x42bec0!=0x5318ec83||*(U*)0x42b8a0!=0x1468ff6a||*(U*)0x41ebf0!=0x459a9ca1)return;
 static ThemePlan p;U got=0,more=0;unsigned char extra;
 H file=CreateFileA("..\\menu-runtime\\theme.bin",0x80000000,1,0,3,0,0);if(file==(H)-1){ThemeState[0]=3;return;}
 I ok=ReadFile(file,&p,sizeof(p),&got,0);ok=ok&&ReadFile(file,&extra,1,&more,0);CloseHandle(file);
 if(!ok||got!=sizeof(p)||more||p.magic!=0x31545242||p.count!=13||p.theme>=4)return;
 ThemeState[4]=p.theme;
 I(W*getinfo)(U,U,U,U,U,H)=(void*)0x450de6;
 U app=*(U*)0x459a94,bank=*(U*)(app+0x1c4);
 for(U i=0;i<13;i++){
  ThemeFrame*f=&p.frames[i];if(f->oi!=themeOI[i]||f->direction!=themeDirection[i])return;
  if(f->width!=(i==0?823:i==5||i==6?32:16)||f->height!=(i==0?480:i==5||i==6?32:16))return;
  U pointer=theme_handle(run,f),image=pointer?*(unsigned short*)pointer:0;if(!image||image>=32768)return;
  unsigned char info[64]={0};if(!getinfo(bank,image,0,0x3f800000,0x3f800000,info))return;
  if(f->width!=*(unsigned short*)(info+12)||f->height!=*(unsigned short*)(info+14)||f->hx!=*(short*)(info+20)||f->hy!=*(short*)(info+22))return;
  char path[96]={0};theme_path(path,i,0);U j=0;for(;j<96&&path[j];j++)if(path[j]!=f->path[j])return;if(j==96||f->path[j])return;
  if(!theme_png(path,f->width,f->height))return;theme_path(path,i,1);if(!theme_png(path,f->width,f->height))return;
 }
 for(U i=0;i<13;i++){
  if(!theme_load(run,&p.frames[i],p.frames[i].path)){
   /* Restore every attempted replacement if the engine cannot import a file. */
   for(U j=0;j<=i;j++){char path[96]={0};theme_path(path,j,1);theme_load(run,&p.frames[j],path);}
   ThemeState[0]=4;*(unsigned char*)(run+0x1a7)|=2;return;
  }
  ThemeState[1]++;
 }
 *(unsigned char*)(run+0x1a7)|=2;ThemeState[0]=1;
}
