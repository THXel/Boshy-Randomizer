"""Publish only verified native blood evidence and state remaining limits."""

import hashlib, html, json, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/Fusion-Blood-20261024"


def picture(path, caption):
    assert (OUT / path).is_file(), path
    return (
        '<figure><img loading="lazy" src="'
        + html.escape(path)
        + '"><figcaption>'
        + html.escape(caption)
        + "</figcaption></figure>"
    )


def main():
    suite = json.loads((OUT / "death-suite.json").read_text())
    assert len(suite) == 6 and all(r["passed"] for r in suite)
    for row in suite:
        r = json.loads((OUT / row["result"]).read_text())
        assert r["passed"] and r["same_process"]
    enemies = {}
    for scene in ("mario-routes", "ninja-routes"):
        d = json.loads((OUT / ("enemy-" + scene) / "result.json").read_text())
        assert (
            d["passed"]
            and d["enemy_killed_by_native_collision"]
            and d["player_alive_after_kill"]
            and d["same_audio_stream_active"]
        )
        enemies[scene] = dict(
            passed=True,
            player_alive=True,
            normal_effects=True,
            same_audio_stream_active=True,
            audio_capture=d.get("audio_capture"),
        )
    assert enemies["ninja-routes"]["audio_capture"]["last_second_rms"] > 0.001
    raw = OUT / "enemy-ninja-routes/game-audio.s16le"
    with wave.open(str(raw.with_suffix(".wav")), "wb") as f:
        f.setparams((2, 2, 22050, 0, "NONE", "not compressed"))
        f.writeframes(raw.read_bytes())
    source = json.loads((OUT / "project/blood-source-audit.json").read_text())
    assert sum(r["change"] == "player_creation_only" for r in source["changes"]) == 47
    repro = json.loads((OUT / "reproducibility.json").read_text())
    assert repro["existing_run_protected"]
    original = Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    )
    with original.open("rb") as f:
        assert (
            hashlib.file_digest(f, "sha256").hexdigest()
            == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
        )
    tests = (OUT / "tests.log").read_text()
    assert "Ran 64 tests" in tests and tests.rstrip().endswith("OK")
    summary = dict(
        date="2026-10-24",
        scope="private native Fusion player-only blood plus seed-local scenery and actor palettes",
        automated_tests=64,
        player_death_paths=47,
        death_restart_runs=6,
        enemy_kill_runs=2,
        packs=["original", "kamilia3", "wannafest22"],
        retained_images=7087,
        enemies=enemies,
        reproducible_export=True,
        installation_unchanged=True,
        not_verified=[
            "Full playthroughs and all 44 route stations on this build",
            "All enemies and alternate character deaths",
            "Subjective audio quality or uninterrupted musical timing",
            "Windows 11",
            "Main menu integration",
            "Soundpack audio/music migration",
            "Custom game-over screens",
            "New installers or publication",
        ],
        excluded_attempts=[
            "Original-blood observation raced particle destruction; observer now skips expired particles and test passed on rerun",
            "First positioned Mario test bullet missed; final tests use normal shots with player positioning",
            "Initial Mario bounds assertion assumed 4px; original blood is 6x3 and its rotated bounds reach 7px; corrected and rerun",
        ],
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for pack in summary["packs"]:
        p = ROOT / "work/fusion-lab" / ("route-build-blood-" + pack + ".json")
        d = json.loads(p.read_text())
        d.update(
            live_runtime_root_verified=True,
            live_player_blood_verified=True,
            live_evidence="outputs/Fusion-Blood-20261024/death-suite.json",
        )
        if pack == "wannafest22":
            d["live_enemy_separation_verified"] = ["mario-routes", "ninja-routes"]
        p.write_text(json.dumps(d, indent=2) + "\n")
    parts = [
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Boshy – eigene Blutgrafiken</title>
<style>body{max-width:1180px;margin:36px auto;padding:0 24px;background:#111c26;color:#edf4f8;font:17px/1.5 system-ui}h1,h2{line-height:1.2}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}figure{margin:0}img{max-width:100%;image-rendering:pixelated}figcaption{color:#b9cddc}section{margin:30px 0;padding-top:20px;border-top:1px solid #466078}a{color:#88d6ff}li{margin:8px 0}.ok{color:#a7e9b0}code{overflow-wrap:anywhere}</style>
<h1>Eigene Blutgrafiken ausschließlich für Boshy</h1><p>24.10.2026 · Privater Fusion-Testbuild unter Linux/Wine</p>
<p class="ok"><strong>64 automatische Prüfungen · 6 Tod-/Neustarttests · 2 Gegner-Kill-Tests bestanden</strong></p>
<p>Die vorhandenen Kamilia- und WannaFest-Blutbilder werden in einen eigenen Animationsplatz geladen. Nur Partikel aus Boshys nativer Todesschleife wechseln darauf. Gegnerblut und andere Treffereffekte behalten ihre ursprünglichen Grafiken. Die bisherigen 7.087 Bilder – einschließlich der 179 Seed-Grafiken – bleiben bytegenau erhalten.</p>
<p>47 gemeinsame Todesabläufe sind erfasst. Alle 46 vorhandenen Aufrufer der verwendeten Erzeugungsschleife gehören zu „Die“ beziehungsweise „Die2“ und prüfen den Spieler. Eigene Partikel haben eine begrenzte Lebensdauer und werden durch native Spielereignisse entfernt. Gegner-Kills lösen keine eigenen Audio- oder Todesaktionen aus.</p>
<p><strong>Entwicklungsstand:</strong> Die Kombination aus Route, Gegnerfarben, Seed-Texturen und Blutpaket ist als privater Lauf exportierbar. Die installierte Version wurde nicht ersetzt und es wurde nichts veröffentlicht.</p>
<section><h2>Original, Kamilia und WannaFest</h2><p>Alle drei Varianten wurden in Castlevania mit Tod und Neustart geprüft. Die Tests verwenden einen vorbereiteten Spielstand, temporären Schutz und Positionsvorgaben. Der Tod wird über die originale Q-Taste ausgelöst.</p><div class="grid">"""
    ]
    for pack, label in [
        ("original", "Originalblut"),
        ("kamilia3", "Kamilia-Blut"),
        ("wannafest22", "WannaFest-Blut"),
    ]:
        parts.append(picture("live-castlevania-routes-" + pack + "/death-0.png", label))
    parts.append(
        """</div></section><section><h2>Sonic und Solgryn</h2><p>Bei Sonic bestanden beide Blutpakete Tod und Neustart; bei Solgryn wurde WannaFest geprüft. Spätere Game-Over-Bilder und Neustarts zeigen in den aufgenommenen Szenen keine fremden Sprites oder verzerrten Spielflächen. Das sind gezielte Q-Todestests, keine vollständigen Bosskämpfe oder erneuten Feuerphasen-Prüfungen.</p><div class="grid">"""
    )
    for path, label in [
        ("live-sonic-routes-wannafest22/death-0.png", "Sonic: eigene Partikel"),
        ("live-sonic-routes-wannafest22/death-late.png", "Sonic: späteres Game Over"),
        ("live-finale-routes-wannafest22/restart.png", "Solgryn: nach Neustart"),
    ]:
        parts.append(picture(path, label))
    parts.append(
        """</div></section><section><h2>Normale Gegner und Musik</h2><p>Ein Endphasen-Gegner von Mario wurde über seinen nativen Erzeugungsablauf bereitgestellt. In Ninja Gaiden wurde ein vorhandener Gegner gewählt. Normale Schüsse lösen die ursprünglichen Treffer- und Todesereignisse aus; für reproduzierbare Treffer wird die Spielerposition vorgegeben. Boshy bleibt geschützt und am Leben. Die Tests schreiben keine Gegner-Todesmarkierung, Blutzuordnung oder Audiodaten.</p><div class="grid">"""
    )
    parts.append(
        picture(
            "enemy-mario-routes/enemy-after-0.png",
            "Mario: kleine Original-Blutpartikel trotz aktiviertem WannaFest-Paket",
        )
    )
    parts.append(
        picture(
            "enemy-ninja-routes/enemy-after-0.png",
            "Ninja Gaiden: ursprünglicher Treffereffekt, Boshy lebt",
        )
    )
    parts.append(
        """</div><p>In beiden Fällen bleibt derselbe Spiel-Audiostream aktiv und ungemutet. Sämtliche ursprünglichen Audioaktionen sind in den Quellereignissen unverändert. Zusätzlich wurde ausschließlich der Ninja-Spielstream aufgenommen: Auch nach dem Kill ist Audioausgabe vorhanden. Das bestätigt Ausgabe, ersetzt aber keinen subjektiven Hörtest auf musikalische Übergänge oder Klangqualität.</p><audio controls src="enemy-ninja-routes/game-audio.wav"></audio></section>
<section><h2>Export und Nachweise</h2><p>Der neue Exporter nimmt einen vollständigen BR12-Seed und separat die lokale Blut-Auswahl „original“, „kamilia3“ oder „wannafest22“. Ein unabhängiger zweiter Kamilia-Export erzeugte dieselbe Spieldatei; bestehende Laufordner werden nicht überschrieben.</p>
<p><a href="summary.json">Zusammenfassung</a> · <a href="tests.log">64 automatische Prüfungen</a> · <a href="death-suite.json">6 Tod-/Neustarttests</a> · <a href="enemy-mario-routes/result.json">Mario-Nachweis</a> · <a href="enemy-ninja-routes/result.json">Ninja-Nachweis</a> · <a href="reproducibility.json">Reproduzierbarkeit</a></p>
<p>Frühe Diagnoseversuche mit einer Beobachtungsrace, einem verfehlten Testschuss und einer falschen Größenannahme im Prüfhelfer sind in der Zusammenfassung dokumentiert und zählen nicht als bestandene Läufe.</p>
<p><strong>Offen:</strong> vollständige Durchläufe, weitere Gegner und alternative Charakter-Todesabläufe, Windows 11, die Hauptmenü-Anbindung, Soundpack-Musik und -Audio, eigene Game-Over-Bilder sowie Installer und Veröffentlichung.</p></section></html>"""
    )
    (OUT / "Pruefstand.html").write_text("".join(parts))
    print(
        json.dumps(
            dict(report=str(OUT / "Pruefstand.html"), tests=64, live_runs=8), indent=2
        )
    )


if __name__ == "__main__":
    main()
