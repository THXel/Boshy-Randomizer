<p align="right">
  🌐 <b>Language / Sprache / Язык:</b>
  🇬🇧 <a href="README.md">English</a> |
  🇩🇪 <a href="README_DE.md">Deutsch</a> |
  🇷🇺 <a href="README_RU.md"><b>Русский</b></a>
</p>

<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Создано THXel и сообществом спидраннеров I Wanna Be The Boshy</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Современный рандомайзер для <i>I Wanna Be The Boshy</i></b><br>
  Случайные маршруты • Live‑трекер • Сиды маршрутов • Аккуратный GUI
</p>

<p align="center">
  <a href="#-features">Особенности</a> •
  <a href="#-installation">Установка</a> •
  <a href="#-gameplay--modes">Геймплей и режимы</a> •
  <a href="#-technical">Техническая информация</a> •
  <a href="#-support">Поддержка</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – порядок уровней и боссов меняется в каждом забеге  
- 🧩 **Item & Collectable Handling** – стабильная логика триггеров для предметов и коллектаблов  
- 🧍 **Random Characters** – случайные персонажи при старте или на каждой стадии  
- 🎯 **Target Collect Mode** – маршрут скрыт, нужно собрать все целевые предметы  
- 📊 **Live Tracker** – отслеживает достижения, предметы, боссов и персонажей  
- 🧾 **Endscreen Stats** – сводка на финальном экране + код маршрута  
- 🔁 **Deterministic Seeds** – детерминированные сиды для повторения и шаринга забегов  
- ⚙️ **Auto-Setup System** – авто‑настройка Python, модулей, шрифтов и импорта игры  

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="Custom/gameplay.gif?raw=true" width="300">
</div>

---

## 🟩 Requirements

- Windows 10 или новее  
- Подключение к интернету для установки  
- Копия **I Wanna Be The Boshy** (ZIP с сайта Grynsoft)

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550" alt="Download Installer">
</a>

</div>

---

### ▶ Шаг 1 — Запустить установщик  

**`Boshy Randomizer Installer.exe`**

⚠️ **Важно:**  
Windows может показать предупреждение **SmartScreen** вида  
“Windows protected your PC” / “Unrecognized app”.

Это происходит потому, что установщик **не имеет цифровой подписи**.

Чтобы продолжить установку:

1. Нажмите **«More information»**  
2. Нажмите **«Run anyway»**

Это нормально и безопасно.

Далее установщик автоматически:

- копирует все файлы рандомайзера  
- установит Python 3.x (если он не установлен)  
- установит необходимые модули  
- попросит указать **IWBTB ZIP**  
- распакует игру IWBTB в `/IWBTB`  
- создаст ярлыки в меню «Пуск»  

---

### ▶ Шаг 2 — Запуск рандомайзера  

Запуск:

**Пуск → Boshy Randomizer**

Лаунчер проверит:

- корректно ли импортирована папка с игрой IWBTB  
- установлены ли Python и все необходимые модули  
- присутствуют ли все файлы рандомайзера  

Если чего‑то не хватает, будет показано подробное отладочное сообщение.

---

# 🟪 Gameplay & Modes

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="Custom/GUI1.PNG?raw=true" width="300">
  <img src="Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Старт забега

Каждый забег начинается с **Tutorial**, а затем продолжается в один из режимов:

- **Random Route Mode**, или  
- **Target Collect Mode**

в зависимости от настроек в GUI.

## 🧍 Character Randomizer

- По умолчанию: **Dark Boshy**  
- Дополнительно можно включить:
  - случайный персонаж при старте забега  
  - случайный персонаж на каждой стадии  
- При включении:  
  **меню персонажей на F3 отключается** → сиды становятся полностью детерминированными

---

## 🎯 Target Collect Mode

- Скрывает слайдеры маршрута  
- Включает все необходимые необязательные уровни  
- Выбор целей зависит от сида  
- После сбора всех целей: **Solgryn появляется автоматически**

### Важное обновление логики  

Чтобы обеспечить доступ ко всем предметам, **единственные необязательные зоны, которые можно отключать**, это:

- **Boberman**  
- **Questionmark (?)**  
- **Ridley**

Все остальные необязательные зоны **должны оставаться включёнными**.

---

## 🧠 System Behaviour

- Используется только **SaveFile1**  
- **SaveFile1 нельзя удалять**  
- SaveFile2/3 всегда перезаписываются значениями по умолчанию  
- Достижения и разблокированные элементы сохраняются на протяжении всего забега  
- Комната телепорта работает как обычно, но:  
  **вы должны играть тот уровень, который даёт рандомайзер**  
  → пропустить прогресс через телепортер нельзя

---

# 📊 Live Tracker

<div align="left">
  <img src="Custom/livetracker.gif?raw=true" width="300">
</div>

В реальном времени отслеживает:

- предметы  
- достижения  
- боссов  
- персонажей  
- прогресс  

Полностью автоматически — никаких действий от игрока не требуется.

---

# 🎲 Seed-System

Каждый сид определяет:

- порядок уровней и боссов  
- полную структуру маршрута  
- опциональный RNG персонажей  
- выбор целевых предметов  

Сиды отображаются в:

- загрузочном оверлее  
- оверлее старта забега  
- финальном экране  
- отладочном логе  

<div align="left">
  <img src="Custom/route_overlay.gif?raw=true" width="300">
</div>

Делитесь сидами, чтобы другие могли точно повторить ваш забег.

---

# 🟫 Известные примечания

- Некоторые триггеры намеренно слегка смещены ради стабильности  
- Моды или внешние сейв‑файлы могут влиять на работу рандомайзера  

---

# 🔧 Technical

- Python **3.11**  
- Использует:
  - pygetwindow  
  - pyautogui  
  - pillow  
  - numpy  
  - tkinter  

Файл лога:

```txt
INI/randomizer_debug.log
```

Пожалуйста, прикладывайте этот файл при сообщении о багах.

---

# 🟨 Support

**Twitch:**  
https://twitch.tv/THXel  

**Discord:**  
https://discord.gg/ZXgTFjGw

---

# ⚫ Disclaimer

Этот проект не является официальным и никак не связан с  
**Solgryn (Grynsoft)** или каким‑либо официальным релизом IWBTB.

Используйте на свой страх и риск.  
**Удачи — it’s Boshy Time!**
