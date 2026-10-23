"""Reversible three-slot lifecycle for the native Boshy laboratory.

Installed native mode uses the same reversible save lifecycle. Each slot is initialized only by an
explicit new run; resume never resets inventory, checks or the Gastly journal.
"""

from host_platform import replace_file
from pathlib import Path
from contextlib import contextmanager
import hashlib
import json
import os
import shutil
import uuid
import time
from host_platform import lock_file, owned_process

FILES = ('SaveFile1.ini', 'onlineLicense.ini', 'options.ini')
ASSETS = (
    'reward_journal.py',
    'native_targets.py',
    'native_menu.dll',
    'character_cycle.py',
    'INI/characters_rando.json',
    'native-icons/Simon Belmont.bmp',
    'native-icons/Spike.bmp',
    'slot_reward_plan.json',
    'slot_reward_hook.bin',
    'slot_reward_symbols.json',
    'slot_reward_launcher.exe',
    'native_start_profile.json',
    'native_spots.json',
    'mixed_rewards.py',
    'Custom/trophies/Arthur.png',
    'Custom/trophies/Ash Ketchum.png',
    'Custom/trophies/Awesomesauce.png',
    'Custom/trophies/Barrel Roll CD.png',
    'Custom/trophies/Cake.png',
    'Custom/trophies/Chocolate CD.png',
    'Custom/trophies/Cookie CD.png',
    'Custom/trophies/Dark Boshy.png',
    'Custom/trophies/Hamster CD.png',
    'Custom/trophies/Kappa.png',
    'Custom/trophies/Keyboard Cat CD.png',
    'Custom/trophies/Kirby.png',
    'Custom/trophies/LIVE CD.png',
    'Custom/trophies/Lalalalalala CD.png',
    'Custom/trophies/Luigi.png',
    'Custom/trophies/Mario.png',
    'Custom/trophies/Metal Gear.png',
    'Custom/trophies/Mixer.png',
    'Custom/trophies/Mr Game And Watch.png',
    'Custom/trophies/Orc.png',
    'Custom/trophies/Pit.png',
    'Custom/trophies/Quote.png',
    'Custom/trophies/RickRoll CD.png',
    'Custom/trophies/Rupees.png',
    'Custom/trophies/Ryu.png',
    'Custom/trophies/Sagat.png',
    'Custom/trophies/Sax CD.png',
    'Custom/trophies/Scouter.png',
    'Custom/trophies/Sexy Sax CD.png',
    'Custom/trophies/Simon Belmont.png',
    'Custom/trophies/Solgryn.png',
    'Custom/trophies/Sonic.png',
    'Custom/trophies/Spike.png',
    'Custom/trophies/Timer.png',
    'Custom/trophies/Trololol CD.png',
    'Custom/trophies/Wily CD.png',
)


def assets_for(options):
    from extras_runtime import ASSETS as EXTRA_ASSETS

    return ASSETS + EXTRA_ASSETS if 'extras' in options else ASSETS


SAFE_SPOTS = (
    'save1.ini',
    'save2.ini',
    'save3.ini',
    'save4.ini',
    'save6.ini',
    'save7.ini',
    'gastly_grass',
    'boss_solgryn.ini',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        replace_file(temp, path)
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if temp.exists():
            temp.unlink()


def write_json(path, value):
    atomic(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


def section(text, name, values):
    """Replace exactly one case-insensitive group, preserve every other line."""
    out = []
    inside = False
    for line in text.splitlines():
        if line.strip().startswith('[') and line.strip().endswith(']'):
            inside = line.strip()[1:-1].casefold() == name.casefold()
        if not inside:
            out.append(line)
    return (
        '\n'.join(out)
        + '\n['
        + name
        + ']\n'
        + ''.join(f'{k}={v}\n' for k, v in values.items())
    )


_CURRENT = object()


class SessionStore:
    def __init__(self, base, *, read_save, encode_save, game_running=lambda: False):
        self.base = Path(base)
        self.root = self.base / 'native-runs'
        self.read_save = read_save
        self.encode_save = encode_save
        self.game_running = game_running

    @contextmanager
    def lock(self):
        self.root.mkdir(exist_ok=True)
        with (self.root / 'session.lock').open('a') as f:
            try:
                lock_file(f)
            except BlockingIOError:
                raise RuntimeError('Ein Randomizer-Lauf wird bereits verwaltet.')
            if (self.root / 'delete-pending.json').exists():
                self.recover_delete()
            yield

    def registry(self):
        p = self.root / 'slots.json'
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

    def current(self, slot=1):
        if slot not in (1, 2, 3):
            raise ValueError('Ungültiger Speicherplatz.')
        run = self.registry().get(str(slot))
        if run is None:
            return None
        if (
            not isinstance(run, str)
            or len(run) != 32
            or any(c not in '0123456789abcdef' for c in run)
        ):
            raise ValueError('Ungültiger Laufverweis.')
        m = json.loads((self.root / run / 'manifest.json').read_text(encoding='utf-8'))
        if m['run_id'] != run or m['slot'] != slot:
            raise ValueError('Laufverweis passt nicht zum Slot.')
        return m

    def by_id(self, run_id):
        for slot in (1, 2, 3):
            m = self.current(slot)
            if m and m['run_id'] == run_id:
                return self.validate(m)
        raise ValueError(
            'Dieser Spielstand wurde noch nicht als nativer Randomizer-Lauf vorbereitet.'
        )

    def save_manifest(self, m):
        write_json(self.root / m['run_id'] / 'manifest.json', m)

    def _stopped(self):
        if self.game_running():
            guard = getattr(self, '_menu_guard', None)
            if guard is None:
                raise RuntimeError('Das Spiel läuft noch. Zuerst regulär schließen.')
            guard()

    def prepare(self, seed, slot=1, options=None):
        self._stopped()
        if slot not in (1, 2, 3):
            raise ValueError('Ungültiger Speicherplatz.')
        if not str(seed).strip():
            raise ValueError('Bitte einen Seed eingeben.')
        from beta_catalogue import goals, ROOMS, BOSSES, EXTRA_POINTS
        from run_settings import normalize, decode, route, pool_names, character

        seed, options = decode(seed, options)
        character(self.base, seed, options)
        old = self.current(slot)
        if old and old['status'] != 'restored':
            raise RuntimeError(
                'Dieser Slot hat bereits einen Lauf. Fortsetzen oder zuerst zurücksetzen.'
            )
        name = f'SaveFile{slot}.ini'
        path = self.base / 'IWBTB' / name
        if path.is_symlink():
            raise ValueError('Verknüpfte Spielstände werden nicht verändert.')
        from native_level_route import catalogue

        pool = catalogue(
            json.loads((self.base / 'INI/positions.json').read_text(encoding='utf-8'))
        )
        pool.update(
            json.loads((self.base / 'native_spots.json').read_text(encoding='utf-8'))
        )
        names = (
            SAFE_SPOTS
            if options.get('mode') != 'target'
            else tuple(
                dict.fromkeys(
                    (
                        *SAFE_SPOTS,
                        *ROOMS,
                        *(
                            BOSSES[k][2]
                            for k in goals(self.base, seed, options)['bosses']
                        ),
                    )
                )
            )
        )
        if (
            options.get("route_version") in (2, 3, 4, 5, 6, 7, 8, 9)
            or options.get("mode") == "target"
        ):
            names = pool_names(options)
        pool.update(EXTRA_POINTS)
        from minibosses import prepare_pool

        pool = prepare_pool(pool, options)
        pool = {k: pool[k] for k in names}
        plan = json.loads(
            (self.base / 'slot_reward_plan.json').read_text(encoding='utf-8')
        )
        from mixed_rewards import assignments
        from seed_audit import audit

        rewards = (
            assignments(seed, plan)
            if options['items']
            else {
                l['key']: dict(name=l['source'], kind=l['source_kind'])
                for l in plan['locations']
            }
        )
        seed_check = audit(self.base, seed, options, pool, rewards, plan['locations'])
        if seed_check['errors']:
            raise ValueError('Seed-Prüfung: ' + '; '.join(seed_check['errors']))
        run = uuid.uuid4().hex
        folder = self.root / run
        folder.mkdir()
        (folder / 'before').mkdir()
        write_json(folder / 'seed-check.json', seed_check)
        before = path.read_bytes() if path.exists() else None
        if before is not None:
            atomic(folder / 'before' / name, before)
        assets = {n: digest((self.base / n).read_bytes()) for n in assets_for(options)}
        from mixed_rewards import assignments

        binding = dict(
            run_id=run,
            slot=slot,
            seed=str(seed),
            options=options,
            rewards=rewards,
            assets=assets,
            pool=pool,
            game_hash=digest(
                (self.base / 'IWBTB/I Wanna Be The Boshy.exe').read_bytes()
            ),
        )
        m = {
            **binding,
            'session_binding': digest(json.dumps(binding, sort_keys=True).encode()),
            'status': 'preparing',
            'backup_hash': digest(before) if before is not None else None,
        }
        self.save_manifest(m)
        registry = self.registry()
        registry[str(slot)] = run
        write_json(self.root / 'slots.json', registry)
        data = None
        try:
            profile = json.loads(
                (self.base / 'native_start_profile.json').read_text(encoding='utf-8')
            )
            save = '\n'.join(profile['content']) + '\n'
            save = section(
                save,
                'Collectables',
                dict(Awesomesauce=0, Gastly=0, Scouter=0, Timer=0, Cake=0),
            )
            from PY.ini_utils import apply_values_in_section

            save = apply_values_in_section(
                save, 'Stats', {'Difficulty': str(options['difficulty'])}
            )
            planned = route(seed, options)
            first = (
                pool[planned[0]]
                if planned and options['levels']
                else dict(frame=3, x=30, y=40)
            )
            save = section(
                save,
                'Positions',
                dict(frame=first['frame'], xPos=first['x'], yPos=first['y']),
            )
            checks = {
                'RunId': plan['run_id'],
                'Binding': plan['binding'],
                'SessionId': run,
                'SessionBinding': m['session_binding'],
                'Slot': slot,
            }
            checks.update({s['key']: '0' for s in plan['locations']})
            data = self.encode_save(section(save, 'RandoChecks', checks))
            atomic(path, data)
            from native_profiles import make_profile

            make_profile(self, m)
            from reward_journal import initialize

            initialize(self, m)
            from run_insights import initialize as initialize_insights

            initialize_insights(self, m)
            from runtime_versions import pin

            pin(self, m)
            self.validate(m, allow_preparing=True)
            m['status'] = 'ready'
            self.save_manifest(m)
            return m
        except Exception:
            current = path.read_bytes() if path.exists() else None
            if current not in (before, data):
                raise RuntimeError(
                    'Spielstand hat sich während der Vorbereitung geändert. Sicherung bleibt erhalten.'
                )
            if before is not None:
                atomic(path, before)
            elif path.exists():
                path.unlink()
            m['status'] = 'restored'
            self.save_manifest(m)
            raise

    def validate(self, m=_CURRENT, *, allow_preparing=False):
        from PY.ini_utils import parse_ini

        if m is _CURRENT:
            m = self.current()
        if not m or m['status'] not in (
            ('ready', 'preparing') if allow_preparing else ('ready',)
        ):
            raise ValueError('Kein fortsetzbarer Randomizer-Lauf vorhanden.')
        self.validate_binding(m)
        from runtime_versions import Rules

        plan = json.loads(
            (Rules(self, m).base / 'slot_reward_plan.json').read_text(encoding='utf-8')
        )
        name = f"SaveFile{m['slot']}.ini"
        d = parse_ini(self.read_save(self.base / 'IWBTB' / name))
        v = {k.casefold(): v for k, v in d.get('randochecks', {}).items()}
        expected = dict(
            sessionid=m['run_id'],
            sessionbinding=m['session_binding'],
            slot=str(m['slot']),
            runid=plan['run_id'],
            binding=plan['binding'],
        )
        if any(v.get(k) != value for k, value in expected.items()):
            raise ValueError('Spielstand und Lauf passen nicht zusammen: ' + name)
        if any(v.get(s['key'].casefold()) not in ('0', '1') for s in plan['locations']):
            raise ValueError('Ungültiger Fundortstatus: ' + name)
        return m

    def validate_binding(self, m):
        from runtime_versions import Rules

        rules = Rules(self, m)
        normalize = rules.module('run_settings').normalize
        if normalize(m['options']) != m['options']:
            raise ValueError('Unvereinbare Target-Optionen.')
        binding = {
            k: m[k]
            for k in (
                'run_id',
                'slot',
                'seed',
                'options',
                'rewards',
                'assets',
                'pool',
                'game_hash',
            )
        }
        if digest(json.dumps(binding, sort_keys=True).encode()) != m['session_binding']:
            raise ValueError('Laufdaten stimmen nicht mit ihrer Bindung überein.')
        if set(m['assets']) != set(
            ASSETS
            + (
                rules.module('extras_runtime').ASSETS
                if 'extras' in m['options']
                else ()
            )
        ):
            raise ValueError('Ungültige Patchliste.')
        for n, h in m['assets'].items():
            if digest((rules.base / n).read_bytes()) != h:
                raise ValueError(
                    'Der Spielpatch hat sich seit Laufbeginn geändert: ' + n
                )
        if (
            digest((self.base / 'IWBTB/I Wanna Be The Boshy.exe').read_bytes())
            != m['game_hash']
        ):
            raise ValueError('Andere Spielversion.')
        plan = json.loads(
            (rules.base / 'slot_reward_plan.json').read_text(encoding='utf-8')
        )
        validate_rewards = rules.module('mixed_rewards').validate
        validate_rewards(m['rewards'], m['seed'], plan, enabled=m['options']['items'])
        return m

    def delete(self, slot):
        self._stopped()
        if slot not in (1, 2, 3):
            raise ValueError('Ungültiger Speicherplatz.')
        from native_profiles import lease

        if lease(self):
            raise RuntimeError('Aktives Charakterprofil zuerst beenden.')
        path = self.base / 'IWBTB' / f'SaveFile{slot}.ini'
        if path.is_symlink():
            raise ValueError('Verknüpfter Spielstand wird nicht gelöscht.')
        if not path.exists():
            return False
        m = self.current(slot)
        if m and m['status'] == 'ready':
            self.validate(m)
        folder = self.root / 'deleted' / (str(time.time_ns()) + '-slot' + str(slot))
        folder.mkdir(parents=True)
        atomic(folder / path.name, path.read_bytes())
        if m:
            write_json(folder / 'manifest.json', m)
        if m and (self.root / m['run_id'] / 'profile.ini').exists():
            atomic(
                folder / 'profile.ini',
                (self.root / m['run_id'] / 'profile.ini').read_bytes(),
            )
        write_json(
            self.root / 'delete-pending.json',
            dict(
                slot=slot,
                run_id=m['run_id'] if m else None,
                hash=digest(path.read_bytes()),
                backup=str(folder.relative_to(self.root)),
            ),
        )
        self.recover_delete()
        return True

    def recover_delete(self):
        self._stopped()
        pending = self.root / 'delete-pending.json'
        j = json.loads(pending.read_text(encoding='utf-8'))
        slot = j['slot']
        if slot not in (1, 2, 3):
            raise ValueError('Ungültiger Löschauftrag.')
        registry = self.registry()
        current = registry.get(str(slot))
        if current not in (j['run_id'], None):
            raise ValueError('Speicherplatz wurde seit Löschauftrag verändert.')
        folder = (self.root / j['backup']).resolve()
        if not folder.is_relative_to((self.root / 'deleted').resolve()):
            raise ValueError('Ungültige Löschsicherung.')
        path = self.base / 'IWBTB' / f'SaveFile{slot}.ini'
        if digest((folder / path.name).read_bytes()) != j['hash']:
            raise ValueError('Löschsicherung beschädigt.')
        if path.exists():
            if path.is_symlink() or digest(path.read_bytes()) != j['hash']:
                raise ValueError('Spielstand wurde seit Löschauftrag verändert.')
            path.unlink()
        if j['run_id']:
            m = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
            if m['run_id'] != j['run_id'] or m['slot'] != slot:
                raise ValueError('Falsche Löschsicherung.')
            m['status'] = 'deleted'
            self.save_manifest(m)
        registry.pop(str(slot), None)
        write_json(self.root / 'slots.json', registry)
        pending.unlink()

    def restore(self, slot=1):
        self._stopped()
        from native_profiles import lease, finish

        if lease(self):
            finish(self)
        m = self.current(slot)
        if not m or m['status'] == 'restored':
            return False
        if m['status'] not in ('preparing', 'restoring'):
            self.validate(m)
        name = f'SaveFile{slot}.ini'
        path = self.base / 'IWBTB' / name
        folder = self.root / m['run_id']
        backup = (
            (folder / 'before' / name).read_bytes()
            if m['backup_hash'] is not None
            else None
        )
        if backup is not None and digest(backup) != m['backup_hash']:
            raise ValueError('Sicherung beschädigt; nichts wurde zurückgespielt.')
        archive = folder / 'last-save'
        archive.mkdir(exist_ok=True)
        if m['status'] != 'restoring':
            if path.exists():
                atomic(archive / name, path.read_bytes())
            m['status'] = 'restoring'
            self.save_manifest(m)
        if backup is not None:
            atomic(path, backup)
        elif path.exists():
            path.unlink()
        m['status'] = 'restored'
        self.save_manifest(m)
        return True


def real_store():
    from lab import BASE, EXPECTED
    from PY.file_utils import smart_read
    from PY.rc4_utils import rc4_crypt
    import psutil
    from runtime_paths import verify_root

    verify_root()
    if digest((BASE / 'IWBTB/I Wanna Be The Boshy.exe').read_bytes()) != EXPECTED:
        raise RuntimeError('Unbekannte Spielversion.')

    def running():
        for p in psutil.process_iter():
            try:
                if owned_process(p, BASE):
                    return True
            except (psutil.Error, OSError):
                pass
        return False

    return SessionStore(
        BASE,
        read_save=lambda p: smart_read(str(p))[0],
        encode_save=lambda s: rc4_crypt(b'BLOB', s.encode('latin-1')),
        game_running=running,
    )


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['new', 'resume', 'restore', 'status'])
    p.add_argument('--seed', default='Boshy')
    p.add_argument('--slot', type=int, choices=[1, 2, 3], default=1)
    a = p.parse_args()
    store = real_store()
    with store.lock():
        if a.action == 'new':
            print(json.dumps(store.prepare(a.seed, a.slot)))
        elif a.action == 'resume':
            print(json.dumps(store.validate(store.current(a.slot))))
        elif a.action == 'restore':
            print(json.dumps({'restored': store.restore(a.slot)}))
        else:
            print(json.dumps(store.current(a.slot)))
