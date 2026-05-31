# Claude Code Guide

Claude Code の使い方を基礎から応用まで完全解説するモバイル対応HTMLガイド。

## URL

https://fukukei23.github.io/claude-code-guide/

## 構成

- `source/` — 元Markdownファイル
- `convert.py` — Markdown→HTML変換スクリプト
- `docs/` — 生成されたHTML（GitHub Pages）
- `assets/` — CSS・JS

## 新しい章の追加方法

`source/` にMDファイルを置いてコミットするだけ。**手動でのHTML編集・CHAPTER_MAP更新は不要。**

```bash
# 1. MDファイルを source/ に作る（番号_タイトル.md の形式）
vim source/15_新機能.md

# 2. コミットするだけ（pre-commit hookが自動発火）
git add source/15_新機能.md
git commit -m "add: 第15章"
# → convert.py が自動実行 → HTML全生成 → index.html更新 → 全部コミット済み

# 3. push
git push
```

### タイトル・アイコン・説明の自動取得

| 情報 | 取得元（優先順） |
|---|---|
| タイトル | フロントマター `title:` → H1の章番号除去・ダッシュ前 |
| 説明文 | フロントマター `card_desc:` → H1のダッシュ以降 |
| アイコン | フロントマター `icon:` → デフォルト `📄` |

カスタマイズしたい場合はMDにフロントマターを追加：

```markdown
---
icon: 🚀
card_desc: 説明文（index.htmlのカードに表示される）
---

# 15 章タイトル — サブタイトル
```

または `convert.py` の `CHAPTER_MAP` に1行追加でも対応可。

## ローカル開発

```bash
pip install markdown-it-py jinja2
python3 convert.py
# docs/index.html をブラウザで開く
```

## ライセンス

MIT
