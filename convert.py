#!/usr/bin/env python3
"""Claude Code Guide: Markdown → モバイル最適化HTML変換スクリプト."""

import re
from pathlib import Path

from jinja2 import Template
from markdown_it import MarkdownIt

# --- 設定 ---

SOURCE_DIR = Path(__file__).parent / "source"
OUTPUT_DIR = Path(__file__).parent / "docs"

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
}

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
    A["📋 タスク受付"] --> B{"GLM-5.1<br/>デフォルト"}
    B -->|"成功"| C["✅ 結果返却"]
    B -->|"失敗"| D{"MiniMax<br/>フォールバック"}
    D -->|"成功"| C
    B -->|"大量処理"| E["MiniMaxに委譲"]
    E --> C
    B -->|"高品質必要"| F{"👤 ユーザー許可"}
    F -->|"許可"| G["Sonnetで処理"]
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
            {{ content }}
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
""")

INDEX_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="ja" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code 完全ガイド</title>
    <meta name="description" content="AIコーディングアシスタント Claude Code CLI の使い方を基礎から応用まで完全解説">
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
            <p>AIコーディングアシスタント Claude Code CLI の使い方を、<br>基礎から応用まで完全解説</p>
        </section>

        <section class="chapter-grid">
            {% for ch in chapters %}
            <a href="chapters/{{ ch.slug }}.html" class="chapter-card">
                <div class="card-icon">{{ ch.icon }}</div>
                <div class="card-number">第{{ ch.number }}章</div>
                <h2 class="card-title">{{ ch.title }}</h2>
                <p class="card-desc">{{ ch.desc }}</p>
            </a>
            {% endfor %}
        </section>

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
                    <p>スマホからいつでも見返せるレスポンシブ设计</p>
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
        <p>Claude Code Guide — <a href="https://github.com/fukukei23/claude-code-guide">GitHub</a></p>
    </footer>

    <script src="assets/script.js"></script>
</body>
</html>
""")


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
    text = text.replace("yn4416", "<USER>")
    text = text.replace("fukukei23", "<USERNAME>")
    text = text.replace("fukukei", "<USERNAME>")

    return text


# --- Markdown → HTML変換 ---

def convert_md_to_html(md_text: str) -> str:
    """MarkdownをHTMLに変換."""
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    return md.render(md_text)


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

        # <h2>テキスト</h2> または <h2><a ...></a>テキスト</h2> の前に挿入
        pattern = f"(<h2>(?:<a[^>]*></a>)?{re.escape(heading_text)}</h2>)"
        if re.search(pattern, html):
            html = re.sub(pattern, mermaid_block + r"\1", html, count=1)

    return html


def rewrite_links(html: str) -> str:
    """内部リンクをHTML URLに書き換え."""
    from urllib.parse import quote, unquote

    for filename, info in CHAPTER_MAP.items():
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
        for filename, info in CHAPTER_MAP.items():
            # hrefの中にファイル名が含まれているか
            decoded = unquote(href)
            if filename in decoded or filename in href:
                anchor = ""
                if "#" in href:
                    anchor = "#" + href.split("#", 1)[1]
                elif "#" in decoded:
                    anchor = "#" + decoded.split("#", 1)[1]
                return f'href="{info["slug"]}.html{anchor}"'
        return f'href="#"'

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


# --- メイン ---

def main():
    # ディレクトリ準備
    chapters_dir = OUTPUT_DIR / "chapters"
    assets_dir = OUTPUT_DIR / "assets"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 章リストを構築
    chapters = []
    for filename, info in sorted(CHAPTER_MAP.items()):
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
        html_body = rewrite_links(html_body)
        html_body = enhance_html(html_body)

        prev_ch = chapters[i - 1] if i > 0 else None
        next_ch = chapters[i + 1] if i < len(chapters) - 1 else None

        full_html = CHAPTER_TEMPLATE.render(
            title=ch["title"],
            current_slug=ch["slug"],
            content=html_body,
            chapters=chapters,
            prev_ch=prev_ch,
            next_ch=next_ch,
        )

        out = chapters_dir / f"{ch['slug']}.html"
        out.write_text(full_html, encoding="utf-8")
        print(f"OK: {ch['slug']}.html")

    # index.html 生成
    index_html = INDEX_TEMPLATE.render(chapters=chapters)
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("OK: index.html")

    print(f"\n完了: {len(chapters)}章 + index → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
