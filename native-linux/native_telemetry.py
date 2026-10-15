"""Small read-only native diagnostics; resolve exports once per game process."""
import struct
from pathlib import Path

def export_rva(path,name):
 data=Path(path).read_bytes();pe=struct.unpack_from('<I',data,60)[0]
 if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid PE')
 count=struct.unpack_from('<H',data,pe+6)[0];opt=pe+24
 if struct.unpack_from('<H',data,opt)[0]!=0x10b:raise ValueError('Expected PE32')
 sections=opt+struct.unpack_from('<H',data,pe+20)[0]
 def offset(rva):
  for i in range(count):
   size,addr,rawsize,raw=struct.unpack_from('<4I',data,sections+i*40+8)
   if addr<=rva<addr+rawsize:return raw+rva-addr
  raise ValueError('Export bounds')
 directory=offset(struct.unpack_from('<I',data,opt+96)[0])
 n,functions,names,ordinals=struct.unpack_from('<4I',data,directory+24)
 if n>4096:raise ValueError('Export count')
 for i in range(n):
  at=offset(struct.unpack_from('<I',data,offset(names)+i*4)[0])
  if data[at:at+128].split(b'\0')[0].decode('ascii')==name:
   ordinal=struct.unpack_from('<H',data,offset(ordinals)+i*2)[0]
   return struct.unpack_from('<I',data,offset(functions)+ordinal*4)[0]
 raise ValueError('Missing export '+name)

class NativeReader:
 def __init__(self,player):self.player=player;self.base=None;self.offsets={}
 def read(self,name,count):
  if self.base is None:
   from lab import game_window
   rows=[line.split() for line in Path(f'/proc/{game_window().pid}/maps').read_text().splitlines() if line.endswith('/native_menu_polished.dll')]
   if not rows:return None
   self.base=min(int(r[0].split('-')[0],16)-int(r[2],16) for r in rows)
  if name not in self.offsets:self.offsets[name]=export_rva(self.player.store.base/'native_menu_polished.dll',name)
  return struct.unpack('<'+'I'*count,self.player.bridge.read(self.base+self.offsets[name],count*4))

class MusicReader:
 def __init__(self,player):
  self.player=player;self.reader=NativeReader(player)
  music=player.rules.module('music_randomizer')
  self.tracks=music.TRACKS;self.mapping=music.mapping(player.m['seed'])
 def read(self):
  if not self.player.m['options'].get('extras',{}).get('music'):return None
  try:
   state=self.reader.read('MusicState',6)
   if not state or state[0]!=0x42524d31 or state[1]!=1 or not state[3] or state[4] or state[5]>=len(self.tracks):return None
   original=self.tracks[state[5]]
   return dict(original=original,track=self.mapping[original],changes=state[3])
  except (OSError,ValueError,RuntimeError,struct.error):return None
