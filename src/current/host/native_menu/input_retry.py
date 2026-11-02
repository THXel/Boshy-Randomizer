"""Retry an unacknowledged native menu input after a transient save failure.

INI++ may fail to save while another reader holds the mailbox open. Its in-memory
sequence has already advanced, so the normal input guards then reject every new
key. Resend the same pending command; only the host acknowledgement releases it.
"""

from gameplay.native_events import Events
from native_menu.events import INPUT, VIEW, GROUP
from transition.events import action, ini_value, integer


def transform(sections):
    e = Events(sections, low=0xD900, high=0xDA00)
    pending = e.cmp(
        ini_value(GROUP, "Sequence", 0, oi=INPUT),
        e.add(ini_value(GROUP, "Ack", 0, oi=VIEW), integer(1)),
    )
    return [
        *sections,
        [
            e.row(
                [e.eq(VIEW, GROUP, "Schema", 3), pending],
                [action(33, 124, INPUT, [])],
            )
        ],
    ]
