'use strict';
const texts = {
 en: {overview:'Overview',items:'Items',characters:'Characters',bosses:'Bosses',route_stages:'Route',goals:'Targets',copy:'Copy seed',copied:'Copied!',copyhint:'Select and copy this seed:',seed:'Seed',deaths:'Deaths',slot:'Save',menu:'Choose a save',waiting:'Waiting for Boshy Randomizer…',empty:'Nothing here yet',running:'Playing',loading:'Loading',finished:'Finished',offline:'Game closed or connection lost',found:'UNLOCKED',defeated:'BOSS DEFEATED',done:'Done',open:'Pending',current:'Current stage',target:'Target',checks:'Chests',stages:'Stages completed',normal:'Original progression · modded run',footer:'Original by Solgryn · Randomizer by THXel',randomizer:'Randomizer',target_mode:'Target Select',normal_mode:'Normal · Randomizer',boss_rush:'Boss Rush',level_rush:'Level Rush',finale:'Solgryn unlocked'},
 de: {overview:'Übersicht',items:'Items',characters:'Figuren',bosses:'Bosse',route_stages:'Route',goals:'Ziele',copy:'Seed kopieren',copied:'Kopiert!',copyhint:'Diesen Seed markieren und kopieren:',seed:'Seed',deaths:'Tode',slot:'Save',menu:'Spielstand wählen',waiting:'Warte auf Boshy Randomizer…',empty:'Noch keine Einträge',running:'Im Spiel',loading:'Wird geladen',finished:'Abgeschlossen',offline:'Spiel geschlossen oder Verbindung unterbrochen',found:'FREIGESCHALTET',defeated:'BOSS BESIEGT',done:'Erledigt',open:'Offen',current:'Aktueller Abschnitt',target:'Ziel',checks:'Truhen',stages:'Abschnitte abgeschlossen',normal:'Originaler Spielverlauf · modifizierter Run',footer:'Original von Solgryn · Randomizer von THXel',randomizer:'Randomizer',target_mode:'Target Select',normal_mode:'Normal · Randomizer',boss_rush:'Boss Rush',level_rush:'Level Rush',finale:'Solgryn freigegeben'},
 es: {overview:'Resumen',items:'Objetos',characters:'Personajes',bosses:'Jefes',route_stages:'Ruta',goals:'Objetivos',copy:'Copiar semilla',copied:'¡Copiada!',copyhint:'Selecciona y copia esta semilla:',seed:'Semilla',deaths:'Muertes',slot:'Partida',menu:'Elige una partida',waiting:'Esperando Boshy Randomizer…',empty:'Todavía no hay entradas',running:'Jugando',loading:'Cargando',finished:'Completado',offline:'Juego cerrado o conexión perdida',found:'DESBLOQUEADO',defeated:'JEFE DERROTADO',done:'Completado',open:'Pendiente',current:'Etapa actual',target:'Objetivo',checks:'Cofres',stages:'Etapas completadas',normal:'Recorrido original · partida modificada',footer:'Original de Solgryn · Randomizer de THXel',randomizer:'Randomizer',target_mode:'Selección de objetivos',normal_mode:'Normal · Randomizer',boss_rush:'Solo jefes',level_rush:'Solo niveles',finale:'Solgryn desbloqueado'},
 ru: {overview:'Обзор',items:'Предметы',characters:'Персонажи',bosses:'Боссы',route_stages:'Маршрут',goals:'Цели',copy:'Копировать сид',copied:'Скопировано!',copyhint:'Выделите и скопируйте сид:',seed:'Сид',deaths:'Смерти',slot:'Сохранение',menu:'Выберите сохранение',waiting:'Ожидание Boshy Randomizer…',empty:'Пока нет записей',running:'В игре',loading:'Загрузка',finished:'Завершено',offline:'Игра закрыта или связь потеряна',found:'ОТКРЫТО',defeated:'БОСС ПОБЕЖДЁН',done:'Готово',open:'Осталось',current:'Текущий этап',target:'Цель',checks:'Сундуки',stages:'Этапов завершено',normal:'Оригинальный маршрут · модифицированная игра',footer:'Оригинал: Solgryn · Randomizer: THXel',randomizer:'Рандомайзер',target_mode:'Выбор целей',normal_mode:'Обычный · Randomizer',boss_rush:'Только боссы',level_rush:'Только уровни',finale:'Solgryn доступен'},
 ja: {overview:'一覧',items:'アイテム',characters:'キャラクター',bosses:'ボス',route_stages:'ルート',goals:'目標',copy:'シードをコピー',copied:'コピーしました',copyhint:'シードを選択してコピーしてください：',seed:'シード',deaths:'死亡',slot:'セーブ',menu:'セーブを選択',waiting:'Boshy Randomizerを待っています…',empty:'まだありません',running:'プレイ中',loading:'読み込み中',finished:'クリア',offline:'ゲーム終了または接続切断',found:'アンロック',defeated:'ボス撃破',done:'完了',open:'未達成',current:'現在の区間',target:'目標',checks:'宝箱',stages:'完了した区間',normal:'元のルート・改造版のプレイ',footer:'原作：Solgryn · Randomizer：THXel',randomizer:'ランダマイザー',target_mode:'目標選択',normal_mode:'通常・Randomizer',boss_rush:'ボスラッシュ',level_rush:'レベルラッシュ',finale:'Solgryn解放'}
};
const detailTexts = {
 en:{settings:'Settings',active_extras:'Active extras',no_extras:'No extras enabled',music_pack:'Music pack',blood_pack:'Blood effects',shots:'Shot effects',music_off:'Original music',original:'Original',kamilia3:'Kamilia 3',wannafest22:'WannaFest 22',settings_hint:'Saved run settings. The music pack does not identify the currently playing track.'},
 de:{settings:'Einstellungen',active_extras:'Aktive Extras',no_extras:'Keine Extras aktiv',music_pack:'Musikpaket',blood_pack:'Bluteffekte',shots:'Schusseffekte',music_off:'Originalmusik',original:'Original',kamilia3:'Kamilia 3',wannafest22:'WannaFest 22',settings_hint:'Gespeicherte Run-Einstellungen. Das Musikpaket bezeichnet nicht den gerade laufenden Track.'},
 es:{settings:'Ajustes',active_extras:'Extras activos',no_extras:'No hay extras activos',music_pack:'Paquete musical',blood_pack:'Efectos de sangre',shots:'Efectos de disparo',music_off:'Música original',original:'Original',kamilia3:'Kamilia 3',wannafest22:'WannaFest 22',settings_hint:'Ajustes guardados de la partida. El paquete no indica la pista que está sonando.'},
 ru:{settings:'Настройки',active_extras:'Активные опции',no_extras:'Опции выключены',music_pack:'Музыкальный набор',blood_pack:'Эффекты крови',shots:'Эффекты выстрелов',music_off:'Оригинальная музыка',original:'Оригинал',kamilia3:'Kamilia 3',wannafest22:'WannaFest 22',settings_hint:'Сохранённые настройки забега. Набор не определяет текущую композицию.'},
 ja:{settings:'設定',active_extras:'有効な追加設定',no_extras:'追加設定なし',music_pack:'音楽パック',blood_pack:'血の演出',shots:'弾の演出',music_off:'元の音楽',original:'オリジナル',kamilia3:'Kamilia 3',wannafest22:'WannaFest 22',settings_hint:'保存済みのプレイ設定です。音楽パックは再生中の曲名ではありません。'}
};
for(const [language, rows] of Object.entries(detailTexts)) Object.assign(texts[language],rows);
const $ = id => document.getElementById(id);
const overlay = location.pathname === '/overlay';
document.body.classList.toggle('overlay', overlay);
let state = {connected:false}, language = 'en', selected = 'overview', identity = null;
let initialized = false, seen = new Set(), pending = [], showing = null, showUntil = 0;
let copiedUntil = 0, signature = '', tabSignature = '', lastFetch = 0, menuBaseline = null;
const t = key => texts[language][key] || texts.en[key] || key;
const rowName = row => row.name === 'Ryu (Ausweichen)' ? {de:'Ryu (Ausweichen)',en:'Ryu (Dodge)',es:'Ryu (Esquivar)',ru:'Рю (уклонение)',ja:'リュウ（回避）'}[language] : row.name;
const rowKey = row => `${row.kind}:${row.name}`;
function setLanguage() {
 // The game owns presentation preferences, including OBS and old ?lang links.
 language = state.language || language;
 if (!(language in texts)) language = 'en';
 document.documentElement.lang = language;
}
function formatTime(value) {
 const ticks = Math.floor(Math.max(0, value) * 100), centi = ticks % 100;
 const seconds = Math.floor(ticks / 100) % 60, mins = Math.floor(ticks / 6000);
 return `${String(mins).padStart(2,'0')}:${String(seconds).padStart(2,'0')}.${String(centi).padStart(2,'0')}`;
}
function clearPopup() { pending = []; showing = null; $('popup').hidden = true; }
function accept(next) {
 const hadConnection = state.connected;
 if (state.connected && state.mode === 'menu') menuBaseline = state.updated_at;
 state = next;
 setLanguage();
 const run = state.run_id || null;
 if (!state.connected || state.mode === 'menu') clearPopup();
 if (run) {
  const events = state.events || [];
  if (!initialized || !hadConnection || run !== identity) {
   seen = new Set(events.map(e => e.id));
   identity = run; initialized = true; clearPopup(); selected = 'overview';
   if (hadConnection && menuBaseline !== null) pending = events.filter(e => e.time > menuBaseline && Date.now()/1000-e.time < 12);
   menuBaseline = null;
  } else {
   for (const e of events) {
    if (!seen.has(e.id) && Date.now()/1000 - e.time < 12) pending.push(e);
    seen.add(e.id);
   }
   if (seen.size > 256) seen = new Set(events.map(e => e.id));
  }
 }
 render();
}
function tabs() {
 return ['overview', ...(state.play_mode === 'target' ? ['goals'] : []),
         'items','characters','bosses', ...((state.route_stages || []).length ? ['route_stages'] : []), 'settings'];
}
function groups() {
 if (selected !== 'overview') return [[selected, state[selected] || []]];
 if (state.play_mode === 'target') return [['goals', state.goals || []]];
 if (state.play_mode === 'boss_rush' || state.play_mode === 'level_rush')
  return [['route_stages',state.route_stages || []],['items',(state.items||[]).filter(r=>r.done)],['characters',(state.characters||[]).filter(r=>r.done)]];
 return ['items','characters','bosses'].map(k=>[k,state[k]||[]]);
}
function renderSettings(content) {
 const data=state.run_settings||{};
 const table=document.createElement('dl');table.className='settings-list';
 const pairs=[['music_pack',data.music_enabled?t(data.music_pack||'original'):t('music_off')],['blood_pack',t(data.blood_pack||'original')],['shots',data.shot_labels?.[language]||'—']];
 for(const [key,value] of pairs){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=t(key);dd.textContent=value;table.append(dt,dd);}
 content.append(table);
 const heading=document.createElement('h2');heading.textContent=t('active_extras');content.append(heading);
 const extras=document.createElement('div');extras.className='extras';
 for(const row of state.active_extras||[]){const badge=document.createElement('span');badge.textContent=`${row.icon||'✓'} ${row.labels?.[language]||row.key}`;extras.append(badge);}
 if(!extras.childElementCount)extras.textContent=t('no_extras');content.append(extras);
 const hint=document.createElement('p');hint.className='settings-hint';hint.textContent=t('settings_hint');content.append(hint);
}
function renderGrid() {
 const content = $('content'), groupList = groups();
 const key = JSON.stringify([language,selected,state.connected,state.mode,groupList,showing?.id,state.active_extras,state.run_settings]);
 if (key === signature) return;
 signature = key; content.replaceChildren();
 content.classList.toggle('compact', selected === 'overview' && state.play_mode !== 'target');
 if (!state.connected || state.mode === 'menu') {
  const p=document.createElement('p'); p.className='empty'; p.textContent=t(state.connected?'menu':'waiting'); content.append(p); return;
 }
 if(selected==='settings'){renderSettings(content);return;}
 let count=0;
 for (const [group,rows] of groupList) {
  if (!rows.length) continue;
  count += rows.length;
  const title=document.createElement('h2'), total=document.createElement('span');
  title.textContent=t(group); total.textContent=`${rows.filter(r=>r.done).length}/${rows.length}`; title.append(total); content.append(title);
  const grid=document.createElement('div'); grid.className='grid';
  for (const row of rows) {
   const cell=document.createElement('div'); cell.className='cell'; cell.tabIndex=0;
   for (const [flag,on] of Object.entries({done:row.done,current:row.current,goal:group==='goals',flashing:showing && rowKey(row)===rowKey(showing)})) cell.classList.toggle(flag,Boolean(on));
   cell.title=`${rowName(row)} · ${t(row.done?'done':'open')}${row.current?' · '+t('current'):''}${group==='goals'?' · '+t('target'):''}`;
   cell.setAttribute('aria-label',cell.title);
   const img=document.createElement('img'); img.src=row.icon; img.alt=rowName(row); cell.append(img);
   if (row.done || row.current) { const mark=document.createElement('span'); mark.className='marker'; mark.textContent=row.done?'✓':'▶'; cell.append(mark); }
   grid.append(cell);
  }
  content.append(grid);
 }
 if (!count) {const p=document.createElement('p');p.className='empty';p.textContent=t('empty');content.append(p);}
}
function render() {
 const menu = !state.connected || state.mode === 'menu';
 $('mode').textContent=menu ? 'BOSHY RANDOMIZER' : t(state.play_mode === 'target' ? 'target_mode' : state.play_mode === 'normal' ? 'normal_mode' : state.play_mode || 'randomizer');
 $('deaths').textContent=`${t('deaths')} · ${state.deaths || 0}`;
 $('slot').textContent=state.slot ? `${t('slot')} ${state.slot}` : '';
 $('phase').textContent=t(!state.connected?'offline':state.mode==='menu'?'menu':state.phase||'running');
 $('seed').textContent=`${t('seed')} · ${state.seed||'—'}`;
 $('copy').textContent=t(Date.now()<copiedUntil?'copied':'copy');
 $('copy').disabled=!state.share_seed;
 $('copyhint').textContent=t('copyhint'); $('share').value=state.share_seed||'';
 if (menu) $('copyfallback').hidden=true;
 $('location').textContent=menu?'':state.location||'';
 let rows=state.play_mode==='target'?state.goals||[]:state.route_stages||[];
 let done=rows.filter(r=>r.done).length, total=rows.length;
 $('progress').textContent=menu?'':state.play_mode==='normal'?`${t('normal')} · ${t('checks')} ${state.checks_done||0}/${state.checks_total||0}`:`${t(state.play_mode==='target'?'goals':'stages')} · ${done}/${total}${state.play_mode==='target'&&total>0&&done===total?' · '+t('finale'):''}`;
 $('bar').max=total||1; $('bar').value=done;
 const available=tabs(); if(!available.includes(selected)) selected='overview';
 const tk=JSON.stringify([available,selected,language]);
 if(tk!==tabSignature) {
  tabSignature=tk; $('tabs').replaceChildren();
  for(const key of available){const b=document.createElement('button');b.type='button';b.textContent=t(key);b.dataset.tab=key;b.setAttribute('aria-selected',key===selected?'true':'false');b.onclick=()=>{selected=key;render();};$('tabs').append(b);}
 }
 $('footer').textContent=t('footer'); renderGrid(); tick();
}
function tick() {
 const now=Date.now();
 let elapsed=Number(state.elapsed||0);
 if(state.timer_running&&state.connected) elapsed+=Math.max(0,Math.min(8,now/1000-Number(state.updated_at)));
 $('clock').textContent=formatTime(elapsed);
 if(showing&&now>=showUntil){showing=null;$('popup').hidden=true;renderGrid();}
 if(!showing&&pending.length&&state.connected&&state.mode!=='menu') {
  showing=pending.shift();showUntil=now+4200;
  const goal=(state.goals||[]).some(r=>rowKey(r)===rowKey(showing));
  selected=goal?'goals':{item:'items',character:'characters',boss:'bosses'}[showing.kind];
  $('rewardicon').src=showing.icon;$('rewardname').textContent=rowName(showing);
  $('rewardlabel').textContent=t(showing.kind==='boss'?'defeated':'found');$('popup').hidden=false;render();
 }
 if(copiedUntil&&now>=copiedUntil){copiedUntil=0;$('copy').textContent=t('copy');}
}
$('copy').onclick=async()=>{
 if(!state.share_seed)return;
 try{await navigator.clipboard.writeText(state.share_seed);copiedUntil=Date.now()+2000;$('copyfallback').hidden=true;render();}
 catch{ $('copyfallback').hidden=false;$('share').focus();$('share').select(); }
};
async function poll(){
 try{
  const response=await fetch('/state',{cache:'no-store',signal:AbortSignal.timeout(2500)});
  if(!response.ok)throw new Error('Tracker unavailable');
  const next=await response.json();lastFetch=Date.now();accept(next);
 }catch{if(Date.now()-lastFetch>3000)accept({connected:false});}
 setTimeout(poll,350);
}
setLanguage();render();setInterval(tick,50);poll();
