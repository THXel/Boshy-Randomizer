"""Publishing must reject unreviewed source and damaged release assets."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'current_publisher',
    Path(__file__).resolve().parents[2] / 'packaging/publish_release.py',
)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class ReleaseTests(unittest.TestCase):
    def run_case(self, *, draft=True, commit='reviewed', corrupt=False, branch=None):
        calls = []
        body = b'reviewed installer'
        digest = hashlib.sha256(body).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'packaging').mkdir()
            (root / 'notes.md').write_text('First release')
            cfg = dict(
                tag='v1.0.0',
                title='1.0.0',
                notes='notes.md',
                assets={'setup.exe': dict(sha256=digest, bytes=len(body))},
            )
            (root / 'packaging/release.json').write_text(json.dumps(cfg))

            def gh(*args):
                calls.append(args)
                if args[0] == 'api' and '/releases/tags/' in args[1]:
                    return json.dumps(
                        dict(
                            draft=draft,
                            assets=[dict(name='setup.exe', digest='sha256:' + digest)],
                        )
                    )
                if args[0] == 'api' and '/commits/' in args[1]:
                    return commit
                if args[:2] == ('release', 'download'):
                    path = Path(args[args.index('--dir') + 1]) / 'setup.exe'
                    path.write_bytes(b'damaged' if corrupt else body)
                    return ''
                if args[:2] == ('release', 'edit'):
                    return ''
                raise AssertionError(args)

            env = dict(
                GITHUB_REPOSITORY='THXel/Boshy-Randomizer',
                GITHUB_REF=branch or 'refs/heads/Boshy-Randomizer',
                GITHUB_SHA='reviewed',
            )
            with (
                patch.object(publisher, 'ROOT', root),
                patch.object(publisher, 'gh', gh),
                patch.dict(os.environ, env),
            ):
                if draft and commit == 'reviewed' and not corrupt and not branch:
                    publisher.main()
                    self.assertEqual(
                        sum(c[:2] == ('release', 'edit') for c in calls), 1
                    )
                else:
                    with self.assertRaises(SystemExit):
                        publisher.main()
                    self.assertFalse(any(c[:2] == ('release', 'edit') for c in calls))

    def test_reviewed_draft_publishes(self):
        self.run_case()

    def test_published_release_is_never_replaced(self):
        self.run_case(draft=False)

    def test_wrong_commit_is_rejected(self):
        self.run_case(commit='other')

    def test_damaged_asset_is_rejected(self):
        self.run_case(corrupt=True)

    def test_other_branch_is_rejected(self):
        self.run_case(branch='refs/heads/other')
