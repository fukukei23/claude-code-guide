# 04 MCPサーバー — 外部ツールの統合

## MCPとは

**MCP（Model Context Protocol）** は、Claude Codeから外部ツールを利用するための仕組み。

```
Claude Code
  │
  ├─ brave-search MCP ──→ Brave検索API ──→ Web検索結果
  ├─ github MCP ────────→ GitHub API ────→ PR・Issue・ファイル
  ├─ playwright MCP ────→ Chromium ──────→ ブラウザ操作
  ├─ context7 MCP ──────→ Docs API ─────→ ライブラリドキュメント
  ├─ discord MCP ───────→ Discord API ──→ メッセージ送受信
  ├─ mermaid MCP ───────→ Mermaid API ──→ 図表生成
  ├─ exa MCP ───────────→ Exa API ──────→ セマンティック検索
  ├─ minimax MCP ───────→ MiniMax API ──→ テキスト処理（コスト削減）
  ├─ minimax-official ──→ MiniMax API ──→ 画像・音楽・動画生成
  ├─ minimax-video ─────→ MiniMax API ──→ 動画生成（従量課金）
  ├─ 4_5v_mcp ──────────→ 画像分析AI ───→ 画像診断・UI模写
  └─ web_reader ────────→ URL取得 ──────→ WebページMarkdown化
```

MCPサーバーを追加すると、Claude Codeが**そのサーバーのツール**を使えるようになる。各ツールはコンテキストを消費するため、必要なものだけを維持する。

---

## 現在の構成（12サーバー・125ツール）

### minimax（自作テキスト処理 / 17ツール / ~1kトークン） {#minimax}

**LLM委譲用MCPサーバー（自作・MiniMax-M3使用）**。環境によって役割が異なる。

| 環境 | 役割 |
|---|---|
| **Windows Desktop版** | SonnetがMCP経由でMiniMaxに処理を委譲。glm MCPと同様の位置づけで、GLMとMiniMaxを用途で使い分ける |
| **WSL CLI版** | ① glm-rate-proxyのフォールバック先（GLMがレート制限・エラー時に**自動**切替） ② 明示的にMCPツールとして呼び出すことも可能（要約・翻訳・データ処理等でコスト削減） |

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

**使いどころ**: 要約・フォーマット変換・テストデータ生成・メール文面・キーワード抽出など大量処理タスク。

> **実装**: `~/.claude/scripts/mcp/minimax-mcp-server.py` — 自作Pythonスクリプト（**MiniMax-M3**使用）。glm-rate-proxyの設定ファイル（config.py）でフォールバック先として指定されているが、MCPサーバーとしては**別ファイル**。glm-rate-proxyによる自動フォールバック（ピーク時間15-19時・429/エラー時）とMCPによる明示的呼び出しは独立した仕組み。

---

### minimax-official（公式 / 画像・音楽・動画・10ツール） {#minimax-official}

**MiniMax公式MCPサーバー**。画像・音楽・動画・音声などのメディア生成機能を提供する。自作の `minimax`（テキスト処理特化）とは別サーバー。

| ツール | 用途 |
|---|---|
| `generate_video` | テキストプロンプト or 画像から動画を生成（`MiniMax-Hailuo-02`等） |
| `query_video_generation` | 非同期動画生成タスクのステータス確認 |
| `text_to_image` | テキストから画像を生成（image-01） |
| `text_to_audio` | テキストを音声に変換（TTS） |
| `music_generation` | テキストプロンプトから音楽を生成 |
| `voice_clone` | 音声ファイルからカスタムボイスを作成 |
| `voice_design` | テキスト説明からボイスを生成 |
| `list_voices` | 使用可能なボイス一覧を表示 |
| `play_audio` | 生成した音声ファイルを再生 |
| `image_to_video` | 画像を動画に変換（JS/TS実装のみ） |

**使いどころ**: 「〇〇の動画を生成して」「画像を作って」「BGMを生成して」など、メディア生成タスク全般。
**出力先**: `~/minimax-output/`（WSL内）に自動保存される。

---

### minimax-video（公式 / 動画生成専用・従量課金） {#minimax-video}

**MiniMax公式MCPサーバー（動画生成専用・従量 Cash$ アカウント）**。`minimax-official` と**同じバイナリ**（公式パッケージ `minimax-mcp`）だが、**APIキー（従量課金アカウント）と出力先を分離**した別サーバー。official（無料枠）と使い分けることで、動画生成を大量利用しても無料枠を消費しない。

| 項目 | minimax-official | minimax-video |
|---|---|---|
| バイナリ | 公式 `minimax-mcp` | **同じ**（公式 `minimax-mcp`） |
| APIキー | 無料枠アカウント（`MINIMAX_API_KEY`） | **従量 Cash$**（`MINIMAX_API_KEY_VIDEO`・別アカウント） |
| 出力先 | `~/minimax-output/` | `~/minimax-output-video/` |
| 用途 | メディア生成全般 | 動画生成の大量利用 |

**使いどころ**: 動画生成を大量に行いたい場合。official の無料枠とは課金体系が独立しているため、動画専用に従量アカウントを分けて運用する。

> **実装**: `~/.claude/scripts/mcp/start-minimax-video-mcp.sh` — 公式パッケージ `minimax-mcp` を VIDEO キーで起動（`export MINIMAX_API_KEY="${MINIMAX_API_KEY_VIDEO}"` でマップ）。`minimax-official` と同じバイナリ・別アカウント・別出力先。2026-06-14 追加。

#### minimax系のセットアップ（公式2サーバー）

同一の `minimax-mcp` バイナリを2本起動し、環境変数でAPIキーとアカウントを切り替えて**コスト分離**する構成。

**使い分けのポイント**: 同一バイナリのため `generate_video` 等が両サーバーに生える。**動画生成時は必ず `mcp__minimax-video__generate_video`** を使う（`minimax-official` は Token Plan の動画 quota が枯渇するため）。

- **サーバー登録は `claude mcp add -s user` で `~/.claude.json`（userスコープ）へ。`settings.json` の `mcpServers` は読まれないので注意**（2026-06-15検証済み・下記トラブルシューティング「2層問題」参照）。
  ```bash
  claude mcp add minimax-video -s user -- bash ~/.claude/scripts/mcp/start-minimax-video-mcp.sh
  ```
- 起動スクリプト: `~/.claude/scripts/mcp/start-minimax-official-mcp.sh` / `start-minimax-video-mcp.sh`
- 鍵管理: `~/.secrets.env` の `MINIMAX_API_KEY`（無料枠）/ `MINIMAX_API_KEY_VIDEO`（従量）

**注意**: MCP接続は起動時確立のため、設定変更後は Claude Code の再起動が必要。

---

### brave-search（6ツール / ~5.5kトークン） {#brave-search}

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

### github（41ツール / ~9.6kトークン） {#github}

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

### playwright（25ツール / ~4.7kトークン） {#playwright}

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

### context7（2ツール / ~1.2kトークン） {#context7}

ライブラリの公式ドキュメント検索。

| ツール | 用途 |
|---|---|
| `resolve-library-id` | ライブラリ名からIDを解決 |
| `query-docs` | ドキュメントを検索・取得 |

**使いどころ**: ライブラリの最新API確認、使用方法の調査

### discord（5ツール / ~0.6kトークン） {#discord}

Discordとの連携。

| ツール | 用途 |
|---|---|
| `reply` | メッセージ送信 |
| `fetch_messages` | メッセージ履歴取得 |
| `edit_message` | メッセージ編集 |
| `react` | リアクション追加 |
| `download_attachment` | 添付ファイルダウンロード |

**使いどころ**: Discord経由での通知、メッセージ監視

### mermaid（4ツール / ~0.4kトークン） {#mermaid}

図表の生成。

| ツール | 用途 |
|---|---|
| `get_diagram` | 図のテンプレート取得 |
| `get_diagram_examples` | 図の例を取得 |
| `list_diagrams` | 対応図の種類一覧 |
| `readme` | ツールの説明 |

**使いどころ**: フローチャート、シーケンス図、クラス図の生成

### exa（3ツール / ~1.5kトークン） {#exa}

セマンティックWeb検索。

| ツール | 用途 |
|---|---|
| `web_search_exa` | セマンティックWeb検索（技術記事の深掘り） |
| `web_fetch_exa` | URLの内容をMarkdownで取得（バッチ対応） |

**使いどころ**: 技術記事の深掘り調査、コード検索

### 4_5v_mcp（画像分析 / ~0.8kトークン） {#4-5v-mcp}

AI画像分析。

| ツール | 用途 |
|---|---|
| `analyze_image` | 画像の詳細分析（OCR・レイアウト理解・UI複製用プロンプト生成） |

**使いどころ**: スクリーンショット診断、UI模写、図解理解

### web_reader（1ツール / ~0.5kトークン） {#web-reader}

URL内容取得。

| ツール | 用途 |
|---|---|
| `webReader` | URLをMarkdownに変換（画像保持オプション付き） |

**使いどころ**: Webページ内容の取得、ドキュメント読み込み

---

## 環境別の対応（WSL CLI / Windows Desktop）

一部のMCPサーバーは実行環境によって役割・有無が異なる：

| サーバー | WSL CLI版 | Windows Desktop版 | 備考 |
|---|---|---|---|
| minimax | ✅ あり | ✅ あり | コスト削減で明示的に呼び出し（要約・翻訳・データ処理等） |
| minimax-official | ✅ あり | ✅ あり | 動画・画像・音声生成（Hailuo）。両環境で利用可能 |
| minimax-video | ✅ あり | ✅ あり | 動画生成専用（従量・両環境） |
| brave-search | ✅ | ✅ | 共通 |
| github | ✅ | ✅ | 共通 |
| playwright | ✅ | ✅ | 共通 |
| context7 | ✅ | ✅ | 共通 |
| discord | ✅ | ✅ | 共通 |
| mermaid | ✅ | ✅ | 共通 |
| exa | ✅ | ✅ | 共通 |
| 4_5v_mcp | ✅ | ✅ | 共通 |
| web_reader | ✅ | ✅ | 共通 |
| **glm** | ❌ **不要** | ✅ あり | WSL CLI版は自分自身がGLMで動作。Windows版はSonnet→GLM委譲用（下記参照） |

> **注意**: WSL CLI版はClaude Code自体のエンドポイントがglm-rate-proxy経由でGLMを指しているため、セッション全体がすでにGLMで動作している。その中でglm MCPをさらに呼ぶのは二重になるため不要。Windows Desktop版はSonnetで動作するため、GLMに委譲する手段としてglm MCPが有効。
>
> **将来変更の可能性**: 現在はGLMだが、プロバイダー乗り換えやコスト変化でルーティング先が変わる可能性がある。その場合はglm MCPの要否を再評価すること。変更はglm-rate-proxyの向き先を変えるだけでCLI全体に反映される。

---

## glm（Windows Desktop版用 / WSL CLI版では不要・自作 / ~1kトークン） {#glm}

**LLM委譲用MCPサーバー（自作・GLM-5.2/Z.AI API）**。**WSL CLI版では不要のため「現在の構成（実態12サーバー）」には含まれない**。Windows Desktop版でのみ有効。

| 環境 | 役割 |
|---|---|
| **Windows Desktop版** | SonnetがMCP経由でGLMに処理を委譲。Sonnetがエンドポイントを変更できないため、会話ごとにglm MCPを呼び出してGLMに回答生成を依頼し、Sonnetが最終回答する |
| **WSL CLI版** | Claude Code自体がglm-rate-proxy経由でGLMで動作しているため、このMCPを呼び出すと二重になり**実質不要** |

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

**使いどころ**: Windows Desktop版でコード生成・レビュー・説明など開発全般の処理をGLMに委譲したい場合。
**注意（Windows Desktop版）**: ZAI APIキーが設定されていないと接続不可。
**注意（WSL CLI版）**: glm-rate-proxyが起動していないと接続不可（ただし実際には呼び出す必要がない）。→ [13_glm-rate-proxy](13_glm-rate-proxy.md)

> **実装**: `~/.claude/scripts/mcp/glm-mcp-server.py` — 自作Pythonスクリプト。glm-rate-proxyとは**別ファイル**。glm-rate-proxyはWSL CLI版のエンドポイント制御担当、glm MCPサーバーはMCPプロトコル経由の呼び出し担当。

---

## zernio（導入済み・現在未接続 / ホストMCP / 280+ツール） {#zernio}

**SNS自動投稿MCP**。Instagram/TikTok/X/Facebook/YouTube等15プラットフォーム対応。導入済み・投稿テスト済みだが、**現在は未接続**（必要時に再有効化）。

| カテゴリ | ツール例 |
|---|---|
| 投稿 | `posts_publish_now`, `posts_create`, `posts_cross_post` |
| スケジュール | `posts_create`（日時指定）, `posts_list` |
| 分析 | `get_analytics`, `get_best_time_to_post` |
| DM・コメント | `send_inbox_message`, `reply_to_inbox_post` |
| 広告 | `create_standalone_ad`, `boost_post`, `get_ad_analytics` |
| メディア | `media_generate_upload_link`, `media_check_upload_status` |

**使いどころ**: TikTok/Instagram等への自動投稿、SNS分析、投稿スケジュール管理

**料金**: 最初2アカウント無料 → 3つ目以降 $6/月

**セットアップ**: 公式プラグイン方式で導入（手動の `url` + `headers` + `env` 設定は非推奨 — `${VAR}` 変数展開が動作しない場合あり）

```bash
/plugin marketplace add zernio-dev/zernio-claude-plugin
/plugin install zernio@zernio
# APIキー入力 → システムキーチェーンに保存
```

**投稿テスト結果**（2026-06-13）: 4プラットフォーム（Discord / Instagram / TikTok / YouTube）の下書き投稿・クロス投稿・一覧取得・削除まで全て正常動作を確認。即時投稿（`publish_now=True`）も利用可能。

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

| サーバー | ツール数 | トークン | コンテキスト比 |
|---|---|---|---|
| github | 41 | 9.6k | 4.8% |
| brave-search | 6 | 5.5k | 2.8% |
| playwright | 25 | 4.7k | 2.4% |
| exa | 3 | ~1.5k | ~0.8% |
| context7 | 2 | 1.2k | 0.6% |
| 4_5v_mcp | 1 | ~0.8k | ~0.4% |
| discord | 5 | 0.6k | 0.3% |
| mermaid | 4 | 0.4k | 0.2% |
| web_reader | 1 | ~0.5k | ~0.3% |
| minimax | 17 | ~1k | ~0.5% |
| minimax-official | 10 | ~1k | ~0.5% |
| minimax-video | 10 | ~1k | ~0.5% |
| **合計** | **125** | **~24.8k** | **~12.4%** |

- **GitHub**が最も重い（41ツール = 全MCPの約3割）
- 以前は9サーバー（~35kトークン）だったが、使用頻度分析で最適化後、exa・画像分析・web_readerを追加
- **クイックリファレンス**: [ガイドサイト - MCPサーバーカタログ](https://fukukei23.github.io/guides/claude-code-mcp-catalog/)

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

### トラブルシューティング: 「設定したのに接続されない」（Windows Desktop版）

Windows Desktop版（特に**Microsoft Store版 / サンドボックス化されたインストール**）でMCPサーバーを追加しても一向に接続されない場合、**編集すべき設定ファイルを間違えている**可能性が高い。候補は3つある：

1. `C:\Users\<user>\.claude\settings.json` — CLI/共通設定用
2. `C:\Users\<user>\AppData\Roaming\Claude\claude_desktop_config.json` — 通常版チャットアプリ用
3. `C:\Users\<user>\AppData\Local\Packages\<Claudeのパッケージフォルダ>\LocalCache\Roaming\Claude\claude_desktop_config.json` — **サンドボックス化パッケージキャッシュ内**（Microsoft Store版で実際に使われるのはここ）

**判別方法**: 既に動いている他のMCPサーバーのエントリの `args`（`wsl -d Ubuntu -- bash <path>` のようなコマンド形式）が、UI上の接続ログ（`/mcp` → サーバー詳細）に表示される実際の起動コマンドと一致しているファイルが「本物」。3つの候補に同名・類似のサーバーエントリがあっても、起動コマンドが実際のログと食い違っていれば、それは使われていない古いコピーである。

詳細な調査の経緯: `01_DECISIONS/claude-code/2026-06-07_minimax-official-MCP接続トラブル解決と動画生成成功.md`

### トラブルシューティング: 「設定ファイルの2層問題」（WSL CLI版）

WSL CLI版でMCPサーバーが `Connection closed (-32000)` になる場合、**`settings.json` と `.claude.json` の両方にMCP定義があるか確認**する。

**どちらが使われているか**: `/mcp` → サーバー選択 → 詳細画面の「Config location」で確認。

**よくある原因**:

| 原因 | 症状 | 修正 |
|---|---|---|
| `.claude.json` のパス間違い | `-32000` エラー | `scripts/xxx.py` → `scripts/mcp/xxx.py` |
| `.claude.json` が python3 直接起動 | APIキー未設定でクラッシュ | `bash start-*.sh` 経由に変更（`secrets.env` をsource） |
| 一方だけ修正 | 修正が反映されない | 両ファイルの定義を一致させる |
| glm が WSL CLI で不要なのに有効 | 警告が出る | `disabled: true` を追加 |

**診断コマンド**:
```bash
# 両ファイルのMCP定義を確認（env値は非表示）
python3 -c "
import json
for path in ['.claude/settings.json', '.claude.json']:
    s = json.load(open(path))
    for name, cfg in s.get('mcpServers', {}).items():
        display = {k: v for k, v in cfg.items() if k != 'env'}
        print(f'{path} → {name}: {display}')
"
```

詳細: `01_DECISIONS/claude-code/2026-06-11_MCP設定2層問題と接続トラブル修正.md`

---

## MCPをスクリプトに置き換える（コンテキスト節約）

MCPサーバーは便利だが、**常時起動するだけでコンテキストを消費する**。
定型操作に限れば `gh` コマンドや curl（webhook）で代替でき、MCPを切れる。

| 操作 | MCPの代わりに使うもの | 備考 |
|---|---|---|
| GitHub Issue作成 | `gh issue create` | gh CLI で完結 |
| GitHub PR確認・マージ | `gh pr list` / `gh pr merge` | gh CLI で完結 |
| CI結果確認 | `gh run watch` | gh CLI で完結 |
| Discord への通知送信 | `curl` + webhook URL | MCP不要・軽量 |

**判断基準：**
- 「Claudeに話しかけながら操作したい」→ MCP を使う
- 「スクリプトで定型的に実行したい」→ gh コマンド / curl に置き換えてMCPを切る

→ GitHub の基本概念・gh コマンドの詳細は **[GitHub 基礎ガイド](https://fukukei23.github.io/github-basics/)** を参照

---

## MCPツール使い分けガイド

詳細な使い分け基準は別ドキュメントを参照:

→ `00_SYSTEM/MCPツール使い分けガイド.md`

---

## 💡 やさしい補足（初心者向け）

- **「MCP」= Claudeに後付けする能力**: 標準ではできない「Web検索」「GitHub操作」「ブラウザ操作」等を追加できる仕組み
- **追加しすぎると高くつく**: 使っていなくても、追加した能力の「説明書」を毎回読み込むので**毎回料金がかかる**。使わないものは外すのが節約
- **公式と自作がある**: 検索等の汎用なものは公式、特注なものは自作可能
- **迷ったら**: よく使う機能だけ残す。不要なサーバーは思い切って外すのが一番の節約

---

## 次の章

- **[05_フック](05_フック.md)** — フックの仕組み
- **[00_早見表](00_早見表.md)** — 全機能のチートシートに戻る

## 関連

- [Claude-Code完全ガイド作成](../../01_DECISIONS/claude-code/2026-05-20_Claude-Code完全ガイド作成.md) — ガイド全体の設計と作成
- [MCP設定削減2回目](../../01_DECISIONS/claude-code/2026-05-20_MCP設定削減2回目.md) — MCP使用頻度分析に基づく削減
- [MCP-10ツール一括追加](../../01_DECISIONS/claude-code/2026-04-30_MCP-10ツール一括追加.md) — MCPツールの大規模追加
