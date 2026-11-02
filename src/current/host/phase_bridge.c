/* Private, local test helper. Reads and compare-writes only the explicitly named BoshySceneTests process. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static HANDLE proc;
static int rd(uintptr_t a,void *v,size_t n){SIZE_T got;return ReadProcessMemory(proc,(void*)a,v,n,&got)&&got==n;}
static uint32_t u32(uintptr_t a){uint32_t v=0;rd(a,&v,4);return v;}
static uint16_t u16(uintptr_t a){uint16_t v=0;rd(a,&v,2);return v;}
int main(int argc,char **argv){
 const char *prefix="C:\\BoshySceneTests\\";
 if(argc!=2||strncmp(argv[1],prefix,strlen(prefix))||strstr(argv[1],".."))return 2;
 HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);PROCESSENTRY32 pe={0};pe.dwSize=sizeof(pe);DWORD pid=0;uintptr_t base=0;
 if(Process32First(snap,&pe))do{if(lstrcmpiA(pe.szExeFile,"Boshy.exe"))continue;
 HANDLE ms=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pe.th32ProcessID);MODULEENTRY32 me={0};me.dwSize=sizeof(me);
 if(Module32First(ms,&me)&&!lstrcmpiA(me.szExePath,argv[1])){if(pid)return 3;pid=pe.th32ProcessID;base=(uintptr_t)me.modBaseAddr;}CloseHandle(ms);
 }while(Process32Next(snap,&pe));CloseHandle(snap);if(!pid)return 4;
 proc=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION,FALSE,pid);if(!proc)return 5;
 printf("{\"pid\":%lu,\"base\":%llu}\n",(unsigned long)pid,(unsigned long long)base);fflush(stdout);
 char line[256];while(fgets(line,sizeof(line),stdin)){
 unsigned long long addr;unsigned n;
 if(!strncmp(line,"quit",4))break;
 unsigned expected,replacement;
 if(sscanf(line,"cas32 %llx %x %x",&addr,&expected,&replacement)==3){
  SIZE_T wrote=0;int ok=u32(addr)==expected&&WriteProcessMemory(proc,(void*)(uintptr_t)addr,&replacement,4,&wrote)&&wrote==4;
  printf("{\"written\":%s}\n",ok?"true":"false");fflush(stdout);continue;
 }
 if(sscanf(line,"read %llx %u",&addr,&n)==2&&n<=65536){unsigned char *p=malloc(n?n:1);if(rd(addr,p,n)){printf("{\"hex\":\"");for(unsigned i=0;i<n;i++)printf("%02x",p[i]);puts("\"}");}else puts("{\"error\":\"read\"}");free(p);}
 else if(!strncmp(line,"scan",4)){
  MEMORY_BASIC_INFORMATION m;uintptr_t a=0x10000;unsigned count=0;
  puts("{\"objects\":[");
  while(a<0x80000000&&VirtualQueryEx(proc,(void*)a,&m,sizeof(m))){uintptr_t end=(uintptr_t)m.BaseAddress+m.RegionSize;if(end<=a)break;
   if(m.State==MEM_COMMIT&&m.Type==MEM_PRIVATE&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&m.RegionSize<0x4000000){
    unsigned char *b=malloc(m.RegionSize);if(b&&rd((uintptr_t)m.BaseAddress,b,m.RegionSize))for(size_t i=0;i+160<=m.RegionSize;i+=4){
     uint32_t size=*(uint32_t*)(b+i+4),run=*(uint32_t*)(b+i+8);
     if(size<160||size>8192||run<0x10000||*(uint16_t*)(b+i+24)!=2||*(uint16_t*)(b+i+18)>20000)continue;
     if(!u32(run)||u32(run+0x40)>30000||u32(run+0x40)<100)continue;
     printf("%s{\"ptr\":%llu,\"size\":%u,\"run\":%u,\"oi\":%u,\"x\":%d,\"y\":%d,\"hex\":\"",count++?",":"",(unsigned long long)((uintptr_t)m.BaseAddress+i),size,run,*(uint16_t*)(b+i+18),*(int*)(b+i+76),*(int*)(b+i+84));for(unsigned j=0;j<160;j++)printf("%02x",b[i+j]);puts("\"}");
    }free(b);
   }a=end;
  }printf("],\"count\":%u}\n",count);
 }else puts("{\"error\":\"command\"}");fflush(stdout);
 }
 CloseHandle(proc);return 0;
}
