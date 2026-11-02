"""Preserve non-contiguous frame handles, including compiled aliases.

Fusion frame-jump literals address handles, not positions. Boshy's 62-entry
lookup maps onto 61 frames: handles 2 and 4 both address frame position zero.
The recovered project needs one canonical handle per frame and equivalent
literal references for aliases. Expression-based jumps remain unchanged.
"""

import struct
from transition.events import commands, event


def mapping(payload, frame_count):
    if payload is None or len(payload) % 2:
        raise ValueError("Missing or malformed frame-handle lookup")
    table = struct.unpack("<" + "H" * (len(payload) // 2), payload)
    canonical = [None] * frame_count
    for handle, position in enumerate(table):
        if position != 0xFFFF and position >= frame_count:
            raise ValueError("Frame handle references an absent frame")
        if position < frame_count and canonical[position] is None:
            canonical[position] = handle
    if any(handle is None for handle in canonical):
        raise ValueError("A frame has no recoverable handle")
    aliases = {
        h: canonical[p]
        for h, p in enumerate(table)
        if p < frame_count and h != canonical[p]
    }
    return table, canonical, aliases


def rewrite_sections(sections, aliases, table):
    result = []
    changes = []
    literals = []
    for section_index, section in enumerate(sections):
        rows = []
        for row_index, row in enumerate(section):
            conditions = []
            actions = []
            for command_index, (condition, kind, code, oi, raw) in enumerate(
                commands(row)
            ):
                updated = bytearray(raw)
                offset = 16 if condition else 14
                for parameter_index in range(raw[12]):
                    size, ptype = struct.unpack_from("<HH", raw, offset)
                    if size < 4 or offset + size > len(raw):
                        raise ValueError("Invalid event parameter layout")
                    if ptype == 26:
                        if size != 8:
                            raise ValueError("Unknown frame literal layout")
                        handle = struct.unpack_from("<I", raw, offset + 4)[0]
                        if handle >= len(table):
                            raise ValueError("Unknown literal frame handle")
                        position = table[handle]
                        # 0xffff denotes the engine's next-frame fallback; do not
                        # silently assign a destination that the original lacks.
                        if position == 0xFFFF:
                            raise ValueError("Unresolved deleted frame literal")
                        literals.append(
                            {
                                "section": section_index,
                                "row": row_index,
                                "command": command_index,
                                "handle": handle,
                                "destination_frame": position + 1,
                            }
                        )
                        if handle in aliases:
                            struct.pack_into("<I", updated, offset + 4, aliases[handle])
                            changes.append(
                                {
                                    "section": section_index,
                                    "row": row_index,
                                    "command": command_index,
                                    "old": handle,
                                    "new": aliases[handle],
                                }
                            )
                    offset += size
                if offset != len(raw):
                    raise ValueError("Unconsumed event parameters")
                (conditions if condition else actions).append(bytes(updated))
            rows.append(event(row, conditions, actions))
        result.append(rows)
    return result, {"literal_alias_changes": changes, "literal_destinations": literals}
