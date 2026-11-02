"""Commit related Ini++ fields together, never autosave intermediate values.

INI++.mfx action 52 (event code 132) changes read-only mode without reloading
or saving data. In-memory edits remain allowed. Action 44 (124) saves the
complete document, respecting its existing filename, encryption and compression.
The IDs and parameter types come from the installed extension's action table.

This protects against frame/restart interruption between actions. It does not
claim crash-safe filesystem replacement; the host still validates each snapshot.
"""

from transition.events import action, expression, integer


def begin(oi):
    return action(33, 132, oi, [expression(integer(1))])


def finish(oi):
    return [
        action(33, 132, oi, [expression(integer(0))]),
        action(33, 124, oi, []),
    ]


def batch(oi, actions):
    return [begin(oi), *actions, *finish(oi)]
