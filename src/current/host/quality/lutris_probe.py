"""Check the generated entry with installed Lutris APIs in isolated XDG folders.

Does not launch its GUI or claim a fresh operating-system installation.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace


def run(output, executable, prefix):
    output, executable, prefix = map(lambda p: Path(p).resolve(), (output, executable, prefix))
    assert Path(os.environ['XDG_DATA_HOME']).resolve() == output / 'data'
    assert Path(os.environ['XDG_CONFIG_HOME']).resolve() == output / 'config'
    import sys, shutil
    sys.path.insert(0, str(Path(shutil.which("lutris")).resolve().parent))
    from lutris.startup import init_dirs
    init_dirs()
    from lutris.database.schema import syncdb
    from lutris.installer.installer import LutrisInstaller
    from lutris.database.games import get_game_by_field
    from lutris.config import LutrisConfig
    from distribution.lutris import installer
    syncdb()
    description = installer(executable, prefix)
    context = SimpleNamespace(target_path=str(output / 'game'), game_files={}, _substitute=lambda v: v)
    candidate = LutrisInstaller(description, context, None, None)
    assert not candidate.get_errors()
    game_id = candidate.save()
    assert candidate.save() == game_id
    row = get_game_by_field(game_id, 'id')
    cfg = LutrisConfig(runner_slug='wine', game_config_id=row['configpath']).game_level
    assert cfg['game']['exe'] == str(executable)
    assert cfg['game']['prefix'] == str(prefix)
    for key in ('dxvk', 'vkd3d', 'esync', 'fsync'):
        assert cfg['wine'][key] is False
    assert cfg['wine']['MouseWarpOverride'] == 'enable'
    from distribution.linux.launcher import registered_game
    assert registered_game() == game_id
    report = {'passed': True, 'lutris_api_registered_game': game_id,
              'same_entry_updated': True, 'reviewed_settings_retained': True,
              'scope': 'real Lutris installer/config/database APIs in isolated XDG directories; GUI first-run flow not tested'}
    (output / 'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    import sys
    run(*sys.argv[1:])
