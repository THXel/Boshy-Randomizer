#define main baseline_main
#include "fast_exit_harness.c"
#undef main
#include <stdlib.h>
int main(int argc,char**argv){
 baseline_main();volatile U*c=exit_control();int cases=0;
 for(int i=1;i+1<argc;i+=2){
  U origin=atoi(argv[i]),target=atoi(argv[i+1]);q->scene=origin;q->enabled=1;*(U*)(uintptr_t)(r+0xd0)=50;
  exit_tick(r,origin);c[1]=target<32?1U<<target:0;c[2]=target>=32?1U<<(target-32):0;c[3]=1;exit_tick(r,origin);
  command=3;dest=0x8000|target;exit_action(0);assert(c[3]==256+target&&exitWaiting&&guardOn);
  exit_action(0);assert(*(unsigned short*)(uintptr_t)(r+0x30)==0);
  c[3]=2;exit_tick(r,origin);assert(!exitWaiting&&*(U*)(uintptr_t)(r+0x38)==dest);
  *(unsigned short*)(uintptr_t)(r+0x30)=0;cases++;
 }
 printf("Verified %d configured native exits\n",cases);return 0;
}
