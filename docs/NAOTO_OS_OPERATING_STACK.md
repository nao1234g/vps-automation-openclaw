# NAOTO OS Operating Stack

最終更新: 2026-03-31

この文書は、Naoto が求めていることを AI 群が毎回同じ順序で読み、同じ前提で判断するための正本です。
個別の agent の性格や推論差よりも、先にこの stack を読むことを優先します。

## 目的

- 1体でも1000体でも、すべての agent が同じ目的で動く
- 書けることではなく、公開してよいことだけを通す
- 人間に迷惑をかける未確認情報や内部情報を public に出さない

## 読み込み順

1. `scripts/mission_contract.py`
   - オーナー、北極星、非交渉条件、Founder OS、PVQE を定義する
2. `scripts/agent_bootstrap_context.py`
   - 現在の公開状態、governance 監査、mistake registry を要約する
3. `scripts/canonical_public_lexicon.py`
   - public UI と公開説明文で使う語彙の正本
4. `.claude/rules/NORTH_STAR.md`
   - 目指す価値の正本
5. `.claude/rules/OPERATING_PRINCIPLES.md`
   - 判断の原則
6. `docs/TRUTH_PROTOCOL.md`
   - 事実確認と公開停止の原則
7. `data/mistake_registry.json` / `docs/KNOWN_MISTAKES.md`
   - 既知事故と再発防止の正本

## Founder OS

- Founder OS: `NAOTO OS`
- North Star: `Nowpattern is a verifiable forecast platform.`
- PVQE
  - `P = 判断精度`
  - `V = 価値密度`
  - `Q = 行動量`
  - `E = 波及力`

## 非交渉条件

- agent は `mission_contract` を読まずに public action してはならない
- agent は `bootstrap_context` を読まずに現状判断してはならない
- public UI は `canonical_public_lexicon` 以外の語彙を使ってはならない
- public release は `release_governor` を通らずに行ってはならない
- incident は `rule + test + monitor` に変換されなければ完了ではない

## 変更ルール

- Founder OS や北極星を変える時は `mission_contract.py` を先に変える
- 公開語彙を変える時は `canonical_public_lexicon.py` を先に変える
- 現状認識の数値は固定文言に埋め込まず、release snapshot にだけ置く
- 新しい agent / cron / publish path は追加前に `mission_contract_audit` と `publish_path_guard_audit` を通す

## 到達目標

- 全 active agent が `mission_contract_hash` を持つ
- 全 active agent が `bootstrap_context_hash` を持つ
- 全 public page が `canonical_public_lexicon` だけを使う
- 全 public action が `release_governor` だけを通る
