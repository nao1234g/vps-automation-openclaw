# Claude Code Sidecar — Task Result
> Generated: 2026-04-04 | Agent: claude-opus-4-6 | Mission Contract: v3 | Lexicon: v4

---

## A. distribution_blocked 262 棚卸し

### 全体像

| 指標 | 値 |
|------|-----|
| published_total | 474 |
| distribution_allowed | 212 (44.73%) |
| distribution_blocked | 262 (55.27%) |
| truth_blocked | 0 |
| policy minimum | 30.0% ← 現在クリア |

**262件全てが `release_lane = review_required`。truth 違反はゼロ。**

### ブロック理由の内訳

| risk_flags 組み合わせ | 件数 | 割合 |
|----------------------|------|------|
| WAR_CONFLICT + FINANCIAL_CRISIS | 196 | 75% |
| WAR_CONFLICT のみ | 59 | 23% |
| FINANCIAL_CRISIS のみ | 4 | 1.5% |
| フラグなし（3件） | 3 | 1% |

### ブロックの仕組み（コード参照）

```
article_release_guard.py
  L43-65:  HIGH_RISK_RULES — regex でタイトル/本文/HTMLを走査
  L68-94:  classify_release_lane() — risk_flags × verified_count で lane 判定
  L86-89:  ★ 2+flags → review_required（verified_count >= 2 なら editorial_review_advised）
  L90-91:  ★ 1 flag + verified_count < 1 → review_required
  L92-93:  1 flag (AUTO_SAFE) + verified_count >= 1 → auto_safe
  L224-226: release_errors に "EDITOR_REVIEW_REQUIRED:{flags}" を注入
```

**根本原因**: WAR_CONFLICT regex が `military|conflict|sanction|attack` など単語レベルで発火。地政学記事の 96%（456/474）がヒット。さらに 196件は FINANCIAL_CRISIS とダブルフラグになり、dual-flag の `verified_count >= 2` 要件を満たせずブロック。

### 改善候補 Top 3

#### IC-1: dual-flag AUTO_SAFE threshold 緩和（最優先）

| 項目 | 内容 |
|------|------|
| 対象件数 | 196件（WAR_CONFLICT + FINANCIAL_CRISIS） |
| 止めている rule | `classify_release_lane` L87: `verified_count >= 2` |
| rule 細分化案 | `verified_count >= 1` に緩和し、戻り値を `editorial_review_advised` に変更（distribution_allowed=true + warning 付き） |
| リスク | **低** — editorial_review_advised は warning を残すため安全網は維持。distribution_allowed=true になるだけ |
| Codex 触るべきファイル | `scripts/article_release_guard.py` L87 |
| 推定効果 | distribution_allowed_ratio: 44.73% → **~65%** |

#### IC-2: WAR_CONFLICT regex コンテキスト化

| 項目 | 内容 |
|------|------|
| 対象件数 | 456件（WAR_CONFLICT フラグ付き全体） |
| 止めている rule | `HIGH_RISK_RULES` L45-52: 単語レベル regex |
| rule 細分化案 | 単語マッチ → 複合句マッチ。例: `military` → `military\s+(?:operation\|action\|force\|offensive\|campaign)`、`conflict` → `(?:armed\|military)\s+conflict` |
| リスク | **中** — false negative が生まれる可能性。段階的に緩和し manifest 再生成で検証 |
| Codex 触るべきファイル | `scripts/article_release_guard.py` L45-52 |
| 推定効果 | WAR_CONFLICT フラグ数: 456 → ~200-300（推定） |

#### IC-3: single-flag external_url_count fallback

| 項目 | 内容 |
|------|------|
| 対象件数 | 59件（WAR_CONFLICT のみ、verified_count < 1） |
| 止めている rule | `classify_release_lane` L90-91: `verified_count < 1` |
| rule 細分化案 | `verified_count < 1` かつ `external_url_count >= 2` なら `editorial_review_advised` に格下げ |
| リスク | **低** — external_url_count は既に計算済み（L195-196）。URL 存在自体が信頼性指標 |
| Codex 触るべきファイル | `scripts/article_release_guard.py` L90-91 |
| 推定効果 | distribution_allowed_ratio: +5-8pp |

### 累積効果予測

```
現状:                44.73%
IC-1 適用後:         ~65%
IC-1 + IC-3 適用後:  ~72%
全3件適用後:         ~80%
```

---

## B. NAOTO OS ↔ Nowpattern 語彙ドリフト監査

### mojibake 監査

**結果: ゼロ件検出。**

- 検査対象: 全 .md / .py ファイル
- 検査手法: `lexicon_contract_audit.py` の mojibake markers（縺, 繧, 蛻､, 讀懆, 莠域ｸｬ）+ grep
- UTF-8 エンコーディング: 全ファイル健全

### 語彙ドリフト検出（3件）

#### VD-1: NAOTO OS vs Nowpattern アイデンティティ混同（info）

- **事象**: 一部 docs 内で「Nowpattern」を OS 名として使用
- **正**: NAOTO OS = OS 名、Nowpattern = プロジェクト名/プラットフォーム名
- **ガード**: `PROJECT_DRIFT_GUARD` in mistake_patterns.json で検知可能
- **対応**: ドキュメント修正のみ。影響低。

#### VD-2: Brier Score 3値並存（info）

- **事象**: 0.1780（VPS live, n=7）、0.1828（stale stats）、0.4759（official binary, n=53）が混在
- **正**: 公式値は binary methodology（n=53, avg=0.4759）。0.1780 は部分集合
- **ガード**: M006 in mistake_registry.json
- **対応**: `.agent-mailbox/vps-findings.md` で既にフラグ済み。Codex 整理待ち。

#### VD-3: PVQE の V 定義不一致（info）

- **事象**: `mission_contract.py` (v3) では V = "価値密度"、`.claude/rules/NORTH_STAR.md` では V = "改善速度"
- **正**: mission_contract.py が権威ソース → V = "価値密度"
- **影響ファイル**: NORTH_STAR.md, OPERATING_PRINCIPLES.md
- **対応**: docs 側を修正（Codex handoff IC-VD3）

### Lexicon シム健全性

| ファイル | 状態 |
|----------|------|
| canonical_public_lexicon.py (v4) | **正** — 唯一の権威ソース |
| public_lexicon.py | shim → canonical に転送。健全 |
| product_lexicon.py | shim → canonical に転送。健全 |
| test_public_lexicon.py | v4 回帰テスト。健全 |
| lexicon_contract_audit.py | mission_contract ↔ lexicon 整合チェック。健全 |

---

## C. Codex Handoff

### Codex が実行すべきアクション（優先順）

| ID | ファイル | 行 | アクション | 優先度 | リスク |
|----|----------|-----|----------|--------|--------|
| IC-1 | article_release_guard.py | 87 | dual-flag verified_count >= 2 → >= 1 に緩和、戻り値を editorial_review_advised に | **高** | 低 |
| IC-3 | article_release_guard.py | 90-91 | external_url_count >= 2 fallback 追加 | 中 | 低 |
| IC-2 | article_release_guard.py | 45-52 | WAR_CONFLICT regex を複合句マッチに変更 | 中 | 中 |
| VD-3 | NORTH_STAR.md + OPERATING_PRINCIPLES.md | PVQE 表 | V = "改善速度" → "価値密度" に修正 | 低 | 低 |

### 検証手順

```bash
# IC-1/IC-2/IC-3 適用後に必ず実行:
python3 /opt/shared/scripts/build_article_release_manifest.py
python3 /opt/shared/scripts/article_release_guard.py --report
# distribution_allowed_ratio_pct が 65%+ になることを確認
# truth_blocked が 0 のままであることを確認

# VD-3 適用後:
python3 /opt/shared/scripts/lexicon_contract_audit.py
```

### 触ってはいけないもの

- `data/prediction_db.json`
- `scripts/one_pass_completion_gate.py`（production runner）
- `build_article_release_manifest.py`（production 実行のみ。コードレビューは OK）
- deploy 系スクリプト全般

---

## 完了条件チェック

| 条件 | 状態 |
|------|------|
| distribution_blocked 棚卸し完了 | ✅ |
| Top 3 候補（対象件数/rule/細分化案/リスク/Codex ファイル） | ✅ |
| 語彙ドリフト監査完了 | ✅ |
| mojibake 監査完了（ゼロ件） | ✅ |
| Codex handoff 作成完了 | ✅ |
| 禁止ファイル未編集 | ✅ |

---

*End of sidecar task result. Machine-readable version: `task_result.json`*
