# Linux installation

For Linux Mint 22 / Ubuntu 24.04, **amd64 and X11**.

Download **boshy-randomizer_1.0.0-1_amd64.deb** from the [1.0.0 release](https://github.com/THXel/Boshy-Randomizer/releases/tag/v1.0.0), then open it in your package installer. Alternatively:

```sh
sudo apt install ./boshy-randomizer_1.0.0-1_amd64.deb
```

Open **Boshy Randomizer** from your applications menu. First-time setup prepares the Wine Staging runner, asks for your original Boshy ZIP or folder and creates the game entry in Lutris with its icon. Internet access is required for missing dependencies and the first runner download.

The original game is not included. Setup creates a separate patched copy. For later runs, use the application menu or Lutris.

Use the launcher's **Uninstall game** action to remove the managed game installation. Removing the DEB alone retains your user data. The uninstaller offers an explicit choice for saves and preferences.

The package version is `1:1.0.0-1`. The leading Debian epoch makes this first semantic release newer than the earlier date-numbered development packages; the game version is **1.0.0**.
