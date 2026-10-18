"""Headless controller: all visible interaction lives in Boshy's native window."""
import json,time,traceback
from lab import BASE,game_window,key
from native_session import real_store
from native_models import slot_available
from native_profiles import activate,finish
from native_player import Player,transient_read_error,poll_delay
from menu_runtime import MenuGame,EndingDelay,SlotSelectionError
from menu_model import Menu
from menu_render import Renderer
from native_tracker import Publisher
import subprocess,os

from menu_navigation import load_slot
from loading_screen import LoadingScreen
from loading_destination import for_selection,for_frame
from game_focus import activate_game
from debug_runtime import DebugRuntime
from live_session import LiveSession

def select_requested_slot(game,model,debug):
 selected=model.requested_slot;model.requested_slot=None
 try:game.select_slot(selected)
 except SlotSelectionError as error:
  # A missed selection acknowledgement is recoverable UI feedback, not a crash.
  debug.error(error)
  h=game.header()
  if h[7]==0 and h[9] in (1,2,3):model.select(h[9])
  from ui_i18n import tr
  model.message=tr('Speicherplatzauswahl nicht bestätigt. Bitte erneut auswählen.')
  model.action=None;model.focus=0;model.dirty=True
  return False
 model.select(selected);model.message='';model.focus=0;model.dirty=True
 return True

def update_result(player,tracker,model,view,renderer,debug):
 """Credits change scenes without gameplay state; keep the game and result alive."""
 model.pump()
 try:
  if player.bridge.snapshot()['scene']<=1:
   # F2 ends the presentation session, not the durable victory record.
   view.write(60,0);model.page='slots';model.focus=0
   model.action=('result_back',model.slot,None);model.dirty=True
   return True
  for event in view.events():model.event(*event)
  if model.action is not None:
   view.write(60,0);return True
  if model.dirty:renderer.draw(model);view.refresh()
  result=player.poll();tracker.run(player,result)
  debug.commands();debug.tick('finished',player,model)
 except (KeyError,StopIteration,RuntimeError) as error:
  if not transient_read_error(error):raise
  return False
 return True

def run():
 s=real_store();game=None;player=None;cover=None;renderer=Renderer(BASE);tracker=Publisher(s)
 from host_platform import python_command
 subprocess.Popen(python_command('tracker_entry.py') if os.name=='nt' else [str(BASE/'start-live-tracker.sh')],cwd=BASE,env={**os.environ,'BOSHY_TRACKER_HOST':str(os.getpid())},stdout=subprocess.DEVNULL,stderr=open(BASE/'evidence/tracker-process.log','a',encoding='utf-8'),start_new_session=True,**__import__('host_platform').child_options())
 with s.lock():
  s._stopped();finish(s)
  from intro_cast import prepare as prepare_intro
  prepare_intro(BASE)
  from runtime_versions import recover_all
  recover_all(s);model=Menu(s);renderer.draw(model);debug=DebugRuntime(s)
  try:
   while True:
    if game is None:
     game=MenuGame(position=cover.position if cover else None)
     if cover:cover.restore_game();cover.close();cover=None
     activate_game()
    model.action=None
    while s.game_running() and model.action is None:
     tracker.menu();model.pump();debug.commands();debug.tick('menu',model=model)
     for event in game.events():model.event(*event)
     if model.requested_slot is not None:
      select_requested_slot(game,model,debug)
     if model.dirty:renderer.draw(model);game.write(60,1 if model.page=='slots' else 2);game.refresh()
     time.sleep(.035)
    if not s.game_running():game.bridge.close();game=None;return
    action,slot,settings=model.action
    if action=='result_back':continue
    if action=='quit':game.close();game=None;return
    debug.tick('loading',model=model,force=True)
    cover=LoadingScreen(BASE,slot,destination=for_selection(s,slot,action,settings))
    model.page='loading';model.message='Dein Spielstand wird geladen …';renderer.draw(model);game.refresh();time.sleep(.12)
    tracker.menu(loading=True)
    try:
     if action=='delete':
      with LiveSession(s,game).transaction() as live:
       s.delete(slot);live.reload(slot)
      model.message=f'Speicherplatz {slot} gelöscht und gesichert.'
      cover.restore_game();cover.close();cover=None
     elif action in ('new','resume'):
      if action=='new' and not slot_available(s,slot):raise ValueError('Dieser Speicherplatz ist belegt. Bitte zuerst im Menü löschen.')
      live=LiveSession(s,game)
      with live.transaction():
       m=s.prepare(settings['seed'],slot,settings['options']) if action=='new' else s.current(slot)
       if action=='new':model.consume_seed()
       hot=bool(m and m['status']=='ready' and live.compatible(m))
       if hot:activate(s,m);live.bind(m)
       elif not m or m['status']!='ready':live.clear();live.reload(slot)
      if m and m['status']=='ready':
       s.validate(m);player=Player(s,m)
       if hot:
        game.write(60,0);time.sleep(.1);player.start(game=game);game=None
       else:
        # Incompatible archived native code retains its audited cold-start path.
        game.close();game=None;activate(s,m);player.start(position=cover.position)
       player.bridge.cmd(f"menu {player.metadata['menu']:x} 60 1")
       cover.restore_game();cover.close();cover=None;activate_game()
       last_read=time.monotonic();back=False;ending=EndingDelay();keep_draft=False
       while s.game_running():
        poll_started=time.monotonic()
        model.pump()
        try:
         if player.bridge.snapshot()['scene']<=1:back=True;break
         # Tab belongs to the separate tracker; gameplay is never covered or paused.
         view=MenuGame.__new__(MenuGame);view.bridge=player.bridge;view.address=player.metadata['menu']
         for event in view.events():
          if event[0]==7:model.event(*event)
         debug.commands(player);result=player.poll();tracker.run(player,result);debug.tick('running',player,model);last_read=time.monotonic()
         if result.get('completed'):
          if ending.ready(result['frame'],time.monotonic()):
           player.insights.pause()
           if player.shots:player.shots.pause()
           model.open_result(player.m);model.action=None;renderer.draw(model);view.generation=view.header()[10];view.write(60,4);view.refresh()
           while s.game_running() and model.action is None:
            if update_result(player,tracker,model,view,renderer,debug):last_read=time.monotonic()
            time.sleep(.035)
           keep_draft=model.page=='new';back=s.game_running();break
        except (KeyError,StopIteration,RuntimeError) as e:
         if not s.game_running():break
         if transient_read_error(e) and time.monotonic()-last_read<5:time.sleep(.1);continue
         raise
        time.sleep(poll_delay(poll_started))
       if not back and not (player.folder/'summary.json').exists():debug.error(RuntimeError('Spiel während eines aktiven Laufs geschlossen; Ursache unbekannt.'))
       if back:cover=LoadingScreen(BASE,0,'Zurück zum Hauptmenü …',destination=for_frame(BASE,2))
       tracker.menu(loading=True);metadata=dict(player.metadata);player.close();player=None
       if not back:finish(s);return
       game=MenuGame.attach(metadata);game.title()
       with LiveSession(s,game).transaction() as live:
        live.clear();finish(s);live.reload()
       cover.restore_game();cover.close();cover=None;activate_game()
      else:
       # Existing ordinary saves retain their original game rules and profile.
       game.write(60,0);time.sleep(.1);load_slot(game.bridge,game.address,slot);game.write(60,1)
       cover.restore_game();cover.close();cover=None;activate_game()
       while s.game_running() and game.bridge.snapshot()['scene']>1:model.pump();debug.commands();debug.tick('ordinary',model=model);time.sleep(.1)
       if not s.game_running():game.bridge.close();game=None;return
       cover=LoadingScreen(BASE,0,'Zurück zum Hauptmenü …',destination=for_frame(BASE,2))
       game.title()
       cover.restore_game();cover.close();cover=None;activate_game()
      model.message='Lauf gespeichert.'
    except Exception as error:
     debug.error(error);debug.tick('error',model=model,force=True)
     traceback.print_exc()
     if player:player.close(close_game=True);player=None
     if game:game.close();game=None
     finish(s);model.message='Angehalten: '+str(error)
    if not locals().get('keep_draft',False):model.page='slots'
    keep_draft=False;model.reload();renderer.draw(model)
    if game:game.write(60,1 if model.page=='slots' else 2);game.refresh()
  except Exception as error:
   debug.error(error)
   raise
  finally:
   debug.close();model.close();tracker.pause()
   if player:player.close(close_game=True)
   if game:game.close()
   finish(s);tracker.stopped()
   if cover:cover.close()
if __name__=='__main__':run()
