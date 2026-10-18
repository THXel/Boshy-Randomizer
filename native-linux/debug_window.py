"""Optional independent diagnostics window; Ctrl+Alt+D, scoped to this randomizer."""
from ui_i18n import tr, display as localize, font_path, font_family, configure_tk, LANGUAGE, Localized
import argparse,os,time,uuid,json,subprocess,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk,filedialog
import psutil
if os.name!='nt':from Xlib import display,XK
from debug_data import Recorder,Chord,read_json,write_json,report_text

class Window:
 def __init__(self,host,folder):
  self.base=Path(__file__).resolve().parent;self.folder=Path(folder);self.host=psutil.Process(host);self.birth=self.host.create_time()
  self.root=tk.Tk();configure_tk(self.root);self.root.withdraw();self.root.title('Boshy Randomizer – Debug');self.root.geometry('900x720');self.root.minsize(650,500)
  self.visible=False;self.state={};self.run=None;self.pending={};self.recorder=Recorder(self.base);self.chord=Chord();self.x=display.Display() if os.name!='nt' else None;self.closing=False
  self.marker_chord=Chord();self.marker_future=None;self.marker_last=-float('inf');self.exporter=ThreadPoolExecutor(max_workers=1,thread_name_prefix='debug-export')
  self.keys={n:self.x.keysym_to_keycode(XK.string_to_keysym(n)) for n in ('Control_L','Control_R','Alt_L','Alt_R','d','m')} if self.x else {}
  self.status=tk.StringVar(value=tr('Warte auf den Randomizer …'));self.notice=tk.StringVar(value=tr('Strg+Alt+D öffnet oder versteckt dieses Fenster.'));self.record_status=tk.StringVar();self.enabled=tk.BooleanVar(value=False)
  bar=ttk.Frame(self.root,padding=10);bar.pack(fill='x');ttk.Label(bar,text=tr('Randomizer-Diagnose'),font=('',16,'bold')).pack(side='left');ttk.Button(bar,text=tr('Seed kopieren'),command=lambda:self.copy(self.state.get('share_seed',''))).pack(side='right')
  self.marker_button=ttk.Button(bar,text=tr('Problem markieren · Strg+Alt+M'),command=self.mark_problem);self.marker_button.pack(side='right',padx=8)
  ttk.Label(self.root,textvariable=self.status,padding=(10,0),wraplength=850).pack(fill='x')
  tabs=ttk.Notebook(self.root);tabs.pack(fill='both',expand=True,padx=10,pady=10)
  overview=ttk.Frame(tabs,padding=8);actions=ttk.Frame(tabs,padding=12);record=ttk.Frame(tabs,padding=12)
  audit=ttk.Frame(tabs,padding=8)
  tabs.add(audit,text=tr('Trigger-Prüfung'))
  ttk.Label(audit,text=tr('Logiktest = simuliert. Spieltest = kontrollierter Eingriff. Regulärer Ausgang = durchgespielt.'),wraplength=800).pack(anchor='w')
  self.audit=ttk.Treeview(audit,columns=('start','exit','reset','hacks','natural'),height=20)
  self.audit.heading('#0',text=tr('Randomizer-Punkt'));self.audit.column('#0',width=230)
  for key,label in [('start','Start'),('exit','Ausgang'),('reset','Reset'),('hacks','Hacks'),('natural','Regulärer Ausgang')]:self.audit.heading(key,text=tr(label));self.audit.column(key,width=110)
  scrollbar=ttk.Scrollbar(audit,command=self.audit.yview);self.audit.configure(yscrollcommand=scrollbar.set);scrollbar.pack(side='right',fill='y');self.audit.pack(fill='both',expand=True)
  ttk.Button(audit,text=tr('Prüfstand aktualisieren'),command=self.refresh_audit).pack(anchor='w');self.refresh_audit()
  tabs.add(overview,text=tr('Live-Übersicht'));tabs.add(actions,text=tr('Testaktionen'));tabs.add(record,text=tr('Aufzeichnung & Bericht'));tabs.select(overview)
  graphics=ttk.Frame(tabs,padding=12);tabs.add(graphics,text=tr('Grafikdiagnose'))
  ttk.Label(graphics,text=tr('Angehakte Kategorien vorübergehend abschalten. Wirksam beim nächsten Levelwechsel. R allein lädt nicht alle Bilder neu. Beim Laden eines Spielstands gelten wieder dessen Seed-Einstellungen.'),wraplength=800).pack(anchor='w',pady=8)
  from graphics_debug import CATEGORIES
  self.graphics_vars={};self.graphics_dirty=False
  for bit,title in CATEGORIES:
   value=tk.BooleanVar(value=False);self.graphics_vars[bit]=value
   ttk.Checkbutton(graphics,text=tr(title),variable=value,command=lambda:setattr(self,'graphics_dirty',True)).pack(anchor='w',pady=5)
  self.graphics_apply=ttk.Button(graphics,text=tr('Auswahl vormerken'),command=self.graphics_command);self.graphics_apply.pack(anchor='w',pady=10)
  self.graphics_info=tk.StringVar();ttk.Label(graphics,textvariable=self.graphics_info,wraplength=800).pack(anchor='w',pady=10)
  timings=ttk.Frame(tabs,padding=8);tabs.add(timings,text=tr('Übergangszeiten'))
  ttk.Label(timings,text=tr('Gemessen ab Trigger-Erkennung. Warten umfasst Vorbereitung und Dialoge; Laden endet bei bestätigtem Ziel und Spawn. Bis zu 32 Übergänge dieses Laufs.'),wraplength=800).pack(anchor='w',pady=(0,8))
  self.timings=ttk.Treeview(timings,columns=('source','target','wait','load','total','status'),show='headings',height=18)
  for key,label,width in [('source','Von',190),('target','Nach',190),('wait','Warten (ms)',95),('load','Laden (ms)',95),('total','Gesamt (ms)',95),('status','Status',150)]:
   self.timings.heading(key,text=tr(label));self.timings.column(key,width=width,minwidth=60)
  tscroll=ttk.Scrollbar(timings,command=self.timings.yview);tscroll.pack(side='right',fill='y');self.timings.configure(yscrollcommand=tscroll.set);self.timings.pack(fill='both',expand=True)
  self.details=tk.Text(overview,wrap='word',font=(font_family(),10),state='disabled');scroll=ttk.Scrollbar(overview,command=self.details.yview);self.details.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.details.pack(fill='both',expand=True)
  ttk.Label(actions,text=tr('Diese Aktionen verändern den aktuellen Lauf. Vor jedem Eingriff wird eine Sicherung angelegt.\nDer Lauf bleibt danach als Testlauf gekennzeichnet.'),wraplength=800).pack(anchor='w',pady=(0,12))
  ttk.Checkbutton(actions,text=tr('Testaktionen für diesen Lauf freigeben'),variable=self.enabled).pack(anchor='w')
  self.combos={};self.buttons=[];self.options={}
  for kind,title,action in [('spots',tr('Zu einem verfügbaren Randomizer-Punkt teleportieren'),'teleport'),('items',tr('Item vergeben'),'grant_item'),('characters',tr('Charakter freischalten'),'grant_character')]:
   box=ttk.LabelFrame(actions,text=title,padding=10);box.pack(fill='x',pady=10)
   c=ttk.Combobox(box,state='readonly',width=55);c.pack(side='left',fill='x',expand=True);self.combos[kind]=c
   b=ttk.Button(box,text=tr('Ausführen'),command=lambda k=kind,a=action:self.command(k,a));b.pack(side='right',padx=(10,0));self.buttons.append(b)
  ttk.Label(actions,text=tr('Es gelten weiterhin die Regeln des Seeds, die Gastly-Voraussetzung und die Ziel-Liste. Während des Ladens oder einer Belohnungsanimation sind Testaktionen gesperrt.'),wraplength=800).pack(anchor='w',pady=8)
  ttk.Label(record,text=tr('Strg+Alt+M speichert sofort einen Problembericht mit bis zu zwei Minuten Vorlauf, auch bei geschlossenem Debugfenster. Für längere Abläufe kannst du eine Aufzeichnung starten. Beschreibe hier optional, was du erwartet hast.'),wraplength=800).pack(anchor='w')
  row=ttk.Frame(record);row.pack(fill='x',pady=12);self.record_button=ttk.Button(row,text=tr('Aufzeichnung starten'),command=self.start_record);self.record_button.pack(side='left');ttk.Button(row,text=tr('Bericht / Aufzeichnung speichern'),command=self.save_record).pack(side='left',padx=8)
  ttk.Button(record,text=tr('Letzten Fehlerbericht exportieren'),command=self.export_error).pack(anchor='w',pady=4)
  ttk.Label(record,textvariable=self.record_status).pack(anchor='w')
  ttk.Label(record,text=tr('Was sollte passieren? Was ist stattdessen passiert?'),padding=(0,12,0,5)).pack(anchor='w')
  self.note=tk.Text(record,height=8,wrap='word');self.note.pack(fill='both',expand=True)
  row=ttk.Frame(record);row.pack(fill='x',pady=12);ttk.Button(row,text=tr('Bericht kopieren'),command=lambda:self.copy(report_text(self.state,self.note.get('1.0','end-1c')))).pack(side='left');ttk.Button(row,text=tr('Berichtordner öffnen'),command=self.open_folder).pack(side='left',padx=8);ttk.Button(row,text=tr('Dateipfad kopieren'),command=lambda:self.copy(str(self.recorder.last_export or ''))).pack(side='left')
  ttk.Label(record,text=tr('Der Bericht enthält Zustände, Grafikwechsel und einen Screenshot nur des Spielfensters, falls verfügbar. Spielstände und das Charakterprofil werden nicht mitgeschickt.'),wraplength=800).pack(anchor='w')
  ttk.Label(self.root,textvariable=self.notice,padding=10,wraplength=850).pack(fill='x')
  self.root.protocol('WM_DELETE_WINDOW',self.hide);self.watch();self.root.after(40,self.pump)
 def refresh_audit(self):
  from trigger_audit import rows
  for item in self.audit.get_children():self.audit.delete(item)
  for row in rows(self.base):self.audit.insert('', 'end',text=row['name'],values=[tr(row[k]) for k in ('start','exit','reset','hacks','natural')])
 def export_error(self):
  try:
   data=read_json(self.base/'debug-reports/latest-error.json',{});source=Path(data.get('path',''))
   if source.parent.resolve()!=(self.base/'debug-reports').resolve() or not source.is_file():self.notice.set(tr('Noch kein automatischer Fehlerbericht vorhanden.'));return
   dest=filedialog.asksaveasfilename(parent=self.root,title=tr('Letzten Fehlerbericht exportieren'),initialfile=source.name,defaultextension='.zip',filetypes=[('ZIP','*.zip')])
   if dest:
    if Path(dest).resolve()!=source.resolve():shutil.copy2(source,dest)
    self.notice.set(tr('Gespeichert: ')+str(dest))
  except OSError as e:self.notice.set(str(e))
 def copy(self,text):
  if text:self.root.clipboard_clear();self.root.clipboard_append(text);self.notice.set(tr('In die Zwischenablage kopiert.'))
 def open_folder(self):
  self.recorder.folder.mkdir(exist_ok=True)
  if os.name=='nt':os.startfile(self.recorder.folder);return
  subprocess.Popen(['xdg-open',str(self.recorder.folder)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def watch(self):write_json(self.folder/'watch.json',{'observe':self.visible or bool(self.recorder.stream),'window_pid':os.getpid(),'visible':self.visible,'recording':bool(self.recorder.stream)})
 def show(self):self.visible=True;self.root.deiconify();self.root.lift();self.root.focus_force();self.watch()
 def hide(self):self.visible=False;self.root.withdraw();self.watch()
 def allowed_focus(self):
  try:
   if self.visible and self.root.focus_displayof() is not None:return True
   if os.name=='nt':
    from windows_api import user,pid
    from host_platform import owned_process
    current=pid(user.GetForegroundWindow())
    return current in (os.getpid(),self.host.pid) or owned_process(psutil.Process(current),self.base)
   root=self.x.screen().root;p=root.get_full_property(self.x.intern_atom('_NET_ACTIVE_WINDOW'),0)
   if p is None or not p.value[0]:return False
   w=self.x.create_resource_object('window',int(p.value[0]));prop=w.get_full_property(self.x.intern_atom('_NET_WM_PID'),0)
   if prop is None:return False
   pid=int(prop.value[0])
   if pid in (os.getpid(),self.host.pid):return True
   proc=psutil.Process(pid)
   if Path(proc.cwd()).resolve()==(self.base/'IWBTB').resolve():return Path(proc.environ().get('WINEPREFIX','/missing')).resolve()==(self.base/'wineprefix').resolve()
   return proc.environ().get('BOSHY_TRACKER_HOST')==str(self.host.pid)
  except Exception:return False
 def hotkey(self):
  if os.name=='nt':
   from windows_api import key_down as down
  else:
   keys=self.x.query_keymap()
   def down(name):code=self.keys[name];return bool(keys[code//8]&(1<<(code%8)))
  modifiers=(down('Control_L') or down('Control_R')) and (down('Alt_L') or down('Alt_R'))
  held=modifiers and down('d');marked=modifiers and down('m');eligible=self.allowed_focus() if held or marked else False
  if self.chord.update(held,eligible):self.hide() if self.visible else self.show()
  if self.marker_chord.update(marked,eligible):self.mark_problem()
 def mark_problem(self):
  if self.closing or self.marker_future is not None or time.monotonic()-self.marker_last<3:return
  if not self.state:self.notice.set(tr('Noch keine Diagnosedaten vorhanden.'));return
  frozen,state,note=self.recorder.marker_snapshot(self.state,self.note.get('1.0','end-1c'))
  self.marker_future=self.exporter.submit(frozen.export_marker,state,note);self.marker_last=time.monotonic()
  self.marker_button.configure(state='disabled');self.notice.set(tr('Problembericht wird gespeichert …'))
 def marker_result(self):
  if self.marker_future is None or not self.marker_future.done():return
  try:
   path=self.marker_future.result();self.recorder.last_export=path;self.notice.set(tr('Gespeichert: ')+str(path))
   if not self.visible and shutil.which('notify-send'):
    subprocess.Popen(['notify-send','--app-name=Boshy Randomizer','--expire-time=4000',str(tr('Problembericht gespeichert')),path.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  except Exception as e:self.notice.set(tr('Bericht konnte nicht gespeichert werden: ')+str(e))
  finally:self.marker_future=None;self.marker_button.configure(state='normal')
 def start_record(self):
  try:self.recorder.start();self.notice.set(tr('Aufzeichnung läuft, auch wenn du das Debugfenster versteckst.'));self.watch()
  except OSError as e:self.notice.set(tr('Aufzeichnung konnte nicht starten: ')+str(e))
 def save_record(self):
  try:
   path=self.recorder.finish(self.note.get('1.0','end-1c'),self.state);self.notice.set(tr('Gespeichert: ')+str(path));self.watch()
  except (OSError,ValueError) as e:self.notice.set(tr('Bericht konnte nicht gespeichert werden: ')+str(e))
 def command(self,kind,action):
  if not self.enabled.get():self.notice.set(tr('Bitte zuerst Testaktionen für diesen Lauf freigeben.'));return
  if self.pending:self.notice.set(tr('Bitte das Ergebnis der laufenden Testaktion abwarten.'));return
  c=self.combos[kind];index=c.current();rows=self.options.get(kind,[])
  if not 0<=index<len(rows):return
  if time.time()-self.state.get('time',0)>3:self.notice.set(tr('Live-Daten sind veraltet; bitte warten.'));return
  request=dict(session=self.folder.name,created_at=time.time(),run_id=self.state.get('run_id'),binding=self.state.get('binding'),frame=self.state.get('last',{}).get('frame'),enabled=True,action=action,value=rows[index]['key'])
  identity=uuid.uuid4().hex;write_json(self.folder/('request-'+identity+'.json'),request);self.pending[identity]=time.time();self.notice.set(tr('Testaktion wird geprüft …'))
 def graphics_command(self):
  if self.pending or self.state.get('phase')!='running' or time.time()-self.state.get('time',0)>3:return
  mask=sum(k for k,v in self.graphics_vars.items() if v.get())
  identity=uuid.uuid4().hex
  request=dict(session=self.folder.name,created_at=time.time(),run_id=self.state.get('run_id'),binding=self.state.get('binding'),enabled=False,action='graphics_mask',value=mask)
  write_json(self.folder/('request-'+identity+'.json'),request);self.pending[identity]=time.time();self.graphics_dirty=False
  self.notice.set(tr('Grafikauswahl wird geprüft …'))
 def render(self):
  names={r['key']:localize(r['label'].rsplit(' · ',1)[0]) for r in self.state.get('choices',{}).get('spots',[])}
  for item in self.timings.get_children():self.timings.delete(item)
  statuses={'pending':'Wartet','loading':'Lädt','arrived':'Angekommen','confirmed':'Bestätigt','already_at_target':'Bereits am Ziel','interrupted':'Unterbrochen'}
  for row in reversed(self.state.get('transition_timings',[])):
   values=[names.get(row.get(k),row.get(k) or '–') for k in ('source','target')]
   values += ['–' if row.get(k) is None else str(round(row[k],1)) for k in ('detection_to_request_ms','request_to_arrival_ms','total_ms')]
   status=str(tr(statuses.get(row['status'],row['status'])))
   if row.get('elapsed_ms') is not None:status+=' · '+str(round(row['elapsed_ms']/1000,1))+' s'
   self.timings.insert('','end',values=values+[status])
  s=self.state
  graphic=s.get('graphics',{});wanted=graphic.get('requested_disabled',0);applied=graphic.get('applied_disabled',0)
  if not self.graphics_dirty and not self.pending:
   for bit,value in self.graphics_vars.items():value.set(bool(wanted&bit))
  self.graphics_info.set(tr('Aktiver Hintergrund: {0}\nSpeicher: {1} MiB\nStatus: {2}',str(graphic.get('background_set','–')),str(graphic.get('memory_rss_mib','–')),str(tr('Wirksam') if wanted==applied else tr('Wartet auf Levelwechsel'))))
  self.graphics_apply.configure(state='normal' if s.get('phase')=='running' and not self.pending else 'disabled')
  last=s.get('last',{});p=s.get('progress',{});obs=s.get('observed',{})
  from native_models import location
  phase={'menu':tr('Hauptmenü'),'loading':tr('Wird geladen'),'running':tr('Lauf aktiv'),'ordinary':tr('Normaler Spielstand'),'stopped':tr('Beendet')}.get(s.get('phase'),s.get('phase',tr('Warte …')))
  self.status.set(tr('{0} · Speicherplatz {1} · {2}', str(phase), str(s.get('slot', s.get('selected_slot', '–'))), localize(location(last.get('frame'))) if last else '–')+(tr(' · TESTLAUF') if s.get('debug_modified') else ''))
  gate=p.get('completion_gate',{});spot=p.get('trigger_spot',p.get('spot'));candidate=gate.get('candidate')
  if p.get('pending'):reason=tr('Der nächste Punkt wurde angefordert. Warte auf bestätigte Ankunft.')
  elif p.get('dialog_wait'):reason=tr('Ein Belohnungsfenster muss zuerst bestätigt werden.')
  elif obs.get('beta_boss'):
   beta=p.get('beta_gate',{});hp=obs['beta_boss'].get('hp')
   reason=(tr('Intro läuft: Boss unverwundbar. S überspringt das Intro.') if obs['beta_boss'].get('intro_active') else tr('Boshy ist gestorben. Kein Boss-Übergang.') if not obs['beta_boss'].get('player_alive') else tr('Boss-Tod erkannt. Kurze Bestätigung vor dem automatischen Übergang.') if beta.get('death_seen') else tr('Beta-Boss: {0} Lebenspunkte. Warte auf den bestätigten Boss-Tod.', str(hp)))
  elif p.get('miniboss_gate',{}).get('identity'):
   mini=p['miniboss_gate'];sample=obs.get('miniboss') or {}
   reason=(tr('Miniboss-Übergang erkannt: ')+str(mini['candidate']) if mini.get('candidate') else tr('Miniboss: Startbereich bestätigt. Warte auf Ausgang oder Sieg.') if mini.get('armed') else tr('Miniboss: Ankunft gesperrt. Warte auf den tatsächlichen Eintritt.'))
   if mini['identity'][-1]=='kracko':reason+=tr(' Kracko: {0} Lebenspunkte.', str(sample.get('hp', '–')))
  elif gate.get('won'):reason=tr('Boss besiegt. Warte auf den zugeordneten Ausgang; R allein wechselt die Route nicht.')
  elif candidate:reason=tr('Abschluss erkannt: ')+str(candidate)+tr('. Warte auf das Ende der Animation.')
  elif not gate.get('seen_origin'):reason=tr('Warte darauf, dass der zugehörige Startbereich beobachtet wird.')
  else:reason=tr('Warte auf einen bestätigten Levelabschluss, regulären Ausgang oder Boss-Sieg.')
  if s.get('phase')!='running':reason=tr('Trigger werden erst im geladenen Randomizer-Lauf ausgewertet.')
  explanation=s.get('trigger_explanation',{})
  if explanation:reason=str(tr(explanation['reason_key'],*explanation.get('reason_args',[]))) if explanation.get('reason_key') else str(localize(explanation['reason']))
  if explanation:reason+=tr('\nExpected: {0}',explanation['expected'])+tr('\nRules: {0}',explanation['rules_version'][:20])
  if explanation:reason+=tr('\nObserved room: {0} · Expected rooms: {1}',str(explanation.get('evidence',{}).get('frame','–')),', '.join(map(str,explanation.get('evidence',{}).get('expected_frames',[]))) or '–')
  lines=[tr('Aktualisiert: {0}', str(time.strftime('%H:%M:%S', time.localtime(s.get('time', time.time()))))),tr('Spielkopie: {0}', str(s.get('game_root', '–'))),f"Seed: {s.get('seed','–')}",'', tr('WARUM GEHT ES GERADE WEITER – ODER NICHT?'),reason,'',tr('Aktiver Punkt: {0}', str(spot or '–')),tr('Boshy-Position: {0}', str(s.get('player_position', '–'))),tr('Gespeicherter Kontrollpunkt: {0}', str(obs.get('checkpoint', '–'))),tr('Route: Schritt {0} von {1}', str(p.get('index', '–')), str(p.get('limit', '–'))),tr('Ausgangsraum beobachtet: {0}', tr('Ja' if gate.get('seen_origin') else 'Nein')),tr('Szene stabil: {0}  /  R gedrückt: {1}', str(obs.get('settled', '–')), str(obs.get('restart_down', '–'))),tr('Gastly-Ablauf: {0}', str(last.get('route', {}).get('phase', '–'))),tr('Nativer Patch: {0}  /  Fehler: {1}', str(last.get('hook', {}).get('status', '–')), str(last.get('hook', {}).get('errors', '–'))),'',tr('BEOBACHTETE ABSCHLUSSMERKMALE')]
  for name,value in (gate.get('previous') or {}).items():
   lines.append(tr('{0}: Spiel {1} / gespeichert {2} / bestätigt {3}', str(name), str(obs.get('live_achievements', {}).get(name, '–')), str(obs.get('disk_achievements', {}).get(name, '–')), str(value)))
  spawn=s.get('spawn_guard')
  if spawn:lines+=['',tr('Zielreset: {0} · Soll: {1} · Boshy: {2}',tr('Bestätigt') if spawn['status']=='confirmed' else tr('Nicht bestätigt'),str(spawn['expected']) if spawn.get('coordinates_checked') else tr('Nativer Boss-Start'),str(spawn.get('position')))]
  lines+=['',tr('LETZTE ÜBERGÄNGE')]
  for row in p.get('transition_trace',[])[-10:]:
   when=time.strftime('%H:%M:%S',time.localtime(row.get('time',0)));details=row.get('reason') or row.get('target') or row.get('spot','')
   lines.append(f"{when}  {row.get('event','')} · {details}")
  lines+=['',tr('DEBUG-EREIGNISSE')]
  for row in s.get('events',[])[-10:]:lines.append(time.strftime('%H:%M:%S',time.localtime(row['time']))+'  '+row['event']+' · '+str(row.get('message',row.get('value',''))))
  lines+=['',tr('Die vollständigen Messwerte stehen im gespeicherten Bericht.')]
  if s.get('observation_error'):lines.insert(1,tr('Beobachtung fehlgeschlagen: ')+s['observation_error'])
  old=self.details.yview();self.details.configure(state='normal');self.details.delete('1.0','end');self.details.insert('1.0','\n'.join(lines));self.details.configure(state='disabled');self.details.yview_moveto(old[0])
  for kind,c in self.combos.items():
   rows=s.get('choices',{}).get(kind,[])
   if rows!=self.options.get(kind):
    selected=c.get();self.options[kind]=rows;c.configure(values=[localize(r['label']) for r in rows]);labels=[localize(r['label']) for r in rows]
    if rows:c.current(labels.index(selected) if selected in labels else 0)
    else:c.set('')
  can=s.get('phase')=='running' and s.get('run_id') and not p.get('pending') and not p.get('dialog_wait') and time.time()-s.get('time',0)<3
  for b in self.buttons:b.configure(state='normal' if can and not self.pending else 'disabled')
 def stop(self):
  if self.closing:return
  self.closing=True
  if self.recorder.stream:self.save_record()
  self.exporter.shutdown(wait=False)
  if self.x:self.x.close()
  self.root.destroy()
 def pump(self):
  try:
   if not self.host.is_running() or self.host.create_time()!=self.birth or self.host.status()==psutil.STATUS_ZOMBIE:self.stop();return
   state=read_json(self.folder/'state.json',{})
   if state:
    self.state=state;self.recorder.note=self.note.get('1.0','end-1c');self.recorder.observe(state)
    if state.get('phase')=='stopped':self.stop();return
    if self.run!=state.get('run_id'):self.run=state.get('run_id');self.enabled.set(False);self.graphics_dirty=False
   self.hotkey();self.marker_result()
   for identity,started in list(self.pending.items()):
    response=read_json(self.folder/('response-'+identity+'.json'))
    if response:self.notice.set((tr('Erfolgreich: ') if response.get('ok') else tr('Abgewiesen: '))+response.get('message',''));del self.pending[identity]
    elif time.time()-started>15:self.notice.set(tr('Noch keine Bestätigung. Die Aktion wird nicht wiederholt; bitte Bericht speichern.'));del self.pending[identity]
   if self.visible and getattr(self,'rendered',None)!=self.state.get('sequence'):self.render();self.rendered=self.state.get('sequence')
   active=bool(self.recorder.stream);self.record_button.configure(state='disabled' if active else 'normal');self.record_status.set((tr('Aufzeichnung läuft · ') if active else tr('Bereit · '))+tr('{0} Zustände im Vorlauf · {1} KB aufgezeichnet', str(len(self.recorder.ring)), str(self.recorder.bytes // 1024)))
   if self.recorder.notice:self.notice.set(self.recorder.notice);self.recorder.notice='';self.watch()
  except (psutil.NoSuchProcess,psutil.ZombieProcess):self.stop();return
  except Exception as e:self.notice.set(tr('Diagnosefehler: ')+str(e))
  self.root.after(40,self.pump)

def main():
 p=argparse.ArgumentParser();p.add_argument('--host',type=int,required=True);p.add_argument('--session',required=True);a=p.parse_args();Window(a.host,a.session).root.mainloop()
if __name__=='__main__':main()
