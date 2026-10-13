# Boshy Randomizer — Español

[Linux download — 2026.10.13 RC1](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.13-rc1) · [DEB](https://github.com/THXel/Boshy-Randomizer/releases/download/v2026.10.13-rc1/boshy-randomizer_2026.10.13-1_amd64.deb)

La versión actual integra la configuración en el menú animado original de Boshy: tres partidas independientes, Randomizer y Target Select, semillas BR2 compartibles, selección avanzada de niveles y jefes, recompensas mixtas, un tracker separado y depuración con Ctrl+Alt+D.

## Instalación en Linux

El paquete Debian está dirigido a Linux Mint 22.x / Ubuntu 24.04, amd64 y X11. **La versión actualizada de Windows llegará después.** Los ejecutables de Windows en la raíz corresponden a la versión antigua.

```sh
sudo apt install ./boshy-randomizer_2026.10.13-1_amd64.deb
```

Se instalan Wine, Lutris y las bibliotecas necesarias como dependencias. Abre **Boshy Randomizer** desde el menú de aplicaciones y elige tu carpeta de Boshy o un ZIP del juego. **El juego no se incluye ni se descarga.** El instalador verifica la versión y crea una copia independiente, sin cambiar los guardados ni la configuración originales.

El primer inicio descarga Wine Staging 11.2 WoW64 (unos 72 MiB), verifica su suma de comprobación y prepara un entorno privado. Se reutiliza una instalación idéntica del runner de Lutris si existe. Hace falta internet para las dependencias y la descarga inicial; Lutris no necesita permanecer abierto.

Datos: `~/.local/share/boshy-randomizer/`. Desinstalar el paquete conserva los datos del usuario. Una instalación anterior de desarrollo no se migra automáticamente. El idioma se detecta entre inglés, alemán, ruso, español y japonés, con inglés como alternativa. Los registros de actualización permanecen en inglés. PinguLexa/OBS se mantiene por separado.

[English overview](../README.md) · [Compilación y pruebas](../docs/LINUX_PACKAGE.md)

## Capturas actuales

![Native menu](../docs/media/linux-native-menu.gif)

![Live tracker](../docs/media/linux-run-tracker.png)
