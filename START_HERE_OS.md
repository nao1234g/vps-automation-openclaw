# START HERE — Naoto Intelligence OS 起動手順

> 5分で今週の焦点を掴む。迷ったらここに戻る。

---

## セッション開始（1分チェック）

この順番で開く:

```
1. memory/WORKING_MEMORY.md          ← 今週の3タスクと文脈を確認
2. projects/nowpattern/CLAUDE.md     ← Nowpatternの現在地（週次で変わる部分だけ見る）
3. brainstorm/SESSION_INDEX.md       ← 今月のbrainstormは終わったか？
```

**確認事項（30秒）**:
- 今週の3タスクのうち、OSレイヤーのタスクは1つあるか？
- 今月のbrainstormは予約されているか？

---

## 今日どう動くか（5分で決める）

```
Nowpatternのタスクがある  → projects/nowpattern/CLAUDE.md を読んで着手
OS視点で考えたい          → memory/WORKING_MEMORY.md の「OS・世界理解」を書く
月次brainstormをやりたい  → brainstorm/OPERATING_RULES.md を見て30分取る
過去の判断を確認したい    → decisions/DECISION_LOG.md を参照
洞察を探したい            → intelligence/DOMAINS.md を参照
```

---

## 省略してよいもの（毎回は見なくていい）

| ファイル | 見るタイミング |
|---------|--------------|
| `.claude/rules/NORTH_STAR.md` | 方向に迷ったとき（月1回） |
| `intelligence/MENTAL_MODELS.md` | 新しい思考枠組みが必要なとき |
| `decisions/DECISION_LOG.md` | 過去の判断を参照したいとき |
| `intelligence/LONG_TERM.md` | 中長期の目標を確認したいとき |

---

## OS構造マップ（全体を把握する）

```
vps-automation-openclaw/
├── START_HERE_OS.md           ← いまここ
├── memory/
│   └── WORKING_MEMORY.md      ← 毎週更新（今週の焦点）
├── brainstorm/
│   ├── OPERATING_RULES.md     ← 月次セッションの制度ルール
│   ├── SESSION_INDEX.md       ← 全セッション一覧
│   └── sessions/              ← 実際のセッション記録
├── intelligence/
│   ├── DOMAINS.md             ← クロスドメイン洞察の蓄積
│   ├── MENTAL_MODELS.md       ← 使える思考枠組み
│   └── LONG_TERM.md           ← 中長期の方向性
├── decisions/
│   └── DECISION_LOG.md        ← 重要意思決定の永続記録
├── projects/
│   └── nowpattern/
│       └── CLAUDE.md          ← Nowpatternプロジェクト指示書
└── .claude/
    └── CLAUDE.md              ← OS全体の指示書（AIが読む）
```

---

## 最小OS稼働ループ（これだけ続けば機能している）

```
毎週月曜（5分）: memory/WORKING_MEMORY.md の「▼ 毎週ここを更新する」を書き換える
毎月第1週（30〜60分）: brainstorm session を1件実施 → SESSION_INDEX.md に追記
```

**これ以上のことは、できればやる。できなければやらない。**
**この2つだけが必須ループ。**

---

## Nowpatternが詰まったとき

```
VPSの現状確認:
  ssh root@163.44.124.123 "cat /opt/shared/SHARED_STATE.md"

既知のミスを確認:
  docs/KNOWN_MISTAKES.md

バックログを確認:
  docs/BACKLOG.md
```

---

*作成: 2026-03-18 — D-003（最小OS稼働単位確立）の一部として作成*
