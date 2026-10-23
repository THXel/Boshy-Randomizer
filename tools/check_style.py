"""Check the maintained Python and hand-written C source without touching builds."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# Generated data tables remain compact and are validated against their catalogues.
GENERATED_HEADERS = {'extras_plan.h', 'spider_players.h'}


def native_sources():
    return sorted(
        path
        for path in (ROOT / 'src/native').rglob('*')
        if path.suffix in {'.c', '.h'}
        and not path.name.endswith('_catalogue.h')
        and path.name not in GENERATED_HEADERS
    ) + sorted((ROOT / 'tests/runtime').glob('*.c'))


def main():
    subprocess.run(
        ['black', '--check', 'src', 'tests', 'tools', 'packaging'],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ['clang-format', '--dry-run', '--Werror', *map(str, native_sources())],
        cwd=ROOT,
        check=True,
    )


if __name__ == '__main__':
    main()
