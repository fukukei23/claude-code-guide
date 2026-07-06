# 決定ログ — 設計判断の図解記録

> 設計判断を「どういう考えで決めたか」図と表入りで残す場所。スマホでサクッと見返す用。

---

## 🧩 sentaku に「L1.5 Diverge（案拡張）」を追加した話

### 🎯 TL;DR（3行）
- 比較スキル `sentaku` に **L1.5 Diverge**（案拡張・軽量・毎回自動）を追加
- 比較の直後に「他の軸はないか？」と自問し、**新案を1-2個提示**
- 「もっと広げて」で6技法（逆転/類推/統合/極端化/制約解除/次元追加）フルへ昇格

### 🗺️ 全体像（図）

```
[旧] L1比較 → (L2まで行かないと案が増えない)
              ↓ L1で終わると案が少ないまま ⚠

[新] L1比較 → L1.5 Diverge（自動・毎回）→ L2マトリクス
              ↑                          ↑
              「他の軸はないか？」1回自問    広がった案で定量比較
              → 新案1-2個提示              （質が高い）
                    ↓
              「もっと広げて」→ 6技法フル
```

### 🌧️ きっかけ

ある決定で比較スキルを使った後、「**他に案はない？**」と聞いたことで、**3段階細分化**という新視点の案が出た。この「他に案はない？」の威力を実感し、定型化したいという発想に。

### 🤔 検討した選択肢（表）

| 案 | 概要 | 評価点 |
|---|---|---|
| **1: L2.5拡張** | L2マトリクス後にDiverge | 49 |
| 2: 新スキル | Diverge専用スキル新設 | 31 |
| 3: トリガー拡張 | 「他に案はない？」で自動 | 46 |
| 4: 既存スキル活用 | brainstormingへ委譲 | 40 |
| 5: プロンプト集 | 6技法を文書化 | 41 |

**決め手**: 「L2マトリクスまで行かないことが多い。案を増やすなら最初のうちに」→ **L2.5でなくL1.5（L2の前）** に配置。

### ✅ 決定と理由

**L1.5 Diverge（軽量版）採用**。理由:
1. **L2前配置**で、L1で終わるケースもカバー
2. **軽量版（毎回1-2新案）**で手軽さを保持・6技法フルは「もっと広げて」で昇格
3. **sentaku内に統合**で新スキル増やさない
4. **6技法体系化**で水平思考を明示

却下: L2.5（L2後で遅い） / 新スキル（呼び分け負担） / フル6技法毎回（重い）

### 📋 次のアクション

- 実運用でのL1.5効果検証（次回sentaku使用時・新案が出るか）
- L1.5軽量版で新案が出ない場合→フル6技法をデフォルトにするか検討

---

## 💡 このページの使い方

- **目的**: 設計判断を図解入りで残し、スマホで見返す
- **更新**: 記録は更新されるが、このページは「その時決めた内容のスナップショット」。陳腐化しても気にしない
- **追加**: 新しい決定があれば章を追加していく

---

## 🎨 図解の3種類比較（PoC）

同じ「sentaku L1.5 の流れ」を3種類の絵で描き比べ。

### 1. ASCII図（文字の絵・無料・現状）

```
[L1:比較] → [L1.5:Diverge] → [L2:マトリクス]
                ↓
         新案1-2個
                ↓
         「もっと広げて」→ 6技法フル
```

### 2. SVG（本物の図・無料）

<div class="flow-svg-wrap" style="background:var(--bg-secondary, #e8edf5);padding:1rem;border-radius:12px;margin:1rem 0">
<svg viewBox="0 0 600 240" width="100%" style="max-width:600px;margin:0 auto;display:block;font-family:system-ui,sans-serif">
  <defs>
    <marker id="arrL15" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="var(--accent, #6366f1)"/>
    </marker>
  </defs>
  <rect x="10" y="20" width="130" height="50" rx="10" fill="var(--accent-bg, #eef2ff)" stroke="var(--accent, #6366f1)" stroke-width="2"/>
  <text x="75" y="50" text-anchor="middle" fill="var(--text, #1e293b)" font-size="14" font-weight="700">L1: 比較</text>
  <rect x="235" y="20" width="170" height="50" rx="10" fill="var(--accent-bg, #eef2ff)" stroke="var(--accent, #6366f1)" stroke-width="2"/>
  <text x="320" y="43" text-anchor="middle" fill="var(--text, #1e293b)" font-size="14" font-weight="700">L1.5: Diverge</text>
  <text x="320" y="60" text-anchor="middle" fill="var(--text-secondary, #64748b)" font-size="11">「他に軸はないか？」</text>
  <rect x="500" y="20" width="90" height="50" rx="10" fill="var(--accent-bg, #eef2ff)" stroke="var(--accent, #6366f1)" stroke-width="2"/>
  <text x="545" y="50" text-anchor="middle" fill="var(--text, #1e293b)" font-size="14" font-weight="700">L2</text>
  <line x1="140" y1="45" x2="230" y2="45" stroke="var(--accent, #6366f1)" stroke-width="2" marker-end="url(#arrL15)"/>
  <line x1="405" y1="45" x2="495" y2="45" stroke="var(--accent, #6366f1)" stroke-width="2" marker-end="url(#arrL15)"/>
  <line x1="320" y1="70" x2="320" y2="120" stroke="var(--accent, #6366f1)" stroke-width="2" marker-end="url(#arrL15)"/>
  <rect x="245" y="125" width="150" height="40" rx="8" fill="var(--bg-card, #ffffff)" stroke="var(--border, #cbd5e1)" stroke-width="1.5"/>
  <text x="320" y="150" text-anchor="middle" fill="var(--text, #1e293b)" font-size="13">💡 新案 1-2個</text>
  <line x1="320" y1="165" x2="320" y2="195" stroke="var(--text-secondary, #64748b)" stroke-width="1.5" stroke-dasharray="4,3" marker-end="url(#arrL15)"/>
  <rect x="220" y="200" width="200" height="32" rx="8" fill="var(--bg-card, #ffffff)" stroke="var(--accent, #6366f1)" stroke-width="1.5" stroke-dasharray="5,3"/>
  <text x="320" y="221" text-anchor="middle" fill="var(--accent-dark, #4f46e5)" font-size="12">「もっと広げて」→ 6技法フル</text>
</svg>
</div>

### 3. 画像イラスト（写真みたいな絵・有料・minimax MCP）

> ※画像生成API利用（1枚あたり課金）。必要なら生成します。
