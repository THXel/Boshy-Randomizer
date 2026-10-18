"""Per-run onlineLicense snapshots; switch while stopped or in a verified native menu transaction."""
import json,time,uuid
from native_session import atomic,write_json,digest,section
from PY.ini_utils import parse_ini

def profile_path(store,m):return store.root/m['run_id']/'profile.ini'
def make_profile(store,m):
 original=store.read_save(store.base/'IWBTB/onlineLicense.ini');d=parse_ini(original)
 from run_settings import character
 chosen=character(store.base,m['seed'],m['options'])
 fields=dict(d.get('license',{}));fields.update(Character=str(chosen['id']),CharacterName=chosen['name'])
 # The offline F3 picker only requires a nonempty local profile name.
 # Fresh imports have no online account; preserve existing names verbatim.
 name_key=next((k for k in fields if k.casefold()=='name'),'Name')
 if not fields.get(name_key,'').strip():fields[name_key]='Player'
 text=section(original,'License',fields)
 # A starting appearance is not a collected unlock (same as default Dark Boshy).
 text=section(text,'Unlockables',{k:'0' for k in json.loads((store.base/'INI/characters.json').read_text(encoding='utf-8'))})
 # Achievements in a global profile must never pre-complete a new run.
 text=section(text,'Achievements',{})
 text=section(text,'RandoProfile',dict(RunId=m['run_id'],Binding=m['session_binding'],Slot=m['slot']))
 atomic(profile_path(store,m),store.encode_save(text))
def lease(store):
 p=store.root/'profile-lease.json'
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

def validate_profile(store,path):
 d=parse_ini(store.read_save(path))
 if 'license' not in d or 'unlockables' not in d:raise ValueError('Charakterprofil ist unvollständig.')
 return d

def activate(store,m):
 store._stopped()
 from runtime_versions import reconcile
 reconcile(store,m);store.validate(m)
 if lease(store):finish(store)
 profile=profile_path(store,m);validate_profile(store,profile)
 path=store.base/'IWBTB/onlineLicense.ini';old=path.read_bytes();new=profile.read_bytes()
 backups=store.root/'profile-backups';backups.mkdir(exist_ok=True);name=uuid.uuid4().hex+'.ini';atomic(backups/name,old)
 journal=dict(run_id=m['run_id'],slot=m['slot'],backup=name,backup_hash=digest(old),profile_hash=digest(new),phase='preparing')
 write_json(store.root/'profile-lease.json',journal);atomic(path,new)
 journal['phase']='active';write_json(store.root/'profile-lease.json',journal)
def snapshot(store,m):
 journal=lease(store)
 if not journal or journal['phase']!='active' or journal['run_id']!=m['run_id']:return
 source=store.base/'IWBTB/onlineLicense.ini';validate_profile(store,source);data=source.read_bytes();dest=profile_path(store,m)
 if dest.read_bytes()!=data:atomic(dest,data)
def finish(store):
 store._stopped();journal=lease(store)
 if not journal:return False
 if journal['slot'] not in (1,2,3):raise ValueError('Ungültige Profilzuordnung.')
 m=store.current(journal['slot'])
 if not m or m['run_id']!=journal['run_id']:raise ValueError('Charakterprofil gehört zu einem anderen Lauf.')
 name=journal['backup']
 if '/' in name or '\\' in name:raise ValueError('Ungültige Profilsicherung.')
 backup=(store.root/'profile-backups'/name).read_bytes()
 if digest(backup)!=journal['backup_hash']:raise ValueError('Profilsicherung beschädigt.')
 path=store.base/'IWBTB/onlineLicense.ini';current=path.read_bytes()
 if journal['phase']=='active':
  from runtime_versions import reconcile
  reconcile(store,m,active_profile=True);snapshot(store,m)
 elif journal['phase']=='preparing' and digest(current) not in (journal['backup_hash'],journal['profile_hash']):raise ValueError('Unklarer Profilstand; Sicherungen bleiben erhalten.')
 # Recovery after a crash during restoration must not capture the baseline as run progress.
 journal['phase']='restoring';write_json(store.root/'profile-lease.json',journal)
 atomic(path,backup);(store.root/'profile-lease.json').unlink();return True
