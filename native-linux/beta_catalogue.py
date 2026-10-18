"""Versioned catalogues: old shared seeds retain their original pools."""
import hashlib
import native_targets as legacy
BETA={'questionmark':('Questionmark',44,'boss19.ini'),'ridley':('Ridley',45,'boss20.ini')}
V3_BOSSES={**legacy.BOSSES,**BETA}
EXTRA_BOSSES={'gradius':('Gradius',39,'boss10.ini'),'bomberman':('Bomberman',28,'boss15.ini'),'oldsonic':('Old Sonic',60,'boss23.ini'),'cheetahman':('Cheetahman',54,'boss21.ini')}
V4_BOSSES={**V3_BOSSES,**EXTRA_BOSSES}
MINIBOSSES={'kracko':('Kracko',5,'boss2.ini'),'gravitron':('Gravitron',11,'boss7.ini'),'ninja_ryu':('Ryu (Ausweichen)',31,'boss16.ini')}
V5_BOSSES={**V4_BOSSES,**MINIBOSSES}
MINIBOSSES={**MINIBOSSES,'kid_icarus':('Kid Icarus',27,'boss_kid_icarus')}
V7_BOSSES={**V5_BOSSES,'kid_icarus':MINIBOSSES['kid_icarus']}
MINIBOSSES={**MINIBOSSES,'kappa':('Kappa',37,'boss_kappa')}
BOSSES={**V7_BOSSES,'kappa':MINIBOSSES['kappa']}
ROOMS=legacy.ROOMS
is_target=legacy.is_target
confirmed=legacy.confirmed
# These stages have no reliable distinct native achievement (Sonic is shared).
RECEIPT_BOSSES={'sonic',*EXTRA_BOSSES,*MINIBOSSES}
EXTRA_POINTS={'tutorial':dict(frame=36,x=3263,y=313,category='rooms')}

def catalogue(options):
 version=options.get('route_version',1)
 return BOSSES if version>=8 else V7_BOSSES if version>=6 else V5_BOSSES if version>=5 else V4_BOSSES if version>=4 else V3_BOSSES if version>=3 else legacy.BOSSES

def stage_achievements(options,progress,achievements):
 result=dict(achievements)
 if options.get('mode')=='normal':return result
 result.update({k:2 for k in progress.get('beta_bosses',{}) if k in BETA})
 if options.get('route_version',1)>=4:
  result.update({k:2 if k in progress.get('stage_bosses',{}) else 0 for k in RECEIPT_BOSSES})
 return result

def normalize_core(options,version):
 raw=dict(options);count=raw.get('boss_count')
 if count is not None:
  if type(count) is not int or not 0<=count<=len(catalogue({'route_version':version})):raise ValueError('Ungültige Ziel-Boss-Anzahl.')
  raw['boss_count']=min(count,len(legacy.BOSSES))
 result=legacy.normalize(raw)
 if count is not None:result['boss_count']=count
 return result

def goals(base,seed,options):
 if options.get('route_version',1)<3:return legacy.goals(base,seed,options)
 result=legacy.goals(base,seed,{**options,'boss_count':0})
 if options.get('mode')=='target':
  score=lambda v:hashlib.sha256(f'{seed}\0target-v1\0bosses\0{v}'.encode()).digest()
  result['bosses']=sorted(sorted(catalogue(options),key=score)[:options['boss_count']])
 return result
