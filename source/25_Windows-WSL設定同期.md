---
title: Windows⇔WSL 設定同期
icon: 🪟
slug: 25-windows-wsl
card_desc: WSL CLI版とWindows Desktop版の2環境での設定配置と同期の考え方 — WSL symlink方式の罠を実測4パターンで検証し、確認コマンド付きで解説
---

# 25 Windows⇔WSL 設定同期

> 最終更新: 2026-10-14 | 対象: WSL2 CLI版とWindows Desktopアプリ版の2環境運用

## この章の目的

Claude Codeを **WSL CLI版**（Linuxホーム）と **Windows Desktopアプリ版**（`C:\Users\<ユーザー>\`）の2環境で使うとき、設定（CLAUDE.md・settings.json・skills・hooks）が**どのように配置され・どう同期されるか**を1ページにまとめる。

**結論**: 2環境は「**独立実体 + 部分的な自動同期**」で運用するのが現実解。**WSL symlinkでWindows側に見せかける方式は罠だらけ**（本記事の経緯参照・実測で全パターンFAILを確認済み）。

## 現在の構成（実測ベース）

```
【WSL側】~/                             【Windows側】C:\Users\<ユーザー>\
├─ .claude/ ←実ディレクトリ             ├─ .claude/ ←完全に独立した実ファイル
│   ├─ scripts → 正典repoへsymlink      │   ├─ CLAUDE.md（Desktop版専用にカスタマイズ）
│   ├─ skills  → 正典repoへsymlink      │   ├─ settings.json（独立管理）
│   ├─ CLAUDE.md（CLI版・実ファイル）    │   └─ settings.local.json
│   └─ settings.json（実ファイル）       │
└─ projects/<正典repo>/                  └─ projects/
    （scripts/skillsの実体・git管理）
```

| 項目 | WSL CLI版 | Windows Desktop版 | 同期 |
|---|---|---|---|
| CLAUDE.md | CLI版専用（全量・長め） | Desktop版専用（Windows固有の注意点に絞る） | **非同期**（意図的に別物が正解） |
| settings.json | CLI版 | Desktop版 | hooks等を**手動で二重管理**（自動同期はシークレット事故リスクがあるため意図的に限定的） |
| scripts/ | symlink → 正典repo | 実ファイル | 非同期 |
| skills/ | symlink → 正典repo | 実ファイル | 非同期 |

**ポイント**: 両環境のCLAUDE.mdを同じにしない。CLI版とDesktop版では使える機能・パス解決・シェルが違い、共通化しようとすると「どちらかでしか動かない指示」が混入する。Desktop版は「Windows固有の注意（パス変換・文字コード等）」に絞った薄いファイルにするのが効く。

## WSL symlink方式が失敗する理由（実測）

Windows側からWSLの設定を使いたくて、`C:\Users\<ユーザー>\projects\repo` にWSL symlink（`ln -s`）を張ると次の挙動になる（全部実測済み）:

| セル | ツール | 操作 | 結果 |
|---|---|---|---|
| 1 | PowerShell | Get-Content | **FAIL**: `PathNotFound` — symlinkのtargetがLinux pathなのでWindowsから解決できない |
| 2 | PowerShell | git status | **FAIL**: カレント移動に失敗し、別ディレクトリで実行される |
| 3 | cmd.exe | type | **FAIL**: 「UNC パスはサポートされません」+ フォールバック先が別リポジトリになる |
| 4 | cmd.exe | git status | **FAIL**: UNCフォールバックで**意図しない別リポジトリでgitコマンドが動く**（危険） |

特にセル4が深刻: 「あるrepoの状態を見たつもり」が**別repoのgit操作**になっており、誤コミット・誤pushの温床になる。

### どうすればいいか

- Windows側から必要な時は `\\wsl.localhost\<ディストロ>\home\<ユーザー>\...` の**UNC直接指定**を使う（VSCode等のWSL対応アプリ経由が最も安全）
- 設定の共通化は「symlink」でなく「**同期スクリプト＋git**」で行う（シークレットを含むsettings.jsonは必ずマスク処理を挟む）
- CLAUDE.mdは環境別に分け、共通知識だけコピーで持たせる

## 確認コマンド（自分の環境の点検用・読み取り専用）

```bash
# ① WSL側 .claude の symlink 構造を把握
ls -la ~/.claude/ | grep -E "^l"

# ② Windows側 .claude がsymlink無し（=独立実体）であること
ls -la /mnt/c/Users/<ユーザー>/.claude/ | grep -cE "^l"

# ③ Windows側projects配下に迷子symlinkが残っていないか
ls -la /mnt/c/Users/<ユーザー>/projects/

# ④ Windows側からWSL symlinkが解決できるか（失敗パターンの再現確認）
powershell.exe -NoProfile -Command "Get-Item 'C:\Users\<ユーザー>\projects\<repo>' | Select Name"

# ⑤ WSL symlinkの中身をWSL側から確認（target がLinux pathか）
readlink ~/.claude/scripts
```

## 📖 かみ砕くと

2つの家（WSLとWindows）から同じ金庫室（設定フォルダ）を使いたいとき、**渡り廊下（symlink）を自作すると鍵が合わず開かない**か、最悪**別の部屋に繋がる**。正解は「金庫室は1つに置き、必要な複製を検閲付きの宅配（同期スクリプト）で送る」こと。

## 環境早見表（ここを見れば自分の環境が1目でわかる）

### ファイル配置 — 何がどこにあるか

| 役割 | WSL CLI版 | Windows Desktop版 |
|---|---|---|
| 大本の指示書（CLAUDE.md） | `~/.claude/CLAUDE.md`（フル版・`@include`でルールファイルを毎回読込） | `~/.claude/CLAUDE.md`（**Windows固有の注意に絞った別物**・共通化しないのが正解） |
| プロジェクト指示書 | 各repoの `CLAUDE.md` | 同左（`\\wsl.localhost\...`経由で読める） |
| 動作設定（settings.json） | `~/.claude/settings.json`（hooks多数） | `~/.claude/settings.json`（**hooksはWSL版より少ない**・移行済み分のみ） |
| APIキー | `~/.secrets.env`（SessionStart hookがsettings.jsonへ注入・**値を会話やコマンド引数に書かない**） | `.env`読込不可 → Windows環境変数（`[System.Environment]::SetEnvironmentVariable`）かsettings.json直書き・**設定後はアプリ再起動** |
| プロジェクト永続メモリ | `~/.claude/projects/<プロジェクト>/memory/`（`MEMORY.md`索引が毎セッション自動読込） | `C:\Users\<ユーザー>\.claude\projects\...`（**WSL側とは別管理**・同期されない） |

**読み込み順序**（Claude Code標準）: ①ユーザー設定（`~/.claude/`）→ ②プロジェクト設定（repoの`.claude/`）→ ③ローカル設定（`settings.local.json`）。後の方が優先。

### バックエンドLLM — 何で動いているか確認する方法

**原則**: 実行エンジンは**動的**。プロキシ（localhost:8787）が使用率・時間帯で自動切替するため、**起動時のバッジ・画面表示・transcriptのモデル名は当てにならない**（自己申告のキャッシュ）。

| 方法 | 信頼度 | 内容 |
|---|---|---|
| **プロキシstatus（1行確認）** | 高 | `bash ~/bin/proxy-mode.sh status` → 実効provider・使用率を表示。**迷ったらこれ** |
| プロキシ転送ログ | 最高 | journalctlの`Captured actual model`行（実エンジンの直接証跡・`llm-check`スキルの手順） |
| 起動時バッジ/画面表示 | ❌不可 | 起動時固定で動的切替を追跡しない（例: 15-19時のピーク帯は別エンジンに自動フォールバックするがバッジは変わらない） |

切替: 「MiniMaxにして」「GLMにして」「自動に戻して」等の発話でプロキシの手動モード切替（TTL式・期限切れで自動復帰）。**Desktop版（ネイティブSonnet動作）ではモデル切替不可**・外部LLMはMCPツール経由で呼ぶ。

### コマンド系の制限 — guard・分類器と安全な回避

コマンド実行には3層の防御が働く。**引っかかったら別ツールに差し替えて迂回するのではなく、正規経路を使う**のが原則:

| 層 | 検知するもの | 引っかかる例 | 安全な対処 |
|---|---|---|---|
| 破壊的コマンドdeny（hook） | 恒真に危険な操作 | `rm -rf /`・`git push --force origin main`・`sudo rm -rf /`・`DROP DATABASE`・`terraform destroy` | 実行しない。削除は個別ファイル指定+ユーザー確認の正規経路 |
| 設定ファイル書込guard（hook） | 設定ファイル読取→外部送信の連鎖 | `cat settings.json` の内容を含むcurl送信 | 設定の**値**をコマンドに含めない（キー名のみ扱う） |
| 権限分類器（CC本体・auto mode） | 外部送信系コマンド | curlでのデータ送信（設定ファイルを含まなくても発火する場合がある） | **WebFetchツール**や`gh` CLI等の専用経路を使う。分類器の迂回（別ツールへの差し替え）はしない——迂回は検知を外れるだけで事故種別は消えない |

シークレットの鉄則: ①コマンド引数に直接書かない（`source ~/.secrets.env`して`$変数`参照）②「今後許可」を押すと**コマンド全文がallowリストに永続化**される（埋め込み値も）③ denyされたら、なぜ止まったかを確認してから正規経路へ。

### 得意・不得意・障害（実測ベース）

**WSL CLI版**:
- ✅ 得意: bash/スクリプト類の完全動作・cron・hook群（フルセット登録済み）・git hooks・両側ファイル操作（`/mnt/c`でWindows側も参照可）・LLMコスト最適化（プロキシ経由の低コスト運用）
- ⚠️ 不得意/障害: Windows GUIアプリの直接操作・**WSL symlinkはWindows側から解決不可**（本記事前半の実測）・LLMが動的切替のため確認を怠ると誤報告する

**Windows Desktop版**:
- ✅ 得意: Windows固有のファイル/アプリ操作・PowerShellネイティブ実行・GUI連携
- ⚠️ 不得意/障害（実測）: `source ~/.secrets.env`が使えない（Windows環境変数へ）・WSLパス参照は`\\wsl.localhost\...`形式が必要・bash/シェルスクリプトはGit Bash経由で限定的（**chmod/ln -sはexit 0だが実効果なし**＝NTFSで反映されない）・pre-commitフックが`/usr/bin/python3`不在で失敗・WSL側cron/自動実行は`wsl bash -c "..."`経由が必須・hook登録数がWSL版より少なく一部ガードが未登録

**使い分けの指針**: 自動化・スクリプト・定期実行は**WSL CLI版**（本丸）。Windowsアプリ操作・GUIが絡む作業だけDesktop版。両者で設定を共通化しようとせず、**「独立実体+必要なものだけ同期」**（本記事前半の構成）が実測上の正解。

## 🔗 関連章

- [08_設定ファイル](08_設定ファイル.html) — CLAUDE.md・settings.jsonの基本
- [01_基礎概念](01_基礎概念.html) — Desktop vs CLI の違い
