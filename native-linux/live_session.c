/* Menu-only transaction. Commands run on the engine thread, never in a reader.
 * Exact ABI, PID, nonce, menu generation and INI++ signatures are checked first. */
U SessionState[8]={0x42524c31,0,0,0,0,0,0,0};
static U sessionRun,sessionPause;
static unsigned char sessionPayload[304296];
static U session_object(U run,U oi){
 U table=*(U*)(run+0x1278),count=*(U*)(run+0x40);if(table<0x10000||!count||count>20000)return 0;
 for(U i=0;i<count;i++){U o=*(U*)(table+8*i);if(o>=0x10000&&*(unsigned short*)(o+18)==oi&&*(unsigned short*)(o+24)==33&&*(U*)(o+0x168)>=0x10000)return o;}return 0;
}
static U session_ini(void){
 H(W*module)(S)=(void*)symbol(library("kernel32.dll"),"GetModuleHandleA");
 U base=module?(U)module("INI++.mfx"):0;
 if(!base||*(U*)(base+0xa130)!=0x83ec8b55||*(U*)(base+0xa134)!=0x8b5624ec)return 0;
 return base;
}
static void session_reset(U run){
 musicLoaded=musicCount=0;for(U i=1;i<6;i++)MusicState[i]=0;
 sceneryLoaded=sceneryRun=sceneryTick=0;sceneryScene=~0U;
 for(U i=1;i<8;i++)SceneryState[i]=0;for(U i=0;i<SCENERY_COUNT;i++)sceneryHandles[i]=sceneryApplied[i]=0;
 chaosLoaded=chaosMask=chaosRun=chaosTick=chaosClouds=chaosCloudReady=0;chaosScene=~0U;
 for(U i=1;i<14;i++)ChaosState[i]=0;for(U i=0;i<CHAOS_COUNT;i++)chaosDone[i]=chaosHandles[i]=chaosApplied[i]=0;
 for(U i=0;i<3;i++)ChaosCloudState[i]=0;
 spider_remove(run);spiderLoaded=spiderImage=spiderRun=spiderScene=spiderTick=spiderNow=spiderPlayer=spiderSlot=spiderAge=0;
 for(U i=0;i<32;i++)spiderImages[i]=0;for(U i=1;i<10;i++)SpiderState[i]=0;
 exitRun=exitScene=exitData=exitCommand=exitSince=exitWaiting=exitArmed=exitTick=0;
 hubNoticeActive=0;hubLastScene=~0U;for(U i=1;i<6;i++)ExitState[i]=0;
 /* Character commands, shot style, spawn guard and exit command are per-run. */
 for(U i=1648;i<2160;i++)*((unsigned char*)q+i)=0;
}
static void session_tick(U run,U scene){
 if(sessionLocked){
  if(scene!=1||run!=sessionRun){sessionLocked=0;SessionState[3]=0;SessionState[2]=8;q->error=45;return;}
  *(U*)(run+0x178)=1;
 }
 if(scene!=1||!receipt_init())return;
 static U last;U now=GetTickCount();if(now-last<25)return;last=now;
 H f=CreateFileA("..\\menu-runtime\\session-command.bin",0x80000000,1,0,3,0,0);if(f==(H)-1)return;
 U h[8],n=0,extra=0;unsigned char tail;I ok=ReadFile(f,h,sizeof(h),&n,0)&&n==sizeof(h);
 U(W*pid)(void)=(void*)symbol(library("kernel32.dll"),"GetCurrentProcessId");
 if(!ok||h[0]!=0x42524c31||!pid||h[1]!=pid()||!h[2]||h[2]==SessionState[1]){CloseHandle(f);return;}
 SessionState[1]=h[2];SessionState[2]=1;SessionState[4]=run;SessionState[5]=scene;
 if(h[3]<1||h[3]>5||h[4]>3||h[7]||h[6]!=(h[3]==2?304296U:0)){CloseHandle(f);SessionState[2]=2;return;}
 if(h[6])ok=ReadFile(f,sessionPayload,sizeof(sessionPayload),&n,0)&&n==sizeof(sessionPayload);
 ok=ok&&ReadFile(f,&tail,1,&extra,0)&&!extra;CloseHandle(f);if(!ok){SessionState[2]=3;return;}
 if(h[3]==1){
  if(sessionLocked||q->enabled!=2||!session_ini()||!session_object(run,83)||!session_object(run,47)){SessionState[2]=4;return;}
  sessionRun=run;sessionPause=lastRun==run?savedPause:*(U*)(run+0x178);savedPause=sessionPause;lastRun=run;sessionLocked=1;SessionState[3]=1;*(U*)(run+0x178)=1;
 }else{
  if(!sessionLocked||run!=sessionRun){SessionState[2]=5;return;}
  if(h[3]==3){sessionLocked=0;SessionState[3]=0;*(U*)(run+0x178)=sessionPause;}
  else{
   U base=session_ini(),profile=session_object(run,83),save=session_object(run,47);
   if(!base||!profile||!save){SessionState[2]=4;return;}
   if(h[3]==2){
    if(!h[4]||*(U*)sessionPayload!=0x42524832||*(U*)(sessionPayload+4)!=7||!*(U*)(sessionPayload+48)||*(U*)(sessionPayload+48)>40||sessionPayload[96]){SessionState[2]=6;return;}
    for(U i=64;i<96;i++)if(!((sessionPayload[i]>='0'&&sessionPayload[i]<='9')||(sessionPayload[i]>='a'&&sessionPayload[i]<='f'))){SessionState[2]=6;return;}
   }
   short(W*load)(U,S,I)=(void*)(base+0xa130);
   load(profile,"onlineLicense.ini",1);
   if(h[4]){char file[]="SaveFile1.ini";file[8]='0'+h[4];load(save,file,1);}
   if(h[3]==2||h[3]==5){
    session_reset(run);unsigned char*context=(unsigned char*)q-304284;
    if(h[3]==2){for(U i=0;i<304284;i++)context[i]=sessionPayload[i];q->a=h[5];for(U i=0;i<12;i++)*((unsigned char*)q+2124+i)=sessionPayload[304284+i];}
    else{for(U i=0;i<304284;i++)context[i]=0;*(U*)context=0x42524832;*(U*)(context+4)=7;q->a=0;}
    SessionState[6]++;SessionState[7]=(U)context;
   }
  }
 }
 SessionState[2]=0;
}
