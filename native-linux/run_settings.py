"""Versioned, portable seed settings and deterministic level/boss routes."""
import base64, hashlib, json, zlib
from beta_catalogue import BOSSES, ROOMS, normalize_core, catalogue
from native_targets import BOSSES as LEGACY_BOSSES

LEGACY_LEVELS = dict(zip(ROOMS, ('Prehistorik','Green Greens','Cheetahmen II','VVVVVV','Wario','Castlevania','Milons Secret Castle','Metal Gear','Megaman','Kid Icarus','Ninja Gaiden','Desert')))
V4_LEVELS={**LEGACY_LEVELS,'tutorial':'Tutorial','save14.ini':'Secret Mario','save17.ini':'Justin.tv','save19.ini':'Pokémon','save20.ini':'Tower','save21.ini':'World of Warcraft','save18.ini':'Final Path (Terranigma)'}
NEW_LEVELS={'save23.ini':'Green Greens · nach Kracko','save22.ini':'Ninja Gaiden · nach Ryu'}
LEVELS={**V4_LEVELS,**NEW_LEVELS}
def level_catalogue(version):return LEVELS if version>=5 else V4_LEVELS if version>=4 else LEGACY_LEVELS
ADVANCED_PAGE_SIZE=13
ADVANCED_PAGES=(max(len(LEVELS),len(BOSSES))+ADVANCED_PAGE_SIZE-1)//ADVANCED_PAGE_SIZE
ADVANCED = {'route_version','level_pool','boss_pool','level_count','route_boss_count','start_character'}

def defaults(version=5):
    return dict(route_version=version, level_pool=list(level_catalogue(version)), boss_pool=list(catalogue({"route_version":version})), level_count=7, route_boss_count=7, start_character='Auto')

def normalize(options):
    raw=dict(options or dict(difficulty=1,levels=True,items=True,characters=False))
    has_hacks='extras' in raw
    hacks=raw.pop('extras',None)
    if has_hacks:
        from run_extras import normalize as normalize_extras
        hacks=normalize_extras(hacks)
    extra={k:raw.pop(k) for k in ADVANCED if k in raw}
    d=normalize_core(raw,extra.get('route_version',1))
    if hacks is not None:d['extras']=hacks
    if not extra:return d  # Existing manifests retain their exact binding.
    if set(extra)!=ADVANCED or extra['route_version'] not in (2,3,4,5):raise ValueError('Unbekannte Routen-Version.')
    for key,valid in [('level_pool',level_catalogue(extra['route_version'])),('boss_pool',catalogue(extra))]:
        values=extra[key]
        if not isinstance(values,list) or any(type(v) is not str or v not in valid for v in values) or len(values)!=len(set(values)):raise ValueError('Ungültige Level-/Boss-Auswahl.')
        extra[key]=sorted(values)
    for key,pool in [('level_count','level_pool'),('route_boss_count','boss_pool')]:
        if type(extra[key]) is not int or not 0<=extra[key]<=len(extra[pool]):raise ValueError('Anzahl übersteigt die ausgewählten Level/Bosse.')
    if extra['level_count']+extra['route_boss_count']==0:raise ValueError('Mindestens ein Level oder Boss muss ausgewählt sein.')
    if type(extra['start_character']) is not str or not 1<=len(extra['start_character'])<=50:raise ValueError('Ungültiger Startcharakter.')
    if d.get('mode')=='target':extra=defaults(extra['route_version']);extra.update(level_pool=sorted(level_catalogue(extra["route_version"])),boss_pool=sorted(catalogue(extra)))
    return {**d,**extra}

def route(seed, options):
    if options.get('route_version') not in (2,3,4,5) or options.get('mode')=='target':return []
    def pick(values,n,kind):
        return sorted(values,key=lambda v:hashlib.sha256(f'{seed}\0route-v{options["route_version"]}\0{kind}\0{v}'.encode()).digest())[:n]
    levels=pick(options['level_pool'],options['level_count'],'level')
    bosses=[BOSSES[k][2] for k in pick(options['boss_pool'],options['route_boss_count'],'boss')]
    result=[]
    for i in range(max(len(levels),len(bosses))):
        if i<len(levels):result.append(levels[i])
        if i<len(bosses):result.append(bosses[i])
    return result+['boss_solgryn.ini']

def pool_names(options):
    if options.get('mode')=='target':return (*level_catalogue(options.get("route_version",1)),*(v[2] for v in catalogue(options).values()),'gastly_grass','boss_solgryn.ini')
    return (*options['level_pool'],*(BOSSES[k][2] for k in options['boss_pool']),'boss_solgryn.ini')

def character(base,seed,options):
    from character_cycle import initial,roster
    name=options.get('start_character','Auto')
    if name=='Auto' or options.get('mode')=='target':return initial(base,seed,options['characters'])
    return next((dict(name=c['name'],id=c['id']) for c in roster(base) if c['name']==name),None) or _invalid_character()
def _invalid_character():raise ValueError('Dieser Startcharakter ist nicht verfügbar.')

def _encode_legacy(seed,options):
    # All gameplay settings travel with the seed, including the rules revision.
    payload=json.dumps([2,str(seed),normalize(options)],sort_keys=True,separators=(',',':')).encode()
    body=base64.urlsafe_b64encode(zlib.compress(payload,9)).decode().rstrip('=')
    return 'BR2-'+body+'.'+hashlib.sha256(payload).hexdigest()[:12]

def _decode_legacy(value,options=None):
    value=str(value).strip()
    if not value.startswith('BR'):
        if not value or len(value)>128 or any(ord(c)<32 or ord(c)>126 for c in value):raise ValueError('Seed: 1–128 druckbare Zeichen verwenden.')
        return value,normalize(options)
    if not value.startswith('BR2-'):raise ValueError('Diese Seed-Version wird nicht unterstützt.')
    try:
        if len(value)>4096:raise ValueError()
        body,check=value[4:].split('.')
        packed=base64.b64decode(body+'='*(-len(body)%4),altchars=b'-_',validate=True)
        inflater=zlib.decompressobj();payload=inflater.decompress(packed,8193)
        if len(payload)>8192 or not inflater.eof or inflater.unused_data or hashlib.sha256(payload).hexdigest()[:12]!=check:raise ValueError()
        version,seed,settings=json.loads(payload)
        if version!=2 or not isinstance(seed,str) or not seed or len(seed)>128 or any(ord(c)<32 or ord(c)>126 for c in seed):raise ValueError()
        return seed,normalize(settings)
    except (ValueError,TypeError,KeyError,zlib.error) as e:raise ValueError('Der geteilte Seed ist unvollständig oder beschädigt.') from e


# BR3 is a wire format, independent of future UI defaults/catalogue order.
# Never reorder or extend these tables in place: introduce a new seed version.
_BR3_LEVELS=('save1.ini','save10.ini','save11.ini','save12.ini','save13.ini','save14.ini','save15.ini','save17.ini','save18.ini','save19.ini','save2.ini','save20.ini','save21.ini','save22.ini','save23.ini','save3.ini','save4.ini','save6.ini','save7.ini','save9.ini','tutorial')
_BR3_BOSSES=('biollante','bomberman','cheetahman','ganon','gradius','gravitron','hellokitty','kingdedede','kracko','mario','megaman','missingno','ninja_ryu','oldsonic','questionmark','ridley','ryu','shangtsung','skeletonking','sonic')
_BR3_EXTRAS=('quiet_pickups','no_mouse_ghost','one_hp','god_mode','autofire','mirror','death_character','skip_intro','fast_chests')
_BR3_SHOTS=('off','random_interval','spot','death','death_and_spot')
_BR3_KEYS=('difficulty','levels','items','characters','mode','target_count','boss_count','route_version','level_pool','boss_pool','level_count','route_boss_count','start_character','extras')

def _br3_defaults():
    return dict(difficulty=1,levels=True,items=True,characters=False,mode='randomizer',target_count=5,boss_count=0,
                route_version=5,level_pool=list(_BR3_LEVELS),boss_pool=list(_BR3_BOSSES),level_count=7,route_boss_count=7,start_character='Auto',
                extras=dict(version=3,shot_mode='off',shot_interval_seconds=300,**{k:i<2 for i,k in enumerate(_BR3_EXTRAS)}))

def _seed_text(seed):
    seed=str(seed)
    if not seed or len(seed)>128 or any(ord(c)<32 or ord(c)>126 for c in seed):raise ValueError('Seed: 1–128 druckbare Zeichen verwenden.')
    return seed

def _varuint(value):
    out=bytearray()
    while value>=128:out.append((value&127)|128);value>>=7
    out.append(value);return bytes(out)

class _SeedReader:
    def __init__(self,data):self.data=data;self.at=0
    def take(self,n):
        if n<0 or self.at+n>len(self.data):raise ValueError('Truncated seed')
        data=self.data[self.at:self.at+n];self.at+=n;return data
    def number(self):
        value=0
        for shift in range(0,35,7):
            b=self.take(1)[0];value|=(b&127)<<shift
            if not b&128:return value
        raise ValueError('Seed integer too large')
    def text(self):
        n=self.number()
        if n>200:raise ValueError('Seed text too long')
        return self.take(n).decode('utf-8')

def _seed_string(value):
    data=value.encode('utf-8');return _varuint(len(data))+data

def _seed_mask(values,table):
    if any(v not in table for v in values):raise ValueError('Unsupported seed catalogue')
    return sum(1<<table.index(v) for v in values)

def _seed_pool(mask,table):
    if mask>>len(table):raise ValueError('Unknown seed catalogue bit')
    return [v for i,v in enumerate(table) if mask&(1<<i)]

def encode(seed,options):
    """Lossless offline share code. Only differences from frozen defaults travel."""
    seed=_seed_text(seed);settings=normalize(options);baseline=_br3_defaults()
    present=sum(1<<i for i,k in enumerate(_BR3_KEYS) if k in settings)
    changed=sum(1<<i for i,k in enumerate(_BR3_KEYS) if k in settings and settings[k]!=baseline[k])
    hex_seed=len(seed)==8 and all(c in '0123456789ABCDEF' for c in seed)
    full=(1<<len(_BR3_KEYS))-1
    payload=bytearray([int(hex_seed)|(2 if present!=full else 0)])
    payload.extend(bytes.fromhex(seed) if hex_seed else _seed_string(seed))
    if present!=full:payload.extend(_varuint(present))
    payload.extend(_varuint(changed))
    for i,k in enumerate(_BR3_KEYS):
        if not changed&(1<<i):continue
        value=settings[k]
        if k in ('levels','items','characters'):continue # Changed boolean is its inverse.
        if k=='mode':payload.append(int(value=='target'))
        elif k in ('level_pool','boss_pool'):payload.extend(_varuint(_seed_mask(value,_BR3_LEVELS if k=='level_pool' else _BR3_BOSSES)))
        elif k=='start_character':payload.extend(_seed_string(value))
        elif k=='extras':
            version=value['version'];payload.append(version)
            rows=_BR3_EXTRAS[:7] if version==1 else _BR3_EXTRAS
            payload.extend(_varuint(sum(1<<j for j,key in enumerate(rows) if value[key])))
            if version>=2:payload.append(_BR3_SHOTS.index(value['shot_mode']))
            if version>=3:payload.extend(_varuint(0 if value['shot_interval_seconds']==300 else value['shot_interval_seconds']))
        else:payload.extend(_varuint(value))
    payload.extend(hashlib.sha256(b'BR3\0'+payload).digest()[:4])
    return 'BR3-'+base64.urlsafe_b64encode(payload).decode().rstrip('=')

def _decode_compact(code):
    try:
        if len(code)>1024:raise ValueError()
        body=code[4:];packet=base64.b64decode(body+'='*(-len(body)%4),altchars=b'-_',validate=True)
        if len(packet)<6:raise ValueError()
        payload,checksum=packet[:-4],packet[-4:]
        if hashlib.sha256(b'BR3\0'+payload).digest()[:4]!=checksum:raise ValueError()
        r=_SeedReader(payload);flags=r.take(1)[0]
        if flags&~3:raise ValueError()
        seed=r.take(4).hex().upper() if flags&1 else r.text();_seed_text(seed)
        full=(1<<len(_BR3_KEYS))-1;present=r.number() if flags&2 else full;changed=r.number()
        if present&~full or changed&~present:raise ValueError()
        baseline=_br3_defaults();settings={k:baseline[k] for i,k in enumerate(_BR3_KEYS) if present&(1<<i)}
        for i,k in enumerate(_BR3_KEYS):
            if not changed&(1<<i):continue
            if k in ('levels','items','characters'):value=not baseline[k]
            elif k=='mode':
                mode=r.take(1)[0]
                if mode not in (0,1):raise ValueError()
                value=('randomizer','target')[mode]
            elif k in ('level_pool','boss_pool'):value=_seed_pool(r.number(),_BR3_LEVELS if k=='level_pool' else _BR3_BOSSES)
            elif k=='start_character':value=r.text()
            elif k=='extras':
                version=r.take(1)[0]
                if version not in (1,2,3):raise ValueError()
                rows=_BR3_EXTRAS[:7] if version==1 else _BR3_EXTRAS;mask=r.number()
                if mask>>len(rows):raise ValueError()
                value=dict(version=version,**{key:bool(mask&(1<<j)) for j,key in enumerate(rows)})
                if version>=2:value['shot_mode']=_BR3_SHOTS[r.take(1)[0]]
                if version>=3:value['shot_interval_seconds']=r.number() or 300
            else:value=r.number()
            settings[k]=value
        if r.at!=len(payload):raise ValueError()
        normalized=normalize(settings)
        if settings!=normalized or encode(seed,normalized)!=code:raise ValueError()
        return seed,normalized
    except (ValueError,TypeError,KeyError,IndexError,OverflowError) as e:
        raise ValueError('Der geteilte Seed ist unvollständig oder beschädigt.') from e

def decode(value,options=None):
    value=str(value).strip()
    return _decode_compact(value) if value.startswith('BR3-') else _decode_legacy(value,options)
