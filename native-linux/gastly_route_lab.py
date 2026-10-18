"""Explicitly attached laboratory driver; no input emulation or item writes.

Uses the established single-position-write/native-scene transition. Start
only with an explicit run id; journal reuse never resets an existing run.
"""
from lab import *
from native_level_route import catalogue,eligible,GastlyRoute,RestartGate
from PY.file_utils import smart_read
from PY.ini_utils import parse_ini
OUT=BASE/'evidence/gastly-route'

def read_state(b,save_name="SaveFile1.ini"):
    before=b.snapshot();oi=ini_object_ids(b)['Ini++']
    cached={k:v['value'] for k,v in ini_items(b,'collectables',oi).items()}
    disk={k.casefold():v for k,v in parse_ini(smart_read(str(BASE/'IWBTB'/save_name))[0]).get('collectables',{}).items()}
    after=b.snapshot()
    if before['scene']!=after['scene'] or before['run']!=after['run']:raise RuntimeError('Scene changed during observation')
    return dict(frame=after['scene']+1,collectables=cached,disk_collectables=disk,
                settled=after['next']==0 and after['frame_count']>=2)

def move(b,pool,name,save_name="SaveFile1.ini",*,stabilize=False):
    state=read_state(b,save_name)
    if not state['settled']:raise RuntimeError('Scene transition in progress')
    if any(state['collectables'].get(k,'0')!=state['disk_collectables'].get(k,'0') for k in ('awesomesauce','gastly')):
        raise RuntimeError('Inventory not yet saved')
    if name not in eligible(pool,state['collectables']):raise ValueError('Destination locked by progression')
    p=pool[name];return transition(b,p['frame'],p['x'],p['y'],save_name,stabilize=stabilize)

class RestartWatcher:
    """Observe only the configured restart key while the exact lab window is focused.
    No grabbing, suppression, or recording of other keys. Poll independently of
    slower inventory reads so short R presses are not lost.
    """
    def __init__(self):
        import threading
        if os.name!='nt':from Xlib import XK
        from PY import platform_windows as gw
        options=parse_ini(smart_read(str(BASE/'IWBTB/options.ini'))[0]).get('options',{})
        value=next((v for k,v in options.items() if k.casefold()=='controlrestart'),'R')
        self.key_name=value.lower() if len(value)==1 else value
        self.window_id=game_window()._hWnd
        self.stop=threading.Event();self.ready=threading.Event();self.pressed=threading.Event()
        self.down=False;self.error=None
        def worker():
            try:
                if os.name=='nt':
                    from windows_api import key_down
                    window=gw.Window(self.window_id);gate=RestartGate()
                    while not self.stop.is_set():
                        self.down=key_down(self.key_name)
                        if gate.update(down=self.down,focused=window.isActive,ready=self.ready.is_set()):self.pressed.set()
                        self.stop.wait(.01)
                    return
                d=gw.connection();code=d.keysym_to_keycode(XK.string_to_keysym(self.key_name))
                if not code:raise ValueError('Unknown configured restart key')
                window=gw.Window(self.window_id);gate=RestartGate()
                while not self.stop.is_set():
                    bits=d.query_keymap();self.down=bool(bits[code//8] & (1<<(code%8)))
                    if gate.update(down=self.down,focused=window.isActive,ready=self.ready.is_set()):self.pressed.set()
                    self.stop.wait(.01)
            except Exception as exc:self.error=exc
        self.thread=threading.Thread(target=worker,daemon=True);self.thread.start()
    def close(self):self.stop.set();self.thread.join(timeout=2)
