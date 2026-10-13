"""Headless controller: all visible interaction lives in Boshy's native window."""
import json,time,traceback
from lab import BASE,game_window,key
from native_session import real_store
from native_profiles import activate,finish
from native_player import Player,transient_read_error
from menu_runtime import MenuGame
from menu_model import Menu
from menu_render import Renderer
from native_tracker import Publisher
import subprocess,os

from menu_navigation import load_slot
from loading_screen import LoadingScreen
from loading_destination import for_selection,for_frame
from game_focus import activate_game
from debug_runtime import DebugRuntime

def run():
 s=real_store();game=None;player=None;cover=None;renderer=Renderer(BASE);tracker=Publisher(s)
 subprocess.Popen([str(BASE/'start-live-tracker.sh')],cwd=BASE,env={**os.environ,'BOSHY_TRACKER_HOST':str(os.getpid())},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 with s.lock():
  s._stopped();finish(s)
  from runtime_versions import recover_all
  recover_all(s);model=Menu(s);renderer.draw(model);debug=DebugRuntime(s)
  try:
   while True:
    if game is None:
     game=MenuGame(position=cover.position if cover else None)
     if cover:cover.restore_game();cover.close();cover=None;activate_game()
    model.action=None
    while s.game_running() and model.action is None:
     tracker.menu();model.pump();debug.commands();debug.tick('menu',model=model)
     for event in game.events():model.event(*event)
     if model.dirty:renderer.draw(model);game.write(60,1 if model.page=='slots' else 2);game.refresh()
     time.sleep(.035)
    if not s.game_running():game.bridge.close();game=None;return
    action,slot,settings=model.action
    if action=='result_back':continue
    if action=='quit':game.close();game=None;return
    debug.tick('loading',model=model,force=True)
    cover=LoadingScreen(BASE,slot,destination=for_selection(s,slot,action,settings))
    model.page='loading';model.message='Dein Spielstand wird geladen …';renderer.draw(model);game.refresh();time.sleep(.12)
    tracker.menu(loading=True);game.close();game=None
    try:
     if action=='delete':
      s.delete(slot);model.message=f'Speicherplatz {slot} gelöscht und gesichert.'
     elif action in ('new','resume'):
      if action=='new' and (s.base/'IWBTB'/f'SaveFile{slot}.ini').exists() and (s.base/'IWBTB'/f'SaveFile{slot}.ini').stat().st_size>0:raise ValueError('Dieser Speicherplatz ist belegt. Bitte zuerst im Menü löschen.')
      m=s.prepare(settings['seed'],slot,settings['options']) if action=='new' else s.current(slot)
      if m and m['status']=='ready':
       s.validate(m);activate(s,m);player=Player(s,m);player.start(position=cover.position)
       player.bridge.cmd(f"menu {player.metadata['menu']:x} 60 1")
       cover.restore_game();cover.close();cover=None;activate_game()
       last_read=time.monotonic();back=False;result_since=None;keep_draft=False
       while s.game_running():
        model.pump()
        try:
         if player.bridge.snapshot()['scene']<=1:back=True;break
         # Tab belongs to the separate tracker; gameplay is never covered or paused.
         view=MenuGame.__new__(MenuGame);view.bridge=player.bridge;view.address=player.metadata['menu']
         view.events()
         debug.commands(player);result=player.poll();tracker.run(player,result);debug.tick('running',player,model);last_read=time.monotonic()
         if result.get('completed'):
          if result_since is None:result_since=time.monotonic()
          if result['frame']==47 or time.monotonic()-result_since>=5:
           player.insights.pause()
           if player.shots:player.shots.pause()
           model.open_result(player.m);model.action=None;renderer.draw(model);view.generation=view.header()[10];view.write(60,4);view.refresh()
           while s.game_running() and model.action is None:
            model.pump()
            for event in view.events():model.event(*event)
            if model.dirty:renderer.draw(model);view.refresh()
            tracker.run(player,result)
            debug.commands();debug.tick('finished',player,model);time.sleep(.035)
           keep_draft=model.page=='new';back=s.game_running();break
        except (KeyError,StopIteration,RuntimeError) as e:
         if not s.game_running():break
         if transient_read_error(e) and time.monotonic()-last_read<5:time.sleep(.1);continue
         raise
        time.sleep(.08)
       if back:cover=LoadingScreen(BASE,0,'Zurück zum Hauptmenü …',destination=for_frame(BASE,2))
       tracker.menu(loading=True);player.close(close_game=True);player=None;finish(s)
       if not back:return
      else:
       # Existing ordinary saves retain their original game rules and profile.
       game=MenuGame(enabled=False,position=cover.position);load_slot(game.bridge,game.address,slot);game.write(60,1)
       cover.restore_game();cover.close();cover=None;activate_game()
       while s.game_running() and game.bridge.snapshot()['scene']>1:model.pump();debug.commands();debug.tick('ordinary',model=model);time.sleep(.1)
       if not s.game_running():game.bridge.close();game=None;return
       cover=LoadingScreen(BASE,0,'Zurück zum Hauptmenü …',destination=for_frame(BASE,2))
       game.close();game=None
      model.message='Lauf gespeichert.'
    except Exception as error:
     debug.error(error);debug.tick('error',model=model,force=True)
     traceback.print_exc()
     if player:player.close(close_game=True);player=None
     if game:game.close();game=None
     finish(s);model.message='Angehalten: '+str(error)
    if not locals().get('keep_draft',False):model.page='slots'
    keep_draft=False;model.reload();renderer.draw(model)
  finally:
   debug.close();model.close();tracker.pause()
   if player:player.close(close_game=True)
   if game:game.close()
   finish(s);tracker.stopped()
   if cover:cover.close()
if __name__=='__main__':run()
