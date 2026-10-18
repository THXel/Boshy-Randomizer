"""Exercise native reward rebinding against every real mixed-chest record."""
import json,platform,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import mixed_rewards
class ContextReferences(unittest.TestCase):
 @unittest.skipUnless(platform.system()=='Linux' and shutil.which('gcc'),'native harness')
 def test_all_records_and_atomic_rejection(self):
  plan=json.loads((ROOT/'slot_reward_plan.json').read_text())
  data=mixed_rewards.context(plan,mixed_rewards.assignments('references-test',plan),'a'*32)
  code=(ROOT/'context_rebase.c').read_text().replace('#include "native_oi.h"','static int runtime_oi_index(U oi){return oi<32768?(oi+17)%19000:-1;}')
  harness=r'''#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
typedef uint32_t U;typedef int32_t I;
static unsigned char context[310000],run[512],before[310000];
static struct {U error;}*q;
static int samebytes(const unsigned char*a,const unsigned char*b,U n){return !memcmp(a,b,n);}
'''+code+r'''
int main(int argc,char**argv){(void)argc;FILE*f=fopen(argv[1],"rb");assert(f);assert(fread(context,1,304284,f)==304284);fclose(f);
 q=(void*)(context+304284);*(U*)(run+0x88)=0x10000;*(U*)(run+0xd0)=100;
 U count=*(U*)(context+48);RefLocation*ls=(void*)(context+124);
 for(U i=0;i<count;i++){context_rebase((U)(uintptr_t)run,ls[i].scene);assert(!q->error);assert(!ReferenceState[3]);}
 assert(ReferenceState[1]>10&&ReferenceState[2]>100);
 /* A later malformed record must prevent every earlier staged write. */
 RefLocation*l=&ls[count-1];*(unsigned short*)(l->grant+8)=0;*(unsigned short*)l->extra=0;
 memcpy(before,context,sizeof(context));*(U*)(run+0xd0)=0;context_rebase((U)(uintptr_t)run,l->scene);
 assert(q->error==46&&ReferenceState[3]==1);assert(!memcmp(before,context,304284));return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   f=Path(folder);(f/'context').write_bytes(data);(f/'test.c').write_text(harness)
   subprocess.run(['gcc','-no-pie','-w',str(f/'test.c'),'-o',str(f/'test')],check=True)
   subprocess.run([str(f/'test'),str(f/'context')],check=True)
if __name__=='__main__':unittest.main()
