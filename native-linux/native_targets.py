"""Seeded, save-local Target Select goals; original chest contents are preserved."""
import hashlib,json
BOSSES={
 'hellokitty':('Hello Kitty',4,'boss1.ini'), 'kingdedede':('King Dedede',6,'boss3.ini'),
 'ryu':('Ryu',7,'boss4.ini'), 'mario':('Mario',10,'boss6.ini'),
 'biollante':('Biollante',12,'boss8.ini'), 'sonic':('Sonic',14,'boss9.ini'),
 'skeletonking':('Skeleton King',17,'boss11.ini'), 'megaman':('Mega Man',24,'boss12.ini'),
 'shangtsung':('Shang Tsung',26,'boss13.ini'), 'missingno':('Missingno',32,'boss17.ini'),
 'ganon':('Ganon',59,'boss22.ini')}
ROOMS=('save1.ini','save2.ini','save3.ini','save4.ini','save6.ini','save7.ini','save9.ini','save10.ini','save11.ini','save12.ini','save13.ini','save15.ini')
def is_target(m):return m.get('options',{}).get('mode')=='target'
def goals(base,seed,options):
 if options.get('mode')!='target':return dict(items=[],bosses=[])
 plan=json.loads((base/'slot_reward_plan.json').read_text(encoding='utf-8'))
 items=sorted({l['source'] for l in plan['locations'] if l['source_kind']=='item'})
 def take(values,n,kind):return sorted(sorted(values,key=lambda v:hashlib.sha256(f'{seed}\0target-v1\0{kind}\0{v}'.encode()).digest())[:n])
 return dict(items=take(items,options['target_count'],'items'),bosses=take(BOSSES,options['boss_count'],'bosses'))
def normalize(options):
 d=dict(options or dict(difficulty=1,levels=True,items=True,characters=False))
 core={'difficulty','levels','items','characters'};extra={'mode','target_count','boss_count'}
 if set(d)-core-extra or not core<=set(d):raise ValueError('Ungültige Laufoptionen.')
 if type(d['difficulty']) is not int or d['difficulty'] not in range(4) or any(type(d[k]) is not bool for k in ('levels','items','characters')):raise ValueError('Ungültige Laufoptionen.')
 if set(d)&extra:
  if not extra<=set(d) or d['mode'] not in ('randomizer','target','normal','boss_rush','level_rush') or type(d['target_count']) is not int or not 1<=d['target_count']<=19 or type(d['boss_count']) is not int or not 0<=d['boss_count']<=len(BOSSES):raise ValueError('Ungültige Zielauswahl.')
  if d['mode']=='target':d.update(levels=True,items=False)
  elif d['mode']=='normal':d.update(levels=False,items=False)
  elif d['mode'] in ('boss_rush','level_rush'):d['levels']=True
 return d

def confirmed(goals,items,disk_items,bosses,disk_bosses):
 own=lambda k:items.get(k.lower(),'0')=='1' and disk_items.get(k.lower(),'0')=='1'
 won=lambda k:int(bosses.get(k,0))>=2 and int(disk_bosses.get(k,0))>=2
 return dict(items=[v for v in goals['items'] if own(v)],bosses=[v for v in goals['bosses'] if won(v)])
