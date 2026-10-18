/* Per-process, per-run cosmetic suppression, applied only at frame loading. */
U GraphicsDebug[8]={1,0,0,0,0,0,0,0}; /* version, applied disabled categories, sequence, load count */
static void graphics_debug_load(void){
 GraphicsDebug[1]=GraphicsDebug[2]=0;GraphicsDebug[3]++;GraphicsDebug[4]=1;
 if(!q||!receipt_init())return;GraphicsDebug[4]=2;
 unsigned char p[48]={0},tail;U n=0,more=0;
 H f=CreateFileA("..\\menu-runtime\\graphics-debug.bin",0x80000000,1,0,3,0,0);
 if(f==(H)-1)return;I ok=ReadFile(f,p,48,&n,0)&&ReadFile(f,&tail,1,&more,0);CloseHandle(f);
 U(W*pid)(void)=(void*)symbol(library("kernel32.dll"),"GetCurrentProcessId");
 GraphicsDebug[4]=3;GraphicsDebug[5]=pid?pid():0;GraphicsDebug[6]=*(U*)(p+4);GraphicsDebug[7]=n;
 if(!ok||n!=48||more||!pid||*(U*)p!=0x31444742||*(U*)(p+4)!=pid()||!samebytes(p+8,(const unsigned char*)q-304284+64,32)||*(U*)(p+40)>15)return;
 GraphicsDebug[4]=0;GraphicsDebug[1]=*(U*)(p+40);GraphicsDebug[2]=*(U*)(p+44);
}
