# Decision Log — 意思決定の永続記録

> すべての重要意思決定を記録する。「なぜそうしたか」が3年後にわかるように。
> **記録原則**: YES/NOの結論だけでなく、「なぜNOにしたか」も必ず記録する。
> **追記のみ** — 過去の決定は変更禁止。

---

## テンプレート

```markdown
### D-XXX: [決定事項の一行タイトル]
- **日付**: YYYY-MM-DD
- **状態**: 検討中 / 決定済み / 保留
- **質問**: 何を決めるか？（1文）
- **オプション検討**:
  - Option A: ...（メリット / デメリット）
  - Option B: ...（メリット / デメリット）
- **決定**: Option [X] を選択
- **理由**: なぜそれを選んだか（事実ベースで）
- **なぜ他を選ばなかったか**: （重要 — 未来の自分への説明）
- **期待成果**: 3ヶ月後に何が変わるか
- **検証方法**: どうなれば正解だったとわかるか
```

---

## 🔴 未解決（承認待ち・検討中）

### D-002: DeepSeek R1移行（ROI提案 7aa06939）
- **日付**: 2026-03-08（提案）
- **状態**: 承認待ち（`data/pending_approvals.json`）
- **質問**: NEO-ONE/TWOをclaude-opus-4-6からDeepSeek R1 Distill Qwen 32Bに切り替えるか？
- **提案内容**: 現在$200/月 → $0.29/1Mトークン
- **懸念点**: NEO品質崩壊リスク（既知ミス: フルエージェント→ステートレスAPI置換禁止）
- **決定待ち**: Naoto承認必要

---

## ✅ 解決済み

### D-001: naoto-os統合アーキテクチャ
- **日付**: 2026-03-18
- **状態**: 決定済み
- **質問**: 既存の `vps-automation-openclaw` をNaoto Intelligence OSのルートとして機能させるか？
- **オプション検討**:
  - Option A: 既存リポジトリ（`vps-automation-openclaw`）にOS骨格ディレクトリを追加し、`.claude/CLAUDE.md`の主語をIntelligence OSに変更する ← **選択**
  - Option B: naoto-os を独立リポジトリにして Nowpattern を submodule/symlink（設計が綺麗だが移行コストが高い）
  - Option C: 今のまま（naoto-os は Desktop 上の別ディレクトリとして並走）
- **決定**: Option A を選択
- **理由**: 「美しい構造」ではなく「今のrepoのまま上位OSとして機能し始めること」がゴール。VPSのcron/systemdが参照する`scripts/`等のパスを一切変更せずに、OSアイデンティティと知性蓄積層を追加できる。即日機能し始められる。
- **なぜ他を選ばなかったか**:
  - Option B: VPS本番パス変更が必須になる。`scripts/`を移動するとcronが全滅する。移行コストがOption Aの20倍以上。
  - Option C: naoto-osの知性蓄積がvps-automation-openclawの作業コンテキストと完全に分離し、AIが毎セッション両方を見ることができない。
- **期待成果**: 毎セッション開始時にAIが「自分はNaoto Intelligence OSのAIエージェントだ」というコンテキストで動く。Nowpatternの作業が知性OSの「最重要プロジェクト」として位置づけられる。
- **検証方法**: `memory/WORKING_MEMORY.md`が毎週更新され、`brainstorm/sessions/`に壁打ちセッションが積み上がり始めたら成功。
- **変更ファイル**:
  - `.claude/CLAUDE.md` — タイトル + OSアイデンティティ宣言テーブル追加
  - `projects/nowpattern/CLAUDE.md` — 新規作成
  - `intelligence/DOMAINS.md` — naoto-osから移植
  - `memory/WORKING_MEMORY.md`, `LONG_TERM.md`, `MENTAL_MODELS.md` — naoto-osから移植
  - `brainstorm/SESSION_TEMPLATE.md`, `SESSION_INDEX.md` — naoto-osから移植
  - `decisions/DECISION_LOG.md` — このファイル（naoto-osから移植 + D-001解決更新）

### D-000: 予測プラットフォームの言語戦略
- **日付**: 2026-03-06
- **決定**: 日英バイリンガル（JA: `/predictions/` + EN: `/en/predictions/`）
- **理由**: 世界中の予測プラットフォーム（Metaculus/Manifold/Polymarket/GJ Open/PredictIt）が全て英語のみ（2026-03確認）。日本語×英語バイリンガルは空白市場。
- **なぜ日本語のみを選ばなかったか**: 英語市場を取り込まないとグローバルなSuperforecasterコミュニティが形成できない。
- **検証**: `/en/predictions/` が200応答 → ✅ 確認済み

---

*最終更新: 2026-03-18 — naoto-osから移植 + D-001をOption A決定済みに更新*
