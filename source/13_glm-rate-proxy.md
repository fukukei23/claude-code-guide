# 13 GLM Rate Proxy — Claude CodeをZAI/GLMで動かす低コスト運用

> **⚠️ これはWSL CLI版（Claude Code CLI）専用の仕組みです。**
> Windows Desktopアプリ版はエンドポイントを変更できないため、このプロキシは使用しません。Windows版でGLM/MiniMaxを使う場合は [04_MCPサーバー](04-mcp.html#glm) のglm/minimax MCPを参照してください。

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

使用量（`usage_pct`）に応じて自動でモデルが切り替わる。

| モード | 条件 | 使用モデル | プロバイダ |
|---|---|---|---|
| `normal` | usage < 80% | GLM-5.3 | ZAI |
| `economy` | 80% ≤ usage < 95% | GLM-4.7 | ZAI |
| `emergency` | usage ≥ 95% | GLM-4.7-Flash | ZAI |
| `peak_block` | JST 15:00〜18:59（15時台〜18時台・`15≦hour<19`） | MiniMax-M3 | MiniMax |

> **ピーク時間帯の理由**: ZAI公式ドキュメント（[usage-revision](https://docs.z.ai/devpack/notice/usage-revision)・2026-08-17確認）によるとGLM-5.3はピーク時に**3倍の消費レート**（オフピークは1倍・ピーク=月〜金 14:00-18:00 UTC+8）で計算される。MiniMaxに逃がすことでZAIクォータを温存する。

### フォールバックチェーン

```
ZAI 429 → GLM-4.7-Flash（emergency）→ MiniMax keys[0] → MiniMax keys[1] → 503
ZAI 5xx → MiniMax keys[0] → MiniMax keys[1] → 503

MiniMax 429/401/403 → 次キーへ連鎖（Pro→旧）
MiniMax 2キー両方 429/401/403 → 503
```

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

`config/config.json` で制御可能（2026-08-15時点の現行構成: **glm-5.3 をprimary**に切替・MiniMaxにM3追加・`last_actual_model`等の実測ラベルは自動記録）：


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
  "last_actual_model": "glm-5.3"
}
```

| フィールド | 意味 |
|---|---|
| `usage_pct` | ZAIの月間クォータ消費率（%） |
| `mode` | 現在のルーティングモード |
| `provider` | 次のリクエストの送信先 |
| `peak_block` | ピーク時間帯ブロック中かどうか |
| `last_actual_model` | 直近のリクエストで実際に使われたモデル |

---

## <a id="start-stop"></a>起動・停止

```bash
# 起動（SessionStart hookで自動実行されるが、手動でも可）
bash ~/.claude/scripts/llm/start-glm-proxy.sh

# プロセス確認
pgrep -a -f glm_rate_proxy

# 停止
pkill -f glm_rate_proxy

# ログ確認
tail -f /tmp/glm-proxy.log
```

### ピークブロックを一時的に無効化

```bash
# 環境変数でピークブロック無効化
GLM_PEAK_BLOCK=false bash ~/.claude/scripts/llm/start-glm-proxy.sh
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

- `usage_pct` が80%超 → `economy`モードに自動切替済みのはず
- 95%超 → `emergency`モード（GLM-4.7-Flash）に切替済みのはず
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
    "normal":    {"max_pct": 80,  "model": null},
    "economy":   {"max_pct": 95,  "model": "GLM-4.7"},
    "emergency": {"max_pct": 100, "model": "GLM-4.7-Flash"}
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
- [11 現場の知見](11_現場の知見.md)
