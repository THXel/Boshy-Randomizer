"""Summarize only completed native scenery evidence, including its limits."""

import hashlib
import html
import json
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/Fusion-Scenery-20261023"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def picture(path, label):
    return (
        '<figure><img loading="lazy" src="'
        + html.escape(str(path))
        + '"><figcaption>'
        + html.escape(label)
        + "</figcaption></figure>"
    )


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    suite = json.loads((OUT / "live-suite.json").read_text())
    assert len(suite) == 9 and all(r["passed"] for r in suite)
    records = {
        (r["scene"], r["mode"]): json.loads((OUT / r["evidence"]).read_text())
        for r in suite
    }
    chain = json.loads((OUT / "live-level-chain/result.json").read_text())
    assert chain["passed"] and chain["same_process"]
    assert digest(OUT / "Boshy-scenery.exe") == audit["sha256"]
    repro = json.loads((OUT / "reproducibility.json").read_text())
    assert repro["game_sha256"] == audit["sha256"]
    original = Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    )
    assert (
        digest(original)
        == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
    )
    animations = json.loads((OUT / "animation-comparison.json").read_text())
    comparisons = {}
    for scene in ["castlevania-routes", "prehistorik-routes", "secret-mario-routes"]:
        off, on = (records[scene, m] for m in ["off", "on"])
        landing = [
            {k: d["landing"]["settled"][k] for k in ["x", "y", "w", "h"]}
            for d in [off, on]
        ]
        assert landing[0] == landing[1]
        assert animations[scene] and all(
            row["layout_equal"] for row in animations[scene].values()
        )
        pics = [
            Image.open(OUT / ("live-" + scene + "-" + m) / "collision-landing.png")
            for m in ["off", "on"]
        ]
        comparisons[scene] = {
            "landing": landing[0],
            "runtime_animation_layout_equal": True,
            "compiled_actor_image_references_unchanged": True,
            "landing_view_identical": ImageChops.difference(*pics).getbbox() is None,
        }
    for scene in ["sonic-routes", "oldsonic-routes"]:
        assert min(records[scene, "on"]["platform_widths"]) == 168
    assert records["finale-routes", "on"]["climb_entered"]
    summary = {
        "scope": "Private Linux/Wine native Fusion route, actor palette and curated scenery prototype",
        "date": "2026-10-24",
        "seed": audit["seed"],
        "game_sha256": audit["sha256"],
        "cloned_images": 179,
        "original_images_unchanged": 6908,
        "automated_tests": 54,
        "live_runs_passed": 9,
        "native_chain_passed": True,
        "animation_comparison_runs_passed": 6,
        "reproducible_export": True,
        "comparisons": comparisons,
        "protected": audit["protected_objects"],
        "excluded_attempts": [
            "Initial export omitted the updated native data checksum; startup failed before any game window. Checksum update fixed and retested.",
            "Initial Castle smoke used the wrong expected station save6.ini instead of save7.ini; not counted; final fixtures use the verified route catalogue.",
        ],
        "not_verified": [
            "Full playthroughs",
            "All 44 route stations on this graphics build",
            "Every fire effect",
            "Windows 11",
            "Full main menu integration",
            "Custom blood/music migration",
            "Installer/release publication",
        ],
        "installation_unchanged": True,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    profile_path = ROOT / "work/fusion-lab/route-build-scenery.json"
    profile = json.loads(profile_path.read_text())
    profile.update(
        live_runtime_root_verified=True,
        live_scene_suite="outputs/Fusion-Scenery-20261023/live-suite.json",
        live_level_chain_verified=True,
    )
    profile_path.write_text(json.dumps(profile, indent=2) + "\n")
    parts = [
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Boshy – Hintergründe und Kacheln</title><style>body{max-width:1180px;margin:36px auto;padding:0 24px;background:#101923;color:#edf3f7;font:17px/1.5 system-ui}h1,h2{line-height:1.2}.pairs{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}figure{margin:0}img{max-width:100%;image-rendering:pixelated}figcaption{color:#c0ced8}section{margin:30px 0;padding-top:20px;border-top:1px solid #3a4c5d}a{color:#8dd9ff}.ok{color:#a8e6b5}li{margin:8px 0}code{overflow-wrap:anywhere}table{border-collapse:collapse}td,th{padding:8px 18px;border:1px solid #536574;text-align:left}</style>
<h1>Boshy: Hintergründe und Kacheln pro Seed</h1><p>Abgeschlossen am 24.10.2026 · Privater Fusion-Testbuild unter Linux/Wine</p>
<p class="ok"><strong>179 eigene Bildkopien · 54 automatische Prüfungen · 9/9 Live-Durchläufe · zusätzliche Weltkette bestanden</strong></p>
<p>Die bereits geprüfte Grafikauswahl wird vor dem Start in eine eigene Spieldatei für den Seed geschrieben. Sämtliche 6.908 Originalbilder bleiben unverändert. Nur die ausgewählten Hintergrund-, Dekorations- und Kachelobjekte verweisen auf die neuen Kopien. Gegner und Effekte behalten ihre ursprünglichen Bilder; die native Gegnerfärbung bleibt aktiv.</p>
<p>Maße, Ankerpunkte und jeder Transparenzwert sind erhalten. Kollisions-, Bewegungs- und Ereignisdaten wurden nicht verändert. Fusion prüft die Dateidaten weiterhin mit seiner nativen Integritätsprüfung; deren Wert wird beim Export korrekt aktualisiert. Ein vollständiger BR12-Seed erzeugte bei einem unabhängigen zweiten Export exakt dieselbe EXE.</p>
<p><strong>Noch ein Entwicklungsstand:</strong> Der Exporter ist ausführbar, aber noch nicht mit dem vollständigen Hauptmenü verbunden. Keine Installation und keine Veröffentlichung wurden ersetzt.</p>
<section><h2>Ein/Aus-Vergleiche im Spiel</h2><p>Gleicher Seed und gleiche Gegnerfarben in beiden Varianten. Temporärer Schutz und Positionsvorgaben erreichen die Prüfstellen. Danach wurden native Todesroutinen wieder aktiviert und Neustarts geprüft. Die Bilder sind keine framegenau synchronisierte Aufnahme.</p>"""
    ]
    names = {
        "prehistorik-routes": "Prehistorik",
        "secret-mario-routes": "Mario-Geheimbereich",
        "castlevania-routes": "Castlevania",
    }
    for scene in ["prehistorik-routes", "secret-mario-routes", "castlevania-routes"]:
        parts.append("<h3>" + names[scene] + "</h3>")
        if scene == "castlevania-routes":
            parts.append(
                "<p>Diese gezeigte Ansicht bleibt absichtlich original; der bestehende Katalog wählt die dort sichtbaren Wald- und Schädelgrafiken nicht aus. Geprüft wurden das erhaltene Skelett am Anfang, beide gefärbten Skeletttypen, Tod/Neustart und unveränderte Kollisionshöhe. Das ist ein Regressionstest, keine Behauptung einer vollständigen Castlevania-Umgestaltung.</p>"
            )
        label = "waypoint-1" if scene == "prehistorik-routes" else "waypoint-0"
        parts.append('<div class="pairs">')
        for mode in ["off", "on"]:
            parts.append(
                picture(
                    "live-" + scene + "-" + mode + "/" + label + ".png",
                    "Texturpaket " + ("aus" if mode == "off" else "an"),
                )
            )
        parts.append(
            "</div><p>Identische Landeposition: x="
            + str(comparisons[scene]["landing"]["x"])
            + ", y="
            + str(comparisons[scene]["landing"]["y"])
            + ". Gegner-Animationsabläufe unverändert. Interne Bildnummern werden beim Laden neu vergeben; nach deren Ausblendung sind auch die Laufzeitdaten identisch.</p>"
        )
    parts.append(
        "</section><section><h2>Feuer und Neustarts</h2><p>Sonic und Old Sonic erreichten wieder die Feuerphase mit 168 Pixel breiter Plattform. Diese schrumpfende Grasplattform bleibt vom Texturtausch ausgenommen. Solgryn erreichte den Kletterabschnitt mit Feuerstrahl und Folgeeffekt. Tod und Neustart wurden bei allen drei Tests bestätigt.</p><p>Dies sind gezielte Phasentests mit temporärem Schutz und gesetzten Boss-HP, bei Solgryn zusätzlich einer Position am Klettereingang. Keine regulär vollständig gewonnenen Kämpfe und kein manuell abgeschlossener Aufstieg.</p>"
    )
    for scene in ["sonic-routes", "oldsonic-routes", "finale-routes"]:
        d = records[scene, "on"]
        target = 6248 if scene == "finale-routes" else 1300
        shot = min(d["samples"], key=lambda r: abs(r["boss_values"][0] - target))[
            "image"
        ]
        parts.append(
            "<h3>"
            + {
                "sonic-routes": "Sonic",
                "oldsonic-routes": "Old Sonic",
                "finale-routes": "Solgryn",
            }[scene]
            + '</h3><div class="pairs">'
            + picture(
                "live-" + scene + "-on/" + shot + ".png",
                "Feuerphase mit aktiviertem Texturpaket",
            )
            + picture("live-" + scene + "-on/fire-restart.png", "Nach Tod und Neustart")
            + "</div>"
        )
    parts.append(
        """</section><section><h2>Eine zusammenhängende Weltkette</h2><p>Prehistorik → Castlevania → Solgryn wurde in einem einzigen Spielprozess über native Ausgangskontakte durchlaufen. In Castlevania waren die Skelette nach dem Weltwechsel vorhanden. Tod/Neustart in Castlevania und bei Solgryn sowie die gespeicherten Abschlussmarkierungen blieben korrekt.</p><p><a href="live-level-chain/result.json">Kettenprotokoll und dokumentierte Testeingriffe</a></p></section>
<section><h2>Nachweise und offene Arbeit</h2><p>Die gezielten Prüfungen decken drei Levelbereiche und drei Bossphasen ab. Die 179 Katalogeinträge sind strukturell auf unveränderte Geometrie und Transparenz geprüft, aber nicht alle einzeln im Spiel besucht. Vollständige Durchläufe, die gesamte 44-Stationen-Matrix mit diesem Build, alle weiteren Feuereffekte und Windows 11 bleiben offen.</p><p>Als nächste Funktionen fehlen eigene Blutgrafiken ausschließlich für Boshy, Musiksteuerung und die vollständige Hauptmenü-Anbindung. Der Linux-Exporter benötigt derzeit liblz4; Windows-Paketierung und neue Installer sind noch nicht erstellt.</p><p>Frühe Diagnoseversuche mit veralteter Dateiprüfsumme sowie ein falscher erwarteter Stationsname im Testhelfer sind nicht als bestandene Tests gezählt. Ein zusätzlicher Animationshelfer behandelte anfangs interne Ersatzrichtungswerte falsch; er wurde korrigiert und separat erneut geprüft. Alle hier aufgeführten finalen Durchläufe verwenden den korrigierten Build und passende Seed-Spielstände.</p><p><a href="summary.json">Zusammenfassung</a> · <a href="audit.json">179 Bildkopien und geschützte Objekte</a> · <a href="live-suite.json">9 Live-Durchläufe</a> · <a href="tests.log">54 automatisierte Prüfungen</a> · <a href="animation-comparison.json">6 zusätzliche Animationsvergleiche</a> · <a href="reproducibility.json">Reproduzierbarkeit</a></p>
<p>Formatreferenz: <a href="https://github.com/AITYunivers/NebulaFD/blob/a24d4d1da78c35412413faac750e07ff7d603a8a/Nebula.Core/Data/Chunks/BankChunks/Images/Image2.5Plus.cs">NebulaFD – Fusion-Grafikdatensatz</a>. Die Integritätsberechnung wurde zusätzlich am Loader des eigenen kompilierten Builds nachvollzogen; der Spielcode bleibt unverändert.</p></section></html>"""
    )
    (OUT / "Pruefstand.html").write_text("".join(parts))
    print(
        json.dumps(
            {
                "report": str(OUT / "Pruefstand.html"),
                "live_runs": 9,
                "native_chain": True,
                "tests": 54,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
