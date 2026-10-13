"""Small native panels complement the original animated Boshy menu."""
from ui_i18n import tr, display, font_path, font_family, configure_tk, LANGUAGE, Localized
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import os,json
from native_models import duration
from menu_model import DIFFICULTIES
from run_extras import EXTRAS,SHOT_MODES,SHOT_LABELS,shot_label,presentation
from run_settings import LEVELS,BOSSES as ROUTE_BOSSES,ADVANCED_PAGE_SIZE,ADVANCED_PAGES
from beta_catalogue import goals,BOSSES,confirmed
class Renderer:
 def __init__(self,base):
  self.base=Path(base);self.icons={p.stem.casefold():p for p in (self.base/'Custom/trophies').glob('*.png')};self.cache={}
  self.icons.update({p.stem.casefold():p for p in (self.base/'menu-character-icons').glob('*.png')})
  self.fonts={n:ImageFont.truetype(font_path(),n) for n in (10,11,12,13,14,15,16,17,19,20,22,25)}
  folder=self.base/'menu-runtime';folder.mkdir(exist_ok=True)
  logo=Image.open(self.base/'Custom/boshy_randomizer.png').convert('RGBA');logo.thumbnail((302,121),Image.Resampling.LANCZOS)
  out=Image.new('RGBA',(302,121));out.alpha_composite(logo,((302-logo.width)//2,(121-logo.height)//2));out.save(folder/'logo.png')
 def text(self,x,y,s,n=14,color='white'):
  value=display(s);limit=(860 if x>=237 else 268)-x
  if self.d.textlength(value,font=self.fonts[n])>limit:value=self.fit(value,limit,n)
  self.d.text((x,y),str(value),font=self.fonts[n],fill={'white':'#edf5f6','#92ee92':'#92e4cd','#86e486':'#92e4cd','#dddddd':'#b3c3ce'}.get(color,color))
 def fit(self,s,width,n):
  s=display(s)
  if self.d.textlength(s,font=self.fonts[n])<=width:return s
  while s and self.d.textlength(s+'…',font=self.fonts[n])>width:s=s[:-1]
  return Localized(s+'…')
 def wrap(self,x,y,s,width,n=12,color='#dddddd'):
  s=display(s);line='';separator='' if LANGUAGE=='ja' else ' '
  for word in (list(s) if LANGUAGE=='ja' else s.split()):
   test=(line+separator+word).strip()
   if self.d.textlength(test,font=self.fonts[n])>width and line:self.text(x,y,Localized(line),n,color);y+=n+4;line=word
   else:line=test
  if line:self.text(x,y,Localized(line),n,color);y+=n+4
  return y
 def box(self,r,selected=False):
  self.d.rounded_rectangle(r,radius=5,fill='#244342' if selected else '#16232f',outline='#8cddc6' if selected else '#435767',width=2 if selected else 1)
 def icons_row(self,names,x,y,cols=14,size=17,done=None):
  for i,name in enumerate(names):
   k=(name.casefold(),size);px=x+i%cols*(size+4);py=y+i//cols*(size+5)
   if k not in self.cache:
    p=self.icons.get(k[0]);im=Image.open(p).convert('RGBA') if p else Image.new('RGBA',(size,size),'#555555');im.thumbnail((size,size),Image.Resampling.NEAREST);self.cache[k]=im
   im=self.cache[k];self.im.paste(im,(px,py),im)
   if done is not None and name in done:self.d.rectangle((px,py,px+size,py+size),outline='#72df71')
  return y+max(1,(len(names)+cols-1)//cols)*(size+5)
 def draw(self,m):
  self.im=Image.new('RGB',(880,660),'#ff00ff');self.d=ImageDraw.Draw(self.im)
  self.updates(214 if m.page!='slots' else 251)
  temp=self.base/'menu-runtime/updates-next.bmp';self.im.save(temp);os.replace(temp,self.base/'menu-runtime/updates.bmp')
  self.d.rectangle((0,0,879,659),fill='#ff00ff')
  if m.page=='slots':self.overview(m)
  else:
   self.box((237,254,865,650))
   if m.page=='new':self.new(m)
   elif m.page=='advanced':self.advanced(m)
   elif m.page=='extras':self.extras(m)
   elif m.page=='interval':self.interval_dialog(m)
   elif m.page=='presets':self.presets(m)
   elif m.page=='result':self.result(m)
   elif m.page=='seed':self.seed_dialog(m)
   elif m.page=='characters':self.characters(m)
   elif m.page=='delete':
    self.text(258,284,tr('Speicherplatz {0} löschen?', str(m.slot)),22);self.wrap(258,348,tr('Nur dieser Spielstand wird gelöscht. Eine Sicherung bleibt erhalten.'),568,16)
    self.box((255,530,525,578),m.focus==0);self.text(312,543,tr('Abbrechen'),17);self.box((550,530,850,578),m.focus==1);self.text(606,543,tr('Löschen'),17)
   elif m.page=='targets':self.targets(m)
   else:self.text(263,306,tr('Lauf wird geladen …'),22)
  tmp=self.base/'menu-runtime/frame-next.bmp';self.im.save(tmp);os.replace(tmp,self.base/'menu-runtime/frame.bmp');m.dirty=False
 def updates(self,width=251):
  self.d.rectangle((0,266,285,660),fill='#111b25')
  self.text(17,284,'RANDOMIZER',11,'#90dac7');self.text(17,303,'Latest updates',22)
  self.d.line((17,340,268,340),fill='#3c5362')
  all_entries=json.loads((self.base/'menu_updates.json').read_text())['entries']
  latest=all_entries[0]
  text='LATEST UPDATE\r\n'+latest['date']+'\r\n\r\n'+latest['title']+'\r\n\r\n'+'\r\n\r\n'.join(latest['lines'])
  temp=self.base/'menu-runtime/updates-next.txt';temp.write_bytes(text.encode('cp1252',errors='replace'));os.replace(temp,self.base/'menu-runtime/updates.txt')
  entries=all_entries[:2]
  y=348
  for entry in entries:
   self.text(17,y,entry['date'],10,'#94aebd');y+=15
   self.text(17,y,self.fit(entry['title'],width,14),14,'#c7f2e5');y+=22
   for line in entry['lines']:y=self.wrap(17,y,line,width,10,'#b3c3ce')+2
   y+=12
  self.d.line((17,632,268,632),fill='#3c5362');self.text(17,643,'Randomizer changelog.',10,'#91a7b7')
 def overview(self,m):
  s=m.saves[m.slot];self.box((322,268,870,364))
  self.text(335,277,f"{m.slot}  ·  "+self.fit(s['location'] if s['exists'] else tr('Neuer Spielstand'),480,19),19)
  if s['exists']:
   mode='Target Select' if s.get('settings',{}).get('mode')=='target' else 'Randomizer' if s.get('managed') else tr('Originaler Spielstand')
   self.text(335,305,self.fit(mode+'  ·  '+s['difficulty_name']+'  ·  '+s['character'],521,12),12,'#c3d2dc')
   self.text(335,325,tr('{0}  ·  {1} Tode  ·  {2} Level  ·  {3} Bosse', str(duration(s['seconds'])), str(s['deaths']), str(len(s['worlds'])), str(len(s['bosses']))),12)
   self.text(335,347,'Seed  '+self.fit(s['seed'] or 'Original',470,10),10,'#a8bdc9')
  else:
   self.text(335,308,tr('Modus, Schwierigkeit und Randomizer nach deinem Geschmack.'),12,'#c3d2dc')
   self.text(335,332,tr('Empfohlen: 7 Level + 7 Bosse, danach Solgryn.'),12,'#91d9c4')
  self.box((604,407,870,653))
  self.text(617,417,tr('GESAMMELTE ITEMS'),10,'#94aebd')
  self.icons_row(s['items'],617,436,cols=12,size=16)
  self.text(617,490,tr('GESAMMELTE CHARAKTERE'),10,'#94aebd')
  self.icons_row(s['characters'],617,509,cols=12,size=16)
  if not s['exists']:
   self.text(617,443,tr('Deine Funde erscheinen hier.'),12,'#a8bdc9')
   self.text(617,516,tr('Neue Charaktere im Überblick.'),11,'#a8bdc9')
  self.box((614,570,860,593),m.focus==2)
  self.text(624,575,tr('Entf · Spielstand löschen') if s['exists'] else tr('Advanced · Route & Start'),11,'#d4bac0' if s['exists'] else 'white')
  self.box((614,600,860,624),m.focus==0)
  self.text(624,605,(tr('Enter · Laden wiederholen') if s.get('recovery') else tr('Enter · Fortsetzen')) if s['exists'] else tr('Enter · Neuer Lauf'),12)
  self.box((614,630,860,649),m.focus==1);self.text(624,633,tr('T · Run-Ergebnis') if s.get('completed') else tr('T · Ziele & Details'),11)
  if m.message:self.text(335,350,self.fit(m.message,518,10),10,'#ffce87')
 def new(self,m):
  target=m.options['mode']=='target';self.text(252,265,tr('Neuer Lauf'),20)
  self.box((635,263,854,291),m.focus==9);self.text(652,270,tr('Vorlagen · Standard / …'),12)
  rows=[(tr('Modus'),'Target Select' if target else 'Randomizer'),(tr('Schwierigkeit'),DIFFICULTIES[m.options['difficulty']])]
  rows+= [(tr('Ziel-Items'),str(m.options['target_count'])),(tr('Ziel-Bosse'),tr('AUS') if not m.options['boss_count'] else str(m.options['boss_count']))] if target else [(tr('Position-Randomizer'),tr('AN') if m.options['levels'] else tr('AUS')),(tr('Item-Randomizer'),tr('AN') if m.options['items'] else tr('AUS'))]
  rows.append((tr('Charakter-Randomizer'),tr('AN / F3 gesperrt') if m.options['characters'] else tr('AUS / ')+('Dark Boshy' if m.options.get('start_character','Auto')=='Auto' else m.options['start_character'])))
  rows.append((tr('Schussstil-Randomizer'),shot_label(m.options)))
  for i,(label,value) in enumerate(rows):
   y=295+i*35;self.box((245,y,856,y+32),m.focus==([1,2,3,4,5,8][i]));self.text(257,y+9,self.fit(label,230,13),13);self.text(496,y+9,self.fit(value,345,13),13,'#92ee92')
  msg='Zufällige Ziele pro Seed, originale Truheninhalte. Endlos bis alle Ziele erfüllt sind. Ziele im separaten Live-Tracker.' if target else 'Charakterwechsel bei neuen Spots; neue Charakterfunde kommen in den Pool.'
  self.box((245,508,856,539),m.focus==7);self.text(258,516,tr('Advanced · Hacks (alle Level / Bosse)') if target else tr('Advanced · Route, Start & Hacks'),13,'white')
  self.box((245,546,856,580),m.focus==0);self.text(257,555,tr('Seed'),13);self.text(390,555,self.fit(m.seed+tr(' · Enter: teilen / einfügen'),454,13),13,'#92ee92')
  self.text(255,587,self.fit(m.message or tr('Pfeile: Auswahl / Enter: Öffnen / Esc: Zurück'),590,11),11,'#ffcf75' if m.message else 'white')
  self.box((245,603,856,642),m.focus==6);self.text(455,613,tr('Lauf starten'),17)
 def advanced(self,m):
  o=m.options;self.text(252,264,tr('Advanced · Randomizer (+ Solgryn-Finale)'),17)
  controls=[(tr('Level-Anzahl'),str(o['level_count'])+' / '+str(len(o['level_pool']))),(tr('Boss-Anzahl'),str(o['route_boss_count'])+' / '+str(len(o['boss_pool']))),(tr('Startcharakter'),(tr('Automatisch') if o['start_character']=='Auto' else o['start_character'])+tr(' · Enter: Auswahl'))]
  for i,(label,value) in enumerate(controls):
   y=299+i*25;self.box((245,y,856,y+23),m.focus==i);self.text(255,y+4,self.fit(label,221,12),12);self.text(486,y+4,self.fit(value,358,12),12,'#92ee92')
  self.text(252,378,tr('LEVEL IM SEED-POOL'),12);self.text(556,378,tr('BOSSE'),12)
  self.text(666,378,f'{m.advanced_page+1} / {ADVANCED_PAGES}',12)
  self.box((751,374,791,395),False);self.text(764,377,'<',12)
  self.box((799,374,845,395),False);self.text(815,377,'>',12)
  entries=[(k,n,'level_pool') for k,n in LEVELS.items()]+[(k,v[0],'boss_pool') for k,v in ROUTE_BOSSES.items()]
  for i,(key,name,pool) in enumerate(entries):
   col=0 if i<len(LEVELS) else 1;row=i if col==0 else i-len(LEVELS)
   if row//ADVANCED_PAGE_SIZE!=m.advanced_page:continue
   row%=ADVANCED_PAGE_SIZE;x=249+col*304;y=399+row*15
   if m.focus==i+3:self.d.rectangle((x,y,x+292,y+14),fill='#183f1c')
   self.text(x+3,y+1,self.fit(('✓ ' if key in o[pool] else '– ')+str(display(name)),284,11),11,'#92ee92' if key in o[pool] else '#929292')
  self.box((245,608,548,642),m.focus==len(entries)+3);self.text(260,618,tr('Fertig · Auswahl übernehmen'),12)
  self.box((558,608,856,642),m.focus==len(entries)+4);self.text(573,618,tr('Hacks · Pop-ups, Mausgeist & mehr'),12)
 def extras(self,m):
  self.text(252,265,tr('Advanced · Hacks für diesen Lauf'),20)
  for i,(key,label,hint,default) in enumerate(EXTRAS):
   y=293+i*33;active=m.options.get('extras',{}).get(key,False)
   self.box((245,y,856,y+31),m.focus==i);self.text(257,y+2,label,12)
   self.text(794,y+2,tr('AN') if active else tr('AUS'),13,'#92e4cd' if active else '#a8bdc9')
   self.text(257,y+17,self.fit(hint,584,10),10,'#b3c3ce')
  self.box((245,608,856,642),m.focus==len(EXTRAS));self.text(260,618,tr('Zurück · Alle Extras werden im geteilten Seed gespeichert.'),12)
 def seed_dialog(self,m):
  self.text(252,265,tr('Seed · teilen und einfügen'),20)
  try:
   seed,o=m.seed_value(m.seed_text)
   mode='Target Select' if o['mode']=='target' else 'Randomizer'
   details=(tr('{0} Ziel-Items / {1} Ziel-Bosse', str(o['target_count']), str(o['boss_count'])) if o['mode']=='target' else tr('{0} Level / {1} Bosse', str(o['level_count']), str(o['route_boss_count'])))
   self.text(253,296,self.fit(mode+' · '+DIFFICULTIES[o['difficulty']]+' · '+details,596,11),11,'#92ee92')
   self.text(253,313,self.fit(tr('Start: ')+o['start_character']+tr(' / Charakterwechsel: ')+(tr('AN') if o['characters'] else tr('AUS'))+tr(' / Items: ')+(tr('AN') if o['items'] else tr('AUS')),596,10),10)
  except ValueError:self.text(253,299,tr('Vollständigen BR2-Seed einfügen oder neu generieren.'),12)
  self.box((251,329,851,486),m.focus==0)
  if m.seed_selected:self.d.rectangle((254,332,848,483),fill='#31567b')
  text=m.seed_text+('|' if m.focus==0 and not m.seed_selected else '')
  lines=[text[i:i+88] for i in range(0,len(text),88)] or ['']
  if len(lines)>10:lines=['…']+lines[-9:]
  for i,line in enumerate(lines):self.text(259,338+i*14,Localized(line),11)
  for i,(left,right,label) in enumerate(((251,443,tr('Neu generieren')),(455,647,tr('Kopieren')),(659,851,tr('Einfügen'))),1):
   self.box((left,499,right,533),m.focus==i);self.text(left+13,509,label,13)
  self.wrap(253,544,m.message or tr('Strg+A: Text markieren · Strg+V: Einfügen · Strg+C: Kopieren. Übernehmen lädt Seed und Einstellungen; Esc verwirft den Entwurf.'),595,11,'#ffcf75' if m.message else '#dddddd')
  self.box((251,604,546,640),m.focus==4);self.text(327,615,tr('Übernehmen'),14)
  self.box((558,604,851,640),m.focus==5);self.text(646,615,tr('Abbrechen'),14)
 def characters(self,m):
  self.text(252,265,tr('Startcharakter auswählen'),20)
  self.text(253,288,tr('Pfeile: Auswahl · Enter: Übernehmen · Esc: Zurück'),11)
  for i,name in enumerate(m.character_names):
   x=249+i%7*87;y=303+i//7*49;self.box((x,y,x+82,y+45),m.focus==i)
   if name.casefold() in self.icons:self.icons_row([name],x+30,y+3,cols=1,size=22)
   elif name=='Auto':self.text(x+32,y+2,'?',19,'#92ee92')
   else:self.text(x+26,y+5,''.join(v[0] for v in name.split())[:3],14,'#92ee92')
   self.text(x+4,y+30,self.fit('Auto' if name=='Auto' else name,75,10),10)
  name=m.character_names[m.focus]
  self.text(253,557,tr('Automatisch') if name=='Auto' else name,16,'#92ee92')
  self.wrap(253,580,tr('Auto: Dark Boshy, bei aktivem Charakter-Randomizer zufälliger Start.') if name=='Auto' else tr('Auswahl gilt für den Start. Enter übernimmt diesen Charakter.'),595,11)
  self.box((249,608,852,640));self.text(487,618,tr('Zurück'),13)
 def targets(self,m):
  s=m.saves[m.slot];self.text(252,265,tr('Speicherplatz {0} · Ziele & Details', str(m.slot)),20)
  if not s['exists']:
   self.wrap(254,326,tr('Hier erscheinen deine gesammelten Items, Charaktere und abgeschlossenen Bosse. Dieser Speicherplatz ist noch frei.'),576,16)
   self.text(254,624,tr('Esc / Enter · Zurück'),12);return
  options=s.get('settings',{});g=goals(self.base,s.get('seed',''),options)
  items=g['items'] or s.get('items',[]);bosses=g['bosses'] or s.get('bosses',[])
  self.text(254,307,(tr('ZIEL-ITEMS') if g['items'] else tr('GESAMMELTE ITEMS'))+f'  ·  {len(items)}',12,'#92e4cd')
  self.icons_row(items,254,335,cols=9,size=26,done=set(s.get('items',[])) if g['items'] else None)
  self.text(558,307,tr('ZIEL-BOSSE') if g['items'] else tr('BESIEGTE BOSSE'),12,'#92e4cd')
  for i,key in enumerate(bosses):
   name=BOSSES[key][0] if key in BOSSES else key;done=name in s.get('bosses',[]);x=558+(i//11)*147;y=335+(i%11)*23
   self.text(x,y,('✓ ' if done else '· ')+self.fit(name,127,11),11,'#92e4cd' if done else '#b3c3ce')
  self.text(254,446,tr('GESAMMELTE CHARAKTERE'),12,'#92e4cd');self.icons_row(s.get('characters',[]),254,474,cols=9,size=26)
  self.text(254,553,tr('LEVEL ABGESCHLOSSEN'),11,'#94aebd')
  self.wrap(254,575,', '.join(map(str,s.get('worlds',[]))) or tr('Noch keine'),279,12)
  self.d.line((254,610,850,610),fill='#435767');self.text(254,624,tr('Esc / Enter · Zurück'),12)

 def interval_dialog(self,m):
  self.text(252,265,tr('Schusswechsel · zufällige Wartezeit'),20)
  self.wrap(253,305,tr('Nach jedem Wechsel wird eine neue Wartezeit zwischen 1 Sekunde und deiner Obergrenze gezogen.'),593,13)
  for i,(x,label) in enumerate(((260,tr('Minuten')),(555,tr('Sekunden')))):
   self.box((x,354,x+275,414),m.focus==i);self.text(x+14,362,label,11,'#a8bdc9');self.text(x+14,382,m.interval_fields[i] or '0',22,'#92e4cd')
  self.wrap(253,450,tr('Standard: 5 Minuten. Menüs und geschlossene Spiele verbrauchen keine Wechselzeit. Die Obergrenze wird mit deinem Seed geteilt.'),590,13)
  self.wrap(253,535,m.message or tr('Ziffern: Eingabe · Pfeile links/rechts: ±1 · Tab: nächstes Feld'),590,12,'#ffcf75' if m.message else '#a8bdc9')
  self.box((251,604,546,640),m.focus==2);self.text(327,615,tr('Übernehmen'),14)
  self.box((558,604,851,640),m.focus==3);self.text(646,615,tr('Abbrechen'),14)
 def presets(self,m):
  self.text(252,265,tr('Vorlagen · danach frei anpassbar'),20)
  self.text(253,294,tr('Spielmodus und Anzahl der Target-Ziele bleiben erhalten.'),11,'#a8bdc9')
  for i,(name,hint) in enumerate(((tr('Standard'),tr('Pop-ups und Mausgeist aus; übrige Hacks deaktiviert.')),(tr('Chaos'),tr('Zusätzlich Charakterwechsel sowie Schusswechsel bei Tod und Spot.')),(tr('Training'),tr('God Mode, 1-HP-Bosse, Dauerfeuer und verkürzte Animationen.')),(tr('Abbrechen'),tr('Aktuelle Einstellungen behalten.')))):
   y=315+i*73;self.box((251,y,851,y+60),m.focus==i);self.text(265,y+8,name,17,'#92e4cd');self.text(265,y+36,self.fit(hint,568,11),11)
 def result(self,m):
  r=m.result;h=r.get('highlights',{});self.text(252,265,tr('Solgryn besiegt · Dein Run'),22,'#92e4cd')
  self.text(253,304,tr('{0}   ·   {1} Tode   ·   Slot {2}', str(duration(r.get('seconds', 0))), str(r.get('deaths', 0)), str(r.get('slot', m.slot))),17)
  self.text(253,337,self.fit('Seed: '+str(m.result_manifest['seed']),595,13),13)
  y=371
  for key,title in (('hardest',tr('Meiste Tode')),('longest_boss',tr('Längster Bossabschnitt'))):
   v=h.get(key);text=(v['name']+' · '+(str(v['deaths'])+tr(' Tode') if key=='hardest' else duration(v['seconds']))) if v else tr('Noch keine vollständigen Messdaten')
   self.text(253,y,title,11,'#94aebd');self.text(253,y+17,self.fit(text,594,14),14);y+=48
  self.text(253,472,tr('FUNDE IN REIHENFOLGE'),11,'#94aebd')
  names=[v['name'] for v in h.get('finds',[])];self.icons_row(names,253,493,cols=20,size=23)
  options=m.result_manifest['options'];labels=[str(display(x['label'])) for x in presentation(options)]
  if options.get('extras',{}).get('shot_mode','off')!='off':labels.insert(0,tr('Schussstil: ')+str(display(shot_label(options))))
  extras=' · '.join(labels) or tr('Keine Extras')
  self.wrap(253,552,self.fit(extras,594,10),594,10,'#a8bdc9')
  self.text(253,580,self.fit(m.message or (tr('Auswertung ab diesem Update; ältere Abschnitte fehlen.') if h.get('partial',True) else tr('Seed und vollständige Auswertung im Debugbericht verfügbar.')),594,11),11,'#ffcf75' if m.message else '#a8bdc9')
  self.box((251,604,546,640),m.focus==0);self.text(277,615,tr('Diesen Seed erneut spielen'),14)
  self.box((558,604,851,640),m.focus==1);self.text(623,615,tr('Zum Hauptmenü'),14)
