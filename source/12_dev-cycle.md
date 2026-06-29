# dev-cycle — コード品質改善サイクル

Claude Code で**コード品質を継続的に改善するための5フェーズサイクル**。
スキル `/dev-cycle` として呼び出す。

---

## 全体フロー

```
【0. 判断】プロジェクト規模で開始フェーズを決める
  小規模（変更ファイル少）→ フェーズ2から
  大規模（50件超の改善）  → フェーズ1から
        ↓
【1. 任意】品質スイープ
        ↓
【2. 推奨】コードレビュー v3
        ↓
【3. 必須】Issue化
        ↓
【4. 必須】自律実装ループ（Daily Triage メタループ）
        ↓
【5. 自動】完了通知
```

> **フェーズ4は方式刷新済み**: 旧 `start.sh --auto`（Issue一括自動実装）は廃止。現在は **Daily Triage メタループ**（毎朝タスク候補を生成→人間承認→実装+検証の連鎖）が主役。詳細は「フェーズ4」参照。

---

## フェーズ1: 品質スイープ

全ファイルを機械的に走査し **High/Medium/Low** リストを生成する（読み取り専用・変更なし）。

| 項目 | 内容 |
|---|---|
| 実行方法 | CronCreate（20分間隔）または手動 |
| チェック内容 | セキュリティ問題・巨大関数（50行超）・重複ロジック・未使用import |
| いつ使う | 50件超の大規模改善前、定期健全性確認 |

CronCreate 設定例:

```
CronCreate:
  schedule: "*/20 * * * *"
  durable: true
  prompt: |
    <project> のコード品質スイープ。
    未完了エリアを1つ選び全ファイルを読んでHigh/Medium/Lowに分類。
    結果を記録に保存。コード変更は一切しない。
```

---

## フェーズ2: コードレビュー v3

重要ファイルを深く読み、**★スコア + P1/P2 改善提案**を出力する。

### 実行手順

```bash
# Step 0: ファイルの重要度スコアリング
python score-files.py <project_path> --top 20 --json

# Step 1: 行数実測（スコアと照合）
wc -l <file1> <file2> ...

# Step 2: Read ツールで実際に読む → LLM で評価
```

> **注意**: LLMに読ませずに評価させると行数捏造が発生する（v2での教訓）。
> Step 2 の「実際に読む」が最重要。

### 評価カード形式

```
file: routes/products.py
loc: 342
star: ★★★☆☆
strengths: Blueprint分離が明確、エラーハンドリング統一
weaknesses: 関数が50行超×3件、except Exceptionが2箇所
priority: P1（except限定化）、P2（関数分割）
```

---

## フェーズ3: Issue化

P1/P2 リストを作業タスク（Issue またはバックログ）に一括登録する。

### タイトル形式

| ラベル | 優先度 | 目安工数 |
|---|---|---|
| `[A]` | low | 1h以下 |
| `[B][C]` | medium | 2〜3h |
| `[D]` | high | 4h以上 |

タイトル例:
```
test: [A] test_xxx.py に scope="function" を明示
fix:  [B] except Exception を具体的な例外型に限定
refactor: [D] test_routes_coverage.py を6ファイルに分割
```

> Phase3以降は GitHub Issue に限らず、ローカルのバックログ（Markdown）をタスク源としても運用できる（フェーズ4の Daily Triage は両方を収集対象とする）。

---

## フェーズ4: 自律実装ループ（Daily Triage メタループ）

タスクを**人間承認付きで自律実行する連鎖**。毎朝タスク候補を自動生成し、承認を経て「実装→検証→次タスク」が自動で回る。

### 1日の流れ

```
① Daily Triage（毎朝6:07・自動）
   バックログ + handoff + 進行中タスクを収集 → today-tasks.md 生成
        ↓
② 候補確認（セッション開始時・自動表示）
        ↓
③ 人間承認（approve.py・手動ゲート）
   実行タスクを選択 → state.json 登録 → 最初のタスク起動
        ↓
④ 自律実行連鎖（自動）
   run-task.sh: 実装（git commit まで）→ 検証（別プロセス・分離）
     ↓ verify-result.txt に OK / NG を書き出し
   Stop Hook → next_issue.py が判定:
     OK → completed 記録 → 次タスク起動
     NG → blocked 記録 → 停止（人間エスカレーション）
        ↓
⑤ 終了（自動）
   全完了 → 完了通知 / NG等 → 停止通知
```

### アーキテクチャ

| コンポーネント | 役割 |
|---|---|
| `daily-triage.sh` | Triage 発火エンジン（LLM判定呼出・today-tasks.md 生成・通知） |
| `daily_triage.py` | バックログ/handoff収集・LLM判定・実在 repo チェック |
| `approve.py` | 人間承認ゲート・manual タスク除外・state.json 登録 |
| `run-task.sh` | 実装 + 検証（別プロセス）・対象 repo で実行 |
| `next_issue.py` | Stop hook 発火・検証結果判定・completed/blocked 遷移・次タスク起動 |

### 多 repo 混在キューのタグ付け

`today-tasks.md` の候補は1個のリストに複数リポジトリのタスクが混在しうる。`daily_triage.py` が `repo-index.yaml` から実在リポ名一覧（`collect_repo_names`）を取得し、LLM判定プロンプト（`JUDGE_PROMPT`）に「この中から選べ」と制約として渡す。出力フォーマットは各候補行末に repo タグを付与する:

```
1. **<タスク>** — <理由>（想定コスト: <S/M/L>）（repo: <name>）
2. **<タスク>** — <理由>（想定コスト: <S/M/L>）（手動）
```

- `（repo: <name>）`: コード作業・対象リポジトリが repo_list 内に実在
- `（手動）`: コード作業でない（応募・学習・手動運用）、または対象リポジトリ外

`approve.py` はこのタグを解析して `state.json` にタスクごとの `repo` を登録する（旧: 承認時に手動でrepoをCLI入力 → 廃止・自動解析に統一）。`手動` タグのタスクは自律実行キューから除外される。
| `apply-crons` | Cron定義（`renew-crons.sh` の `@cron`タグ）↔実体（`scheduled_tasks.json`）の冪等同期・健康診断（`check`/`diff`/`apply`/`clean`）・7日失効を補完するCron永続化インフラ |

### state.json 構造（タスクごとに repo を持つ）

```json
{
  "active": false,
  "current": null,
  "pending": [],
  "completed": [
    { "title": "validate_email にRFCチェックを追加" }
  ],
  "blocked": []
}
```

- `active`: ループ生存フラグ（false で即終了）
- `current`: 実行中タスク（`repo` はタスクごと・真実のソース）
- `pending`: 待機中タスク群（複数 repo 混在可）
- `completed` / `blocked`: 各タスクの `repo` を記録

> **重要**: 複数リポジトリが混在するキューにも対応するため、repo は top-level ではなく**タスクごと**に持たせる（旧 `repo_path` は廃止）。

### 実装と検証を分離する理由

`run-task.sh` は「実装する Claude」と「検証する Claude」を**別プロセス**で起動する。実装した主体が自分で「OK」と判定するのを防ぎ、独立した検証結果（`verify-result.txt`）を連鎖の判定に使う。これで「テストを通したつもり」の誤判定を排除する。

### 運用コマンド

```bash
# 手動で Daily Triage 実行（通知なし）
bash scripts/auto-dev/daily-triage.sh

# 承認（候補選択 → state.json 登録・最初のタスク起動）
python3 scripts/auto-dev/approve.py

# state 確認
cat ~/.claude/state/state.json

# テスト
cd scripts/auto-dev && python3 -m pytest -q
```

### 毎朝の自動化（CronCreate）

Daily Triage は durable Cron で毎朝6:07に発火。結果は Discord 等の webhook に通知（未設定時は skip 警告のみ）。

```
CronCreate:
  schedule: "7 6 * * *"
  durable: true
  prompt: |
    Daily Triage: daily-triage.sh --notify-discord を実行。
    バックログ + handoff + 進行中タスクを収集 → today-tasks.md 生成 → 通知。
    失敗時は理由を報告。
```

> Cron は7日で失効するため、`renew-crons.sh`（外部スクリプト）経由で6日ごとに再登録して永続化する。定義（`@cron`タグ）↔実体（`scheduled_tasks.json`）の整合は `apply-crons`（`check`/`apply`/`clean`）で冪等同期・健康診断する。詳細は **11章「Cron管理の注意点」** 参照。

### 緊急停止

```python
import json
state_path = '~/.claude/state/state.json'
s = json.load(open(state_path))
s['active'] = False
json.dump(s, open(state_path, 'w'), indent=2)
print('停止:', s)
```

---

## フェーズ5: 完了通知（自動）

全タスク完了（`pending=[]`）を検知したら自動実行:

- ターミナルベル音
- OS通知（macOS: `osascript` / Windows: PowerShell toast）

```python
# macOS 例
import subprocess
subprocess.run(["osascript", "-e",
    'display notification "全タスク完了" with title "dev-cycle"'])

# Windows (WSL2) 例
subprocess.Popen(["powershell.exe", "-c",
    '$n=New-Object System.Windows.Forms.NotifyIcon; ...'])
```

---

## LLM 割り当て

| フェーズ | 推奨LLM | 理由 |
|---|---|---|
| 品質スイープ | 高速・安価なモデル | パターン検出・列挙 |
| コードレビュー v3 | 高精度モデル | 深い読解・主観評価 |
| Issue 化 | 任意 | テンプレート変換 |
| コード生成（実装） | 大量処理向けモデル | 繰り返し生成 |
| テスト・CI 確認 | Claude 直接 | ツール呼び出し |

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| 承認時に候補が変わる | 別セッションが Triage を再実行 | 承認直前に today-tasks.md を再読 or タイムスタンプ確認 |
| 検証 NG で停止 | テスト失敗・実装不備 | `blocked` を確認 → 手動修正 → `active:true` + pending 追加で再開 |
| Cron が消えた | 7日失効 | `renew-crons.sh` で再登録（11章参照） |
| 次タスクが起動しない | `active: false` / Stop hook 未発火 | state.json 確認 → 手動で `active:true` |

---

## 💡 やさしい補足（初心者向け）

- **「dev-cycle」= コードを自動で良くするサイクル**: 品質チェック→レビュー→修正を、人間が細かく指示しなくても回せる仕組み
- **5つのフェーズ**: ①全体をざっと掃除 ②詳しくレビュー ③問題をリスト化 ④自動で修正 ⑤完了報告
- **フェーズ4が主役**: 毎朝「今日やるタスク」を自動で拾ってきて、承認ボタン1つで実装→検証まで自動で進む
- **人間は承認と見守りだけ**: 完全に放置するのではなく、朝の候補を確認して「これでお願い」と渡すと、あとは自律的に回る
- **使う場面**: 「このプロジェクト、だらしなくなってきたな」を一気に綺麗にしたい時や、日々の小さな改善を自動で積み重ねたい時

---

## 実績（参考）

| プロジェクト | 実施内容 | 結果 |
|---|---|---|
| Flask 物販管理システム | Issue #75〜#77 を自律実装 | 3件全自動完了・テスト全件パス |
| 自律型AIフレームワーク | テストカバレッジ 83.81% 達成 | 4,602 テスト通過・0 失敗 |
| NexusCore（Daily Triage方式） | ハードコードフォールバックの設定化 | 連鎖1サイクルで実装+検証完了 |

---

## 補足: 旧Issue一括自律ループ（start.sh --auto・廃止）

Loop Engineering 導入前に使っていた方式。現在は機能喪失中。

- **方式**: `start.sh --auto <repo>` で GitHub のオープン Issue を priority 順に一括自動実装（ブランチ作成→実装→テスト→PR→close を Stop hook 連鎖で回す）
- **廃止理由**: 完全自動だと品質・安全のコントロールが難しく、人間承認ゲートを挟む Daily Triage 方式に移行
- **後継**: フェーズ4（Daily Triage メタループ）。Issue を手動で選んで承認してから回す設計
