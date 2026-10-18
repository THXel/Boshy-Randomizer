"""Chest timing tolerates only MMF's cosmetic OI-list relocation."""
import platform,shutil,subprocess,tempfile,unittest,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import intro_guard
class ExtrasRelocation(unittest.TestCase):
 @unittest.skipUnless(platform.system()=='Linux' and shutil.which('gcc'),'native patch harness')
 def test_rebased_cache_preserves_identity_and_atomic_validation(self):
  source=(ROOT/'extras_native_tail.c').read_text();code=source[:source.index('static int extras_session')]
  harness=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint32_t U;typedef unsigned short H;typedef unsigned char B;
static H h(const B*p){return *(const H*)p;}
'''+code+r'''
static B bank[1000000],before[1000000];
int main(void){const struct ExtraPatch*first=0;U checked=0;
 for(U i=0;i<sizeof(patches)/sizeof(*patches);i++){const struct ExtraPatch*p=&patches[i];if(p->scene!=26||p->flag!=1024)continue;memcpy(bank+p->offset,p->old,p->len);if(p->len==46&&h(p->old+2)==2&&(short)h(p->old+4)==-27){*(H*)(bank+p->offset+8)=h(p->old+8)+1;if(!first)first=p;checked++;}}
 assert(first&&checked>1);memcpy(before,bank,sizeof(bank));
 assert(ExtrasPatch(bank,26,1024));assert(ExtrasPatch(bank,26,1024));
 assert(h(bank+first->offset+8)==h(first->old+8)+1); /* never overwrite the rebased index */
 memcpy(bank,before,sizeof(bank));bank[first->offset+6]^=1;memcpy(before,bank,sizeof(bank));
 assert(!ExtrasPatch(bank,26,1024));assert(!memcmp(bank,before,sizeof(bank))); /* wrong object: no partial writes */
 bank[first->offset+6]^=1;bank[first->offset+4]^=1;assert(!ExtrasPatch(bank,26,1024)); /* wrong opcode */
 bank[first->offset+4]^=1;bank[first->offset+38]^=1;assert(!ExtrasPatch(bank,26,1024)); /* wrong value */
 bank[first->offset+38]^=1;*(H*)(bank+first->offset+8)=0xffff;assert(!ExtrasPatch(bank,26,1024)); /* impossible cache */
 return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   c=Path(folder)/'test.c';exe=Path(folder)/'test';c.write_text(harness)
   subprocess.run(['gcc','-w','-I',str(ROOT),str(c),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
 def test_only_known_legacy_builds_get_runtime_fix(self):
  legacy=next(iter(intro_guard.EXTRAS_LEGACY))
  with tempfile.TemporaryDirectory() as folder:
   base=Path(folder)/'current';saved=Path(folder)/'saved';base.mkdir();saved.mkdir()
   (base/'native_extras.dll').write_bytes(b'current');(saved/'native_extras.dll').write_bytes(b'legacy')
   hashes={b'current':intro_guard.EXTRAS_CURRENT,b'legacy':legacy,b'unknown':'f'*64}
   with patch('intro_guard.hashlib.sha256',side_effect=lambda data:SimpleNamespace(hexdigest=lambda:hashes[data])):
    self.assertEqual(intro_guard.extras_path(base,saved),base/'native_extras.dll');self.assertTrue(intro_guard.extras_compatible(base,saved))
    (saved/'native_extras.dll').write_bytes(b'unknown');self.assertEqual(intro_guard.extras_path(base,saved),saved/'native_extras.dll');self.assertFalse(intro_guard.extras_compatible(base,saved))
if __name__=='__main__':unittest.main()
