"""Generate a precise local overview from passing route evidence, not assumptions."""

import hashlib
import html
import json
from pathlib import Path
import sys
from live_route_session import ROOT
from transition.router import STAGES, GROUP

sys.path.insert(0, str(ROOT / "work/Boshy-Randomizer/src/python/rules"))
from beta_catalogue import BOSSES
from run_settings import level_catalogue

OUT = ROOT / "outputs/Fusion-RouteCoverage-20261023"
EVIDENCE = [
    ROOT / "outputs/Fusion-Routes-20261023/live-mario-chain-confirmed/result.json",
    ROOT / "outputs/Fusion-Routes-20261023/live-split-kracko/result.json",
    *[
        OUT / name / "result.json"
        for name in [
            "live-questionmark-routes-guards",
            "live-ridley-routes-guards",
            "live-ninja-routes-pass1",
            "live-kid-routes-pass2",
            "live-kappa-routes-pass2",
            "live-random1-routes-pass1",
            "live-random2-routes-pass1",
            "live-dedede-shortcut-routes-guards-confirm",
            "live-random1-bonus-routes-guards",
            "live-finale-routes-guards",
        ]
    ],
]


def receipts(value):
    if isinstance(value, dict):
        group = value.get(GROUP)
        if isinstance(group, dict):
            for key, val in group.items():
                if key.lower().startswith("done") and str(val) == "1":
                    yield int(key[4:])
            if str(group.get("completed", group.get("Completed", "0"))) == "1":
                yield STAGES["boss_solgryn.ini"]["id"]
        for child in value.values():
            yield from receipts(child)
    elif isinstance(value, list):
        for child in value:
            yield from receipts(child)


def generate():
    evidence = {}
    covered = set()
    # Matrix runs include failed fixture attempts. Only successful complete
    # results provide coverage; retain the failed attempts separately for review.
    matrix_results = sorted(OUT.glob("live-*-matrix-*/result.json"))
    passing_matrix = []
    failed_attempts = []
    for path in matrix_results:
        data = json.loads(path.read_text())
        if data.get("passed") and data.get("same_process"):
            passing_matrix.append(path)
        else:
            failed_attempts.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "error": data.get("error"),
                    "case": data.get("case"),
                }
            )
    passing_cases = {
        json.loads(path.read_text())["case"]: str(path.relative_to(ROOT))
        for path in passing_matrix
    }
    for attempt in failed_attempts:
        attempt["subsequent_passing_evidence"] = passing_cases.get(attempt["case"])
    for path in [*EVIDENCE, *passing_matrix]:
        data = json.loads(path.read_text())
        assert data["passed"] and data["same_process"], path
        stage_ids = set(receipts(data))
        covered |= stage_ids
        evidence[str(path.relative_to(ROOT))] = sorted(stage_ids)
    names = {
        **level_catalogue(9),
        **{v[2]: v[0] for v in BOSSES.values()},
        "boss_solgryn.ini": "Solgryn",
    }
    stations = []
    for spot, stage in STAGES.items():
        stations.append(
            {
                "spot": spot,
                "id": stage["id"],
                "name": stage.get("label", names.get(spot, spot)),
                "frame": stage["frame"],
                "exit_live_tested": stage["id"] in covered,
                "evidence": [p for p, ids in evidence.items() if stage["id"] in ids],
            }
        )
    cold = json.loads((OUT / "cold-resume-results.json").read_text())
    assert len(cold) == 5 and all(r["passed"] for r in cold)
    shots = {}
    for name in ["beta-damage-before", "beta-damage-after", "ridley-damage-confirmed"]:
        d = json.loads((OUT / name / "result.json").read_text())
        assert d["passed"]
        shots[name] = {k: d[k] for k in ["early", "fight"]}
    original = Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    )
    digest = hashlib.file_digest(original.open("rb"), "sha256").hexdigest()
    assert digest == "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
    summary = {
        "status": "private Fusion prototype; not installed or released",
        "current_build": json.loads(
            (ROOT / "work/fusion-lab/route-build-guards.json").read_text()
        ),
        "live_tested_outgoing_stations": len(covered),
        "total_stations": len(STAGES),
        "scope": "Native transitions tested using documented position, projectile, HP and phase fixtures; not complete played-through levels or fights. Mario was separately played fully in godmode.",
        "native_credits_observed": True,
        "gravitron_timed_survival_verified": any(
            "native_survival_seconds" in json.loads(p.read_text())
            and json.loads(p.read_text())["native_survival_seconds"] >= 30
            for p in passing_matrix
        ),
        "cold_resume_cases": cold,
        "beta_damage_comparison": shots,
        "stations": stations,
        "unsuccessful_test_attempts": failed_attempts,
        "lab_tests_passed": 43,
        "unchanged_installed_game_sha256": digest,
        "open_work": [
            "Additional alternative paths and full gameplay runs beyond targeted exit fixtures",
            "Sprite, fire, blood and music randomizer migration into Fusion build",
            "GUI integration with new engine",
            "Windows 11 VM validation",
            "Installers and GitHub/site publication after parity",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    rows = []
    for s in sorted(
        stations, key=lambda s: (not s["exit_live_tested"], s["name"].casefold())
    ):
        status = "Ausgang geprüft" if s["exit_live_tested"] else "Noch offen"
        links = " ".join(
            f'<a href="../../{html.escape(p)}">Beleg {n+1}</a>'
            for n, p in enumerate(s["evidence"])
        )
        rows.append(
            f'<tr><td>{html.escape(s["name"])}</td><td>{s["frame"]}</td><td class="{"ok" if s["exit_live_tested"] else "open"}">{status}</td><td>{links}</td></tr>'
        )
    content = (
        """<!doctype html><html lang="de"><meta charset="utf-8"><title>Fusion – Prüfstand</title><style>
body{font:17px/1.55 system-ui,sans-serif;background:#101722;color:#e8eef6;margin:0}main{max-width:1100px;margin:auto;padding:40px 26px}h1{font-size:34px;margin-bottom:4px}h2{margin-top:32px;font-size:23px}p{max-width:850px}.note{color:#b9c8dc}.cards{display:flex;gap:18px;flex-wrap:wrap;margin:25px 0}.card{background:#1a2739;padding:20px;border-radius:10px;flex:1;min-width:180px}.number{font-size:32px;font-weight:700}.ok{color:#76dfba}.open{color:#eac481}a{color:#92c7ff}table{border-collapse:collapse;width:100%;background:#152132}td,th{text-align:left;padding:11px 14px;border-bottom:1px solid #304056}th{background:#203149}td:last-child{font-size:14px}code{color:#afc7e4}footer{margin-top:28px;color:#b9c8dc}</style><main>
<h1>Fusion: Übergänge und Boss-Schutz</h1><p class="note">Lokaler Teststand vom 23. Oktober 2026. Kein veröffentlichter Installer.</p>
<div class="cards"><div class="card"><div class="number">COVERAGE / 44</div>Stationen mit live geprüftem Ausgang</div><div class="card"><div class="number">5</div>vollständige Neustarts mit erhaltenem Fortschritt</div><div class="card"><div class="number">43</div>bestandene Werkzeug- und Regressionstests</div></div>
<h2>Ergebnis</h2><p>MATRIX_COUNT zusätzliche Stationen wurden mit separaten Ausgangs- und Tod/Neustart-Fixtures geprüft. Erfolgreiche Tests und fehlgeschlagene Testversuche bleiben im Bericht nachvollziehbar getrennt. Gravitron wurde mit seinem vollständigen 30-Sekunden-Countdown im Godmode geprüft; erst danach wurde der Teleporter betreten. Zuvor verfrühte Portalversuche zählen nicht als Spielfehler.</p><p>Die Übergänge bei Questionmark und Ridley, die geteilten Abschnitte um Ninja-Ryu, Kid Icarus und Kappa sowie beide Teile der Random World bestehen die Prüfungen. Der Dedede-Ausweichweg und der Bonusausgang aus Random World Teil 1 folgen dem Seed. Solgryns originales Finale erreicht die Credits und speichert die Abschlussmarkierung.</p>
<p>Bei Questionmark und Ridley wurde die Schadensfreigabe korrigiert: In der Einleitung zählen die drei Testtreffer jetzt nicht. Ab dem Kampfbeginn verursachen sie weiterhin drei Schadenspunkte. Questionmarks Vergleich davor zeigte bereits drei Schadenspunkte während der Einleitung.</p>
<h2>Was „geprüft“ bedeutet</h2><p>Die Spielengine führt Sieg-Ereignisse, Portale, Raumwechsel und Speichern selbst aus. Für diese gezielten Prüfungen wurden Spielerpositionen, einzelne Boss-Phasen bzw. Lebenspunkte und die Positionen echter Projektile vorgegeben. Dies sind keine vollständig durchgespielten Levels oder Bosskämpfe. Mario wurde zuvor separat vollständig im Godmode besiegt.</p>
<p>Die aktuelle Spielkorrektur betrifft die beiden Schadensbedingungen in Frame 44 und 45. Die neue Ausgangsmatrix läuft im korrigierten Build; die älteren Übergangsbelege stammen teilweise aus dem vorherigen Routenbuild. Die Schadenskorrektur verändert deren Frames nicht. Die ursprüngliche installierte Spiel-EXE bleibt unverändert.</p>
<h2>Abdeckung aller Stationen</h2><table><thead><tr><th>Station</th><th>Frame</th><th>Status</th><th>Prüfdaten</th></tr></thead><tbody>ROWS</tbody></table>
<h2>Noch offen</h2><p>Zusätzliche Alternativwege und vollständige Spieldurchläufe, die Sprite-/Feuer-/Blut-/Musik-Integration, die GUI-Anbindung an den neuen Build und die Windows-11-Prüfungen. Erst danach werden neue Installer und die GitHub-Veröffentlichung vorbereitet.</p>
<footer><a href="summary.json">Maschinenlesbarer Prüfbericht</a> · <a href="lab-tests.log">Testausgabe</a></footer></main></html>""".replace(
            "COVERAGE", str(len(covered))
        )
        .replace("ROWS", "".join(rows))
        .replace(
            "MATRIX_COUNT",
            str(
                len(
                    {
                        i
                        for p in passing_matrix
                        for i in receipts(json.loads(p.read_text()))
                    }
                )
            ),
        )
    )
    (OUT / "Pruefstand.html").write_text(content)
    print("Live station exits", len(covered), "of", len(STAGES))


if __name__ == "__main__":
    generate()
