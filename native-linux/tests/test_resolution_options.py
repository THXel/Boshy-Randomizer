import unittest,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ResolutionTests(unittest.TestCase):
 def test_fit_and_monotonic_presets(self):
  source='''#include <assert.h>
#include "resolution_policy.h"
int main(void){
 assert(resolution_limit(3840,2120)==2780);
 assert(resolution_limit(3840,2160)==2832);
 assert(resolution_limit(5120,2880)==2880);
 assert(resolution_limit(1920,1040)==1340);
 for(int h=600;h<=4320;h+=120)for(int w=800;w<=7680;w+=160){
  unsigned limit=resolution_limit(w,h);assert(limit<=2880&&limit%4==0&&limit<=(unsigned)w&&limit*3/4+35<=(unsigned)h);
  unsigned p=320;int count=0;
  while(p<limit){unsigned n=resolution_next(p,limit,1);assert(n>p&&n<=limit&&n%4==0);p=n;assert(++count<30);}
  while(p>320){unsigned n=resolution_next(p,limit,-1);assert(n<p&&n>=320);p=n;}
 }
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'policy.c').write_text(source)
   subprocess.run(['gcc','-Wall','-Wextra','-Werror','-I',str(ROOT),str(p/'policy.c'),'-o',str(p/'policy')],check=True)
   subprocess.run([str(p/'policy')],check=True)
