/* Music stays on MMF's original channel and obeys its mute/pause/stop actions.
 * An exact-build dispatcher hook substitutes only catalogued music actions. */
static struct {char name[68],path[100];} musicRows[64];
static U musicCount,musicLoaded;
U MusicState[6]={0x42524d31,0,0,0,0,0}; /* magic, loaded, count, swaps, error, last row */
static void (*musicOriginal)(U);
static I music_text(S s,U n){for(U j=0;j<n;j++)if(!s[j])return j>0;return 0;}
static I music_equal(S a,S b,U n){for(U j=0;j<n;j++){if(a[j]!=b[j])return 0;if(!a[j])return 1;}return 0;}
static void music_load(void){
 if(musicLoaded)return;musicLoaded=1;
 if(!q||(q->a&4096)==0)return;
 if(!receipt_init()){MusicState[4]=1;return;}
 H f=CreateFileA("..\\menu-runtime\\music.bin",0x80000000,1,0,3,0,0);if(f==(H)-1){MusicState[4]=2;return;}
 unsigned char header[40];U n=0;I ok=ReadFile(f,header,40,&n,0)&&n==40;
 S session=(S)((char*)q-304284+64);U count=*(U*)(header+36);
 if(!ok||!samebytes(header,(const unsigned char*)"BRM1",4)||!samebytes(header+4,(const unsigned char*)session,32)||!count||count>64){CloseHandle(f);MusicState[4]=3;return;}
 ok=ReadFile(f,musicRows,count*168,&n,0)&&n==count*168;unsigned char end;U more=0;
 ok=ok&&ReadFile(f,&end,1,&more,0)&&!more;CloseHandle(f);
 if(!ok){MusicState[4]=4;return;}
 for(U i=0;i<count;i++){
  S p=musicRows[i].path;if(!music_text(musicRows[i].name,68)||!music_text(p,100)||!samebytes((const unsigned char*)p,(const unsigned char*)"..\\menu-runtime\\music\\",22)){MusicState[4]=5;return;}
  /* Generated names contain only a digest and a supported extension. */
  for(U j=22;p[j];j++)if(!((p[j]>='0'&&p[j]<='9')||(p[j]>='a'&&p[j]<='z')||p[j]=='.')){MusicState[4]=5;return;}
  f=CreateFileA(p,0x80000000,7,0,3,0,0);if(f==(H)-1){MusicState[4]=6;return;}CloseHandle(f);
 }
 musicCount=count;MusicState[1]=1;MusicState[2]=count;
}
static void music_action(U action){
 pack_observe(action);if(pack_action(action))return;
 if(q&&(q->a&4096)&&q->scene>1&&musicCount){
  unsigned short size=*(unsigned short*)action,code=*(unsigned short*)(action+4);
  if((code==11&&size==108)||(code==12&&size==128)){
   /* Only literal channel 2 / infinite-loop music; never dynamic expressions. */
   if(*(U*)(action+88)==0x00160014&&*(U*)(action+92)==0xffff0000&&*(U*)(action+96)==0x000a0000&&*(U*)(action+100)==2&&*(U*)(action+104)==0
      &&(code==11||(*(U*)(action+108)==0x001b0014&&*(U*)(action+112)==0xffff0000&&*(U*)(action+116)==0x000a0000&&*(U*)(action+120)==0&&*(U*)(action+124)==0))){
    for(U i=0;i<musicCount;i++)if(music_equal((S)(action+22),musicRows[i].name,66)){
     void(*play)(S,U,I,I)=(void*)0x41f9a0;
     /* External samples have no embedded handle. MMF otherwise mistakes
      * channel 2 for a free automatic-SFX channel. Reserve it via the native
      * Lock Channel action; explicit music, stop, pause and volume still work. */
     void(*reserve)(I,I)=(void*)0x41fe30;reserve(2,1);
     /* Retain the original sample priority / uninterruptible flag. */
     /* A shorter replacement must not fall silent when an original boss song
      * used the one-shot action. Catalogued background music always loops. */
     U flags=0x10010|((*(unsigned char*)(action+20)&1)?2:0);
     play(musicRows[i].path,flags,0,2);MusicState[3]++;MusicState[5]=i;return;
    }
   }
  }
 }
 musicOriginal(action);
}
static I music_init(void){
 if(*(U*)0x457054!=0x415120||*(U*)0x41fe30!=0x0824448b)return 0;
 musicOriginal=(void*)0x415120;return hook(0x457054,music_action);
}
