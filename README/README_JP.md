# Boshy Randomizer — 日本語

[Linux download — 2026.10.13 RC1](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.13-rc1) · [DEB](https://github.com/THXel/Boshy-Randomizer/releases/download/v2026.10.13-rc1/boshy-randomizer_2026.10.13-2_amd64.deb)

現在のバージョンは、Boshy 本来のアニメーション付きメニューに設定を統合しています。独立した3つのセーブ、Randomizer と Target Select、共有可能な BR2 シード、ステージとボスの詳細設定、アイテムとキャラクターの混合報酬、別ウィンドウのトラッカー、Ctrl+Alt+D のデバッグ画面を利用できます。

## Linux へのインストール

Debian パッケージの対象は Linux Mint 22.x / Ubuntu 24.04、amd64、X11 です。**更新版の Windows バージョンは後日提供予定です。** リポジトリ直下の Windows 実行ファイルは旧バージョンです。

```sh
sudo apt install ./boshy-randomizer_2026.10.13-2_amd64.deb
```

Wine、Lutris、必要なライブラリが依存パッケージとしてインストールされます。アプリケーションメニューから **Boshy Randomizer** を起動し、Boshy のフォルダーまたはゲームの ZIP を選択してください。**ゲーム本体は同梱されず、ダウンロードもされません。** バージョンを確認して専用コピーを作成するため、元のセーブや設定は変更されません。

初回起動時に Wine Staging 11.2 WoW64（約72 MiB）を自動取得し、チェックサムを検証して専用環境を準備します。同一の Lutris ランナーがあれば再利用します。依存パッケージと初回の Wine 取得にはインターネットが必要です。プレイ中に Lutris を開いておく必要はありません。

データの保存先は `~/.local/share/boshy-randomizer/` です。パッケージを削除してもユーザーデータは保持されます。以前の開発版からの自動移行は行いません。英語、ドイツ語、ロシア語、スペイン語、日本語を自動判定し、非対応の言語では英語を使用します。更新履歴は常に英語です。PinguLexa/OBS 連携は別途管理されています。

[English overview](../README.md) · [ビルドと検証](../docs/LINUX_PACKAGE.md)

## 現在の画面

![Native menu](../docs/media/linux-native-menu.gif)

![Live tracker](../docs/media/linux-run-tracker.png)
