/* Native mixed chest rewards. Original chest touch, boss gating and timing remain.
 * All event signatures in a scene validate before any mutation; native setters
 * grant only the bound run's reward, then persist a separate source check.
 */
typedef unsigned int u32;typedef unsigned char u8;typedef unsigned short u16;
#define MAX_SOURCES 40
struct Patch{u32 off,len,conditions,actions;u8 old[512],newv[512],mask[512];};
struct Display{u32 off;int kind;u32 len;u8 action[256];};
struct Location{u32 scene,object,grant_off,grant_len,extra_len,awards,last_action,patch_count,save_oi;char key[8];u8 grant[256],extra[192];struct Patch p[4];u32 display_count;struct Display display[3];};
struct Icon{u32 common,image,loads,status;int hx,hy;u32 width,height;char path[64];};
struct Context{u32 magic,version,status,patch_count,ticks,scene,bank,active,original33,entry,awards,errors,count,r0,r1,r2;char session[36],group[12],session_key[12];struct Location loc[MAX_SOURCES];struct Icon icon[MAX_SOURCES];};
_Static_assert(sizeof(struct Location)==7508,"Location layout");
static u32 rd(u32 a){return *(volatile u32*)a;}
static int eq(volatile u8*a,const u8*b,const u8*m,u32 n){for(u32 i=0;i<n;i++)if((a[i]&m[i])!=(b[i]&m[i]))return 0;return 1;}
static u32 find_object(u32 run,u32 oi,u32 type){
 u32 table=rd(run+0x1278);if(table<0x10000||rd(run+0x40)!=20000)return 0;
 for(u32 i=0;i<20000;i++){u32 o=rd(table+i*8);if(o>=0x10000&&*(u16*)(o+0x12)==oi&&*(u16*)(o+0x18)==type)return o;}return 0;
}
static u32 tree_find(u32 head,const char*key){
 if(head<0x10000)return 0;u32 node=rd(head+4);
 for(u32 step=0;step<128&&node>=0x10000&&node!=head;step++){
  u32 len=rd(node+20),ptr=rd(node+16);if(len>127||ptr<0x10000||len>rd(node+24))return 0;
  int cmp=0;for(u32 j=0;j<=len;j++){u8 a=key[j],b=j<len?*(u8*)(ptr+j):0;if(a!=b){cmp=(int)a-(int)b;break;}if(!a)break;}
  if(!cmp)return node;node=rd(node+(cmp<0?0:8));
 }return 0;
}
static u32 item_node(struct Context*c,u32 run,struct Location*l,const char*key){
 u32 o=find_object(run,l->save_oi,33);if(!o)return 0;u32 state=rd(o+0x168);if(state<0x10000)return 0;
 u32 group=tree_find(rd(state+0x14),c->group);return group?tree_find(rd(group+32),key):0;
}
static int same_session(struct Context*c,u32 run,struct Location*l){
 if(!c->session[0])return 0;u32 n=item_node(c,run,l,c->session_key);if(!n||rd(n+52)!=32||rd(n+56)<32)return 0;
 u32 ptr=rd(n+48);if(ptr<0x10000)return 0;for(u32 j=0;j<32;j++)if(*(u8*)(ptr+j)!=(u8)c->session[j])return 0;return 1;
}
static int consumed(struct Context*c,u32 run,struct Location*l){u32 n=item_node(c,run,l,l->key);return n&&rd(n+52)==1&&rd(n+48)>=0x10000&&*(u8*)rd(n+48)=='1';}
/* Verified built-in Active-object action 89: load a single animation frame.
 * Let the engine own resource handles, alpha, reference counts and rendering.
 */
#ifndef NATIVE_IMAGE_INFO
#define NATIVE_IMAGE_INFO 0x450de6
#endif
#ifndef NATIVE_FRAME_LOADER
#define NATIVE_FRAME_LOADER 0x42bec0
#endif
static void icon(struct Context*c,u32 which,u32 run){
 struct Icon*i=&c->icon[which];struct Location*l=&c->loc[which];
 u32 table=rd(run+0x1278);if(table<0x10000)return;
 for(u32 n=0;n<20000;n++){
  u32 o=rd(table+n*8);if(o<0x10000||*(u16*)(o+0x12)!=l->object||*(u16*)(o+0x18)!=2)continue;
  if(rd(o+0xb8)!=462){i->status=3;return;}
  u32 common=rd(o+0x44),dir=rd(o+0x1ee);if(common<0x10000||dir<0x10000)return;
  /* Frame handles are allocated by the runtime and change after scene loads.
   * Validate the known three-frame chest layout, not one run's image IDs.
   * The object identity and event signatures were verified by tick(). */
  u32 closed=*(u16*)(dir+8),opened=*(u16*)(dir+10);
  if(*(u16*)(dir+6)!=3||!closed||closed>=32768||!opened||opened>=32768||closed==opened){i->status=3;return;}
  u32 before=*(u16*)(dir+12);
  if(i->common==common&&i->image==before&&i->status==2)return;
  if(rd(0x42bec0)!=0x5318ec83||!before||before>=32768){i->status=3;return;}
  if(i->status==4&&i->common==common)return;
  i->common=common;i->status=1;
  void(*load)(u32,const char*,int,int,int,int,int,int,int,int)=(void*)NATIVE_FRAME_LOADER;
  u8 info[64];for(u32 z=0;z<64;z++)info[z]=0;
  int(__attribute__((stdcall))*getinfo)(u32,u32,u32,u32,u32,void*)=(void*)NATIVE_IMAGE_INFO;
  if(!getinfo(rd(rd(o+8)+8),before,0,0x3f800000,0x3f800000,info)){i->status=4;c->r2++;return;}
  i->width=*(u16*)(info+12);i->height=*(u16*)(info+14);i->hx=*(short*)(info+20);i->hy=*(short*)(info+22);
  if(!i->width||!i->height||i->width>128||i->height>128){i->status=4;c->r2++;return;}
  load(o,i->path,0,0,2,16+i->hx-(int)i->width/2,32+i->hy-(int)i->height,0,0,-1);
  dir=rd(o+0x1ee);u32 after=*(u16*)(dir+12);
  if(after==before||!after){i->status=4;c->r2++;return;}
  i->image=after;i->loads++;i->status=2;c->r0++;c->r1=after;
  return;
 }
}
static u32 table(u32 i){if(i==0)return 0x457058;if(i==1)return 0x4570dc;if(i==2)return 0x4570e0;return 0x4570f0;}
static u32 original_addr(int kind){return kind==-1?0x415140:0x415330;}
static void call_action(u32 run,u8*action);
struct CharCommand{u32 request,done,scene,save_oi,status,len1,len2;u8 first[224],second[224],pad[36];};
struct Menu{u32 header[16];char frame[260];u32 events[64][4];u32 module,fn;char dll[260],symbol[32];struct CharCommand command;};
static void menu_tick(struct Context*c){
 struct Menu*m=(void*)(c+1);if(m->header[0]!=0x424d4e31)return;
 u32 app=rd(0x459a94),run=rd(0x459a9c);if(app<0x10000||run<0x10000)return;
 if(!m->module){u32(__attribute__((stdcall))*load)(const char*)=(void*)rd(0x45314c);m->module=load(m->dll);if(!m->module){m->header[12]=10;return;}}
 if(!m->fn){u32(__attribute__((stdcall))*get)(u32,const char*)=(void*)rd(0x453128);m->fn=get(m->module,m->symbol);if(!m->fn){m->header[12]=11;return;}}
 void(*f)(void*,u32,u32)=(void*)m->fn;f(m,run,rd(app+0x1ec));
 struct CharCommand*q=&m->command;
 if(q->request!=q->done){
  struct Location l={0};l.save_oi=q->save_oi;q->status=2;
  if(q->scene==rd(app+0x1ec)&&same_session(c,run,&l)&&q->len1>=14&&q->len1<=224&&q->len2>=14&&q->len2<=224&&*(u16*)q->first==q->len1&&*(u16*)q->second==q->len2&&*(u16*)(q->first+2)==33&&*(u16*)(q->second+2)==33&&*(u16*)(q->first+4)==95&&*(u16*)(q->second+4)==95){call_action(run,q->first);call_action(run,q->second);q->status=1;}
  q->done=q->request;
 }
}
void tick(struct Context*c,u32 entry){
 menu_tick(c);if(!c->session[0]){c->status=0;return;}
 if(c->magic!=0x42524832||c->version!=7)return;c->ticks++;c->active=0;
 if(!c->count||c->count>MAX_SOURCES){c->status=4;return;}
 for(u32 j=0;j<4;j++){u32 d=rd(table(j));if(d!=original_addr(j==0?-1:33)&&d!=entry){c->status=6;return;}}
 for(u32 j=0;j<4;j++)*(volatile u32*)table(j)=entry;c->original33=0x415330;c->entry=entry;
 u32 app=rd(0x459a94),run=rd(0x459a9c);if(app<0x10000||run<0x10000){c->status=0;return;}
 c->scene=rd(app+0x1ec);c->bank=rd(run+0x88);int state[MAX_SOURCES][4];u32 count=0;
 for(u32 k=0;k<c->count;k++){
  struct Location*l=&c->loc[k];if(l->scene!=c->scene)continue;count++;
  if(c->bank<0x10000||rd(run+0x40)!=20000){c->status=3;return;}
  if(l->patch_count<2||l->patch_count>4||l->extra_len<14||l->extra_len>192||*(u16*)l->extra!=l->extra_len||l->grant_len<14||l->grant_len>256||*(u16*)l->grant!=l->grant_len||l->display_count>3){c->status=4;return;}
  for(u32 j=0;j<l->display_count;j++)if(l->display[j].len<14||l->display[j].len>256||*(u16*)l->display[j].action!=l->display[j].len){c->status=4;return;}
  for(u32 i=0;i<l->patch_count;i++){
   struct Patch*p=&l->p[i];if(p->off>1000000||p->len<14||p->len>512){c->status=4;return;}
   volatile u8*a=(volatile u8*)(c->bank+p->off);u32 oldc=p->conditions&255,newc=(p->conditions>>8)&255;if(!newc)newc=oldc;
   if(-(short)(*(volatile u16*)a)!=(int)(p->len+14)||(a[2]!=oldc&&a[2]!=newc)||a[3]!=p->actions){c->status=4;return;}
   if(a[2]==newc&&eq(a+14,p->newv,p->mask,p->len))state[k][i]=1;
   else if(a[2]==oldc&&eq(a+14,p->old,p->mask,p->len))state[k][i]=0;
   else {c->status=5;return;}
  }
 }
 if(!count){c->status=0;return;}
 int changed=0;
 for(u32 k=0;k<c->count;k++){
  struct Location*l=&c->loc[k];if(l->scene!=c->scene)continue;
  for(u32 i=0;i<l->patch_count;i++)if(!state[k][i]){
   struct Patch*p=&l->p[i];volatile u8*a=(volatile u8*)(c->bank+p->off+14);
   for(u32 j=0;j<p->len;j++)if(p->old[j]!=p->newv[j])a[j]=p->newv[j];a[-12]=(p->conditions>>8)?(p->conditions>>8):(p->conditions&255);changed=1;
  }
  if(same_session(c,run,l)){c->active=1;icon(c,k,run);}
 }
 if(changed)c->patch_count++;c->status=c->active?2:7;
}
/* The original pickup-state flag must still be set when the reward is granted.
 * Active action 35 (0x4126a0) stores flags at object + rd(object+0x80) + 0x68.
 * This preserves the original player-state gate even if an enemy interrupts pickup. */
static int pickup_active(u32 run,struct Location*l){
 u8*condition=l->p[1].old;u32 player=find_object(run,*(u16*)(condition+6),2);if(!player)return 0;
 u32 rel=rd(player+0x80);if(!rel||rel>4096)return 0;
 return (rd(player+rel+0x68)&(1u<<(rd((u32)condition+28)&31)))!=0;
}
static void call_action(u32 run,u8*action){
 u32 selection=rd(run+0x404);*(volatile u32*)(run+0x404)=(u32)action;
 void(*original)(u8*)=(void*)original_addr(*(short*)(action+2));original(action);
 *(volatile u32*)(run+0x404)=selection;
}
static int commit_reward(struct Context*c,struct Location*l){
 struct Menu*m=(void*)(c+1);if(!m->module)return 0;
 u32(__attribute__((stdcall))*get)(u32,const char*)=(void*)rd(0x453128);
 /* The injected blob is moved without PE relocations: build the export name
  * on the stack, never use a link-time absolute string pointer. */
 volatile char name[13];name[0]=82;name[1]=101;name[2]=119;name[3]=97;name[4]=114;name[5]=100;name[6]=67;name[7]=111;name[8]=109;name[9]=109;name[10]=105;name[11]=116;name[12]=0;
 int(*commit)(const char*,const char*)=(void*)get(m->module,(const char*)name);
 return commit&&commit(c->session,l->key);
}
static int reward_owned(u32 run,struct Location*l){
 u8*a=l->grant;u32 o=find_object(run,*(u16*)(a+6),33);if(!o)return 0;
 u32 state=rd(o+0x168);if(state<0x10000)return 0;
 const char*group=(const char*)(a+26);const char*key=(const char*)(a+26+*(u16*)(a+14));
 char lower[96];u32 j=0;for(;j<95&&group[j];j++)lower[j]=(group[j]>='A'&&group[j]<='Z')?group[j]+32:group[j];lower[j]=0;
 u32 g=tree_find(rd(state+0x14),lower);if(!g)return 0;
 for(j=0;j<95&&key[j];j++)lower[j]=(key[j]>='A'&&key[j]<='Z')?key[j]+32:key[j];lower[j]=0;
 u32 n=tree_find(rd(g+32),lower);return n&&rd(n+52)==1&&rd(n+48)>=0x10000&&*(u8*)rd(n+48)=='1';
}
static void halt_reward(struct Context*c,u32 run){c->errors++;*(volatile u32*)(run+0x178)=1;}
void dispatch(struct Context*c,u8*action){
 int kind=*(short*)(action+2);void(*original)(u8*)=(void*)original_addr(kind);
 if(c->magic!=0x42524832||c->version!=7||c->count>MAX_SOURCES)return;
 u32 run=rd(0x459a9c),app=rd(0x459a94);
 if(run>=0x10000&&app>=0x10000){
  u32 scene=rd(app+0x1ec),bank=rd(run+0x88);
  for(u32 k=0;k<c->count;k++){
   struct Location*l=&c->loc[k];if(l->scene!=scene)continue;
   if((u32)action==bank+l->grant_off){
    /* Never grant into a different slot/profile while the GUI switches runs. */
    if(c->errors||c->status!=2||c->bank!=bank||!same_session(c,run,l))return;
    if(kind!=33||*(u16*)(action+4)!=94){c->errors++;return;}
    if(consumed(c,run,l)||!pickup_active(run,l))return;
    if(!commit_reward(c,l)){halt_reward(c,run);return;}
    call_action(run,l->grant);
    if(!reward_owned(run,l)){halt_reward(c,run);return;}
    call_action(run,l->extra);
    if(!consumed(c,run,l)){halt_reward(c,run);return;}
    l->last_action=(u32)action;l->awards++;c->awards++;return;
   }
   if(c->status==2&&c->bank==bank)for(u32 j=0;j<l->display_count;j++){
    struct Display*d=&l->display[j];if((u32)action==bank+d->off&&kind==d->kind&&same_session(c,run,l)){call_action(run,d->action);return;}
   }
  }
 }
 original(action);
}
