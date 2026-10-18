/* Rebind only native cached object indices in the injected reward context.
 * Called on the game thread, before the unchanged reward dispatcher validates
 * event signatures. IDs, opcodes, values, masks and seed assignments stay exact. */
#include "native_oi.h"
typedef struct {U off,len,conditions,actions;unsigned char old[512],replacement[512],mask[512];} RefPatch;
typedef struct {U off;I kind;U len;unsigned char action[256];} RefDisplay;
typedef struct {U scene,object,grantOff,grantLen,extraLen,awards,lastAction,patchCount,saveOI;char key[8];unsigned char grant[256],extra[192];RefPatch patches[4];U displayCount;RefDisplay displays[3];} RefLocation;
_Static_assert(sizeof(RefLocation)==7508,"Reward reference ABI");
U ReferenceState[6]; /* revision, successful batches, changed indices, error, scene, run */
static struct {unsigned short*at,value;} refChanges[4096];static U refCount;
static I ref_index(unsigned char*p,U oi){
 /* Qualifier indices have a separate native table; no added scenery qualifiers. */
 if(oi>=32768)return 1;I index=runtime_oi_index(oi);if(index<0||refCount>=4096)return 0;
 if(*(unsigned short*)p!=(U)index){refChanges[refCount].at=(unsigned short*)p;refChanges[refCount++].value=(unsigned short)index;}return 1;
}
static I ref_records(unsigned char*b,U len,U records){
 U at=0;if(len>512||records>64)return 0;
 for(U i=0;i<records;i++){
  if(at+14>len)return 0;unsigned char*r=b+at;U n=*(unsigned short*)r;I kind=*(short*)(r+2),code=*(short*)(r+4);U off=code<0?16:14;
  if(n<off||at+n>len)return 0;
  if(kind>=0&&!ref_index(r+8,*(unsigned short*)(r+6)))return 0;
  for(U j=0;j<r[12];j++){
   if(off+4>n)return 0;unsigned char*p=r+off;U size=*(unsigned short*)p,type=*(unsigned short*)(p+2);
   if(size<4||off+size>n)return 0;
   if(type==1){if(size<10||!ref_index(p+4,*(unsigned short*)(p+6)))return 0;}
   /* Parameter dispatch at 0x43443c: expressions start after a six-byte header. */
   if(type==15||type==22||type==23||type==27||type==28||type==45||type==46||type==52||type==53||type==54||type==59||type==62){
    U e=6;if(size<10)return 0;
    while(e+4<=size&&*(U*)(p+e)){
     if(e+6>size)return 0;U step=*(unsigned short*)(p+e+4);if(step<6||e+step>size)return 0;
     if(*(short*)(p+e)>0&&(step<10||!ref_index(p+e+8,*(unsigned short*)(p+e+6))))return 0;
     e+=step;
    }
    if(e+4>size)return 0;
   }
   off+=size;
  }
  /* Deliberate padding in replacement conditions is retained verbatim. */
  at+=n;
 }
 return at==len;
}
static void context_rebase(U run,U scene){
 static U lastRun,lastBank,lastScene=~0U,lastTick;static unsigned char session[32];
 if(!q||scene<=1)return;unsigned char*c=(unsigned char*)q-304284;
 if(*(U*)c!=0x42524832||*(U*)(c+4)!=7||!c[64])return;
 U bank=*(U*)(run+0x88),tick=*(U*)(run+0xd0),count=*(U*)(c+48);
 if(run==lastRun&&bank==lastBank&&scene==lastScene&&tick>=lastTick&&samebytes(c+64,session,32)){lastTick=tick;return;}
 if(!count||count>40||bank<65536)return;
 ReferenceState[0]=1;ReferenceState[3]=0;ReferenceState[4]=scene;ReferenceState[5]=run;refCount=0;
 RefLocation*locations=(RefLocation*)(c+124);
 for(U k=0;k<count;k++){
  RefLocation*l=&locations[k];if(l->scene!=scene)continue;
  if(l->patchCount<2||l->patchCount>4||l->displayCount>3||l->grantLen>256||l->extraLen>192)goto invalid;
  if(!ref_records(l->grant,l->grantLen,1)||!ref_records(l->extra,l->extraLen,1))goto invalid;
  for(U j=0;j<l->displayCount;j++)if(l->displays[j].len>256||!ref_records(l->displays[j].action,l->displays[j].len,1))goto invalid;
  for(U j=0;j<l->patchCount;j++){
   RefPatch*p=&l->patches[j];U old=p->conditions&255,newc=(p->conditions>>8)&255;if(!newc)newc=old;
   if(!ref_records(p->old,p->len,old+p->actions)||!ref_records(p->replacement,p->len,newc+p->actions))goto invalid;
  }
 }
 for(U i=0;i<refCount;i++)*refChanges[i].at=refChanges[i].value;
 ReferenceState[1]++;ReferenceState[2]+=refCount;lastRun=run;lastBank=bank;lastScene=scene;lastTick=tick;for(U i=0;i<32;i++)session[i]=c[64+i];return;
invalid:ReferenceState[3]=1;q->error=46;
}
