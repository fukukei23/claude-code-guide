# 04 MCPサーバー — 外部ツールの統合

## MCPとは

**MCP（Model Context Protocol）** は、Claude Codeから外部ツールを利用するための仕組み。

```
Claude Code
  │
  ├─ brave-search MCP ──→ Brave検索API ──→ Web検索結果
  ├─ github MCP ────────→ GitHub API ────→ PR・Issue・ファイル
  ├─ playwright MCP ────→ Chromium ──────→ ブラウザ操作
  ├─ context7 MCP ──────→ Docs API ─────→ ライブラリ文档
  ├─ discord MCP ───────→ Discord API ──→ メッセージ送受信
  └─ mermaid MCP ───────→ Mermaid API ──→ 図表生成
```

MCPサーバーを追加すると、Claude Codeが**そのサーバーのツール**を使えるようになる。各ツールはコンテキストを消費するため、必要なものだけを維持する。

---

## 現在の構成（6サーバー・83ツール）

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

## コンテキスト消費のトレードオフ

| サーバー | ツール数 | トークン | コンテキスト比 |
|---|---|---|---|
| github | 41 | 9.6k | 4.8% |
| brave-search | 6 | 5.5k | 2.8% |
| playwright | 25 | 4.7k | 2.4% |
| context7 | 2 | 1.2k | 0.6% |
| discord | 5 | 0.6k | 0.3% |
| mermaid | 4 | 0.4k | 0.2% |
| **合計** | **83** | **21.4k** | **10.7%** |

- **GitHub**が最も重い（41ツール = 全MCPの半分）
- 以前は9サーバー（~35kトークン）だったが、使用頻度分析で6サーバーに最適化済み

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
