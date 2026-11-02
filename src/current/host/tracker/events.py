"""Native ownership changes, with a baseline per save and no menu replay."""

import time
import uuid
from collections import OrderedDict


class Awards:
    def __init__(self):
        self.owned = OrderedDict()
        self.events = []
        self.prefix = uuid.uuid4().hex
        self.sequence = 0

    def update(self, data):
        identity = data.get("run_id")
        if not identity:
            return []
        owned = {
            (row["kind"], row["name"])
            for key in ("items", "characters", "bosses")
            for row in data.get(key, [])
            if row["done"]
        }
        previous = self.owned.get(identity)
        if previous is not None and data.get("phase") != "loading":
            for kind, name in sorted(owned - previous):
                self.sequence += 1
                self.events.append(
                    dict(
                        id=f"{self.prefix}:{self.sequence}",
                        run_id=identity,
                        kind=kind,
                        name=name,
                        time=time.time(),
                    )
                )
        self.owned[identity] = owned
        self.owned.move_to_end(identity)
        while len(self.owned) > 3:
            self.owned.popitem(last=False)
        self.events = self.events[-64:]
        return [e for e in self.events if e["run_id"] == identity]
