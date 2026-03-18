# Working Memory — 今週の焦点

> **[OS固有]** このファイルは Naoto Intelligence OS のコアメモリ。
> Nowpatternの作業ログではなく、「Naotoの知性が今どこを向いているか」を示す。

---

## 📝 更新ルール（3行）

```
1. 毎週月曜に「▼ 毎週ここを更新する」セクションだけ書き換える（5分）
2. 古い「今週」は先週の振り返りに移してから消す
3. 「以下は参照のみ」は変えない。変えるときはOSレベルの判断が必要
```

---

## ▼ 毎週ここを更新する（5分で完結）

### 今週（2026-W12: 3/18〜3/24）

**最重要の3タスク**（今週これだけ完了すれば成功）

| # | レイヤー | タスク |
|---|---------|-------|
| 1 | [Nowpattern] | **K3: resolving→resolved バックフィル** — 499件のresolving予測に対してバックフィルを実行し、正確なBrier Scoreを計算する |
| 2 | **[OS]** | **Intelligence OS ループ確立** — WORKING_MEMORY・brainstorm・DOMAINS の最低限の習慣ループを今週定着させる |
| 3 | [Nowpattern] | **週次進捗確認** — prediction_db の解決件数をカウントし、Brier Scoreの変化を記録する |

**今週の文脈**

- Nowpattern: prediction_auto_verifier.py のJSONパースエラー修正完了（2026-03-18）。K3バックフィルが次の山。
- OS: 初回brainstorm実施済み（主語の維持は制度設計の問題、という洞察を得た）。今週このループが2回目を回るか？

**エネルギーレベル**: [毎週記入 — 高/中/低]
**今週のブロッカー**: [何かある場合に記入]

---

## ▼▼ 以下は参照のみ（週次更新不要）

> 以下は変えない。変えるときは重要な判断があったときだけ。

---

### 今月（2026年3月）の焦点

**OSテーマ**: 「知性OSとして最初の1呼吸をする」
```
まず機能すること（美しい構造より先）:
  → WORKING_MEMORY が毎週更新される
  → brainstorm sessions/ に月1回のセッションが積み上がる
  → DOMAINS.md に洞察が追記される
```

**Nowpatternテーマ**: 「予測精度の基盤を固める」
```
K3（resolving→resolved）完了後:
  → 実際のBrier Scoreが計算される
  → どの分野で外れているかが見える
  → 次の予測で改善できる
```

---

### 記憶すべき重要な文脈

**OS設計の決定（2026-03-18）**
- D-001: vps-automation-openclaw をそのまま Intelligence OS ルートとして機能させる（Option A）
- D-003: 最小OS稼働単位 = 週次WORKING_MEMORY更新 + 月次brainstorm session（継続性優先）
- **主語分離**: `.claude/CLAUDE.md` = OS、`projects/nowpattern/CLAUDE.md` = プロジェクト

**Nowpatternの競合ベンチマーク**
- Kalshi: Brier 0.05-0.06 / Polymarket: ~0.09 / Metaculus: 0.107
- AI分野は最難: Metaculus AI予測 = 0.237（ほぼランダム）
- **Nowpattern現在地**: 0.2205（n=8、統計的有意性には件数が少ない）

**Nowpatternの差別化**
- 言語: 日英バイリンガル（世界で唯一）
- フォーカス: 地政学×経済×技術（AIドメインは後回し）
- コンテンツ: 力学分析付き予測（単なる確率ではなく「なぜ」の説明）

---

### 先週の振り返り（2026-W11）

- ✅ prediction_auto_verifier.py JSON パースエラーを修正
- ✅ Naoto Intelligence OS の設計と初期化（D-001 決定、3点セット完了）
- ✅ OS 初回稼働: WORKING_MEMORY OS視点追加・brainstorm session実施・DOMAINS更新
- 📋 K3バックフィルは今週に持ち越し

---

*更新: 2026-03-18 — 週次更新ゾーンを明示。更新ルール3行追加。参照ゾーンを分離。*
