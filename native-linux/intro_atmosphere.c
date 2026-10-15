/* Preload a bounded set through MMF's own image importer. MMF records ownership
 * in its application image bitmap. No file I/O or allocation in the animation
 * loop; only the title background's image changes, as in Active action 89. */
U AtmosphereState[5]; /* status, loaded images, frame, swaps, run */
static U atmosphereRun,atmosphereTick;
static unsigned short atmosphereImages[24];
static void atmosphere_path(char*out,U index){
 S p="..\\menu-runtime\\theme\\e";U n=0;for(;p[n];n++)out[n]=p[n];out[n++]='0'+index/10;out[n++]='0'+index%10;out[n++]='.';out[n++]='p';out[n++]='n';out[n++]='g';out[n]=0;
}
static void intro_atmosphere(U run,U scene){
 if(scene!=1){atmosphereRun=0;AtmosphereState[0]=0;return;}
 if(ThemeState[0]!=1||ThemeState[2]!=run)return;
 U o=intro_object(run,30);if(!o)return;
 if(atmosphereRun!=run){
  atmosphereRun=run;AtmosphereState[0]=2;AtmosphereState[1]=0;AtmosphereState[2]=0;AtmosphereState[3]=0;AtmosphereState[4]=run;
  if(*(U*)0x42b8a0!=0x1468ff6a||*(unsigned short*)0x451926!=0x25ff||*(U*)(0x451926+2)!=0x45975c)return;
  U p[6],got=0,more=0;unsigned char extra;
  H f=CreateFileA("..\\menu-runtime\\theme\\effects.bin",0x80000000,1,0,3,0,0);if(f==(H)-1){AtmosphereState[0]=3;return;}
  I ok=ReadFile(f,p,sizeof(p),&got,0);ok=ok&&ReadFile(f,&extra,1,&more,0);CloseHandle(f);
  if(!ok||got!=sizeof(p)||more||p[0]!=0x31465242||p[1]!=24||p[2]!=ThemeState[4]||p[3]!=250||p[4]!=823||p[5]!=480)return;
  for(U i=0;i<24;i++){char path[96]={0};atmosphere_path(path,i);if(!theme_png(path,823,480))return;}
  I settings[6]={24,0,0,0,0,-1};
  U pointer=theme_handle(run,&(ThemeFrame){30,0,823,480,0,0,{0}});if(!pointer)return;
  unsigned char info[64]={0};I(W*getinfo)(U,U,U,U,U,H)=(void*)0x450de6;
  U bank=*(U*)(*(U*)0x459a94+0x1c4);
  if(!getinfo(bank,*(unsigned short*)pointer,0,0x3f800000,0x3f800000,info))return;
  settings[1]=*(short*)(info+20);settings[2]=*(short*)(info+22);
  I(*load)(U,S,I*)=(void*)0x42b8a0;
  for(U i=0;i<24;i++){
   atmosphereImages[i]=0;char path[96]={0};atmosphere_path(path,i);
   if(!load((U)&atmosphereImages[i],path,settings)||!atmosphereImages[i]){AtmosphereState[0]=4;return;}
   AtmosphereState[1]++;
  }
  atmosphereTick=GetTickCount();AtmosphereState[0]=1;
 }
 if(AtmosphereState[0]!=1||*(U*)(run+0x178))return;
 H window=*(H*)(run+0x10);if(GetForegroundWindow()!=window)return;
 U elapsed=GetTickCount()-atmosphereTick;if(elapsed<250)return;
 atmosphereTick+=elapsed/250*250;
 U index=(AtmosphereState[2]+elapsed/250)%24,image=atmosphereImages[index];
 U pointer=theme_handle(run,&(ThemeFrame){30,0,823,480,0,0,{0}});if(!pointer)return;
 *(unsigned short*)pointer=image;*(U*)(o+0xdc)=image;*(U*)(o+0x10c)=image;
 U sprite=*(U*)(o+0xd4);if(sprite){
  void(W*refresh)(U,U,I,I,U)=(void*)0x451926;
  refresh(*(U*)0x459a6c,sprite,*(I*)(o+0x4c)-*(I*)(run+0xb0),*(I*)(o+0x54)-*(I*)(run+0xb4),image);
 }
 AtmosphereState[2]=index;AtmosphereState[3]++;
}
