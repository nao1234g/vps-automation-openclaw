#!/usr/bin/env python3
"""Insert v4.0 format rules into NEO-TWO CLAUDE.md."""

NEW_SECTION = """## 0.6. 記事フォーマットルール v4.0（2026-02-21 オーナー確定 — 必須）

> **記事を書く前に必ず `/opt/shared/scripts/ARTICLE_FORMAT_SPEC.md` を読むこと。**
> これが記事フォーマットの唯一の真実源（Single Source of Truth）です。

### v4.0 必須フィールド（絶対に含めること）

記事JSONに以下のフィールドが**全て必須**。1つでも欠けると公開がブロックされます。

| フィールド | 説明 |
|---|---|
| bottom_line | 記事の核心を1文で要約 |
| bottom_line_pattern | 力学パターン名の要約 |
| bottom_line_scenario | 基本シナリオの一文要約 |
| bottom_line_watch | 次の注目イベント+日付 |
| between_the_lines | 報道が「言っていないこと」を1段落で分析 |
| open_loop_trigger | 次にこのストーリーが動くトリガー+日付 |
| open_loop_series | このパターンの続きとして追跡すべきテーマ |

### 記事構造（この順序で書くこと）

1. BOTTOM LINE（TL;DR）← v4.0 必須
2. タグバッジ
3. Why it matters
4. What happened
5. The Big Picture
6. Between the Lines ← v4.0 必須
7. NOW PATTERN
8. Pattern History
9. What's Next（3シナリオ+確率）
10. Open Loop ← v4.0 必須

### 文体ルール
- 太字強調: 力学分析内の最重要フレーズを **太字** に
- 会話調: Matt Levine スタイル
- シナリオラベル: 「楽観」「基本」「悲観」（ビルダーが自動でシナリオ付加）
- 最低6,000語（Deep Patternのみ。Speed Log廃止）

---

"""

path = "/opt/claude-code-telegram-neo2/CLAUDE.md"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

marker = "## 1. Architecture Rules"
pos = content.find(marker)
if pos >= 0:
    new_content = content[:pos] + NEW_SECTION + content[pos:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"OK: Inserted section 0.6 before section 1 in {path}")
else:
    print(f"ERROR: marker not found")
