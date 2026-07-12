# 14 SSOT — 個人ナレッジベースを使いこなす

> **3行で分かる**
> 1. SSOT（Single Source of Truth）は個人の判断・決定・知見を集約する知識ベース
> 2. 3つのスキル（record / search / check）で運用する
> 3. この章ではSSOT全般の使い方を説明し、詳細は各スキルの折りたたみへ

---

## SSOTとは？

**SSOT** = **S**ingle **S**ource **o**f **T**ruth（真実の単一情報源）

個人の判断・決定・知見・設計判断をすべて集約する知識ベースです。AI駆動開発では、Claude Codeがセッションをまたいで同じ判断を再現できるよう、SSOTを「長期記憶」として活用します。

### なぜSSOTが必要か

- **判断の再現性**: 「なぜそうしたか」を毎回考え直さなくて済む
- **セッション跨ぎ**: 別日・別セッションでも同じ判断を引き継げる
- **AIの記憶**: Claude Codeに過去の判断を自動で参照させる

---

## 3つの基本スキル（使い分け早見表）

SSOT運用は3つのスキルで完結します:

| スキル | いつ使う？ | トリガー例 |
|---|---|---|
| **ssot-record** | 作業内容・決定を記録したい | 「記録して」「保存して」「メモして」 |
| **ssot-search** | 過去の情報を探したい | 「SSOTから探して: キーワード」「SSOT検索」 |
| **ssot-check** | SSOTが古いか確認したい | 「SSOT整理して」「乖離を直して」「00_SYSTEM更新して」 |

---

## 使い分けフロー

```
「いま何をしたい？」
    │
    ├─ 記録したい → ssot-record
    │              └ 内容を分析→振り分け→自動記録
    │
    ├─ 探したい  → ssot-search
    │              └ 全文検索＋意味的検索で関連文書5件表示
    │
    └─ 確認したい → ssot-check
                   └ 00_SYSTEM/の設定と実態を照合・修正提案
```

---

## 各スキルの詳細

### 📝 ssot-record（記録）

**トリガーワード**:
- 「記録して」「保存して」「メモして」
- 「SSOTに入れて」「ガイドに追加して」

**やること**:
1. 内容をGLMが分析
2. 機密レベル・想定寿命・削除可能性・検索優先度から保管場所を判定
3. 01_DECISIONS/または適切な場所に保存
4. _INDEX.md追記・日記追記・ガイド転記まで一括実行

**詳細は**: [ssot-guide 03 SSOT - SSOTレコード](https://fukukei23.github.io/ssot-guide/#ssot-record)

---

### 🔍 ssot-search（検索）

**トリガーワード**:
- 「SSOTから探して」「SSOT検索」
- 「SSOTから探して: キーワード」

**やること**:
1. ripgrep全文検索（~0.5秒）
2. sentence-transformersでrerank（~1秒）
3. 関連文書を上位5件表示

**詳細**:

### 概要

「SSOTから探して: glm-rate-proxy」と話しかけると、1,900件超のMarkdownファイルを横断検索して関連ドキュメントを5件表示するスキルです。

```
あなた: SSOTから探して: MiniMaxのフォールバック設定

Claude: 🔍 SSOT検索: 「MiniMax フォールバック 設定」— 5件ヒット
  1. 📋 DECISIONS  01_DECISIONS/claude-code/2026-05-11_...
  2. 📅 DAILY      10_DAILY/2026-05-11.md
  ...
```

### アーキテクチャ

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

### セットアップ

```bash
# ripgrep インストール
sudo apt-get install -y ripgrep

# Python venv 作成
sudo apt-get install -y python3.12-venv
python3 -m venv ~/.claude/venv/ssot-search
~/.claude/venv/ssot-search/bin/pip install sentence-transformers
```

> **注意**: Python 3.12以降はシステムへの直接 `pip install` がブロックされます（PEP 668）。必ずvenvを使うこと。

### 使い方

```
SSOTから探して: <キーワード>
SSOT検索: <キーワード>
/ssot-search <キーワード>
```

**例**:
```
SSOTから探して: glm-rate-proxy の設定
SSOTから探して: openclaw-stack 設計方針
SSOTから探して: Zenn記事 LLMルーティング
SSOTから探して: MiniMax フォールバック
```

### 日本語クエリのコツ

スペース区切りでキーワードを並べると精度が上がります:

```
# よりよい
SSOTから探して: MiniMax フォールバック 設定

# 動くが精度が落ちる場合も
SSOTから探して: MiniMaxのフォールバック設定方法
```

### 内部動作の詳細

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

### トラブルシューティング

- `ModuleNotFoundError: No module named 'sentence_transformers'` → venvを使ってるか確認
- `rg: command not found` → `sudo apt-get install -y ripgrep`
- 検索結果が0件 → クエリを短く・スペース区切りに分割

### 💡 やさしい補足

- **「SSOT検索」= メモの山を探す機能**: ため込んだメモ（SSOT）から、欲しい情報を日本語で探せる
- **日本語で聞ける**: 「〇〇について書いたメモある？」と聞くと、該当箇所を探してくれる
- **探す時間を省ける**: 手動でフォルダを漁る代わりに、一発で見つけられる

---

### 🔧 ssot-check（整合性）

**トリガーワード**:
- 「SSOT整合性チェックして」「SSOT整理して」「SSOT同期して」
- 「SSOTのズレを直して」「00_SYSTEM更新して」「乖離を修正して」

**やること**:
1. 00_SYSTEM/配下の設定ファイルと実態を照合
2. 乖離があれば自動修正 or 修正提案
3. 対話モードでの深掘り検証

**チェック対象**:
- `00_SYSTEM/自動化.md` — hooks/cron/スクリプトの記載漏れ
- `00_SYSTEM/repo-index.yaml` — リポジトリ数・visibility・last_updated
- `00_SYSTEM/MCPツール使い分けガイド.md` — 有効サーバー数
- `00_SYSTEM/全体マップ_MOC.md` — リポジトリ数・プロジェクト一覧
- `00_SYSTEM/チャーター.md` — 禁止操作リスト

**乖離パターン**:
- 設計変更後の記述未更新
- リポジトリ/プロジェクト追加時のindex未追記
- Cron実体の増減と記述のズレ（ゴーストCron等）

**詳細は**: [ssot-guide 03 SSOT - SSOTチェック](https://fukukei23.github.io/ssot-guide/#ssot-check)

---

## 特性カタログ（保管場所の分類基準）

SSOTには9つの保管場所があります。**⭐ `00_SYSTEM/` は最重要**で、SSOT全体の構造・ルール・自動化の正典がここに集約されています。内容を分析して適切な場所に振り分けます。

| 場所 | 機密レベル | 想定寿命 | 検索優先度 | 用途 |
|---|---|---|---|---|
| ⭐ **`00_SYSTEM/`** | 低 | 長期 | 中 | **最重要**：全体マップ・共通ルール・自動化・設定の正典 |
| **01_DECISIONS/<project>** | 中〜高 | 長期 | 高 | 決定ログ・技術詳細・なぜそうしたか |
| **10_DAILY/YYYY-MM-DD** | 低〜中 | 短期 | 中 | 日次サマリー・セッションログ |
| **30_RESEARCH/** | 中 | 中期 | 低〜中 | 参考資料・調査結果 |
| **バックログ.md** | 低〜中 | 中期 | 中 | 未完了タスク・WIP構想 |
| **20_PUBLISHING/** | 高 | 短期 | 低 | 外部公開コンテンツ |
| **プロジェクト固有** | プロジェクト依存 | 短期〜中期 | 低〜中 | プロジェクト固有のドキュメント |
| **メモリ** | 中 | 短期 | 高 | セッション中のコンテキスト |
| **feedback_*.md** | 低〜中 | 中期 | 低〜中 | ユーザー指摘・好みのパターン |

**判定基準**: 機密レベル × 想定寿命 × 削除可能性 × 検索優先度

**詳細は**: [ssot-guide 03 SSOT - 特性カタログ](https://fukukei23.github.io/ssot-guide/#特性カタログ)

---

## 💡 やさしい補足（初心者向け）

- **SSOT = 自分の判断を覚えておくノート**: 毎日書いているとAIが「前にそうしたよね」と言ってくれる
- **3スキルで運用**: 記録（書く）・検索（探す）・チェック（整える）の3つだけ覚えればOK
- **迷ったら record から**: 何か新しいことをしたら、まず「記録して」と言う癖をつける
- **定期的に check**: 月金に `ssot-check auto` で自動整理しておくとSSOTが腐らない

---

## 関連ファイル

| ファイル | 役割 |
|---|---|
| `~/.claude/skills/ssot-record/SKILL.md` | 記録スキルの定義 |
| `~/.claude/skills/ssot-search/SKILL.md` | 検索スキルの定義 |
| `~/.claude/skills/ssot-check/SKILL.md` | 整合性チェックスキルの定義 |

---

## 関連章

- [15 auto-sync改善](15_auto-sync改善.md) — 自動化・設定の整合性チェック
- [16 record-decision](16_record-decision.md) — 単一決定の記録
- [17 sentaku](17_sentaku.md) — 選択肢の深掘り比較
