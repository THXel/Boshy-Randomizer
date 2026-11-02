"""Isolated UI fixture server; never writes the actual game feed."""
import json
from pathlib import Path
from tracker.server import Server
ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/'outputs/Fusion-StandaloneTracker-20261025/browser-fixture.json'
def source():
    try:return json.loads(PATH.read_text())
    except (ValueError,OSError):return None
Server(18766,source=source).serve_forever()
