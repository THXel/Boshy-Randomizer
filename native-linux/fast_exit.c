/* Shared tail: magic, allowed scene bitmasks, status (0 idle, 1 armed,
 * 2 cancel, 3 committed, 256+destination latched). Fail open on timeout. */
static U exitRun,exitScene,exitData,exitCommand,exitSince,exitWaiting,exitArmed,exitTick;
U ExitState[6]={0x42584531,0,0,0,0,0}; /* magic, catches, fallbacks, from, to, waiting */
static void(*exitOriginal)(U);
static volatile U*exit_control(void){return (volatile U*)((char*)q+2144);}
static void exit_tick(U run,U scene){
 volatile U*c=exit_control();
 if(c[0]!=0x42584531){c[0]=0x42584531;c[1]=c[2]=c[3]=0;}
 if(exitWaiting){
  I same=run==exitRun&&scene==exitScene;
  I expire=(U)(GetTickCount()-exitSince)>=1500;
  if(!same||c[3]<256||expire){
   /* A completed destination request wins; never restore an obsolete exit. */
   if(same&&c[3]!=3&&*(unsigned short*)(run+0x30)==0){*(U*)(run+0x38)=exitData;*(unsigned short*)(run+0x30)=exitCommand;ExitState[2]++;}
   exitWaiting=0;ExitState[5]=0;c[3]=0;
   if(same&&guardOn&&guardRun==run){*(U*)(run+0x178)=guardPause;guardOn=0;if(q->enabled==3)q->enabled=1;}
  }
 }else if(c[3]==1){
  U tick=*(U*)(run+0xd0);
  if(exitArmed&&(run!=exitRun||scene!=exitScene||tick<exitTick)){c[3]=0;exitArmed=0;}
  else {exitRun=run;exitScene=scene;exitTick=tick;exitArmed=1;}
 }else {exitArmed=0;if(c[3])c[3]=0;}
}
static void exit_action(U action){
 exitOriginal(action);
 if(!q)return;U run=*(U*)0x459a9c;
 if(exitWaiting){
  /* A second matching action in the same event pass must stay intercepted. */
  if(run==exitRun&&q->scene==exitScene&&*(unsigned short*)(run+0x30)==exitCommand&&*(U*)(run+0x38)==exitData)*(unsigned short*)(run+0x30)=0;
  return;
 }
 if(q->scene<=1||q->enabled!=1)return;
 volatile U*c=exit_control();
 if(c[0]!=0x42584531||c[3]!=1||run!=exitRun||q->scene!=exitScene)return;
 U command=*(unsigned short*)(run+0x30),data=*(U*)(run+0x38),dest=~0U;
 /* MMF next-frame and jump-to-frame actions. Restart/quit are never exits. */
 if(command==1)dest=exitScene+1;
 else if(command==3&&(data&0xffff8000)==0x8000)dest=data&0x7fff;
 else if(command==3&&data<0x8000){
  /* MMF's literal frame handles use the application's original lookup. */
  U app=*(U*)0x459a94,table=*(U*)(app+0xcc),count=*(unsigned short*)(app+0xc8);
  if(table>=0x10000&&data<count){dest=*(unsigned short*)(table+2*data);if(dest==0xffff)dest=exitScene+1;}
 }
 if(dest>=64||!(c[1+dest/32]&(1U<<(dest%32)))||dest==exitScene)return;
 if((oldAsync(82)&0x8000)||(oldAsync(81)&0x8000))return;
 exitData=data;exitCommand=command;exitSince=GetTickCount();exitWaiting=1;exitArmed=0;
 *(unsigned short*)(run+0x30)=0;
 guardRun=run;guardScene=exitScene;guardPause=*(U*)(run+0x178);guardSince=exitSince;guardOn=1;
 *(U*)(run+0x178)=1;q->enabled=3;
 ExitState[1]++;ExitState[3]=exitScene;ExitState[4]=dest;ExitState[5]=1;
 __asm__ volatile("":::"memory");c[3]=256+dest;
}
static I exit_init(void){if(*(U*)0x457050!=0x415100)return 0;exitOriginal=(void*)0x415100;return hook(0x457050,exit_action);}
