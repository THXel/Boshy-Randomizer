"""Common worker for the native laboratory GUI and integration tests."""
import json,time,struct,subprocess
from native_session import real_store,write_json
from lab import BASE,Bridge,game_window,ini_object_ids,ini_items,key,IniReadInProgress,ini_integer_fields
from window_position import wait_for_game
from launch_slot_reward import launch
from gastly_route_lab import read_state,move,RestartWatcher
from native_level_route import GastlyRoute,eligible
from mixed_rewards import CONTEXT_SIZE
from run_extras import flags as extra_flags,enabled as extra_enabled
from transition_guard import protect

def transient_read_error(error):
    if isinstance(error,(KeyError,StopIteration,IniReadInProgress)):return True
    if not isinstance(error,RuntimeError):return False
    if str(error) in ('Scene changed during observation','Inventory not yet saved','Scene transition in progress'):return True
    return bool(error.args and isinstance(error.args[0],dict) and error.args[0].get('error') in ('state unavailable','read failed'))

class SlotSwitchRequested(Exception):
    def __init__(self,manifest):self.manifest=manifest;super().__init__('Speicherplatz wird gewechselt.')

class Player:
    def __init__(self,store,manifest):
        self.store=store;self.m=manifest;self.folder=store.root/manifest['run_id']
        self.bridge=None;self.route=None;self.watch=None;self.metadata=None;self.last=None
        self.changed_at=time.monotonic();self.last_scene=None;self.last_validation=0;self.progress=None;self.in_menu=False;self.icon_object=None;self.icon_scene=None
    def start(self,cancel=None,auto=True,position=None):
        self.store._stopped();self.store.validate(self.m)
        self.metadata=launch(self.store,self.m);self.metadata['menu']=self.metadata['context']+CONTEXT_SIZE;write_json(self.folder/'process.json',self.metadata)
        wait_for_game(position)
        self.bridge=Bridge()
        if auto:
            from menu_navigation import load_slot
            load_slot(self.bridge,self.metadata['menu'],self.m['slot'],cancel)
        # Leave menu selection to the player; adopt the run actually loaded.
        deadline=time.monotonic()+120;loaded_since=None
        while time.monotonic()<deadline:
            if cancel and cancel.is_set():raise RuntimeError('Start abgebrochen.')
            try:snapshot=self.bridge.snapshot()
            except RuntimeError as e:
                if e.args and isinstance(e.args[0],dict) and e.args[0].get('error')=='state unavailable':
                    time.sleep(.1);continue
                raise
            if snapshot['scene']>1:
                if loaded_since is None:loaded_since=time.monotonic()
                try:
                    oi=ini_object_ids(self.bridge)['Ini++'];checks=ini_items(self.bridge,'randochecks',oi)
                    loaded=self.store.by_id(checks['sessionid']['value'])
                    if loaded['run_id']!=self.m['run_id']:raise SlotSwitchRequested(loaded)
                    break
                except (KeyError,StopIteration):
                    if time.monotonic()-loaded_since>5:raise ValueError('Dieser Speicherplatz ist nicht vorbereitet. Im Starter zuerst einen neuen Lauf für diesen Slot anlegen.')
                    time.sleep(.1);continue
            else:loaded_since=None
            time.sleep(.08)
        else:raise RuntimeError('Bitte einen vorbereiteten Speicherplatz im Spielmenü wählen.')
        self.save_name=f"SaveFile{self.m['slot']}.ini"
        write_json(self.folder/'process.json',self.metadata)
        self.bind(self.m)
        self.watch=RestartWatcher()
        from fast_exit import FastExit
        self.fast_exit=FastExit(self)
        deadline=time.monotonic()+5
        while True:
            try:return self.poll()
            except Exception as error:
                if not transient_read_error(error) or time.monotonic()>=deadline:raise
                time.sleep(.05)
    def bind(self,m):
        if self.route:self.route.close()
        self.ending_started=False
        self.m=m;self.folder=self.store.root/m['run_id'];self.save_name=f"SaveFile{m['slot']}.ini"
        from runtime_versions import Rules
        self.rules=Rules(self.store,m);v=self.rules.view
        self.spider=self.rules.module('spider_randomizer').SpiderCycle(self) if extra_enabled(m['options'],'spider') else None
        self.progress=self.rules.module('native_progress').Progress(v,m)
        self.beta_reader=self.rules.module('beta_bosses').Reader()
        self.mini_reader=self.rules.module('minibosses').Reader()
        from old_sonic import Reader as SonicReader,Gate as SonicGate
        self.sonic_reader=SonicReader();self.sonic_gate=SonicGate()
        self.rewards=self.rules.module('reward_journal').Observer(v,m)
        from run_insights import Insights
        self.insights=Insights(v,m)
        self.shots=self.rules.module('shot_cycle').ShotCycle(v,m) if m['options'].get('extras',{}).get('shot_mode','off')!='off' else None
        self.death_characters=self.rules.module('death_character').DeathCycle(v,m) if extra_enabled(m['options'],'death_character') else None
        self.characters=self.rules.module('character_cycle').CharacterCycle(v,m) if m['options']['characters'] else None
        if self.characters and m['options'].get('start_character','Auto')!='Auto':
            self.characters.data['choices']['0']=self.rules.module('run_settings').character(v.base,m['seed'],m['options'])
        self.route=self.rules.module('native_level_route').GastlyRoute(self.folder/'gastly.sqlite',run_id=m['run_id'],seed=m['seed'],game_hash=m['game_hash'],pool=m['pool'])
        if self.watch:self.watch.ready.clear();self.watch.pressed.clear()
        write_json(self.folder/'process.json',self.metadata);self.last_validation=0
    def can_transition(self):
        # Wine modal reward boxes own focus until the player acknowledges them.
        # Retain the pending destination; never close dialogs or reroll here.
        from PY import platform_windows as gw
        game=game_window();blocked=False
        for dialog in gw.getAllWindows():
            if dialog.pid!=game.pid or dialog._hWnd==game._hWnd:continue
            title=dialog.title
            if title in ('RANDOMIZER','Congratulations!') or title.upper().endswith('GET!'):
                blocked=True;break
        if self.progress.data.get('dialog_wait',False)!=blocked:
            self.progress.data['dialog_wait']=blocked
            self.progress.trace('transition-waiting' if blocked else 'transition-resumed',reason='reward-dialog')
            self.progress.save()
        return not blocked
    def hook(self):
        h=struct.unpack('<16I',self.bridge.read(self.metadata['context'],64))
        if h[0]!=0x42524832 or h[1]!=7:raise RuntimeError('Der native Patch wurde nicht bestätigt.')
        if h[2] in (3,4,5,6) or h[11]:raise RuntimeError('Der native Patch meldet einen Fehler. Der Lauf wurde angehalten.')
        if h[15]:raise RuntimeError('Eine native Belohnungsgrafik konnte nicht geladen werden. Bitte die Installation prüfen.')
        menu=struct.unpack('<16I',self.bridge.read(self.metadata['menu'],64))
        if menu[0]!=0x424d4e31 or menu[2]!=2 or menu[12] or menu[8]!=extra_flags(self.m['options']):raise RuntimeError('Menü oder Charakter-Tastensperre wurde nicht bestätigt.')
        return dict(status=h[2],scene=h[5],awards=h[10],errors=h[11],native_icons=h[13],icon_errors=h[15])
    def completed_result(self,frame):
        # The ending scenes have no Ini++ gameplay object. Once victory was
        # durably confirmed, presentation must not depend on gameplay memory.
        path=self.folder/'summary.json'
        if not path.exists():return None
        summary=json.loads(path.read_text())
        if summary.get('run_id')!=self.m['run_id'] or summary.get('completed') is not True:
            raise ValueError('Abschlussauswertung gehört nicht zu diesem Lauf.')
        if not getattr(self,'ending_started',False):
            self.insights.pause()
            if self.shots:self.shots.pause()
            self.watch.ready.clear();self.watch.pressed.clear();self.ending_started=True
        result={**(self.last or summary.get('live',{})),
                'run_id':self.m['run_id'],'slot':self.m['slot'],'seed':self.m['seed'],
                'frame':frame,'completed':True,
                'progress':{k:v for k,v in self.progress.data.items() if k!='transition_trace'},
                'stats':{'difficulty':str(summary.get('difficulty',self.m['options']['difficulty'])),
                         'deaths':str(summary['deaths']),
                         'timeseconds':str(summary.get('game_seconds',summary['seconds']))}}
        if result!=self.last:write_json(self.folder/'status.json',result)
        self.last=result
        return result

    def poll(self):
        if self.watch.error:raise RuntimeError('Die Neustarttaste kann nicht beobachtet werden.') from self.watch.error
        snap=self.bridge.snapshot()
        completed=self.completed_result(snap['scene']+1)
        if completed is not None:return completed
        if getattr(self,'spider',None):self.spider.observe()
        if snap['scene']<=1:
            if self.shots:self.shots.pause()
            self.insights.pause()
            self.watch.ready.clear();self.in_menu=True
            if self.last:return {**self.last,'frame':snap['scene']+1,'gastly_available':False,'pickup':None}
            raise KeyError('menu')
        if snap['scene']==20:
            if self.shots:self.shots.pause()
            self.insights.pause()
            self.watch.ready.clear();self.in_menu=True
            from native_profiles import snapshot
            snapshot(self.store,self.m)
            if self.last:return {**self.last,'pickup':None}
            raise KeyError('dresser')
        oi=ini_object_ids(self.bridge)['Ini++'];checks=ini_items(self.bridge,'randochecks',oi)
        if checks['sessionid']['value']!=self.m['run_id']:raise SlotSwitchRequested(self.store.by_id(checks['sessionid']['value']))
        s=read_state(self.bridge,self.save_name);after=self.bridge.snapshot()
        if (snap['scene'],snap['run'])!=(after['scene'],after['run']):raise RuntimeError('Scene changed during observation')
        hook=self.hook()
        self.rewards.poll()
        from native_profiles import snapshot
        # Keep the profile attached to the active run, never to the GUI selection.
        if time.monotonic()-self.last_validation>2:
            self.store.validate(self.m);snapshot(self.store,self.m);self.last_validation=time.monotonic()
        target=self.route.observe(**s,restart_pressed=self.watch.pressed.is_set(),next_target=lambda:self.progress.request(s['collectables'],s['frame'],'Gastly gefangen',{})) if self.m['options']['levels'] else None;rs=self.route.state()
        if rs['phase']=='caught' or self.progress.gate.won:self.watch.ready.set()
        else:self.watch.ready.clear()
        if target and not self.watch.down and s['settled'] and self.can_transition():
            time.sleep(.08);s=read_state(self.bridge,self.save_name)
            if s['settled'] and not self.watch.down:
                with protect(self.bridge,self.metadata['menu']):self.arrive(target)
                rs=self.route.state();s=read_state(self.bridge,self.save_name)
        # Native checkpoints and save-local achievements drive the level route.
        oi=ini_object_ids(self.bridge)['Ini++']
        def group(name):
            try:return {k:v['value'] for k,v in ini_items(self.bridge,name,oi).items()}
            except KeyError:return {}
        pos=group('positions');stats=group('stats');ach=group('achievements')
        if self.death_characters:self.death_characters.observe(stats,self.bridge,self.metadata['menu'])
        from native_models import ini
        disk=ini(self.store,self.store.base/'IWBTB'/self.save_name)
        saved_position=ini_integer_fields(pos,('frame','xpos','ypos'),required=True)
        disk_position=ini_integer_fields(disk.get('positions',{}),('frame','xpos','ypos'),required=True)
        position=(saved_position['xpos'],saved_position['ypos'])
        confirm=self.bridge.snapshot()
        if confirm['scene']!=s['frame']-1 or (not target and confirm['run']!=after['run']):raise RuntimeError('Scene changed during observation')
        self.debug_sample=dict(time=time.time(),frame=s['frame'],scene_tick=confirm['frame_count'],settled=s['settled'],checkpoint=position,live_collectables=s['collectables'],disk_collectables=s['disk_collectables'],live_achievements=ach,disk_achievements=disk.get('achievements',{}),saved_positions=pos,disk_positions=disk.get('positions',{}),restart_pressed=self.watch.pressed.is_set(),restart_down=self.watch.down)
        beta_sample=self.beta_reader.sample(self.bridge,confirm)
        self.debug_sample['beta_boss']=beta_sample
        mini_sample=self.mini_reader.sample(self.bridge,confirm) if self.m['options'].get('route_version',1)>=5 else None
        self.debug_sample['miniboss']=mini_sample
        sonic_sample=self.sonic_reader.sample(self.bridge,confirm)
        self.debug_sample['old_sonic']=sonic_sample
        if self.in_menu:self.progress.rebase(s['frame'],position);self.progress.pause();self.progress.entry_frame=None;self.in_menu=False
        if rs['phase'] not in ('armed','caught','pending'):
            from old_sonic import confirm as confirm_sonic
            sonic_won=confirm_sonic(self.progress,self.sonic_gate,sonic_sample,stats)
            dest=self.progress.observe(frame=s['frame'],position=position,collectables=s['collectables'],achievements=ach,disk_achievements=disk.get('achievements',{}),stats=stats,settled=s['settled'],disk_collectables=s['disk_collectables'],saved_frame=saved_position['frame'],disk_frame=disk_position['frame'],disk_position=(disk_position['xpos'],disk_position['ypos']),scene_tick=confirm['frame_count'],beta_sample=beta_sample,mini_sample=mini_sample,restart_pressed=self.watch.pressed.is_set() and not self.watch.down)
            captured=self.fast_exit.captured(s['frame'],stats)
            if captured and not dest:dest=self.fast_exit.request(captured,s['collectables'],stats)
            if sonic_won and not dest:dest=self.progress.request(s['collectables'],s['frame'],'Old Sonic besiegt (HP 0)',stats)
            if dest and self.can_transition():
                with protect(self.bridge,self.metadata['menu']):
                    if self.characters:self.characters.prepare(self.progress.data['index']+1,self.bridge,self.metadata['menu'])
                    p=self.progress.destination(dest)
                    move(self.bridge,{**self.m['pool'],dest:p},dest,self.save_name)
                    self.progress.arrive(dest,p['frame'],(p['x'],p['y']));self.watch.pressed.clear();self.watch.ready.clear()
                s=read_state(self.bridge,self.save_name)
        if rs['phase'] not in ('armed','caught','pending'):self.fast_exit.arm(s['frame'],stats)
        if self.shots:self.shots.observe(stats,self.progress.data['index'],self.bridge,self.metadata['menu'])
        ready=eligible(self.m['pool'],s['collectables'])
        result=dict(run_id=self.m['run_id'],slot=self.m['slot'],seed=self.m['seed'],frame=s['frame'],
                    awesomesauce=s['collectables'].get('awesomesauce','0'),gastly=s['collectables'].get('gastly','0'),
                    gastly_available='gastly_grass' in ready,route=rs,hook=hook,progress={k:v for k,v in self.progress.data.items() if k!='transition_trace'},completed=(self.folder/'summary.json').exists(),stats=stats)
        self.insights.observe(self.progress.data,stats,self.rules.module('reward_journal').claims(self.rules.view,self.m),s['collectables'],result['completed'])
        if result!=self.last:
            write_json(self.folder/'status.json',result)
            with (self.folder/'events.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
            self.last=result
        return result
    def arrive(self,target):
        p=self.m['pool'][target];s=read_state(self.bridge,self.save_name)
        oi=ini_object_ids(self.bridge)['Ini++'];pos=ini_items(self.bridge,'positions',oi)
        at_target=s['frame']==p['frame'] and all(int(pos[k]['value'])==v for k,v in [('frame',p['frame']),('xpos',p['x']),('ypos',p['y'])])
        if not at_target:
            if self.characters:self.characters.prepare(self.progress.data['index']+1,self.bridge,self.metadata['menu'])
            move(self.bridge,self.m['pool'],target,self.save_name)
        fresh=read_state(self.bridge,self.save_name);oi=ini_object_ids(self.bridge)['Ini++'];pos=ini_items(self.bridge,'positions',oi)
        if fresh['collectables'].get('gastly')!=fresh['disk_collectables'].get('gastly') or fresh['collectables'].get('gastly')!='1':raise RuntimeError('Gastly-Speicherung nicht bestätigt.')
        self.route.confirm_arrival(target,frame=fresh['frame'],position=(int(pos['xpos']['value']),int(pos['ypos']['value'])))
        self.progress.request(fresh['collectables'],fresh['frame'],'Gastly gefangen',{},target=target)
        self.progress.arrive(target,fresh['frame'],(int(pos['xpos']['value']),int(pos['ypos']['value'])))
        used_restart=self.watch.pressed.is_set()
        self.watch.pressed.clear();self.watch.ready.clear()
        write_json(self.folder/'gastly-arrival.json',dict(target=target,frame=fresh['frame'],position=[p['x'],p['y']],restart_pressed=used_restart,native_scene_requests=int(not at_target),extra_R_presses=0))
    def close(self,*,close_game=False):
        if getattr(self,'spider',None):self.spider.observe(force=True)
        if getattr(self,'shots',None):self.shots.pause()
        if getattr(self,'insights',None):self.insights.pause()
        if self.watch:self.watch.close();self.watch=None
        if self.bridge:
            try:self.bridge.close()
            except (BrokenPipeError,RuntimeError):pass
            self.bridge=None
        if self.route:self.route.close();self.route=None
        if close_game and self.store.game_running():
            import psutil
            w=game_window();p=psutil.Process(w.pid)
            # These acknowledgement dialogs block WM_DELETE on the owner window.
            from PY import platform_windows as gw
            for dialog in gw.getAllWindows():
                if dialog.pid==w.pid and dialog.title in ('RANDOMIZER','Congratulations!'):
                    dialog.activate();subprocess.run(['xdotool','key','Return'],check=True);time.sleep(.3)
            subprocess.run(['wmctrl','-ic',hex(w._hWnd)],check=True);p.wait(timeout=15)
