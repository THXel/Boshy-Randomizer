/* Boshy laboratory bridge. RunHeader offsets and scene-request semantics:
 * Pixelsuft/boshyst commit 55e40b3e5a232a040e56aa2a249a501ca456352e,
 * src/ui.cpp, src/utils.cpp, src/ghidra_headers.h. See reference-boshyst/LICENSE.md.
 * ReadProcessMemory transport based on the user's PinguLexa Boshy reader.
 * This prototype refuses any executable outside this dated laboratory copy.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "runtime_root.h"
static HANDLE proc;
static uintptr_t base;
static int rd(uintptr_t a,void *p,size_t n){SIZE_T got=0;return ReadProcessMemory(proc,(void*)a,p,n,&got)&&got==n;}
static uint32_t u32(uintptr_t a){uint32_t v=0;rd(a,&v,4);return v;}
static uint16_t u16(uintptr_t a){uint16_t v=0;rd(a,&v,2);return v;}
static int wr(uintptr_t a,void *p,size_t n){SIZE_T got=0;return WriteProcessMemory(proc,(void*)a,p,n,&got)&&got==n;}
static uint32_t app(void){return u32(base+0x59a94);}
static uint32_t run(void){return u32(base+0x59a9c);}
static uint32_t scene(void){return u32(app()+0x1ec);}
static uint32_t find_object(uint16_t oi){
 uint32_t r=run(),list=u32(r+0x1278),count=u32(r+0x40);
 if(count>20000)return 0;
 for(unsigned i=0;i<count;i++){uint32_t p=u32(list+i*8);if(p>0x10000&&u16(p+0x12)==oi&&u16(p+0x18)==33)return p;}
 return 0;
}
static uint32_t tree_find(uint32_t head,const char *key){
 uint32_t node=u32(head+4);char name[128];
 for(unsigned i=0;i<128 && node>0x10000 && node!=head;i++){
  uint32_t len=u32(node+0x14);if(len>=sizeof(name)||!rd(u32(node+0x10),name,len))return 0;name[len]=0;
  int cmp=strcmp(key,name);if(!cmp)return node;
  node=u32(node+(cmp<0?0:8));
 }
 return 0;
}
static uint32_t ini_node(unsigned oi,const char *group,const char *key){
 uint32_t obj=find_object(oi);if(!obj)return 0;
 uint32_t state=u32(obj+0x168);if(state<0x10000)return 0;
 uint32_t g=tree_find(u32(state+0x14),group);if(!g)return 0;
 return tree_find(u32(g+0x20),key);
}
int main(void){
 char exe[MAX_PATH],directory[MAX_PATH];if(!runtime_root(exe,directory)){fprintf(stderr,"Private runtime required\n");return 2;}
 HANDLE s=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);PROCESSENTRY32 pe={0};pe.dwSize=sizeof(pe);DWORD pid=0;
 if(Process32First(s,&pe))do{
  if(lstrcmpiA(pe.szExeFile,"I Wanna Be The Boshy.exe"))continue;
  HANDLE m=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pe.th32ProcessID);MODULEENTRY32 me={0};me.dwSize=sizeof(me);
  if(Module32First(m,&me)&&!lstrcmpiA(me.szExePath,exe)){pid=pe.th32ProcessID;base=(uintptr_t)me.modBaseAddr;}
  CloseHandle(m);
 }while(Process32Next(s,&pe));CloseHandle(s);
 if(!pid){fprintf(stderr,"Exact private game not found\n");return 3;}
 proc=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION,FALSE,pid);
 if(!proc)return 4;
 printf("{\"ready\":true,\"pid\":%lu,\"base\":%llu}\n",(unsigned long)pid,(unsigned long long)base);fflush(stdout);
 char line[2048];
 while(fgets(line,sizeof(line),stdin)){
  if(!strncmp(line,"quit",4))break;
  uint32_t a=app(),r=run();
  if(a<0x10000||r<0x10000||scene()>1000){puts("{\"error\":\"state unavailable\"}");fflush(stdout);continue;}
  if(!strncmp(line,"snapshot",8)){
   uint32_t stats=u32(base+0x59a98);
   printf("{\"scene\":%u,\"legacy_frame\":%u,\"app\":%u,\"run\":%u,\"stats\":%u,\"next\":%u,\"next_data\":%u,\"objects\":%u,\"object_list\":%u,\"globals\":%u,\"active_array\":%u,\"frame_count\":%u,\"viewport\":[%d,%d]}\n",scene(),u32(u32(a+0x268)+0xa8),a,r,stats,u16(r+0x30),u32(r+0x38),u32(r+0x40),u32(r+0x1278),u32(a+0x25c),u32(a+0x268),u32(r+0xd0),(int)u32(r+0xb0),(int)u32(r+0xb4));
  }else if(!strncmp(line,"window",6)){
   HWND h=(HWND)(uintptr_t)u32(r+0x10);RECT rect;POINT origin={0,0};
   if(GetClientRect(h,&rect)&&ClientToScreen(h,&origin))printf("{\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld,\"scroll_x\":%d,\"scroll_y\":%d}\n",(long)origin.x,(long)origin.y,(long)rect.right,(long)rect.bottom,(int)u32(r+0x190),(int)u32(r+0x194));
   else puts("{\"error\":\"window unavailable\"}");
  }else if(!strncmp(line,"read ",5)){
   unsigned long long addr;unsigned n;
   if(sscanf(line+5,"%llx %u",&addr,&n)!=2||n>65536){puts("{\"error\":\"bad read\"}");}
   else {unsigned char *buf=malloc(n?n:1);if(rd(addr,buf,n)){printf("{\"hex\":\"");for(unsigned i=0;i<n;i++)printf("%02x",buf[i]);puts("\"}");}else puts("{\"error\":\"read failed\"}");free(buf);}
  }else if(!strncmp(line,"character ",10)){
   unsigned addr;char hex[1025];unsigned char data[512];int ok=1;
   if(sscanf(line+10,"%x %1024s",&addr,hex)!=2||strlen(hex)!=1024||u32(addr)!=0x424d4e31||u32(addr+4)!=1||u32(addr+1648)!=u32(addr+1652))ok=0;
   for(unsigned j=0;ok&&j<512;j++){unsigned x;if(sscanf(hex+j*2,"%2x",&x)!=1)ok=0;else data[j]=x;}
   if(ok)ok=wr(addr+1652,data+4,472)&&wr(addr+1648,data,4);
   printf("{\"written\":%s}\n",ok?"true":"false");
  }else if(!strncmp(line,"exit ",5)){
   unsigned addr,expected,op,lo,hi;int ok=0;
   if(sscanf(line+5,"%x %u %u %u %u",&addr,&expected,&op,&lo,&hi)==5&&u32(addr)==0x424d4e31&&u32(addr+4)==1&&u32(addr+2144)==0x42584531&&scene()==expected&&expected>1&&expected<64&&op<=3){
    uint32_t status=u32(addr+2156),masks[2]={lo,hi};
    if(op==1&&status<256&&u32(addr+60)==1&&u16(r+0x30)==0){uint32_t off=0;ok=wr(addr+2156,&off,4)&&wr(addr+2148,masks,8)&&run()==r&&scene()==expected&&wr(addr+2156,&op,4);}
    else if(op!=1)ok=wr(addr+2156,&op,4);
   }
   printf("{\"written\":%s}\n",ok?"true":"false");
  }else if(!strncmp(line,"menu ",5)){
   unsigned addr,off,val;
   if(sscanf(line+5,"%x %u %u",&addr,&off,&val)!=3||u32(addr)!=0x424d4e31||u32(addr+4)!=1||(off!=24&&off!=40&&off!=60)||(off==60&&val>4))puts("{\"error\":\"menu precondition\"}");
   else printf("{\"written\":%s}\n",wr(addr+off,&val,4)?"true":"false");
  }else if(!strncmp(line,"value ",6)){
   unsigned oi;char group[64],key[64],old[64],value[64],cur[64];
   if(sscanf(line+6,"%u %63s %63s %63s %63s",&oi,group,key,old,value)!=5||(oi>8192)){puts("{\"error\":\"bad value request\"}");}
   else{
    uint32_t node=ini_node(oi,group,key),len=node?u32(node+0x34):999,p=node?u32(node+0x30):0;
    if(!node||len!=strlen(old)||len!=strlen(value)||len>31||!rd(p,cur,len)||memcmp(cur,old,len)){puts("{\"error\":\"value precondition\"}");}
    else printf("{\"written\":%s}\n",wr(p,value,len)?"true":"false");
   }
  }else if(!strncmp(line,"scene ",6)){
   unsigned dest,expected;uint16_t command=3;
   if(sscanf(line+6,"%u %u",&dest,&expected)!=2||dest>60||dest==54||scene()!=expected||u16(r+0x30)!=0){puts("{\"error\":\"scene precondition\"}");}
   else{uint32_t data=dest|0x8000;int ok=wr(r+0x38,&data,4)&&run()==r&&scene()==expected&&wr(r+0x30,&command,2);printf("{\"requested\":%s,\"destination\":%u}\n",ok?"true":"false",dest);}
  }else if(!strncmp(line,"quit",4))break;
  else puts("{\"error\":\"unknown command\"}");
  fflush(stdout);
 }
 CloseHandle(proc);return 0;
}
