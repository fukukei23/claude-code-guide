# 13 GLM Rate Proxy — Claude CodeをZAI/GLMで動かす低コスト運用

> 💡 **章の核**: プロキシはLLMコストの調整弁。止まったらproxy-doctorで診断。


> **⚠️ 旧記述の訂正（2026-10-14）**: 以前は「Windows Desktopアプリ版はエンドポイント変更できないため本プロキシは使用しない」だったが、**Anthropicが2026-07-09にthird-party inferenceモードをGA化**したことでDesktop側もGateway接続（Developer Mode → Configure Third-Party Inference）で本プロキシに接続可能になった。本環境でも主力Desktop移行Phase 0でDesktop側が本プロキシを使用中（Windows localhost:8787 → portproxy(v6tov4) → WSL 127.0.0.1:8787・正典: [LLMルーティングSSOT](../共通ルール/LLMルーティング.md)）。Desktop側でのLLM呼出運用は実行指示書 `70_PROMPTS/coding/windows-desktop-glm-review.md` 参照。MCP（glm/minimax）は併用可能な補完経路（[04_MCPサーバー](04-mcp.html#glm)）。

Claude Code CLIのバックエンドをAnthropicからZAI（GLM-5.3）に切り替えるローカルプロキシの仕組みと運用ガイド。

---

## <a id="overview"></a>概要：なぜプロキシが必要か

Claude Codeは通常、Anthropic APIに直接接続する。しかし `ANTHROPIC_BASE_URL` を差し替えることで、**Anthropic互換APIを持つ別プロバイダ**に向けられる。

```
通常:
Claude Code ────→ api.anthropic.com (Sonnet/Opus)

プロキシ経由:
Claude Code ──→ localhost:8787 (glm-rate-proxy) ──→ api.z.ai (GLM-5.3)
                                                 └──→ api.minimax.io (MiniMax, フォールバック)
```

### コスト比較

| | Claude Pro $19/月 | Claude Max $200/月 | ZAI Lite $18/月 | ZAI Pro $72/月 | ZAI Max $160/月 |
|---|---|---|---|---|---|
| Claude Pro比の利用量 | 1x（基準） | 20x | 3x | 15x | 60x |
| 月額（USD） | $19 | $200 | $18 | $72 | $160 |
| コスパ（1xあたり） | $19 | $10 | $6 | $4.8 | $2.7 |

> **ポイント**: ZAI Max（$160/月）でClaude Max（$200/月）の**約3倍**の利用量を使える。ZAIは月額サブスク制で、5時間・週単位のローリング制限あり（従量課金ではない）。

---

## <a id="architecture"></a>アーキテクチャ

```
settings.json
  └─ ANTHROPIC_BASE_URL: "http://127.0.0.1:8787"

Claude Code（CLI）
  │  Anthropic形式のAPIリクエスト
  ▼
┌─────────────────────────────────────────┐
│         glm-rate-proxy (port 8787)      │
│                                         │
│  1. モデル名を書き換え（claude → GLM-5.3） │
│  2. thinking制御を注入                  │
│  3. 使用量に応じてモデルをダウングレード   │
│  4. ピーク時間帯はMiniMaxに強制切替       │
│  5. MiniMaxフォールバック(2アカウント)    │
│     - keys[0]=MINIMAX_API_KEY(Pro優先・大量消費) │
│     - keys[1]=MINIMAX_API_KEY_FALLBACK(旧・5h制限) │
│     - 429/401/403で次キーへ連鎖           │
│     - 起動ログでkeys=2確認                 │
└─────────────────────────────────────────┘
  │                        │
  ▼                        ▼
api.z.ai              api.minimax.io
(GLM-5.3)             (MiniMax-M3)
```

### ファイル構成

```
~/.claude/scripts/glm-rate-proxy/
├── src/glm_rate_proxy/
│   ├── proxy.py          # メインプロキシ処理・thinking制御
│   ├── config.py         # 設定読み込み（DEFAULTS + config.json）
│   ├── model_router.py   # モデル選択ロジック（使用量・ピーク判定）
│   ├── upstream.py       # ZAI/MiniMaxへのHTTP通信
│   └── usage_tracker.py  # 使用量トラッキング
├── config/
│   └── config.json       # ユーザー設定（DEFAULTSを上書き）
└── service/
    └── glm-rate-proxy.service  # systemdサービス定義
```

---

## <a id="model-routing"></a>モデルルーティング

使用量（`usage_pct` = **max(5h%, 週間%)**）に応じて自動でモデルが切り替わる。

> **使用率の取得方法（2026-08-17刷新）**: ZAI はレスポンスヘッダに rate limit 情報を返さないため、プロキシが ZAI monitor API（`GET /api/monitor/usage/quota/limit`・サブスク管理UIの内部API）を**60秒間隔でポーリング**して 5h% と週間% を取得する。`/proxy/status` の `usage_5h_pct` / `usage_week_pct` で内訳を確認できる。

| モード | 条件 | 使用モデル | プロバイダ |
|---|---|---|---|
| `manual` | `POST /proxy/mode` で手動指定中（全モード優先・2026-08-19追加） | MiniMax-M3 | MiniMax |
| `normal` | usage < 95% | GLM-5.3 | ZAI |
| `emergency` | usage ≥ 95% | MiniMax-M3 | MiniMax |
| `peak_block` | JST 15:00〜18:59（15時台〜18時台・`15≦hour<19`） | MiniMax-M3 | MiniMax |

> **⚠️ 2026-10-13更新**: `fallback`/`emergency`/`peak_block` のMiniMaxモデルは **`MiniMax-M3.1-Flash-Preview`** へ載せ替え済み（config `dc51c6f`・effort非転送=省略max動作・上表の「MiniMax-M3」は載せ替え前の記録）。詳細: [01_DECISIONS/2026-10-13_MiniMax-M3.1-Flash-Preview採用-proxyモデル載せ替え](../../01_DECISIONS/claude-code/2026-10-13_MiniMax-M3.1-Flash-Preview採用-proxyモデル載せ替え.md)

### 手動モード切替（2026-08-19追加）

GLM使用率が枯渇しそうな時など、**再起動なし**で「今日はMiniMax固定」に切り替える:

```bash
# MiniMaxへ固定（TTL 10時間・既定8・上限72・期限切れで自動auto復帰）
curl -X POST http://127.0.0.1:8787/proxy/mode -d '{"provider":"minimax","hours":10}'
# 通常運用へ戻す
curl -X POST http://127.0.0.1:8787/proxy/mode -d '{"provider":"auto"}'
# 状態確認（manual_provider / manual_expires_at）
curl -s http://127.0.0.1:8787/proxy/status
```

manual=minimax中はpeak時間帯・使用率しきい値を無視して全リクエストがMiniMax-M3へ。状態は `/tmp/glm-rate-proxy-manual.json` に永続化（クラッシュ→systemd再起動でも意図維持）・期限30分前にWARNINGログ。詳細: [01_DECISIONS/2026-08-19_glm-rate-proxy手動モードAPI実装完走](../../01_DECISIONS/claude-code/2026-08-19_glm-rate-proxy手動モードAPI実装完走-peak最後の砦.md)

**manual=glm（2026-09-04追加）**: `proxy-mode.sh glm` で peak_block（JST 15-19時・クォータ保護）中のみGLMへ強制。**peak_block外は無効**（autoと同じ＝戻し忘れても19時に自然解除）。GLMが429を返した場合はpeak_block専用分岐を迂回し通常チェーン（MiniMax→4.7-Flash）へ逃がすため保険は維持。トリガー: 「今夜はGLM」「GLMにして」。詳細: [01_DECISIONS/2026-09-04_peak_block中手動GLM切替-provider-glm拡張](../../01_DECISIONS/claude-code/2026-09-04_peak_block%E4%B8%AD%E6%89%8B%E5%8B%95GLM%E5%88%87%E6%9B%BF-provider-glm%E6%8B%A1%E5%BC%B5.md)

> **日常の切替は `proxy-mode` スキル経由が正規経路（2026-08-20追加）**: 「今夜はミニマックス」「GLMに戻して」等の日本語発話で `~/bin/proxy-mode.sh`（on/off/status・時間帯ガード付き翌朝6時計算・calc-test内蔵）が実行される。curl直打ちよりスキル経由を推奨（時間計算ミス・コマンド打ち間違いを機械的に排除）。詳細: `skills/proxy-mode/SKILL.md`
> **⚠️ status-first規則（2026-09-20追加）**: 切替系・確認系発話（「GLMに変更して」「今のモデルは？」等）では、CCは**応答前に必ず `proxy-mode.sh status` を実行して実効providerを実測**する（起動時ラベル・バッジは実エンジン保証にならないため・2026-09-18/19の「すでにGLM動作中」誤応答2日連続反復の再発防止）。詳細: `skills/proxy-mode/SKILL.md` の status-first規則節

> **economy 段（80-95%）は2026-08-17に廃止**: 95%までは GLM-5.3 のまま使い切る方針（ユーザー確定）。

> **ピーク時間帯の理由**: ZAI公式ドキュメント（[usage-revision](https://docs.z.ai/devpack/notice/usage-revision)・2026-08-17確認）によるとGLM-5.3はピーク時に**3倍の消費レート**（オフピークは1倍・ピーク=月〜金 14:00-18:00 UTC+8）で計算される。MiniMaxに逃がすことでZAIクォータを温存する。

### フォールバックチェーン（2026-08-17改訂・順序入れ替え）

```
ZAI 429 → MiniMax keys[0](Pro) → MiniMax keys[1](旧) → GLM-4.7-Flash（ZAI無料枠・最後の砦）→ 503（Retry-After: 600）
ZAI 5xx → MiniMax keys[0] → MiniMax keys[1] → 503

MiniMax 429/401/403 → 次キーへ連鎖（Pro→旧）
MiniMax 2キー両方 429/401/403 → GLM-4.7-Flash（ZAI）へ → それでもダメなら 503
peak_block中にMiniMax 2キー全滅 → GLM-4.7-Flash（60sタイムアウト付き1回）→ 503（2026-08-19改訂）
```

> **順序入れ替えの理由**: MiniMax-M3（高性能・月額サブスク枠）を先に使い、GLM-4.7-Flash（無料・無制限）を最後の砦にする方針（ユーザー確定・2026-08-17）。

> **✅ MiniMax 2アカウント対応（2026-07-27追加）**
> Pro（大量消費）と旧（安全網）の2アカウント運用。起動ログ `keys=2` で確認。
> フォールバック連鎖: `request_minimax` 内で Pro(MINIMAX_API_KEY)→旧(MINIMAX_API_KEY_FALLBACK) の429/401/403で次キーへ。状態管理不要・自動復帰。詳細: [01_DECISIONS/2026-07-27_glm-rate-proxy-MiniMax2アカウント-Pro優先フォールバック](../../01_DECISIONS/claude-code/2026-07-27_glm-rate-proxy-MiniMax2%E3%82%A2%E3%82%AB%E3%82%A6%E3%83%B3%E3%83%88-Pro%E5%84%AA%E5%85%88%E3%83%95%E3%82%A9%E3%83%BC%E3%83%AB%E3%83%90%E3%83%83%E3%82%AF.md)

> **✅ 週間制限時のフォールバック実機確認済（2026-07-11）**
> ZAIの**週間**制限到達で429が返っても、上記チェーン通りMiniMax-M3へ自動フォールバックすることを仕様+実機で確認（MiniMax API単体疎通テスト HTTP 200・`proxy.py:115-173`）。`usage_pct`は5時間窓の値で、週間累計（ZAIダッシュボード）とは別物。詳細: [01_DECISIONS/2026-07-11_glm-rate-proxy週間制限時フォールバック実機確認](../../01_DECISIONS/claude-code/2026-07-11_glm-rate-proxy週間制限時フォールバック実機確認.md)

> **⚠️ 重要な制限: コンテキスト上限到達時はフォールバックが発動しない**
>
> Claude Codeのコンテキストウィンドウが上限に達した場合、**APIリクエストを送る前にClaude Code本体が判定してエラーを返す**。そのためglm-rate-proxyにリクエストが届かず、MiniMaxへのフォールバックも発動しない。
>
> ```
> 通常時: Claude Code → glm-rate-proxy → GLM（→ エラー時MiniMax）
> 上限時: Claude Code → （本体がAPIリクエストを送らずエラー）← プロキシに届かない
> ```
>
> **対策**: コンテキストが溜まってきたら早めに `/compact` または `/new-session` で切り替える。80%を超えたら `/new-session` 推奨。

---

## <a id="thinking"></a>Thinking（思考）モードの動的制御

GLM-5.3はデフォルトで「思考モード」が有効で、内部推論トークンを大量消費する。

### 問題

- 「このファイルも確認が必要」という1行のために **16,000トークンの内部思考**を消費した例あり
- 全体として **平均LLMの2.6倍**の冗長さ（Artificial Analysis実測）

### 解決策：キーワードベースの動的切り替え

プロキシがリクエストのメッセージ内容を見て自動判断する。

```
メッセージに以下のキーワードが含まれる場合 → Thinking ON（budget: 8,000トークン）
  edit / fix / implement / debug / write / refactor
  create / add / modify / update / build / test / generate

それ以外（質問・説明・要約など）→ Thinking OFF
```

### thinking設定のパラメータ

`config/config.json` で制御可能：

```json
{
  "thinking": {
    "mode": "auto",
    "budget_tokens": 8000
  }
}
```

| `mode` | 動作 |
|---|---|
| `"auto"` | キーワード判定（デフォルト） |
| `"always_on"` | 全リクエストでThinking ON |
| `"always_off"` | 全リクエストでThinking OFF |

> **budget_tokensの注意**: これは上限であり、モデルが必ず使い切るわけではない。ただしGLM-5.3が上限を守るかは未検証。16,000以上は暴走リスクあり。

---

## <a id="status"></a>ステータス確認

```bash
# プロキシの状態確認
curl -s http://127.0.0.1:8787/proxy/status | python3 -m json.tool
```

```json
{
  "usage_pct": 23.5,
  "request_count": 1016,
  "mode": "normal",
  "provider": "zai",
  "peak_block": false,
  "last_actual_model": "glm-5.3",
  "usage_5h_pct": 23.5,
  "usage_week_pct": 12.1,
  "monitor_error_count": 0,
  "monitor_last_error": null
}
```

| フィールド | 意味 |
|---|---|
| `usage_pct` | 使用率 = **max(5h%, 週間%)**（ルーティング判定に使用） |
| `usage_5h_pct` | 5時間制限の使用率（monitor API取得・2026-08-17追加） |
| `usage_week_pct` | 週間制限の使用率（monitor API取得・2026-08-17追加） |
| `monitor_error_count` / `monitor_last_error` | monitor API の取得エラー状況（0/null が正常） |
| `mode` | 現在のルーティングモード |
| `provider` | 次のリクエストの送信先 |
| `peak_block` | ピーク時間帯ブロック中かどうか |
| `last_actual_model` | 直近のリクエストで実際に使われたモデル |

---

## <a id="start-stop"></a>起動・停止

```bash
# 起動・再起動（2026-10-15からsystemd統一・直接kill/バックグラウンド直接起動は禁止）
systemctl --user start glm-rate-proxy.service
systemctl --user restart glm-rate-proxy.service

# start-glm-proxy.sh も使える（systemdラッパー・内部はsystemctl経由）
bash ~/.claude/scripts/llm/start-glm-proxy.sh

# プロセス確認
pgrep -a -f glm_rate_proxy

# 停止
systemctl --user stop glm-rate-proxy.service

# ログ確認
journalctl --user -u glm-rate-proxy -f
```

> ⚠️ 直接killやバックグラウンド直接起動は systemd 非管理の野良インスタンスを生み、bind失敗無限ループの原因になる（2026-10-14事故・詳細: 01_DECISIONS/claude-code/2026-10-15_プロキシ野良インスタンス事故とstart-glm-proxy.sh遺物.md）。unit側ExecStartPreがhealthyな別インスタンスを検知すると起動を拒否する（exit 75）。

### ピークブロックを一時的に無効化

```bash
# 環境変数はunit経由では渡らない・peak_blockはconfig.jsonまたはproxy-mode.shで制御
bash ~/bin/proxy-mode.sh status
```

---

## <a id="troubleshooting"></a>トラブルシューティング

### ❌ Claude Codeが「API error」を返す

**確認手順:**

```bash
# 1. プロキシが起動しているか
pgrep -a -f glm_rate_proxy

# 2. ポートが開いているか
curl -s http://127.0.0.1:8787/proxy/status

# 3. settings.jsonのBASE_URLが正しいか
grep ANTHROPIC_BASE_URL ~/.claude/settings.json
```

**解決:**
```bash
# プロキシを再起動
pkill -f glm_rate_proxy
bash ~/.claude/scripts/llm/start-glm-proxy.sh
```

---

### ❌ 応答が遅い・ハングする

**原因候補:**
1. Thinkingモードが暴走している（`budget_tokens`を超えている）
2. ZAIのレート制限に引っかかっている

**確認:**
```bash
# ログでthinking状況を確認（DEBUGレベル要設定）
tail -50 /tmp/glm-proxy.log

# ステータスでpeak_blockを確認
curl -s http://127.0.0.1:8787/proxy/status | python3 -c "import json,sys; d=json.load(sys.stdin); print('mode:', d['mode'], '/ peak:', d['peak_block'])"
```

**応急処置（全ThinkingをOFFに）:**

`config/config.json` の `thinking.mode` を一時的に `"always_off"` に変更してプロキシ再起動。

---

### ❌ レート制限（429）が頻発する

**確認:**
```bash
curl -s http://127.0.0.1:8787/proxy/status | python3 -c "import json,sys; d=json.load(sys.stdin); print('usage:', d['usage_pct'], '%')"
```

- `usage_pct` が95%超 → `emergency`モード（MiniMax-M3）に自動切替済みのはず
- `monitor_error_count` が増え続ける → monitor API 到達障害（usage が前回値固定になる・`monitor_last_error` を確認）
- 429が続く場合 → MiniMaxへのフォールバックが機能しているか `last_actual_model` を確認

**手動でMiniMaxに切り替え:**

`config/config.json` に追加：
```json
{
  "peak_hours": {
    "enabled": true,
    "start_hour": 0,
    "end_hour": 24
  }
}
```
（24時間ピーク扱いにして強制MiniMax）

---

### ❌ MiniMax APIキー変更後に400エラーが出る

**原因**

ピークブロック（JST 15:00–19:00）が有効な状態では全リクエストがMiniMaxに強制ルーティングされる。この時間帯にMiniMaxのAPIキーをリセット・変更すると、プロキシが古いキーを保持したまま稼働し続け、全リクエストが400エラーになってClaude Codeが停止する。

**確認手順**

```bash
# ピークブロック中かどうか確認
curl -s http://127.0.0.1:8787/proxy/status | python3 -c "import json,sys; d=json.load(sys.stdin); print('peak_block:', d['peak_block'], '/ provider:', d['provider'])"

# ログで400エラーを確認
tail -30 /tmp/glm-proxy.log
```

**⚠️ APIキー変更時の手順（必須）**

- [ ] `~/.secrets.env` の `MINIMAX_API_KEY` を新しい値に更新
- [ ] プロキシを再起動して新しいキーを読み込ませる

```bash
# 1. ~/.secrets.env を編集（値はAPIキー管理ポリシーに従い直接記載）
# 2. プロキシ再起動
source ~/.secrets.env
pkill -f glm_rate_proxy
cd ~/.claude/scripts/glm-rate-proxy
PYTHONPATH=src nohup python3 -m glm_rate_proxy > /tmp/glm-proxy.log 2>&1 &
sleep 2
curl http://127.0.0.1:8787/proxy/status
```

**ピークブロック中に緊急回避する場合**

```bash
# ピークブロックを無効化してGLM（ZAI）直結に戻す
pkill -f glm_rate_proxy
source ~/.secrets.env
cd ~/.claude/scripts/glm-rate-proxy
GLM_PEAK_BLOCK=false PYTHONPATH=src nohup python3 -m glm_rate_proxy > /tmp/glm-proxy.log 2>&1 &
```

---

### ❌ `No module named glm_rate_proxy` エラー

プロキシの作業ディレクトリかPYTHONPATHが正しくない。

```bash
# 正しい起動方法
cd ~/.claude/scripts/glm-rate-proxy
PYTHONPATH=src python3 -m glm_rate_proxy
```

---

### ❌ thinking ONなのに効果が感じられない

ZAIの `enabled` モードはモデルが「自動判断」して思考量を決める。`budget_tokens`を上げても体感が変わらない場合、モデル自身が「不要」と判断している可能性がある。

`always_on` + `budget_tokens: 16000` を試すことで強制的に思考を増やせるが、**トークン暴走リスクが上がる**。

---

## <a id="config-reference"></a>設定リファレンス

`config/config.json` の全項目：

```json
{
  "zai_base_url": "https://api.z.ai/api/anthropic",
  "minimax_base_url": "https://api.minimax.io/anthropic/v1",
  "listen_host": "127.0.0.1",
  "listen_port": 8787,
  "upstream_timeout": 1200,
  "log_level": "INFO",
  "default_model": "GLM-5.3",
  "thresholds": {
    "normal":    {"max_pct": 95,  "model": null,         "provider": "zai"},
    "emergency": {"max_pct": 95,  "model": "MiniMax-M3", "provider": "minimax"}
  },
  "monitor": {
    "enabled": true,
    "interval_sec": 60,
    "timeout_sec": 10
  },
  "fallback": {
    "provider": "minimax",
    "model": "MiniMax-M3"
  },
  "peak_hours": {
    "enabled": true,
    "start_hour": 15,
    "end_hour": 19,
    "timezone_offset": 9
  },
  "thinking": {
    "mode": "auto",
    "budget_tokens": 8000,
    "coding_keywords": [
      "edit", "fix", "implement", "debug", "write", "refactor",
      "create", "add", "modify", "update", "build", "test", "generate"
    ]
  }
}
```

---

## <a id="proxy-doctor"></a>proxy-doctor スキル — 診断を自動化する

プロキシが壊れた時の原因調査を自動化する Claude Code スキル。

### できること

- プロセス・ステータス・ログを自動収集して原因を分類
- 10パターン（停止・400/401/429・タイムアウト・99%固定・設定書き換えなど）を診断
- 各パターンへの具体的な対処コマンドを提示（実行はユーザー確認後）
- 複数プロセス起動・32MB上限接近・ZAI直結化などエッジケースも検出

### いつ使うか

「なんか遅い・エラーが出る・フォールバックしない」と思ったら、原因を自分で追わずこのスキルを最初に使う。

### 使い方

CLIセッション内で以下のいずれかを言うとトリガーされる：

```
/proxy-doctor
プロキシ直して
GLMが使えない
400エラーが出る
プロキシを診断して
```

### 出力例

```
## proxy-doctor 診断結果

プロセス      : 起動中 (PID: 354224)
BASE_URL      : http://127.0.0.1:8787（プロキシ経由）
モード        : peak_block
プロバイダ    : minimax
ZAI使用率     : 0.0%
直近リクエスト: 2.1MB
ピークブロック: true

【検出された問題】 パターン J: 正常
【原因】 -

【推奨対処】 なし（正常動作中）
```

---

## 💡 やさしい補足（初心者向け）

- **「プロキシ」= AIを安く使うための中継地点**: 公式の高価なAIに直接つなぐ代わりに、間に安いAIを置いてコストを下げる仕組み
- **この環境の核心**: Claude Code → 中継（プロキシ）→ GLM/MiniMax（安いAI）。これで大幅に節約
- **壊れたら**: AIが反応しない・エラーが出る等は、このプロキシが原因のことが多い。この章の「トラブルシューティング」を参照
- **意識しなくてOK**: 普段は裏で自動で動いている。トラブル時だけこの章を見る

---

## <a id="related"></a>関連リンク

- [ZAI公式ドキュメント - Deep Thinking](https://docs.z.ai/guides/capabilities/thinking)
- [ZAI公式ドキュメント - GLM-5.3モデル概要](https://docs.z.ai/guides/llm/glm-5.3)
- [Artificial Analysis - GLM-5.2ベンチマーク](https://artificialanalysis.ai/models/glm-5-2)（※GLM-5.3版ページは2026-08-17時点で未掲載・404確認済み。5.2が直近の計測対象）
- [04 MCPサーバー](04_MCPサーバー.md)
- [11 現場の知見](12_現場の知見.md)

> 💡 **章の落とし所**: 再起動は全セッション数秒停止とセット——必ず事前警告を。

## 🆘 野良プロセス検知時の手動応答手順（2026-10-20・proxy-norai-check.sh検知時）

1. `pgrep -af glm_rate_proxy` で対象PIDを特定（**PID+起動時刻を記録してからkill**・PID再利用防止）
2. `systemctl --user show -p MainPID glm-rate-proxy.service` と照合し、MainPID以外なら野良確定
3. `kill <野良PID>`（kill -9は最終手段）→ `ss -tlnp | grep 8787` で正規proxyがlisten復帰したか確認
4. 正規unitが死んでいれば `bash ~/projects/claude-config/scripts/llm/start-glm-proxy.sh`（systemctlラッパー）で復旧
5. 検知ログ `~/.claude/state/proxy-norai/log.jsonl` の該当行に対応メモを残す（再発パターン分析用）

機構: PreToolUse gate `proxy-op-gate.sh`（経路A）+ .bashrc wrapper関数（経路B）+ 本checker（定期検知）の3層。
正典: `docs/superpowers/specs/2026-10-15_ボード宣言なしプロキシ操作恒久対策-design.md`
