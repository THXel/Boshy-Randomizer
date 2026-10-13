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

def encode(seed,options):
    # All gameplay settings travel with the seed, including the rules revision.
    payload=json.dumps([2,str(seed),normalize(options)],sort_keys=True,separators=(',',':')).encode()
    body=base64.urlsafe_b64encode(zlib.compress(payload,9)).decode().rstrip('=')
    return 'BR2-'+body+'.'+hashlib.sha256(payload).hexdigest()[:12]

def decode(value,options=None):
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
