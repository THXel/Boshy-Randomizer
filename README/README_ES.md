<p align="right">
  <strong>Language:</strong><br>
  <a href="../README.md" title="English">🇬🇧 English</a> ·
  <a href="README_DE.md" title="Deutsch">🇩🇪 Deutsch</a> ·
  <a href="README_RU.md" title="Русский">🇷🇺 Русский</a> ·
  <a href="README_ES.md" title="Español"><strong>🇪🇸 Español</strong></a> ·
  <a href="README_JP.md" title="日本語">🇯🇵 日本語</a>
</p>


<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Creado por THXel y la comunidad de speedrun de I Wanna Be The Boshy</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Randomizador moderno para <i>I Wanna Be The Boshy</i></b><br>
  Rutas aleatorias • Live Tracker • Seeds de ruta • GUI limpia
</p>

<p align="center">
  <a href="#-features">Características</a> •
  <a href="#-installation">Instalación</a> •
  <a href="#-gameplay--modes">Gameplay y modos</a> •
  <a href="#-technical">Técnico</a> •
  <a href="#-support">Soporte</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – el orden de niveles y jefes se mezcla en cada run  
- 🧩 **Item & Collectable Handling** – lógica de triggers estable para ítems y coleccionables  
- 🧍 **Random Characters** – personajes aleatorios al inicio o por etapa  
- 🎯 **Target Collect Mode** – la ruta está oculta, recoge todos los ítems objetivo  
- 📊 **Live Tracker** – muestra logros, ítems, jefes y personajes  
- 🧾 **Endscreen Stats** – resumen al final + código de ruta  
- 🔁 **Deterministic Seeds** – seeds deterministas para compartir y repetir runs  
- ⚙️ **Auto-Setup System** – autoconfiguración de Python, módulos, fuentes e importación del juego  

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="Custom/gameplay.gif?raw=true" width="300">
</div>

---

## 🟩 Requirements

- Windows 10 o superior  
- Conexión a Internet para la instalación  
- Una copia de **I Wanna Be The Boshy** (ZIP de Grynsoft)

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550" alt="Download Installer">
</a>

</div>

---

### ▶ Paso 1 — Ejecutar el instalador  

**`Boshy Randomizer Installer.exe`**

⚠️ **Nota:**  
Windows puede mostrar una advertencia de **SmartScreen** como  
“Windows protected your PC” / “Unrecognized app”.

Esto ocurre porque el instalador **no está firmado digitalmente**.

Para continuar con la instalación:

1. Haz clic en **“More information”**  
2. Haz clic en **“Run anyway”**

Esto es normal y seguro.

Después, el instalador hará automáticamente:

- copiar todos los archivos del randomizador  
- instalar Python 3.x (si no está instalado)  
- instalar los módulos necesarios  
- pedir tu archivo **IWBTB ZIP**  
- descomprimir el juego IWBTB en `/IWBTB`  
- crear accesos directos en el menú Inicio  

---

### ▶ Paso 2 — Iniciar el Randomizer  

Inicia el programa desde:

**Menú Inicio → Boshy Randomizer**

El launcher comprobará:

- que la carpeta del juego IWBTB se ha importado correctamente  
- que Python y todos los módulos necesarios están instalados  
- que todos los archivos del randomizador están presentes  

Si falta algo, se mostrará un mensaje de depuración detallado。

---

# 🟪 Gameplay & Modes

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="Custom/GUI1.PNG?raw=true" width="300">
  <img src="Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Inicio del run

Cada run comienza en el **Tutorial** y continúa en uno de estos modos:

- **Random Route Mode**, o  
- **Target Collect Mode**  

dependiendo de la configuración en la GUI.

## 🧍 Character Randomizer

- Por defecto: **Dark Boshy**  
- Opcional:
  - personaje aleatorio al inicio del run  
  - personaje aleatorio por etapa  
- Cuando está activado:  
  **el menú de personajes con F3 se desactiva** → los seeds son totalmente deterministas

---

## 🎯 Target Collect Mode

- Oculta los sliders de la ruta  
- Activa todos los niveles opcionales necesarios  
- La selección de objetivos depende del seed  
- Después de recoger todos los objetivos: **Solgryn aparece automáticamente**

### Cambio importante en la lógica  

Para garantizar acceso completo a todos los ítems, **las únicas áreas opcionales que se pueden desactivar** son:

- **Boberman**  
- **Questionmark (?)**  
- **Ridley**

Todas las demás áreas opcionales **deben permanecer activadas**.

---

## 🧠 System Behaviour

- Solo se utiliza **SaveFile1**  
- **No debes eliminar SaveFile1**  
- SaveFile2/3 se sobrescriben siempre con valores por defecto  
- Los logros y desbloqueables se mantienen durante todo el run  
- La sala de teletransporte funciona normalmente, pero:  
  **tienes que jugar el nivel que te da el randomizador**  
  → no es posible saltarse progreso usando el teleporter

---

# 📊 Live Tracker

<div align="left">
  <img src="Custom/livetracker.gif?raw=true" width="300">
</div>

Muestra en tiempo real:

- ítems  
- logros  
- jefes  
- personajes  
- progreso  

Todo es completamente automático — no se requieren acciones del jugador。

---

# 🎲 Seed-System

Cada seed define:

- el orden de niveles y jefes  
- la estructura completa de la ruta  
- RNG opcional de personajes  
- la selección de ítems objetivo  

Los seeds aparecen en:

- el overlay de carga  
- el overlay del inicio del run  
- la pantalla final  
- el log de depuración  

<div align="left">
  <img src="Custom/route_overlay.gif?raw=true" width="300">
</div>

Comparte tus seeds para que otros puedan reproducir exactamente el mismo run。

---

# 🟫 Notas conocidas

- Algunos triggers están desplazados ligeramente a propósito para mejorar la estabilidad  
- Mods o archivos de guardado externos pueden afectar al comportamiento del randomizador  

---

# 🔧 Technical

- Python **3.11**  
- Usa:
  - pygetwindow  
  - pyautogui  
  - pillow  
  - numpy  
  - tkinter  

Archivo de log:

```txt
INI/randomizer_debug.log
```

Por favor adjunta este archivo cuando informes de errores。

---

# 🟨 Support

**Twitch:**  
https://twitch.tv/THXel  

**Discord:**  
https://discord.gg/ZXgTFjGw

---

# ⚫ Disclaimer

Este proyecto es no oficial y no está afiliado a  
**Solgryn (Grynsoft)** ni a ningún lanzamiento oficial de IWBTB。

Úsalo bajo tu propia responsabilidad。  
**¡Diviértete — it’s Boshy Time!**
