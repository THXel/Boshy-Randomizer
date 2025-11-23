from __future__ import annotations

from typing import Dict


def parse_ini(text: str) -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}
    sec: str | None = None
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("[") and s.endswith("]"):
            sec = s.strip("[]").lower()
            data.setdefault(sec, {})
            continue
        if "=" in s and sec:
            k, v = [x.strip() for x in s.split("=", 1)]
            data[sec][k] = v
    return data


def apply_values_in_section(
    original_text: str,
    section_name: str,
    kv_updates: Dict[str, str],
) -> str:
    lines = (original_text or "").splitlines()
    out: list[str] = []
    sec = None
    section_l = (section_name or "").lower()

    in_section = False
    seen_keys: set[str] = set()
    inserted_new = False

    has_section = any(
        ln.strip().lower() == f"[{section_l}]"
        for ln in lines
    )

    for line in lines:
        s = line.strip()

        if s.startswith("[") and s.endswith("]"):
            if in_section and not inserted_new:
                for k, v in kv_updates.items():
                    if k not in seen_keys:
                        out.append(f"{k}={v}")
                inserted_new = True

            sec = s.strip("[]").lower()
            in_section = (sec == section_l)
            out.append(line)
            continue

        if "=" in s and in_section:
            k, v = [x.strip() for x in s.split("=", 1)]
            if k in kv_updates:
                out.append(f"{k}={kv_updates[k]}")
                seen_keys.add(k)
            else:
                out.append(line)
        else:
            out.append(line)

    if not has_section:
        if out and out[-1] != "":
            out.append("")
        out.append(f"[{section_name}]")
        for k, v in kv_updates.items():
            out.append(f"{k}={v}")
        return "\n".join(out) + ("\n" if original_text.endswith("\n") else "\n")

    if has_section and not inserted_new:
        for k, v in kv_updates.items():
            if k not in seen_keys:
                out.append(f"{k}={v}")

    return "\n".join(out) + ("\n" if original_text.endswith("\n") else "")
