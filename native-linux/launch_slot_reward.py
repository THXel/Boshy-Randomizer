"""Launch the native four-source patch; the menu retains all three save slots."""
import json,os,subprocess,struct
from lab import BASE,RUNNER,EXPECTED
from runtime_paths import command,environment
from native_session import digest,write_json,atomic

def prepare_payload(store,manifest):
    store._stopped();store.validate(manifest)
    if digest((BASE/'IWBTB/I Wanna Be The Boshy.exe').read_bytes())!=EXPECTED:raise RuntimeError('Unsupported game version')
    from runtime_versions import Rules
    rules=Rules(store,manifest);asset_base=rules.base;run_blob=rules.module('mixed_rewards').run_blob
    payload=store.root/manifest['run_id']/'reward_hook.bin'
    from intro_guard import attach
    offset=json.loads((asset_base/'slot_reward_symbols.json').read_text(encoding='utf-8'))['context_offset']
    if 'extras' in manifest['options']:
        blob,offset=rules.module('extras_runtime').run_blob(asset_base,manifest)
        atomic(payload,attach(BASE,rules.icons(blob,offset),context_offset=offset,extras=True,asset_base=asset_base))
    else:atomic(payload,attach(BASE,rules.icons(run_blob(asset_base,manifest),offset),context_offset=offset,asset_base=asset_base))
    from soundpacks import prepare_music as prepare_pack_music
    if not prepare_pack_music(BASE,manifest):
        rules.module('music_randomizer').prepare(BASE,manifest)
        from music_playback import prepare as prepare_music_playback
        prepare_music_playback(BASE,manifest)
    rules.module('spider_randomizer').prepare(BASE,manifest)
    rules.module('sprite_scenery').prepare(BASE,manifest)
    rules.module('background_sets').prepare(BASE,manifest)
    from graphics_debug import reset
    reset(BASE)
    extra=manifest['options'].get('extras',{})
    hide_clouds=bool(extra.get('sprite_scenery') and extra.get('version',0)>=7 and extra.get('sprite_backgrounds'))
    atomic(BASE/'menu-runtime/clouds.bin',b'BRC1'+manifest['run_id'].encode('ascii')+struct.pack('<I',hide_clouds))
    return payload,offset

def launch(store,manifest):
    payload,offset=prepare_payload(store,manifest)
    logpath=store.root/manifest['run_id']/'launch.log'
    with logpath.open('w') as log:
        p=subprocess.Popen(command('slot_reward_launcher.exe',payload.relative_to(BASE)),cwd=BASE,env=environment(),stdout=log,stderr=log,start_new_session=True,**__import__('host_platform').child_options())
        p.wait(timeout=45)
    if p.returncode:raise RuntimeError('Native launcher failed: '+logpath.read_text(encoding='utf-8')[-800:])
    data=json.loads(next(l for l in logpath.read_text(encoding='utf-8').splitlines() if l.startswith('{')))
    data['context']=data['hook']+offset
    return data
