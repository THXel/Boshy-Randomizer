"""Check seed-to-game evidence and write a bounded, reproducible result summary."""
import configparser
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'outputs/Fusion-Seed-20261023'
sys.path.insert(0, str(ROOT/'work/Boshy-Randomizer/src/python/rules'))
import fusion_route as f

def ini(text):
    result = configparser.ConfigParser(interpolation=None)
    result.read_string(text)
    return result

def digest(path):
    with path.open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()

cases=[]
for seed in ('fusion-1','fusion-2'):
    plan=json.loads((OUT/seed/'plan.json').read_text())
    result=json.loads((OUT/('live-'+seed)/'result.json').read_text())
    arrival=ini(result['save_arrival']);restart=ini(result['save_restart'])
    for save in (arrival,restart):
        for key,field in [('frame','frame'),('xPos','x'),('yPos','y')]:
            assert save.getint('Positions',key)==plan['destination'][field]
        assert save.get(f.GROUP,'Binding')==plan['binding']
        assert bytes.fromhex(save.get(f.GROUP,'SeedHex')).decode('ascii')==seed
        assert save.getint(f.GROUP,'CheetahDone')==1
    assert result['same_process_at_end']
    assert result['hidden_exit_contact']['boss_present']
    assert ini(result['hidden_exit_contact']['save']).getint('Positions','frame')==54
    assert not result['death_before_exit']['player_present']
    assert ini(result['death_before_exit']['save']).getint('Positions','frame')==54
    assert not result['player_after_death']
    assert 'Player' in result['restart_objects']
    assert restart.getint('Stats','Deaths')>arrival.getint('Stats','Deaths')
    cases.append({'seed':seed,'shared_seed':plan['shared_seed'],'route':plan['route'],
                  'destination':plan['destination'],'binding':plan['binding'],
                  'live_exit_death_restart_and_gate':True})
cold=json.loads((ROOT/'outputs/Fusion-Seed-Cold2-20261023/rebuilt-cheetah-seed/result.json').read_text())
assert cold['frame']==15 and cold['reused_save']
assert ini(cold['save_after']).get(f.GROUP,'Binding')==cases[1]['binding']
assert (ROOT/'outputs/Fusion-Seed-Cold1-20261023/cold-entry.png').is_file()
original=Path('/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe')
assert digest(original)=='dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806'
exe=Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-seed.exe')
assert digest(exe)==f.BUILD_SHA256
summary={'schema':f.SCHEMA,'scope':'Cheetahman outgoing edge only; no GUI integration',
         'cases':cases,'unit_tests':{'adapter':7,'event_and_fixture':8,'export_boundary':4,'existing_BR12':14},
         'seed_property_checks':200,'existing_random_settings_checks':1000,
         'game_sha256':digest(exe),'original_unchanged':True,
         'mfa_sha256':digest(OUT/'project/I Wanna Be The Boshy.seed.mfa'),
         'cold1':'../Fusion-Seed-Cold1-20261023/cold-entry.png',
         'cold2':'../Fusion-Seed-Cold2-20261023/rebuilt-cheetah-seed/entry.png',
         'limitations':['Synthetic starting saves; boss phase 6499 and player-position fixtures.',
                        'Temporary source-arena death suppression; destination death tests unprotected.',
                        'Cold1 needed one extra focused Return after initial menu automation timed out.',
                        'No complete route, item/music/sprite randomization, GUI, Windows 11 or installer integration.']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'LIESMICH.txt').write_text('''Fusion: Verbindung mit dem bestehenden Seed-Routenplan — 23.10.2026

Ergebnis
Die Ziele stammen jetzt direkt aus run_settings.route des bestehenden
Randomizers. Der Adapter würfelt nicht erneut und ersetzt keine Ziele.
Zwei BR12-Codes wurden exportiert und im kompilierten Spiel geprüft:
- fusion-1: Castlevania -> Cheetahman -> Prehistorik -> Solgryn.
- fusion-2: Prehistorik -> Cheetahman -> Castlevania -> Solgryn.
Getestet wurde jeweils nur der Ausgang von Cheetahman. Der Testspielstand
startet dort; vorherige Stationen werden nicht als erledigt ausgegeben.

Korrektur gegenüber dem ersten Prototyp
Prehistorik startet jetzt an der Katalogposition (30,40), nicht mehr am
Test-Checkpoint (200,226). Deshalb neue Schnittstelle FusionRandoV2 und
Bindung an den exakten neuen EXE-Hash. Castlevania bleibt (30,1300).

Nachweise
- Beide berechneten Ziele live erreicht, identischer Prozess blieb aktiv.
- Vorzeitige Berührung des versteckten Ausgangs löste keinen Wechsel aus.
- Tod vor Ausgang ließ Checkpoint bei Cheetahman.
- Tod am Ziel, Todeszähler und R führten wieder zum korrekten Checkpoint.
- Beide Ziellevel nach vollständigem Programmneustart visuell bestätigt.
- Seed und Bindung bleiben über Speichern und Tod erhalten.
- 33 gezielte automatisierte Tests bestanden, darin 200 weitere Seeds
  und 1.000 bestehende BR12-Einstellungskombinationen.
- Nicht unterstützte Ziele, falsche Builds und abweichende Katalogpositionen
  werden vor dem Export abgewiesen. Vorhandene Ausgabeverzeichnisse und
  Spielstände werden nicht überschrieben.

Editor
Drei alte Fusion-Instanzen geschlossen. Zwei hatten Änderungen; vorherige
Dateistände liegen in editor-backups/, die offenen Änderungen wurden beim
Schließen gespeichert. Nur eine Fusion-Instanz bleibt offen. Das neue
Projekt wurde in dieser vorhandenen Instanz geladen und gebaut.

Grenzen und Testbesonderheiten
Die Siegesphase wurde mit Testfixtures verkürzt, kein voller Bosskampf.
Nur im Ausgangsraum zeitweiliger Todesschutz. Keine Zielframe- oder
Fortschrittsänderungen durch den Speicher-Testhelfer: Das Spiel löst
Übergang und Speicherung aus. Der erste Kaltstart benötigte nach einem
Timeout der Menünavigation noch eine fokussierte Enter-Eingabe.
Ein BR12-Test im reinen Python-Export benötigte native Begleitdateien;
derselbe Test im vorhandenen vollständigen Runtime-Export bestand danach.
Kein kompletter Randomizer-Lauf, keine GUI-Verbindung, kein Sprite-/Musik-
oder Item-Randomizer im Fusion-Build, kein Windows-11-/Installer-Test.
Die installierte Spielversion wurde nicht ersetzt; keine Veröffentlichung.

Quellen
work/Boshy-Randomizer/src/python/rules/fusion_route.py: reiner Seed-Adapter.
work/Boshy-Randomizer/tests/runtime/test_fusion_route.py: Regressionen.
work/fusion-lab/export_seed_probe.py: neuer verschlüsselter Testspielstand
  aus einem vorhandenen BR12-Code, --shared CODE --game EXE --out NEU.
work/fusion-lab/transition/: versionierte originale Ausgangsereignisse.
summary.json sowie live-fusion-*/: Hashes, Spielbilder und Zustandsprotokolle.

Nächster Schritt
Weitere echte Ausgangsereignisse (Kracko und Mario) anbinden und mit
unveränderten Seed-Routen prüfen. Danach den vollständigen Laufstart und
die GUI-Verbindung integrieren; unsupported Ziele bleiben bis dahin gesperrt.
''')
print(json.dumps(summary,indent=2))
