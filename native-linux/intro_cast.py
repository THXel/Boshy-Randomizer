"""Cosmetic intro cast extracted from the user's verified game, never bundled assets."""
import hashlib,json,logging,random,struct,zlib
from pathlib import Path
from PIL import Image
# Original object IDs in the supported game build. Gameplay and seed RNG are untouched.
CAST={194:'The Kid',197:'Mario',198:'Ash',206:'Kirby',208:'Link',219:'Dig Dug',
      227:'Ness',244:'Megaman',250:'Kid Icarus',251:'Luigi',255:'Solgryn',
      256:'Dark Boshy',257:'Sonic',258:'Excite Bike',259:'Meat Boy',260:'Quadrick',
      265:'Ice Climbers',266:'Simon',272:'Nyan Cat',285:'Yoshi',289:'Quote',294:'Arthur'}
TARGETS=(18,21,23)
MAGIC=b'BRI1'
def chunks(data,start,end):
 while start<end:
  if start+8>end:raise ValueError('Truncated chunk')
  kind,flags,size=struct.unpack_from('<HHI',data,start);start+=8
  if start+size>end:raise ValueError('Chunk bounds')
  payload=data[start:start+size];start+=size
  if flags==1:
   if len(payload)<8:raise ValueError('Compressed chunk header')
   length,packed=struct.unpack_from('<II',payload)
   if packed!=len(payload)-8 or length>2_000_000:raise ValueError('Chunk size')
   payload=zlib.decompress(payload[8:])
   if len(payload)!=length:raise ValueError('Chunk length')
  elif flags:raise ValueError('Unsupported chunk format')
  yield kind,payload

def animations(data):
 offset=struct.unpack_from('<H',data,6)[0]
 if not 70<=offset<len(data)-4:raise ValueError('Animation offset')
 bank=data[offset:];size,count=struct.unpack_from('<HH',bank)
 if size!=len(bank) or not 1<=count<=256:raise ValueError('Animation bank')
 result={}
 for anim in range(count):
  at=struct.unpack_from('<H',bank,4+anim*2)[0]
  if not at:continue
  for direction in range(32):
   rel=struct.unpack_from('<H',bank,at+direction*2)[0]
   if not rel:continue
   pos=at+rel;frames=struct.unpack_from('<H',bank,pos+6)[0]
   if not 1<=frames<=256:raise ValueError('Animation frame count')
   result[anim,direction]=struct.unpack_from('<'+'H'*frames,bank,pos+8)
 return result

def read_game(path,expected,*,extra_images=()):
 data=Path(path).read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Unsupported game checksum')
 # This exact build has a PAME container after its packed runtime libraries.
 start=2495611
 if data[start:start+4]!=b'PAME':raise ValueError('Game container')
 objects={};image_bank=None
 for kind,payload in chunks(data,start+16,len(data)):
  if kind==0x2229:
   oid=None
   for part,body in chunks(payload,4,len(payload)):
    if part==0x4444:oid=struct.unpack_from('<H',body)[0]
    elif part==0x4446 and oid in (*TARGETS,*CAST):objects[oid]=animations(body)
  elif kind==0x6666:image_bank=payload
 if set(objects)!=set(TARGETS)|set(CAST) or image_bank is None:raise ValueError('Incomplete cast')
 images={};count=struct.unpack_from('<I',image_bank)[0];pos=4
 wanted={h for anims in objects.values() for frames in anims.values() for h in frames}|set(extra_images)
 for _ in range(count):
  handle,length,packed=struct.unpack_from('<III',image_bank,pos);pos+=12
  if pos+packed>len(image_bank):raise ValueError('Image bounds')
  if handle in wanted:
   if length>2_000_000:raise ValueError('Image size')
   raw=zlib.decompress(image_bank[pos:pos+packed])
   if len(raw)!=length:raise ValueError('Image length')
   images[handle]=raw
  pos+=packed
 if pos!=len(image_bank) or wanted-set(images):raise ValueError('Incomplete images')
 return objects,images

def image(raw,*,max_side=256):
 width,height=struct.unpack_from('<HH',raw,12);mode,flags=raw[16:18]
 if not (0<width<=max_side and 0<height<=max_side) or mode!=4 or flags not in (0,4,16):raise ValueError('Image format')
 stride=(width+1)//2*2*3;size=stride*height;pos=32;pixels=bytearray()
 if flags&4:
  while len(pixels)<size:
   count=raw[pos];pos+=1
   if not count:raise ValueError('Early RLE terminator')
   if count<128:chunk=raw[pos:pos+3];pos+=3;pixels.extend(chunk*count)
   else:count-=128;pixels.extend(raw[pos:pos+3*count]);pos+=3*count
   if pos>len(raw) or len(pixels)>size:raise ValueError('Invalid RLE')
 else:pixels=raw[pos:pos+size];pos+=size
 if len(pixels)!=size:raise ValueError('Image pixel count')
 out=Image.frombytes('RGB',(width,height),bytes(pixels),'raw','BGR',stride).convert('RGBA')
 if flags&16:
  # Alpha rows use DWORD alignment in this runtime.
  alpha_stride=(width+3)//4*4;alpha=raw[pos:pos+alpha_stride*height]
  if len(alpha)!=alpha_stride*height:raise ValueError('Alpha size')
  out.putalpha(Image.frombytes('L',(width,height),alpha,'raw','L',alpha_stride))
 else:
  transparent=tuple(raw[28:31]);out.putdata([(*p[:3],0 if p[:3]==transparent else 255) for p in out.getdata()])
 return out

def choose(previous,rng=None):
 rng=rng or random.SystemRandom();chosen=[]
 for slot in range(3):
  old=previous[slot] if isinstance(previous,list) and len(previous)==3 else None
  choices=[oid for oid in CAST if oid!=old and oid not in chosen]
  chosen.append(rng.choice(choices))
 return chosen

def make_plan(folder,objects,images,chosen):
 folder.mkdir(parents=True,exist_ok=True);records=[]
 for target,source in zip(TARGETS,chosen):
  for (anim,direction),original in objects[target].items():
   frames=objects[source].get((anim,direction)) or objects[source].get((anim,0)) or objects[source][0,0]
   for frame,old_handle in enumerate(original):
    old=images[old_handle];w,h=struct.unpack_from('<HH',old,12);hx,hy=struct.unpack_from('<hh',old,20)
    graphic=image(images[frames[frame*len(frames)//len(original)]]);box=graphic.getbbox()
    if box:graphic=graphic.crop(box)
    graphic.thumbnail((w,h),Image.Resampling.NEAREST)
    canvas=Image.new('RGBA',(w,h));canvas.alpha_composite(graphic,((w-graphic.width)//2,h-graphic.height))
    name=f'{len(records):02d}.png';canvas.save(folder/name)
    path=('..\\menu-runtime\\intro\\'+name).encode('ascii')
    records.append(struct.pack('<6I2i96s',target,anim,direction,frame,w,h,hx,hy,path))
 if len(records)!=32:raise ValueError('Unexpected intro layout')
 return MAGIC+struct.pack('<I',len(records))+b''.join(records)

def prepare(base,*,rng=None):
 """Call once under the host lock, not on internal game reloads. Fail to vanilla."""
 from lab import EXPECTED
 from native_session import atomic
 root=Path(base)/'menu-runtime';root.mkdir(parents=True,exist_ok=True);plan=root/'intro.bin'
 try:
  try:previous=json.loads((root/'intro-last.json').read_text()).get('cast')
  except (OSError,ValueError,AttributeError):previous=None
  from intro_themes import IMAGE_IDS,prepare as prepare_theme
  chosen=choose(previous,rng);objects,images=read_game(Path(base)/'IWBTB/I Wanna Be The Boshy.exe',EXPECTED,extra_images=IMAGE_IDS)
  blob=make_plan(root/'intro',objects,images,chosen);atomic(plan,blob)
  prepare_theme(base,images)
  atomic(root/'intro-last.json',json.dumps({'version':1,'cast':chosen,'names':[CAST[x] for x in chosen]}).encode())
  return chosen
 except Exception:
  plan.unlink(missing_ok=True);(root/'theme.bin').unlink(missing_ok=True);logging.exception('Cosmetic intro unavailable; keeping original sprites')
  return None
