<p align="right">
  🌐 <b>Language / Sprache / Язык / Idioma / 言語:</b>
  🇬🇧 <a href="README.md">English</a> |
  🇩🇪 <a href="README_DE.md">Deutsch</a> |
  🇷🇺 <a href="README_RU.md">Русский</a> |
  🇪🇸 <a href="README_ES.md">Español</a> |
  🇯🇵 <a href="README_JP.md"><b>日本語</b></a>
</p>

<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>THXel と I Wanna Be The Boshy スピードランコミュニティによって制作</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b><i>I Wanna Be The Boshy</i> 向けモダンランダマイザー</b><br>
  ランダムルート • ライブトラッカー • ルートシード • クリーンな GUI
</p>

<p align="center">
  <a href="#-features">機能</a> •
  <a href="#-installation">インストール</a> •
  <a href="#-gameplay--modes">ゲームプレイ & モード</a> •
  <a href="#-technical">技術情報</a> •
  <a href="#-support">サポート</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – 各ランごとにステージとボスの順番がシャッフルされます  
- 🧩 **Item & Collectable Handling** – アイテム／コレクタブル用の安定したトリガーロジック  
- 🧍 **Random Characters** – ラン開始時、またはステージごとにランダムキャラ  
- 🎯 **Target Collect Mode** – ルート非表示で、指定されたターゲットをすべて集めるモード  
- 📊 **Live Tracker** – 実績・アイテム・ボス・キャラをリアルタイム表示  
- 🧾 **Endscreen Stats** – エンドスクリーンにサマリー + ルートコードを表示  
- 🔁 **Deterministic Seeds** – 同じシードでランを完全再現・共有可能  
- ⚙️ **Auto-Setup System** – Python、モジュール、フォント、ゲームインポートを自動セットアップ  

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="Custom/gameplay.gif?raw=true" width="300">
</div>

---

## 🟩 Requirements

- Windows 10 以上  
- セットアップ用のインターネット接続  
- **I Wanna Be The Boshy** のコピー（Grynsoft 配布の ZIP）

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550" alt="Download Installer">
</a>

</div>

---

### ▶ 手順 1 — インストーラーを実行  

**`Boshy Randomizer Installer.exe`**

⚠️ **注意:**  
Windows が **SmartScreen 警告** を表示する場合があります:  
“Windows protected your PC” / “Unrecognized app”

これはインストーラーが **デジタル署名されていない** ためです。

インストールを続行するには:

1. **「More information」** をクリック  
2. **「Run anyway」** をクリック  

これは正常で、安全に実行できます。

その後、インストーラーが自動的に以下を行います:

- ランダマイザーファイル一式のコピー  
- Python 3.x のインストール（未インストールの場合）  
- 必要なモジュールのインストール  
- **IWBTB ZIP** のパスを確認  
- IWBTB 本体を `/IWBTB` に展開  
- スタートメニューにショートカットを作成  

---

### ▶ 手順 2 — ランダマイザーを起動  

起動方法:

**スタートメニュー → Boshy Randomizer**

ランチャーは次の内容をチェックします:

- IWBTB ゲームフォルダが正しくインポートされているか  
- Python と必要なモジュールがインストールされているか  
- すべてのランダマイザーファイルが揃っているか  

不足がある場合は、詳細なデバッグメッセージが表示されます。

---

# 🟪 Gameplay & Modes

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="Custom/GUI1.PNG?raw=true" width="300">
  <img src="Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ ラン開始

すべてのランはまず **Tutorial** から始まり、その後いずれかのモードに進みます:

- **Random Route Mode**  
- **Target Collect Mode**  

どちらになるかは GUI 設定によって決まります。

## 🧍 Character Randomizer

- デフォルトキャラ: **Dark Boshy**  
- オプション:
  - ラン開始時にランダムキャラ  
  - 各ステージごとにランダムキャラ  
- 有効化時:  
  **F3 キャラクターメニューが無効化されます** → シードは完全に決定論的になります

---

## 🎯 Target Collect Mode

- ルートスライダーを非表示にします  
- 必要なオプションエリアをすべて有効化します  
- ターゲット選択はシードに基づきます  
- すべてのターゲットを集めると **Solgryn が自動で出現** します  

### ロジックに関する重要な変更  

すべてのアイテムにアクセスできるようにするため、  
**無効化してよいオプションエリアは次の 3 つのみです**:

- **Boberman**  
- **Questionmark (?)**  
- **Ridley**

それ以外のオプションエリアは **必ず有効にしておく必要があります**。

---

## 🧠 System Behaviour

- 使用されるのは **SaveFile1** のみです  
- **SaveFile1 を削除しないでください**  
- SaveFile2/3 は常にデフォルト値で上書きされます  
- 実績およびアンロック要素はラン全体を通して保持されます  
- テレポートルームは通常どおり機能しますが:  
  **ランダマイザーが指定したステージを必ずプレイする必要があります**  
  → テレポーターで進行度をスキップすることはできません  

---

# 📊 Live Tracker

<div align="left">
  <img src="Custom/livetracker.gif?raw=true" width="300">
</div>

リアルタイムで表示:

- アイテム  
- 実績  
- ボス  
- キャラクター  
- 進行状況  

完全自動 — プレイヤー側の操作は不要です。

---

# 🎲 Seed-System

各シードは次の要素を定義します:

- ステージとボスの順番  
- ルート全体の構造  
- 任意のキャラクター RNG  
- ターゲットアイテムの選択  

シードは以下の場所に表示されます:

- ローディングオーバーレイ  
- ラン開始オーバーレイ  
- エンドスクリーン  
- デバッグログ  

<div align="left">
  <img src="Custom/route_overlay.gif?raw=true" width="300">
</div>

シードを共有することで、他のプレイヤーがまったく同じランを再現できます。

---

# 🟫 既知の注意点

- 安定性向上のため、一部のトリガー位置は意図的に少しずらされています  
- MOD や外部のセーブファイルは動作に影響を与える可能性があります  

---

# 🔧 Technical

- Python **3.11**  
- 使用ライブラリ:
  - pygetwindow  
  - pyautogui  
  - pillow  
  - numpy  
  - tkinter  

ログファイル:

```txt
INI/randomizer_debug.log
```

バグ報告の際はこのファイルを添付してください。

---

# 🟨 Support

**Twitch:**  
https://twitch.tv/THXel  

**Discord:**  
https://discord.gg/ZXgTFjGw

---

# ⚫ Disclaimer

このプロジェクトは非公式であり、  
**Solgryn (Grynsoft)** および公式 IWBTB リリースとは一切関係ありません。

ご利用は自己責任でお願いします。  
**楽しんでください — it’s Boshy Time!**
