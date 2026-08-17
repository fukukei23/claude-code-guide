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
【4. 必須】自律実装ループ
        ↓
【5. 自動】完了通知
```

---

## フェーズ1: 品質スイープ

全ファイルを機械的に走査し **High/Medium/Low** リストを生成する（読み取り専用・変更なし）。

| 項目 | 内容 |
|---|---|
| 実行方法 | CronCreate（20分間隔）または手動 |
| チェック内容 | セキュリティ問題・巨大関数（50行超）・重複ロジック・未使用import |
| 出力先 | `01_DECISIONS/<project>/YYYY-MM-DD_リファクタリング調査_<area>.md` |
| いつ使う | 50件超の大規模改善前、定期健全性確認 |

CronCreate 設定例:

```
CronCreate:
  schedule: "*/20 * * * *"
  durable: true
  prompt: |
    <project> のコード品質スイープ。
    未完了エリアを1つ選び全ファイルを読んでHigh/Medium/Lowに分類。
    結果をSSOTに保存。コード変更は一切しない。
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

P1/P2 リストを GitHub Issues に一括登録する。

### タイトル形式

| ラベル | 優先度 | 目安工数 |
|---|---|---|
| `[A]` | priority:low | 1h以下 |
| `[B][C]` | priority:medium | 2〜3h |
| `[D]` | priority:high | 4h以上 |

タイトル例:
```
test: [A] test_xxx.py に scope="function" を明示
fix:  [B] except Exception を具体的な例外型に限定
refactor: [D] test_routes_coverage.py を6ファイルに分割
```

### GitHub API 一括作成

```python
import json, urllib.request

TOKEN = "your_github_token"
REPO = "your_username/your_repo"

issues = [
    {
        "title": "test: [A] xxx",
        "body": "## 概要\n...\n\n## 完了条件\n- pytest 全件パス\n\n## 推定工数: 1h",
        "labels": ["type:test", "priority:low"]
    },
]

for issue in issues:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues",
        data=json.dumps(issue).encode(),
        headers={
            "Authorization": f"token {TOKEN}",
            "Content-Type": "application/json"
        }
    )
    res = json.load(urllib.request.urlopen(req))
    print(f"Created #{res['number']}: {res['title']}")
```

---

## フェーズ4: 自律実装ループ

GitHub Issues を **高→中→低の順に自動実装**する Stop Hook 連鎖方式。

### アーキテクチャ

```
start.sh --auto <repo>
    │
    ▼
state.json: active=true / pending=[76,77,78]
    │
    ▼
claude --print "Issue #76 を実装して..."
    │ セッション終了
    ▼
[Stop Hook 発火] → next-issue.py
    │ completed=[76] / pending=[77,78]
    ▼
claude --print "Issue #77 を実装して..."
    │ ... 繰り返す ...
    ▼
pending=[] → active=false → 完了通知
```

### state.json 構造

```json
{
  "project": "my-project",
  "repo_path": "/path/to/repo",
  "active": true,
  "pending": [76, 77, 78],
  "current": 76,
  "completed": []
}
```

### 起動コマンド

```bash
# Issue番号を指定して実行
bash ~/.claude/scripts/auto-dev/start.sh 76 77 78

# GitHub から priority 順に自動取得
bash ~/.claude/scripts/auto-dev/start.sh --auto my-repo
```

### 夜間・放置実行（CronCreate 方式）

```
CronCreate:
  schedule: "7 * * * *"   # 毎時:07
  durable: true
  prompt: |
    GitHub のオープン Issue を priority:high → medium → low の順で1件実装。
    pytest 全件パス確認 → commit → push → Issue close。
    1セッション1Issue のみ。失敗は最大3回リトライ。
```

| 方式 | 使い分け |
|---|---|
| Stop Hook（start.sh） | 今すぐ連続実行したい |
| CronCreate | 夜間・放置・数日かけて処理 |

### 1 Issue あたりの自動処理

```
実装（LLM でコード生成）
    ↓
pytest 全件パス確認
    ↓
git commit && git push
    ↓
CI 確認
    ↓
Issue close（GitHub API）
    ↓
次の Issue へ（Stop Hook 連鎖）
```

### 緊急停止

```bash
python3 -c "
import json
state_path = '/path/to/state.json'
s = json.load(open(state_path))
s['active'] = False
json.dump(s, open(state_path, 'w'), indent=2)
print('停止:', s)
"
```

---

## フェーズ4.5: Daily Triage & Stale検知（2026-07-24追加）

並行セッションの stale🟢検知と、staleタスクの自動除外ロジックを実装。

### stale判定（⚠staleマーク）

`daily_triage.py` で実装:
- **閾値**: 30日（STALE_DAYS = 30）
- **判定ロジック**: タスクの更新日が30日以上前 → `⚠stale ` プレフィックスを付与
- **理由**: 古い前提で実装AIが空振りするのを防ぐ

```python
# daily_triage.py
STALE_DAYS = 30
_STALE_PREFIX = "⚠stale "

def parse_task_date(text: str) -> date | None:
    # ... (日付抽出ロジック)
    if task_date and (today - task_date).days > STALE_DAYS:
        body = _STALE_PREFIX + body
```

### heartbeat機構

`resume-session` スキル + `check-stale-sessions.sh` で実装:
- **trigger**: SessionStart hook で自動発火
- **検知条件**:
  - `heartbeat_timeout`: 12h超の無活動
  - `handoff_timeout`: handoffのmtimeが古い・heartbeat無し
  - `no_trace`: 証跡ゼロ（6d3f型等）
  - `[長時間]`マーカー付き行は72h閾値
- **対処**: `active-sessions.md` で🟢→✅変更 + `new-session` でhandoff生成

**heartbeat管理**:
- `track-tool-usage.sh` (PostToolUse) が毎ツール使用で `~/.claude/state/heartbeat/$WT4` を touch
- **一次情報源**: `check-stale-sessions.sh --help`

```bash
# 12hを超える🟢行を検知
~/.claude/scripts/obsidian/check-stale-sessions.sh
```

### daily_triage.sh 統合

`daily_triage.py` を CronCreate で定期実行:
```bash
CronCreate:
  schedule: "7 * * * *"   # 毎時:07
  durable: true
  prompt: |
    バックログ.mdからP0/P1未完了タスク抽出。
    stale（30日超）には⚠staleマークを付与。
    結果を 10_DAILY/2026-07-27.md に追記。
```

**Cron管理**: `apply_crons.py` で管理・crons.shで再登録

---

## フェーズ5: 完了通知（自動）

`pending=[]` を検知したら自動実行:

- ターミナルベル音
- OS通知（macOS: `osascript` / Windows: PowerShell toast）

```python
# macOS 例
import subprocess
subprocess.run(["osascript", "-e",
    'display notification "全 Issue 完了" with title "dev-cycle"'])

# Windows (WSL2) 例
subprocess.Popen(["powershell.exe", "-c",
    '$n=New-Object System.Windows.Forms.NotifyIcon; ...'])
```

---

## Phase 5: 別LLMレビュー（実装済み・2026-08-12）

`review_lib.py` に `run_multi_llm_review()` をTDDで実装（設計は3機レビューで確定済み）:

- **レビュアー**: Gemini 3.1-pro + MiniMax-M3 を HTTP直接呼出（`backend_kind` 必須引数で区別）
- **判定3値**: critical / pass / warning・`verify-result.txt` への拒否権（critical≥1でNG）
- **早期abort**: 両ベンダーcriticalで即中止・ベンダー数<2で警告（モデル数でなくベンダー数判定）
- **縮退戦略**: 片系障害→残り1ベンダーで警告付き続行／両系→pending-retry退避

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
| Stop 後に次が起動しない | `active: false` | `start.sh` を再実行 |
| Issue が自動取得されない | ラベルなし | `priority:high/medium/low` ラベルを付与 |
| CI 失敗で詰まる | テストエラー | ログ確認 → 手動対応 → 再起動 |
| 完了通知が来ない | OS 通知の設定 | `notify-done.sh` をデバッグ |

---

## 💡 やさしい補足（初心者向け）

- **「dev-cycle」= コードを自動で良くするサイクル**: 品質チェック→レビュー→修正を、人間が細かく指示しなくても回せる仕組み
- **5つのフェーズ**: ①全体をざっと掃除 ②詳しくレビュー ③問題をリスト化 ④自動で修正 ⑤完了報告
- **人間は見守るだけ**: 始めると最後まで自動で回る。途中で止めたり指示したりも可能
- **使う場面**: 「このプロジェクト、だらしなくなってきたな」を一気に綺麗にしたい時

---

## 実績（参考）

| プロジェクト | 実施内容 | 結果 |
|---|---|---|
| Flask 物販管理システム | Issue #75〜#77 を自律実装 | 3件全自動完了・テスト全件パス |
| 自律型AIフレームワーク | テストカバレッジ 83.81% 達成 | 4,602 テスト通過・0 失敗 |
