/* Whole cosmetic sets enter MMF's frame list before its own resource loader.
 * Native allocations, image references, movements and cleanup remain owned by
 * MMF. Existing gameplay instances/handles and collision geometry stay intact. */
typedef struct{U oi,type,size,offset,width,height;I hx,hy,ax,ay;U cloud;I speed;} BgObject;
typedef struct{U object;I x,y;} BgInstance;
typedef struct{U scene,count,width,coefficient,locked,start,countInstances;} BgSet;
#include "background_sets_catalogue.h"
#define BG_COUNT (sizeof(bgSets)/sizeof(*bgSets))
typedef struct{U magic;unsigned char session[32];U count,dim,source[9];} BgPlan;
_Static_assert(sizeof(BgPlan)==80,"Background plan ABI");
U BackgroundDetail[8];
U BackgroundMotion[8]; /* foreign cloud steps, foreign Parallaxer steps */
U BackgroundState[12]={1,0,0,0,0,0,0,0,0,0,0,0}; /* revision, active, scene, source scene, loads, added, error, imports, wraps, time ms, generation, handles */
static U bgScene=~0U,bgSource,bgFirstHandle,bgLastHandle,bgFrame,bgDim,bgReady;
static I bg_has(U set,U oi){for(U i=0;i<bgSets[set].countInstances;i++)if(bgObjects[bgInstances[bgSets[set].start+i].object].oi==oi)return 1;return 0;}
static I background_owns(U scene,U oi){if(!BackgroundState[1]||scene!=bgScene)return 0;for(U i=0;i<BG_COUNT;i++)if(bgSets[i].scene==scene)return bg_has(i,oi)||bg_has(bgSource,oi);return 0;}
static void bg_copy(U to,U from,U bytes){for(U i=0;i<bytes;i++)((unsigned char*)to)[i]=((unsigned char*)from)[i];}
static void bg_zero(U to,U bytes){for(U i=0;i<bytes;i++)((unsigned char*)to)[i]=0;}
static I bg_plan(BgPlan*p){
 if(!q||!(q->a&32768)||!receipt_init())return 0;
 U got=0,more=0;unsigned char extra;H f=CreateFileA("..\\menu-runtime\\background-sets.bin",0x80000000,1,0,3,0,0);
 if(f==(H)-1)return 0;I ok=ReadFile(f,p,sizeof(*p),&got,0);ok=ok&&ReadFile(f,&extra,1,&more,0);CloseHandle(f);
 if(!ok||got!=sizeof(*p)||more||p->magic!=0x31424742||p->count!=BG_COUNT||!samebytes(p->session,(const unsigned char*)q-304284+64,32)||p->dim>60||p->dim%20)return 0;
 for(U i=0;i<BG_COUNT;i++)if(p->source[i]>=BG_COUNT||(bgSets[i].locked&&bgSets[p->source[i]].coefficient!=bgSets[i].coefficient))return 0;
 return 1;
}
static void bg_instance(U at,U handle,const BgInstance*instance,I shift){
 const BgObject*o=&bgObjects[instance->object];bg_zero(at,36);*(unsigned short*)at=handle;*(unsigned short*)(at+2)=o->oi;*(I*)(at+4)=instance->x+shift;*(I*)(at+8)=instance->y;*(unsigned short*)(at+18)=o->type;
}
static void background_load(U frame){
 pack_death_clear();deathEpoch++;DeathScreenState[0]=DeathScreenState[1]=0;
 graphics_debug_load();
 U app=*(U*)0x459a94,scene=app?*(U*)(app+0x1ec):~0U;bgReady=0;bgScene=~0U;BackgroundState[1]=0;BackgroundState[2]=scene;BackgroundState[6]=0;
 U target=BG_COUNT;for(U i=0;i<BG_COUNT;i++)if(bgSets[i].scene==scene){target=i;break;}
 BgPlan p;
 if(!(GraphicsDebug[1]&1)&&target<BG_COUNT&&bg_plan(&p)){
  U count=*(U*)(frame+0x44),oldmap=*(U*)(frame+0x4c),old=*(U*)(frame+0x50),handles=*(U*)(frame+0x48),layers=*(U*)(frame+0x30),nl=*(U*)(frame+0x2c);
  const BgSet*s=&bgSets[p.source[target]];
  if(count!=bgSets[target].count||!handles||handles>16000||old<65536||oldmap<65536||layers<65536||nl<2||nl>16||*(U*)(layers+0x30)!=bgSets[target].coefficient){BackgroundState[6]=1;goto original;}
  /* Refuse unexpected layer membership and non-cosmetic source definitions. */
  for(U i=0;i<count;i++){U r=old+i*36;if(*(unsigned short*)(r+0x10)>=nl||*(unsigned short*)r>=handles){BackgroundState[6]=2;goto original;}}
  for(U i=0;i<s->countInstances;i++){const BgObject*o=&bgObjects[bgInstances[s->start+i].object];U d=theme_definition(o->oi);if(!d||*(unsigned short*)(d+2)!=o->type){BackgroundState[6]=3;goto original;}}
  /* Repeat still landscapes only when a wider destination needs more coverage.
   * Moving cloud strips keep their original native movement and wrap below. */
  I width=0;for(U i=0;i<s->countInstances;i++){const BgInstance*r=&bgInstances[s->start+i];const BgObject*o=&bgObjects[r->object];if(o->type==1&&r->x+(I)o->width>width)width=r->x+(I)o->width;}
  if(width<320||width>4096){BackgroundState[6]=4;goto original;}
  union{U u;float f;} cf={s->coefficient};U cover=640+(U)((float)bgSets[target].width*cf.f),repeats=(cover+width-1)/width;if(!repeats)repeats=1;if(repeats>16){BackgroundState[6]=4;goto original;}
  U added=0;for(U i=0;i<s->countInstances;i++){const BgObject*o=&bgObjects[bgInstances[s->start+i].object];added+=o->cloud||o->type==48?1:repeats;}
  if(added>96||handles+added>=16384){BackgroundState[6]=4;goto original;}
  I(*alloc)(U,U*)=(void*)0x420240;void(*release)(U*)=(void*)0x4202d0;U list=0,map=0;
  if(!alloc((count+added+1)*36,&list)||!alloc((handles+added+1)*2,&map)){if(list)release(&list);if(map)release(&map);BackgroundState[6]=5;goto original;}
  bg_zero(list,(count+added+1)*36);for(U i=0;i<handles+added+1;i++)*(unsigned short*)(map+2*i)=0xffff;
  U at=0,next=handles;
  for(U layer=0;layer<nl;layer++){
   U first=at,bgs=0;
   for(U pass=0;pass<2;pass++){
    if(layer==0)for(U i=0;i<s->countInstances;i++){
     const BgInstance*r=&bgInstances[s->start+i];const BgObject*o=&bgObjects[r->object];I backdrop=o->type==1;if(backdrop!=(pass==0))continue;
     U times=o->cloud||o->type==48?1:repeats;
     for(U repeat=0;repeat<times;repeat++){U to=list+36*at;bg_instance(to,next,r,(I)repeat*width);*(unsigned short*)(map+2*next)=at;next++;at++;if(backdrop)bgs++;}
    }
    /* Imported scenery belongs behind retained decoration and collision tiles. */
    for(U i=0;i<count;i++){U r=old+i*36;I backdrop=*(unsigned short*)(r+18)<2;if(*(unsigned short*)(r+16)!=layer||backdrop!=(pass==0))continue;
     U to=list+36*at;bg_copy(to,r,36);if(layer==0&&bg_has(target,*(unsigned short*)(r+2))){if(backdrop){*(I*)(to+4)=-32000;*(I*)(to+8)=-32000;}else *(unsigned short*)(to+12)=1;}
     *(unsigned short*)(map+2**(unsigned short*)to)=at;at++;if(backdrop)bgs++;
    }
   }
   U l=layers+layer*0x5c;*(U*)(l+0x38)=*(U*)(l+0x54)=bgs;*(U*)(l+0x3c)=*(U*)(l+0x58)=bgs?first:0;
  }
  *(U*)(layers+0x30)=*(U*)(layers+0x4c)=s->coefficient;
  *(U*)(frame+0x44)=count+added;*(U*)(frame+0x48)=handles+added;*(U*)(frame+0x50)=list;*(U*)(frame+0x4c)=map;
  /* Re-read cosmetic common data through the engine. Extension objects can
   * cache rebased image handles even without a user image import. */
  for(U i=0;i<s->countInstances;i++){U d=theme_definition(bgObjects[bgInstances[s->start+i].object].oi);if(*(U*)(d+20))*(U*)(d+28)|=0x20;}
  release(&old);release(&oldmap);bgScene=scene;bgSource=p.source[target];bgFrame=frame;bgFirstHandle=handles;bgLastHandle=handles+added;bgDim=p.dim;bgReady=1;
  BackgroundState[1]=1;BackgroundState[3]=s->scene;BackgroundState[4]++;BackgroundState[5]=added;BackgroundState[10]++;BackgroundState[11]=handles;
 }
original:;
 void(*load)(U)=(void*)0x427e70;load(frame);
}
static void bg_path(char*out,U i,I original){S p="..\\menu-runtime\\background-sets\\";U n=0;for(;p[n];n++)out[n]=p[n];if(original)out[n++]='o';out[n++]='0'+i/10;out[n++]='0'+i%10;out[n++]='.';out[n++]='p';out[n++]='n';out[n++]='g';out[n]=0;}
static I background_images(U arg){
 /* Parallaxer's cached source-image mapping can survive F2 after the original
  * World 3 has run. Give our instance a freshly imported, checksum-extracted
  * texture instead. 0xffff is MMF's absent source-image sentinel: the loader
  * skips its count, converts it to 0, and the importer owns the new reference.
  * Original instances outside this plan keep the original loader untouched. */
 death_before_images();
 I direct=0;U pd=0,pc=0;
 if(bgReady&&bg_has(bgSource,681)){
  pd=theme_definition(681);pc=pd?*(U*)(pd+20):0;
  if(pc>=65536&&*(U*)pc==174&&*(U*)(pc+46)==0x70616c78&&*(U*)(pc+152)==1&&*(unsigned short*)(pc+170)==2936){*(unsigned short*)(pc+170)=0xffff;direct=1;}
 }
 I(*loadOriginal)(U)=(void*)0x41b840;I result=loadOriginal(arg);death_after_images(result);
 if(result||!bgReady||bgFrame!=*(U*)0x459a98)return result;
 U start=GetTickCount(),seen[sizeof(bgObjects)/sizeof(*bgObjects)]={0},indices[25],pointers[25],definitions[25],n=0;const BgSet*s=&bgSets[bgSource];
 U bank=*(U*)(*(U*)0x459a94+0x1c4);I(W*getinfo)(U,U,U,U,U,H)=(void*)0x450de6;
 /* Validate the entire import batch before replacing any ordinary texture. */
 for(U i=0;i<s->countInstances;i++){
  U index=bgInstances[s->start+i].object;if(seen[index])continue;seen[index]=1;const BgObject*o=&bgObjects[index];
  if(!bgDim&&o->type!=48)continue;
  U d=theme_definition(o->oi),c=d?*(U*)(d+20):0;if(c<65536||*(U*)c!=o->size||o->offset+2>o->size){BackgroundState[6]=6;goto refused;}
  U pointer=c+o->offset,before=*(unsigned short*)pointer;unsigned char info[64]={0};
  if(o->type==48){if(!direct||before){BackgroundState[6]=7;goto refused;}}
  else if(!before||!getinfo(bank,before,0,0x3f800000,0x3f800000,info)||*(unsigned short*)(info+12)!=o->width||*(unsigned short*)(info+14)!=o->height||*(short*)(info+20)!=o->hx||*(short*)(info+22)!=o->hy||*(short*)(info+24)!=o->ax||*(short*)(info+26)!=o->ay){BackgroundDetail[0]=o->oi;BackgroundDetail[1]=before;BackgroundState[6]=7;goto refused;}
  char path[96];bg_path(path,index,0);if(!theme_png(path,o->width,o->height)){BackgroundState[6]=8;goto refused;}
  bg_path(path,index,1);if(!theme_png(path,o->width,o->height)){BackgroundState[6]=8;goto refused;}
  indices[n]=index;pointers[n]=pointer;definitions[n++]=d;
 }
 for(U i=0;i<n;i++){
  const BgObject*o=&bgObjects[indices[i]];U before=*(unsigned short*)pointers[i];char path[96];bg_path(path,indices[i],0);
  /* RGB colour-key import is required by Parallaxer's native scanline mask. */
  I settings[6]={24,o->hx,o->hy,o->ax,o->ay,o->oi==681?0:-1};I(*import)(U,S,I*)=(void*)0x42b8a0;*(U*)(definitions[i]+28)|=0x20;
  if(!import(pointers[i],path,settings)||!*(unsigned short*)pointers[i]||*(unsigned short*)pointers[i]==before){
   BackgroundState[6]=9;
   for(U j=0;j<=i;j++){const BgObject*r=&bgObjects[indices[j]];I original[6]={24,r->hx,r->hy,r->ax,r->ay,r->oi==681?0:-1};bg_path(path,indices[j],1);import(pointers[j],path,original);}
   goto refused;
  }
  BackgroundState[7]++;
 }
 BackgroundState[9]=GetTickCount()-start;return result;
refused:
 /* Do not instantiate an extension with a missing or ambiguous texture. */
 if(direct){U records=*(U*)(bgFrame+0x50),count=*(U*)(bgFrame+0x44);for(U i=0;i<count;i++){U r=records+i*36;if(*(unsigned short*)(r+2)==681)*(unsigned short*)(r+12)=1;}}
 BackgroundState[9]=GetTickCount()-start;return result;
}
static void background_init(void){
 static I done;if(done)return;done=1;
 const U addresses[3]={0x41c0bb,0x41c0f4,0x41b7f9};U protections[3],acquired=0;
 I(W*flush)(H,H,U)=(void*)symbol(library("kernel32.dll"),"FlushInstructionCache");
 if(!flush){BackgroundState[6]=10;return;}
 for(U i=0;i<3;i++){U a=addresses[i];if(*(unsigned char*)a!=0xe8||a+5+*(U*)(a+1)!=(i==2?0x41b840:0x427e70)){BackgroundState[6]=10;return;}}
 /* Acquire every page before changing a call. Restore in reverse order because
  * the two frame-loader calls share a page. A denied page leaves all calls intact. */
 for(;acquired<3;acquired++)if(!VirtualProtect((H)addresses[acquired],5,0x40,&protections[acquired]))break;
 if(acquired==3){for(U i=0;i<3;i++){U a=addresses[i];*(U*)(a+1)=(U)(i==2?(void*)background_images:(void*)background_load)-a-5;flush((H)-1,(H)a,5);}}
 else BackgroundState[6]=11;
 while(acquired){U ignored;acquired--;VirtualProtect((H)addresses[acquired],5,protections[acquired],&ignored);}
}

/* Reuse the engine's position action to wrap only our own moving cloud strips.
 * A bounded cache avoids scanning every game object on each frame. */
static void background_tick(U run,U scene){
 static U generation,clouds[96],slots[96],n,tick;static I speeds[96];
 BackgroundMotion[4]=*(U*)(run+0x178);BackgroundMotion[5]=scene==bgScene;BackgroundMotion[6]=bgFrame==*(U*)0x459a98;BackgroundMotion[7]=*(U*)(run+0xd0);
 if(!BackgroundState[1]||scene!=bgScene||bgFrame!=*(U*)0x459a98||*(U*)(run+0x178))return;
 U now=*(U*)(run+0xd0);if(now==tick)return;tick=now;
 U table=*(U*)(run+0x1278),count=*(U*)(run+0x40);if(table<65536||count>20000)return;
 if(generation!=BackgroundState[10]){
  n=0;
  for(U i=0;i<count&&n<96;i++){
   U o=*(U*)(table+i*8);if(o<65536)continue;U handle=*(unsigned short*)(o+0x10);
   if(handle<bgFirstHandle||handle>=bgLastHandle)continue;
   if(*(unsigned short*)(o+0x18)==48&&*(unsigned short*)(o+18)==681){clouds[n]=o;speeds[n]=0;slots[n++]=i;continue;}
   if(*(unsigned short*)(o+0x18)!=2)continue;
   for(U j=0;j<sizeof(bgObjects)/sizeof(*bgObjects);j++)if(bgObjects[j].cloud&&bgObjects[j].oi==*(unsigned short*)(o+18)){clouds[n]=o;speeds[n]=bgObjects[j].speed;slots[n++]=i;break;}
  }
 }
 if(generation!=BackgroundState[10]){BackgroundMotion[2]=n;BackgroundMotion[3]++;U expected=0;for(U j=0;j<bgSets[bgSource].countInstances;j++){const BgObject*o=&bgObjects[bgInstances[bgSets[bgSource].start+j].object];if(o->cloud||o->type==48)expected++;}if(n==expected)generation=BackgroundState[10];}
 I offset=*(I*)(run+0xb0);
 for(U i=0;i<n;i++){
  U o=clouds[i];if(slots[i]>=count||*(U*)(table+slots[i]*8)!=o||*(unsigned short*)(o+0x7c)&1){generation=~0U;continue;}
  if(*(unsigned short*)(o+0x18)==48){
   /* World 3's Always event calls Parallaxer action 0 with Offset + 1.
    * Its action stores the negated offset and marks the native renderer dirty.
    * Reproduce that cosmetic update only where the source event is absent. */
   U c=*(U*)(o+0x44);
   if(scene!=7&&c>=65536&&*(U*)c==174&&*(U*)(c+46)==0x70616c78&&*(U*)(o+0xbc)==0x1ce){*(U*)(o+0x214)-=1;*(U*)(o+0xfc)=1;BackgroundMotion[1]++;}
   continue;
  }
  I x=*(I*)(o+0x4c)-offset,w=*(I*)(o+0x60);if(w<1||w>4096)continue;
  /* In its own scene the original events animate these cloud objects.
   * Foreign scenes lack those events: apply the original alterable-C speed
   * once per game tick, preserving MMF's own layer/camera positioning. */
  I dest=x+(bgSets[bgSource].scene==scene?0:speeds[i]);if(bgSets[bgSource].scene!=scene)BackgroundMotion[0]++;
  if(dest< -w){dest=640;BackgroundState[8]++;}else if(dest>640+w){dest=-w;BackgroundState[8]++;}
  if(dest!=x&&*(U*)0x411820==0x24748b56){void(*position)(U,I,I)=(void*)0x411820;position(o,dest+offset,*(I*)(o+0x54));}
 }
}
