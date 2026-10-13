"""Convert two opaque RGBA trophies to BMP for the engine's native colour key.
RGB pixels are unchanged. The game uses the top-left background colour as the
transparent key, as it does for its non-alpha images. Original assets stay intact.
"""
from pathlib import Path
from PIL import Image
NAMES=('Simon Belmont','Spike')
def build(base=None):
 base=Path(base or Path(__file__).resolve().parent);target=base/'native-icons';target.mkdir(exist_ok=True)
 for name in NAMES:
  with Image.open(base/'Custom/trophies'/f'{name}.png') as source:
   assert source.size==(32,32) and source.mode=='RGBA'
   assert source.getchannel('A').getextrema()==(255,255)
   rgb=source.convert('RGB');path=target/f'{name}.bmp';rgb.save(path)
   with Image.open(path) as result:assert list(result.getdata())==list(rgb.getdata())
if __name__=='__main__':build()
