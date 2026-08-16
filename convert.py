#!/usr/bin/env python3
"""Claude Code Guide: Markdown → モバイル最適化HTML変換スクリプト."""

import re
from pathlib import Path

from jinja2 import Template
from markdown_it import MarkdownIt

# --- 設定 ---

SOURCE_DIR = Path(__file__).parent / "source"
OUTPUT_DIR = Path(__file__).parent / "docs"

# 既存章の手動定義（タイトル・アイコン・説明をカスタマイズしたい場合に記載）
# ここに書かれていないファイルは source/ を自動スキャンして追加される
CHAPTER_MAP = {
    "00_早見表.md": {"slug": "00-cheatsheet", "title": "早見表", "icon": "📋", "desc": "全機能チートシート"},
    "01_基礎概念.md": {"slug": "01-basics", "title": "基礎概念", "icon": "🏗️", "desc": "Claude Codeの3つの形態とコンテキストの仕組み"},
    "02_コマンド一覧.md": {"slug": "02-commands", "title": "コマンド一覧", "icon": "⌨️", "desc": "ビルトインコマンドの全解説"},
    "03_スキルシステム.md": {"slug": "03-skills", "title": "スキルシステム", "icon": "🎯", "desc": "スキルの仕組みと活用方法"},
    "04_MCPサーバー.md": {"slug": "04-mcp", "title": "MCPサーバー", "icon": "🔌", "desc": "MCPツールの使い分けと設定"},
    "05_フック.md": {"slug": "05-hooks", "title": "フック", "icon": "🪝", "desc": "4種のフックでClaude Codeを自動化"},
    "06_メモリ.md": {"slug": "06-memory", "title": "メモリ", "icon": "🧠", "desc": "セッションをまたぐ記憶の仕組み"},
    "07_エージェント.md": {"slug": "07-agents", "title": "エージェント", "icon": "🤖", "desc": "サブエージェントの並列活用"},
    "08_設定ファイル.md": {"slug": "08-config", "title": "設定ファイル", "icon": "⚙️", "desc": "CLAUDE.md・settings.json・3層構造"},
    "09_統合.md": {"slug": "09-integration", "title": "統合", "icon": "🔗", "desc": "IDE連携・リモート・モデル切替"},
    "10_用語集.md": {"slug": "10-glossary", "title": "用語集", "icon": "📖", "desc": "A〜Zの用語解説"},
    "11_現場の知見.md": {"slug": "11-tips", "title": "現場の知見", "icon": "💡", "desc": "実践テクニックと落とし穴"},
    "12_dev-cycle.md": {"slug": "12-dev-cycle", "title": "dev-cycle", "icon": "🔄", "desc": "コード品質改善サイクル — スイープ→レビュー→Issue化→自律実装"},
    "13_glm-rate-proxy.md": {"slug": "13-glm-rate-proxy", "title": "GLM Rate Proxy", "icon": "⚡", "desc": "ZAI/GLMで動かす低コスト運用 — モデルルーティング・Thinking制御"},
    "15_コスト最適化構成.md": {"slug": "15-cost-optimization", "title": "コスト最適化", "icon": "💰", "desc": "GLM/MiniMaxルーティング（独自構成）"},
    "17_キーバインド.md": {"slug": "17-keybindings", "title": "CLI操作・キーバインド", "icon": "🎛️", "desc": "プロンプト入力欄の編集操作 — 全選択/消去/行編集/Vim/履歴/Windows特有"},
    "19_decisions_log.md": {"slug": "19-decisions-log", "title": "決定ログ", "icon": "🧩", "desc": "設計判断の図解入り記録 — どういう考えで決めたか"},
}


# --- 自動スキャン ---

def _filename_to_slug(filename: str) -> str:
    """ファイル名からslugを生成: '13_glm-rate-proxy.md' → '13-glm-rate-proxy'"""
    stem = Path(filename).stem  # 拡張子除去
    # 先頭の数字+区切り文字を抽出: "13_foo" → "13-foo", "00_早見表" → "00-cheatsheet相当"
    # アンダースコアをハイフンに、日本語はASCIIに変換できないのでそのまま残す
    slug = stem.replace("_", "-", 1)  # 最初の _ のみハイフン化
    # 残りの _ もハイフン化
    slug = slug.replace("_", "-")
    # ASCII以外の文字を除去してslugを作る
    ascii_slug = ""
    for ch in slug:
        if ch.isascii():
            ascii_slug += ch.lower()
        elif ch == "-":
            ascii_slug += "-"
    # 連続ハイフン・末尾ハイフンを整理
    ascii_slug = re.sub(r"-+", "-", ascii_slug).strip("-")
    return ascii_slug or slug


def _extract_frontmatter(text: str) -> tuple[dict, str]:
    """YAMLフロントマターを抽出。なければ空dictとテキストをそのまま返す。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def _extract_title_from_h1(text: str) -> str:
    """H1ヘッダーからタイトルを抽出。'# 13 GLM Rate Proxy — ...' → 'GLM Rate Proxy'"""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            # 番号プレフィックスを除去: "13 GLM Rate Proxy" → "GLM Rate Proxy"
            title = re.sub(r"^\d+\s+", "", title)
            # ダッシュ以降の説明を除去: "GLM Rate Proxy — 説明" → "GLM Rate Proxy"
            title = re.split(r"\s+[—–-]\s+", title)[0].strip()
            return title
    return ""


def _extract_desc_from_h1(text: str) -> str:
    """H1ヘッダーのダッシュ以降を説明として抽出。"""
    for line in text.splitlines():
        if line.startswith("# "):
            parts = re.split(r"\s+[—–-]\s+", line[2:].strip(), maxsplit=1)
            if len(parts) > 1:
                return parts[1].strip()
    return ""


def build_chapter_map() -> dict:
    """source/ をスキャンして完全なCHAPTER_MAPを構築。
    CHAPTER_MAPに未登録のファイルは自動検出して追加する。"""
    result = dict(CHAPTER_MAP)

    for md_file in sorted(SOURCE_DIR.glob("*.md")):
        filename = md_file.name
        if filename.startswith("_"):
            continue  # _README.md等は除外
        if filename in result:
            continue  # 既登録はスキップ

        text = md_file.read_text(encoding="utf-8")
        meta, body = _extract_frontmatter(text)

        title = meta.get("title") or _extract_title_from_h1(text) or Path(filename).stem
        desc = meta.get("card_desc") or meta.get("desc") or _extract_desc_from_h1(text) or title
        icon = meta.get("icon", "📄")
        slug = meta.get("slug") or _filename_to_slug(filename)

        result[filename] = {"slug": slug, "title": title, "icon": icon, "desc": desc}
        print(f"AUTO: {filename} → {slug} ({title})")

    return result

REMOVE_SECTIONS = [
    "## 関連",
    "## 関連ドキュメント",
    "## 次の章",
    "## あなたの現在のフック構成",
    "## あなたの環境のメモリ構成",
    "## あなたの設定ファイル一覧",
    "## あなたのLLMルーティング",
    "## あなたの環境での使い方",
    "## あなたの環境の特記事項",
    "## あなたのMCPサーバー構成",
    "## あなたのフック一覧",
]

REMOVE_PATTERNS = [
    "あなたの",
]

INLINE_REPLACEMENTS = [
    # 個人ルーティング情報 → 汎用化
    (r"GLM-5\.1にルーティング", "Anthropic APIまたは代替プロバイダー経由で利用可能"),
    (r"GLM-4\.7にルーティング", "Anthropic APIまたは代替プロバイダー経由で利用可能"),
    (r"GLM-4\.5-Airにルーティング", "Anthropic APIまたは代替プロバイダー経由で利用可能"),
    (r"GLM-5\.1がデフォルト", "デフォルトモデルが自動選択"),
    (r"あなたの環境:\s*GLM-5\.1\s*→\s*MiniMax\s*→\s*Sonnet", "モデルは /model コマンドで切替可能"),
    (r"あなたの環境ではGLM-5\.1にルーティング", "API経由で利用可能"),
    (r"あなたの環境ではGLM-4\.7にルーティング", "API経由で利用可能"),
    (r"GLM-4\.5-Air に切替", "Haiku に切替"),
    (r"GLM-4\.7 に戻す", "Sonnet に戻す"),
    (r"通常タスク → 🟡 GLM-5\.1（glm_ask経由）", "通常タスク → Opus または Sonnet"),
    (r"フォールバック → 🟠 MiniMax（minimax_ask経由）", "フォールバック → Haiku"),
    (r"大量処理委譲 → 🟠 MiniMax（自動委譲）", "大量処理 → Haiku等の軽量モデル"),
    # 内部パス参照 → 除去
    (r"→ `00_SYSTEM/共通ルール/LLMルーティング\.md`", ""),
    (r"→ `00_SYSTEM/MCPツール使い分けガイド\.md`", ""),
    (r"あなたのobsidian-ssotリポジトリがこれに該当。", "単一リポジトリで一元管理する構成がこれに該当。"),
    (r"あなたのグローバルCLAUDE\.mdに含まれるもの:", "グローバルCLAUDE.mdに含まれるもの:"),
    (r"あなたの現在のメイン環境（WSL2）", "Linuxターミナル環境"),
    (r"LLMルーティング（GLM → MiniMax → Sonnet）", "モデルルーティング（上位モデル → バランス型 → 軽量型）"),
    (r"バッジ表示ルール（🟡\[GLM\]等）", "使用モデル表示ルール"),
    (r"GLM-5\.1", "Claude"),
    (r"GLM-4\.7", "Claude"),
    (r"GLM-4\.5-Air", "Claude"),
    (r"LLM（Claude / GLM / MiniMax）", "LLM（Claude）"),
    (r"Claude, GLM, MiniMax等", "Claude等"),
    (r"Opus/Sonnet/Haiku \+ GLM", "Opus / Sonnet / Haiku"),
    # obsidian-ssot / 00_SYSTEM パス（スキル内コードブロック）
    (r"obsidian-ssot/00_SYSTEM/handoff/", "claude-code/handoff/"),
    (r"obsidian-ssot", "knowledge-base"),
    (r"00_SYSTEM/", "00★SYSTEM/"),
    # 「あなたの設定」テーブル列 → 行ごと書き換え
    (r"\| あなたの設定 \|.*?\|", "| 備考 | なし |"),
]

TABLE_COL_SANITIZE = [
    # テーブルヘッダーから「あなたの設定」列を除去するパターン
    (r"\|\s*あなたの設定\s*\|", "| 備考 |"),
    (r"\|\s*`~/.secrets\.env`\s+からAPIキーを注入.*?\|", "| APIキーは環境変数で管理 |"),
    (r"\|\s*`check-command-safety\.py`\s+が危険コマンドを自動ブロック.*?\|", "| 危険コマンドを自動ブロック |"),
    (r"\|\s*MCP設定変更時の使い分けガイド自動更新.*?\|", "| 設定変更を自動検知 |"),
    (r"\|\s*セッション終了時のサマリー記録.*?\|", "| セッション終了時に記録 |"),
    (r"\|\s*Anthropic APIまたは代替プロバイダー経由で利用可能\s*\|", "| API経由で利用可能 |"),
]

MERMAID_DIAGRAMS = {
    "01_基礎概念.md": [
        (
            "## アーキテクチャ",
            """graph TD
    User["👤 ユーザー"] --> CLI["💻 Claude Code CLI"]
    CLI --> SP["📋 システムプロンプト"]
    CLI --> MCP["🔌 MCPツール定義"]
    CLI --> SK["🎯 スキル定義"]
    CLI --> MEM["🧠 メモリ読込"]
    CLI --> LLM["🤖 LLM"]
    LLM --> Tools["🔧 ツール実行"]
    Tools --> Files["📁 ファイル操作"]
    Tools --> Shell["💻 シェル実行"]
    Tools --> API["🌐 API呼出"]
    Tools --> Agent["🤖 サブエージェント"]
    LLM --> Resp["💬 レスポンス"]
    Resp --> User""",
        ),
        (
            "## コンテキストの仕組み",
            """graph LR
    subgraph "200K トークン コンテキストウィンドウ"
        A["システムプロンプト<br/>~3%"]
        B["ツール定義<br/>~20%"]
        C["メモリ・スキル<br/>~4%"]
        D["会話履歴<br/>~3%"]
        E["空き容量<br/>~70%"]
    end""",
        ),
    ],
    "05_フック.md": [
        (
            "## 4種のフック",
            """sequenceDiagram
    participant U as ユーザー
    participant CC as Claude Code
    participant Pre as PreToolUse
    participant Tool as ツール
    participant Post as PostToolUse

    Note over CC: 🔄 SessionStart Hook発火
    U->>CC: リクエスト送信
    CC->>Pre: ツール実行前チェック
    alt チェックOK
        Pre->>Tool: ✅ ツール実行
        Tool->>Post: 実行完了
        Post->>CC: ログ記録
    else チェックNG
        Pre-->>CC: 🚫 ブロック
    end
    CC->>U: レスポンス
    Note over CC: 🔄 Stop Hook発火""",
        ),
    ],
    "06_メモリ.md": [
        (
            "## メモリの種類",
            """graph TD
    subgraph "🧠 メモリシステム"
        AUTO["Auto Memory<br/>~/.claude/projects/"]
        USER["User Memory<br/>~/.claude/CLAUDE.md"]
        PROJ["Project Memory<br/>repo/CLAUDE.md"]
        IDX["MEMORY.md<br/>インデックス"]
    end
    AUTO --> T1["user: 役割・目標"]
    AUTO --> T2["feedback: 指導"]
    AUTO --> T3["project: 決定事項"]
    AUTO --> T4["reference: 外部参照"]
    IDX --> AUTO""",
        ),
    ],
    "07_エージェント.md": [
        (
            "## 並列実行の例",
            """graph TD
    MAIN["🖥️ メインセッション"] --> A1["🔍 エージェントA<br/>コード探索"]
    MAIN --> A2["📝 エージェントB<br/>レビュー"]
    MAIN --> A3["🧪 エージェントC<br/>テスト実行"]
    A1 --> |"結果"| MAIN
    A2 --> |"結果"| MAIN
    A3 --> |"結果"| MAIN
    MAIN --> |"統合表示"| USER["👤 ユーザー"]""",
        ),
    ],
    "08_設定ファイル.md": [
        (
            "## 設定の3層構造",
            """graph BT
    L1["Layer 1: グローバル<br/>~/.claude/CLAUDE.md<br/>全プロジェクト共通"]
    L2["Layer 2: プロジェクト<br/>repo/CLAUDE.md<br/>プロジェクト固有"]
    L3["Layer 3: ディレクトリ<br/>repo/dir/CLAUDE.md<br/>特定ディレクトリ"]
    L3 -->|"上書き"| L2
    L2 -->|"上書き"| L1
    style L3 fill:#e8f5e9
    style L2 fill:#fff3e0
    style L1 fill:#e3f2fd""",
        ),
    ],
    "09_統合.md": [
        (
            "## モデル切替",
            """graph TD
    A["📋 タスク受付"] --> B{"Opus<br/>デフォルト"}
    B -->|"成功"| C["✅ 結果返却"]
    B -->|"失敗"| D{"Haiku<br/>フォールバック"}
    D -->|"成功"| C
    B -->|"大量処理"| E["軽量モデルに委譲"]
    E --> C
    B -->|"高品質必要"| F{"👤 ユーザー確認"}
    F -->|"許可"| G["上位モデルで処理"]
    G --> C
    F -->|"拒否"| B""",
        ),
    ],
}

# --- HTMLテンプレート ---

CHAPTER_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="ja" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — Claude Code Guide</title>
    <meta name="description" content="Claude Code CLI {{ title }}の解説 — AIコーディングアシスタント完全ガイド">
    <meta property="og:title" content="{{ title }} — Claude Code Guide">
    <meta property="og:description" content="Claude Code CLI {{ title }}の解説">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://fukukei23.github.io/claude-code-guide/chapters/{{ slug }}.html">
    <meta property="og:image" content="https://fukukei23.github.io/claude-code-guide/assets/ogp.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="stylesheet" href="../assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">
</head>
<body>
    <header class="site-header">
        <button class="menu-toggle" aria-label="メニュー" id="menuToggle">
            <span></span><span></span><span></span>
        </button>
        <a href="../index.html" class="site-title">⚡ Claude Code Guide</a>
        <button class="theme-toggle" id="themeToggle" aria-label="テーマ切替">
            <span class="icon-light">☀️</span>
            <span class="icon-dark">🌙</span>
        </button>
    </header>

    <nav class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <a href="../index.html">🏠 ホーム</a>
        </div>
        {% for ch in chapters %}
        <a href="{{ ch.slug }}.html"
           class="sidebar-link{{ ' active' if ch.slug == current_slug }}">
            <span class="sidebar-icon">{{ ch.icon }}</span>
            {{ ch.title }}
        </a>
        {% endfor %}
    </nav>
    <div class="sidebar-overlay" id="sidebarOverlay"></div>

    <main class="content">
        <div class="chapter-nav-top">
            {% if prev_ch %}
            <a href="{{ prev_ch.slug }}.html" class="nav-prev">← {{ prev_ch.title }}</a>
            {% endif %}
            {% if next_ch %}
            <a href="{{ next_ch.slug }}.html" class="nav-next">{{ next_ch.title }} →</a>
            {% endif %}
        </div>

        <article class="chapter-body">
            {{ content|safe }}
        </article>

        <nav class="chapter-nav-bottom">
            {% if prev_ch %}
            <a href="{{ prev_ch.slug }}.html" class="nav-card prev">
                <span class="nav-label">← 前の章</span>
                <span class="nav-title">{{ prev_ch.icon }} {{ prev_ch.title }}</span>
            </a>
            {% endif %}
            {% if next_ch %}
            <a href="{{ next_ch.slug }}.html" class="nav-card next">
                <span class="nav-label">次の章 →</span>
                <span class="nav-title">{{ next_ch.icon }} {{ next_ch.title }}</span>
            </a>
            {% endif %}
        </nav>
    </main>

    <footer class="site-footer">
        <p>Claude Code Guide — <a href="https://github.com/fukukei23/claude-code-guide">GitHub</a>
         · <a href="https://fukukei23.github.io/ssot-guide/">SSOT Guide</a>
         · <a href="https://fukukei23.github.io/loop-engineering-guide/">Loop Engineering Guide</a>
         · <a href="https://fukukei23.github.io/guides/">技術ガイド集</a>
         · <a href="https://fukukei23.github.io/">fukukei23</a></p>
    </footer>

    <script src="../assets/script.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
            themeVariables: { fontSize: '14px' }
        });
    </script>
</body>
</html>
""", autoescape=True)

INDEX_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="ja" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code 完全ガイド</title>
    <meta name="description" content="AIコーディングアシスタント Claude Code の使い方を基礎から応用まで完全解説">
    <meta property="og:title" content="Claude Code 完全ガイド">
    <meta property="og:description" content="AIコーディングアシスタント Claude Code の使い方を基礎から応用まで完全解説">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://fukukei23.github.io/claude-code-guide/">
    <meta property="og:image" content="https://fukukei23.github.io/claude-code-guide/assets/ogp.png">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="stylesheet" href="assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">
</head>
<body class="index-page">
    <header class="site-header">
        <span class="site-title">⚡ Claude Code Guide</span>
        <button class="theme-toggle" id="themeToggle" aria-label="テーマ切替">
            <span class="icon-light">☀️</span>
            <span class="icon-dark">🌙</span>
        </button>
    </header>

    <main class="content">
        <section class="hero">
            <h1>Claude Code 完全ガイド</h1>
            <p>AIコーディングアシスタント Claude Code の使い方を、<br>基礎から応用まで完全解説</p>
        </section>

        {% for cat in categories %}
        <section class="chapter-category">
            <h2 class="chapter-category-heading">{{ cat.name }}</h2>
            <div class="chapter-grid">
                {% for ch in cat.chapters %}
                <a href="chapters/{{ ch.slug }}.html" class="chapter-card">
                    <div class="card-icon">{{ ch.icon }}</div>
                    <div class="card-number">第{{ ch.number }}章</div>
                    <h2 class="card-title">{{ ch.title }}</h2>
                    <p class="card-desc">{{ ch.desc }}</p>
                </a>
                {% endfor %}
            </div>
        </section>
        {% endfor %}

        <section class="features">
            <h2>📖 このガイドの特徴</h2>
            <div class="feature-grid">
                <div class="feature-item">
                    <span class="feature-icon">🎯</span>
                    <h3>初心者向け</h3>
                    <p>専門用語は初出時に説明。前提知識不要</p>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📊</span>
                    <h3>図解付き</h3>
                    <p>アーキテクチャやフローをMermaid図で視覚化</p>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📱</span>
                    <h3>モバイル対応</h3>
                    <p>スマホからいつでも見返せるレスポンシブデザイン</p>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🌙</span>
                    <h3>ダークモード</h3>
                    <p>目に優しいテーマ切替対応</p>
                </div>
            </div>
        </section>
    </main>

    <footer class="site-footer">
        <p>Claude Code Guide — <a href="https://github.com/fukukei23/claude-code-guide">GitHub</a>
         · <a href="https://fukukei23.github.io/ssot-guide/">SSOT Guide</a>
         · <a href="https://fukukei23.github.io/loop-engineering-guide/">Loop Engineering Guide</a>
         · <a href="https://fukukei23.github.io/guides/">技術ガイド集</a>
         · <a href="https://fukukei23.github.io/">fukukei23</a></p>
    </footer>

    <script src="assets/script.js"></script>
</body>
</html>
""", autoescape=True)


# --- フィルタリング ---

def filter_sections(text: str) -> str:
    """個人情報・環境固有セクションを除去."""
    lines = text.split("\n")
    result = []
    skip = False

    for line in lines:
        stripped = line.strip()

        # 除去対象セクションの開始（## または ### セクション）
        if stripped.startswith("## ") and any(stripped.startswith(s) for s in REMOVE_SECTIONS):
            skip = True
            continue

        # 「あなたの」で始まる## / ### セクションも除去
        if (stripped.startswith("## ") or stripped.startswith("### ")) and any(p in stripped for p in REMOVE_PATTERNS):
            skip = True
            continue

        # 次の ## セクションでスキップ解除（### はスキップ解除しない）
        if skip and stripped.startswith("## ") and not any(p in stripped for p in REMOVE_PATTERNS):
            skip = False

        if not skip:
            result.append(line)

    text = "\n".join(result)

    # 個人識別子のサニタイズ
    # ※公開URL（https://fukukei23.github.io/...）は置換対象外（リンク壊れ防止・公開GitHub Pages URL）
    public_urls = set(re.findall(r'https?://fukukei23\.github\.io[^\s)）]*', text))
    url_placeholders = {}
    for i, url in enumerate(sorted(public_urls)):
        ph = f"__PUBLIC_URL_{i}__"
        url_placeholders[ph] = url
        text = text.replace(url, ph)

    text = text.replace("yn4416", "<USER>")
    text = text.replace("fukukei23", "<USERNAME>")
    text = text.replace("fukukei", "<USERNAME>")

    # 公開URL復元
    for ph, url in url_placeholders.items():
        text = text.replace(ph, url)

    # インライン個人情報のサニタイズ
    for pattern, replacement in INLINE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    for pattern, replacement in TABLE_COL_SANITIZE:
        text = re.sub(pattern, replacement, text)

    # 未処理の「あなたの」を行内テキストから除去
    text = re.sub(r"あなたの環境では", "", text)
    text = re.sub(r"あなたの環境:", "", text)

    return text


# --- Markdown → HTML変換 ---

def convert_md_to_html(md_text: str) -> str:
    """MarkdownをHTMLに変換（見出しID記法 {#id} を id 属性に変換）。."""
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    html = md.render(md_text)
    return _attach_heading_ids(html)


def _attach_heading_ids(html: str) -> str:
    """MarkdownIt が残した {#id} を h1-h6 の id 属性に変換.

    例: <h2>概要 {#overview}</h2> → <h2 id="overview">概要</h2>
    html:False 環境で attrs プラグイン不要の軽量パーサ。
    """
    def _repl(match: "re.Match") -> str:
        level, text, hid = match.group(1), match.group(2), match.group(3)
        return f'<h{level} id="{hid}">{text}</h{level}>'
    return re.sub(
        r'<h([1-6])>(.*?)\s*\{#([^}]+)\}\s*</h\1>',
        _repl,
        html,
    )


def inject_mermaid(html: str, filename: str) -> str:
    """Mermaid図を指定位置に挿入."""
    diagrams = MERMAID_DIAGRAMS.get(filename, [])
    if not diagrams:
        return html

    for heading, diagram_code in diagrams:
        # HTMLの見出しタグを検索（<a id>タグ込みも対応）
        heading_text = heading.replace("## ", "").strip()
        mermaid_block = (
            f'<div class="mermaid-wrapper">'
            f'<div class="mermaid">\n{diagram_code}\n</div>'
            f'</div>'
        )

        # <h2 id="...">テキスト</h2> の前に挿入（{#id}記法 → id属性化に対応）
        pattern = f'(<h2[^>]*>{re.escape(heading_text)}</h2>)'
        if re.search(pattern, html):
            html = re.sub(pattern, mermaid_block + r"\1", html, count=1)

    return html


def rewrite_links(html: str, chapter_map: dict | None = None) -> str:
    """内部リンクをHTML URLに書き換え."""
    from urllib.parse import quote, unquote

    cmap = chapter_map or CHAPTER_MAP

    for filename, info in cmap.items():
        # [テキスト](XX_YY.md) → XX-yy.html
        html = html.replace(f'href="{filename}', f'href="{info["slug"]}.html')
        # [テキスト](XX_YY.md#anchor) → XX-yy.html#anchor
        html = re.sub(
            rf'href="{re.escape(filename)}#',
            f'href="{info["slug"]}.html#',
            html,
        )

        # URLエンコードされたリンク（例: 11_%E7%8F%BE%E5%A0%B4...）も処理
        encoded_name = quote(filename, safe='')
        if encoded_name != filename:
            html = html.replace(f'href="{encoded_name}', f'href="{info["slug"]}.html')
            html = re.sub(
                rf'href="{re.escape(encoded_name)}#',
                f'href="{info["slug"]}.html#',
                html,
            )

    # 未変換の.mdリンクをすべて処理
    def replace_md_link(match):
        href = match.group(1)
        for filename, info in cmap.items():
            decoded = unquote(href)
            if filename in decoded or filename in href:
                anchor = ""
                if "#" in href:
                    anchor = "#" + href.split("#", 1)[1]
                elif "#" in decoded:
                    anchor = "#" + decoded.split("#", 1)[1]
                return f'href="{info["slug"]}.html{anchor}"'
        return 'href="#"'

    html = re.sub(r'href="([^"]*\.md[^"]*)"', replace_md_link, html)

    # 外部リンク（obsidian-ssot内の他ファイル）を除去
    html = re.sub(r'href="\.\./[^"]*"', 'href="#"', html)
    html = re.sub(r'href="01_DECISIONS[^"]*"', 'href="#"', html)

    return html


def enhance_html(html: str) -> str:
    """HTMLに装飾を追加（テーブルラップ・コールアウト等）."""
    # テーブルをスクロールラッパーで囲む
    html = re.sub(
        r"(<table[^>]*>.*?</table>)",
        r'<div class="table-wrapper">\1</div>',
        html,
        flags=re.DOTALL,
    )

    # 引用ブロックをコールアウトに変換
    def callout_replace(match):
        content = match.group(1)
        if "注意" in content or "⚠" in content:
            return f'<div class="callout callout-warn"><p>{content}</p></div>'
        if "重要" in content:
            return f'<div class="callout callout-danger"><p>{content}</p></div>'
        if "現場の知見" in content or "💡" in content or "Tip" in content:
            return f'<div class="callout callout-tip"><p>{content}</p></div>'
        return f'<div class="callout callout-info"><p>{content}</p></div>'

    html = re.sub(r"<blockquote>\s*<p>(.*?)</p>\s*</blockquote>", callout_replace, html, flags=re.DOTALL)

    return html


# --- 用語ツールチップ（add-term-tooltip パターン・クリック/ホバーで解説表示） ---
# source MD は html:False で生HTMLを書けないため、レンダリング後の後処理で囲む
# ※ 包含関係のある用語は「長い方を先に」定義すること（例: システムプロンプト → プロンプト）
TERM_TOOLTIPS = {
    "コンテキストウィンドウ": (
        "AIが一度に「覚えていられる」会話・資料の容量上限のこと。作業が長くなると上限に近づき、"
        "古い内容の把握が荒くなる（＝自動で要約圧縮される）"
    ),
    "コンテキスト圧縮": (
        "会話が長くなって容量上限に近づいた時、AIが古い内容を要約にまとめて"
        "容量を空ける仕組み。要約された細部は失われるため、重要な経緯はファイルに記録して残す"
    ),
    "サブエージェント": (
        "メインのAIから独立して呼び出される「作業班」のAI。親の会話を汚さずに調査等を任せられ、"
        "結果の報告だけを受け取る。並行して複数動かすこともできる"
    ),
    "エージェント": (
        "与えられた目標に向かって、自分で手順を組み立てて作業を進めるAIプログラム。"
        "質問に答えるだけのチャットAIと違い、「調べる→書く→確認する」を自律的に行う"
    ),
    "システムプロンプト": (
        "AIに最初から組み込まれている「基本の指示書」。ユーザーの発話とは別に、"
        "AIの振る舞い方の土台を決めている。CLAUDE.md等はここに近い形で常に読み込まれる"
    ),
    "プロンプト": (
        "AIに渡す指示文のこと。「この機能を作って」「この文を直して」等"
    ),
    "トークン": (
        "AIにとっての「文字数」のようなもの。AIは文章をトークンという小片に区切って処理する。"
        "課金や入力上限（コンテキストウィンドウ）はこの単位で数えられる"
    ),
    "スキル": (
        "Claude Codeで「特定の作業手順」をパッケージ化したもの。SKILL.mdに手順を書いておくと、"
        "対応する場面でAIがその手順を読み込んで従う。経験を再利用する仕組み"
    ),
    "MCP": (
        "Model Context Protocol（エムシーピー）の略。"
        "AIに外部ツール（検索・GitHub・データベース等）を繋ぐための共通接続規格。"
        "USBのような「差せば繋がる」仕組みでAIの能力を拡張する"
    ),
    "hook": (
        "Claude Codeの特定のタイミング（ツール実行前後・セッション開始時等）で"
        "自動処理を差し込む仕組み。「保存前にチェック」「終了時に記録」等を機械的に強制できる"
    ),
    "Hook": (
        "Claude Codeの特定のタイミング（ツール実行前後・セッション開始時等）で"
        "自動処理を差し込む仕組み。「保存前にチェック」「終了時に記録」等を機械的に強制できる"
    ),
    "セッション": (
        "Claude Codeの1回の対話単位。起動から終了までの会話と作業状態のこと。"
        "長く使うと内容が混ざるため、トピックの区切りで新セッションに引き継ぐ運用をする"
    ),
    "フォールバック": (
        "メインの手段が使えなくなった時に、自動的に予備の手段へ切り替える仕組み。"
        "「本命が失敗したら副えに任せる」二段構え"
    ),
    "プロキシ": (
        "通信の中継役。「クライアント→プロキシ→本来の宛先」の順に通信を一度経由させる仕組みで、"
        "仲介者が経路の切替・集計・制限等を担当する"
    ),
    "レート制限": (
        "短時間の利用回数にかけられる上限。API等で一定時間内のリクエスト数が制限されること。"
        "超えると一時的にエラーになる"
    ),
    "環境変数": (
        "プログラムの外側（OS側）で設定する値の入れ物。プログラムを書き換えずに設定を切り替えられる。"
        "APIキー等の秘密の値はソースコードに直書きせずここに入れるのが安全な定石"
    ),
    "RAG": (
        "Retrieval-Augmented Generation（ラグ・検索拡張生成）の略。"
        "AIに答えさせる前に、自分の文書から関連箇所を検索して渡し、"
        "その内容に基づいて答えさせる仕組み"
    ),
    "埋め込み": (
        "文章の意味を数字の列（ベクトル）に変換すること。意味が近い文章は近い数字になるため、"
        "「意味での検索」ができるようになる。RAGの部品"
    ),
    "チャンキング": (
        "長い文書を検索しやすい大きさの断片（チャンク）に切ること。切り方が検索精度を大きく左右する"
    ),
    "OAuth": (
        "オーオースと読む。他のサービスの機能を、IDやパスワードを教えずに"
        "安全に使わせるための認可の標準規格。「○○でログイン」ボタンの裏側で動いている仕組み"
    ),
    "認証": (
        "「あなたは誰か」を確認すること。パスワードや鍵で本人であることを確かめる手続き"
    ),
    "API": (
        "Application Programming Interface（エーピーアイ）の略。"
        "あるプログラムの機能を、別のプログラムから呼び出せるようにした「窓口」"
    ),
    "Webhook": (
        "ウェブフック。「イベントが起きたら指定URLに自動で通知を送る」仕組み。"
        "GitHubで更新があればDiscordに通知が飛ぶ、等の連携に使う"
    ),
    "webhook": (
        "ウェブフック。「イベントが起きたら指定URLに自動で通知を送る」仕組み。"
        "GitHubで更新があればDiscordに通知が飛ぶ、等の連携に使う"
    ),
    "localhost": (
        "ローカルホスト。「自分のPCの中」を指す特別なアドレス。"
        "localhost:8787 のような書式は「自分のPCの8787番ポート」の意味"
    ),
    "ポート": (
        "同じPCの中で複数のプログラムが通信を待ち受けるための「窓口番号」。"
        "8787番・3000番のように番号で区別する"
    ),
    "HTTP": (
        "エイチティーティーピー。Webの通信で使われる基本的な約束事（プロトコル）。"
        "ブラウザとサーバー、プログラム同士のやり取りの共通言語"
    ),
    "ブランチ": (
        "Gitで、本体（main）とは別に作業履歴を分けて保管できる「平行世界」。"
        "実験的な変更を本体に影響させずに進められる。終わったら本体に合流（マージ）する"
    ),
    "マージ": (
        "分かれていた変更を1つに統合すること。ブランチで進めた作業を本体（main）に取り込む作業"
    ),
    "プルリクエスト": (
        "「この変更を本体に取り込んでください」とレビューを求める仕組み（GitHubの機能）。"
        "自分の変更を他人が確認してから統合するフローに使う"
    ),
    "CI": (
        "Continuous Integration（シーアイ・継続的インテグレーション）の略。"
        "コードを変更するたびに自動でテストとチェックを回し、"
        "壊れていないかを常に確認する仕組み"
    ),
    "GitHub Actions": (
        "GitHubが提供する自動実行の仕組み。pushをきっかけにテストやビルドを自動で回せる。"
        "「リポジトリに置いておくと動く作業ロボット」"
    ),
    "GitHub Pages": (
        "GitHubが無料で提供するWeb公開サービス。リポジトリ内のHTMLファイルを"
        "そのままWebサイトとして公開できる。本ガイドもこれで公開されている"
    ),
    "デプロイ": (
        "作ったプログラムやサイトを、実際に動く環境へ設置して公開すること"
    ),
    "bash": (
        "バッシュ。Linux等で使われる標準的なシェル（コマンド入力を受け付ける程序）の名前。"
        "シェルスクリプトを書く時の定番"
    ),
    "シェル": (
        "ユーザーとOSの間に入って、コマンド入力を受け付けて実行する程序。"
        "ターミナルで打つコマンドを実際に処理する部分"
    ),
    "パイプ": (
        "コマンドの結果を次のコマンドへ流し込む「｜」記号の仕組み。"
        "「検索する → 結果を数える」のように処理をつなげられる"
    ),
    "標準出力": (
        "プログラムが結果を書き出す標準的な出口。画面表示や次のプログラムへの受け渡しに使われる。"
        "ちなみにエラー情報は「標準エラー出力」という別の出口に出る"
    ),
    "終了コード": (
        "プログラムが終了時に返す「結果の合図」。0は成功、0以外は失敗や異常を意味する。"
        "自動化の判定はこれを見て行う"
    ),
    "正規表現": (
        "文字のパターンを記号で表す書き方。「数字3桁」等を簡潔に指定でき、"
        "検索・置換・チェックに使う"
    ),
    "grep": (
        "グレップ。ファイルやテキストの中から、指定したパターンを含む行を抜き出すコマンド。"
        "大量のファイルから目的の言葉を探す時の定番"
    ),
    "glob": (
        "グロブ。ファイル名を「＊（任意の文字列）」等のワイルドカードで指定する書き方。"
        "「*.md」＝すべてのmdファイル、のような使い方"
    ),
    "シンボリックリンク": (
        "ファイルやフォルダの「ショートカット」のようなもの。リンクを辿ると実体の場所として扱える。"
        "1つの実体を複数の場所から参照したい時に使う"
    ),
    "シェルスクリプト": (
        "コマンドの並びをファイルに書いて、まとめて自動実行できるようにしたもの。"
        "定型作業の手順書をプログラム化したもの"
    ),
    "実行権限": (
        "ファイルを「プログラムとして実行してよい」権限。Linuxでは権限がないと実行を拒否される。"
        "chmodコマンドで付与する"
    ),
    "絶対パス": (
        "一番上（ルート）から数えた完全な住所のようなファイルの場所表記。「/home/…」で始まる"
    ),
    "相対パス": (
        "今いる場所からの相対的なファイルの場所表記。「../」は1つ上のフォルダの意味"
    ),
    "JSON": (
        "ジェイソン。データを記述する標準的な書式の1つ。設定ファイルやデータのやり取りに広く使われ、"
        "「名前: 値」の組み合わせで書く"
    ),
    "YAML": (
        "ヤムル。階層構造を字下げで表す、人間が読みやすい設定ファイルの書式。"
        "frontmatter（文書冒頭の---で囲んだ設定塊）で使われる"
    ),
    "フロントマター": (
        "Markdownファイルの冒頭に「---」で囲んで置く設定データの塊。"
        "タイトルやタグ等を本文と分離して書ける"
    ),
    "スキーマ": (
        "データの型・形の決まり。「このファイルには何の項目が必須か」等の定義。"
        "決まりに合っているか機械で検査できる"
    ),
    "エスケープ": (
        "特別な意味を持つ文字（< > 等）を、ただの文字として扱われるよう別の書き方に変えること。"
        "画面表示や注入攻撃の防止に使う"
    ),
    "仮想環境": (
        "プロジェクトごとにインストールするライブラリを分ける独立したPython環境。"
        "プロジェクト間のバージョン衝突を防ぐ"
    ),
    "venv": (
        "ブイエンブ。Python標準の仮想環境を作るコマンド/仕組み。"
        "プロジェクトごとにライブラリを分けてインストールできるようにする"
    ),
    "pip": (
        "ピップ。Pythonのライブラリ（部品）をインストールするコマンド。"
        "Pythonの買い物カートのようなもの"
    ),
    "型ヒント": (
        "変数や関数の入出力が「数値か文字列か」等の型であると予め宣言する書き方。"
        "書き間違いを実行前に機械が検出できるようになる"
    ),
    "docstring": (
        "ドックストリング。関数等の直後に書く説明文。プログラムの動作を1行で説明し、"
        "AIや人間がコードを理解する助けになる"
    ),
    "リンター": (
        "コードの「怪しい書き方」を自動で指摘する道具。バグの元になる書き方や"
        "読みにくい書き方を見つける。ruffはPython用の定番リンター"
    ),
    "単体テスト": (
        "関数など部品単位で動作を確認するテスト。pytestはPythonの定番テスト実行道具。"
        "変更のたびに自動で回して壊れていないことを担保する"
    ),
    "TDD": (
        "テスト駆動開発。先にテストを書き、そのテストを通すようにコードを書く進め方。"
        "「何をもって正しいとするか」を最初に固定できる"
    ),
    "カバレッジ": (
        "テストがコードのどれくらいの割合を確認できているかを表す数字（％）。"
        "80%なら、コードの8割が少なくとも1回はテストで実行されたことになる"
    ),
    "リファクタリング": (
        "動きを変えずにコードの中身を読みやすく整理すること。"
        "機能追加でなく「掃除」の作業"
    ),
    "デバッグ": (
        "不具合の原因を特定して直すこと。ログや実行の跡を辿って、"
        "どこで期待と違う動きをしたかを突き止める作業"
    ),
    "スタックトレース": (
        "エラー発生時に表示される「どこ経由でエラーに至ったか」の記録。"
        "一番下（最後）に書いてある行が実際に失敗した場所のことが多い"
    ),
    "例外": (
        "プログラムの実行中に起きた異常のこと、とその知らせ。"
        "例外を捕まえて処理（ハンドリング）しないと、その場でプログラムが止まる"
    ),
    "冪等": (
        "めいとう。「同じ操作を2回実行しても、1回実行した時と同じ結果になる」性質。"
        "再実行時の二重登録等の事故を防ぐ設計"
    ),
    "キャッシュ": (
        "一度得た結果を取っておいて、次回は同じ計算をせず使い回す仕組み。"
        "速くなるが、元のデータが変わった時の更新忘れに注意"
    ),
    "キーバインド": (
        "キーボードのキー操作と機能の割り当てのこと。「Ctrl+Sで保存」のような対応関係"
    ),
    "cron": (
        "クロン。Linuxで「毎日6時」「30分ごと」等の定期実行を予約する仕組み。"
        "予約実行の登録表（crontab）に書いて運用する"
    ),
    # --- 平易語彙拡張（2026-08-17・ユーザー要望で閾値を下げて追加） ---
    # ※ 包含関係: シェルスクリプト→スクリプト / 変数展開→変数 / 環境変数→変数 は「長い方を先に」
    "コードレビュー": (
        "書かれたコードを、書いた本人以外の視点で読んで問題を指摘する作業。"
        "バグ・読みにくさ・危険な書き方を見つけるのに有効"
    ),
    "コマンド": (
        "ターミナルに入力してコンピュータに与える一行の指示。"
        "lsやcdのように『プログラム名+補足指定』で構成される"
    ),
    "実装": (
        "設計や仕様を、実際に動くコードに作り込むこと。"
        "「実装済み」＝コードとして完成している状態"
    ),
    "スクリプト": (
        "自動実行できる小さなプログラム。手順を書いたテキストファイルの形をしている"
    ),
    "ロック": (
        "複数の処理が同時に同じ対象を触って衝突するのを防ぐ「鍵」の仕組み。"
        "鍵を持っている間は他の処理は待つか諦める"
    ),
    "ディレクトリ": (
        "フォルダのこと。ファイルを階層的に整理する入れ物。"
        "Linux系ではフォルダをディレクトリと呼ぶのが普通"
    ),
    "設定ファイル": (
        "プログラムの動作を決める設定値を書いたファイル。"
        "コード本体を書き換えずに、設定だけ変えられるようにする"
    ),
    "デフォルト": (
        "指定がない時に自動的に使われる初期値・初期設定のこと"
    ),
    "ターミナル": (
        "文字だけでパソコンと対話する画面。コマンドを打ち込むと結果が文字で返ってくる。"
        "Claude Code CLIはここで動く"
    ),
    "変数展開": (
        "$HOME のように変数名が書かれた場所を、実際の値に置き換えること"
    ),
    "変数": (
        "値を入れておく名前付きの箱。x = 1 のように名前に値を紐付けて、後で使い回す"
    ),
    "仕様": (
        "「どう動くべきか」の取り決め。仕様書＝要件と動作の定義を書いた文書"
    ),
    "バグ": (
        "プログラムの不具合。意図しない動きを引き起こすコードの欠陥"
    ),
    "並列": (
        "複数の処理を同時に進めること。順番に1つずつやる「直列」の対義語"
    ),
    "ループ": (
        "同じ処理の繰り返し、または一連の作業サイクルのこと。"
        "プログラミングではfor文等の繰り返し構造、"
        "開発では「計画→実装→検証」の反復サイクルを指す"
    ),
    "プラグイン": (
        "本体に後から差し込んで機能を足す追加部品。Claude Codeにもプラグイン機構がある"
    ),
    "拡張機能": (
        "ソフト本体に後から足して機能を増やす追加部品。プラグインとほぼ同義"
    ),
    "バージョン": (
        "ソフトウェアやファイルの「どの時点の状態か」を示す番号。v1.2等。"
        "更新のたびに番号が上がる"
    ),
    "最適化": (
        "速さ・コスト・品質等の指標が良くなるように調整すること"
    ),
    "ライブラリ": (
        "よく使う機能をまとめて再利用可能にした部品集。"
        "作りかけの部品を組み込んで使うことで、同じものを一から作らずに済む"
    ),
    "差分": (
        "変更前後の違い。git diffのように「何がどう変わったか」を示すもの"
    ),
    "プロセス": (
        "動いているプログラム1つ1つの実体。番号（PID）で管理される"
    ),
    "テンプレート": (
        "雛形。穴埋め部分だけ差し替えて、同じ形の文書やコードを量産する元になるもの"
    ),
    "キュー": (
        "待ち行列。依頼された処理を順番に並べて、前から順に消化していく仕組み"
    ),
    "競合": (
        "複数の処理・人が同時に同じものを触って衝突すること。"
        "gitでは同時に同じファイルを編集すると競合（コンフリクト）が起きる"
    ),
    "引数": (
        "コマンドや関数に渡す補足の指定。ls -la の -la の部分のように、"
        "動作を細かく指示する値"
    ),
    "オプション": (
        "コマンドの動作を変えるスイッチ。-x や --verbose のような指定。引数の一種"
    ),
    "ワークフロー": (
        "一連の作業の流れ・手順の定義。GitHub Actionsでは自動実行の手順をこう呼ぶ"
    ),
    "フレームワーク": (
        "アプリを作るための骨組み部品のセット。土台が用意されているので、"
        "中身の作り込みに集中できる"
    ),
    "ビルド": (
        "ソースコードから、実行可能な完成品を組み立てること"
    ),
    "タイムアウト": (
        "待ち時間の上限。指定時間内に応答が無ければ「失敗」とみなして打ち切る仕組み"
    ),
    "関数": (
        "一連の処理をまとめて名前を付けたもの。呼び出すたびに同じ処理が実行される。"
        "プログラムの基本単位"
    ),
    "リリース": (
        "完成したものを外に出すこと。公開・出荷の意味"
    ),
    "パッケージ": (
        "配布・インストール可能な形にまとめたソフトウェアの単位。"
        "Pythonではpipで入れる部品のこと"
    ),
    "エディタ": (
        "テキストファイルを編集するソフト。VS CodeやVim等"
    ),
    "拡張子": (
        "ファイル名の末尾の「.md」「.py」等の部分。ファイルの種類を示す目印"
    ),
    "モック": (
        "テスト用の「偽物」。本物の代わりに決まった値を返すようにして、"
        "テスト対象だけを確実に検査できるようにする"
    ),
    "モジュール": (
        "コードを機能ごとに分けたファイル単位。他のファイルから読み込んで使える"
    ),
    "パース": (
        "文字で書かれたデータを、プログラムが扱える構造に変換すること。"
        "JSONパース＝JSON文字列→データ構造"
    ),
    "ドライラン": (
        "本番の処理はせずに「何をしたはずか」だけ確認する実行モード（Dry Run）。"
        "影響を与える前に動作予定の確認ができる"
    ),
    "スナップショット": (
        "ある瞬間の状態のコピー。後で比較・復元するために取っておくもの"
    ),
    "コンパイル": (
        "人が読むソースコードを、コンピュータが実行できる形式に変換すること"
    ),
    "クラス": (
        "データとその操作をひとまとめにした設計図。オブジェクト指向の基本単位"
    ),
    "依存関係": (
        "ある部品が別の部品に依存して動く関係。"
        "片方を変えるともう片方にも影響する繋がり"
    ),
    "再帰": (
        "関数が自分自身を呼び出す構造。入れ子の問題を扱う時に使うが、"
        "終了条件を忘れると無限ループになる"
    ),
    "回帰テスト": (
        "変更後に「以前動いていた機能が壊れていないか」を確認するテスト。"
        "直したつもりが別の場所を壊す事故の防止"
    ),
    "条件分岐": (
        "if文のように、条件によって実行する処理を変える構造"
    ),
}


# Mermaid図・コードブロックは用語ラップの対象外（構文破壊防止・2026-08-17）
_PROTECTED_BLOCK_RE = re.compile(
    r'(<div class="mermaid">.*?</div>|<pre>.*?</pre>|<code>.*?</code>)',
    re.DOTALL,
)


def wrap_terms(html: str) -> str:
    """登録用語の最初の出現箇所だけを、クリック解説付きマークアップで囲む.

    3フェーズ構成: (1) Mermaid図・コードブロックを退避 (2) 用語をプレースホルダー
    （\\x00TERM{n}\\x00）へ置換 (3) 全走査後に実マークアップと退避ブロックを差し戻し。
    これにより (1) 挿入済みpopup内の説明文が後続用語で再ラップされるネスト
    (2) 「FastAPI」が「API」で二重ラップされる部分一致
    (3) Mermaid図のソースとコード表示への混入による構文破壊
    を構造的に防ぐ（(3)は2026-08-17 01-basicsのmermaid構文エラーの修正）。
    """
    import html as html_mod

    blocks: list[str] = []

    def _stash(m: "re.Match[str]") -> str:
        blocks.append(m.group(1))
        return f"\x01BLOCK{len(blocks) - 1}\x01"

    html = _PROTECTED_BLOCK_RE.sub(_stash, html)

    wraps: dict[str, str] = {}
    for i, (term, desc) in enumerate(TERM_TOOLTIPS.items()):
        if term in html:
            ph = f"\x00TERM{i}\x00"
            wraps[ph] = (
                f'<span class="term" tabindex="0">{term}'
                f'<span class="term-popup">{html_mod.escape(desc)}</span></span>'
            )
            html = html.replace(term, ph, 1)
    for ph, wrapped in wraps.items():
        html = html.replace(ph, wrapped)
    for i, block in enumerate(blocks):
        html = html.replace(f"\x01BLOCK{i}\x01", block)
    return html


def convert_tldr(html: str) -> str:
    """H1直後の『3行で分かる』blockquote を <aside class="tldr"> に変換.

    平易化（2026-07-03）: 各ページH1直後に置いた `> **3行で分かる**` blockquoteを
    目立つTLDR枠に変換する。enhance_html の単一段落callout変換（<blockquote><p>…</p></blockquote>）
    にマッチしない複数要素blockquoteを対象とするため、enhance_html の後に呼ぶこと。
    H1直後の最初のblockquoteのみ（位置保証）。'3行で分かる' を含まなければ変換しない（後方互換）。
    """
    pattern = re.compile(
        r'(<h1[^>]*>.*?</h1>\s*)(<blockquote>.*?</blockquote>)',
        re.DOTALL,
    )
    m = pattern.search(html)
    if not m:
        return html
    head, block = m.group(1), m.group(2)
    if '3行で分かる' not in block:
        return html
    inner = block[len('<blockquote>'):-len('</blockquote>')]
    converted = head + f'<aside class="tldr">{inner}</aside>'
    return html[:m.start()] + converted + html[m.end():]


# --- トップページのカテゴリ分け ---

# 章番号→カテゴリの境界（番号レンジは閉区間）
INDEX_CATEGORIES = [
    ("🏗️ 基礎・仕組み", 0, 9),
    ("📖 参考・実践知見", 10, 11),
    ("🛠️ 個人運用・カスタムワークフロー", 12, 17),
]
INDEX_CATEGORY_FALLBACK = "📚 リソース"


def group_chapters_by_category(chapters: list) -> list:
    """章番号レンジに基づき、トップページ表示用にカテゴリへグルーピング."""
    buckets = {name: [] for name, _, _ in INDEX_CATEGORIES}
    buckets[INDEX_CATEGORY_FALLBACK] = []

    for ch in chapters:
        number = ch["number"]
        category_name = INDEX_CATEGORY_FALLBACK
        if number.isdigit():
            n = int(number)
            for name, lo, hi in INDEX_CATEGORIES:
                if lo <= n <= hi:
                    category_name = name
                    break
        buckets[category_name].append(ch)

    ordered_names = [name for name, _, _ in INDEX_CATEGORIES] + [INDEX_CATEGORY_FALLBACK]
    return [{"name": name, "chapters": buckets[name]} for name in ordered_names if buckets[name]]


# --- メイン ---

def main():
    # ディレクトリ準備
    chapters_dir = OUTPUT_DIR / "chapters"
    assets_dir = OUTPUT_DIR / "assets"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 章リストを構築（自動スキャン込み）
    effective_map = build_chapter_map()
    chapters = []
    for filename, info in sorted(effective_map.items()):
        chapters.append({
            "number": info["slug"][:2],
            "slug": info["slug"],
            "title": info["title"],
            "icon": info["icon"],
            "desc": info["desc"],
            "filename": filename,
        })

    # 各章を変換
    for i, ch in enumerate(chapters):
        src = SOURCE_DIR / ch["filename"]
        if not src.exists():
            print(f"SKIP: {ch['filename']} not found")
            continue

        md_text = src.read_text(encoding="utf-8")
        md_text = filter_sections(md_text)
        html_body = convert_md_to_html(md_text)
        html_body = inject_mermaid(html_body, ch["filename"])
        html_body = rewrite_links(html_body, effective_map)
        html_body = convert_tldr(html_body)
        html_body = enhance_html(html_body)
        html_body = wrap_terms(html_body)

        prev_ch = chapters[i - 1] if i > 0 else None
        next_ch = chapters[i + 1] if i < len(chapters) - 1 else None

        full_html = CHAPTER_TEMPLATE.render(
            title=ch["title"],
            slug=ch["slug"],
            current_slug=ch["slug"],
            content=html_body,
            chapters=chapters,
            prev_ch=prev_ch,
            next_ch=next_ch,
        )

        out = chapters_dir / f"{ch['slug']}.html"
        out.write_text(full_html, encoding="utf-8")
        print(f"OK: {ch['slug']}.html")

    # index.html 生成（カテゴリ分けして表示）
    categories = group_chapters_by_category(chapters)
    index_html = INDEX_TEMPLATE.render(categories=categories)
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("OK: index.html")

    print(f"\n完了: {len(chapters)}章 + index → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
