/* Starts ONLY the exact laboratory executable suspended, installs its
 * verified game-loop detour, then resumes. Original EXE stays unchanged.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "runtime_root.h"
int main(int argc,char**argv){
 char exe[MAX_PATH],directory[MAX_PATH];if(!runtime_root(exe,directory))return 2;
 if(argc!=2||strlen(argv[1])!=60||strncmp(argv[1],"native-runs/",12)||strcmp(argv[1]+44,"/reward_hook.bin"))return 3;
 for(int j=12;j<44;j++)if(!((argv[1][j]>='0'&&argv[1][j]<='9')||(argv[1][j]>='a'&&argv[1][j]<='f')))return 3;
 FILE *f=fopen(argv[1],"rb");if(!f)return 3;
 unsigned char*blob=malloc(524288);if(!blob)return 4;size_t n=fread(blob,1,524288,f);fclose(f);if(n<128||n==524288)return 4;
 char cmd[512];snprintf(cmd,sizeof(cmd),"\"%s\"",exe);
 STARTUPINFOA si={0};si.cb=sizeof(si);PROCESS_INFORMATION pi={0};
 fprintf(stderr,"Creating suspended lab game\n");fflush(stderr);
 if(!CreateProcessA(exe,cmd,NULL,NULL,FALSE,CREATE_SUSPENDED,NULL,directory,&si,&pi)){fprintf(stderr,"CreateProcess %lu\n",(unsigned long)GetLastError());return 5;}
 fprintf(stderr,"Created child %lu\n",(unsigned long)pi.dwProcessId);fflush(stderr);
 int rc=6;SIZE_T got=0;unsigned char original[6],expected[]={0x51,0xa1,0x94,0x9a,0x45,0x00};
 if(!ReadProcessMemory(pi.hProcess,(void*)0x4365a0,original,6,&got)||got!=6||memcmp(original,expected,6))goto fail;
 fprintf(stderr,"Signature verified\n");fflush(stderr);
 void *remote=VirtualAllocEx(pi.hProcess,NULL,n,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
 if(!remote||(uintptr_t)remote>0xffffffff)goto fail;
 if(!WriteProcessMemory(pi.hProcess,remote,blob,n,&got)||got!=n)goto fail;
 DWORD old;if(!VirtualProtectEx(pi.hProcess,(void*)0x4365a0,6,PAGE_EXECUTE_READWRITE,&old))goto fail;
 unsigned char jump[6]={0xe9,0,0,0,0,0x90};int32_t rel=(int32_t)((uintptr_t)remote-0x4365a5);memcpy(jump+1,&rel,4);
 if(!WriteProcessMemory(pi.hProcess,(void*)0x4365a0,jump,6,&got)||got!=6)goto fail;
 DWORD ignored;if(!VirtualProtectEx(pi.hProcess,(void*)0x4365a0,6,old,&ignored))goto fail;
 if(!FlushInstructionCache(pi.hProcess,remote,n)||!FlushInstructionCache(pi.hProcess,(void*)0x4365a0,6))goto fail;
 if(ResumeThread(pi.hThread)==(DWORD)-1)goto fail;
 printf("{\"pid\":%lu,\"hook\":%llu,\"size\":%zu}\n",(unsigned long)pi.dwProcessId,(unsigned long long)(uintptr_t)remote,n);
 CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return 0;
 fail:fprintf(stderr,"Labor hook setup failed (%lu); unfinished child closed.\n",(unsigned long)GetLastError());
 TerminateProcess(pi.hProcess,1);CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return rc;
}
