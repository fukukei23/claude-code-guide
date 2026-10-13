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

## 🔗 関連章

- [08_設定ファイル](08_設定ファイル.html) — CLAUDE.md・settings.jsonの基本
- [01_基礎概念](01_基礎概念.html) — Desktop vs CLI の違い
