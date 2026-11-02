"""Read actor animation banks across private scenery on/off builds, serially."""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
OUT = LAB.parents[1] / "outputs/Fusion-Scenery-20261023"

def layout(record):
    bank = bytes.fromhex(record["animation_bank_hex"])
    masked = bytearray(bank)
    size, count = struct.unpack_from("<HH", bank)
    assert size == len(bank) and 4 + count * 2 <= size
    handles = {}
    for a in range(count):
        start = struct.unpack_from("<h", bank, 4 + a * 2)[0]
        # Fusion fills absent animations/directions with negative fallback markers.
        if start <= 0:
            continue
        assert start + 64 <= size
        for d in range(32):
            offset = struct.unpack_from("<h", bank, start + d * 2)[0]
            if offset <= 0:
                continue
            at = start + offset
            assert at + 8 <= size
            frames = struct.unpack_from("<H", bank, at + 6)[0]
            assert at + 8 + frames * 2 <= size
            for f in range(frames):
                pos = at + 8 + f * 2
                handles[pos] = struct.unpack_from("<H", bank, pos)[0]
                masked[pos:pos+2] = bytes(2)
    assert handles
    return hashlib.sha256(masked).hexdigest(), handles

def main():
    results = {}
    for scene in ["castlevania-routes", "prehistorik-routes", "secret-mario-routes"]:
        samples = []
        for mode in ["off", "on"]:
            result = OUT / ("animation-inspect-"+scene+"-"+mode) / "result.json"
            if not result.exists():
                build = "scenery" if mode == "on" else "actors"
                with (OUT/("animation-inspect-"+scene+"-"+mode+".log")).open("x") as log:
                    for args in [
                        ["scene_probe.py", "rebuilt", scene, "--route-build", build,
                         "--save-fixture", str(OUT/("seed-"+scene+"-"+mode)/"SaveFile1.ini"),
                         "--seconds", "0", "--leave-open", "--output-group", "Fusion-Scenery-Inspect-"+scene+"-"+mode],
                        ["scenery_animation_probe.py", scene, mode]
                    ]:
                        run = subprocess.run([sys.executable, str(LAB/args[0]), *args[1:]], stdout=log, stderr=subprocess.STDOUT, timeout=100)
                        assert run.returncode == 0, (scene, mode, args[0])
            record = json.loads(result.read_text())
            assert record["passed"]
            samples.append({oi: layout(r) for oi,r in record["animations"].items()})
            print("captured", scene, mode, flush=True)
        assert samples[0].keys() == samples[1].keys()
        results[scene] = {}
        for oi in samples[0]:
            off, on = [s[oi] for s in samples]
            assert off[0] == on[0], (scene, oi, "Animation layout changed")
            results[scene][oi] = {"layout_sha256":off[0], "layout_equal":True,
                "off_image_handles":off[1], "on_image_handles":on[1]}
        print("PASS layout", scene, flush=True)
    (OUT/"animation-comparison.json").write_text(json.dumps(results, indent=2)+"\n")

if __name__ == "__main__":
    main()
