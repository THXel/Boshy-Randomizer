/* Cosmetic death resources only. The frame loader owns the expanded animation
 * banks and all imported images; gameplay events, saves and RNG stay intact. */
typedef struct {U magic,screenCount,screenFps,screenLoop,bloodCount,bloodFps,bloodLoop,width,height,origin;char identity[32];} DeathPlan;
_Static_assert(sizeof(DeathPlan)==72,"Death plan ABI");
static U deathCommon[8],deathPointers[8],deathReady,deathRun,deathTick,deathEpoch;
static DeathPlan deathPlan;static unsigned short deathDurations[96];
static U spider_player(U run,U scene);
U DeathScreenState[7]; /* visible, original object, image, serial, resets, scale (1000), opacity (255) */
static const U deathOI[8]={161,330,1042,1322,2947,105,1032,1323};

static U deathBorn[20000],deathObject[20000],deathBirthId[20000];
U DeathVisualState[10]={1,0,0,0,0,0,0,0,0,0}; /* version, active, load generation, imported, error, screen ticks, blood ticks, frame, max load ms, scene */
/* +0x1a is the native creation ID; +2 is the mutable selection-list link.
 * A skipped render tick must not restart a living particle's animation. */
static U death_age(U slot,U o,U tick){
 U birth=*(unsigned short*)(o+0x1a);
 if(deathObject[slot]!=o||deathBirthId[slot]!=birth){deathObject[slot]=o;deathBirthId[slot]=birth;deathBorn[slot]=tick;}
 return tick-deathBorn[slot];
}
static U death_index(U age,U fps,U count,U loop){U frame=age*fps/50;return frame<count?frame:loop+(frame-loop)%(count-loop);}
static U death_screen_index(U age){
 if(deathPlan.screenFps)return death_index(age,deathPlan.screenFps,deathPlan.screenCount,deathPlan.screenLoop);
 U prefix=0,cycle=0;for(U i=0;i<deathPlan.screenCount;i++){if(i<deathPlan.screenLoop)prefix+=deathDurations[i];else cycle+=deathDurations[i];}
 if(age>=prefix)age=prefix+(age-prefix)%cycle;
 for(U i=0;i<deathPlan.screenCount;i++){if(age<deathDurations[i])return i;age-=deathDurations[i];}return 0;
}
static void death_path(char*out,U role,U frame){
 S prefix="..\\menu-runtime\\deathpacks\\";U n=0;for(;prefix[n];n++)out[n]=prefix[n];
 for(U j=0;j<32;j++)out[n++]=deathPlan.identity[j];out[n++]='\\';S kind=role?"blood\\":"screen\\";
 for(U j=0;kind[j];j++)out[n++]=kind[j];out[n++]='0'+frame/100;out[n++]='0'+frame/10%10;out[n++]='0'+frame%10;out[n++]='.';out[n++]='p';out[n++]='n';out[n++]='g';out[n]=0;
}
static I death_plan(void){
 U got=0,more=0;unsigned char extra;H f=CreateFileA("..\\menu-runtime\\deathpack.bin",0x80000000,7,0,3,0,0);if(f==(H)-1)return 0;
 I ok=ReadFile(f,&deathPlan,sizeof(deathPlan),&got,0);U timeline=0;
 if(ok&&got==sizeof(deathPlan)&&!deathPlan.screenFps&&deathPlan.screenCount&&deathPlan.screenCount<=96){U n=0;ok=ReadFile(f,deathDurations,deathPlan.screenCount*2,&n,0)&&n==deathPlan.screenCount*2;for(U j=0;ok&&j<deathPlan.screenCount;j++){if(!deathDurations[j]||deathDurations[j]>500)ok=0;timeline+=deathDurations[j];}if(timeline>3000)ok=0;}
 ok=ok&&ReadFile(f,&extra,1,&more,0);CloseHandle(f);
 DeathPlan*p=&deathPlan;
 if(!ok||got!=sizeof(*p)||more||p->magic!=0x31445242){DeathVisualState[4]=1;return 0;}
 if(!p->screenCount&&!p->bloodCount)return 0;
 if(!p->screenCount||p->screenCount>96||!p->bloodCount||p->bloodCount>32||(!p->screenFps&&!timeline)||p->screenFps>50||p->bloodFps>50||p->screenLoop>=p->screenCount||p->bloodLoop>=p->bloodCount||!p->width||p->width>64||!p->height||p->height>64||(p->origin&65535)>=p->width||(p->origin>>16)>=p->height){DeathVisualState[4]=1;return 0;}
 for(U j=0;j<32;j++)if(!hexchar(p->identity[j])){DeathVisualState[4]=1;return 0;}
 for(U role=0;role<2;role++)for(U j=0;j<(role?p->bloodCount:p->screenCount);j++){char path[100];death_path(path,role,j);if(!theme_png(path,role?p->width:640,role?p->height:480)){DeathVisualState[4]=2;return 0;}}
 return 1;
}
static void death_before_images(void){
 pack_death_clear();deathReady=0;DeathVisualState[1]=DeathVisualState[4]=0;deathEpoch++;
 for(U i=0;i<8;i++)deathCommon[i]=deathPointers[i]=0;
 U app=*(U*)0x459a94,scene=app?*(U*)(app+0x1ec):0;
 if(!q||scene<=1||scene>60||!receipt_init()||!death_plan())return;
 if(*(U*)0x42b8a0!=0x1468ff6a){DeathVisualState[4]=3;return;}
 for(U i=0;i<8;i++){
  U d=theme_definition(deathOI[i]),c=d?*(U*)(d+20):0;U size=i<5?226:258,offset=i<5?116:146,count=i<5?deathPlan.screenCount:deathPlan.bloodCount;
  if(c<65536||!(*(U*)(d+28)&1)||(*(U*)(d+28)&2))continue;
  if(*(unsigned short*)(d+2)!=2||*(U*)c!=size||*(unsigned short*)(c+6)!=offset||*(unsigned short*)(c+offset)!=size-offset||*(unsigned short*)(c+offset+2)!=16||*(unsigned short*)(c+offset+4)!=36||*(unsigned short*)(c+offset+36)!=64||*(unsigned short*)(c+offset+106)!=(i<5?1:2)){DeathVisualState[4]=4;continue;}
  U bytes=offset+108+(count+1)*2,newCommon=0;I(*allocate)(U,U*)=(void*)0x420240;void(*release)(U*)=(void*)0x4202d0;
  if(!allocate(bytes,&newCommon)){DeathVisualState[4]=5;continue;}
  for(U j=0;j<offset+108;j++)*(unsigned char*)(newCommon+j)=*(unsigned char*)(c+j);
  *(U*)newCommon=bytes;*(unsigned short*)(newCommon+offset)=bytes-offset;*(unsigned short*)(newCommon+offset+106)=count+1;
  /* Static animation: the cosmetic clock selects frames, not game RNG/events. */
  *(unsigned short*)(newCommon+offset+100)=0;
  for(U j=0;j<=count;j++)*(unsigned short*)(newCommon+offset+108+j*2)=*(unsigned short*)(c+offset+108+(i<5?0:j%2)*2);
  *(U*)(d+20)=newCommon;*(U*)(d+28)|=0x20;release(&c);
  deathCommon[i]=newCommon;deathPointers[i]=newCommon+offset+108;
 }
 DeathVisualState[2]++;deathReady=1;
}
static void death_after_images(I result){
 if(result||!deathReady){deathReady=0;return;}U started=GetTickCount();
 I(*load)(U,S,I*)=(void*)0x42b8a0;
 for(U i=0;i<8;i++)if(deathPointers[i]){
  U count=i<5?deathPlan.screenCount:deathPlan.bloodCount;
  for(U j=0;j<count;j++){
   U ptr=deathPointers[i]+j*2;char path[100];death_path(path,i>=5,j);
   I settings[6]={24,i<5?320:(I)(deathPlan.origin&65535),i<5?240:(I)(deathPlan.origin>>16),0,0,-1};
   if(!load(ptr,path,settings)||!*(unsigned short*)ptr){
    /* The extra last frame retains a live reference to the original image.
     * Swap references, without reallocating or unbalancing MMF's refcounts. */
    for(U k=0;k<8;k++)if(deathPointers[k]){U end=deathPointers[k]+2*(k<5?deathPlan.screenCount:deathPlan.bloodCount);unsigned short original=*(unsigned short*)end;*(unsigned short*)end=*(unsigned short*)deathPointers[k];*(unsigned short*)deathPointers[k]=original;}
    DeathVisualState[4]=6;deathReady=0;return;
   }DeathVisualState[3]++;
  }
 }
 DeathVisualState[1]=1;U elapsed=GetTickCount()-started;if(elapsed>DeathVisualState[8])DeathVisualState[8]=elapsed;
}
/* Imported pixels own their fade. The original object otherwise stays fully
 * transparent during Boshy's delayed title entrance and hides the red first phase. */
static I death_unfade(U o){
 U rel=*(U*)(o+0xbc);if(rel<256||rel>4096)return 0;
 U r=o+rel,effect=*(U*)(r+24),param=*(U*)(r+28),mode=effect&0xfff;
 if(mode>1)return 0;
 U nextEffect=(effect&~0xfff)|0x1000,nextParam=0xff000000|((effect&0x1000)&&!mode?(param&0xffffff):0xffffff);
 if(effect!=nextEffect||param!=nextParam){*(U*)(r+24)=nextEffect;*(U*)(r+28)=nextParam;void(*update)(U)=(void*)0x4127a0;update(o);}
 DeathScreenState[6]=255;return 1;
}
/* Animated blood stays airborne: Kamilia fades at animation end; WannaFest
 * uses rotating textured cubes. Boshy's paste-and-destroy floor actions would
 * remove these larger particles immediately. Static/vanilla blood and gameplay
 * objects keep the original actions; imported particles have a bounded life. */
static I death_animated_blood(U o){
 if(!deathReady||!deathPlan.bloodFps||o<65536)return 0;
 U oi=*(unsigned short*)(o+0x12);
 for(U i=5;i<8;i++)if(oi==deathOI[i]&&deathCommon[i]&&*(U*)(o+0x44)==deathCommon[i])return 1;
 return 0;
}
static void death_blood_paste(U action){
 U(*selected)(U)=(void*)0x449500;
 if(death_animated_blood(selected(action)))return;
 void(*original)(U)=(void*)0x4111b0;original(action);
}
static void death_blood_destroy(U action){
 U(*selected)(U)=(void*)0x449500;
 if(death_animated_blood(selected(action)))return;
 void(*original)(U)=(void*)0x411e80;original(action);
}
static void death_tick(U run,U scene){
 DeathVisualState[9]=scene;
 U p=spider_player(run,scene),rel=p?*(U*)(p+0x80):0;
 I alive=p&&rel>0&&rel<4096&&!(*(U*)(p+rel+0x68)&(1U<<5));
 if(packDeathSerial&&(scene<=1||scene>60||run!=packDeathRun||*(U*)(run+0xd0)<packDeathTick||alive)){
  pack_death_clear();DeathScreenState[0]=0;DeathScreenState[4]++;
 }
 if(!deathReady||scene<=1||scene>60)return;
 U tick=*(U*)(run+0xd0),table=*(U*)(run+0x1278),count=*(U*)(run+0x40);
 if(table<65536||!count||count>20000)return;
 static U epoch;
 if(run!=deathRun||tick<deathTick||epoch!=deathEpoch){for(U i=0;i<20000;i++)deathObject[i]=0;deathRun=run;epoch=deathEpoch;}
 if(tick==deathTick)return;deathTick=tick;
 for(U slot=0;slot<count;slot++){
  U o=*(U*)(table+slot*8);if(o<65536||*(unsigned short*)(o+0x18)!=2||*(unsigned short*)(o+0x7c)&1)continue;
  U oi=*(unsigned short*)(o+0x12),i=0;for(;i<8&&deathOI[i]!=oi;i++);if(i==8||!deathCommon[i]||*(U*)(o+0x44)!=deathCommon[i]||*(U*)(o+0xb8)!=462)continue;
  U birth=*(unsigned short*)(o+0x1a),age=death_age(slot,o,tick),frame;
  if(i>=5&&deathPlan.bloodFps&&age*deathPlan.bloodFps>=deathPlan.bloodCount*50){
   /* Queue ordinary native destruction, never free a renderer object ourselves. */
   *(unsigned short*)(o+0x7c)|=1;void(*destroy)(I)=(void*)0x41f730;destroy(*(short*)o);continue;
  }
  if(i<5)frame=packDeathSerial&&packDeathRun==run&&tick>=packDeathTick?death_screen_index(tick-packDeathTick):0;
  else frame=deathPlan.bloodFps?(deathPlan.bloodLoop?death_index(age,deathPlan.bloodFps,deathPlan.bloodCount,deathPlan.bloodLoop):(age*deathPlan.bloodFps/50+slot*17U+birth)%deathPlan.bloodCount):(slot*2654435761U+birth)%deathPlan.bloodCount;
  U image=*(unsigned short*)(deathPointers[i]+frame*2);if(!image||image>=32768)continue;
  if(i<5){death_unfade(o);DeathScreenState[0]=packDeathSerial!=0;DeathScreenState[1]=o;DeathScreenState[2]=image;DeathScreenState[3]=packDeathSerial;DeathScreenState[5]=1000;}
  *(U*)(o+0xdc)=*(U*)(o+0x10c)=image;*(U*)(o+0xfc)=1;
  U sprite=*(U*)(o+0xd4);if(sprite){void(W*change)(U,U,I,I,U)=(void*)0x451926;change(*(U*)0x459a6c,sprite,*(I*)(o+0x4c)-*(I*)(run+0xb0),*(I*)(o+0x54)-*(I*)(run+0xb4),image);}
  DeathVisualState[i<5?5:6]++;if(i<5)DeathVisualState[7]=frame;
 }
}

/* Override only the original Game Over scale action. Keeping the original
 * object also keeps its lifetime, reset and renderer cleanup entirely native. */
static void death_scale_action(U action){
 U oi=*(unsigned short*)(action+6),i=0;for(;i<5&&deathOI[i]!=oi;i++);
 if(deathReady&&i<5&&deathCommon[i]){
  U(*selected)(U)=(void*)0x449500;U o=selected(action);
  if(o>=65536&&*(unsigned short*)(o+0x12)==oi&&*(U*)(o+0x44)==deathCommon[i]){void(*scale)(U,U,U,I)=(void*)0x4113e0;scale(o,0x3f800000,0x3f800000,0);return;}
 }
 void(*original)(U)=(void*)0x4114c0;original(action);
}
static void death_alpha_action(U action){
 U oi=*(unsigned short*)(action+6),i=0;for(;i<5&&deathOI[i]!=oi;i++);
 if(deathReady&&i<5&&deathCommon[i]){
  U(*selected)(U)=(void*)0x449500;U o=selected(action);
  if(o>=65536&&*(unsigned short*)(o+0x12)==oi&&*(U*)(o+0x44)==deathCommon[i]&&death_unfade(o))return;
 }
 void(*original)(U)=(void*)0x412d10;original(action);
}
static I death_init(void){
 if(*(U*)0x456a58!=0x4111b0||*(U*)0x456280!=0x411e80||*(U*)0x456a6c!=0x4114c0||*(U*)0x4113e0!=0x8b20ec83||*(U*)0x456324!=0x412d10||*(U*)0x4127a0!=0x04244c8b)return 0;
 return hook(0x456a6c,death_scale_action)&&hook(0x456324,death_alpha_action)&&hook(0x456a58,death_blood_paste)&&hook(0x456280,death_blood_destroy);
}
