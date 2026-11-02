"""Evidence report for the first native Fusion actor-palette milestone."""

import hashlib
import html
import json
from pathlib import Path
from actor_live_probe import OUT, ROOT, SCENES, EXPECTED


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def picture(path, caption):
    return (
        '<figure><img loading="lazy" src="'
        + html.escape(str(path))
        + '"><figcaption>'
        + html.escape(caption)
        + "</figcaption></figure>"
    )


def main():
    suite = json.loads((OUT / "actor-suite.json").read_text())
    assert len(suite) == 10 and all(r["passed"] for r in suite)
    records = {
        (r["scene"], r["mode"]): json.loads((OUT / r["evidence"]).read_text())
        for r in suite
    }
    banks = {}
    for (scene, mode), data in records.items():
        assert data["passed"] and data["same_process"]
        assert data["actor_types_verified"] == sorted(EXPECTED[scene])
        for sample in data["samples"]:
            for o in sample["objects"]:
                banks.setdefault(o["source_oi"], {}).setdefault(mode, set()).add(
                    o["animation_bank_sha256"]
                )
    assert len(banks) == 9
    for oi, versions in banks.items():
        assert versions["on"] == versions["off"], oi
    fire = json.loads((OUT / "fire-suite.json").read_text())
    assert len(fire) == 3 and all(r["passed"] for r in fire)
    fire_records = {
        r["scene"]: json.loads((OUT / r["evidence"]).read_text()) for r in fire
    }
    deaths = json.loads((OUT / "death-suite.json").read_text())
    assert len(deaths) == 2 and all(r["passed"] for r in deaths)
    death_records = {
        r["scene"]: json.loads((OUT / r["evidence"]).read_text()) for r in deaths
    }
    original = Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    )
    original_hash = digest(original)
    assert (
        original_hash
        == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
    )
    profile_path = ROOT / "work/fusion-lab/route-build-actors.json"
    profile = json.loads(profile_path.read_text())
    assert (
        digest(
            Path(
                "/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-actors.exe"
            )
        )
        == profile["sha256"]
    )
    assert any(r.get("compiled_actor_group_verified") for r in records.values())
    profile.update(
        live_runtime_root_verified=True,
        compiled_event_verification="FusionActorsV1 found in actual runtime event banks; see Hello Kitty and Dedede confirmed on/off evidence",
        live_actor_types_verified=9,
    )
    profile_path.write_text(json.dumps(profile, indent=2) + "\n")
    summary = {
        "scope": "Private native Fusion actor palettes; not the complete sprite randomizer",
        "actor_runs_passed": len(suite),
        "actor_types_verified": 9,
        "animation_bank_equal_on_off": {
            str(k): sorted(v["on"]) for k, v in banks.items()
        },
        "fire_runs": fire,
        "delayed_death_runs": deaths,
        "lab_tests": 47,
        "user_observation": "User reported Solgryn fire looked correct during this run",
        "build_sha256": profile["sha256"],
        "installed_original_unchanged": original_hash,
        "excluded_diagnostics": [
            "live-castlevania-routes-on: earlier manual godmode patches were not owned by the next helper; death check inconclusive; fresh confirmed run passed",
            "castlevania-routes-off-confirmed.log: CLI label parsing failed before probe; the already launched process was checked separately and passed",
        ],
        "open": [
            "Scenery and tile randomization",
            "Custom player-only blood migration",
            "Music migration",
            "Full GUI integration",
            "All fire effects across game",
            "Windows 11 and installers",
            "Full normal boss fights",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    sections = [
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Boshy – native Gegnerfarben</title>
<style>body{font:17px/1.5 system-ui;max-width:1180px;margin:35px auto;padding:0 24px;background:#101923;color:#e9f0f5}h1,h2{line-height:1.2}a{color:#83d5ff}.pairs{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:15px}figure{margin:0}img{max-width:100%;image-rendering:pixelated}figcaption{color:#b9ccd9}section{margin:35px 0;padding-top:20px;border-top:1px solid #344454}code{overflow-wrap:anywhere}li{margin:8px 0}.ok{color:#a8e6b5}</style>
<h1>Boshy: erste native Gegnerfarben</h1><p>23.10.2026 · Privater Fusion-Testbuild unter Linux/Wine</p>
<p class="ok"><strong>10/10 Gegnervergleiche bestanden · 9 Gegnertypen · 47 Labortests</strong></p>
<p>Seedabhängige Farben werden direkt auf die jeweiligen Fusion-Objekte angewendet. Animationen, Hotspots und Kollisionen werden dabei nicht ersetzt. Die neun geprüften Typen verwenden mit ein- und ausgeschalteter Färbung dieselben Animationsdaten.</p>
<p>Dieser Stand umfasst die Gegnerfärbung. Er ist noch keine vollständige Übertragung aller Sprite-, Hintergrund-, Blut- und Musikoptionen und wurde nicht installiert oder veröffentlicht.</p>
<section><h2>Prüfmethode</h2><p>Je Gebiet derselbe BR12-Seed mit Färbung aus/an. Temporärer Schutz, festgelegte Positionen und bei Dedede ein Zustandswert erreichen gezielt die Prüfstellen. Native Erstellung späterer Gegner, Tod, Neustart und gespeicherte Route wurden geprüft. Das ersetzt keine vollständig regulär durchgespielten Kämpfe. Alle Teständerungen sind in den Detailprotokollen aufgeführt.</p>
<p>Castlevania: Beide zufällig gefärbten Skeletttypen sind vorhanden; auch das ursprüngliche weiße Skelett am Anfang bleibt sichtbar. Die geprüften Bilder zeigen keine schwarzen Balken oder falschen Hintergrundteile. Die Bilder sind nicht framegenau synchronisiert.</p></section>"""
    ]
    titles = {
        "castlevania-routes": "Castlevania",
        "prehistorik-routes": "Prehistorik",
        "secret-mario-routes": "Mario-Geheimbereich",
        "hellokitty-routes": "Hello Kitty",
        "dedede-fight-routes": "King Dedede",
    }
    for scene in SCENES:
        label = (
            "waypoint-0"
            if SCENES[scene]
            else (
                "native-late-spawn"
                if scene == "dedede-fight-routes"
                else "initial-colours"
            )
        )
        sections.append(
            "<section><h2>"
            + titles[scene]
            + '</h2><p>Ein/Aus, Farben, Alpha, vorhandene Objektgeometrie, Animationsdaten und Tod/Neustart: bestanden.</p><div class="pairs">'
        )
        for mode in ["off", "on"]:
            folder = "live-" + scene + "-" + mode + "-confirmed"
            sections.append(
                picture(
                    folder + "/" + label + ".png",
                    "Färbung " + ("aus" if mode == "off" else "an"),
                )
            )
        sections.append(
            "</div><p>Detailprotokolle: "
            + " · ".join(
                '<a href="live-'
                + scene
                + "-"
                + m
                + '-confirmed/result.json">'
                + m
                + "</a>"
                for m in ["off", "on"]
            )
            + "</p></section>"
        )
    sections.append(
        "<section><h2>Feuerphasen mit Gegnerfarben an</h2><p>Für diese gezielten Prüfungen wurden Boss-HP gesetzt und Schutz vorübergehend aktiviert. Bei Solgryn wurde am originalen Phasenübergang der Klettereingang betreten. Die ursprünglichen Ereignisabschnitte der drei Feuer-Bossräume werden von der Färbungsänderung nicht verändert.</p>"
    )
    for scene, data in fire_records.items():
        sections.append(
            "<h3>"
            + html.escape(scene)
            + ": "
            + ("bestanden" if data["passed"] else "offen / fehlgeschlagen")
            + "</h3>"
        )
        if not data["passed"]:
            sections.append("<p>" + html.escape(data.get("error", "")) + "</p>")
        target = 6248 if scene == "finale-routes" else 1300
        samples = [s for s in data["samples"] if s["boss_values"]]
        selected = min(samples, key=lambda s: abs(s["boss_values"][0] - target))
        sections.append(
            '<div class="pairs">'
            + picture(
                "fire-" + scene + "/" + selected["image"] + ".png",
                "Aufgenommene Feuerphase",
            )
            + picture("fire-" + scene + "/fire-restart.png", "Nach Tod und Neustart")
            + "</div>"
        )
        sections.append(
            "<p>Todesprüfung: "
            + html.escape(data.get("death_trigger", "nicht abgeschlossen"))
            + '. <a href="fire-'
            + scene
            + '/result.json">Messwerte und Eingriffe</a></p>'
        )
    sections.append(
        "</section><section><h2>Verzögerte Todesdarstellung bei Sonic</h2><p>Zusatzprüfung mit aktivierter Färbung: Boshy wurde beim sichtbaren Sonic positioniert; die native Todesroutine blieb aktiv. Kein Q. Aufnahmen direkt nach dem Tod, nach zwei und nach fünf Sekunden sowie nach dem Neustart.</p>"
    )
    for scene, data in death_records.items():
        sections.append(
            "<h3>"
            + html.escape(scene)
            + ": "
            + ("bestanden" if data["passed"] else "offen / fehlgeschlagen")
            + "</h3>"
        )
        if data["passed"]:
            sections.append(
                '<div class="pairs">'
                + picture(
                    "death-" + scene + "/death-5-seconds.png",
                    "Fünf Sekunden nach dem Tod",
                )
                + picture("death-" + scene + "/restart.png", "Nach Neustart")
                + "</div>"
            )
        sections.append(
            '<p><a href="death-' + scene + '/result.json">Detailprotokoll</a></p>'
        )
    sections.append(
        """</section><section><h2>Grenzen und nächster Schritt</h2><p>Noch offen sind Hintergründe/Kacheln, eigene Blutgrafiken ausschließlich für Boshy, Musiksteuerung und die Anbindung an das vollständige Hauptmenü. Ebenfalls offen: sämtliche weiteren Feuereffekte, vollständige reguläre Bosskämpfe, Windows 11 und neue Installer. Die zuvor geprüften 44 Routenstationen beziehen sich auf den vorherigen Routenbuild; diese komplette Matrix wurde mit dem neuen Grafikbuild nicht erneut ausgeführt.</p><p>Die installierte Original-EXE ist laut SHA-256 unverändert. Kein GitHub-Upload und kein Installer-Austausch in diesem Schritt.</p><p>Zwei frühe Castlevania-Diagnoseversuche sind erhalten: ein Fehler in der Testaufruf-Syntax sowie ein Todestest mit übernommenem, fremdem Testschutz. Die anschließend frisch gestarteten bestätigten Läufe bestanden; die frühen Versuche zählen nicht als erfolgreiche Tests.</p><p><a href="summary.json">Zusammenfassung</a> · <a href="actor-suite.json">Gegnertests</a> · <a href="fire-suite.json">Feuertests</a> · <a href="lab-tests.log">47 Labortests</a> · <a href="project/visual-audit.json">Quelländerungen</a></p></section></html>"""
    )
    (OUT / "Pruefstand.html").write_text("".join(sections))
    print(
        json.dumps(
            {
                "actors": len(suite),
                "fire": fire,
                "report": str(OUT / "Pruefstand.html"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
