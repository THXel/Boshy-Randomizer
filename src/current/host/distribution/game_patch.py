"""Exact original-dependent patch container for private packaging tests.

Original images and sounds are reconstructed, identical chunks are copied, and
only changed code/metadata/artwork is stored. No original or full target EXE is
embedded. This technical property is not a distribution-license determination.
"""

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path
from distribution import source_audio, source_images
from distribution.identity import sha256
from distribution.progress import ignore
from distribution.original import ORIGINAL_SHA
from visuals.scenery_pack import App

MAX_PATCH = 128_000_000
MAX_TARGET = 256_000_000


def build(original, target, output):
    original, target, output = Path(original), Path(target), Path(output)
    if sha256(original) != ORIGINAL_SHA:
        raise ValueError("Unsupported original game")
    if output.exists():
        raise FileExistsError(output)
    src, dst = App(original), App(target)
    image_spec, images = source_images.recipe(src, dst)
    audio_spec = source_audio.recipe(src, dst)
    copy_chunks = {
        source_audio.digest(src.data[c.offset : c.offset + 8 + c.size]): (
            c.offset,
            c.size + 8,
        )
        for c in src.chunks
    }
    parts, payload = [], {"images/" + k: v for k, v in images.items()}

    def literal(data):
        key = "parts/" + str(len(parts))
        payload[key] = data
        parts.append({"literal": key})

    literal(dst.data[: dst.chunks[0].offset])
    end = 0
    for chunk in dst.chunks:
        end = chunk.offset + 8 + chunk.size
        raw = dst.data[chunk.offset : end]
        if chunk.id in (0x6666, 0x6668):
            if chunk.flags != 0:
                raise ValueError("Unexpected packed asset bank")
            parts.append(
                {
                    "bank": "images" if chunk.id == 0x6666 else "audio",
                    "header": raw[:8].hex(),
                }
            )
        elif source_audio.digest(raw) in copy_chunks:
            offset, size = copy_chunks[source_audio.digest(raw)]
            parts.append({"source": offset, "size": size})
        else:
            literal(raw)
    literal(dst.data[end:])
    manifest = {
        "schema": 1,
        "source_sha256": ORIGINAL_SHA,
        "target_sha256": sha256(target),
        "target_size": len(dst.data),
        "images": image_spec,
        "audio": audio_spec,
        "parts": parts,
        "payload": {k: source_audio.digest(v) for k, v in payload.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".patch-build-", dir=output.parent) as tmp:
        candidate = Path(tmp) / "candidate.bpatch"
        with zipfile.ZipFile(
            candidate, "w", zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, sort_keys=True, separators=(",", ":")),
            )
            for name, data in sorted(payload.items()):
                archive.writestr(name, data)
        rebuilt = Path(tmp) / "verified.exe"
        apply(
            original,
            candidate,
            rebuilt,
            expected_patch=sha256(candidate),
            expected_target=manifest["target_sha256"],
        )
        os.replace(candidate, output)
    return {
        "source_sha256": ORIGINAL_SHA,
        "target_sha256": manifest["target_sha256"],
        "patch_sha256": sha256(output),
        "patch_bytes": output.stat().st_size,
        "images_reused": len(image_spec["rows"]) - len(images),
        "images_changed_or_added": len(images),
        "sounds_reused": len(audio_spec["rows"]),
        "exact_reconstruction": True,
        "publication": False,
    }


def apply(original, patch, output, *, expected_patch, expected_target, progress=ignore):
    original, patch, output = Path(original), Path(patch), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if sha256(original) != ORIGINAL_SHA or sha256(patch) != expected_patch:
        raise ValueError("Original or patch checksum mismatch")
    with zipfile.ZipFile(patch) as archive:
        info = archive.infolist()
        if len(info) > 20000 or sum(i.file_size for i in info) > MAX_PATCH:
            raise ValueError("Patch exceeds resource bounds")
        names = [i.filename for i in info]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate patch member")
        if archive.getinfo("manifest.json").file_size > 8_000_000:
            raise ValueError("Oversized patch manifest")
        spec = json.loads(archive.read("manifest.json"))
        if (
            spec.get("schema") != 1
            or spec.get("source_sha256") != ORIGINAL_SHA
            or spec.get("target_sha256") != expected_target
        ):
            raise ValueError("Patch identity mismatch")
        if (
            type(spec["target_size"]) is not int
            or not 0 < spec["target_size"] <= MAX_TARGET
        ):
            raise ValueError("Invalid target size")
        if set(names) != {"manifest.json", *spec["payload"]}:
            raise ValueError("Unexpected patch members")
        payload = {name: archive.read(name) for name in spec["payload"]}
    if any(
        source_audio.digest(data) != spec["payload"][name]
        for name, data in payload.items()
    ):
        raise ValueError("Damaged patch payload")
    progress("images")
    src = App(original)
    images, _ = source_images.restore(
        src,
        spec["images"],
        {
            k.removeprefix("images/"): v
            for k, v in payload.items()
            if k.startswith("images/")
        },
        progress=progress,
    )
    progress("audio")
    audio, _ = source_audio.restore(src, spec["audio"], progress=progress)
    progress("writing", 0, spec["target_size"])
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".patched-", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            for part in spec["parts"]:
                if "literal" in part:
                    data = payload[part["literal"]]
                elif "source" in part:
                    offset, size = part["source"], part["size"]
                    if (
                        type(offset) is not int
                        or type(size) is not int
                        or offset < 0
                        or size < 0
                        or offset + size > len(src.data)
                    ):
                        raise ValueError("Patch copy outside original")
                    data = src.data[offset : offset + size]
                else:
                    data = (
                        bytes.fromhex(part["header"])
                        + {"images": images, "audio": audio}[part["bank"]]
                    )
                if stream.tell() + len(data) > spec["target_size"]:
                    raise ValueError("Patch exceeds expected target")
                stream.write(data)
                progress("writing", stream.tell(), spec["target_size"])
            stream.flush()
            os.fsync(stream.fileno())
        if (
            Path(tmp).stat().st_size != spec["target_size"]
            or sha256(tmp) != expected_target
        ):
            raise ValueError("Reconstructed executable differs")
        os.replace(tmp, output)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.original, args.target, args.output), indent=2))


if __name__ == "__main__":
    main()
