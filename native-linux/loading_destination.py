"""Describe the actual saved scene using the existing Boshy icon catalogue."""
import json
from pathlib import Path
from native_models import ini,location,FRAME_NAMES
from native_targets import BOSSES

def for_frame(base,frame):
 frame=int(frame);folder=Path(base)/'loading-icons'
 catalog=json.loads((folder/'index.json').read_text());entry=catalog.get(str(frame),{})
 name=location(frame) if frame in FRAME_NAMES else entry.get('name',location(frame))
 kind='Boss' if frame in {v[1] for v in BOSSES.values()}|{46,54} else 'Level'
 if frame<=2:kind='Menü';name='Hauptmenü'
 return dict(frame=frame,name=name,kind=kind,icon=str(folder/entry.get('icon','boshy.webp')))

def for_selection(store,slot,action,settings=None):
 if action=='new':
  frame=3
  if settings:
   from run_settings import decode,route
   from native_level_route import catalogue
   seed,options=decode(settings['seed'],settings['options']);planned=route(seed,options)
   if planned and options['levels']:
    pool=catalogue(json.loads((store.base/'INI/positions.json').read_text()));pool.update(json.loads((store.base/'native_spots.json').read_text()))
    from beta_catalogue import EXTRA_POINTS
    pool.update(EXTRA_POINTS);frame=pool[planned[0]]['frame']
 elif action=='resume':
  data=ini(store,store.base/'IWBTB'/f'SaveFile{slot}.ini')
  frame=int(data.get('positions',{}).get('frame',2))
 else:frame=2
 return for_frame(store.base,frame)
