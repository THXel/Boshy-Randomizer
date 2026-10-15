"""Small looping background details and stable contrast, independent of run RNG."""
import math,struct
from PIL import Image,ImageDraw,ImageFilter,ImageOps
FRAMES=24
INTERVAL_MS=250

def contrast_mask(background):
 """Fixed in background coordinates; never pulses with the decorative frames."""
 w,h=background.size;mask=Image.new('L',(w,h));pixels=[]
 # The native image begins at world x=-112. Text sits at screen x=0..226.
 for y in range(h):
  top=max(0.,1-y/64)
  panel_y=min(1.,max(0.,(y-178)/22))
  for x in range(w):
   left=min(1.,max(0.,(350-x)/28))
   pixels.append(round(255*max(.70*top,.78*left*panel_y)))
 mask.putdata(pixels)
 # Bright scenery receives more darkening; dark artwork keeps its detail.
 luminance=ImageOps.grayscale(background)
 strength=luminance.point(lambda n:min(255,100+n))
 from PIL import ImageChops
 return ImageChops.multiply(mask,strength)

def frame(background,theme,index,mask):
 """A six-second seamless loop. No moving objects or collision changes."""
 phase=(index%FRAMES)/FRAMES*2*math.pi;w,h=background.size
 layer=Image.new('RGBA',(w,h));d=ImageDraw.Draw(layer)
 if theme in (0,1):
  # Soft distant cloud wisps, moving only a few pixels per step.
  for i,(x,y,width) in enumerate(((190,90,130),(530,142,155),(745,70,100))):
   shift=9*math.sin(phase+i*2);yy=y+2*math.cos(phase+i)
   d.ellipse((x+shift-width/2,yy-6,x+shift+width/2,yy+6),fill=(207,226,239,24 if theme==0 else 19))
  layer=layer.filter(ImageFilter.GaussianBlur(5))
 elif theme==2:
  for i in range(22):
   x=125+(i*97)%625;y=45+(i*61)%215
   alpha=round(30+42*(.5+.5*math.sin(phase+i*1.7)))
   d.point((x,y),fill=(205,221,248,alpha))
   if i%5==0:
    d.line((x-1,y,x+1,y),fill=(205,221,248,alpha//2));d.line((x,y-1,x,y+1),fill=(205,221,248,alpha//2))
 elif theme==3:
  for i in range(20):
   x=130+(i*83)%630+12*math.sin(phase+i*.7);y=235+(i*37)%170+3*math.cos(phase+i)
   alpha=round(10+18*(.5+.5*math.sin(phase+i)))
   d.line((x,y,x+2,y),fill=(242,206,151,alpha))
 else:raise ValueError('Unknown atmosphere theme')
 result=Image.alpha_composite(background.convert('RGBA'),layer)
 shade=Image.new('RGBA',result.size,(0,0,0,0));shade.putalpha(mask)
 return Image.alpha_composite(result,shade)

def prepare(folder,background,theme):
 from native_session import atomic
 mask=contrast_mask(background)
 for i in range(FRAMES):frame(background,theme,i,mask).save(folder/f'e{i:02d}.png')
 atomic(folder/'effects.bin',b'BRF1'+struct.pack('<5I',FRAMES,theme,INTERVAL_MS,*background.size))
 # The static fallback uses exactly the same contrast as the animation.
 return frame(background,theme,0,mask)
