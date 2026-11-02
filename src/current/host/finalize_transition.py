"""Summarize measured routing results without treating fixtures as full boss runs."""
from pathlib import Path
import configparser,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'outputs/Fusion-Transition-20261023'
def ini(text):
 c=configparser.ConfigParser();c.read_string(text);return c
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
rows=[]
for label,expected in [('route1',3),('route2',15),('route1-gate',3),('missing',None),('invalid',None)]:
 r=json.loads((out/label/'result.json').read_text());arr=ini(r['save_arrival']);restart=ini(r['save_restart'])
 assert r['pre_victory']['boss_present']
 assert ini(r['pre_victory']['save']).getint('Positions','frame')==54
 if expected:
  assert arr.getint('Positions','frame')==expected
  assert restart.getint('Positions','frame')==expected
  assert arr.getint('FusionRandoV1','CheetahDone')==1
  assert not r['player_after_death'] and 'Player' in r['restart_objects']
  assert restart.getint('Stats','Deaths')>arr.getint('Stats','Deaths')
 else:
  assert not arr.has_option('FusionRandoV1','CheetahDone')
  assert arr.getint('Teleporter','Unlocked')==1
 if 'hidden_exit_contact' in r:
  assert r['hidden_exit_contact']['boss_present']
  assert ini(r['hidden_exit_contact']['save']).getint('Positions','frame')==54
 rows.append({'case':label,'route_target':expected or 'original teleporter room (visually verified)',
 'native_death_and_restart_verified':bool(expected),'same_process_explicit_check':r.get('same_process_at_end'),
 'hidden_exit_gate_tested':'hidden_exit_contact' in r})
exe=Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-transition.exe')
original=Path('/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe')
assert digest(original)=='dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806'
report={'scope':'Private Fusion prototype, one Cheetahman edge, two target checkpoints; Sprite Randomizer OFF',
 'cases':rows,'original_unchanged':True,'original_sha256':digest(original),'exe_sha256':digest(exe),
 'mfa_sha256':digest(out/'I Wanna Be The Boshy.transition.mfa'),
 'cold_load_evidence':{'prehistorik':'../Fusion-Transition-Cold1-20261023/cold-entry.png',
 'castlevania':'../Fusion-Transition-Cold2-20261023/rebuilt-cheetah/entry.png'},
 'fixture_limitations':['Boss phase advanced to 6499, temporary Die fastloop suppression in source arena, Player positions set; no full boss victory claim.',
 'No frame/route/save writes by memory helper; game executes transition and saves checkpoint.',
 'Cold1 menu automation needed an extra focused Return. Cold2 legacy frame/start metadata still names unused fixture 54; save_after and screenshot show actual frame 15.',
 'Invalid fallback post-exit Q snapshot still had Player present; no death verdict from that snapshot. Routed-target death tests both confirmed absence, counter increment and reappearance.']}
(out/'summary.json').write_text(json.dumps(report,indent=2))
(out/'LIESMICH.txt').write_text('''Fusion-Randomizer: erster nativer Cheetahman-Übergang, 23.10.2026

Umgesetzt
- Separates Fusion-Projekt mit den bisherigen neun Alpha-Korrekturen.
- Originale Ausgangsberührung nach der Siegesanimation steuert den Wechsel.
- [FusionRandoV1] CheetahRoute im verschlüsselten aktiven Testspielstand:
  1 = Prehistorik, Frame 3, Checkpoint (200,226).
  2 = Castlevania, Frame 15, Checkpoint (30,1300).
  Fehlend/0/andere Werte = originaler Teleporterraum.
- Vor gültigem Wechsel: Zielposition und Frame speichern, CheetahDone=1,
  originalen save-Fastloop aufrufen, dann originalen Szenenwechsel ausführen.
- Keine externen Prozessneustarts zum Auslösen des Übergangs.

Geprüft im echten kompilierten Spiel unter Wine
- Beide neuen Ziellevel erreicht und visuell kontrolliert.
- Absichtlicher Tod am Ziel, Todeszähler, R und neuer Checkpoint bestätigt.
- Beide Ziellevel nach komplettem Schließen und erneutem Laden erreicht.
- Tod vor Ausgang: Checkpoint bleibt Cheetahman, Frame 54.
- Direkte Berührung des versteckten Ausgangs vor dem Sieg löst Route nicht aus.
- Fehlende Route und Wert 99 führen in den originalen Teleporterraum.
- Sieben automatisierte Struktur-/Testhelferprüfungen bestanden.
- Originale Ini++-Runtime im neuen Build anhand SHA256 bestätigt.
- Installierte Original-EXE unverändert; SHA256 in summary.json.

Testgrenzen
Der Bosskampf wurde mit einer temporären Phase-6499-Fixture verkürzt; dies
ist kein vollständig durchgespielter Bosskampf. Todesschutz nur im privaten
Ausgangsraum, Ziellevel-Tode ohne diesen Schutz. Fixtures setzen Phase und
Spielerposition, niemals Zielframe oder Fortschritt. Der originale Ablauf
führt Siegesanimation, Ausgang, Speicherung und Wechsel aus.
Sprite Randomizer war aus. GUI/Seed-Verbindung, alle übrigen Ausgänge,
Windows 11, Installer und Veröffentlichung sind noch nicht umgesetzt.
Die zusätzliche Todesaufnahme beim ungültigen Fallback ist uneindeutig;
die positiven Todes-/Neustartbefunde beziehen sich auf die neuen Routen.

Dateien
source-audit.json: exakter Eingriff in Abschnitt 101 des Cheetahman-Frames.
summary.json: Ergebnisse, Grenzen, Hashes, Kaltstart-Belege.
route*/result.json und PNGs: Laufzeitzustände und Spielbilder.
Quellen: work/fusion-lab/transition/{events,cheetah}.py,
recover_boshy_transition.py, test_transition.py, transition_probe.py.

Nächster Entwicklungsschritt
Den Seed-/Routenplan des bestehenden Randomizers in ein versioniertes
Fusion-Konfigurationsformat überführen. Danach die bestätigten Trigger
von Kracko und Mario mit derselben nativen Übergangslogik anbinden.
''')
print(json.dumps(report,indent=2))
