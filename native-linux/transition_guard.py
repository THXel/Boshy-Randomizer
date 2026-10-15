"""Bounded native pause while committing an already selected destination."""
import struct,time
from contextlib import contextmanager

@contextmanager
def protect(bridge,address):
 magic,active=struct.unpack('<II',bridge.read(address+2136,8))
 if magic!=0x42544731:raise RuntimeError('Übergangsschutz fehlt; Randomizer bitte vollständig neu starten.')
 # Mode 3 is a hidden native pause. It blocks game input and gameplay events,
 # expires after two seconds, and releases itself when the engine changes scene.
 bridge.cmd(f'menu {address:x} 60 3')
 try:
  deadline=time.monotonic()+.6
  while time.monotonic()<deadline:
   if struct.unpack('<I',bridge.read(address+2140,4))[0]==1:break
   time.sleep(.005)
  else:raise RuntimeError('Übergangsschutz wurde nicht bestätigt.')
  yield
 finally:
  bridge.cmd(f'menu {address:x} 60 1')
