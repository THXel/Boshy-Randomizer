"""Optional independent diagnostics window; Ctrl+Alt+D, scoped to this randomizer."""
from ui_i18n import tr, display as localize, font_path, font_family, configure_tk, LANGUAGE, Localized
import argparse,os,time,uuid,json,subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import psutil
from Xlib import display,XK
from debug_data import Recorder,Chord,read_json,write_json,report_text

class Window:
 def __init__(self,host,folder):
  self.base=Path(__file__).resolve().parent;self.folder=Path(folder);self.host=psutil.Process(host);self.birth=self.host.create_time()
  self.root=tk.Tk();configure_tk(self.root);self.root.withdraw();self.root.title('Boshy Randomizer – Debug');self.root.geometry('900x720');self.root.minsize(650,500)
  self.visible=False;self.state={};self.run=None;self.pending={};self.recorder=Recorder(self.base);self.chord=Chord();self.x=display.Display();self.closing=False
  self.keys={n:self.x.keysym_to_keycode(XK.string_to_keysym(n)) for n in ('Control_L','Control_R','Alt_L','Alt_R','d')}
  self.status=tk.StringVar(value=tr('Warte auf den Randomizer …'));self.notice=tk.StringVar(value=tr('Strg+Alt+D öffnet oder versteckt dieses Fenster.'));self.record_status=tk.StringVar();self.enabled=tk.BooleanVar(value=False)
  bar=ttk.Frame(self.root,padding=10);bar.pack(fill='x');ttk.Label(bar,text=tr('Randomizer-Diagnose'),font=('',16,'bold')).pack(side='left');ttk.Button(bar,text=tr('Seed kopieren'),command=lambda:self.copy(self.state.get('share_seed',''))).pack(side='right')
  ttk.Label(self.root,textvariable=self.status,padding=(10,0),wraplength=850).pack(fill='x')
  tabs=ttk.Notebook(self.root);tabs.pack(fill='both',expand=True,padx=10,pady=10)
  overview=ttk.Frame(tabs,padding=8);actions=ttk.Frame(tabs,padding=12);record=ttk.Frame(tabs,padding=12)
  tabs.add(overview,text=tr('Live-Übersicht'));tabs.add(actions,text=tr('Testaktionen'));tabs.add(record,text=tr('Aufzeichnung & Bericht'))
  self.details=tk.Text(overview,wrap='word',font=(font_family(),10),state='disabled');scroll=ttk.Scrollbar(overview,command=self.details.yview);self.details.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.details.pack(fill='both',expand=True)
  ttk.Label(actions,text=tr('Diese Aktionen verändern den aktuellen Lauf. Vor jedem Eingriff wird eine Sicherung angelegt.\nDer Lauf bleibt danach als Testlauf gekennzeichnet.'),wraplength=800).pack(anchor='w',pady=(0,12))
  ttk.Checkbutton(actions,text=tr('Testaktionen für diesen Lauf freigeben'),variable=self.enabled).pack(anchor='w')
  self.combos={};self.buttons=[];self.options={}
  for kind,title,action in [('spots',tr('Zu einem verfügbaren Randomizer-Punkt teleportieren'),'teleport'),('items',tr('Item vergeben'),'grant_item'),('characters',tr('Charakter freischalten'),'grant_character')]:
   box=ttk.LabelFrame(actions,text=title,padding=10);box.pack(fill='x',pady=10)
   c=ttk.Combobox(box,state='readonly',width=55);c.pack(side='left',fill='x',expand=True);self.combos[kind]=c
   b=ttk.Button(box,text=tr('Ausführen'),command=lambda k=kind,a=action:self.command(k,a));b.pack(side='right',padx=(10,0));self.buttons.append(b)
  ttk.Label(actions,text=tr('Es gelten weiterhin die Regeln des Seeds, die Gastly-Voraussetzung und die Ziel-Liste. Während des Ladens oder einer Belohnungsanimation sind Testaktionen gesperrt.'),wraplength=800).pack(anchor='w',pady=8)
  ttk.Label(record,text=tr('Bei einem Problem: Aufzeichnung starten, den Ablauf spielen und hier beschreiben, was du erwartet hast. Bis zu zwei Minuten Vorlauf werden automatisch mitgenommen.'),wraplength=800).pack(anchor='w')
  row=ttk.Frame(record);row.pack(fill='x',pady=12);self.record_button=ttk.Button(row,text=tr('Aufzeichnung starten'),command=self.start_record);self.record_button.pack(side='left');ttk.Button(row,text=tr('Bericht / Aufzeichnung speichern'),command=self.save_record).pack(side='left',padx=8)
  ttk.Label(record,textvariable=self.record_status).pack(anchor='w')
  ttk.Label(record,text=tr('Was sollte passieren? Was ist stattdessen passiert?'),padding=(0,12,0,5)).pack(anchor='w')
  self.note=tk.Text(record,height=8,wrap='word');self.note.pack(fill='both',expand=True)
  row=ttk.Frame(record);row.pack(fill='x',pady=12);ttk.Button(row,text=tr('Bericht kopieren'),command=lambda:self.copy(report_text(self.state,self.note.get('1.0','end-1c')))).pack(side='left');ttk.Button(row,text=tr('Berichtordner öffnen'),command=self.open_folder).pack(side='left',padx=8);ttk.Button(row,text=tr('Dateipfad kopieren'),command=lambda:self.copy(str(self.recorder.last_export or ''))).pack(side='left')
  ttk.Label(record,text=tr('Die ZIP-Datei kannst du zusammen mit deiner Beschreibung an Codex geben. Sie enthält Zustände, Übergänge, Fehler und Testeingriffe. Spielstände und das globale Charakterprofil werden nicht mitgeschickt.'),wraplength=800).pack(anchor='w')
  ttk.Label(self.root,textvariable=self.notice,padding=10,wraplength=850).pack(fill='x')
  self.root.protocol('WM_DELETE_WINDOW',self.hide);self.watch();self.root.after(40,self.pump)
 def copy(self,text):
  if text:self.root.clipboard_clear();self.root.clipboard_append(text);self.notice.set(tr('In die Zwischenablage kopiert.'))
 def open_folder(self):
  self.recorder.folder.mkdir(exist_ok=True);subprocess.Popen(['xdg-open',str(self.recorder.folder)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def watch(self):write_json(self.folder/'watch.json',{'observe':self.visible or bool(self.recorder.stream),'window_pid':os.getpid(),'visible':self.visible,'recording':bool(self.recorder.stream)})
 def show(self):self.visible=True;self.root.deiconify();self.root.lift();self.root.focus_force();self.watch()
 def hide(self):self.visible=False;self.root.withdraw();self.watch()
 def allowed_focus(self):
  try:
   if self.visible and self.root.focus_displayof() is not None:return True
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
  keys=self.x.query_keymap()
  def down(name):code=self.keys[name];return bool(keys[code//8]&(1<<(code%8)))
  held=(down('Control_L') or down('Control_R')) and (down('Alt_L') or down('Alt_R')) and down('d')
  if self.chord.update(held,self.allowed_focus() if held else False):self.hide() if self.visible else self.show()
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
 def render(self):
  s=self.state;last=s.get('last',{});p=s.get('progress',{});obs=s.get('observed',{})
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
  if explanation:reason=str(localize(explanation['reason']))+tr('\nErwartet: ')+str(localize(explanation['expected']))+tr('\nRegelsatz: ')+explanation['rules_version'][:20]
  lines=[tr('Aktualisiert: {0}', str(time.strftime('%H:%M:%S', time.localtime(s.get('time', time.time()))))),tr('Spielkopie: {0}', str(s.get('game_root', '–'))),f"Seed: {s.get('seed','–')}",'', tr('WARUM GEHT ES GERADE WEITER – ODER NICHT?'),reason,'',tr('Aktiver Punkt: {0}', str(spot or '–')),tr('Boshy-Position: {0}', str(s.get('player_position', '–'))),tr('Gespeicherter Kontrollpunkt: {0}', str(obs.get('checkpoint', '–'))),tr('Route: Schritt {0} von {1}', str(p.get('index', '–')), str(p.get('limit', '–'))),tr('Ausgangsraum beobachtet: {0}', tr('Ja' if gate.get('seen_origin') else 'Nein')),tr('Szene stabil: {0}  /  R gedrückt: {1}', str(obs.get('settled', '–')), str(obs.get('restart_down', '–'))),tr('Gastly-Ablauf: {0}', str(last.get('route', {}).get('phase', '–'))),tr('Nativer Patch: {0}  /  Fehler: {1}', str(last.get('hook', {}).get('status', '–')), str(last.get('hook', {}).get('errors', '–'))),'',tr('BEOBACHTETE ABSCHLUSSMERKMALE')]
  for name,value in (gate.get('previous') or {}).items():
   lines.append(tr('{0}: Spiel {1} / gespeichert {2} / bestätigt {3}', str(name), str(obs.get('live_achievements', {}).get(name, '–')), str(obs.get('disk_achievements', {}).get(name, '–')), str(value)))
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
  self.x.close();self.root.destroy()
 def pump(self):
  try:
   if not self.host.is_running() or self.host.create_time()!=self.birth or self.host.status()==psutil.STATUS_ZOMBIE:self.stop();return
   self.hotkey();state=read_json(self.folder/'state.json',{})
   if state:
    self.state=state;self.recorder.note=self.note.get('1.0','end-1c');self.recorder.observe(state)
    if state.get('phase')=='stopped':self.stop();return
    if self.run!=state.get('run_id'):self.run=state.get('run_id');self.enabled.set(False)
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
