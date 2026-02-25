# Nowpattern プロジェクト全体像

> **ここだけ見れば全てが分かる。** バラバラなドキュメントのエントリーポイント。
> Pがずれてきたと思ったらこれを読む。AIエージェントへの読ませ用としても機能する。
> 最終更新: 2026-02-25 | 管理: ローカルClaude Code

---

## ビジョン

**既存の市場を追いかけるだけでなく、自ら「問い」を定義して市場をリードする。**

| 一般メディア | Nowpattern |
|---|---|
| 「〜の可能性も」と曖昧に書く | 「43%の確率で起きる」と断言する |
| 記事を書いたら終わり | トリガー日に自動検証する |
| 外れを隠す | 的中・外れを全て公開（改ざん不可） |
| 市場を追いかける | 自ら問いを定義して市場をリード |
| 人間がバイアスを持つ | 冷徹な自動判定ロジック |

---

## 現在の状態（2026-02-25）

### 唯一の本命プラットフォーム

- **nowpattern.com** — Ghost CMS、42記事（JA:24 / EN:18）
- **X: @nowpattern** — X Premium加入済み（最大25,000文字投稿可能）
- **note** — キュー稼働中（auto-post.py）
- **Substack** — コンテナ稼働中（substack-api）

### 廃止済み（絶対に言及しない）

- **@aisaintel** — X(Twitter)アカウント廃止済み。存在しない。
- **AISAパイプライン** — SUSPENDED。復活予定なし。
- **AISA ブランド** — Nowpatternに統合済み。

---

## コンテンツ戦略

### 生産量

- **1日200記事**（JP 100 + EN 100）— これは絶対に妥協しない数字
- JP記事を書いたら → Opus 4.6（Claude Max内）で自動翻訳してEN版を作る
- NEO-GPTは翻訳には使わない

### フォーマット: Deep Pattern（唯一）

```
無料ゾーン（Phase 1）:
  0. FAST READ    — 1分サマリー、逆説フック
  1. BOTTOM LINE  — 3秒で核心
  2. DELTA        — 前回からの変化
  3. タグバッジ    — ジャンル/イベント/力学
  4. Why it matters
  5. What happened

有料ゾーン（Phase 2以降、月$9.99予定）:
  6. The Big Picture   — 歴史的文脈
  7. Between the Lines — 報道が言わないこと
  8. NOW PATTERN       — 力学分析 × 2
  9. Pattern History   — 過去の並行事例
  10. What's Next      — 3シナリオ
  11. OPEN LOOP        — 次のトリガー
```

### 配信チャネル

| チャネル | 件数/日 | 備考 |
|---|---|---|
| Ghost (nowpattern.com) | 200本 | メインハブ |
| X (@nowpattern) | 100投稿 | 拡声器 |
| note | 3〜5本 | シャドバン対策、4時間間隔 |
| Substack | 1〜2本 | メール配信 |

---

## エージェント構成

| エージェント | Bot / 場所 | モデル | 役割 |
|---|---|---|---|
| **NEO-ONE** | @claude_brain_nn_bot / Telegram | Claude Opus 4.6 (Max) | CTO・戦略・記事執筆 |
| **NEO-TWO** | @neo_two_nn2026_bot / Telegram | Claude Opus 4.6 (Max) | 補助・並列タスク・翻訳 |
| **NEO-GPT** | Telegram / /opt/neo3-codex/ | OpenAI Codex CLI | NEO-ONE/TWOのバックアップ |
| **Jarvis** | @openclaw_nn2026_bot / Docker | Gemini 2.5 Pro (無料) | 実行・投稿・自動化 |
| **ローカルCC** | このVSCode | Claude Sonnet 4.6 (Max) | 設計・コード・CLAUDE.md管理 |

**重要な制約**: NEOをOpenClawに追加してはいけない（API従量課金になる）。
NEOはClaude Max定額（$200/月）で動く専用Telegramサービスとして独立運用する。

---

## 予測トラッカー

### 根本原則: DBマスターの法則

```
prediction_db.json = 唯一の真実（Single Source of Truth）
Ghost /predictions/ = DBから生成される「影」に過ぎない

→ Ghost HTMLを直接編集するな
→ DBを更新して prediction_page_builder.py --update で再生成せよ
```

### 3フェーズ

| フェーズ | 状態 | 内容 |
|---|---|---|
| **Phase 1** | ✅ 実装済み | 的中スコアボード・hit/miss バッジ・Brier Score |
| **Phase 2** | ✅ 実装済み | resolution_evidence・integrity_hash（SHA-256）・disputed status |
| **Phase 3** | スキーマ済み | 議論フォーラムUI・読者ランキング・ブロックチェーン公証（将来） |

### 重要な設計決定

- **「人間が判断しない」** — 的中・外れの判定は prediction_auto_verifier.py が完全自動。Naotoが判断する仕組みは作らない。

### 現在の予測状況

- 追跡中: 7件（全件 open）
- 平均Brierスコア: 未集計（解決済みなし）

---

## 設計原則: PVQE

| 文字 | 意味 | 実装 |
|---|---|---|
| **P** | 判断精度 | 実装前に3回検索。推測で語らない。このドキュメントがP崩壊防止用。 |
| **V** | 改善速度 | エラー→KNOWN_MISTAKES.mdに即記録。同じミスを繰り返さない。 |
| **Q** | 行動量 | 1日200記事。Hey Loop×4回 + news-analyst×3回。VPS cron 32本稼働。 |
| **E** | 波及力 | 1記事を4チャネルに展開。X Premium活用（25,000文字の深い投稿）。 |

### 3つの判断基準（全行動はこれを通過する）

1. **可逆性テスト** — 取り消せるか？ YES→即実行。NO→確認を取る。
2. **価値テスト** — オーナーの利益になるか？ YES→進める。NO→やめる。
3. **説明責任テスト** — やった後に報告できるか？ できない→やらない。

---

## 技術構成

| レイヤー | 技術 | 備考 |
|---|---|---|
| VPS | ConoHa / Ubuntu 22.04 | 163.44.124.123 |
| リバースプロキシ | Caddy | 自動SSL（Let's Encrypt） |
| CMS | Ghost 5.x | SQLite / ghost-nowpattern.service |
| 自動化 | Docker + N8N | docker-compose.quick.yml |
| DB | PostgreSQL 16 | openclaw_secure_2026 |
| LLM（定額） | Claude Max $200/月 | Opus 4.6 (NEO) + Sonnet 4.6 (ローカル) |
| LLM（無料） | Gemini 2.5 Pro | Jarvis用 |
| X | Grok API + X API | $5クレジット（Pay-Per-Use） |

**Ghost Lexical注意**: Ghost 5.xはLexical使用。`html`フィールドは読み取り専用。
更新はLexical JSON（`{"root":{"children":[{"type":"html",...}]}}`）で直接操作する。

---

## タグルール（5層防御で強制済み）

### Ghost タグ

全記事に必須: `nowpattern` / `deep-pattern` / `lang-ja` or `lang-en`

3層タクソノミー（taxonomy.json が唯一の定義）:
- **ジャンル** (13個): テクノロジー / 地政学・安全保障 / 経済・貿易 / 金融・市場 / ビジネス・産業 / 暗号資産 / エネルギー / 環境・気候 / ガバナンス・法 / 社会 / 文化・エンタメ・スポーツ / メディア・情報 / 健康・科学
- **イベント** (19個): 軍事衝突 / 制裁・経済戦争 / 貿易・関税 / 規制・法改正 / 選挙・政権交代 / 市場ショック / 技術進展 / 条約・同盟変動 / 資源・エネルギー危機 / 司法・裁判 / 災害・事故 / 健康危機・感染症 / サイバー攻撃 / 社会不安・抗議 / 構造シフト / 事業再編・取引 / 競争・シェア争い / スキャンダル・信頼危機 / 社会変動・世論
- **力学** (16個): プラットフォーム支配 / 規制の捕獲 / 物語の覇権 / 権力の過伸展 / 対立の螺旋 / 同盟の亀裂 / 経路依存 / 揺り戻し / 制度の劣化 / 協調の失敗 / モラルハザード / 伝染の連鎖 / 危機便乗 / 後発逆転 / 勝者総取り / 正統性の空白

リスト外のタグ → article_validator.py が exit(1) でブロック。

### X ハッシュタグ

```
必須: #Nowpattern + #ニュース分析（JP）or #NewsAnalysis（EN）
任意: 固有名詞 1〜2個（#Apple #DeepSeek 等）
合計: 3〜4個
禁止: 内部タクソノミータグ / 数字タグ / 5個以上
```

---

## 主要スクリプト（VPS: /opt/shared/scripts/）

| スクリプト | 用途 |
|---|---|
| `prediction_page_builder.py` | Ghost予測ページ生成（JA+EN）。`--update` で両ページ再生成 |
| `prediction_auto_verifier.py` | 予測自動判定。mark_disputed / add_rebuttal / compute_forecaster_rank |
| `pre_write_market_search.py` | 執筆前市場検索。重複チェック + Polymarket照合 + 推奨アクション |
| `nowpattern_publisher.py` | Ghost投稿 + タグ検証（STRICT mode）|
| `article_validator.py` | 記事品質チェック。FAIL=禁止パターン / WARN=推奨セクション欠落 |
| `add_knowledge.py` | AGENT_WISDOM.md への知識追記 |

---

## ロードマップ

- **2026 Q1** ✅ Phase 1完了: スコアボード・判定バッジ・EN/JA両ページ・予測DB v2.0
- **2026 Q2** Phase 2: 初の予測解決 → 証拠パネル・integrity_hash公開・disputed実運用
- **2026 Q3-Q4** Phase 3: 議論フォーラムUI・読者ランキング・ブロックチェーン公証
- **保留中**: NAVER Blog（SMS認証待ち）/ Medium（MEDIUM_TOKEN待ち）/ noteアカウント刷新

---

## ドキュメントマップ（バラバラなやつの場所）

| 知りたいこと | 読むファイル |
|---|---|
| エラーが出た・同じミスを避けたい | `docs/KNOWN_MISTAKES.md` |
| 記事フォーマットの詳細 | `docs/ARTICLE_FORMAT.md` |
| NEOへの指示書 | `docs/NEO_INSTRUCTIONS_V2.md` |
| タクソノミー完全版 | `docs/NOWPATTERN_TAXONOMY_v3.md` |
| 予測システム設計の根拠 | VPS: `/opt/shared/SYSTEM_DESIGN.md` |
| エージェントの共有知識 | VPS: `/opt/shared/AGENT_WISDOM.md` |
| 現在のVPS状態（リアルタイム） | VPS: `/opt/shared/SHARED_STATE.md` |
| パイプライン全体図 | `docs/PIPELINE_ARCHITECTURE.md` |
| 運用マニュアル（詳細） | `docs/NOWPATTERN_OPERATIONS_MANUAL.md` |

---

*このファイルが古くなったら → ローカルClaude Codeに「PROJECT_OVERVIEW.mdを更新して」と言えば直る。*
