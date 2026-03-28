# 301リダイレクト検証レポート（2026-03-28）

## 概要

EN記事スラッグ修正（190件）に伴う301リダイレクトの動作確認結果。

## 実施日時

2026-03-28 JST（slug_repair2.py --execute 実行直後）

## リダイレクト設定

**設定ファイル**: `/etc/caddy/nowpattern-redirects.txt`
**追加行数**: 190行（`redir /en/{old-slug}/ /en/{new-slug}/ permanent`）
**Caddy reload**: 実行済み（exit code 0）

## 検証結果

### サンプル検証（手動確認）

| 旧URL（抜粋） | 新URL | HTTP Status |
|-------------|-------|-------------|
| `/en/en-bitutokoin1500mo-yuan-tu-po-...-zu-zhuan-huan/` | `/en/bitcoin-predicted-to-surpass-15-million/` | **301** ✅ |
| `/en/en-nan-sinahai-nomi-zhong-jun-shi-...-risukuwolin.../` | `/en/us-china-military-standoff-in-the-south-china/` | **301** ✅ |
| `/en/bitcoin-predicted-to-surpass-15-million/` | — | **200** ✅ |
| `/en/us-china-military-standoff-in-the-south-china/` | — | **200** ✅ |

### 全件統計

- 修正スクリプト報告: 189件成功 / 0件失敗（1件は別途手動テスト = 合計190件）
- Caddyリダイレクト行数: 190行（`grep -c '^redir'` で確認）
- `/etc/caddy/nowpattern-redirects.txt` 合計 redir 行数: **237行**（既存47行+新規190行）

## リダイレクトループ・整合性分析（2026-03-28 追加検証）

**分析対象**: `/etc/caddy/nowpattern-redirects.txt` 全237行

| チェック項目 | 期待値 | 実測値 | 判定 |
|------------|--------|--------|------|
| 重複ソース（同一旧URLが複数redir） | 0件 | **0件** | ✅ |
| ループ候補（dst=別エントリのsrc） | 0件 | **2件** ← 精査要 | 要確認 |
| 悪いdst（`/en/en-`含む） | 0件 | **0件** | ✅ |

### ループ候補の精査結果

Python解析で検出された2件のループ候補:

| ソース | 送り先 | 評価 |
|--------|--------|------|
| `/en-predictions-2/` | `/en-predictions/` | 2ホップチェーン（後述） |
| `/en-predictions-3/` | `/en-predictions/` | 2ホップチェーン（後述） |

**チェーン展開**:
```
/en-predictions-2/ → /en-predictions/ → /en/predictions/  (終端・循環なし)
/en-predictions-3/ → /en-predictions/ → /en/predictions/  (終端・循環なし)
```

**結論**: 循環ループ（A→B→A）は**ゼロ**。2件は多段チェーン（2-hop chain）で最終的に `/en/predictions/` へ到達し正常終了。Caddyは多段リダイレクトを処理するため動作上の問題なし。

## 注意事項

### 旧URLへのアクセス

旧スラッグ（例: `en-nan-sinahai-nomi-...`）は Ghost から削除済みのため、Caddy が 301 を返す前に Ghost が 404 を返す可能性あり。

**実測**: Caddy は Ghost より前にリダイレクトを処理するため、旧URLへのアクセスは正しく 301 を返す。

### Googleへの再クロール依頼

- Google Search Console で URL検査 → 再クロール依頼 を実施することを推奨
- 旧URLが Google にインデックスされていた場合、301 を認識するまで 1〜4 週間かかる
- Search Console の「サイトマップ」再送信も推奨

### canonical の整合性

修正後の新URLには Ghost が生成する canonical が自動的に設定される。
旧URLを canonical に指定していた記事がある場合は別途確認が必要（確認済み: 自動canonical = Ghost slug から生成 → 新slugと一致）

## ロールバック手順（必要な場合）

```bash
# 1. slug_migration_map.json で old/new を逆引き
# 2. Ghost Admin API でスラッグを旧に戻す
# 3. Caddyリダイレクトの該当行を削除
# 4. caddy reload

# migration map 参照
ssh root@163.44.124.123 "cat /opt/shared/reports/slug_migration_map.json | python3 -c \"
import json,sys
m=json.load(sys.stdin)
for x in m:
    print(x['new_slug'], '->', x['old_slug'])
\" | head -20"
```

---

*作成: 2026-03-28 | 担当: LEFT_EXECUTOR*
