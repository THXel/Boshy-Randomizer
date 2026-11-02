"""Read-only, path-scoped inspection of the isolated Fusion test runtime."""

from pathlib import Path
from route_cases import CASES
from build_profiles import BUILDS
import json, os, struct, subprocess, argparse

ROOT = Path(__file__).resolve().parents[2]
WINE = "/home/thxel/.local/share/lutris/runners/wine/wine-staging-11.2-x86_64/bin/wine"
PREFIX = Path("/home/thxel/Games/clickteam-fusion-developer")


class MemoryReadUnavailable(RuntimeError):
    """The requested process memory was unloaded during inspection."""


class Bridge:
    def __init__(self, case):
        if case not in {
            "rebuilt-" + scene + suffix
            for scene in CASES
            for suffix in (b[2] for b in BUILDS.values())
        } and case not in (
            "rebuilt-mario-routes",
            "rebuilt-kracko-routes",
            "rebuilt-split-routes",
            "original-solgryn",
            "rebuilt-solgryn",
            "original-sonic",
            "rebuilt-sonic",
            "rebuilt-cheetah",
            "rebuilt-cheetah-seed",
            "rebuilt-kracko-exit",
            "rebuilt-mario-exit",
            "rebuilt-mario-links",
            "rebuilt-kracko-links",
            "rebuilt-cheetah-links",
            "rebuilt-cheetah-exit",
        ):
            raise ValueError(case)
        env = os.environ.copy()
        env.update(WINEPREFIX=str(PREFIX), WINEDEBUG="-all")
        self.p = subprocess.Popen(
            [
                WINE,
                str(Path(__file__).with_name("phase_bridge.exe")),
                f"C:\\BoshySceneTests\\{case}\\Boshy.exe",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self.ready = json.loads(self.p.stdout.readline())

    def cmd(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        s = ""
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError(self.p.stderr.read())
            s += line
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                continue

    def read(self, a, n):
        result = self.cmd(f"read {a:x} {n}")
        if result.get("error") == "read":
            raise MemoryReadUnavailable(f"Cannot read {n} bytes at {a:x}")
        if "hex" not in result:
            raise ValueError("Unexpected bridge response: " + repr(result))
        return bytes.fromhex(result["hex"])

    def u32(self, a):
        return struct.unpack("<I", self.read(a, 4))[0]

    def close(self):
        self.p.communicate("quit\n", timeout=5)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("case")
    a = p.parse_args()
    b = Bridge(a.case)
    try:
        scan = b.cmd("scan")
        from collections import Counter

        run = Counter(o["run"] for o in scan["objects"]).most_common(1)[0][0]
        print(
            "run",
            hex(run),
            "capacity",
            b.u32(run + 0x40),
            "table",
            hex(b.u32(run + 0x1278)),
        )
        print("table sample", b.read(b.u32(run + 0x1278), 128).hex(" "))
        for o in scan["objects"][:1] + scan["objects"][-1:]:
            raw = bytes.fromhex(o["hex"])
            oi_ptr = struct.unpack_from("<I", raw, 0x1C)[0]
            print("oi record", b.read(oi_ptr, 146).hex(" "))
            alt = o["ptr"] + struct.unpack_from("<I", raw, 128)[0]
            print("alterable header", b.read(alt, 64).hex(" "))
        (ROOT / "work/fusion-lab" / f"{a.case}-scan.json").write_text(json.dumps(scan))
    finally:
        b.close()
