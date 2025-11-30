<p align="right">
  <strong>Idioma:</strong><br>
  <a href="../README.md" title="English">🇬🇧 English</a> ·
  <a href="README_DE.md" title="Deutsch">🇩🇪 Deutsch</a> ·
  <a href="README_RU.md" title="Русский">🇷🇺 Русский</a> ·
  <a href="README_ES.md" title="Español"><strong>🇪🇸 Español</strong></a> ·
  <a href="README_JP.md" title="日本語">🇯🇵 日本語</a>
</p>

<div align="center">

  <img src="../Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Creado por THXel & la comunidad de speedrun de I Wanna Be The Boshy</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Randomizer moderno para <i>I Wanna Be The Boshy</i></b><br>
  Rutas aleatorias • Códigos Seed • Máscaras ER/EB • Live Tracker • GUI limpia
</p>

<p align="center">
  <a href="#-características">Características</a> •
  <a href="#-instalación">Instalación</a> •
  <a href="#-gameplay--modos">Gameplay & Modos</a> •
  <a href="#-sistema-de-seeds">Sistema de Seeds</a> •
  <a href="#-técnico">Técnico</a> •
  <a href="#-soporte">Soporte</a>
</p>

---

## 🟦 Características

- 🎲 **Rutas Aleatorias** – rutas de niveles y jefes completamente determinísticas basadas en seeds  
- 🧩 **Item Randomizer (Modo Seguro de Stats)** – *los personajes recolectados se aleatorizan*, pero los ítems del juego no se reemplazan (para evitar crashes)  
- 🧍 **Character Randomizer** – aleatorio al inicio o por nivel, totalmente determinístico  
- 🎯 **Target Collect Mode** – ruta oculta, objetivos basados en el seed  
- 📊 **Live Tracker** – rastrea ítems, logros, jefes, personajes y objetivos  
- 🔁 **Seeds determinísticos** – comparte y reproduce runs idénticos  
- 🧱 **Máscaras ER/EB** – niveles y jefes opcionales incluidos en el seed  
- 🔒 **Seed-Lock GUI** – al introducir un seed, la GUI se bloquea y muestra las configuraciones  
- ⚙️ **Auto-Setup** – instala Python, módulos, fuentes e importa IWBTB automáticamente  

---

## 🎮 Vista previa del gameplay

<div align="center">
  <img src="../Custom/gameplay.gif?raw=true" width="300">
  <img src="../Custom/gameplay2.gif?raw=true" width="300">
</div>

---

## 🟧 Instalación

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DESCARGAR%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550">
</a>

</div>

---

### ▶ Paso 1 — Ejecutar el instalador

**`Boshy Randomizer Installer.exe`**

⚠️ **Aviso SmartScreen:**  
Windows puede mostrar:

“Windows protegió su PC” / “Aplicación desconocida”.

Esto es normal — el instalador **no está firmado digitalmente**.

Haz clic en:

1. **Más información**  
2. **Ejecutar de todas formas**

El instalador hará automáticamente:

- Copiar los archivos del Randomizer  
- Instalar Python 3 (si falta)  
- Instalar todos los módulos necesarios  
- Solicitar tu **IWBTB ZIP**  
- Extraer el juego en `/IWBTB`  
- Crear accesos directos en el menú inicio  

---

### ▶ Paso 2 — Iniciar el Randomizer

Inicia desde:

**Menú Inicio → Boshy Randomizer**

El launcher verificará:

- IWBTB importado correctamente  
- Python y módulos instalados  
- Archivos completos  

Si algo falta, se mostrará un mensaje de depuración.

---

# 🟪 Gameplay & Modos

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="../Custom/GUI1.PNG?raw=true" width="300">
  <img src="../Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Inicio del Run

• Cada run comienza en el **Tutorial**.  
• Luego, según la GUI:  
  – **Ruta Aleatoria**  
  – **Target Collect Mode**

## ▶ Comportamiento del sistema

• Solo se usa **SaveFile1**.  
• **No elimines SaveFile1.**  
• SaveFile2 y SaveFile3 se sobrescriben en cada run.  
• Logros y desbloqueables se mantienen durante todo el run.  
• **Awesomesauce** siempre está disponible al inicio para garantizar la obtención de **Gastly**.  
• El Teleport Room funciona normalmente, pero:  
  Para progresar, **debes jugar el nivel dado por el Randomizer** — no es posible saltarlo.

---

## 🧍 Character Randomizer

- Predeterminado: Dark Boshy  
- Opciones:  
  - Aleatorio al inicio del run  
  - Aleatorio por nivel  
- Mientras está activo:  
  **El menú F3 está deshabilitado** → seeds determinísticos  

---

## 🧩 Item Randomizer – Detalles

El juego hace crash si los ítems se reemplazan **dentro del juego**.  
Por eso funciona así:

- ✔ **Los personajes recolectados se aleatorizan**  
- ✖ **Los ítems no se reemplazan en el gameplay** (protección de crash)  
- ✔ Los ítems aparecen aleatorios **solo en las estadísticas**  
- ✔ No afecta al gameplay  
- ✔ 100% estable y seguro para routing  

---

## 🎯 Target Collect Mode

- Ruta oculta  
- Objetivos determinados por el seed  
- Al recolectar todos los objetivos → **Solgryn aparece automáticamente**

Áreas opcionales que puedes desactivar:

- Boberman  
- “?”  
- Ridley  

Las demás deben permanecer activadas.

---

# 📊 Live Tracker

<div align="left">
  <img src="../Custom/livetracker.gif?raw=true" width="300">
</div>

Rastrea:

- Ítems  
- Logros  
- Jefes  
- Personajes  
- Progreso en vivo  
- **En Target Collect Mode:** los **objetivos necesarios**

Completamente automático — sin entrada del jugador.

---

# 🎲 Sistema de Seeds

<div align="left">
  <img src="../Custom/route_overlay.gif?raw=true" width="300">
</div>

Un código seed como:

```
R14-B4-T0-C2-P1-D1-S152722-ER5-EB34C
```

significa:

- **R** – niveles  
- **B** – jefes  
- **T** – modo Target Collect (0 = apagado, 1 = activado)  
- **C** – randomizador de personaje  
  - 0 = desactivado  
  - 1 = personaje aleatorio al iniciar el run  
  - 2 = personaje aleatorio por nivel  
- **P** – item randomizer (0 = apagado, 1 = encendido — personajes se randomizan, items no se cambian dentro del juego)  
- **D** – dificultad  
  - 0 = Ez  
  - 1 = Average  
  - 3 = Rage  
- **S** – seed  
- **ER** – máscara de niveles opcionales activados  
- **EB** – máscara de jefes opcionales activados  

Cualquier jugador que use este código obtendrá **exactamente la misma ruta, dificultad y RNG de personajes**.

---

# 🔧 Técnico

- Python 3.11  
- Librerías:
  - pillow  
  - numpy  
  - pyautogui  
  - pygetwindow  
  - tkinter  

Archivo de log:

```
INI/randomizer_debug.log
```

---

# 🟨 Soporte

**Twitch:** https://twitch.tv/THXel  
**Discord:** https://discord.gg/ZXgTFjGw  

---

# ⚫ Disclaimer

Proyecto no oficial, sin afiliación con **Solgryn (Grynsoft)**.  
Úsalo bajo tu propia responsabilidad.  
**¡Diviértete — it’s Boshy Time!**
