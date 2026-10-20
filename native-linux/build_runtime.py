"""Rebuild all native payloads. Requires gcc-multilib, binutils and MinGW-w64."""
from pathlib import Path
import subprocess,tempfile,os,json,hashlib,re
B=Path(__file__).resolve().parent

def bind_native_hashes(base):
 """Bind integrity checks to this build, including the named Extras constant."""
 hashes={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in ('native_intro_guard.dll','native_menu_polished.dll','native_extras.dll')}
 p=base/'intro_guard.py';text=p.read_text(encoding='utf-8')
 replacements=[(r"GUARD_HASH='[^']+'",'GUARD_HASH='+repr(hashes['native_intro_guard.dll'])),
               (r"EXTRAS_CURRENT='[^']+'",'EXTRAS_CURRENT='+repr(hashes['native_extras.dll'])),
               (r"(native_menu_polished\.dll'\).read_bytes\(\)\).hexdigest\(\)!=')[^']+",r'\g<1>'+hashes['native_menu_polished.dll'])]
 for pattern,value in replacements:
  text,count=re.subn(pattern,value,text)
  if count!=1:raise RuntimeError('Native integrity binding must match exactly once: '+pattern)
 p.write_text(text,encoding='utf-8')

def build():
 from build_context import build as build_context
 from elf_to_coff import convert
 build_context(Path('/__BOSHY_RUNTIME__'))
 cc=os.environ.get('MINGW_CC','x86_64-w64-mingw32-gcc')
 def run(args,**kw):return subprocess.run(args,cwd=B,check=True,**kw)
 with tempfile.TemporaryDirectory(prefix='boshy-build-') as folder:
  work=Path(folder)
  for name in ('bridge','slot_reward_launcher'):
   run([cc,'-O2','-Wall','-Wextra','-static','-Wl,--no-insert-timestamp','-o',str(B/(name+'.exe')),str(B/(name+'.c'))])
  for name,base,opt in [('native_menu',0x68000000,'-Os'),('native_intro_guard',0x69000000,'-Os'),('native_menu_polished',0x6a000000,'-Os'),('native_extras',0x68000000,'-O2')]:
   obj=work/(name+'.o');coff=work/(name+'.coff.o')
   run(['gcc','-m32',opt,'-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-ffreestanding','-fno-pie','-fno-stack-protector','-fno-asynchronous-unwind-tables','-I',str(B),'-c',str(B/(name+'.c')),'-o',str(obj)])
   convert(obj,coff)
   run(['ld','-mi386pe','--dll','--no-insert-timestamp','--image-base',hex(base),'--entry','_DllMain','--export-all-symbols','--disable-auto-import','--enable-reloc-section','-o',str(B/(name+'.dll')),str(coff)])
  entry=work/'entry.o';run(['gcc','-m32','-c','slot_reward_entry.S','-o',str(entry)])
  for name in ('slot_reward_hook','slot_reward_extras'):
   obj=work/(name+'.o');elf=work/(name+'.elf')
   run(['gcc','-m32','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-ffreestanding','-fno-pie','-fno-stack-protector','-fno-asynchronous-unwind-tables','-fno-jump-tables','-c',name+'.c','-o',str(obj)])
   run(['ld','-m','elf_i386','-T','hook.ld',str(entry),str(obj),'-o',str(elf)])
   run(['objcopy','-O','binary',str(elf),str(B/(name+'.bin'))])
   symbols=run(['nm','-n',str(elf)],capture_output=True,text=True).stdout;offset=int(next(l.split()[0] for l in symbols.splitlines() if l.endswith(' context')),16)
   output='slot_reward_symbols.json' if name=='slot_reward_hook' else 'slot_reward_extras_symbols.json'
   (B/output).write_text(json.dumps({'context_offset':offset},indent=2)+'\n', encoding='utf-8')
 bind_native_hashes(B)
 print('Built portable launchers, four DLLs and two hook payloads.')
if __name__=='__main__':build()
