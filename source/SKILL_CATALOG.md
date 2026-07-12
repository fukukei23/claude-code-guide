# Skill カタログ

> 全スキルのファインダー。仕組み・自作方法は [03_スキルシステム](03_スキルシステム.md)、フェーズ別選択は [スキルマップ](https://fukukei23.github.io/claude-code-guide/chapters/16-skill-map.html) 参照。

## 🎵 楽曲・映像制作

| Skill | 説明 | トリガー |
|---|---|---|
| `make-song` | 任意ジャンル・テーマで曲+歌詞を高品質制作する汎用作曲エンジン（MiniMax music-2.6 主軸） | 「曲作って」「作曲して」`/make-song` |
| `cyber-wa-song` | サイバー和モダン3作品（原点廻帰/電子参拝/百鬼夜行）の楽曲+映像を質問ドリブンで制作 | 「サイバー和モダン」「原点廻帰」`/cyber-wa-song` |
| `sangoku-song` | 三国志武将のHIPHOP楽曲を武将選択から曲+歌詞+画像+動画まで制作するウィザード | 「武将で曲作って」「三国志」`/sangoku-song` |
| `reverse-engineer-song` | YouTube楽曲をリバースエンジニアリングし音楽/画像/動画の3モダリティ プロンプト仕様書を出力 | 「逆コンパイルして」「YouTubeから分析して」`/reverse-engineer-song` |
| `video-prompt-spec` | 入力を映像制作用4構造プロンプト仕様書（タイムライン/ビジュアル/画像/動画モーション）に変換 | 「映像プロンプト」「映像構成作って」`/video-prompt-spec` |
| `analyze-song` | 楽曲を音源から定量分析しBPM/キー/コード進行/メロディ輪郭/音域を抽出 | 「楽曲分析して」「曲を定量分析」「BPM/コード抽出」`/analyze-song` |

## 📝 SSOT・記録・検索

> **SSOTの全体像・使い分け・保管場所の分類基準は [14 SSOT](14_ssot-search.md) を参照**

| Skill | 説明 | トリガー |
|---|---|---|
| `ssot-record` | SSOTへの記録・振り分け自動化。タグマッピングからプロジェクト側docs更新も自動検出 | 「記録して」「書き留めて」「SSOTに入れて」 |
| `record-decision` | ⚠️ 非推奨（ssot-record に統合済み）。`/record-decision` は ssot-record に委譲 | `/record-decision` |
| `ssot-search` | 個人ナレッジベース（obsidian-ssot）をRAG検索。1,900件超から関連5件表示 | 「SSOTから探して」「SSOT検索」 |
| `ssot-check` | SSOTと実ファイル/設定の整合性チェック。乖離があれば自動修正・修正提案 | 「SSOT整合性チェックして」「SSOT整理して」「乖離を修正して」 |
| `record-new-feature` | Claude Code新バージョンのリリースノートを調査しSSOTとガイドに追記 | SessionStart hookで自動発動 |
| `codebase-memory` | コードをナレッジグラフ化し構造検索（呼び出し元/影響範囲/デッドコード/アーキテクチャ） | 「アーキテクチャ理解して」「呼び出し元を探して」「影響範囲」`/codebase-memory` |
| `resume-session` | セッション再開時に最新5件のhandoffを読み込み文脈復元。new-sessionの対 | 「おはよう」「こんにちは」「再開」`/resume-session` |

## 📚 ガイド・文書作成

| Skill | 説明 | トリガー |
|---|---|---|
| `guide-builder` | Markdownソース→GitHub Pagesガイドサイト構築・更新（new/add 2モード） | 「ガイド作って」「章追加して」`/guide-builder` |
| `html-guide` | claude-code-guide用インタラクティブHTMLページ作成 | 「新しいHTMLページを作って」`/html-guide` |
| `textbook-guide` | 語彙帳・教科書・チートシート型HTMLガイドを新規作成・章追加 | 「語彙帳作って」「チートシート作って」`/textbook-guide` |
| `add-term-tooltip` | HTMLページの専門用語にホバーで解説が出るツールチップを追加 | 「ツールチップ追加して」「用語に解説つけて」 |
| `zenn-article-pipeline` | Zenn記事の作成〜公開前チェックを6ステップで実行するパイプライン | `/zenn-article-pipeline` |
| `x-post-draft` | Zenn公開時にX（旧Twitter）投稿用文案を複数パターン生成（手動コピペ前提） | Zenn記事公開時 |
| `make-guide` | ガイド・教科書・チートシート・語彙帳作成の入口（読む系/引く系を判定し分岐） | 「ガイド作って」「教科書作って」「チートシート作って」`/make-guide` |

## 🔧 開発・運用・ユーティリティ

| Skill | 説明 | トリガー |
|---|---|---|
| `dev-cycle` | コード品質改善の全サイクル（品質スイープ→レビュー→Issue化→自律実装→通知）を自律実行 | 「dev-cycle」「品質改善」「自律ループ」`/dev-cycle` |
| `gas-autopilot` | Google Apps Scriptの自律開発。clasp管理・Web App+gas-run.shで自動デプロイ | 「GAS」「Apps Script」「スプレッドシート自動化」 |
| `skill-test` | スキル定義（SKILL.md）を静的点検・ドライランで検証。`/debug`（コード向け）と使い分け | 「スキルを点検して」「スキルのバグ確認」`/skill-test` |
| `new-session` | コンテキスト圧縮・セッション引き継ぎプロンプトを生成 | 「新セッション」「引き継ぎ」`/new-session` |
| `update-guide` | claude-code-guideの更新キューを処理しHTMLを最新化 | `/update-guide` |
| `proxy-doctor` | glm-rate-proxy（localhost:8787）の診断・修復。症状A〜Jに振り分け対処案内 | 「プロキシが壊れた」「GLMが使えない」「proxy止まってる」`/proxy-doctor` |
| `send-email` | Gmail SMTP経由でメール送信。宛先・件名・本文を文脈から自動収集 | 「メールで送って」「email送信」`/send-email` |
| `teian` | 軽量提案。2〜3の選択肢+メリデメ+推奨案をさっと提示。複雑ならbrainstormingへ誘導 | 「提案して」「どう思う」「教えて」 |
| `sentaku` | 選択肢(A/B/C)の深掘り比較→淘汰→推奨。teian(浅)とbrainstorming(深)の間 | 「比較して」「深掘りして」「メリデメ教えて」「徹底的に」`/sentaku` |
| `remove-huadian` | AI生成の古代中国女性画像に強制付加される花鈿（眉間の赤点）を画像処理で除去 | 「花鈿除去」「赤点消して」`/remove-huadian` |
| `demo-site-sales` | ホームページない店舗向けデモサイト(HTML)+営業文面を自動生成（送信は手動） | 「デモサイト作って」「Web制作の新規開拓」`/demo-site-sales` |

---

## Built-in / Plugin Skills

ビルトイン（`init` / `review` / `security-review` / `simplify` / `update-config` / `claude-api` / `loop` / `verify` / `run` 等）とプラグイン（`superpowers` / `pr-review-toolkit` / `code-review` / `feature-dev` / `skill-creator` 等）の全一覧は [03_スキルシステム](03_スキルシステム.md) 参照。

---

## 💡 やさしい補足（初心者向け）

- このページは「使えるスキルの一覧表」。何ができるかざっと見たい時に
- 分野別に分類: 楽曲制作・記録・ガイド作成・開発 等
- 各スキルの詳しい使い方は [03_スキルシステム](03_スキルシステム.md) で
- 「こんなことできないかな？」と思ったら、ここを眺めて探す
