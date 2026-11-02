"""Bounded startup isolation for generated private bank variants."""
import os,subprocess,time,json,struct
from pathlib import Path
from visuals.scenery_pack import App
from visuals.fusion25 import rebuild, property_bank, write_properties, image_bank, write_images, StoredImage
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/Fusion-Scenery-20261023'
case=Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests/rebuilt-castlevania-routes-scenery')
base=App('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-actors.exe')
changed=App(OUT/'Boshy-scenery.exe')
env=os.environ.copy();env.update(WINEPREFIX='/home/thxel/Games/clickteam-fusion-developer',WINEDEBUG='-all')
wine='/home/thxel/.local/share/lutris/runners/wine/wine-staging-11.2-x86_64/bin/wine'
results=[]
original_props=property_bank(base.payload(0x2256),base.payload(0x2257))
new_props=property_bank(changed.payload(0x2256),changed.payload(0x2257))
variants=[]
props=list(original_props)
b=bytearray(props[94]);struct.pack_into('<H',b,16,56);props[94]=bytes(b)
pb,px=write_properties(props)
variants.append(('existing-image',{0x2256:pb,0x2257:px}))
images,n=image_bank(changed.payload(0x6666),changed.payload(0x5555));orig_images,_=image_bank(base.payload(0x6666),base.payload(0x5555))
for row in json.loads((OUT/'audit.json').read_text())['changed']:
 h=row['new_image'];im=orig_images[row['original_image']];head=bytearray(im.header);struct.pack_into('<I',head,0,h+1);images[h]=StoredImage(h,bytes(head),im.packed)
ib,ix=write_images(images,n)
props=list(original_props);props[94]=new_props[94];pb,px=write_properties(props)
variants.append(('clone-original',{0x2256:pb,0x2257:px,0x6666:ib,0x5555:ix}))
for label,replacements in variants:
 path=case/('diagnostic-'+label+'.exe');path.write_bytes(rebuild(base,replacements))
 assert not any(r.endswith(' I Wanna Be The Boshy') for r in subprocess.check_output(['wmctrl','-lp'],text=True).splitlines())
 with (OUT/('diagnostic-'+label+'.log')).open('w') as log:
  p=subprocess.Popen([wine,str(path)],cwd=case,env=env,stdout=log,stderr=log)
  window=None;started=time.monotonic()
  while time.monotonic()-started<15:
   rows=[r.split(None,4) for r in subprocess.check_output(['wmctrl','-lp'],text=True).splitlines() if r.endswith(' I Wanna Be The Boshy')]
   if rows:
    assert len(rows)==1;window=rows[0][0];break
   if p.poll() is not None:break
   time.sleep(.2)
  result={'variant':label,'window':window,'exit':p.poll(),'seconds':round(time.monotonic()-started,2)}
  if window:
   subprocess.run(['wmctrl','-ic',window],check=True);p.wait(timeout=10)
  else:
   assert p.poll() is not None,'Unexpected startup hang'
  results.append(result);print(result,flush=True)
(OUT/'start-diagnostic-reference.json').write_text(json.dumps(results,indent=2))
