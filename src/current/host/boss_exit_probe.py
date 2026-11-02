"""Bounded live fixtures: original Kracko death, or Mario's original pipe timer."""

from pathlib import Path
import argparse, configparser, json, os, runpy, subprocess, time
from Xlib import X, display
from PIL import Image
from phase_state import State

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('boss', choices=['kracko', 'mario'])
parser.add_argument('--label', required=True)
parser.add_argument('--case', choices=['rebuilt-mario-links','rebuilt-kracko-links'])
parser.add_argument('--output-group', default='Fusion-BossExits-20261023')
parser.add_argument('--pipe-entry', action='store_true')
args = parser.parse_args()
case = args.case or 'rebuilt-' + args.boss + '-exit'
assert args.boss in case
assert '/' not in args.output_group and '..' not in args.output_group
lab = (
    Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests') / case
)
out = ROOT / 'outputs' / args.output_group / args.label
out.mkdir(exist_ok=False)
rows = [
    r.split(None, 4)
    for r in subprocess.check_output(['wmctrl', '-lp'], text=True).splitlines()
    if r.endswith(' I Wanna Be The Boshy')
]
assert len(rows) == 1
wid = rows[0][0]
assert Path(os.readlink('/proc/' + rows[0][2] + '/cwd')) == lab
D = display.Display()
w = D.create_resource_object('window', int(wid, 16))
g = w.get_geometry()
subprocess.run(['wmctrl', '-ia', wid])
subprocess.run(['xdotool', 'mousemove', '5', '5'])


def key(k):
    subprocess.run(['wmctrl', '-ia', wid])
    time.sleep(0.15)
    subprocess.run(['xdotool', 'keydown', k])
    time.sleep(0.3)
    subprocess.run(['xdotool', 'keyup', k])


def shot(label):
    i = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes('RGB', (g.width, g.height), i.data, 'raw', 'BGRX').save(
        out / (label + '.png')
    )


rc4 = runpy.run_path(str(ROOT / 'work/Boshy-Randomizer/src/shared/PY/rc4_utils.py'))[
    'rc4_crypt'
]


def save():
    return rc4(b'BLOB', (lab / 'SaveFile1.ini').read_bytes()).decode('latin1')


def parsed():
    c = configparser.ConfigParser()
    c.read_string(save())
    return c


s = State(case)
report = {
    'boss': args.boss,
    'writes': s.writes,
    'pid': rows[0][2],
    'save_before': save(),
}


def obj(name):
    return next(o for o in s.objects() if o['name'] == name)


def unprotect():
    for change in list(s.writes):
        if (
            change['reason'] == 'temporary zero-count Die fastloop for visual fixture'
            and s.b.u32(change['address']) == 0
        ):
            s.cas(
                change['address'], 0, 1, 'restore death calls before intentional death'
            )


def kill_kracko():
    s.position(obj('Player'), 3400, 300)
    boss = obj('Active 83')
    s.set_value(boss, 1, 0)
    for n in range(40):
        time.sleep(0.25)
        if not any(o['name'] == 'Active 83' for o in s.objects()):
            break
    else:
        raise AssertionError('Original Kracko death did not finish')
    time.sleep(0.5)
    shot('kracko-defeated')


try:
    s.protect()
    key('r')
    time.sleep(0.7)
    s.protect()
    report['initial_objects'] = [
        dict(o, values=s.values(o, 7))
        for o in s.objects()
        if o['name']
        in ('Player', 'Active 83', 'Active 27', 'Classic Mario', 'Classic Mario 3')
    ]
    if args.boss == 'kracko':
        s.position(obj('Player'), 3920, 200)
        time.sleep(0.5)
        shot('no-premature-exit')
        report['before_win_stays_in_origin'] = any(
            o['name'] == 'Active 83' for o in s.objects()
        )
        assert report['before_win_stays_in_origin']
        kill_kracko()
        report['victory_before_exit'] = save()
        unprotect()
        key('q')
        time.sleep(0.8)
        report['dead_before_exit'] = not any(o['name'] == 'Player' for o in s.objects())
        shot('dead-before-exit')
        assert report['dead_before_exit']
        key('r')
        time.sleep(0.7)
        s.protect()
        s.position(obj('Player'), 3920, 200)
        time.sleep(0.5)
        report['restart_does_not_unlock'] = any(
            o['name'] == 'Active 83' for o in s.objects()
        )
        assert report['restart_does_not_unlock']
        shot('restart-gate')
        kill_kracko()
        s.position(obj('Player'), 3920, 200)
    else:
        # The original pipe's completion is A=50, after its original entry animation.
        # This bypasses the fight ONLY as a fixture; victory actions remain engine-owned.
        pipe = obj('Active 27')
        report['pipe_before'] = s.values(pipe, 2)
        report['before_pipe_frame'] = parsed().getint('Positions', 'frame')
        if args.pipe_entry:
            report['pipe_entry_fixture'] = (
                'Pipe and Player placed at (600,400); original collision starts entry timer'
            )
            s.position(pipe, 600, 400)
            s.position(obj('Player'), 600, 400)
            report['pipe_samples'] = []
            for tick in range(20):
                time.sleep(0.1)
                pipes = [o for o in s.objects() if o['name'] == 'Active 27']
                if not pipes:
                    break
                report['pipe_samples'].append(s.values(pipes[0], 1)[0])
            shot('pipe-entry')
        else:
            s.set_value(pipe, 0, 50)
    time.sleep(1)
    shot('arrival')
    report['save_arrival'] = save()
    report['arrival_objects'] = [o['name'] for o in s.objects()]
    key('q')
    time.sleep(0.8)
    shot('death')
    report['dead_at_target'] = not any(o['name'] == 'Player' for o in s.objects())
    key('r')
    time.sleep(0.8)
    shot('restart')
    report['save_restart'] = save()
    report['player_after_restart'] = any(o['name'] == 'Player' for o in s.objects())
    report['same_process'] = s.b.read(s.b.ready['base'], 2) == b'MZ'
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ('writes', 'initial_objects', 'arrival_objects')
            }
        ),
        flush=True,
    )
finally:
    (out / 'result.json').write_text(json.dumps(report, indent=2))
    s.close()
