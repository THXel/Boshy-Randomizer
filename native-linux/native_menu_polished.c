/* Owned native dialogs in the Boshy process, aligned with its client window. */
typedef unsigned int U;typedef int I;typedef void* H;typedef const char* S;
#define W __attribute__((stdcall))
typedef struct{I l,t,r,b;} Rect;
typedef struct{H dc;I erase;Rect r;I restore,update;char reserve[32];} Paint;
typedef struct{U style;I(W*proc)(H,U,U,I);I clsExtra,winExtra;H instance,icon,cursor,brush;S menu,name;} Class;
typedef struct{volatile U magic,version,status,window,shown,write,ack,type,a,b,generation,rendered,error,scene,run,enabled;char path[260];U events[64][4];} Shared;
static Shared*q;static H child,parent,bitmap,instance,updatesChild,updatesBitmap;static U lastRun,savedPause,menuLayer=99,menuSlot=1,keysBefore,logoRun,rootLast;
static H(W*library)(S);static H(W*symbol)(H,S);
#define API(ret,name,args) static ret(W*name)args
API(U,RegisterClassA,(Class*));API(H,CreateWindowExA,(U,S,S,U,I,I,I,I,H,H,H,H));
API(I,DefWindowProcA,(H,U,U,I));API(I,GetClientRect,(H,Rect*));API(I,ShowWindow,(H,I));API(H,SetFocus,(H));API(I,MoveWindow,(H,I,I,I,I,I));
API(H,BeginPaint,(H,Paint*));API(I,EndPaint,(H,Paint*));API(I,InvalidateRect,(H,Rect*,I));API(H,LoadImageA,(H,S,U,I,I,U));API(I,FillRect,(H,Rect*,H));
API(H,CreateCompatibleDC,(H));API(H,SelectObject,(H,H));API(I,DeleteObject,(H));API(I,DeleteDC,(H));API(I,StretchBlt,(H,I,I,I,I,H,I,I,I,I,U));API(H,GetStockObject,(I));API(I,IsWindow,(H));
API(I,VirtualProtect,(H,U,U,U*));
API(H,CreateRectRgn,(I,I,I,I));API(I,SetWindowRgn,(H,H,I));API(H,GetForegroundWindow,(void));API(I,SetForegroundWindow,(H));API(I,GetWindowLongA,(H,I));API(I,SetWindowLongA,(H,I,I));API(I,SetStretchBltMode,(H,I));API(I,SetLayeredWindowAttributes,(H,U,unsigned char,U));API(I,ClientToScreen,(H,void*));
static unsigned char modalHeld[256];
static I menuKey(I key){return key==13||key==27||key==46||key==9||(key>=37&&key<=40);}
static short(W*oldAsync)(I);static short(W*oldKey)(I);static I(W*oldKeyboard)(unsigned char*);
static I blocked(I key){return q&&((key>=0&&key<256&&modalHeld[key])||((q->scene==1||q->enabled==4)&&q->enabled>=2&&menuKey(key))||((q->a&1)&&key==0x72)||((q->a&2)&&q->enabled&&q->scene>1&&key==9)||(q->enabled&&q->scene==1&&menuLayer==0&&(key==13||key==46||key==84||key==38||key==40||key==9)));}
static short W lockedAsync(I key){return blocked(key)?0:oldAsync(key);}
static short W lockedKey(I key){return blocked(key)?0:oldKey(key);}
static I W lockedKeyboard(unsigned char*keys){I ok=oldKeyboard(keys);if(ok){for(I k=0;k<256;k++)if(blocked(k))keys[k]=0;}return ok;}
static I hook(U address,H replacement){U old;if(!VirtualProtect((H)address,4,4,&old))return 0;*(H*)address=replacement;U ignored;return VirtualProtect((H)address,4,old,&ignored);}
static void event(U type,U a,U b){if(!q)return;U n=q->write;if(n-q->ack>=64){q->error=4;return;}q->events[n%64][0]=type;q->events[n%64][1]=a;q->events[n%64][2]=b;q->events[n%64][3]=0;__asm__ volatile("":::"memory");q->write=n+1;}
static I W proc(H w,U msg,U a,I b){
 if(msg==0x14)return 1;
 if(msg==0xf){Paint p;H dc=BeginPaint(w,&p);Rect r;GetClientRect(w,&r);FillRect(dc,&r,GetStockObject(4));H paintBitmap=w==updatesChild?updatesBitmap:bitmap;if(paintBitmap){H mem=CreateCompatibleDC(dc),old=SelectObject(mem,paintBitmap);SetStretchBltMode(dc,3);StretchBlt(dc,0,0,r.r,r.b,mem,0,0,880,660,0xcc0020);SelectObject(mem,old);DeleteDC(mem);}EndPaint(w,&p);return 0;}
 if(msg==0x100){if((oldKey(17)&0x8000)&&(a==65||a==86||a==67)){if(!(b&(1<<30)))event(1,a==65?4097:(a==86?4098:4099),0);return 0;}if(!(b&(1<<30))&&(a==8||a==9||a==13||a==27||a==46||(a>=37&&a<=40)))event(1,a,0);return 0;}
 if(msg==0x101||msg==0x104||msg==0x105)return 0;
 if(msg==0x102){if(a>=32&&a<=126)event(2,a,0);return 0;}
 if(msg==0x202){Rect r;GetClientRect(w,&r);if(r.r&&r.b)event(3,((U)b&65535)*880/r.r,((U)b>>16)*660/r.b);if(q&&q->enabled==1)SetForegroundWindow(parent);SetFocus(q&&q->enabled==1?parent:w);return 0;}
 if(msg==0x20)return 1;
 return DefWindowProcA(w,msg,a,b);
}
#define GET(mod,name) name=(void*)symbol(mod,#name);if(!name)return 0
#include "reward_receipt.c"

/* Original MMF String object: use its own allocator, layout and redraw path.
 * Addresses and structure are tied to the launcher's verified game checksum. */
static I update_text(U object){
 static char text[2048];static U generation;
 if(*(U*)0x40e790!=0x748b5655||*(U*)0x415180!=0x04244c8b||*(U*)0x40e380!=0x245c8b53||*(U*)0x40e3f0!=0x08244c8b||*(U*)0x41e210!=0x24748b56)return 0;
 if(generation!=q->generation){
  if(!receipt_init())return 0;
  H file=CreateFileA("..\\menu-runtime\\updates.txt",0x80000000,7,0,3,0,0);
  if(file==(H)-1)return 0;
  U count=0;I ok=ReadFile(file,text,sizeof(text)-1,&count,0);CloseHandle(file);
  if(!ok||!count||count>=sizeof(text)-1)return 0;text[count]=0;generation=q->generation;
 }
 U old=*(U*)(object+0x22e);I equal=old>=0x10000;
 if(equal)for(U j=0;j<sizeof(text);j++){if(*(char*)(old+j)!=text[j]){equal=0;break;}if(!text[j])break;}
 if(!equal){
  void(*set)(U,S)=(void*)0x40e380;void(*layout)(U,I)=(void*)0x40e3f0;void(*redraw)(U)=(void*)0x41e210;
  set(object,text);layout(object,-1);*(U*)(object+0xfc)=1;redraw(object);
 }
 return 1;
}
/* Remove only the original Online menu object through MMF's deferred
 * destruction queue. Game/Options and save-slot objects are independent. */
static I remove_online_sprite(U run,U object){
 if(*(U*)0x41f730!=0x04244c8b||*(U*)0x411ecb!=0x7c468b66)return 0;
 I handle=*(short*)object;U table=*(U*)(run+0x1278),count=*(U*)(run+0x40);
 if(handle<0||(U)handle>=count||*(U*)(table+(U)handle*8)!=object)return 0;
 if(!(*(unsigned short*)(object+0x7c)&1)){
  *(unsigned short*)(object+0x7c)|=1;
  *(U*)(table+(U)handle*8+4)=0;
  void(*destroy)(I)=(void*)0x41f730;destroy(handle);
 }
 return 1;
}
static I init(void){
 library=*(void**)0x45314c;symbol=*(void**)0x453128;H user=library("user32.dll"),gdi=library("gdi32.dll");if(!user||!gdi)return 0;
 GET(user,RegisterClassA);GET(user,CreateWindowExA);GET(user,DefWindowProcA);GET(user,GetClientRect);GET(user,ShowWindow);GET(user,SetFocus);GET(user,MoveWindow);GET(user,BeginPaint);GET(user,EndPaint);GET(user,InvalidateRect);GET(user,LoadImageA);GET(user,FillRect);GET(user,IsWindow);GET(user,SetWindowRgn);GET(user,GetForegroundWindow);GET(user,SetForegroundWindow);GET(user,GetWindowLongA);GET(user,SetWindowLongA);GET(user,SetLayeredWindowAttributes);GET(user,ClientToScreen);
 GET(gdi,CreateCompatibleDC);GET(gdi,SelectObject);GET(gdi,DeleteObject);GET(gdi,DeleteDC);GET(gdi,StretchBlt);GET(gdi,GetStockObject);GET(gdi,CreateRectRgn);GET(gdi,SetStretchBltMode);
 H kernel=library("kernel32.dll");GET(kernel,VirtualProtect);
 oldAsync=*(H*)0x453384;oldKey=*(H*)0x453398;oldKeyboard=*(H*)0x453410;
 if(!hook(0x453384,lockedAsync)||!hook(0x453398,lockedKey)||!hook(0x453410,lockedKeyboard))return 0;
 Class c={0};c.proc=proc;c.instance=instance;c.name="BoshyNativeRandomizerMenu";return RegisterClassA(&c)!=0;
}
void MenuTick(Shared*s,U run,U scene){
 if(s->magic!=0x424d4e31||s->version!=1)return;q=s;q->scene=scene;q->run=run;
 if(!q->status){if(!init()){q->error=1;q->status=3;return;}q->status=1;}
 if(q->status==3||run<0x10000)return;
 H h=*(H*)(run+0x10);if(!IsWindow(h))return;
 if(!child||!IsWindow(child)||h!=parent){parent=h;SetWindowLongA(parent,-16,GetWindowLongA(parent,-16)|0x02000000);Rect r;GetClientRect(h,&r);child=CreateWindowExA(0x80080,"BoshyNativeRandomizerMenu","",0x80000000,0,0,r.r,r.b,h,0,instance,0);if(!child){q->error=2;return;}SetLayeredWindowAttributes(child,0x00ff00ff,240,3);q->window=(U)child;
 updatesChild=CreateWindowExA(0x80080,"BoshyNativeRandomizerMenu","",0x80000000,0,0,r.r,r.b,h,0,instance,0);
 if(!updatesChild){q->error=2;return;}SetLayeredWindowAttributes(updatesChild,0,255,2);
 }
 /* Prefer the original message-of-the-day String; fallback only after intro. */
 /* Keep a dialog-closing key consumed until release after unpausing. */
 for(I k=0;k<256;k++)if(menuKey(k)){I down=(oldAsync(k)&0x8000)!=0;if(q->enabled>=2&&(scene==1||q->enabled==4)&&down)modalHeld[k]=1;else if(!down)modalHeld[k]=0;}
 H foreground=GetForegroundWindow();I focused=foreground==parent||foreground==child||foreground==updatesChild;
 I nativeUpdates=0;
 U previousLayer=menuLayer;menuLayer=99;
 if(scene==1){
  U table=*(U*)(run+0x1278),n=*(U*)(run+0x40);
  if(table>=0x10000&&n>0&&n<=20000)for(U i=0;i<n;i++){
   U o=*(U*)(table+i*8);if(o<0x10000)continue;
   if(*(unsigned short*)(o+0x18)==3&&*(unsigned short*)(o+0x12)==85&&q->enabled)nativeUpdates=update_text(o);
   if(*(unsigned short*)(o+0x18)!=2)continue;
   U oi=*(unsigned short*)(o+0x12);
   if(oi==70){if(!remove_online_sprite(run,o)){q->error=34;return;}continue;}
   if(oi==46){U off=*(U*)(o+0x80);if(off>0&&off<1024){U v=*(U*)(o+off);if(v>=0x10000){menuLayer=*(U*)(v+24);U slot=*(U*)(v+8);if(menuLayer==0xffffffff){if(slot==2){slot=rootLast==1?0:1;*(U*)(v+8)=slot;}if(slot<2)rootLast=slot;}if(menuLayer==0&&slot<3&&(menuSlot!=slot+1||previousLayer!=0)){menuSlot=slot+1;event(4,menuSlot,0);}}}}
   if(oi==41&&logoRun!=run&&*(U*)0x42bec0==0x5318ec83){
    void(*load)(U,S,I,I,I,I,I,I,I,I)=(void*)0x42bec0;
    unsigned char info[64]={0};U dir=*(U*)(o+0x1ee);U before=dir>=0x10000?*(unsigned short*)(dir+8):0;
    I(W*getinfo)(U,U,U,U,U,H)=(void*)0x450de6;
    if(before&&getinfo(*(U*)(*(U*)(o+8)+8),before,0,0x3f800000,0x3f800000,info)){event(6,*(unsigned short*)(info+12),*(unsigned short*)(info+14));}
    load(o,"..\\menu-runtime\\logo.png",0,0,0,151,60,0,0,-1);logoRun=run;
   }
  }
 }
 static U updatesShown,updatesRun,introSeen;
 if(scene!=1||updatesRun!=run){introSeen=0;updatesRun=scene==1?run:0;}
 if(scene==1&&menuLayer==0xfffffffe)introSeen=1;
 if(scene==1&&(introSeen||menuLayer==0)&&menuLayer!=99&&menuLayer!=0xfffffffe&&q->enabled&&focused&&!nativeUpdates){
  Rect u;I xy[2]={0,0};GetClientRect(parent,&u);ClientToScreen(parent,xy);MoveWindow(updatesChild,xy[0],xy[1],u.r,u.b,0);
  SetWindowRgn(updatesChild,CreateRectRgn(0,u.b*266/660,u.r*285/880,u.b),1);
  if(!updatesShown){ShowWindow(updatesChild,4);updatesShown=1;}
 }else if(updatesShown){ShowWindow(updatesChild,0);updatesShown=0;}
 q->type=menuLayer;q->b=menuSlot;
 U down=0;{if(oldAsync(13)&0x8000)down|=1;if(oldAsync(46)&0x8000)down|=2;if(oldAsync(84)&0x8000)down|=4;if(oldAsync(9)&0x8000)down|=8;if(oldAsync(38)&0x8000)down|=16;if(oldAsync(40)&0x8000)down|=32;}
 U pressed=down&~keysBefore;keysBefore=down;
 if(GetForegroundWindow()==parent&&scene==1&&q->enabled==1&&menuLayer==0){if(pressed&1)event(4,menuSlot,1);else if(pressed&2)event(4,menuSlot,2);else if(pressed&4)event(4,menuSlot,3);else if(pressed&16)event(1,38,0);else if(pressed&32)event(1,40,0);else if(pressed&8)event(1,9,0);}
 if(GetForegroundWindow()==parent&&scene>1&&(q->a&2)&&q->enabled==1&&(pressed&8)){event(7,0,0);}
 I modal=q->enabled>=2,show=focused&&((scene==1&&q->enabled&&(modal||menuLayer==0))||(scene>1&&(((q->a&2)&&q->enabled==3)||q->enabled==4)));
 static U shownMode;
 if(show){
  if(modal){if(lastRun!=run){lastRun=run;savedPause=*(U*)(run+0x178);}*(U*)(run+0x178)=1;}
  else if(lastRun==run){*(U*)(run+0x178)=savedPause;lastRun=0;}
  Rect r;GetClientRect(parent,&r);I origin[2]={0,0};ClientToScreen(parent,origin);MoveWindow(child,origin[0],origin[1],r.r,r.b,0);
  if(!q->shown||shownMode!=q->enabled){
   H region=modal?CreateRectRgn(r.r*235/880,r.b*252/660,r.r*873/880,r.b*655/660):CreateRectRgn(r.r*318/880,r.b*264/660,r.r*876/880,r.b);
   SetLayeredWindowAttributes(child,0x00ff00ff,modal?255:246,3);
   SetWindowRgn(child,region,1);ShowWindow(child,modal?5:4);if(!modal&&shownMode>=2)SetForegroundWindow(parent);SetFocus(modal?child:parent);q->shown=1;shownMode=q->enabled;
  }
  if(q->generation!=q->rendered){H next=LoadImageA(0,q->path,0,0,0,0x2010);if(next){H old=bitmap;bitmap=next;if(old)DeleteObject(old);q->rendered=q->generation;H news=LoadImageA(0,"..\\menu-runtime\\updates.bmp",0,0,0,0x2010);if(news){if(updatesBitmap)DeleteObject(updatesBitmap);updatesBitmap=news;}InvalidateRect(child,0,0);InvalidateRect(updatesChild,0,0);}else q->error=3;}
 }else if(q->shown){ShowWindow(child,0);q->shown=0;if(lastRun==run)*(U*)(run+0x178)=savedPause;lastRun=0;if(focused)SetFocus(parent);}
 if(scene==1&&q->enabled&&q->generation!=q->rendered){H next=LoadImageA(0,q->path,0,0,0,0x2010);if(next){H old=bitmap;bitmap=next;if(old)DeleteObject(old);q->rendered=q->generation;H news=LoadImageA(0,"..\\menu-runtime\\updates.bmp",0,0,0,0x2010);if(news){if(updatesBitmap)DeleteObject(updatesBitmap);updatesBitmap=news;}InvalidateRect(updatesChild,0,0);}else q->error=3;}
 q->status=2;
}
I W DllMain(H h,U reason,H unused){(void)unused;if(reason==1)instance=h;return 1;}
