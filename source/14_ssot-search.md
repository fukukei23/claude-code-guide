# 14 SSOTから探して — 個人ナレッジベースへのRAG検索

> **3行で分かる**
> 1. Claude Code から個人ナレッジベース（knowledge-base）を横断検索するスキル
> 2. ripgrep + sentence-transformers のハイブリッド RAG・関連文書を5件表示
> 3. 「SSOTから探して: キーワード」と話しかけるだけで1900件超から検索

---

> Claude Codeから obsidian-ssot（個人ナレッジベース）を横断検索するスキル。ripgrep + sentence-transformers のハイブリッドRAG構成。

---

## 概要：これは何か {#overview}

「SSOTから探して: glm-rate-proxy」と話しかけると、1,900件超のMarkdownファイルを横断検索して関連ドキュメントを5件表示するスキルです。

```
あなた: SSOTから探して: MiniMaxのフォールバック設定

Claude: 🔍 SSOT検索: 「MiniMax フォールバック 設定」— 5件ヒット
  1. 📋 DECISIONS  01_DECISIONS/claude-code/2026-05-11_...
  2. 📅 DAILY      10_DAILY/2026-05-11.md
  ...
```

### RAGとは
**R**etrieval-**A**ugmented **G**eneration（検索拡張生成）の略。LLMに回答させる前に関連文書を検索してプロンプトに渡す仕組みです。専用のベクトルDBなしで、ファイルシステム上で軽量に実現しています。

---

## アーキテクチャ {#architecture}

```
ユーザーの質問
    │
    ▼
① ripgrep 全文検索（~0.5秒）
   ├─ フェーズ1: フレーズ完全一致
   └─ フェーズ2: ヒット不足 → トークンOR検索（日本語対応）
    │
    ▼
② sentence-transformers rerank（~1秒）
   all-MiniLM-L6-v2 でコサイン類似度を計算
    │
    ▼
③ 上位5件を層別表示
   📋 DECISIONS / 📅 DAILY / 🔧 SYSTEM / 💼 CAREER ...
```

### キーワード検索と意味的検索の違い

| | キーワード検索のみ | ハイブリッド（本構成）|
|---|---|---|
| 「glm-rate-proxy」 | ◎ ヒット | ◎ ヒット |
| 「プロキシ レートリミット」 | ◯ 部分ヒット | ◎ ヒット |
| 「429エラーの対処」→「glm-rate-proxy」 | ✗ ミス | ◎ ヒット |

---

## セットアップ {#setup}

### 1. ripgrep インストール

```bash
sudo apt-get install -y ripgrep
```

### 2. Python venv 作成

```bash
sudo apt-get install -y python3.12-venv
python3 -m venv ~/.claude/venv/ssot-search
~/.claude/venv/ssot-search/bin/pip install sentence-transformers
```

> **注意**: Python 3.12以降はシステムへの直接 `pip install` がブロックされます（PEP 668）。必ずvenvを使うこと。

### 3. スクリプト配置

`~/projects/claude-config/scripts/ssot/search.py` が  
`~/.claude/scripts/ssot/search.py` にシンボリックリンクされていることを確認:

```bash
ls -la ~/.claude/scripts/ssot/
```

### 4. スキル定義確認

```bash
cat ~/.claude/skills/ssot-search/SKILL.md
```

---

## 使い方 {#usage}

### 基本

```
SSOTから探して: <キーワード>
SSOT検索: <キーワード>
/ssot-search <キーワード>
```

### 例

```
SSOTから探して: glm-rate-proxy の設定
SSOTから探して: openclaw-stack 設計方針
SSOTから探して: Zenn記事 LLMルーティング
SSOTから探して: MiniMax フォールバック
```

### 件数を増やす

ClaudeにBashコマンドを直接実行させる場合:

```bash
~/.claude/venv/ssot-search/bin/python3 ~/.claude/scripts/ssot/search.py "クエリ" --top 10
```

---

## 日本語クエリのコツ {#japanese}

スペース区切りでキーワードを並べると精度が上がります:

```
# よりよい
SSOTから探して: MiniMax フォールバック 設定

# 動くが精度が落ちる場合も
SSOTから探して: MiniMaxのフォールバック設定方法
```

スペースなしでも内部でトークン分割（助詞・英数字境界で分割）するため多くの場合動作します。

---

## 内部動作の詳細 {#internals}

### search.py の処理フロー

```python
# 1. ripgrep でフレーズ検索
hits = rg_search(query, ssot_dir, max_files=80)

# 2. 不足時はトークンOR検索で補完
if len(hits) < 80:
    tokens = _tokenize(query)  # 助詞・英数字境界で分割
    hits += rg_search("|".join(tokens), ...)

# 3. sentence-transformers でrerank
results = rerank(query, hits, top_n=5)
```

### 日本語トークナイザ

```python
DELIMITERS = r"[\s　のをがはにでもとからまでよりへ、。・]+"
# さらに英数字↔日本語境界でも分割
# 例: "MiniMaxのAPI" → ["MiniMax", "API"]
```

### 使用モデル

| 項目 | 内容 |
|---|---|
| モデル | `all-MiniLM-L6-v2` |
| サイズ | ~80MB（初回実行時に自動DL） |
| 速度 | rerank ~1秒（CPU） |
| 依存 | PyTorch 2.12.0 込み |

---

## トラブルシューティング {#troubleshoot}

### `ModuleNotFoundError: No module named 'sentence_transformers'`

venvが使われていません:

```bash
# 正しい実行方法
~/.claude/venv/ssot-search/bin/python3 ~/.claude/scripts/ssot/search.py "クエリ"
```

### `rg: command not found`

```bash
sudo apt-get install -y ripgrep
```

### 検索結果が0件

クエリが長すぎてripgrepが完全一致できない場合。スペース区切りで短いキーワードに分割してください。

### `apt-get install` が数十分ハング

バックグラウンドでのsudoコマンドはaptロック競合で止まることがあります。WSLターミナルで直接実行してください。

---

## 💡 やさしい補足（初心者向け）

- **「SSOT検索」= メモの山を探す機能**: ため込んだメモ（SSOT）から、欲しい情報を日本語で探せる
- **日本語で聞ける**: 「〇〇について書いたメモある？」と聞くと、該当箇所を探してくれる
- **探す時間を省ける**: 手動でフォルダを漁る代わりに、一発で見つけられる
- **内部の仕組み**: 詳細は上の章。普段は「検索したい時に使う」とだけ覚えればOK

---

## 関連ファイル {#files}

| ファイル | 役割 |
|---|---|
| `~/.claude/scripts/ssot/search.py` | 検索スクリプト本体 |
| `~/.claude/skills/ssot-search/SKILL.md` | スキル定義（トリガーワード等）|
| `~/.claude/venv/ssot-search/` | Python仮想環境 |
| `~/projects/claude-config/scripts/ssot/` | スクリプトのソース（シンボリックリンク元）|
| `~/projects/claude-config/skills/ssot-search/` | スキルのソース |
