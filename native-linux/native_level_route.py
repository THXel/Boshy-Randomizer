"""Native laboratory level selection and one-shot Gastly continuation.

Reads real Collectables, never grants items. The legacy GUI is not connected.
A journal is bound to a run, seed, game version and exact destination pool.
"""
from pathlib import Path
import hashlib,json,sqlite3

GASTLY_SPOT = 'gastly_grass'

def normalized(values):
    return {str(k).strip().casefold():str(v).strip() for k,v in values.items()}

def gastly_available(collectables):
    v=normalized(collectables)
    return v.get('awesomesauce')=='1' and v.get('gastly','0')=='0'

def catalogue(positions):
    result={}
    for category in ('rooms','bosses'):
        for name,p in positions[category].items():
            # Replace the old direct fight destination with the world-3 grass.
            if int(p['frame'])==9 or name.lower()=='boss5.ini':continue
            result[name]={'frame':int(p['frame']),'x':int(p['xPos']),
                          'y':int(p['yPos']),'category':category}
    result[GASTLY_SPOT]={'frame':8,'x':380,'y':300,'category':'rooms',
                          'requires':'awesomesauce','exclude_owned':'gastly'}
    return result

def eligible(pool,collectables,*,disabled=()):
    disabled={x.casefold() for x in disabled}
    result={}
    v=normalized(collectables)
    for name,p in pool.items():
        if name.casefold() in disabled:continue
        is_gastly=name in (GASTLY_SPOT,'boss5.ini') or p['frame']==9
        if is_gastly and not gastly_available(v):continue
        if p.get('requires') and v.get(p['requires'])!='1':continue
        if p.get('exclude_owned') and v.get(p['exclude_owned'])=='1':continue
        result[name]=p
    return result

class GastlyRoute:
    def __init__(self,path,*,run_id,seed,game_hash,pool):
        if not run_id or not game_hash or not pool:raise ValueError('Run identity and pool required')
        self.pool=pool;self.seed=str(seed)
        self.db=sqlite3.connect(path,timeout=2)
        self.db.execute('PRAGMA synchronous=FULL')
        binding=json.dumps(dict(version=3,run_id=run_id,seed=self.seed,game_hash=game_hash,pool=pool),sort_keys=True)
        try:
            if self.db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Damaged route journal')
            self.db.execute('CREATE TABLE IF NOT EXISTS route (id INTEGER PRIMARY KEY CHECK(id=1),binding TEXT NOT NULL,phase TEXT NOT NULL,target TEXT)')
            row=self.db.execute('SELECT binding,phase,target FROM route WHERE id=1').fetchone()
            if row and (row[0]!=binding or row[1] not in ('idle','armed','caught','pending','done') or (row[1] in ('pending','done') and row[2] not in pool)):
                raise ValueError('Different or invalid run journal; refusing to reset it')
            if not row:self.db.execute("INSERT INTO route VALUES (1,?,'idle',NULL)",(binding,))
            self.db.commit()
        except Exception:
            self.db.close();raise

    def state(self):
        phase,target=self.db.execute('SELECT phase,target FROM route WHERE id=1').fetchone()
        return dict(phase=phase,target=target)

    def observe(self,*,frame,collectables,disk_collectables,settled=True,restart_pressed=False,next_target=None):
        """Frame numbers are one-based. Capture dispatches on a fresh restart press or native return to frame 8.

        Disk and cached flags must agree. Capture is armed only while Gastly
        is absent in the actual encounter; loading an old owned Gastly does
        not fabricate a new completion. Death before capture cannot trigger.
        """
        if not settled:return None
        v=normalized(collectables);disk=normalized(disk_collectables)
        if any(v.get(k,'0')!=disk.get(k,'0') for k in ('awesomesauce','gastly')):return None
        sauce=v.get('awesomesauce')=='1';caught=v.get('gastly','0')=='1'
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            phase,target=self.db.execute('SELECT phase,target FROM route WHERE id=1').fetchone()
            if phase=='idle' and frame==9 and sauce and not caught:phase='armed'
            elif phase=='armed':
                if sauce and caught:phase='caught'
                elif frame!=9 or not sauce:phase='idle'
            if phase=='caught' and (restart_pressed or frame==8) and sauce and caught:
                choices={k:p for k,p in eligible(self.pool,v).items()
                         if p['category']=='rooms' and p['frame'] not in (8,9)}
                if not choices and not next_target:raise ValueError('No eligible destination after Gastly')
                # Stable seeded selection, including across crash/restart.
                names=sorted(choices)
                n=int.from_bytes(hashlib.sha256((self.seed+'\0gastly-captured').encode()).digest(),'big')
                target=next_target() if next_target else names[n%len(names)]
                if target not in eligible(self.pool,v):raise ValueError('Gastly destination is not eligible')
                phase='pending'
            self.db.execute('UPDATE route SET phase=?,target=? WHERE id=1',(phase,target))
        if phase=='pending' and sauce and caught:return target
        return None

    def confirm_arrival(self,target,*,frame,position):
        p=self.pool[target]
        if frame!=p['frame'] or tuple(position)!=(p['x'],p['y']):raise ValueError('Arrival not confirmed')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            state=self.state()
            if state!={'phase':'pending','target':target}:raise ValueError('No matching pending transition')
            self.db.execute("UPDATE route SET phase='done' WHERE id=1")

    def close(self):self.db.close()

class RestartGate:
    """A held key or a press outside the game is never a new restart request."""
    def __init__(self):self.down=False
    def update(self,*,down,focused,ready):
        fresh=bool(down and not self.down and focused and ready)
        self.down=bool(down)
        return fresh
