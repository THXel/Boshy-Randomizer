
from __future__ import annotations
from pathlib import Path
from .save_utils import write_ini_text, read_ini_text

def pin_savefiles_2_3(iwbtb_dir: str, template_text: str) -> None:
    for n in (2, 3):
        p = Path(iwbtb_dir) / f"SaveFile{n}.ini"
        # Always write template if missing or content differs significantly
        try:
            cur = ""
            if p.exists():
                cur = read_ini_text(p)
            if ("[Achievements]" not in cur) or ("[Stats]" not in cur) or len(cur) < 200:
                write_ini_text(p, template_text)
            else:
                # ensure critical keys exist; if not, rewrite
                must_have = ("[Achievements]", "Over9000Deaths", "TriggerFinger", "[Positions]", "[Randoms]")
                if not all(x in cur for x in must_have):
                    write_ini_text(p, template_text)
        except Exception:
            write_ini_text(p, template_text)
