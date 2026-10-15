"""Launch the native four-source patch; the menu retains all three save slots."""
import json,os,subprocess
from lab import BASE,RUNNER,EXPECTED
from runtime_paths import command,environment
from native_session import digest,write_json,atomic

def launch(store,manifest):
    store._stopped();store.validate(manifest)
    if digest((BASE/'IWBTB/I Wanna Be The Boshy.exe').read_bytes())!=EXPECTED:raise RuntimeError('Unsupported game version')
    from runtime_versions import Rules
    rules=Rules(store,manifest);asset_base=rules.base;run_blob=rules.module('mixed_rewards').run_blob
    payload=store.root/manifest['run_id']/'reward_hook.bin'
    from intro_guard import attach
    offset=json.loads((asset_base/'slot_reward_symbols.json').read_text())['context_offset']
    if 'extras' in manifest['options']:
        blob,offset=rules.module('extras_runtime').run_blob(asset_base,manifest)
        atomic(payload,attach(BASE,rules.icons(blob,offset),context_offset=offset,extras=True,asset_base=asset_base))
    else:atomic(payload,attach(BASE,rules.icons(run_blob(asset_base,manifest),offset),context_offset=offset,asset_base=asset_base))
    rules.module('music_randomizer').prepare(BASE,manifest)
    rules.module('spider_randomizer').prepare(BASE,manifest)
    logpath=store.root/manifest['run_id']/'launch.log'
    with logpath.open('w') as log:
        p=subprocess.Popen(command('slot_reward_launcher.exe',payload.relative_to(BASE)),cwd=BASE,env=environment(),stdout=log,stderr=log,start_new_session=True)
        p.wait(timeout=45)
    if p.returncode:raise RuntimeError('Native launcher failed: '+logpath.read_text()[-800:])
    data=json.loads(next(l for l in logpath.read_text().splitlines() if l.startswith('{')))
    data['context']=data['hook']+offset
    return data
