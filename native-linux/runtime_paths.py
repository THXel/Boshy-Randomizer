"""Private, per-user runtime and exact Wine process ownership."""
from pathlib import Path
import os,shutil
BASE=Path(__file__).resolve().parent
EXPECTED='dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806'
RUNNER=os.environ.get('BOSHY_WINE') or shutil.which('wine') or 'wine'
def environment():
 return {**os.environ,'WINEPREFIX':str(BASE/'wineprefix'),'BOSHY_RUNTIME_ROOT':str(BASE),'WINEDEBUG':'-all','WINEDLLOVERRIDES':'mscoree,mshtml=','WINEESYNC':'0','WINEFSYNC':'0','WINE_OPENGL_DRIVER':'glx','__GL_GSYNC_ALLOWED':'0','__GL_VRR_ALLOWED':'0'}
def command(name,*args):return [RUNNER,str(BASE/name),*map(str,args)]
def verify_root():
 if not (BASE/'installed-runtime.json').is_file():raise RuntimeError('Start Boshy Randomizer from the applications menu first.')
 if (BASE/'IWBTB').is_symlink() or (BASE/'wineprefix').is_symlink():raise RuntimeError('The game and Wine prefix must belong to this randomizer.')
