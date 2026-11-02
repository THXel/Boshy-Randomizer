"""Summarize the private host milestone with explicit migration boundaries."""

import hashlib, html, json
from pathlib import Path
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-Menu-20261024"


def main():
    tests = (OUT / "tests.log").read_text()
    assert "Ran 85 tests" in tests and tests.rstrip().endswith("OK")
    lifecycle = json.loads((OUT / "lifecycle.json").read_text())
    ui = json.loads((OUT / "ui-results.json").read_text())
    assert lifecycle["passed"] and ui["passed"]
    original = Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    )
    sha = hashlib.sha256(original.read_bytes()).hexdigest()
    assert sha == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
    summary = dict(
        automated_tests=85,
        lifecycle_checks=lifecycle["events"],
        ui_checks=ui["events"],
        rendered_languages=["de", "en", "es", "ru", "ja"],
        selectable_levels=21,
        selectable_bosses=22,
        fixed_finale="Solgryn",
        installed_game_sha256=sha,
        private_only=True,
        installed_or_published=False,
        implementation=[
            "menu_host/draft.py: canonical BR12 routes and renewed seeds",
            "menu_host/store.py: atomic slot references, independent native saves, integrity and process locks",
            "menu_host/runtime.py: owned Wine game, read-only frame observer, normal key/window controls",
            "menu_host/ui.py: private host UI with disabled immutable saved-run settings",
            "menu_host/labels.py: host captions in five languages",
        ],
        limits=[
            "Linux/X11 and the private Fusion Wine prefix only; no Windows 11 installer test",
            "This is a separate private host UI, not final integration into the existing animated in-game menu",
            "No host menu music/animated loading-screen parity yet; existing installed menu is unchanged",
            "Only native routing, graphics, blood and music options are exposed; other extras rejected",
            "Cold resume tested at a checkpoint with death count/seed retained; no complete new host playthrough or all exits rerun",
            "UI tests invoke real Tk widget commands and game keys; not every control was physically mouse-clicked",
            "Clearing a slot archives its pointer and retains a private undo directory",
        ],
        resolved_test_issue="Initial X key taps were too short for 50 Hz polling. Held key input fixed the probe; original failed evidence retained.",
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    checks = "".join(
        "<li>" + html.escape(r["test"]) + " — bestanden</li>"
        for r in lifecycle["events"] + ui["events"]
    )
    images = "".join(
        f'<figure><figcaption>{lang.upper()}</figcaption><a href="menu-{lang}.png"><img src="menu-{lang}.png"></a></figure>'
        for lang in summary["rendered_languages"]
    )
    page = (
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Fusion – Menü und Speicherplätze</title>
<style>body{font:17px system-ui;max-width:1120px;margin:30px auto;padding:24px;background:#111b25;color:#edf5f6}h1,h2,a{color:#9eddd6}.ok{background:#244342;padding:18px;border-radius:10px}img{width:100%}figure{display:inline-block;vertical-align:top;width:46%;margin:10px 1%}code{color:#f0cc91}li{margin:9px 0}figcaption{padding:6px}p{line-height:1.5}</style>
<h1>Menü und Speicherplätze für den nativen Fusion-Build</h1><p>24.10.2026 · Privates Linux/Wine-Testmenü</p>
<p class="ok">85 automatische Tests bestanden. Neue Läufe, F2-Rückkehr, Fortsetzen nach einem Host-Neustart und getrennte Speicherplätze wurden im echten Spiel geprüft.</p>
<p>Das Testmenü exportiert jeden Lauf mit eigener EXE und eigener nativer SaveFile1.ini. Die drei sichtbaren Plätze verweisen auf getrennte Verzeichnisse. Beim Fortsetzen bleiben EXE, Seed, Route, Musik und Grafiken dieses Laufs erhalten. Spielstände mit falscher Bindung, geänderten Routenverbindungen oder veränderter EXE werden abgewiesen.</p>
<p>Die Oberfläche enthält 21 Level und 22 Bosse, darunter Gravitron, Kracko, Old Sonic und die zusätzlichen Teilstrecken. Solgryn bleibt festes Finale. Einstellungsänderungen erzeugen einen neuen Seed; ein importierter Seed bleibt bis zur nächsten Änderung erhalten. Belegte Plätze zeigen ihre gespeicherten Einstellungen und erlauben das Kopieren des Seeds.</p>
<h2>Bestätigte Abläufe</h2><ul>"""
        + checks
        + """</ul>
<p>Für den Kaltstart wurde der Host vollständig geschlossen und neu erzeugt. Der Todeszähler blieb bei 1, der Seed identisch. Ein zweiter Lauf mit Kamilia-Musik und WannaFest-Blut veränderte den ersten Spielstand nicht. Im Host erfolgt keine Änderung des Spielspeichers; der private Beobachter liest nur den aktuellen Szenennamen.</p>
<h2>Oberfläche in fünf Sprachen</h2>"""
        + images
        + """
<h2>Struktur und Start</h2><p>Die neue Anbindung liegt getrennt in <code>work/fusion-lab/menu_host/</code>: Einstellungen, Speicherung, Spielprozess, Oberfläche und Texte haben jeweils ein eigenes Modul. Einstieg: <code>python3 work/fusion-lab/fusion_menu.py</code>.</p>
<h2>Grenzen dieses Schritts</h2><p>Dies ist eine separate Testoberfläche für den nativen Build. Die endgültige Übernahme des bestehenden animierten Spielmenüs, dessen Menü-Musik und Ladescreens steht noch aus. Weitere Gameplay-Extras, Windows 11, vollständige Routenläufe sowie Veröffentlichung und Installer folgen später. Die installierte Version blieb unverändert.</p>
<p>Die UI-Prüfung verwendet echte Tk-Schaltflächenaufrufe und normale Spieltasten. Sie ist kein manueller Mausklicktest jedes Bedienelements. Der erste Testversuch scheiterte an zu kurzen Tastensignalen; längere Signale wurden danach erfolgreich geprüft. Beim Leeren eines Platzes bleibt eine private Rückgängig-Kopie erhalten.</p>
<p><a href="summary.json">Prüfzusammenfassung</a> · <a href="tests.log">85 Tests</a> · <a href="lifecycle.json">Spielabläufe</a> · <a href="ui-results.json">Menüabläufe</a></p></html>"""
    )
    (OUT / "Pruefstand.html").write_text(page)
    print(
        "Report ready: 85 automated checks, 4 lifecycle checks, 5 UI checks, 5 languages"
    )


if __name__ == "__main__":
    main()
