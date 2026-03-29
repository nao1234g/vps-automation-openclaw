# Verification Log — 2026-03-29 Session 2

> このセッションで実施したライブ検証コマンドと確認結果の証跡。
> 前セッション: VERIFICATION_LOG_2026-03-29.md (Phase 0-4 + nav taxonomy-ja fix)

---

## 検証 1: ISS-014 Homepage WebSite スキーマ重複確認

```
目的: ホームページに WebSite が 2件あるか確認
```

**実行内容**: SSH 経由で `python3` を使いホームページの JSON-LD スキーマを全件列挙

**結果**:
```
ISS-014 homepage: ['WebSite', 'NewsMediaOrganization']
```

**判定**: WebSite は **1件のみ**。重複なし。
**更新**: ISS-014 → **RESOLVED**（元々問題が存在しなかった。監査時の仮説誤り）

---

## 検証 2: ISS-003 /en/predictions/ スキーマ確認

```
目的: Article schema が残存しているか、CollectionPage は存在するか
```

**結果**:
```
ISS-003 /en/predictions/: ['Article', 'NewsMediaOrganization', 'Dataset', 'FAQPage', 'CollectionPage']
```

**判定**:
- CollectionPage ✅ (prior session で注入済み)
- Article ⚠️ — Ghost 5.130.6 `ghost_head` が type=page にも Article を自動生成する**仕様**。
  codeinjection_head の Article ではなく Ghost コア由来のため除去にはテーマ修正が必要。

**詳細調査**:
- Ghost DB で `type='page'` 確認済み → Ghost は page でも Article を生成
- codeinjection_head: hreflang のみ（Article なし）
- position=3711（ghost_head 由来）vs codeinjection (後半)
- 修正コスト: 高（theme `default.hbs` 変更 + Ghost 再起動）
- SEO 影響: 中（CollectionPage/Dataset/FAQPage が優先認識される可能性高）

**結論**: ISS-003 は prior session の RESOLVED ステータスを維持。Article残存は低優先監視継続。

---

## 検証 3: ISS-012 /about/ /taxonomy/ スキーマ確認

```
目的: Article schema が残存しているか、WebPage は存在するか
```

**結果**:
```
=== about ===
  [0] Article   (pos=3711, ghost_head 由来)
  [1] NewsMediaOrganization
  [2] WebPage   (codeinjection_head 由来)

=== taxonomy ===
  [0] Article   (pos=3711, ghost_head 由来)
  [1] NewsMediaOrganization
  [2] WebPage   (codeinjection_head 由来)
```

**判定**: ISS-003 と同根。WebPage ✅ 存在。Article は Ghost ghost_head 由来。
ISS-012 の RESOLVED ステータスを維持。Article残存は低優先監視継続。

---

## 検証 4: ghost_url 対象予測 JA スラッグ存在確認

```
目的: NP-2026-0020/21/25/27 の正しい JA ghost_url を特定・存在確認
```

**Ghost DB 確認**:
```sql
SELECT slug, title, status FROM posts
WHERE slug IN (
  'btc-70k-march-31-2026',
  'btc-90k-march-31-2026',
  'fed-fomc-march-2026-rate-decision',
  'khamenei-assassination-iran-supreme-leader-succession-2026'
)
```

**結果**: 4件とも `status=published` ✅

**Ghost ポート 2368 直接アクセス確認**:
```
301 //btc-70k-march-31-2026/      ← 存在確認（301 は canonical redirect）
301 //btc-90k-march-31-2026/      ← 存在確認
301 //fed-fomc-march-2026-rate-decision/    ← 存在確認
301 //khamenei-assassination-iran-supreme-leader-succession-2026/  ← 存在確認
```

**ID-スラッグ対応確認** (DB 実データから取得):
| prediction_id | JA タイトル | 現 ghost_url (EN) | 正しい ghost_url (JA) |
|--------------|-----------|-------------------|----------------------|
| NP-2026-0020 | FRBは2026年3月のFOMCで利下げするか | `/en/en-fed-fomc-march-2026-rate-decision/` | `/fed-fomc-march-2026-rate-decision/` |
| NP-2026-0021 | BTCは2026年3月末までに9万ドルを回復するか | `/en/en-btc-90k-march-31-2026/` | `/btc-90k-march-31-2026/` |
| NP-2026-0025 | ハメネイ師暗殺後... | `/en/en-khamenei-assassination-iran-supreme-leader-succession-2026/` | `/khamenei-assassination-iran-supreme-leader-succession-2026/` |
| NP-2026-0027 | ビットコインは2026年3月末に$70,000を超えるか | `/en/en-btc-70k-march-31-2026/` | `/btc-70k-march-31-2026/` |

**注記**: FINAL_HANDOFF_2026-03-29 の提案は NP-2026-0020 と NP-2026-0027 のスラッグが入れ替わっていた。
本セッションで DB 実データから正しいマッピングを確認して修正。

---

## 実装 1: prediction_db.json ghost_url 4件修正

```bash
# バックアップ作成
cp prediction_db.json prediction_db.json.bak-20260329-080320

# Python スクリプトで4件更新
```

**変更内容**:
- NP-2026-0020: `https://nowpattern.com/en/en-fed-fomc-march-2026-rate-decision/` → `https://nowpattern.com/fed-fomc-march-2026-rate-decision/`
- NP-2026-0021: `https://nowpattern.com/en/en-btc-90k-march-31-2026/` → `https://nowpattern.com/btc-90k-march-31-2026/`
- NP-2026-0025: `https://nowpattern.com/en/en-khamenei-assassination-iran-supreme-leader-succession-2026/` → `https://nowpattern.com/khamenei-assassination-iran-supreme-leader-succession-2026/`
- NP-2026-0027: `https://nowpattern.com/en/en-btc-70k-march-31-2026/` → `https://nowpattern.com/btc-70k-march-31-2026/`

---

## 実装 2: prediction_page_builder.py 再実行

```bash
cd /opt/shared/scripts
python3 prediction_page_builder.py --force
```

**結果**: `[OK] E2Eテスト全PASS — UIが正常に動作しています`

**検証** (Ghost DB 確認):
```sql
-- JA predictions page
SELECT INSTR(html, 'fed-fomc-march-2026-rate-decision') as fomc_pos,
       INSTR(html, 'btc-90k-march-31-2026') as btc90k_pos,
       INSTR(html, 'khamenei-assassination') as kha_pos,
       INSTR(html, 'btc-70k-march-31-2026') as btc70k_pos
FROM posts WHERE slug='predictions';
-- 結果: 262626|271767|288789|297610 (全件 > 0, 存在確認)

-- EN predictions page (同様に確認)
-- 結果: 794895|804464|822417|831648 (全件 > 0)
```

✅ JA/EN 両ページで4件のJA URLが正しく反映済み

---

## 検証サマリー

| 検証項目 | 結果 | アクション |
|---------|------|----------|
| ISS-014 WebSite重複 | WebSite=1件（重複なし） | RESOLVED |
| ISS-003 Article残存 | Article from ghost_head (仕様)。CollectionPage✅ | 監視継続 |
| ISS-012 Article残存 | Article from ghost_head (仕様)。WebPage✅ | 監視継続 |
| ghost_url NP-0020 | 修正完了（JA URL反映） | DONE |
| ghost_url NP-0021 | 修正完了（JA URL反映） | DONE |
| ghost_url NP-0025 | 修正完了（JA URL反映） | DONE |
| ghost_url NP-0027 | 修正完了（JA URL反映） | DONE |
| prediction page rebuild | E2E全PASS | DONE |

---

*作成: 2026-03-29 Session 2 | Engineer: Claude Code (local)*
