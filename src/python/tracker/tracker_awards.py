"""Detect only new ownership within one loaded run; never replay a loaded save."""


class Awards:
    def __init__(self):
        self.identity = None
        self.owned = set()
        self.sequence = 0
        self.events = []

    def update(self, identity, rows):
        owned = {(r['kind'], r['name']) for r in rows if r.get('done')}
        if identity != self.identity:
            self.identity = identity
            self.owned = owned
            self.events = []
            return []
        result = []
        for kind, name in sorted(owned - self.owned):
            self.sequence += 1
            result.append(
                dict(
                    id=f'{identity}:{self.sequence}',
                    kind='reward',
                    reward_type=kind,
                    name=name,
                    icon=name + '.png',
                )
            )
        self.owned = owned
        self.events = (self.events + result)[-64:]
        return result
