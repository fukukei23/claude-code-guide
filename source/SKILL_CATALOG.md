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

## 📝 SSOT・記録・検索

| Skill | 説明 | トリガー |
|---|---|---|
| `ssot-record` | SSOTへの記録・振り分け自動化。タグマッピングからプロジェクト側docs更新も自動検出 | 「記録して」「書き留めて」「SSOTに入れて」 |
| `record-decision` | ⚠️ 非推奨（ssot-record に統合済み）。`/record-decision` は ssot-record に委譲 | `/record-decision` |
| `ssot-search` | 個人ナレッジベース（obsidian-ssot）をRAG検索。1,900件超から関連5件表示 | 「SSOTから探して」「SSOT検索」 |
| `ssot-sync` | SSOTと実ファイル/設定の整合性チェック。乖離があれば修正 | 「SSOT整合性チェックして」「乖離を修正して」 |
| `record-new-feature` | Claude Code新バージョンのリリースノートを調査しSSOTとガイドに追記 | SessionStart hookで自動発動 |

## 📚 ガイド・文書作成

| Skill | 説明 | トリガー |
|---|---|---|
| `guide-builder` | Markdownソース→GitHub Pagesガイドサイト構築・更新（new/add 2モード） | 「ガイド作って」「章追加して」`/guide-builder` |
| `html-guide` | claude-code-guide用インタラクティブHTMLページ作成 | 「新しいHTMLページを作って」`/html-guide` |
| `textbook-guide` | 語彙帳・教科書・チートシート型HTMLガイドを新規作成・章追加 | 「語彙帳作って」「チートシート作って」`/textbook-guide` |
| `add-term-tooltip` | HTMLページの専門用語にホバーで解説が出るツールチップを追加 | 「ツールチップ追加して」「用語に解説つけて」 |
| `zenn-article-pipeline` | Zenn記事の作成〜公開前チェックを6ステップで実行するパイプライン | `/zenn-article-pipeline` |
| `x-post-draft` | Zenn公開時にX（旧Twitter）投稿用文案を複数パターン生成（手動コピペ前提） | Zenn記事公開時 |

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
| `remove-huadian` | AI生成の古代中国女性画像に強制付加される花鈿（眉間の赤点）を画像処理で除去 | 「花鈿除去」「赤点消して」`/remove-huadian` |

---

## Built-in / Plugin Skills

ビルトイン（`init` / `review` / `security-review` / `simplify` / `update-config` / `claude-api` / `loop` / `verify` / `run` 等）とプラグイン（`superpowers` / `pr-review-toolkit` / `code-review` / `feature-dev` / `skill-creator` 等）の全一覧は [03_スキルシステム](03_スキルシステム.md) 参照。
