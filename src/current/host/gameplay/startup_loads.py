"""Remove redundant generated save loads inside a straight start-event prelude.

This is compile-time coalescing, not a cache across resets. Each room start still
reads the current save. Stop tracking at any ordinary event or system action;
any other action on the INI object invalidates its known contents. Only an exact
standalone, unconditional generated load can be removed. Original conditional
loads, writes, save transactions and action order remain untouched.
"""
from gameplay.native_events import Events
from transition.events import commands


def transform(frame, sections):
    if not sections:
        return sections, []
    known = {}
    rows = []
    removed = []
    for index, row in enumerate(sections[0]):
        cs = commands(row)
        conditions = [c for c in cs if c[0]]
        actions = [c for c in cs if not c[0]]
        if row[4:14] != bytes(10) or not any(c[1:3] == (-3, -1) for c in conditions):
            known.clear()
            rows.append(row)
            continue
        duplicate = False
        for c in actions:
            if c[1] == 33:
                exact = (len(conditions) == 1 and len(actions) == 1
                         and c[-1] == Events.load(c[3], 'SaveFile1.ini'))
                if exact:
                    duplicate = known.get(c[3]) == c[-1]
                    known[c[3]] = c[-1]
                else:
                    known.pop(c[3], None)
            elif c[1] < 0:
                known.clear()
        if duplicate:
            removed.append(index)
        else:
            rows.append(row)
    return [rows, *sections[1:]], ([dict(frame=frame, rule='coalesce_start_loads',
                                       removed=removed)] if removed else [])
