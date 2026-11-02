"""Recover Boshy colour/alpha-only records omitted by KlikBack 1.1.2.

This wrapper changes only the recovered object effect chunk. It does not
alter original EXE data, events, sprites, or installed game files.
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "KlikBack" / "src"))
from klikback.core.mmf2 import write_mfa
from klikback.cli import main

original_effect_chunk = write_mfa._object_effect_chunk
recovered = []

def preserve_alpha_only(obj, app, notes):
    ink = obj.get("inkEffect", 0)
    if obj.get("shader") is None and ink & 0x1000 and not ink & 0xFF:
        word = obj.get("inkEffectParameter", 0)
        recovered.append({"handle": obj["handle"], "name": obj.get("name"),
                          "ink": ink, "colour_alpha": word})
        notes.append("Boshy recovery: preserve colour/alpha-only effect for %r: 0x%08X" % (obj.get("name"), word))
        return struct.pack("<II", word, 0)
    return original_effect_chunk(obj, app, notes)

def run():
    write_mfa._object_effect_chunk = preserve_alpha_only
    try:
        status = main()
    finally:
        write_mfa._object_effect_chunk = original_effect_chunk
    report = Path(__file__).resolve().parents[2] / "outputs" / "Fusion-Graphics-20261023" / "alpha-recovery.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"changed_records": recovered, "exit_code": status}, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(run())
