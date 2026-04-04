# AGENTS.md — 全エージェント共通エントリーポイント

> このファイルはClaude, Codex, GPT, 将来のあらゆるAIエージェントが最初に読むファイル。
> エージェントの種類に関係なく、このリポジトリで作業する前に必ず読むこと。

---

## このリポジトリの正体

**`vps-automation-openclaw` = NAOTO OS（Naoto Intelligence OS）のルートリポジトリ。**

NAOTO OS = 創設者Naotoの意図を実行するOS。
Nowpattern = NAOTO OS配下の最重要プロジェクト（予測オラクルプラットフォーム）。

---

## 読む順番（Read Order）

| 順番 | ファイル | 内容 |
|------|---------|------|
| 1 | `.claude/rules/NORTH_STAR.md` | 意図・哲学・ミッション・永遠の三原則 |
| 2 | `scripts/mission_contract.py` | ミッション契約（全エージェント必読） |
| 3 | `scripts/agent_bootstrap_context.py` | 現在の状態を把握するブートストラップ |
| 4 | `reports/content_release_snapshot.json` | コンテンツリリースの最新スナップショット |
| 5 | `docs/KNOWN_MISTAKES.md` | 既知のミス（同じミスを繰り返さない） |
| 6 | `docs/AGENT_WISDOM.md` | 蓄積された知恵 |

---

## 非交渉条件（全エージェント共通）

- `mission_contract.py` を読まずに public action してはならない
- `bootstrap_context` を読まずに現状判断してはならない
- public UI は `canonical_public_lexicon` 以外の語彙を使ってはならない
- public release は `release_governor` を通らずに行ってはならない
- incident は `rule + test + monitor` に変換されなければ完了ではない

---

## JIT参照（必要時に読む）

| いつ読むか | ファイル |
|-----------|---------|
| NORTH_STARの詳細版（実践ガイド・テンプレート） | `.claude/reference/NORTH_STAR_DETAIL.md` |
| 行動規範・コンテンツ・タグ・X投稿 | `.claude/reference/OPERATING_PRINCIPLES.md` |
| フック・NEO・Docker・VPS・予測ページUI | `.claude/reference/IMPLEMENTATION_REF.md` |
| エントリーポイント（Claude専用設定） | `.claude/CLAUDE.md` |
| 類似予測検索（AI Notion実装） | `scripts/prediction_similarity_search.py` |

---

## エージェント別の追加設定

| エージェント | 追加設定ファイル |
|-------------|----------------|
| Claude Code（ローカル） | `.claude/CLAUDE.md` + `.claude/settings.json` |
| NEO-ONE（VPS） | `/opt/claude-code-telegram/CLAUDE.md` |
| NEO-TWO（VPS） | `/opt/neo2/CLAUDE.md` |
| NEO-GPT / Codex（VPS） | `/opt/neo3-codex/CLAUDE.md` |

---

*最終更新: 2026-04-04 — 全エージェント共通エントリーポイントとして作成*
