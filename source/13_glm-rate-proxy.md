# 13 GLM Rate Proxy — Claude CodeをZAI/GLMで動かす低コスト運用

> Claude CodeのバックエンドをAnthropicからZAI（GLM-5.1）に切り替えるローカルプロキシの仕組みと運用ガイド。

---

## <a id="overview"></a>概要：なぜプロキシが必要か

Claude Codeは通常、Anthropic APIに直接接続する。しかし `ANTHROPIC_BASE_URL` を差し替えることで、**Anthropic互換APIを持つ別プロバイダ**に向けられる。

```
通常:
Claude Code ────→ api.anthropic.com (Sonnet/Opus)

プロキシ経由:
Claude Code ──→ localhost:8787 (glm-rate-proxy) ──→ api.z.ai (GLM-5.1)
                                                 └──→ api.minimax.io (MiniMax, フォールバック)
```

### コスト比較

| | Claude Max $200/月（サブスク） | ZAI GLM（従量） |
|---|---|---|
| 月間トークン上限 | 約3,000〜3,200万トークン | 制限なし（従量課金） |
| 実質換算 | $200 → 約3,700万トークン相当 | $200で数十億トークン規模 |
| 体感差 | ベースライン | **約77〜190倍**のコスパ |

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
│  1. モデル名を書き換え（claude → GLM-5.1） │
│  2. thinking制御を注入                  │
│  3. 使用量に応じてモデルをダウングレード   │
│  4. ピーク時間帯はMiniMaxに強制切替       │
│  5. 429/502エラー時はMiniMaxにフォールバック│
└─────────────────────────────────────────┘
  │                        │
  ▼                        ▼
api.z.ai              api.minimax.io
(GLM-5.1)             (MiniMax-M2.7)
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
| `normal` | usage < 80% | GLM-5.1 | ZAI |
| `economy` | 80% ≤ usage < 95% | GLM-4.7 | ZAI |
| `emergency` | usage ≥ 95% | GLM-4.7-Flash | ZAI |
| `peak_block` | JST 15:00〜19:00 | MiniMax-M2.7 | MiniMax |

> **ピーク時間帯の理由**: ZAI公式ドキュメントによるとGLM-5.1はピーク時に**3倍の消費レート**で計算される。MiniMaxに逃がすことでZAIクォータを温存する。

### フォールバックチェーン

```
ZAI 429 → GLM-4.7-Flash（emergency）→ MiniMax → 503エラー
ZAI 5xx → MiniMax → 503エラー
```

---

## <a id="thinking"></a>Thinking（思考）モードの動的制御

GLM-5.1はデフォルトで「思考モード」が有効で、内部推論トークンを大量消費する。

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

> **budget_tokensの注意**: これは上限であり、モデルが必ず使い切るわけではない。ただしGLM-5.1が上限を守るかは未検証。16,000以上は暴走リスクあり。

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
  "last_actual_model": "glm-5.1"
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
  "default_model": "GLM-5.1",
  "thresholds": {
    "normal":    {"max_pct": 80,  "model": null},
    "economy":   {"max_pct": 95,  "model": "GLM-4.7"},
    "emergency": {"max_pct": 100, "model": "GLM-4.7-Flash"}
  },
  "fallback": {
    "provider": "minimax",
    "model": "MiniMax-M2.7"
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

## <a id="related"></a>関連リンク

- [ZAI公式ドキュメント - Deep Thinking](https://docs.z.ai/guides/capabilities/thinking)
- [ZAI公式ドキュメント - GLM-5.1モデル概要](https://docs.z.ai/guides/llm/glm-5.1)
- [Artificial Analysis - GLM-5.1ベンチマーク](https://artificialanalysis.ai/models/glm-5-1)
- [04 MCPサーバー](04_MCPサーバー.md)
- [11 現場の知見](11_現場の知見.md)
