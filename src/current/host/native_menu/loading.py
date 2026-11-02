"""Real run-preparation stages; worker reports never render or touch the UI."""
from contextlib import contextmanager
from contextvars import ContextVar

_listener = ContextVar('run_loading_listener', default=None)
LANGS = ('de','en','es','ru','ja')
TEXT = {
 'prepare': ('Run wird vorbereitet …','Preparing run …','Preparando partida …','Подготовка забега …','ランを準備中…'),
 'verify': ('Spieldaten werden geprüft …','Checking game data …','Comprobando datos …','Проверка данных …','ゲームデータを確認中…'),
 'graphics': ('Grafiken werden vorbereitet …','Preparing graphics …','Preparando gráficos …','Подготовка графики …','画像を準備中…'),
 'music': ('Musik wird vorbereitet …','Preparing music …','Preparando música …','Подготовка музыки …','音楽を準備中…'),
 'save': ('Spielstand wird erstellt …','Creating save …','Creando partida …','Создание сохранения …','セーブを作成中…'),
 'check': ('Run wird geprüft …','Checking run …','Comprobando partida …','Проверка забега …','ランを確認中…'),
 'start': ('Run wird gestartet …','Starting run …','Iniciando partida …','Запуск забега …','ランを開始中…'),
}

@contextmanager
def listen(callback):
    token = _listener.set(callback)
    try:
        yield
    finally:
        _listener.reset(token)


def report(percent, stage):
    callback = _listener.get()
    if callback is not None:
        callback((max(0,min(100,int(percent))),stage))


def draw(image, model, fonts):
    from PIL import ImageDraw
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((16,198,624,473),6,fill='#121f2b',outline='#8cddc6',width=2)
    percent, stage = getattr(model,'loading_progress',(2,'prepare'))
    title = model.t(model.busy_label)
    language = model.language if model.language in LANGS else 'en'
    label = TEXT.get(stage,TEXT['prepare'])[LANGS.index(language)]
    for y,text,font in ((235,title,16),(293,label,12)):
        x = 320 - d.textlength(text,font=fonts[font])/2
        d.text((x,y),text,font=fonts[font],fill='#edf5f6')
    d.rounded_rectangle((50,345,590,374),5,fill='#243744',outline='#6c8d9c')
    width = max(4,round(536*percent/100))
    d.rounded_rectangle((52,347,52+width,372),4,fill='#8cddc6')
    text = f'{percent} %'
    d.text((320-d.textlength(text,font=fonts[14])/2,389),text,font=fonts[14],fill='#9aecd5')
