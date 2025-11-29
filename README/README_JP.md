<p align="right">
  <strong>言語:</strong><br>
  <a href="../README.md" title="English">🇬🇧 English</a> ·
  <a href="README_DE.md" title="Deutsch">🇩🇪 Deutsch</a> ·
  <a href="README_RU.md" title="Русский">🇷🇺 Русский</a> ·
  <a href="README_ES.md" title="Español">🇪🇸 Español</a> ·
  <a href="README_JP.md" title="日本語"><strong>🇯🇵 日本語</strong></a>
</p>

<div align="center">

  <img src="../Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>作成者: THXel & I Wanna Be The Boshy スピードランコミュニティ</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b><i>I Wanna Be The Boshy</i> 用モダンランダマイザー</b><br>
  ランダムルート • Seedコード • ER/EBマスク • ライブトラッカー • クリーンGUI
</p>

<p align="center">
  <a href="#-特徴">特徴</a> •
  <a href="#-インストール">インストール</a> •
  <a href="#-ゲームプレイ--モード">ゲームプレイ & モード</a> •
  <a href="#-seedシステム">Seedシステム</a> •
  <a href="#-技術情報">技術情報</a> •
  <a href="#-サポート">サポート</a>
</p>

---

## 🟦 特徴

- 🎲 **ランダムルート** – シードに基づく完全決定的なステージ & ボスルート  
- 🧩 **アイテムランダマイザー（安全なステータスモード）** – *取得したキャラクターはランダム化*、ゲーム内アイテムは変更されずクラッシュ回避  
- 🧍 **キャラクターランダマイザー** – ラン開始時またはステージ毎にランダム、完全決定的  
- 🎯 **ターゲットコレクトモード** – ルート非表示、Seedでターゲット決定  
- 📊 **ライブトラッカー** – アイテム、ボス、実績、キャラクター、ターゲットアイテムを追跡  
- 🔁 **決定的シード** – 同じRunを100%再現可能  
- 🧱 **ER/EBマスク** – オプションステージ・ボスのON/OFF情報をSeedに保存  
- 🔒 **SeedロックGUI** – Seed入力でGUIをロックし設定を表示  
- ⚙️ **自動セットアップ** – Python、モジュール、フォントを自動インストールし IWBTB をインポート  

---

## 🎮 ゲームプレイプレビュー

<div align="center">
  <img src="../Custom/gameplay.gif?raw=true" width="300">
  <img src="../Custom/gameplay2.gif?raw=true" width="300">
</div>

---

## 🟧 インストール

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20BOSHY%20RANDOMIZER%20インストーラーをダウンロード-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550">
</a>

</div>

---

### ▶ ステップ1 — インストーラーを実行

**`Boshy Randomizer Installer.exe`**

⚠️ **SmartScreen 注意:**  
Windows が次のように表示する場合があります：

“Windows により PC が保護されました” / “不明なアプリ”。

これは正常で、インストーラーは **デジタル署名されていません**。

続行するには：

1. **詳細情報** をクリック  
2. **実行** を選択  

インストーラーは自動的に以下を行います：

- Randomizerファイルをコピー  
- Python 3 をインストール（必要な場合）  
- 必要なモジュールをインストール  
- **IWBTB ZIP** を要求  
- `/IWBTB` に展開  
- スタートメニューにショートカット追加  

---

### ▶ ステップ2 — ランダマイザーを起動

**スタートメニュー → Boshy Randomizer**

ランチャーは以下をチェックします：

- IWBTB が正しくインポートされたか  
- Python & モジュールがインストール済みか  
- 必要なファイルが揃っているか  

問題がある場合はデバッグメッセージを表示します。

---

# 🟪 ゲームプレイ & モード

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="../Custom/GUI1.PNG?raw=true" width="300">
  <img src="../Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Run開始

• すべてのRunは **チュートリアル** から始まります。  
• その後、GUI設定に応じて：  
  – **ランダムルートモード**  
  – **ターゲットコレクトモード**

## ▶ システム動作

• 使用されるのは **SaveFile1 のみ**。  
• **SaveFile1 を削除しないでください。**  
• SaveFile2/3 は毎回初期化されます。  
• 実績・アンロック項目は全Runで維持されます。  
• **Awesomesauce** は Run開始時に必ず所持 → **Gastly を確実に入手可能**。  
• テレポートルームは通常通り動作しますが：  
  **ランダマイザーが指定するステージを必ずプレイする必要があります。**

---

## 🧍 キャラクターランダマイザー

- デフォルト: Dark Boshy  
- オプション:  
  - Run開始時ランダム  
  - ステージ毎にランダム  
- 有効時：  
  **F3 キャラクターメニュー無効化** → 完全決定的  

---

## 🧩 アイテムランダマイザー – 詳細

IWBTB はゲーム内アイテムの差し替えで **クラッシュ** します。  
そのため以下の仕様：

- ✔ **取得したキャラクターのみランダム化**  
- ✖ **ゲーム内アイテムは変更されない**（クラッシュ防止）  
- ✔ アイテムは **ステータス画面のみ** ランダム表示  
- ✔ ゲームプレイに影響なし  
- ✔ 安定 & ルーティング完全対応  

---

## 🎯 ターゲットコレクトモード

- ルート非表示  
- Seed によりターゲット決定  
- すべて集めると → **Solgryn が出現**

無効化できるオプションステージ：

- Boberman  
- “?”  
- Ridley  

その他は常に有効である必要があります。

---

# 📊 ライブトラッカー

<div align="left">
  <img src="../Custom/livetracker.gif?raw=true" width="300">
</div>

追跡内容：

- アイテム  
- 実績  
- ボス  
- キャラクター  
- プログレッション  
- **ターゲットコレクトモードでは：必要なターゲットアイテム**

全自動で動作します。

---

# 🎲 Seedシステム

<div align="left">
  <img src="../Custom/route_overlay.gif?raw=true" width="300">
</div>

例：

```
R14-B4-T0-C2-P1-S152722-ER5-EB34C
```

意味：

- **R** – ステージ数  
- **B** – ボス数  
- **T** – ターゲットモード  
- **C** – キャラクターランダム  
- **P** – アイテムランダム  
- **S** – Seed値  
- **ER** – ステージマスク  
- **EB** – ボスマスク  

このSeedを使用すれば誰でも **同じRunを完全再現** できます。

---

# 🔧 技術情報

- Python 3.11  
- 使用ライブラリ:
  - pillow  
  - numpy  
  - pyautogui  
  - pygetwindow  
  - tkinter  

ログファイル：

```
INI/randomizer_debug.log
```

---

# 🟨 サポート

**Twitch:** https://twitch.tv/THXel  
**Discord:** https://discord.gg/ZXgTFjGw  

---

# ⚫ 免責事項

本プロジェクトは **Solgryn (Grynsoft)** とは無関係の非公式ツールです。  
使用は自己責任でお願いします。  
**楽しんでください — It’s Boshy Time!**
