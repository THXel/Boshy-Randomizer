"""Immutable per-run game rules; presentation and process control may be updated.

Existing manifest bindings stay intact. A separately bound reference selects a
content-addressed snapshot. No fallback to new rules if a snapshot is damaged.
"""

import builtins
import hashlib
import json
import shutil
import types
import uuid
import os
from pathlib import Path
from native_session import digest, write_json

MODULES = (
    'seed_codec',
    'seed_share',
    'run_settings',
    'run_extras',
    'shot_cycle',
    'death_character',
    'character_cycle',
    'mixed_rewards',
    'extras_runtime',
    'native_targets',
    'beta_catalogue',
    'native_level_route',
    'native_triggers',
    'minibosses',
    'beta_bosses',
    'native_progress',
    'seed_audit',
    'reward_journal',
)
SUPPORT = ('INI/positions.json', 'slot_reward_symbols.json', 'native_intro_guard.dll')


def reference(store, m):
    return store.root / m['run_id'] / 'rules.json'


def pin(store, m):
    ref = reference(store, m)
    if ref.exists():
        return Rules(store, m)
    # Caller must validate the legacy binding before pinning; never bless changed assets.
    for name, want in m['assets'].items():
        if digest((store.base / name).read_bytes()) != want:
            raise ValueError('Alter Lauf benötigt seine ursprüngliche Datei: ' + name)
    names = sorted(set(m['assets']) | set(SUPPORT) | {n + '.py' for n in MODULES})
    hashes = {n: digest((store.base / n).read_bytes()) for n in names}
    identity = digest(json.dumps(hashes, sort_keys=True).encode())
    parent = store.base / 'rule-versions'
    parent.mkdir(exist_ok=True)
    target = parent / identity[:20]
    if not target.exists():
        temp = parent / ('.building-' + uuid.uuid4().hex)
        temp.mkdir()
        try:
            for name, want in hashes.items():
                data = (store.base / name).read_bytes()
                if digest(data) != want:
                    raise ValueError('Installation änderte sich während der Sicherung.')
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            # Short relative resource names fit the game's fixed-size icon fields.
            icons = {
                n: f'icons/{i:03d}' + Path(n).suffix
                for i, n in enumerate(names)
                if n.startswith(('Custom/trophies/', 'native-icons/'))
            }
            for source, dest in icons.items():
                p = temp / dest
                p.parent.mkdir(exist_ok=True)
                shutil.copyfile(temp / source, p)
            write_json(
                temp / 'bundle.json',
                dict(version=1, identity=identity, hashes=hashes, icons=icons),
            )
            if os.name == 'nt':
                import _winapi

                _winapi.CreateJunction(str(store.base / 'IWBTB'), str(temp / 'IWBTB'))
            else:
                (temp / 'IWBTB').symlink_to(
                    store.base / 'IWBTB', target_is_directory=True
                )
            os.rename(temp, target)
        finally:
            if temp.exists():
                shutil.rmtree(temp)
    write_json(
        ref,
        dict(
            version=1, run_id=m['run_id'], binding=m['session_binding'], bundle=identity
        ),
    )
    return Rules(store, m)


class View:
    def __init__(self, store, base):
        self._store = store
        self.base = base
        self.root = store.root

    def __getattr__(self, name):
        return getattr(self._store, name)


class Rules:
    def __init__(self, store, m):
        self.store = store
        self.m = m
        self.modules = {}
        p = reference(store, m)
        self.frozen = p.exists()
        if not self.frozen:
            self.base = store.base
            self.meta = None
            self.view = store
            return
        r = json.loads(p.read_text(encoding='utf-8'))
        identity = r.get('bundle', '')
        if (
            r.get('version') != 1
            or r.get('run_id') != m['run_id']
            or r.get('binding') != m['session_binding']
            or len(identity) != 64
            or any(c not in '0123456789abcdef' for c in identity)
        ):
            raise ValueError('Ungültige Laufversion.')
        self.base = store.base / 'rule-versions' / identity[:20]
        if self.base.is_symlink():
            raise ValueError('Ungültige Versionsablage.')
        self.meta = json.loads((self.base / 'bundle.json').read_text(encoding='utf-8'))
        if (
            self.meta['identity'] != identity
            or digest(json.dumps(self.meta['hashes'], sort_keys=True).encode())
            != identity
        ):
            raise ValueError('Laufversion beschädigt.')
        expected = set(m['assets']) | set(SUPPORT) | {n + '.py' for n in MODULES}
        if set(self.meta['hashes']) != expected:
            raise ValueError('Unvollständige Laufversion.')
        for name, want in self.meta['hashes'].items():
            path = self.base / name
            if path.is_symlink() or digest(path.read_bytes()) != want:
                raise ValueError('Gesicherte Laufregel beschädigt: ' + name)
        if (self.base / 'IWBTB').resolve() != (store.base / 'IWBTB').resolve():
            raise ValueError('Falscher Spielordner für Laufversion.')
        self.view = View(store, self.base)

    def module(self, name):
        if not self.frozen or (
            name not in MODULES
            and not (
                name
                in (
                    'music_randomizer',
                    'spider_randomizer',
                    'sprite_scenery',
                    'sprite_chaos',
                    'background_sets',
                )
                and name + '.py' in self.meta['hashes']
            )
        ):
            return __import__(name)
        if name in self.modules:
            return self.modules[name]
        module = types.ModuleType(name)
        module.__file__ = str(self.base / (name + '.py'))
        module.__package__ = ''
        module.__dict__['__builtins__'] = {**vars(builtins), '__import__': self._import}
        self.modules[name] = module
        try:
            exec(
                compile(Path(module.__file__).read_bytes(), module.__file__, 'exec'),
                module.__dict__,
            )
            correct_known_exits(name, module)
            apply_room_exit_timing(name, module)
            repair_shot_transport(name, module)
            repair_kappa_exit(name, module)
            repair_kracko_animation(name, module)
            repair_kracko_exit(name, module)
            repair_tower_exit(name, module)
            repair_stage_exits(name, module)
            repair_spider_visuals(name, module)
            repair_parallax_visuals(name, module)
        except Exception:
            self.modules.pop(name, None)
            raise
        return module

    def _import(self, name, globals=None, locals=None, fromlist=(), level=0):
        if not level and (
            name in MODULES
            or self.frozen
            and name
            in (
                'music_randomizer',
                'spider_randomizer',
                'sprite_scenery',
                'sprite_chaos',
                'background_sets',
            )
            and name + '.py' in self.meta['hashes']
        ):
            return self.module(name)
        return builtins.__import__(name, globals, locals, fromlist, level)

    def icons(self, blob, offset):
        if not self.frozen:
            return blob
        raw = bytearray(blob)
        plan = json.loads(
            (self.base / 'slot_reward_plan.json').read_text(encoding='utf-8')
        )
        mod = self.module('mixed_rewards')
        start = offset + 124 + mod.MAX_SOURCES * mod.LOCATION_SIZE
        for i, loc in enumerate(plan['locations']):
            name = self.m['rewards'][loc['key']]['name']
            source = (
                ('native-icons/' + name + '.bmp')
                if name in ('Simon Belmont', 'Spike')
                else ('Custom/trophies/' + name + '.png')
            )
            alias = self.meta['icons'][source]
            p = self.base / alias
            if p.is_symlink() or digest(p.read_bytes()) != self.meta['hashes'][source]:
                raise ValueError('Gesicherte Belohnungsgrafik beschädigt.')
            relative = '..\\' + str(p.relative_to(self.store.base)).replace('/', '\\')
            encoded = relative.encode()
            if len(encoded) >= 64:
                raise ValueError('Grafikpfad zu lang.')
            at = start + i * 96 + 32
            raw[at : at + 64] = encoded.ljust(64, b'\0')
        return bytes(raw)


def reconcile(store, m, **kwargs):
    rules = Rules(store, m)
    return rules.module('reward_journal').reconcile(rules.view, m, **kwargs)


def recover_all(store):
    store._stopped()
    from native_profiles import lease

    if lease(store):
        raise RuntimeError('Aktives Profil muss zuerst wiederhergestellt werden.')
    for slot in (1, 2, 3):
        m = store.current(slot)
        if m and m['status'] == 'ready':
            reconcile(store, m)


def correct_known_exits(name, module):
    """Correct a confirmed engine exit without rewriting a saved rules bundle.

    Old Sonic's native victory action advances frame 60 to 61. Older bundles
    incorrectly copied normal Sonic's exit (15). Keep every other frozen rule,
    seed, route and reward intact; persisted bundle hashes still validate first.
    """
    if name != 'native_triggers' or getattr(module, 'BOSS_EXITS', {}).get(60) not in (
        (15,),
        (61,),
    ):
        return
    module.BOSS_EXITS = {**module.BOSS_EXITS, 60: (61,)}
    if getattr(module, 'OLD_SONIC_EXIT_VERSION', 0) >= 1:
        return
    from native_triggers import old_sonic_exit

    original = module.CompletionGate.observe

    def observe(gate, spot, point, frame, ach, disk, *args, **kwargs):
        confirmed = old_sonic_exit(gate, spot, point, frame, ach, disk)
        result = original(gate, spot, point, frame, ach, disk, *args, **kwargs)
        if confirmed:
            return 'Boss-Ausgang'
        return None if spot == 'boss23.ini' and point.get('frame') == 60 else result

    module.CompletionGate.observe = observe
    module.OLD_SONIC_EXIT_VERSION = 1


def apply_room_exit_timing(name, module):
    """Remove only the delay from validated room exits in known saved rules.

    Keep the saved destination table and all route/seed choices. The original
    gate must first establish the origin, exact exit and death/tick checks.
    Miniboss and Old Sonic animation gates are separate.
    """
    if (
        name != 'native_triggers'
        or getattr(module, 'RULE_VERSION', None) != 3
        or getattr(module, 'ROOM_EXIT_TIMING_VERSION', 0) >= 1
    ):
        return
    original = module.CompletionGate.observe

    def observe(
        gate,
        spot,
        point,
        frame,
        ach,
        disk,
        stats,
        tick=None,
        restart_pressed=False,
        position=None,
    ):
        if restart_pressed:
            gate.reset()
        result = original(
            gate,
            spot,
            point,
            frame,
            ach,
            disk,
            stats,
            tick,
            restart_pressed,
            position=position,
        )
        if result is not None or (spot == 'boss23.ini' and point.get('frame') == 60):
            return result
        if (
            gate.seen_origin
            and gate.candidate in ('Level-Ausgang', 'Boss-Ausgang')
            and gate.candidate_frame == frame
            and frame in module.exits_for(spot, point)
        ):
            return gate.candidate
        return None

    module.CompletionGate.observe = observe
    module.ROOM_EXIT_TIMING_VERSION = 1


def repair_shot_transport(name, module):
    """Repair delivery for saved runs without changing their seeded style choices.

    The old character command deliberately preserves trailing control bytes.
    Keep the frozen advance/selection/interval algorithms; only replace the
    observation method's transport with the scoped, acknowledged shot command.
    """
    if name != 'shot_cycle' or getattr(module, 'TRANSPORT_VERSION', 0) >= 1:
        return
    import shot_cycle
    import types

    original = shot_cycle.ShotCycle.observe
    # Use the frozen module globals (not current seed-selection functions).
    module.ShotCycle.observe = types.FunctionType(
        original.__code__,
        module.__dict__,
        original.__name__,
        original.__defaults__,
        original.__closure__,
    )
    module.TRANSPORT_VERSION = 1


def repair_kappa_exit(name, module):
    """Apply the confirmed reward-room exit to saved Kappa stages as well.

    Preserve the run's route and rewards; never finish Kappa on HP/death alone.
    Only the exact Kappa stage adopts its original Teleport Room exit.
    """
    if getattr(module, 'KAPPA_EXIT_VERSION', 0) >= 1:
        return
    if name == 'native_triggers':
        original = module.exits_for

        def exits_for(spot, point):
            if (
                spot == 'boss_kappa'
                and point.get('frame') == 37
                and point.get('segment') == 'kappa'
            ):
                return (29,)
            return original(spot, point)

        module.exits_for = exits_for
    elif name == 'minibosses':
        original = module.Gate.observe

        def observe(gate, spot, index, point, sample, deaths, now=None):
            if (
                spot == 'boss_kappa'
                and point.get('frame') == 37
                and point.get('segment') == 'kappa'
            ):
                gate.reset()
                return None
            return original(gate, spot, index, point, sample, deaths, now)

        module.Gate.observe = observe
    else:
        return
    module.KAPPA_EXIT_VERSION = 1


def repair_tower_exit(name, module):
    """Use the verified top-door edge in saved Tower runs without changing routes."""
    if (
        name != 'native_triggers'
        or getattr(module, 'RULE_VERSION', 0) != 3
        or getattr(module, 'TOWER_EXIT_VERSION', 0) >= 1
    ):
        return
    import native_triggers

    original = module.CompletionGate.observe
    # Only Tower adopts the corrected observation; retain the frozen exit table,
    # reset/death guards and every other stage's existing behaviour.
    tower = types.FunctionType(
        native_triggers.CompletionGate.observe.__code__,
        module.__dict__,
        argdefs=native_triggers.CompletionGate.observe.__defaults__,
    )

    def observe(gate, spot, point, *args, **kwargs):
        return (tower if point.get('frame') == 51 else original)(
            gate, spot, point, *args, **kwargs
        )

    module.CompletionGate.observe = observe
    module.TOWER_EXIT_VERSION = 1


def repair_spider_visuals(name, module):
    """Supply rotated sprites for older saved runs without changing their options."""
    if name != 'spider_randomizer' or getattr(module, 'SPRITE_VERSION', 0) >= 2:
        return
    from spider_randomizer import prepare_orientations

    original = module.prepare

    def prepare(base, manifest):
        result = original(base, manifest)
        if manifest['options'].get('extras', {}).get('spider', False):
            prepare_orientations(base)
        return result

    module.prepare = prepare
    module.SPRITE_VERSION = 2


def repair_kracko_animation(name, module):
    """Keep Kracko's death animation visible in saved runs without changing routes."""
    if name != 'minibosses' or getattr(module, 'KRACKO_ANIMATION_VERSION', 0) >= 1:
        return
    original = module.Gate.observe

    def observe(gate, spot, index, point, sample, deaths, now=None):
        now = module.time.monotonic() if now is None else now
        result = original(gate, spot, index, point, sample, deaths, now)
        if (
            result is not None
            and point.get('segment') == 'kracko'
            and gate.since is not None
            and now - gate.since < 4.0
        ):
            return None
        return result

    module.Gate.observe = observe
    module.KRACKO_ANIMATION_VERSION = 1


def repair_kracko_exit(name, module):
    """Retain Kracko's verified defeat across his right exit in saved runs."""
    if name != 'minibosses' or getattr(module, 'KRACKO_EXIT_VERSION', 0) >= 1:
        return
    import minibosses

    original = module.Gate.observe
    sample_original = module.Reader.sample
    module.KRACKO_EXIT = minibosses.KRACKO_EXIT
    # Only Kracko uses the corrected gate; all other frozen stages keep their
    # existing rules. The reader still validates the frozen original death event.
    corrected = types.FunctionType(
        minibosses.Gate.observe.__code__,
        module.__dict__,
        argdefs=minibosses.Gate.observe.__defaults__,
    )

    def observe(gate, spot, index, point, sample, deaths, now=None):
        return (corrected if point.get('segment') == 'kracko' else original)(
            gate, spot, index, point, sample, deaths, now
        )

    def sample(reader, bridge, snap):
        result = sample_original(reader, bridge, snap)
        if result is not None and snap['scene'] == 4:
            result = {**result, 'generation': [snap['run'], snap['object_list']]}
        return result

    module.Gate.observe = observe
    module.Reader.sample = sample
    module.KRACKO_EXIT_VERSION = 1


def repair_parallax_visuals(name, module):
    """Repair frozen cloud imports, retaining their seed choices and checked assets."""
    if name != 'background_sets' or getattr(module, 'PARALLAX_MASK_VERSION', 0) >= 1:
        return
    from background_sets import repair_parallax_assets, MAGIC

    original = module.prepare

    def prepare(base, manifest):
        result = original(base, manifest)
        if result:
            try:
                repair_parallax_assets(base)
            except Exception:
                import logging
                from native_session import atomic

                atomic(
                    Path(base) / 'menu-runtime/background-sets.bin', MAGIC + bytes(76)
                )
                logging.exception('Parallax mask unavailable; keeping existing scenery')
                return False
        return result

    module.prepare = prepare
    module.PARALLAX_MASK_VERSION = 1


def repair_stage_exits(name, module):
    """Correct only the three confirmed split-stage exits in existing seeds."""
    if (
        name != 'native_triggers'
        or getattr(module, 'RULE_VERSION', 0) != 3
        or getattr(module, 'STAGE_EXIT_VERSION', 0) >= 1
    ):
        return
    from native_triggers import corrected_stage_exits

    original = module.exits_for

    def exits_for(spot, point):
        corrected = corrected_stage_exits(spot, point)
        return original(spot, point) if corrected is None else corrected

    module.exits_for = exits_for
    module.STAGE_EXIT_VERSION = 1
