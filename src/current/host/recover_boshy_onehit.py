"""Recover a separate native gameplay build including phase-local boss damage."""
import json,sys
from pathlib import Path
import recover_boshy_gameplay as gameplay
from gameplay.one_hit import transform
routes=gameplay.routes
changes=[]
def sections(payload):
    frame=routes.payloads[payload]
    ss,audit=transform(frame,gameplay.sections(payload),routes.objects,routes.frames[frame-1]["instances"])
    changes.extend(audit)
    return ss
if __name__=="__main__":
    assert Path(sys.argv[1]).resolve()==routes.SOURCE.resolve()
    type(routes.app).frame_handles=routes.handles
    routes.write_mfa._object_effect_chunk=routes.preserve_alpha_only
    routes.write_mfa._write_frame_item=gameplay.blood.item
    routes.write_mfa._exe_event_sections=sections
    try:status=routes.main()
    finally:
        type(routes.app).frame_handles=routes.original_handles
        routes.write_mfa._write_frame_item=gameplay.blood.original_item
    assert status==0 and len(changes)==68
    out=Path(sys.argv[sys.argv.index("--out")+1])
    (out/"onehit-source-audit.json").write_text(json.dumps(dict(
        scope="Generated source; compilation and live verification required",
        one_hit=changes,gameplay=gameplay.changes,blood=gameplay.blood.changes,routes=routes.changes
    ),indent=2)+"\n")
