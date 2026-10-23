"""Observed run highlights. Never infer unobserved playtime or pickup order."""

import json
import time
from native_session import write_json


def initialize(store, m):
    path = store.root / m['run_id'] / 'insights.json'
    if not path.exists():
        write_json(
            path,
            dict(
                version=1,
                run_id=m['run_id'],
                binding=m['session_binding'],
                partial=False,
                segments=[],
                finds=[],
                seen=[],
                last_deaths=0,
                finished=False,
            ),
        )


class Insights:
    def __init__(self, store, m, clock=time.monotonic):
        self.store = store
        self.m = m
        self.clock = clock
        self.path = store.root / m['run_id'] / 'insights.json'
        self.last = None
        self.saved = clock()
        self.data = (
            json.loads(self.path.read_text(encoding='utf-8'))
            if self.path.exists()
            else dict(
                version=1,
                run_id=m['run_id'],
                binding=m['session_binding'],
                partial=True,
                segments=[],
                finds=[],
                seen=None,
                last_deaths=None,
                finished=False,
            )
        )
        if (
            self.data['run_id'] != m['run_id']
            or self.data['binding'] != m['session_binding']
        ):
            raise ValueError('Auswertung gehört zu anderem Lauf.')

    def save(self):
        write_json(self.path, self.data)
        self.saved = self.clock()

    def pause(self):
        self.last = None
        self.save()

    def observe(self, progress, stats, claims, collectables=None, finished=False):
        if self.data['finished']:
            return
        now = self.clock()
        elapsed = 0 if self.last is None else max(0, now - self.last)
        self.last = now
        if elapsed > 5:
            elapsed = 0
        deaths = int(stats.get('deaths', 0))
        previous = self.data['last_deaths']
        delta = 0 if previous is None else max(0, deaths - previous)
        self.data['last_deaths'] = deaths
        rows = self.data['segments']
        identity = (progress['index'], progress['spot'])
        changed = False
        # The just elapsed interval belongs to the section we observed before the move.
        if rows:
            rows[-1]['seconds'] += elapsed
            rows[-1]['deaths'] += delta
        if not rows or (rows[-1]['index'], rows[-1]['spot']) != identity:
            if rows:
                rows[-1]['closed'] = True
            from native_models import location

            point = self.m['pool'].get(identity[1], {})
            rows.append(
                dict(
                    index=identity[0],
                    spot=identity[1],
                    name=point.get('label', location(point.get('frame'))),
                    boss=point.get('category') == 'bosses',
                    seconds=0.0,
                    deaths=delta if not rows else 0,
                    closed=False,
                )
            )
            changed = True
        # Native receipt file timestamps provide ordering inside a polling interval.
        earned = sorted(
            claims,
            key=lambda key: (
                (
                    self.store.root
                    / self.m['run_id']
                    / 'rewards'
                    / (key.lower() + '.wal')
                )
                .stat()
                .st_mtime_ns,
                key,
            ),
        )
        if collectables and str(collectables.get('gastly', '0')) == '1':
            earned.append('@gastly')
        if self.data['seen'] is None:
            self.data['seen'] = list(earned)
        for key in earned:
            if key in self.data['seen']:
                continue
            reward = (
                dict(name='Gastly', kind='item')
                if key == '@gastly'
                else self.m['rewards'][key]
            )
            self.data['finds'].append(
                dict(
                    **reward,
                    source=key,
                    spot=identity[1],
                    index=identity[0],
                    time=time.time(),
                )
            )
            self.data['seen'].append(key)
            changed = True
        if finished:
            if rows:
                rows[-1]['closed'] = True
            self.data['finished'] = True
            changed = True
        if changed or delta or now - self.saved >= 2:
            self.save()
        if finished:
            self.decorate()

    def highlights(self):
        rows = self.data['segments']
        bosses = [r for r in rows if r['boss']]
        return dict(
            partial=self.data['partial'],
            hardest=(
                max(rows, key=lambda r: (r['deaths'], r['seconds'])) if rows else None
            ),
            longest_boss=max(bosses, key=lambda r: r['seconds']) if bosses else None,
            finds=self.data['finds'],
            segments=rows,
        )

    def decorate(self):
        path = self.path.with_name('summary.json')
        if path.exists():
            summary = json.loads(path.read_text(encoding='utf-8'))
            summary['highlights'] = self.highlights()
            write_json(path, summary)
