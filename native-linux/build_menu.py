from pathlib import Path
import subprocess,struct
B=Path(__file__).resolve().parent
r=lambda a:subprocess.run(a,cwd=B,check=True)
def build():
 r(['gcc','-m32','-Os','-Wall','-Wextra','-Wno-misleading-indentation','-ffreestanding','-fno-pie','-fno-stack-protector','-fno-asynchronous-unwind-tables','-c','native_menu.c','-o','native_menu.elf.o'])
 from elf_to_coff import convert
 convert(B/'native_menu.elf.o',B/'native_menu.coff.o')
 r(['ld','-mi386pe','--dll','--image-base','0x68000000','--entry','_DllMain','--export-all-symbols','--disable-auto-import','--enable-reloc-section','-o','native_menu.dll','native_menu.coff.o'])
if __name__=='__main__':build()
