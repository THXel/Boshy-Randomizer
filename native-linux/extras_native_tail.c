#include "extras_plan.h"
static int matches(const B*a,const B*b,const B*mask,U n){for(U i=0;i<n;i++)if((a[i]&mask[i])!=(b[i]&mask[i]))return 0;return 1;}
/* Validate every selected operation before writing anything to this frame. */
int ExtrasPatch(B*bank,U scene,U flags){
 for(U i=0;i<sizeof(patches)/sizeof(*patches);i++){
  const struct ExtraPatch*p=&patches[i];if(p->scene!=scene||!(flags&p->flag))continue;
  B*a=bank+p->offset;if(!matches(a,p->old,p->mask,p->len)&&!matches(a,p->replacement,p->mask,p->len))return 0;
 }
 for(U i=0;i<sizeof(patches)/sizeof(*patches);i++){
  const struct ExtraPatch*p=&patches[i];if(p->scene!=scene||!(flags&p->flag))continue;
  B*a=bank+p->offset;for(U j=0;j<p->len;j++)if(p->old[j]!=p->replacement[j])a[j]=p->replacement[j];
 }return 1;
}
static int extras_session(U shared,U run){
 const char*session=(const char*)(shared-304284+64);if(!session[0])return 0;
 U table=rd(run+0x1278),count=rd(run+0x40);if(table<0x10000||count!=20000)return 0;
 for(U i=0;i<count;i++){
  U o=rd(table+i*8);if(o<0x10000||*(H*)(o+24)!=33)continue;
  U state=rd(o+0x168);if(state<0x10000)continue;
  U group=tree(rd(state+20),"randochecks");if(!group)continue;
  U node=tree(rd(group+32),"sessionid");if(!node||rd(node+52)!=32)continue;
  U value=rd(node+48);if(value<0x10000)continue;int equal=1;
  for(U j=0;j<32;j++)if(*(char*)(value+j)!=session[j]){equal=0;break;}
  if(equal)return 1;
 }return 0;
}
static void health(U run,U scene){
 U table=rd(run+0x1278);if(table<0x10000||rd(run+0x40)!=20000)return;
 int relevant=0;for(U j=0;j<sizeof(bosses)/sizeof(*bosses);j++)if(bosses[j].scene==scene)relevant=1;if(!relevant)return;
 for(U i=0;i<20000;i++){
  U o=rd(table+i*8);if(o<0x10000||*(H*)(o+24)!=2)continue;
  for(U j=0;j<sizeof(bosses)/sizeof(*bosses);j++){
   const struct BossHP*p=&bosses[j];if(p->scene!=scene||*(H*)(o+18)!=p->oi)continue;
   U rel=rd(o+128);if(rel<128||rel>=4096)continue;U values=rd(o+rel);if(values<0x10000)continue;
   if((scene==43||scene==44)&&(rd(values)!=0||(int)rd(values+8)<780))continue;
   U v=values+p->index*16;if(rd(v)==0&&(int)rd(v+8)>1&&rd(v+8)<=100000)*(U*)(v+8)=1;
  }
 }
}
static int skip_active;
static short(W*old_async)(int);static short(W*old_key)(int);static int(W*old_keyboard)(B*);
static short W extras_async(int key){return key==83&&skip_active?(short)0x8000:old_async(key);}
static short W extras_key(int key){return key==83&&skip_active?(short)0x8000:old_key(key);}
static int W extras_keyboard(B*keys){int ok=old_keyboard(keys);if(ok&&skip_active)keys[83]|=128;return ok;}
static int keyboard_hooks(void){
 if(old_async)return 1;
 void*(W*load)(const char*)=(void*)rd(0x45314c);void*(W*get)(void*,const char*)=(void*)rd(0x453128);
 int(W*protect)(void*,U,U,U*)=get(load("kernel32.dll"),"VirtualProtect");U prior;
 if(!protect||!protect((void*)0x453000,0x1000,4,&prior))return 0;
 old_async=(void*)rd(0x453384);old_key=(void*)rd(0x453398);old_keyboard=(void*)rd(0x453410);
 *(U*)0x453384=(U)extras_async;*(U*)0x453398=(U)extras_key;*(U*)0x453410=(U)extras_keyboard;
 U ignored;protect((void*)0x453000,0x1000,prior,&ignored);return 1;
}
static int skip_ready(B*bank,U scene){
 for(U i=0;i<sizeof(skips)/sizeof(*skips);i++)if(skips[i].scene==scene){
  B*p=bank+skips[i].offset;if(h(p)!=24||(short)h(p+2)!=-6||(short)h(p+4)!=-1||h(p+20)!=83)return -1;
  return 1;
 }return 0;
}
void MenuTick(void*shared,U run,U scene){
 skip_active=0;BaseMenuTick(shared,run,scene);U*s=shared;
 if(s[12]||scene<=1||scene==19||scene==20||!extras_session((U)shared,run))return;
 U bank=rd(run+0x88);if(bank<0x10000)return;
 if(!ExtrasPatch((B*)bank,scene,s[8])){s[12]=40;*(U*)(run+0x178)=1;return;}
 if(s[8]&16)health(run,scene);
 if(s[8]&512){int ready=skip_ready((B*)bank,scene);if(ready<0||!keyboard_hooks()){s[12]=41;*(U*)(run+0x178)=1;return;}skip_active=ready;}
 if(s[8]&2048){U*control=(U*)((B*)shared+2124);if(control[0]==0x42534531&&control[1]<=35){
  for(U i=0;i<sizeof(shots)/sizeof(*shots);i++)if(shots[i].scene==scene)*(U*)(bank+shots[i].offset)=control[1];
  for(U i=0;i<sizeof(sounds)/sizeof(*sounds);i++)if(sounds[i].scene==scene)*(H*)(bank+sounds[i].offset)=control[1]==sounds[i].frame?4:3;
 }}
}
