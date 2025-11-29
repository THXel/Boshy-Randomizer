==============================================================
                        BOSHY RANDOMIZER
      Creado por THXel y la comunidad de speedrun de Boshy
                           © 2025 THXel
==============================================================

Randomizer moderno para "I Wanna Be The Boshy"
Rutas aleatorias • Códigos Seed • Máscaras ER/EB • Live Tracker

--------------------------------------------------------------
CARACTERÍSTICAS
--------------------------------------------------------------
• Orden aleatorio de niveles y jefes (determinístico por seed)
• Target Collect Mode – ruta oculta, objetivos basados en el seed
• Character Randomizer – aleatorio al inicio o por nivel
• Item Randomizer – modo seguro (solo en estadísticas)
• Live Tracker – ítems, jefes, logros, personajes y objetivos
• Estadísticas finales + código de ruta
• Seed-Lock – la GUI se ajusta automáticamente al introducir un seed
• Instalación automática y importación de IWBTB

--------------------------------------------------------------
REQUISITOS
--------------------------------------------------------------
• Windows 10 o más reciente  
• Conexión a internet para la instalación inicial  
• Archivo ZIP original de IWBTB (Grynsoft)

--------------------------------------------------------------
INSTALACIÓN
--------------------------------------------------------------
1) Descargar el instalador:
   https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe

2) Ejecutar:
      Boshy Randomizer Installer.exe

   Nota: SmartScreen puede mostrar una advertencia.
   Haz clic en:
      "Más información" → "Ejecutar de todas formas"

3) El instalador realiza automáticamente:
   • Copia de archivos del Randomizer
   • Instalación de Python 3 (si es necesario)
   • Instalación de módulos requeridos
   • Instalación de la fuente “It’s-Boshy-Time”
   • Importación del ZIP de IWBTB en /IWBTB
   • Creación de accesos directos en el menú inicio

4) Iniciar:
      Menú Inicio → Boshy Randomizer

--------------------------------------------------------------
GAMEPLAY & MODOS
--------------------------------------------------------------

INICIO DEL RUN
• Cada run comienza en el Tutorial.
• Luego, según la GUI:
     - Modo de Ruta Aleatoria
     - Target Collect Mode

COMPORTAMIENTO DEL SISTEMA
• Solo se utiliza SaveFile1.
• NO eliminar SaveFile1.
• SaveFile2 y SaveFile3 se reinician en cada ejecución.
• Logros y desbloqueables se mantienen durante todo el run.
• Awesomesauce está disponible desde el inicio → asegura obtener a Gastly.
• El Teleport Room funciona, pero:
     Debes jugar el nivel asignado por el Randomizer.
     No es posible saltarlo.

--------------------------------------------------------------
CHARACTER RANDOMIZER
--------------------------------------------------------------
• Personaje por defecto: Dark Boshy
• Opciones:
     - Aleatorio al iniciar el run
     - Aleatorio por nivel
• Con el modo activo:
     El menú F3 está deshabilitado (para mantener seeds determinísticos)

--------------------------------------------------------------
ITEM RANDOMIZER (MODO SEGURO)
--------------------------------------------------------------
• El juego se bloquea si se reemplazan ítems durante el gameplay.
• Por eso:
     ✔ Solo se aleatorizan los personajes recolectados
     ✔ Los ítems no cambian dentro del juego
     ✔ La aleatorización aparece solo en la pantalla de estadísticas
• Totalmente estable y seguro para el routing.

--------------------------------------------------------------
TARGET COLLECT MODE
--------------------------------------------------------------
• Ruta completamente oculta
• Objetivos determinados por el seed
• Al recolectar todos los objetivos → Solgryn aparece automáticamente

ÁREAS OPCIONALES QUE PUEDES DESACTIVAR:
• Boberman
• ?
• Ridley

Todas las demás deben permanecer activadas.

--------------------------------------------------------------
LIVE TRACKER
--------------------------------------------------------------
Rastrea en tiempo real:
• Ítems
• Logros
• Jefes
• Personajes
• Progreso
• En Target Collect Mode: los ítems objetivo necesarios

Funciona completamente automático.

--------------------------------------------------------------
SISTEMA DE SEEDS
--------------------------------------------------------------
Ejemplo:
   R14-B4-T0-C2-P1-S152722-ER5-EB34C

Significado:
• R  – cantidad de niveles
• B  – cantidad de jefes
• T  – Target Collect (0/1)
• C  – modo de Character Randomizer
• P  – modo de Item Randomizer
• S  – valor del seed
• ER – máscara de niveles opcionales
• EB – máscara de jefes opcionales

Cualquier jugador usando este seed obtendrá el mismo run 1:1.

--------------------------------------------------------------
TÉCNICO
--------------------------------------------------------------
• Python 3.11
• Módulos: pygetwindow, pyautogui, pillow, numpy, tkinter

Archivo de log:
   INI/randomizer_debug.log

--------------------------------------------------------------
SOPORTE
--------------------------------------------------------------
Twitch:   https://twitch.tv/THXel
Discord:  https://discord.gg/ZXgTFjGw

--------------------------------------------------------------
AVISO LEGAL
--------------------------------------------------------------
Proyecto no oficial.
Sin relación con Solgryn (Grynsoft) o IWBTB.
Úsalo bajo tu propia responsabilidad.
¡Diviértete — It’s Boshy Time!
==============================================================
