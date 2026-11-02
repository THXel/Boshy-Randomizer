"""Verify image-bank lifetimes across native frame transitions and retries."""

from pathlib import Path
from live_route_session import LiveRouteSession, ROOT
from transition.router import GROUP, STAGES
from actor_live_probe import sprite_state

out = ROOT / "outputs/Fusion-Scenery-20261023/live-level-chain"
t = LiveRouteSession("prehistorik-routes", out, build="scenery")
try:
    t.report["scope"] = (
        "Temporary godmode and exit contact positions; real engine transitions with cloned textures"
    )
    t.protect()
    t.restart("save1.ini")
    t.protect()
    t.report["source"] = t.station("save1.ini")
    t.snap("prehistorik")
    gate = t.obj("Active 39")
    t.position(gate["x"], gate["y"])
    t.arrival("save7.ini", "castlevania")
    t.protect()
    t.position(850, 1280)
    t.wait(
        lambda: bool(t.objects("EnemyWidgetTurn 2"))
        and bool(t.objects("EnemyWidgetTurn 3"))
    )
    t.report["skeletons"] = [
        {**o, **sprite_state(t.state, o)}
        for name in ["EnemyWidgetTurn 2", "EnemyWidgetTurn 3"]
        for o in t.objects(name)
    ]
    t.snap("castlevania-skeletons")
    t.death_restart("save7.ini", "castlevania")
    t.protect()
    gate = t.obj("Active 36")
    t.position(gate["x"] + 8, gate["y"] + 16)
    t.arrival("boss_solgryn.ini", "solgryn")
    t.death_restart("boss_solgryn.ini", "solgryn")
    for spot in ["save1.ini", "save7.ini"]:
        assert t.saved().getint(GROUP, "Done" + str(STAGES[spot]["id"])) == 1
    t.report["final"] = t.station("boss_solgryn.ini")
except BaseException as error:
    t.finish(error)
    raise
else:
    t.finish()
    print("PASS native Prehistorik -> Castlevania -> Solgryn chain", flush=True)
