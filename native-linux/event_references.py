"""Read-only canonical view of verified boss conditions after cosmetic OI rebasing.
Frozen rule readers retain their exact original hashes. Never changes game memory.
"""
import hashlib,json,struct
from pathlib import Path
ROWS=json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))
for row in ROWS:
 row['data']=bytes.fromhex(row['raw'])
 if hashlib.sha256(row['data']).hexdigest()!=row['sha256']:raise ValueError('Boss reference catalogue checksum')

def indices(raw):
 """Yield only MMF object cache fields, excluding IDs, values and opcodes."""
 at=14
 for _ in range(raw[2]+raw[3]):
  n,kind,code,oi=struct.unpack_from('<HhhH',raw,at);end=at+n
  if n<14 or end>len(raw):raise ValueError('Event bounds')
  if kind>=0:yield at+8,oi
  p=at+(16 if code<0 else 14)
  for _ in range(raw[at+12]):
   size,typ=struct.unpack_from('<HH',raw,p)
   if size<4 or p+size>end:raise ValueError('Parameter bounds')
   if typ==1:
    if size<10:raise ValueError('Object parameter bounds')
    yield p+4,struct.unpack_from('<H',raw,p+6)[0]
   if typ in (15,22,23,27,28,45,46,52,53,54,59,62):
    e=p+6
    while e+4<=p+size and struct.unpack_from('<I',raw,e)[0]:
     kind,code,step=struct.unpack_from('<hhH',raw,e)
     if step<6 or e+step>p+size:raise ValueError('Expression bounds')
     if kind>0:
      if step<10:raise ValueError('Expression reference bounds')
      yield e+8,struct.unpack_from('<H',raw,e+6)[0]
     e+=step
    if e+4>p+size:raise ValueError('Expression terminator')
   p+=size
  at=end
 if at!=len(raw):raise ValueError('Event length')

def canonical(actual,row,lookup):
 expected=row['data']
 if len(actual)!=len(expected):return actual
 out=bytearray(actual)
 for offset,oi in indices(expected):
  if oi>=32768 or out[offset:offset+2]==expected[offset:offset+2]:continue
  index=struct.unpack_from('<H',out,offset)[0]
  if lookup(index)!=oi:return actual
  out[offset:offset+2]=expected[offset:offset+2]
 return expected if out==expected else actual

class ReaderBridge:
 def __init__(self,bridge,snap):self.bridge=bridge;self.snap=snap;self.bank=None
 def __getattr__(self,name):return getattr(self.bridge,name)
 def read(self,address,size):
  raw=self.bridge.read(address,size)
  rows=[r for r in ROWS if r['scene']==self.snap['scene'] and r['size']==size]
  if not rows:return raw
  if self.bank is None:self.bank=struct.unpack('<I',self.bridge.read(self.snap['run']+0x88,4))[0]
  row=next((r for r in rows if self.bank+r['offset']==address),None)
  if row is None or raw==row['data']:return raw
  frame=struct.unpack('<I',self.bridge.read(0x459a98,4))[0]
  if frame<65536:return raw
  table=struct.unpack('<I',self.bridge.read(frame+0x480,4))[0];count=struct.unpack('<H',self.bridge.read(frame+0x8f2,2))[0]
  if table<65536 or not 0<count<=2048:return raw
  data=self.bridge.read(table,count*122)
  return canonical(raw,row,lambda index:struct.unpack_from('<H',data,index*122)[0] if index<count else None)
