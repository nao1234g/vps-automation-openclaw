# NOWPATTERN CLICKPATH AUDIT — 2026-03-28
> 監査担当: Senior Engineer / UI-UX Audit Lead
> 対象: nowpattern.com の主要コンバージョンパス
> 実施: 2026-03-28 ライブサイトチェック + 既知の実装状況からの分析
> 原則: 監査のみ。実装変更なし。

---

## クリックパス監査の目的

「ユーザーが目標を達成するまでの経路（パス）が機能しているか」を確認する。
Nowpatternで重要な3つのコンバージョンパスを評価する。

---

## CP-01: 予測に参加するパス（最重要）

### 期待されるパス

```
ホーム（/）
  → /predictions/ または /en/predictions/（予測一覧）
    → 個別予測カード（確認）
      → 投票ウィジェット（投票）
        → 確認メッセージ（完了）
```

### ライブチェック結果

| ステップ | 状態 | 証拠 |
|----------|------|------|
| ホームから /predictions/ へのリンク | ✅ あり | Ghost ナビゲーション |
| /predictions/ の HTTP 200 | ✅ 正常 | curl 確認済み |
| 予測カードの存在 | ✅ あり | HTML 解析済み |
| `<button>` 要素 | ✅ 16件 | audit_check.py 確認 |
| `<form>` 要素 | ✅ 1件 | audit_check.py 確認 |
| vote/predict 要素 | ✅ True | audit_check.py 確認 |
| 投票 API (port 8766) | ⚠️ 未確認 | curl /reader-predict/health 未実施 |

### 🔴 ブロッカー: np-scoreboard ID 欠落

```
問題: id="np-scoreboard" が存在しない
影響: /predictions/#np-scoreboard というアンカーリンクが機能しない
ユーザー影響: Xポスト等で「スコアボードを見る」リンクを共有しても
             ページトップにジャンプするだけでスコアボードが見えない
```

### ⚠️ 未確認: 読者投票 API の疎通

```
確認すべきコマンド（VPS実行）:
curl -s https://nowpattern.com/reader-predict/health
期待値: {"status": "ok"} または類似のレスポンス
現状: 未確認（ポート8766が稼働中かどうか）
```

---

## CP-02: 有料プランに登録するパス（現在 BROKEN）

### 期待されるパス

```
記事閲覧
  → 有料コンテンツ遭遇（ペイウォール）
    → Ghost Portal 開く
      → 月額/年額プラン選択
        → Stripe 決済
          → 会員登録完了
```

### ライブチェック結果

| ステップ | 状態 | 根本原因 |
|----------|------|---------|
| 記事閲覧 | ✅ | 全文無料（Phase 1） |
| ペイウォール | ❌ 存在しない | Phase 1 = 全文無料（意図通り） |
| Ghost Portal | ✅ 開く | Ghost Members 稼働中 |
| 月額/年額プラン | 🔴 **非表示** | `portal_plans: ["free"]` |
| Stripe 決済 | 🔴 **到達不可** | プランが表示されないため |

### 根本原因の詳細

```
Ghost Admin Settings → Portal
  portal_plans: ["free"]  ← ここが問題

正しい設定:
  portal_plans: ["free", "monthly", "yearly"]

修正方法（SQLite直接更新）:
  ssh root@163.44.124.123 \
    "sqlite3 /var/www/nowpattern/content/data/ghost.db \
     \"UPDATE settings SET value='{\"plans\":[\"free\",\"monthly\",\"yearly\"]}' \
       WHERE key='portal_plans';\""

  注意: Ghost再起動が必要
  注意: Stripe 接続が別途必要（Stripe API キー未設定の可能性）

影響: 有料転換ゼロ。有料会員 = 0人（推定）
```

---

## CP-03: 英語ユーザーのパス（言語切り替え）

### 期待されるパス（EN → JA）

```
/en/predictions/
  → 「日本語」切り替えリンク
    → /predictions/（JA版）
```

### ライブチェック結果

```python
# audit_check.py の出力より
# /en/predictions/ の EN predictions link 検索:
en_link: ['href="https://nowpattern.com/en/predictions/"', 'href="/en/predictions/"']
```

**発見**: `/en/predictions/` ページ内の「言語切り替え」っぽいリンクが、
`/en/predictions/` 自身を指している（自己参照）の可能性がある。

| 方向 | リンク | 状態 |
|------|--------|------|
| JA → EN（/predictions/ から） | `href="https://nowpattern.com/en/predictions/"` | ✅ 正確 |
| EN → JA（/en/predictions/ から） | `href="/en/predictions/"` の自己参照疑い | ⚠️ 要確認 |

### 確認が必要

```bash
# /en/predictions/ ページの言語切り替えリンクを詳細確認
ssh root@163.44.124.123 \
  "curl -s https://nowpattern.com/en/predictions/ | \
   python3 -c \"
import sys, re
html = sys.stdin.read()
# 全リンクでpredictionsを含むもの
links = re.findall(r'href=[\x27\"](.*?)[\x27\"]', html)
pred_links = [l for l in links if 'predictions' in l]
for l in pred_links: print(l)
\""
```

---

## CP-04: Xシェアから記事へのパス

### 期待されるパス

```
X (@nowpattern) のポスト
  → nowpattern.com/{article-slug}/ へのリンク
    → 記事閲覧
      → /predictions/ への誘導（LIKING CTA）
        → 読者参加
```

### 評価

| ステップ | 状態 | 根拠 |
|----------|------|------|
| X ポストのリンク | ✅ 正常（推定） | x_swarm_dispatcher.py が LINK 型投稿 |
| 記事 HTTP 200 | ✅ 正常 | Ghost 記事全件確認 |
| 記事末尾の CTA | ⚠️ 未確認 | 記事個別の CTA 確認が必要 |
| LIKING 原則（「あなたはどう読む？」） | ⚠️ 実装状況不明 | content-rules.md では必須 |

### X DLQ の影響

```
X DLQ: 79件の REPLY が 403 エラー
影響: 29.7%のリプライがトレンドニュースに届いていない
コンバージョンへの影響: REPLY フォーマット（30%）が事実上停止中
  → Xからのサイト流入が最大 30% 減少の可能性
```

---

## CP-05: AI エージェント経由の発見パス

### 期待されるパス

```
ユーザーが ChatGPT / Claude / Gemini に質問
  → AI が llms.txt / llms-full.txt を参照
    → nowpattern.com を推薦・URLを案内
      → ユーザーが nowpattern.com に来訪
```

### 評価

| ステップ | 状態 | 根拠 |
|----------|------|------|
| llms.txt へのアクセス | ✅ HTTP 200 | curl 確認済み |
| llms.txt の URL 正確性 | 🔴 **EN URL 誤り** | `en-predictions/` → 存在しないURL |
| llms-full.txt へのアクセス | 🔴 **301→404** | AI が全記事リスト取得不可 |
| AI が正しい URL を案内 | ❌ 失敗リスク | llms.txt の URL 誤りが直接原因 |

**最悪ケース**: ChatGPT に「Nowpatternの英語版予測ページは？」と聞くと
→ `https://nowpattern.com/en-predictions/`（404）を案内する可能性が高い。

---

## クリックパス スコアカード

| パス | 機能 | 最重要ブロッカー |
|------|------|----------------|
| CP-01: 予測参加 | ⚠️ 部分的 | np-scoreboard ID 欠落、API 疎通未確認 |
| CP-02: 有料登録 | 🔴 **BROKEN** | portal_plans=["free"] で有料プラン非表示 |
| CP-03: 言語切り替え | ⚠️ 要確認 | EN→JA 自己参照の可能性 |
| CP-04: X → 記事 | ⚠️ 部分的 | X DLQ 79件で REPLY 30%が停止 |
| CP-05: AI 発見 | 🔴 **BROKEN** | llms.txt URL 誤り + llms-full.txt 404 |

---

## 優先度別修正一覧

### 🔴 即日対応

| ID | 問題 | 修正コスト | ROI |
|----|------|-----------|-----|
| CP-001 | llms.txt EN URL 誤り | 低（2行のテキスト修正） | 高（AI 全体に即影響） |
| CP-002 | llms-full.txt 301→404 | 中（Caddyfile 修正） | 高（AI 全記事リスト取得） |
| CP-003 | portal_plans 修正 | 低（SQLite 1行 + Ghost 再起動） | **最高**（有料転換率 0→N） |

### ⚠️ 1週間以内

| ID | 問題 | 修正コスト | ROI |
|----|------|-----------|-----|
| CP-004 | np-scoreboard ID 追加 | 低（prediction_page_builder.py 2行修正） | 中（アンカーリンク復活） |
| CP-005 | X DLQ 79件 REPLY 403 解消 | 中（X API エンドポイント確認） | 高（REPLY 30% 復活） |
| CP-006 | EN→JA 言語切り替え確認 | 低（curl で確認後修正） | 中 |
| CP-007 | 読者投票 API 疎通確認 | 低（curl 1コマンド） | 中 |

---

*作成: 2026-03-28 | 証拠: SSH curl + audit_check.py 実行結果 + 既知の実装状況分析*
*次: NOWPATTERN_ISSUE_MATRIX_2026-03-28.md*
