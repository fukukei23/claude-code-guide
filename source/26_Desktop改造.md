---
title: Claude Code Desktop 改造
icon: 🔧
slug: 26-desktop-mod
card_desc: サードパーティ推論（3Pモード）でDesktopアプリの推論エンジンをGLM/MiniMaxに差し替える — サブスク⇔Gatewayの両方向切替手順と公式ドキュメント照合済みの既知仕様
---

# 26 Claude Code Desktop 改造 — 3P推論でGLM/MiniMaxを使う

> 最終更新: 2026-11-05 | 対象: Claude Desktopアプリ（Windows/Mac・Codeタブ付き）・公式ドキュメント照合済み

## この章の目的

Claude Desktopアプリの推論リクエストの送信先は設定で差し替えられる。本章では推論エンジンを **サブスクログイン ⇔ 自前Gateway（GLM/MiniMaxプロキシ）** の間で往復させる手順と、そこで判明した仕様を1ページにまとめる。

**結論**: Gatewayへ向けるのは設定ウィンドウのGUIで完結。サブスクへ戻すのは **設定の削除＋再起動** が正規ルート。**ドロップダウンに「サブスクへ戻す」選択肢は存在しない**（1P/3P切替の専用UIは未実装・公式ドキュメント照合・2026-11-05時点）。

---

## 概要: なぜ・何ができるか

### 3P推論モードとは

Claude Desktopアプリはサードパーティ推論（third-party inference・3Pモード）を公式にサポートしている。設定ウィンドウ（「サードパーティ推論の設定」→「接続」）で送信先を指定すると、アプリ全体の推論がそこへ向く。

| | 標準モード（サブスク） | 3Pモード |
|---|---|---|
| 認証 | claude.ai ログイン（Pro/Max） | 設定した認証情報のみ |
| 課金 | サブスク枠の消費 | 設定先に依存（従量課金・自前プロキシ等） |
| 推論先 | Anthropic | Gateway・APIキーで指定した先 |
| フォールバック | — | **なし**（設定したソースのみ使用） |

設定画面の注意書き通り「認証情報ソースを選択します。設定すると、そのソースのみが使用されます（フォールバックなし）」。つまり3P設定が存在する限り、サブスク側へは自動フォールバックしない。

### 何ができるか・なぜ「改造」と呼ぶか

- Desktopアプリの推論を **GLM/MiniMaxなど安価なモデル** に差し替え、コード・チャットを低コストで回せる
- 週間クォータが枯渇したプロキシ側から **サブスクへ一時退避** し、枠が回復したらまた戻す、という運用ができる
- 一般ユーザーはあまり行わない構成（公式の1P/3P切替UIは未実装・GitHub上で要望が存在する状態）で、「設定ファイルを書き換えてアプリの挙動を変える」点で改造に近い

### 前提

- [18章 GLM Rate Proxy](18-glm-rate-proxy.html) で構築したプロキシ（`http://localhost:8787`）が動いていること（本章はプロキシの作り方には踏み込まない）
- 設定変更のたびに **アプリが再起動する** ため、作業中のCodeタブセッションが消えてよいタイミングで実施する

---

## 接続の仕組み

### 設定ファイルを開く

設定ウィンドウの **Developer → Open Developer Config File** で推論設定のJSONファイルが開く。実際の設定例（Gateway・GLM運用時）:

```json
{
  "inferenceGatewayBaseUrl": "http://localhost:8787",
  "inferenceGatewayApiKey": "<ゲートウェイAPIキー>",
  "modelDiscoveryEnabled": false,
  "modelPrefer1mContext": true,
  "inferenceModels": [
    {
      "name": "claude-sonnet-5",
      "labelOverride": "GLM（プロキシ経由）",
      "supports1m": true,
      "prefer1m": true
    }
  ],
  "inferenceModelPricingEnabled": true,
  "inferenceProvider": "gateway",
  "inferenceCredentialKind": "static"
}
```

設定ウィンドウの「エクスポート」ボタンでこのJSONをファイル保存でき、「インポート」で復元できる。切替のたびに再入力しないためにも、両方向の設定JSONを保存しておくと楽。

### inferenceProvider の値一覧

| 値 | 意味 | 認証 |
|---|---|---|
| **（未設定）** | 標準モード＝サブスクログイン | claude.aiログイン |
| `gateway` | 自前Gateway | 静的APIキー・認証スキーム（bearer / x-api-key） |
| `anthropic` | Claude API | **Console**サインイン or `sk-ant-` キー（Console＝API従量課金の**別アカウント**・claude.aiサブスクとは紐づかない） |
| `bedrock` / `mantle` / `vertex` / `foundry` | 各クラウドのマネージド版 | 各クラウドの認証 |

**未設定＝標準モード** が公式リファレンスの定義（「When this key is unset, the app opens in standard mode」）。「デフォルト＝サブスク」に対応する値は存在せず、**戻すには設定自体を消す**。

### 認証体系の違い（最重要の注意点）

設定ウィンドウの選択肢にある「Claude API」は **サブスクではありません**。

| 経路 | 課金体系 | サブスク枠が使えるか |
|---|---|---|
| claude.aiログイン（標準モード） | Pro/Maxサブスク | ✅ 使える |
| Claude API（`anthropic`） | Anthropic Console組織の**従量課金** | ❌ 使えない |
| Gateway（自前プロキシ） | プロキシ先の料金（GLM/MiniMax等） | ❌ 別体系 |

「Claude API」を選ぶとConsoleアカウントの残高から従量課金される。サブスクに戻したい場面で「Claude API」を選ぶと別財布にお金を払うことになるので選ばない。

> ⚠ 「Sign in with Claude Console」の「サインイン」は **claude.aiのサブスクログインではありません**。Console（console.anthropic.com）はAPI専用の管理サイトで、アカウント・課金ともサブスクとは完全に独立している。ConsoleサインインでDesktopを使うと、サブスクの月額枠は一切使われず、代わりにConsoleのクレジットからAPI従量課金で請求される。

---

## 実践: サブスク ⇔ Gateway 切替手順

### Gateway（GLM/MiniMax）へ切り替える

1. 設定ウィンドウ → 接続 → 送信先「**Gateway**」を選択
2. ゲートウェイ ベースURL: `http://localhost:8787`（プロキシの待ち受けアドレス）
3. 認証情報の種類: **静的APIキー** / ゲートウェイAPIキー: プロキシ側で決めた値 / ゲートウェイ認証スキーム: **bearer**
4. モデル設定は `inferenceModels` で上書き（名前 `claude-sonnet-5`・ラベル・1Mコンテキスト優先など）
5. 「**接続をテスト**」で疎通確認 →「**変更を適用**」
6. アプリが再起動し、左下のステータス表示が「`<ユーザー名> · Gateway`」に変われば成功

### サブスク（標準モード）へ戻す

1. 設定ウィンドウ右上の **「エクスポート」** で現在の設定JSONを保存（次にGatewayへ戻す時のバックアップ）
2. **Developer → Open Developer Config File** で設定ファイルを開く
3. **内容を空にするかファイルごと削除**して保存
4. アプリを **終了 → 再起動**
5. 左下ステータス表示から「Gateway」表記が消え、claude.aiサインインの標準モードになれば成功

> ⚠ 設定ファイルに `disableDeploymentModeChooser: true` や `bootstrapUrl` など、3Pモードを要求するキーが残っていると、**サブスクログインの選択肢自体が隠される**ことがある。戻す時は完全に空にする。

### 切替のタイミングと実行中セッション

- 「変更を適用」は **設定書き込み後すぐにアプリを再起動（relaunch）する**。実行中のCodeタブセッションは再起動で終わる
- 変更の反映は **次回起動から**（実行中セッションの途中で推論先が差し替わることはない）
- 設定ファイルを直接編集した場合、実行中アプリは約10分毎に変更を再チェックし、再起動要の変更は猶予期間の後にダイアログ表示 → アイドル時に自動再起動する（デフォルト挙動）

---

## 注意点と既知仕様

- **1P/3P切替のネイティブUIは未実装**: ドロップダウンに「サブスクへ戻す」選択肢はなく、設定削除が正規ルート（GitHub上で切替UIの要望issueが存在）
- **3Pモードにはフォールバックがない**: 設定した送信先が落ちていると推論が失敗する。プロキシ運用と併用する場合はプロキシの自動起動（systemd等）を先に固めておく（18章参照）
- **Windows環境ではWSL側プロキシへの転送が必要**: DesktopアプリはWindows側で動くため、`localhost:8787` をWSL側へ `netsh interface portproxy` で転送する構成が実用的（18章のアーキテクチャ節参照）
- **モデル名は `claude-sonnet-5` 等のClaude名を維持**: アプリがClaudeモデル名を前提にするため、`inferenceModels` で実際のバックエンドへのラベル上書き（「GLM（プロキシ経由）」等）を行うのが運用しやすい
- 公式ドキュメント: https://claude.com/docs/third-party/claude-desktop/ （overview / configuration / in-app-configuration / claude-api）

---

## 💡 やさしい補足（初心者向け）

- **設定は「回線の乗り換え手続き」のようなもの**: Gatewayへ乗り換えるのは選択肢から選ぶだけ。でも「元の回線（サブスク）に戻す」だけのボタンは用意されていないので、設定を丸ごと消す＝解約手続きが正規ルート
- **「Claude API」は別財布**: サブスク（月額制）とClaude API（従量課金）は財布が別。「API」の名前で選ぶと月額ではなく使った分だけ別に請求される
- **変更を適用するとアプリは一度閉じる**: 設定は次回起動から効く。書きかけの作業があるセッションは先に締めてから切替える
- **エクスポートしておけば戻しは簡単**: 切替前の設定をJSONで保存しておけば、次に戻す時はインポートで済む

---

## あわせて読む

- [18章 GLM Rate Proxy](18-glm-rate-proxy.html) — プロキシ本体の構築・運用・トラブルシューティング
- [08章 設定ファイル](08-config.html) — Desktopアプリの設定ファイル一覧とWSL/Windows環境差
- [20章 コスト最適化構成](20-cost-optimization.html) — 料金体系ごとの使い分けの考え方
