/* Global cosmetic sound pack. Literal actions only; unrelated audio delegates. */
static struct {char name[68],path[100];U kind;} packRows[32];
static U packCount,packGeneration,packChecked;
static U packDeathSerial,packDeathRun,packDeathTick,packDeathPlaying;
/* During an imported death cue, stop native music/SFX and consume subsequent
 * sound actions. Reset/scene loading clears this gate before native audio starts
 * again. Do not change master or channel volumes (including user mute settings).
 * Channel 32 is reserved only for the one-shot death sequence. */
static void pack_death_clear(void){
 if(packDeathPlaying){void(*stop)(I)=(void*)0x41fab0;void(*reserve)(I,I)=(void*)0x41fe30;stop(32);reserve(32,0);}
 packDeathPlaying=packDeathSerial=0;
}
U SoundPackState[8]={0x42525031,0,0,0,0,0,0,0}; /* magic,generation,count,replaced,error,last row,scene,code */
U SoundTrace[1+16*36]; /* ring: scene, code, size, reserved, up to 128 action bytes */
static I pack_equal(S a,S b,U n){for(U j=0;j<n;j++){if(a[j]!=b[j])return 0;if(!a[j])return 1;}return 0;}
static I pack_text(S a,U n){for(U j=0;j<n;j++)if(!a[j])return j>0;return 0;}
static void pack_observe(U action){
 U size=*(unsigned short*)action,code=*(unsigned short*)(action+4);if((code!=0&&code!=4&&code!=11&&code!=12&&code!=1&&code!=6)||size<8||size>1024)return;
 U *row=SoundTrace+1+(SoundTrace[0]%16)*36;row[0]=q?q->scene:~0U;row[1]=code;row[2]=size;row[3]=0;
 for(U j=0;j<128;j++)((unsigned char*)(row+4))[j]=j<size?*(unsigned char*)(action+j):0;
 SoundTrace[0]++;
}
static void pack_tick(void){
 U now=GetTickCount();if(packChecked&&(U)(now-packChecked)<500)return;packChecked=now?now:1;
 if(!receipt_init())return;
 H f=CreateFileA("..\\menu-runtime\\soundpack.bin",0x80000000,7,0,3,0,0);if(f==(H)-1){pack_death_clear();packCount=0;return;}
 U h[4],n=0;I ok=ReadFile(f,h,16,&n,0)&&n==16&&h[0]==0x31505242&&h[1]&&h[2]<=32&&h[3]==0;
 if(!ok){CloseHandle(f);packCount=0;SoundPackState[4]=1;return;}
 if(h[1]==packGeneration){CloseHandle(f);return;}
 pack_death_clear();packCount=0;SoundPackState[4]=0;
 ok=ReadFile(f,packRows,h[2]*172,&n,0)&&n==h[2]*172;unsigned char end;U more=0;ok=ok&&ReadFile(f,&end,1,&more,0)&&!more;CloseHandle(f);
 if(!ok){SoundPackState[4]=2;return;}
 for(U i=0;i<h[2];i++){
  S p=packRows[i].path;
  if(!pack_text(packRows[i].name,68)||!pack_text(p,100)||(packRows[i].kind!=1&&packRows[i].kind!=2)||!samebytes((const unsigned char*)p,(const unsigned char*)"..\\menu-runtime\\music\\",22)){SoundPackState[4]=3;return;}
  for(U j=22;p[j];j++)if(!((p[j]>='0'&&p[j]<='9')||(p[j]>='a'&&p[j]<='z')||p[j]=='.')){SoundPackState[4]=3;return;}
  f=CreateFileA(p,0x80000000,7,0,3,0,0);if(f==(H)-1){SoundPackState[4]=4;return;}CloseHandle(f);
 }
 packCount=h[2];packGeneration=h[1];SoundPackState[1]=h[1];SoundPackState[2]=h[2];
}
static I pack_action(U action){
 if(packDeathPlaying)return 1; /* One cue per death, no overlapping native audio. */
 if(!q||!packCount)return 0;
 U size=*(unsigned short*)action,code=*(unsigned short*)(action+4);I channel=0;
 if(!((code==0&&size==88)||(code==4&&size==108)||(code==11&&size==108)||(code==12&&size==128)))return 0;
 if(code==11||code==12){
  if(*(U*)(action+88)!=0x00160014||*(U*)(action+92)!=0xffff0000||*(U*)(action+96)!=0x000a0000||*(U*)(action+104)!=0)return 0;
  channel=*(I*)(action+100);if(channel<1||channel>32)return 0;
 }
 for(U i=0;i<packCount;i++)if(pack_equal((S)(action+22),packRows[i].name,66)){
  if(pack_equal(packRows[i].name,"select",68)&&q->scene!=19)return 0;
  U flags=0x10000|((*(unsigned char*)(action+20)&1)?2:0);
  if(packRows[i].kind==1){flags|=0x10;if(!channel)channel=2;void(*reserve)(I,I)=(void*)0x41fe30;reserve(channel,1);}
  if(packRows[i].kind==2){void(*stop)(I)=(void*)0x41fab0;for(I c=1;c<=32;c++)stop(c);channel=32;void(*reserve)(I,I)=(void*)0x41fe30;reserve(channel,1);packDeathPlaying=1;U run=*(U*)0x459a9c;if(run>=65536){packDeathRun=run;packDeathTick=*(U*)(run+0xd0);packDeathSerial++;}}
  void(*play)(S,U,I,I)=(void*)0x41f9a0;play(packRows[i].path,flags,0,channel);
  SoundPackState[3]++;SoundPackState[5]=i;SoundPackState[6]=q->scene;SoundPackState[7]=code;return 1;
 }
 return 0;
}
