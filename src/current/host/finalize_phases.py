"""Validate successful evidence and publish a concise local phase-test report."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/Fusion-Phases-20261023'
CASES = ('original-solgryn-v3', 'rebuilt-solgryn-v3', 'original-sonic-v6', 'rebuilt-sonic-v6')
reports = {name: json.loads((OUT / name / 'result.json').read_text()) for name in CASES}
metrics = {}
for name, report in reports.items():
    assert report.get('complete'), name
    samples = report['samples']
    assert samples and all(s['player'] for s in samples), name
    assert all(s['boss_values'] for s in samples), name
    info = {'captures': len(samples), 'recorded_seconds': samples[-1]['seconds'],
            'player_present_in_all_samples': True,
            'fixture_writes': len(report['writes']),
            'boss_before': report['boss_before']}
    if 'solgryn' in name:
        assert report['climb_entry']['phase'] == 5999
        assert any(s['boss_values'][3] == 60 for s in samples)
        for effect in ('Active 9', 'Active 10'):
            assert any(o['name'] == effect for s in samples for o in s['objects'])
        info['climb_entry_phase'] = 5999
        info['second_health_bar'] = 60
        info['captured_effects'] = ['Active 9', 'Active 10']
    else:
        assert report['hp_fixture'] == 35 and report['difficulty'] == 0
        platforms = [o for s in samples for o in s['objects'] if o['name'] == 'Active 23sonic']
        flames = [o for s in samples for o in s['objects'] if o['name'] == 'Active 17sonic']
        assert platforms and min(o['w'] for o in platforms) == 168
        assert any(o['y'] < 480 and o['y'] + o['h'] > 0 for o in flames)
        info['minimum_platform_width'] = 168
        info['hp_fixture'] = 35
        info['difficulty'] = 'EZ (0)'
    metrics[name] = info

font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
selections = {}
for boss, targets, suffix in [('solgryn', (6248, 6300), 'v3'), ('sonic', (1300,), 'v6')]:
    canvas = Image.new('RGB', (1280, 520 * len(targets)), '#20252b')
    draw = ImageDraw.Draw(canvas)
    rows = []
    for row, phase in enumerate(targets):
        for col, variant in enumerate(('original', 'rebuilt')):
            case = f'{variant}-{boss}-{suffix}'
            # First attack cycle, not a later repeated phase value.
            samples = [s for s in reports[case]['samples'] if s['seconds'] < 35]
            sample = min(samples, key=lambda s: abs(s['boss_values'][0] - phase))
            image = Image.open(OUT / case / sample['image']).convert('RGB')
            assert image.size == (640, 480)
            canvas.paste(image, (640 * col, 520 * row + 40))
            label = 'Original' if variant == 'original' else 'Fusion-Build mit Alpha-Korrektur'
            draw.text((640 * col + 12, 520 * row + 9), f'{label} | Phase {sample["boss_values"][0]}', fill='white', font=font)
            rows.append({'case': case, 'image': sample['image'], 'phase': sample['boss_values'][0]})
    filename = f'{boss.capitalize()}-Vergleich.png'
    canvas.save(OUT / filename)
    selections[filename] = rows

paths = {
    'original': Path('/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe'),
    'rebuilt': Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyGraphics/Boshy-alpha-fixed.exe'),
}
expected = {
    'original': 'dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806',
    'rebuilt': 'd75e8f45c2cc4512a6f6f4d3cf32905dc3b5b118a06754b65158ff3bdec73125',
}
hashes = {}
for name, path in paths.items():
    with path.open('rb') as f:
        hashes[name] = hashlib.file_digest(f, 'sha256').hexdigest()
    assert hashes[name] == expected[name]

summary = {
    'scope': 'Fusion baseline comparison under Linux/Wine; sprite randomizer disabled',
    'cases': metrics, 'comparison_images': selections,
    'exe_hashes': hashes, 'exes_unchanged': True, 'helper_regression_tests_passed': 3,
    'not_verified': ['Regular complete boss victories', 'Full manual climb',
                     'Sprite randomizer integration into Fusion build', 'Windows 11',
                     'Audible music and effects', 'All game fire effects'],
    'excluded_attempts': ['Earlier Solgryn probes with incomplete death suppression',
                          'Sonic v3: 90 HP does not trigger EZ fire phase',
                          'Sonic v4/v5: runtime identification aborted before phase sampling'],
}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
count = sum(v['captures'] for v in metrics.values())
(OUT / 'LIESMICH.txt').write_text(f'''Boshy – gezielte Bossphasen im Fusion-Nachbau
Stand: 23.10.2026

BESTÄTIGT
Sonic: Feuerphase im Original und im korrigierten Fusion-Build erreicht.
Beide Testspielstände laufen auf EZ (Difficulty=0). Deshalb wurden die
Boss-HP von 45 auf 35 gesetzt. Die 90-HP-Schwelle anderer Schwierigkeitsgrade
ist hier ungeeignet; der entsprechende frühe Versuch zählt nicht als Feuertest.
Die Plattform schrumpft in beiden Versionen auf 168 Pixel Breite.
Aufsteigende Feuerwand, kleine Plattform und weiterer Angriff sind aufgenommen.

Solgryn: Erste Phase durch HP=0 beendet. Die originale Übergangssequenz läuft
bis Phase 5999. Nur dort wird die Testfigur einmal an (300,-8) gesetzt, damit
die originale Eingangsbedingung den Kletterabschnitt auslöst. Danach läuft
die Spiellogik weiter. Die zweite Lebensleiste füllt sich auf 60. Feuerstrahl
(Active 10), Folgeeffekt (Active 9) und Plattformen wurden aufgenommen.

Vier erfolgreiche Läufe mit insgesamt {count} Einzelbildern:
- Solgryn: jeweils ca. 60 Sekunden, Original und Fusion-Build.
- Sonic: jeweils ca. 30 Sekunden, Original und Fusion-Build.
Die Spielerfigur ist in allen erfassten Stichproben dieser vier Läufe vorhanden.
Die Vergleichsbilder stellen ähnliche Phasenstände gegenüber; sie sind keine
framegenau synchronisierte Aufnahme und zeigen unterschiedliche Zufallsabläufe.

TESTBEDINGUNGEN
Dies sind gezielte Phasentests mit temporärem Schutz vor den Todesroutinen,
HP-Fixtures und der beschriebenen Solgryn-Positionierung. Keine regulär
gewonnenen vollständigen Bosskämpfe und kein manuell abgeschlossener Aufstieg.
Der Sprite-Randomizer ist ausgeschaltet: geprüft wird die grafische Grundlage
des Nachbaus. Die Integration und Prüfung des Randomizers steht noch aus.
Die Maus bleibt außerhalb des Spielfensters; ihre originale Gefahrenfunktion
wurde nicht aus dem Spiel entfernt.

TESTWERKZEUGE
Der Helfer akzeptiert ausschließlich Prozesse aus C:\\BoshySceneTests.
Zustandsänderungen vergleichen jeweils den erwarteten vorherigen Wert.
Die beiden Runtime-Profile sind an exakte EXE-SHA-256-Werte gebunden.
Nach jedem Neustart wird der aktuelle RunHeader neu gelesen. Für visuelle
Tests werden die Wiederholungszahlen der Fastloops Die/die vorübergehend
auf null gesetzt; die Spieldateien werden nicht verändert.
Drei Regressionstests decken beide Schreibweisen, ANSI/Unicode, wiederholte
Anwendung und verschobene RunHeader nach Neustarts ab.

Wiederholen im Projektverzeichnis:
PYTHONDONTWRITEBYTECODE=1 python3 work/fusion-lab/run_phase_suite.py
Die Tests laufen nacheinander und legen neue Ausgabeordner an. Sie benötigen
denselben Wine-Prefix, die beiden geprüften EXEs und einen freien Spielstart.
Vorhandene Nachweise werden nicht überschrieben.

DATEIEN
Sonic-Vergleich.png: kleine Plattform und Feuerwand.
Solgryn-Vergleich.png: Feuerstrahl und Folgeeffekt.
summary.json: Messwerte, EXE-Prüfsummen und Auswahl der Vergleichsbilder.
Die ausgewerteten Detailaufnahmen liegen in original-solgryn-v3,
rebuilt-solgryn-v3, original-sonic-v6 und rebuilt-sonic-v6.
Frühere Diagnoseversuche sind als solche erhalten und nicht in der Freigabe.

AUSLIEFERUNG UND OFFENES
Die Original-EXE und der Fusion-Testbuild sind unverändert (Hashvergleich).
Keine neue Installation, kein Installer-Update und keine Veröffentlichung.
Audio und Windows 11 wurden in diesem Durchlauf nicht geprüft.
Als nächster Implementierungsschritt bietet sich ein einzelner, direkt an
ein originales Spielereignis gebundener Randomizer-Übergang an, einschließlich
Tod/Neustart und Rückkehr ins Menü. Die vorhandenen nativen Speicheradressen
des alten Randomizers dürfen nicht ungeprüft auf den neuen Build übertragen
werden: Objektkennungen und Runtime-Strukturen unterscheiden sich.
''')
print(json.dumps({'captures': count, 'cases': metrics, 'report': str(OUT / 'LIESMICH.txt')}, ensure_ascii=False))
