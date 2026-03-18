# Working Memory — 今週の焦点

> **毎週月曜更新**。古い内容は `archive/YYYY-WXX.md` に移動する。
> ここに書かれていることが「今のNaotoの意識の前景」である。
> AIはこのファイルを参照して、今週の文脈を理解する。
>
> **[OS固有]** このファイルは Naoto Intelligence OS のコアメモリ。
> Nowpatternの作業ログではなく、「Naotoの知性が今どこを向いているか」を示す。

---

## 今週（2026-W12: 3/18〜3/24）

### 最重要の3タスク（今週これだけ完了すれば成功）

1. **[Nowpattern] K3: resolving→resolved バックフィル** — prediction_auto_verifier.py の修正が完了した（2026-03-18）。499件のresolving予測に対してバックフィルを実行し、正確なBrier Scoreを計算する。
2. **[OS] Intelligence OS 初回稼働確認** — WORKING_MEMORY・brainstorm sessions・DOMAINS が実際に使われているか確認する。「骨格はある、魂を入れる」週。
3. **[Nowpattern] 週次進捗確認** — prediction_db の解決件数をカウントし、Brier Scoreの変化を記録する。

### 今週の文脈

**Nowpattern（最重要プロジェクト）:**
- 直前に完了したこと: prediction_auto_verifier.py のJSONパースエラー修正（根本原因: `re.search(r'\{[^}]+\}')` が `}` 文字を含む日本語フィールドで途中で切れていた）
- 今週気になっていること: 499件のresolving予測のうち、実際に解決できるものが何件あるか？

**OS・世界理解（OSレイヤー）:**
- 今週気になっていること: **Nowpatternの作業に没入するほど「世界を見る目」が細くなっていないか？** 予測プラットフォームの主語は「Naoto=Intelligence OS」であるべきで、Nowpatternに引きずられる逆転が起きていないか。
- 重要判断: Intelligence OS として毎週何を「記録・判断・捨てる」のか、最低限の習慣ループを今週確立する。
- エネルギーレベル: [毎週記入]
- ブロッカー: [何かある場合]

---

## 今月（2026年3月）の焦点

### OSレベルのテーマ
```
テーマ: 「知性OSとして最初の1呼吸をする」

まず機能すること（美しい構造より先）:
  → WORKING_MEMORY が毎週更新される
  → brainstorm sessions/ に月1回のセッションが積み上がる
  → DOMAINS.md に洞察が追記される
```

### Nowpatternのテーマ
```
テーマ: 「予測精度の基盤を固める」

K3（resolving→resolved）完了後:
  → 実際のBrier Scoreが計算される
  → どの分野で外れているかが見える
  → 次の予測で改善できる
```

---

## 記憶すべき重要な文脈

### OS設計の決定（2026-03-18）

- **D-001決定済み**: vps-automation-openclaw をそのまま Intelligence OS ルートとして機能させる（Option A）。VPSパス変更ゼロ。
- **OSとプロジェクトの主語分離**: `.claude/CLAUDE.md` = OS、`projects/nowpattern/CLAUDE.md` = プロジェクト。毎セッションAIが「Naoto Intelligence OS のエージェント」として動く。

### Nowpatternの直近の学び（忘れないように）

- **競合ベンチマーク** （2026-03-18調査）:
  - Kalshi: Brier 0.05-0.06（業界最高精度、規制取引所）
  - Polymarket: Brier ~0.09（$21.5B/年のリアルマネー市場）
  - Metaculus: Brier 0.107（学術寄り、40,000人のForecaster）
  - AI分野は全プラットフォームで最も難しい: Metaculus AI予測 = 0.237（ほぼランダム）
  - **Nowpattern現在地**: 0.2205（n=8、まだ統計的に意味がある件数ではない）

- **Nowpattern の真の差別化**:
  - 言語: 日英バイリンガル（世界で唯一）
  - フォーカス: 地政学×経済×技術（AIドメインは後回し — 全社が苦手）
  - コンテンツ: 力学分析付き予測（単なる確率ではなく「なぜ」の説明）

### 現在の懸念事項

- prediction_db の499件のresolving予測 → 実際には「too_early」が多い可能性
- K2（スコアボード）は Brier Score が蓄積された後の方が意味がある
- **[OS懸念]** Intelligence OS の習慣化が「やりたいこと」から「やるべきこと」に変わる前に定着させる必要がある

---

## 先週の振り返り（2026-W11）

- ✅ prediction_auto_verifier.py JSON パースエラーを修正
- ✅ Naoto Intelligence OS の設計と初期化（D-001 決定、3点セット完了）
- 📋 K3バックフィルは今週に持ち越し
- 📋 Intelligence OS 初回稼働（WORKING_MEMORY更新・brainstorm session）は今週実施

---

*更新: 2026-03-18 — OS視点を追加。OSレイヤーとNowpatternレイヤーを分離して記述。*
