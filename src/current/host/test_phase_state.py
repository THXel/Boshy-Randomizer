"""Regression checks for the fixture mistakes found in live phase testing."""
import struct,unittest
from phase_state import State
class Memory:
 def __init__(self,data):
  self.ready={'base':0x400000};self.bank=0x10000;self.run=0x20000;self.data=bytearray(data+b'\0'*64000)
 def u32(self,address):
  if address==0x400000+0x59a9c:return self.run
  if address==0x20000+0x88:return self.bank
  if address==self.run+0x40:return 20000
  if address==0x3000:return self.run
  raise AssertionError(address)
 def read(self,address,n):return bytes(self.data[address-self.bank:address-self.bank+n])
 def cmd(self,line):
  op,addr,old,new=line.split();assert op=='cas32';addr,old,new=map(lambda s:int(s,16),(addr,old,new));off=addr-self.bank
  if struct.unpack_from('<I',self.data,off)[0]!=old:return {'written':False}
  struct.pack_into('<I',self.data,off,new);return {'written':True}
def action(name,unicode):
 raw=bytes.fromhex('3600ffff0e00000000000000020014002d000000ffff03000a004469650000000000140016000000ffff00000a000100000000000000')
 if unicode:
  raw=bytearray(raw[:26]+name.encode('utf-16le')+b'\0'*6+raw[34:])
  struct.pack_into('<H',raw,0,len(raw));struct.pack_into('<H',raw,14,24);struct.pack_into('<H',raw,18,1);struct.pack_into('<H',raw,24,14)
 else:raw=bytearray(raw);raw[26:29]=name.encode()
 return bytes(raw)
def row(ace,unicode,condition=False):
 head=bytearray(16 if unicode else 14);struct.pack_into('<h',head,0,-len(head)-len(ace));head[2 if condition else 3]=1
 return bytes(head)+ace
class PhaseStateTests(unittest.TestCase):
 def check_format(self,unicode):
  # Name remains intact, including cached Unicode loop index; only repeat count changes.
  data=b''.join(row(action(n,unicode),unicode) for n in ('Die','die','Foo'))
  data+=row(action('Die',unicode),unicode,condition=True)
  s=State.__new__(State);s.b=Memory(data);s.run=0x20000;s.unicode=unicode;s.writes=[];s.run_globals=[0x3000]
  first=s.protect();self.assertEqual(len(first['patched_calls']),2)
  expected=bytearray(data)
  for write in s.writes:
   self.assertEqual(write['old'],1);self.assertEqual(write['new'],0)
   struct.pack_into('<I',expected,write['address']-s.b.bank,0)
  self.assertEqual(s.b.data[:len(data)],expected)
  again=s.protect();self.assertEqual(again['already_patched'],2);self.assertEqual(again['patched_calls'],[])
 def test_runheader_relocation_after_restart(self):
  for unicode in (False,True):
   with self.subTest(unicode=unicode):
    s=State.__new__(State);s.b=Memory(b'');s.run=0x20000;s.unicode=unicode;s.run_globals=[0x3000]
    s.b.run=0x23000;s.refresh();self.assertEqual(s.run,0x23000)
 def test_original_case_variants_and_idempotency(self):self.check_format(False)
 def test_unicode_cached_loop_and_case_variants(self):self.check_format(True)
if __name__=='__main__':unittest.main()
