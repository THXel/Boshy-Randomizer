"""Bounded parsed-save snapshots; file changes never reuse old progress."""
import stat
from pathlib import Path


class SnapshotCache:
    def __init__(self, loader):
        self.loader = loader
        self.entries = {}
        self.hits = 0
        self.misses = 0

    def clear(self):
        self.entries.clear()

    @staticmethod
    def signature(path):
        s = path.lstat()
        if not stat.S_ISREG(s.st_mode) or not 0 < s.st_size < 2_000_000:
            raise ValueError('Save boundary')
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

    def __call__(self, path):
        path = Path(path)
        signature = self.signature(path)
        prior = self.entries.get(path)
        if prior and prior[0] == signature:
            self.hits += 1
            return prior[1]
        self.entries.pop(path, None)
        value = self.loader(path)
        if self.signature(path) != signature:
            raise OSError('Save changed while being read')
        self.misses += 1
        if len(self.entries) >= 2:
            self.entries.clear()
        self.entries[path] = (signature, value)
        return value
