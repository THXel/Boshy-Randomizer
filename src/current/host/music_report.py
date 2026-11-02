"""Assemble the private music migration evidence without claiming release readiness."""

import hashlib, html, json, re, wave
from pathlib import Path
from build_profiles import LAB, profile
from prepare_music_builds import OUT


def main():
    results = []
    for pack in ("original", "kamilia3", "wannafest22"):
        for kind, scene in [
            ("enemy", "mario-routes"),
            ("enemy", "ninja-routes"),
            ("death", "sonic-routes"),
        ]:
            folder = OUT / (kind + "-" + scene + "-" + pack)
            d = json.loads((folder / "result.json").read_text())
            assert d["passed"] and d["same_process"]
            row = dict(
                kind=kind,
                scene=scene,
                pack=pack,
                passed=True,
                evidence=str(folder.relative_to(OUT) / "result.json"),
            )
            if kind == "enemy":
                c = json.loads((folder / "music-continuity.json").read_text())
                assert c["passed"]
                row["music"] = c
                pcm = (folder / "game-audio.s16le").read_bytes()
                with wave.open(str(folder / "game-audio.wav"), "wb") as w:
                    w.setnchannels(2)
                    w.setsampwidth(2)
                    w.setframerate(22050)
                    w.writeframes(pcm)
            results.append(row)
        path = LAB / ("route-build-music-" + pack + ".json")
        p = json.loads(path.read_text())
        p.update(
            live_verified=True,
            live_runtime_root_verified=True,
            live_player_blood_verified=True,
            live_enemy_separation_verified=["mario-routes", "ninja-routes"],
            live_music_continuity_verified=["mario-routes", "ninja-routes"],
            live_evidence="outputs/Fusion-Music-20261024/summary.json",
        )
        path.write_text(json.dumps(p, indent=2) + "\n")
    log = (OUT / "tests.log").read_text()
    assert "Ran 74 tests" in log and log.rstrip().endswith("OK")
    original = Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    )
    assert (
        hashlib.sha256(original.read_bytes()).hexdigest()
        == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
    )
    export = OUT / "reproducible-export"
    assert (
        hashlib.sha256((export / "Boshy.exe").read_bytes()).hexdigest()
        == profile("music-wannafest22")["sha256"]
    )
    menu = json.loads((OUT / "menu-catalogue-audit.json").read_text())
    summary = dict(
        automated_tests=74,
        live_tests=9,
        music_continuity_tests=6,
        music_cues=45,
        untouched_other_sounds=426,
        original_installed_game_unchanged=True,
        reproducible_export=True,
        menu_catalogue=menu,
        results=results,
        limits=[
            "Private Linux/Wine builds; not installed or released",
            "No full boss fights, full route sweep or Windows 11 validation on these builds",
            "Sonic player death invoked through native Q event; not natural Sonic collision",
            "Enemy tests use protection/player positioning and native bullets; Mario spawn selector is a fixture",
            "Audio waveform matching verifies continuity; no subjective sound quality review",
            "Main menu launch/save integration remains pending; catalogue comparison is static only",
            "Custom death audio/screens and remaining gameplay extras are not migrated",
        ],
        excluded_attempts=[
            "enemy-ninja-routes-kamilia3-missed-effect: short native effect missed by observer; retained; retry passed"
        ],
        next="Port menu process/save ownership to native Fusion runs without the old runtime hooks",
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    rows = "".join(
        "<tr><td>"
        + html.escape(r["pack"])
        + "</td><td>"
        + html.escape(r["scene"])
        + "</td><td>"
        + ("Gegner-Kill" if r["kind"] == "enemy" else "Tod / Neustart")
        + "</td><td>Bestanden</td><td>"
        + (f"{r['music']['advance_error']*1000:.3f} ms" if "music" in r else "—")
        + "</td></tr>"
        for r in results
    )
    audio = "".join(
        f'<figure><figcaption>{r["pack"]} · {r["scene"]}</figcaption><audio controls preload="none" src="{r["kind"]}-{r["scene"]}-{r["pack"]}/game-audio.wav"></audio></figure>'
        for r in results
        if r["kind"] == "enemy"
    )
    page = (
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Fusion – native Musik</title>
<style>body{font:17px system-ui;max-width:1080px;margin:36px auto;padding:24px;background:#121923;color:#e9f1fa}h1,h2{color:#8ed8ff}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #435166;text-align:left}.ok{padding:16px;background:#163f36;border-radius:10px}img{max-width:48%;margin-right:1%}audio{width:100%}a{color:#8ed8ff}figure{display:inline-block;width:44%;margin:12px 2%}</style>
<h1>Native Musik im Fusion-Randomizer</h1><p>24.10.2026 · Privater Linux/Wine-Teststand</p>
<p class="ok">74 automatische Tests · 9 Spieltests · 6 bestandene Musik-Kontinuitätsprüfungen</p>
<p>45 Musikeinträge werden seedabhängig ersetzt. Original Boshy, Kamilia 3 und WannaFest22 verwenden getrennte Boss- und Levelpools. Alle 426 übrigen Sounds, Spielereignisse, Grafiken und Engine-Code bleiben bytegleich zum jeweiligen Blut-Testbuild.</p>
<p>Die Musik liegt direkt in der nativen Soundbank. Es gibt keine neue Wiedergabeschleife und keine Umdeutung von Gegner-Todessounds. Im Vergleich der Tonaufnahmen laufen die erwarteten Musikstücke nach den Kills an der erwarteten Position weiter.</p>
<h2>Spieltests</h2><p>Ein Spielprozess zur Zeit. Isolierte Saves, Schutz und Positionshilfen; Gegner sterben durch native Geschosse. Sonic-Tod über die normale Q-Funktion, anschließend R. Keine vollständigen Bosskämpfe.</p>
<table><tr><th>Paket</th><th>Szene</th><th>Prüfung</th><th>Ergebnis</th><th>Musikposition-Abweichung</th></tr>"""
        + rows
        + """</table>
<p>Ein erster Kamilia/Ninja-Versuch verpasste den kurzen Treffer-Effekt. Die Beobachtung erfasst diesen jetzt unmittelbar; der wiederholte Fall bestand. Der fehlgeschlagene Versuch bleibt separat erhalten.</p>
<h2>Spielton zum Nachhören</h2><p>Nur der Boshy-Audiostream. Die automatische Auswertung vergleicht echte Musikdaten vor/nach dem Kill und einen unpassenden Kontrolltrack; sie ersetzt keine subjektive Hörprüfung.</p>"""
        + audio
        + """
<h2>Sonic</h2><img src="death-sonic-routes-kamilia3/death-late.png" alt="Kamilia Game Over"><img src="death-sonic-routes-wannafest22/restart.png" alt="WannaFest Neustart">
<h2>Export und Menü</h2><p>Der gemeinsame Exporter <code>work/fusion-lab/export_native_run.py</code> erzeugt Route, Grafiken, Boshy-Blut und die ausgewählte Musik. Der vollständige WannaFest-Export reproduziert den getesteten Build bytegenau. Die alte Exportdatei bleibt als kleiner kompatibler Einstieg bestehen.</p>
<p>Statischer Abgleich: 21 Level und 22 auswählbare Bosse sowie Solgryn als festes Finale ergeben alle 44 Routenpunkte. Das bestätigt die Menüdefinitionen, noch keinen Klicktest oder die Anbindung des neuen Builds.</p>
<h2>Noch offen</h2><p>Native Hauptmenü-/Start-/Speicheranbindung; übrige Gameplay-Extras; eigene Todessounds/-bilder; vollständiger Routentest und Windows 11. Die installierte Spielversion blieb unverändert. Kein GitHub-Release und kein neuer Installer in diesem Schritt.</p>
<p><a href="summary.json">Prüfzusammenfassung</a> · <a href="tests.log">Automatische Tests</a> · <a href="menu-catalogue-audit.json">44 Routenpunkte</a></p></html>"""
    )
    (OUT / "Pruefstand.html").write_text(page)
    print("74 automated; 9 live; 6 waveform continuity; private report ready")


if __name__ == "__main__":
    main()
