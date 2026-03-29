# NOWPATTERN TOP 10 LINK FIXES — 2026-03-28
> 監査Round 4（ホームページ実地監査）の成果を反映した修正優先リスト
> 依拠: LINK_FIX_PROPOSALS_2026-03-28.md（詳細手順はそちら参照）
> 選定基準: ユーザー体験への直接影響 × 修正コスト（低いほど優先）

---

## 選定の考え方

```
ROI = 効果 ÷ 実装コスト

FIX-001（Caddyfile 1行）= 最高ROI
FIX-002（Ghost Admin）  = 高ROI
FIX-003（PB修正）       = 中ROI（が P1 の信頼性に関わる）
```

---

## TOP 10 優先修正リスト

### 🔴 #1 — フッター「タクソノミーガイド」誤リダイレクト修正

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-001 |
| 根本原因 | `/etc/caddy/nowpattern-redirects.txt` の設定誤り（1行） |
| 影響 | 全ページフッターから間違いページへ誘導 → 回遊性 0/10 |
| 修正コスト | 1分（Caddyfile sed + reload） |
| 検証 | `curl -o /dev/null -w "%{redirect_url}\n" -s https://nowpattern.com/taxonomy-guide-ja/` → `/taxonomy-guide/` を確認 |

**修正コマンド（1行）:**
```bash
ssh root@163.44.124.123 "cp /etc/caddy/nowpattern-redirects.txt /etc/caddy/nowpattern-redirects.txt.bak-$(date +%Y%m%d) && sed -i 's|redir /taxonomy-guide-ja/ /taxonomy/ permanent|redir /taxonomy-guide-ja/ /taxonomy-guide/ permanent|' /etc/caddy/nowpattern-redirects.txt && systemctl reload caddy"
```

---

### 🔴 #2 — ホームページ 404 記事リンク除去

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-002 |
| 根本原因 | Ghost DBに存在しないslugがホームページに表示されている |
| 影響 | ホームページ記事#4クリックで404 → 信頼性を損なう |
| 修正コスト | 5〜10分（Ghost Admin で Featured 記事を差し替え） |
| 検証 | ホームページの全10件記事リンクが200を返すこと |

**修正手順（Ghost Admin）:**
```
1. Ghost Admin → Posts
2. 「南シナ海の米中軍事対峙」タイトルで検索
3. 対象記事が削除済みなら → Featured設定を外す か別記事を Featured に設定
4. ホームページから問題リンクが消えることを確認
```

---

### 🔴 #3 — `id="np-resolved"` セクション復元

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-003 |
| 根本原因 | prediction_page_builder.py の出力に resolved セクション ID が欠落 |
| 影響 | Oracle Statement 内の `#np-resolved` リンクが全部機能しない。解決済み実績が不可視 |
| 修正コスト | 30〜60分（Python スクリプト調査 + 修正 + 再生成） |
| 検証 | `curl -s https://nowpattern.com/predictions/ \| grep 'id="np-resolved"'` → 1件ヒット |

**確認コマンド（修正前の状態確認）:**
```bash
curl -s https://nowpattern.com/predictions/ | grep -oE 'id="np-[^"]*"'
# 現在: np-tracking-list, np-search, np-pagination, np-cta-ja, np-cta-en のみ
# 修正後に追加されるべき: np-scoreboard ✅, np-resolved ❌ → ✅ にする
```

---

### 🟠 #4 — EN Nav JS の /en-predictions/ → /en/predictions/ 修正

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-004 |
| 根本原因 | EN ページの JavaScript オーバーライドが旧URLを参照 |
| 影響 | EN nav「予測トラッカー」クリック時に不要な 301 が発生 |
| 修正コスト | 10分（Ghost Admin codeinjection_head 更新） |
| 検証 | `curl -s https://nowpattern.com/en/predictions/ \| grep "en-predictions/"` → 0件 |

**修正手順:**
```bash
# ENページすべてのcodeinjection_headで古いURLを確認
ssh root@163.44.124.123 "sqlite3 /var/www/nowpattern/content/data/ghost.db \
  \"SELECT slug FROM posts WHERE slug LIKE 'en-%' AND INSTR(codeinjection_head, 'en-predictions/') > 0;\""

# 見つかったページのURLを修正（Ghost API or SQLite直接）
```

---

### 🟠 #5 — Ghost Nav「力学で探す」を /taxonomy/ 直リンクに変更

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-005 |
| 根本原因 | Ghost ナビゲーション設定が `/taxonomy-ja/` を指している |
| 影響 | 全ページナビから不要な 301 発生 |
| 修正コスト | 5分（Ghost Admin → Settings → Navigation） |
| 検証 | ホームページソースで `taxonomy-ja` が nav に存在しないこと |

```
Ghost Admin → Settings → Navigation →「力学で探す」のURL: /taxonomy-ja/ → /taxonomy/
```

---

### 🟠 #6 — EN article リンクの /en/en- プレフィックス修正

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-006 |
| 根本原因 | prediction_page_builder.py の EN 記事 URL 生成ロジックが Ghost 内部スラッグを使用 |
| 影響 | /en/predictions/ の記事リンク 4 件が 301 経由 |
| 修正コスト | 30分（スクリプト修正 + 再生成） |
| 検証 | `curl -s https://nowpattern.com/en/predictions/ \| grep '/en/en-'` → 0件 |

---

### 🟡 #7 — フッターリンク拡充（X + Subscribe + Predictions 追加）

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-007 |
| 根本原因 | Ghost Admin フッターナビゲーションにリンクが2件しかない |
| 影響 | フッター充実度 2/10 → 最低限の導線不足 |
| 修正コスト | 10分（Ghost Admin → Secondary Navigation） |
| 検証 | ページフッターに X、Subscribe、Predictions リンクが表示されること |

**追加するリンク:**
```
X @nowpattern → https://x.com/nowpattern
Subscribe（無料） → #/portal/signup
予測トラッカー → /predictions/
```

---

### 🟡 #8 — Ghost Nav の taxonomy 言語切り替えURL修正

| 属性 | 内容 |
|------|------|
| 対応 FIX | N/A（URL_AUDIT ISS 相当） |
| 根本原因 | /taxonomy/ 内の言語切替リンクが `/taxonomy-en/` になっている（301経由） |
| 影響 | taxonomy ページでJA→EN切替時に不要な 301 発生 |
| 修正コスト | 15分（Ghost Admin の taxonomy-ja ページ codeinjection_head を修正） |
| 検証 | `/taxonomy/` ページソースの言語切替リンクが `/en/taxonomy/` を直接指すこと |

---

### 🟡 #9 — Hero 価値提案テキスト追加

| 属性 | 内容 |
|------|------|
| 対応 FIX | FIX-008 |
| 根本原因 | ホームページ Hero に「何のサイトか」を説明するテキストがない |
| 影響 | 3秒テスト 6/10（Subscribe ボタンより先に価値が伝わらない） |
| 修正コスト | 30分（テーマ修正 or Ghost codeinjection） |
| 検証 | ホームページ最上部に 1 行の価値提案テキストが表示されること |

**提案テキスト:**
```
JA: 「予測精度を公開する、世界初のバイリンガル予測プラットフォーム」
EN: "The world's first bilingual prediction platform with a public track record."
```

---

### 🟢 #10 — robots.txt に AI クローラー許可ディレクティブ追加

| 属性 | 内容 |
|------|------|
| 対応 FIX | ISS-015 |
| 根本原因 | robots.txt が `User-agent: *` のみで AI ボットへの明示的許可なし |
| 影響 | GPTBot / ClaudeBot / Googlebot への意図が不明確 |
| 修正コスト | 5分（robots.txt に 6行追加） |
| 検証 | `curl -s https://nowpattern.com/robots.txt \| grep -E 'GPTBot|ClaudeBot'` → 各行確認 |

**追加する設定:**
```
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Googlebot
Allow: /
```

---

## 実施順序と工数サマリー

### 即日実施可能（P1: 合計 75〜80 分）

| 順 | Fix | 工数 | 担当者 |
|----|-----|------|--------|
| 1 | #1（Caddyfile taxonomy-guide-ja 修正） | 5分 | local-Claude or NEO-ONE |
| 2 | #2（404 記事リンク修正） | 15分 | local-Claude or NEO-ONE |
| 3 | #3（np-resolved セクション復元） | 60分 | NEO-ONE |

### 1週間以内（P2: 合計 50〜60 分）

| 順 | Fix | 工数 | 担当者 |
|----|-----|------|--------|
| 4 | #4（EN Nav JS URL 修正） | 15分 | NEO-ONE |
| 5 | #5（Ghost Nav taxonomy 直リンク） | 5分 | local-Claude or NEO-ONE |
| 6 | #6（EN article /en/en- プレフィックス修正） | 45分 | NEO-ONE |

### 2週間以内（P3: 合計 60〜70 分）

| 順 | Fix | 工数 | 担当者 |
|----|-----|------|--------|
| 7 | #7（フッターリンク拡充） | 10分 | local-Claude or NEO-ONE |
| 8 | #8（taxonomy 言語切替 URL 修正） | 15分 | NEO-ONE |
| 9 | #9（Hero 価値提案テキスト） | 30分 | local-Claude |
| 10 | #10（robots.txt AI クローラー許可） | 5分 | local-Claude or NEO-ONE |

---

## 修正後の期待スコア変化

| 指標 | 現在 | #1〜3 実施後 | #1〜10 実施後 |
|------|------|------------|-------------|
| フッター回遊性 | 0/10 | 10/10 | 10/10 |
| ホームリンク品質 | 9/10 | 10/10 | 10/10 |
| 解決済み実績可視性 | 2/10 | 8/10 | 8/10 |
| URL品質スコア | 90% | 95% | 98% |
| フッター充実度 | 2/10 | 2/10 | 8/10 |
| 総合UXスコア | 5.8/10 | 7.0/10 | 8.2/10 |

---

## 重要な注記

### ISS-007 ステータス訂正（必須）

`NOWPATTERN_ISSUE_MATRIX_2026-03-28.md` の **ISS-007** は `✅ RESOLVED` と記録されているが、
2026-03-28 ライブサイト確認で `id="np-resolved"` が **現在も存在しない** ことが実証された。
実装セッション開始前に ISS-007 を `OPEN` に戻すこと。

### #3（np-resolved）実装の注意事項

- `prediction-design-system.md` の凍結ベースラインに従い、セクション順序を維持する
- `np-resolved` ID は HTML クラスと同様に保護対象
- 修正後は `/predictions/` と `/en/predictions/` 両方を再生成・確認すること

---

*作成: 2026-03-28 | 基礎データ: LINK_FIX_PROPOSALS_2026-03-28.md + 4監査ドキュメント*
