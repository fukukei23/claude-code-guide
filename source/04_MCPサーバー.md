# 04 MCPサーバー — 外部ツールの統合

## MCPとは

**MCP（Model Context Protocol）** は、Claude Codeから外部ツールを利用するための仕組み。

```
Claude Code
  │
  ├─ glm MCP ───────────→ GLM-5.1 API ──→ LLM呼び出し（メイン）
  ├─ minimax MCP ───────→ MiniMax API ──→ LLM呼び出し（フォールバック）
  ├─ brave-search MCP ──→ Brave検索API ──→ Web検索結果
  ├─ github MCP ────────→ GitHub API ────→ PR・Issue・ファイル
  ├─ playwright MCP ────→ Chromium ──────→ ブラウザ操作
  ├─ context7 MCP ──────→ Docs API ─────→ ライブラリドキュメント
  ├─ discord MCP ───────→ Discord API ──→ メッセージ送受信
  └─ mermaid MCP ───────→ Mermaid API ──→ 図表生成
```

MCPサーバーを追加すると、Claude Codeが**そのサーバーのツール**を使えるようになる。各ツールはコンテキストを消費するため、必要なものだけを維持する。

---

## 現在の構成（8サーバー・119ツール）

### <a id="glm"></a>glm（19ツール）

**Claude CodeのメインLLM**。glm-rate-proxy（localhost:8787）経由でZAI API（GLM-5.1等）を呼び出す。LLMルーティングポリシーに従い、Sonnet直接回答の代わりにこのMCPを使う。

| ツール | 用途 |
|---|---|
| `glm_ask` | 汎用LLM呼び出し（最も頻繁に使う） |
| `glm_generate_code` | コード生成 |
| `glm_review_code` | コードレビュー |
| `glm_explain_code` | コード説明 |
| `glm_refactor_suggest` | リファクタリング提案 |
| `glm_debug_error` | エラーデバッグ |
| `glm_generate_tests` | テスト生成 |
| `glm_security_audit` | セキュリティ監査 |
| `glm_analyze_file` | ファイル分析 |
| `glm_generate_docs` | ドキュメント生成 |
| `glm_write_readme` | README生成 |
| `glm_write_document` | 汎用ドキュメント作成 |
| `glm_write_dockerfile` | Dockerfile生成 |
| `glm_design_api` | API設計 |
| `glm_optimize_sql` | SQL最適化 |
| `glm_generate_regex` | 正規表現生成 |
| `glm_generate_changelog` | CHANGELOG生成 |
| `glm_git_commit_message` | コミットメッセージ生成 |
| `glm_translate` | 翻訳 |

**使いどころ**: Sonnet直接回答の代替（LLMルーティングポリシー参照）。コード生成・レビュー・説明など開発全般。  
**注意**: glm-rate-proxy が起動していないと接続不可。`curl http://127.0.0.1:8787/proxy/status` で確認。→ [13_glm-rate-proxy](13_glm-rate-proxy.md)

> **実装**: `~/.claude/scripts/mcp/glm-mcp-server.py` — 外部パッケージではなく自作のPythonスクリプト。起動は `start-glm-mcp.sh` 経由で `.secrets.env` からAPIキーを読み込む。
> **環境別の扱い**: Windows Desktop版では `claude_desktop_config.json` から自動起動。WSL CLI版には登録されているが、CLI自体がglm-rate-proxy経由でGLMで動作しているため実際には不要（二重呼び出しになる）。将来LLMプロバイダーが変わった場合は要否を再評価すること。

---

### <a id="minimax"></a>minimax（17ツール）

**GLMのフォールバックLLM兼大量処理専用**。GLM失敗時・ピーク時間帯（15〜19時）・大量処理タスクに自動委譲される。自作Pythonスクリプトとして実装。

| ツール | 用途 |
|---|---|
| `minimax_ask` | 汎用LLM呼び出し |
| `minimax_summarize_file` | ファイル要約 |
| `minimax_summarize_url` | URL要約 |
| `minimax_translate_file` | ファイル翻訳 |
| `minimax_extract_keywords` | キーワード抽出 |
| `minimax_convert_format` | フォーマット変換 |
| `minimax_clean_data` | データクリーニング |
| `minimax_generate_test_data` | テストデータ生成 |
| `minimax_generate_schema` | スキーマ生成 |
| `minimax_write_email` | メール文面生成 |
| `minimax_log_analysis` | ログ分析 |
| `minimax_error_group` | エラーグルーピング |
| `minimax_diff_summary` | diff要約 |
| `minimax_diff_releases` | リリース差分比較 |
| `minimax_batch_process` | バッチ処理 |
| `minimax_env_check` | 環境チェック |
| `minimax_cron_helper` | cron設定補助 |

**使いどころ**: 要約・フォーマット変換・テストデータ生成・メール文面・キーワード抽出など大量処理タスク。GLM失敗時のフォールバック。

> **実装**: `~/.claude/scripts/mcp/minimax-mcp-server.py` — 自作のPythonスクリプト。Windows Desktop版・WSL CLI版の両環境で実用。起動は `start-minimax-mcp.sh` 経由。

---

### <a id="brave-search"></a>brave-search（6ツール / ~5.5kトークン）

Web検索に関する各種機能。

| ツール | 用途 |
|---|---|
| `brave_web_search` | 一般的なWeb検索 |
| `brave_image_search` | 画像検索 |
| `brave_video_search` | 動画検索 |
| `brave_news_search` | ニュース検索 |
| `brave_local_search` | ローカルビジネス検索 |
| `brave_summarizer` | 検索結果のAI要約 |

**使いどころ**: 最新情報の調査、エラーの検索、技術記事の検索

> **起動方法**: `~/.claude/scripts/mcp/start-brave-search.sh` — `.secrets.env` から `BRAVE_API_KEY` を読み込んで `brave-search-mcp-server` を起動。

### <a id="github"></a>github（41ツール / ~9.6kトークン）

最もツール数が多いサーバー。GitHub上のあらゆる操作が可能。

| カテゴリ | ツール例 |
|---|---|
| PR操作 | `create_pull_request`, `merge_pull_request`, `pull_request_read`, `update_pull_request` |
| Issue操作 | `issue_read`, `issue_write`, `list_issues`, `search_issues` |
| ファイル操作 | `get_file_contents`, `create_or_update_file`, `push_files`, `delete_file` |
| コミット | `get_commit`, `list_commits` |
| 検索 | `search_code`, `search_repositories`, `search_users`, `search_pull_requests` |
| レビュー | `pull_request_review_write`, `add_comment_to_pending_review`, `request_copilot_review` |
| その他 | `create_branch`, `create_repository`, `fork_repository`, `run_secret_scanning` |

**使いどころ**: PR作成、Issue管理、コード検索、リポジトリ操作

> **起動方法**: `~/.claude/scripts/mcp/start-github.sh` — `.secrets.env` から `GITHUB_TOKEN` 等を読み込んで `github-mcp-server` を起動。

### <a id="playwright"></a>playwright（25ツール / ~4.7kトークン）

ブラウザの自動操作。

| カテゴリ | ツール例 |
|---|---|
| ナビゲーション | `browser_navigate`, `browser_navigate_back`, `browser_tabs` |
| 操作 | `browser_click`, `browser_type`, `browser_hover`, `browser_drag` |
| フォーム | `browser_fill_form`, `browser_select_option`, `browser_file_upload` |
| 情報取得 | `browser_snapshot`, `browser_take_screenshot`, `browser_console_messages` |
| ネットワーク | `browser_network_requests`, `browser_network_request` |
| 高度な操作 | `browser_evaluate`, `browser_run_code_unsafe` |

**使いどころ**: Webアプリのテスト、UI確認、スクレイピング

### <a id="context7"></a>context7（2ツール / ~1.2kトークン）

ライブラリの公式ドキュメント検索。

| ツール | 用途 |
|---|---|
| `resolve-library-id` | ライブラリ名からIDを解決 |
| `query-docs` | ドキュメントを検索・取得 |

**使いどころ**: ライブラリの最新API確認、使用方法の調査

### <a id="discord"></a>discord（5ツール / ~0.6kトークン）

Discordとの連携。

| ツール | 用途 |
|---|---|
| `reply` | メッセージ送信 |
| `fetch_messages` | メッセージ履歴取得 |
| `edit_message` | メッセージ編集 |
| `react` | リアクション追加 |
| `download_attachment` | 添付ファイルダウンロード |

**使いどころ**: Discord経由での通知、メッセージ監視

### <a id="mermaid"></a>mermaid（4ツール / ~0.4kトークン）

図表の生成。

| ツール | 用途 |
|---|---|
| `get_diagram` | 図のテンプレート取得 |
| `get_diagram_examples` | 図の例を取得 |
| `list_diagrams` | 対応図の種類一覧 |
| `readme` | ツールの説明 |

**使いどころ**: フローチャート、シーケンス図、クラス図の生成

---

## 環境別の対応（WSL CLI / Windows Desktop）

一部のMCPサーバーは実行環境によって役割・有無が異なる：

| サーバー | WSL CLI版 | Windows Desktop版 | 備考 |
|---|---|---|---|
| glm | ❌ 不要 | ✅ あり | WSL CLI版はClaude Code自体がGLM経由で動作するため、さらにglm MCPを呼ぶ必要がない |
| minimax | ✅ あり | ✅ あり | コスト削減で明示的に呼び出し（要約・翻訳・データ処理等） |
| brave-search | ✅ | ✅ | 共通 |
| github | ✅ | ✅ | 共通 |
| playwright | ✅ | ✅ | 共通 |
| context7 | ✅ | ✅ | 共通 |
| discord | ✅ | ✅ | 共通 |
| mermaid | ✅ | ✅ | 共通 |

> **補足**: WSL CLI版はClaude Code自体のエンドポイントがglm-rate-proxy経由でGLMを指しているため、セッション全体がすでにGLMで動作している。その中でglm MCPをさらに呼ぶのは二重になるため不要。Windows Desktop版はSonnetで動作するため、GLMに委譲する手段としてglm MCPが有効。
>
> **将来変更の可能性**: 現在はGLMだが、プロバイダー乗り換えやコスト変化でルーティング先が変わる可能性がある。その場合はglm MCPの要否を再評価すること。変更はglm-rate-proxyの向き先を変えるだけでCLI全体に反映される。

---

## セキュリティ: APIキーの管理

全MCPサーバーは `~/.secrets.env` からAPIキーを読み込むラッパースクリプト経由で起動する。**settings.jsonにAPIキーを直接記載しない。**

```
settings.json
  └ command: "bash ~/.claude/scripts/mcp/start-<name>.sh"
       │
start-<name>.sh
  └ source ~/.secrets.env   ← APIキーはここから読み込む
  └ exec <本体スクリプト>
```

---

## コンテキスト消費のトレードオフ

| サーバー | ツール数 | 備考 |
|---|---|---|
| glm | 19 | メインLLM委譲用・Windows Desktopのみ実用（CLI版は不要） |
| minimax | 17 | コスト削減用LLM・両環境 |
| github | 41 | 最もツール数が多い |
| brave-search | 6 | ~5.5kトークン |
| playwright | 25 | ~4.7kトークン |
| context7 | 2 | ~1.2kトークン |
| discord | 5 | ~0.6kトークン |
| mermaid | 4 | ~0.4kトークン |
| **合計** | **119** | |

- **GitHub**が最も重い（41ツール = 全MCPの3分の1強）
- GLM/MiniMaxはLLM委譲用の特殊サーバー（他のMCPとは性質が異なる）
- 以前は9サーバー（~35kトークン）だったが、使用頻度分析で最適化済み

> **現場の知見**: MCPツールは呼び出した時だけコストが発生するわけではない。**ツール定義だけで毎ターン消費**される。使っていないサーバーを残すと、1ターンごとに無駄なトークンを消費し続ける。→ [11_現場の知見](11_現場の知見.md#a-コンテキスト経済学)

---

## サーバーの追加・削除

### 追加

```bash
claude mcp add <サーバー名> -- <コマンド>
```

### 削除

```bash
claude mcp remove <サーバー名>
```

### 確認

```bash
claude mcp list
```

**注意**: `settings.json` だけでなく `~/.claude.json` の両方から削除する必要がある場合がある（2ファイル問題）。

---

## MCPツール使い分けガイド

詳細な使い分け基準は別ドキュメントを参照:

→ `00_SYSTEM/MCPツール使い分けガイド.md`

---

## 次の章

- **[05_フック](05_フック.md)** — フックの仕組み
- **[00_早見表](00_早見表.md)** — 全機能のチートシートに戻る

## 関連

- [Claude-Code完全ガイド作成](../../01_DECISIONS/claude-code/2026-05-20_Claude-Code完全ガイド作成.md) — ガイド全体の設計と作成
- [MCP設定削減2回目](../../01_DECISIONS/claude-code/2026-05-20_MCP設定削減2回目.md) — MCP使用頻度分析に基づく削減
- [MCP-10ツール一括追加](../../01_DECISIONS/claude-code/2026-04-30_MCP-10ツール一括追加.md) — MCPツールの大規模追加
