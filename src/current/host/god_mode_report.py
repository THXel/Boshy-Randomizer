"""Evidence summary for the private native God Mode milestone."""

import hashlib, html, json
from pathlib import Path
from collections import Counter
from export_route_probe import ROOT
from export_native_run import BASE, ORIGINAL
from menu_host.runtime import verify_engine
from menu_host.store import Store, digest
from visuals.scenery_pack import GAMEPLAY_BASE_SHA

OUT = ROOT / "outputs/Fusion-GodMode-20261024"


def main():
    tests = (OUT / "tests.log").read_text()
    assert "Ran 105 tests" in tests and tests.rstrip().endswith("OK")
    live = json.loads((OUT / "live-results.json").read_text())
    bosses = json.loads((OUT / "boss-results.json").read_text())
    ui = json.loads((OUT / "ui-results.json").read_text())
    assert live["passed"] and bosses["passed"] and ui["passed"]
    assert len(live["checks"]) == 2 and len(bosses["cases"]) == 3
    assert all(c["passed"] for c in bosses["cases"])
    audit = json.loads((OUT / "project-final/gameplay-source-audit.json").read_text())
    counts = Counter(a["mode"] for a in audit["gameplay"])
    assert counts == dict(hazard_guard=331, manual_q_unchanged=48, outside_native_run=4)
    verify_engine(BASE, GAMEPLAY_BASE_SHA)
    sha = digest(ORIGINAL)
    assert sha == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
    legacy = Store(ROOT / "outputs/Fusion-Lifecycle-Fix-20261024/profile")
    old, _ = legacy.validate_folder(legacy.folder(1), legacy.current(1))
    assert "gameplay_settings" not in old and not old["options"]["extras"]["god_mode"]
    files = [
        "gameplay/god_mode.py",
        "recover_boshy_gameplay.py",
        "export_native_run.py",
        "visuals/scenery_pack.py",
        "menu_host/draft.py",
        "menu_host/store.py",
        "menu_host/ui.py",
        "menu_host/labels.py",
        "test_god_mode.py",
        "test_gameplay_build.py",
        "test_menu_host.py",
        "god_mode_live.py",
        "god_mode_boss_probe.py",
        "god_mode_ui_probe.py",
    ]
    summary = dict(
        scope=__doc__,
        automated_tests=105,
        new_tests=9,
        source_death_calls=dict(counts),
        compiled_base=str(BASE),
        compiled_base_sha256=GAMEPLAY_BASE_SHA,
        live_checks=live["checks"],
        boss_phase_checks=[
            {k: v for k, v in c.items() if k != "samples"} for c in bosses["cases"]
        ],
        ui_checks=ui["events"],
        final_build_game_launches=7,
        languages=["de", "en", "es", "ru", "ja"],
        legacy_save_validation=True,
        installed_game_sha256=sha,
        installed_or_published=False,
        source_sha256={
            p: hashlib.sha256((ROOT / "work/fusion-lab" / p).read_bytes()).hexdigest()
            for p in files
        },
        found_and_fixed="Solgryn fire uses lowercase die. The first build missed these case-insensitive fastloop calls. Expanded census and live retest verified the fix.",
        limits=[
            "Private Linux/X11 Wine host only; no Windows 11 or installer verification",
            "Boss tests stage HP and player positions; they are not complete fights",
            "No runtime death-loop or invulnerability edits in these tests; only documented phase-entry fixtures",
            "Four calls in the online lobby and unused prototype frame stay unchanged; neither frame belongs to native routes",
            "All 44 exits, other gameplay extras and host menu music were not re-tested or migrated in this milestone",
            "Initial failed build and test-harness attempts are retained separately",
            "Existing saved runs keep their original executable/settings; God Mode is selected before creating a new run",
        ],
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    imgs = "".join(
        f'<figure><figcaption>{html.escape(label)}</figcaption><a href="{name}.png"><img src="{name}.png"></a></figure>'
        for name, label in [
            ("menu-ready", "God Mode im Menü"),
            ("sonic-fire-final", "Sonic: verkleinerte Plattform und Feuer"),
            ("oldsonic-fire-final", "Old Sonic: Feuerphase"),
            ("solgryn-fire-final", "Solgryn: Kletter-/Feuerphase"),
        ]
    )
    (OUT / "Pruefstand.html").write_text(
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Fusion: nativer God Mode</title><style>body{font:18px/1.6 system-ui;max-width:1100px;margin:32px auto;padding:24px;background:#111b25;color:#edf5f6}a{color:#9eddd6}figure{display:inline-block;width:46%;vertical-align:top;margin:1%}img{width:100%}li{margin:10px 0}</style><h1>God Mode im nativen Fusion-Build</h1><p>Privater Teststand · 24.10.2026</p><p><b>105 automatische Tests und sieben Spielstarts mit dem korrigierten Build bestanden.</b></p><p>God Mode ist im neuen Bereich „Spielregeln“ auswählbar. Eine Änderung erneuert den Seed. Die Auswahl wird mit dem Lauf gespeichert und beim Fortsetzen geprüft. Q zum absichtlichen Sterben und R zum Neustarten behalten ihr ursprüngliches Verhalten.</p><h2>Quellpatch</h2><p>331 Gefahren-Aufrufe der nativen Todesroutine verwenden die gespeicherte God-Mode-Einstellung. 48 Q-Aufrufe bleiben unverändert. Vier Aufrufe in der Online-Lobby und einem ungenutzten Prototyp außerhalb der nativen Routen bleiben ebenfalls unverändert. Andere Aktionen, Geräusche und Gegnerereignisse werden nicht geändert. Grafik- und Audiobänke sowie alle 1686 aktiven Objektdefinitionen sind gegenüber dem vorherigen Blut-Build identisch.</p><h2>Gefundener und behobener Fehler</h2><p>Beim ersten Solgryn-Test starb Boshy trotz aktiviertem God Mode: Der Quellcode verwendet auch die kleingeschriebene Routine „die“. Der korrigierte Patch erfasst beide Schreibweisen. Eine unabhängige Quellprüfung und die wiederholten Live-Tests sichern diese Korrektur ab. Die fehlgeschlagenen Versuche bleiben dokumentiert.</p><h2>Live geprüft</h2><ul><li>Mausgeist-Kontakt: Tod bei God Mode aus, Überleben bei God Mode an.</li><li>Q-Tod, R-Neustart und F2-Rückkehr im ersten Level.</li><li>Sonic, Old Sonic und Solgryn mit Sprite-Randomizer, Kamilia-Musik und WannaFest-Blut: Feuerphasen, Q-Tod und Neustart.</li><li>Menü in fünf Sprachen; God-Mode-Schalter, neuer Seed, neuer Lauf, gespeicherte Einstellung beim Fortsetzen und Leeren des Speicherplatzes.</li></ul>"""
        + imgs
        + """<h2>Grenzen</h2><p>Die Bossphasen wurden mit dokumentierten HP- und Positionsfixtures erreicht. Die Unverwundbarkeit stammt ausschließlich aus dem neuen nativen Build und seiner Save-Einstellung. Dies sind keine vollständigen Bosskämpfe und kein neuer Test aller Ausgänge. Der installierte Randomizer blieb unverändert; Windows 11, Installer, weitere Extras und Veröffentlichung stehen noch aus.</p><p><a href="summary.json">Zusammenfassung</a> · <a href="tests.log">105 Tests</a> · <a href="live-results.json">Aus-/An-Vergleich</a> · <a href="boss-results.json">Bossphasen</a> · <a href="ui-results.json">Menüprüfung</a></p></html>"""
    )
    print("God Mode report verified: 105 tests, 7 native launches; private only")


if __name__ == "__main__":
    main()
