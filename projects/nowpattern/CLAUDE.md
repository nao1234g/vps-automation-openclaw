# Nowpattern プロジェクト — CLAUDE.md

> **このファイルはNaoto Intelligence OS（上位CLAUDE.md）の下位レイヤー。**
> Nowpattern事業の実装コンテキストのみを定義する。
> OSレイヤーのミッション・原則・行動指針は上位 `.claude/CLAUDE.md` が持つ。

---

## このプロジェクトの位置づけ

**Nowpattern = Naoto Intelligence OSの最重要プロジェクト**

```
Naoto Intelligence OS（ルート）
  └─ projects/nowpattern/     ← ここ（このファイル）
       ├─ Ghost CMS（nowpattern.com）
       ├─ 記事生成パイプライン（scripts/）
       ├─ 予測システム（prediction_engine/）
       └─ X/note/Substack配信
```

---

## ミッション（プロジェクトレイヤー）

**世界初の日本語×英語バイリンガル・予測プラットフォーム**

- 誰の予測が当たるかをBrier Scoreで可視化
- 力学分析 + 検証可能な予測 + トラックレコード
- 3年分の予測履歴 = コピーできない堀（Moat）

---

## 現在のKPI

| メトリクス | 現在値 | 目標 |
|-----------|--------|------|
| 記事数（JA） | 640+ | 1日100本維持 |
| 記事数（EN） | 0（準備中） | 1日100本 |
| 予測数 | 168件（open:12） | 週10件追加 |
| Brier Score | 0.2171 | 0.20以下 |

---

## 主要パス（実装層 — 絶対にパス変更禁止）

| ファイル/ディレクトリ | 役割 |
|---------------------|------|
| `scripts/` | 全自動化スクリプト（VPS cronが参照） |
| `data/prediction_db.json` | 168件の予測DB（直接編集禁止） |
| `scripts/prediction_page_builder.py` | 予測ページ生成（毎日JST07:00） |
| `scripts/prediction_auto_verifier.py` | 自動検証（Brier Score計算） |
| `docs/BACKLOG.md` | タスクバックログ |
| `docs/KNOWN_MISTAKES.md` | 既知ミス集（実装前必読） |

---

## 記事パイプライン

- **1日200記事**（JP100 + EN100）
- JP書いたら Opus 4.6（Claude Max内）で自動翻訳してEN版
- 配信: Ghost → X → note → Substack

## Ghost / URL標準

```
JA版: nowpattern.com/[name]/
EN版: nowpattern.com/en/[name]/   ← Ghostスラッグ: en-[name]
```

---

## 現在のバックログ（抜粋）

優先タスク: K1〜K8（詳細は `docs/BACKLOG.md`）
- K2: Brier Scoreスコアボード表示
- K3: resolving→resolved自動バックフィル
- K5: Ghost Members有効化
- K6: Schema.org Claimタグ全記事注入

---

*最終更新: 2026-03-18 — 初版作成。Naoto Intelligence OSプロジェクトレイヤーとして設定。*
