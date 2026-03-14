# NOWPATTERN SYSTEM MAP
> AIがシステム全体を3秒で把握するための地図。
> 詳細は各ファイルを参照。このファイルは概観のみ。
> 作成: 2026-03-14

---

## Core Mission

**世界最高の予測プラットフォームを作る。**

```
誰の予測が当たるかを可視化する。
それをBrier Scoreで数値化する。
3年積み上げれば翌日には再現不可能な信頼の堀（Moat）になる。
```

---

## Intelligence Loop（知性の循環）

```
Truth（事実の収集・分類）
  ↓
Prediction（検証可能な予測の生成）
  ↓
Verification（prediction_auto_verifier.py が自動検証）
  ↓
Track Record（Brier Score + 的中履歴の公開）
  ↓
Trust（読者信頼の蓄積 → 次の読者を呼ぶ）
  ↓
（ループ継続）
```

---

## Core Systems（コアシステム）

| システム | 役割 | 主要ファイル |
|----------|------|-------------|
| **Truth Engine** | 5-fact taxonomyで事実を分類・検証 | `engines/truth_engine.py` |
| **Prediction Engine** | 予測生成・追跡・Brier Score計算 | `engines/prediction_engine.py` |
| **Knowledge Engine** | 知識の蓄積・進化（EvolutionLoop） | `engines/knowledge_engine.py` |
| **Decision Engine** | ROI最大化のための意思決定 | `decision_engine/` |
| **Agent Civilization** | 複数エージェントによる分散知性 | `agents/` |

---

## Agents（エージェント構成）

| エージェント | 場所 | 役割 |
|-------------|------|------|
| **NEO-ONE** | VPS `/opt/claude-code-telegram/` | CTO・戦略・記事執筆 |
| **NEO-TWO** | VPS `/opt/claude-code-telegram-neo2/` | 補助・並列タスク |
| **NEO-GPT** | VPS `/opt/neo3-codex/` | バックアップ（OpenAI Codex CLI） |
| **local-claude** | Windows ローカル | ローカルファイル編集・git操作 |

**役割分担:**
- 分析 → NEO-ONE（Anthropic Claude）
- 予測生成 → NEO-ONE / NEO-TWO（Anthropic Claude）
- 検証 → prediction_auto_verifier.py（cron自動）
- 知識進化 → evolution_loop.py（毎週日曜）

---

## Content Pipeline（コンテンツパイプライン）

```
NEO-ONE/TWO が記事執筆
  ↓
article_validator.py（5層防御でタグ検証）
  ↓
nowpattern_publisher.py（Ghost CMS にPublish）
  ↓
prediction_db.json に予測を登録
  ↓
prediction_page_builder.py が /predictions/ を更新（毎日 07:00 JST）
  ↓
x-auto-post.py が X @nowpattern に配信
  ↓
note-auto-post.py / substack が他チャンネルに配信
```

**目標: 1日200本（JP100 + EN100）**

---

## Key Files（重要ファイル）

| ファイル | 用途 |
|----------|------|
| `.claude/rules/NORTH_STAR.md` | 全ルールの入口（最優先） |
| `docs/KNOWN_MISTAKES.md` | 既知のミス（実装前必読） |
| `/opt/shared/SHARED_STATE.md` | VPS最新状態（30分更新） |
| `/opt/shared/AGENT_WISDOM.md` | 全エージェント共有知識 |
| `data/prediction_db.json` | 予測DB（改ざん禁止） |
| `/opt/shared/reader_predictions.db` | 読者投票データ（SQLite） |

---

## Decision Engine（意思決定）

```
StrategyEngine      — 戦略的アクションの優先順位付け
CapitalEngine       — $200/月 Claude Max 予算をROI順で配分
ExecutionPlanner    — タスクを依存関係グラフで実行管理
BoardMeeting        — 毎日06:00 JST に3エンジンを統合・Telegram報告
```

---

## Guard Rails（ガードレール）

| ガード | 場所 | 対象 |
|--------|------|------|
| north-star-guard.py | PreToolUse | NORTH_STAR.md / OPERATING_PRINCIPLES.md への Write禁止 |
| fact-checker.py | Stop hook | 廃止用語・未確認情報の出力ブロック |
| article_validator.py | 投稿前 | タクソノミー外タグの物理ブロック |
| pvqe-p-gate.py | PreToolUse | 証拠なし実装のブロック |
| research-gate.sh | PreToolUse | 未調査での新規コード作成ブロック |

---

## Strategic Goal（戦略ゴール）

```
短期（Phase JA）:
  日本語圏でトラックレコードを積む
  Brier Score < 0.20（GOOD）を達成
  読者100人が毎月予測に参加する状態を作る

中期（Phase EN）:
  英語ページ /en/predictions/ で英語ユーザーを取り込む
  Ghost Members 有料化（$9〜19/月）

長期（Phase GLOBAL）:
  公開API → 世界中の Prediction Contestant が参加
  世界初の日本語×英語バイリンガル予測科学プラットフォーム
```

**Nowpatternを世界で最も信頼される未来予測インフラにする。**

---

*作成: 2026-03-14 | 更新: `.claude/SYSTEM_MAP.md`*
*詳細は `.claude/rules/NORTH_STAR.md` を参照。*
