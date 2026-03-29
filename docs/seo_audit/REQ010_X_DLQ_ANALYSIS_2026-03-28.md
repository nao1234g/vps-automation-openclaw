# REQ-010 X DLQ Analysis & Closure — 2026-03-28

> x_swarm_dispatcher.py の4つの根本原因修正と、DLQ完全解消の証跡。

---

## 根本原因チェーン（4件）

| # | 関数 | 根本原因 | 影響 |
|---|------|---------|------|
| Fix 1 | `retry_dlq()` | RED_TEAM thread content を `post_tweet()` で送信 → thread構造を無視 | スレッド投稿が常に失敗してDLQに残留 |
| Fix 2 | `retry_dlq()` | `--dry-run` フラグ付きでも `save_dlq(remaining)` を呼ぶ | dry-runが副作用（DLQ書き換え）を発生させる |
| Fix 3 | `dispatch_one()` | スレッド失敗時のHTTPコードが上位に伝播しない → `error=True` のみ | DLQに保存されるエラー種別が不明（429/403判定不能） |
| Fix 4 | `run_cycle()` | 403 duplicate/policy違反をDLQに追加 → 永久に再試行 | 403エラーがDLQに詰まり続ける |

---

## Before 状態（修正前）

- **DLQ item count（修正前）**: 5件（all `error: True`）
- **failure type breakdown**:
  - 5件全て `error: True`（型が不明）= Fix 3 の根本原因による（thread失敗時のHTTPコードが伝播していなかった）
  - Fix 3適用後は `error: <実際のHTTPコード>` が記録される

---

## Fix 1 — retry_dlq() thread content ルーティング修正

**修正箇所**: `/opt/shared/scripts/x_swarm_dispatcher.py` lines 600-635

**修正内容**: `content.get("thread")` が真のとき `post_thread()` にルーティング。それ以外は `post_tweet()`。

```python
# RED_TEAM / thread content — use post_thread() not post_tweet()
if content.get("thread"):
    thread_texts = content["thread"]
    if dry_run:
        print(f"  [DRY-RUN] {item['format']}: thread({len(thread_texts)}ツイート) {thread_texts[0][:60]}...")
        continue
    thread_results = post_thread(auth, thread_texts)
    # Poll on last tweet if specified
    poll = content.get("poll_on_last")
    if poll and thread_results and thread_results[-1].get("id"):
        post_tweet(auth, "あなたはどちら？", poll=poll,
                   reply_to_id=thread_results[-1]["id"])
    if thread_results and thread_results[0].get("id"):
        print(f"  ✅ DLQ再試行成功: {item['format']} (thread {len(thread_texts)}ツイート)")
    else:
        item["retries"] = retries + 1
        ...
        remaining.append(item)
    continue
```

**検証**: `grep -n 'content.get..thread' /opt/shared/scripts/x_swarm_dispatcher.py` → line 604 ✅

---

## Fix 2 — retry_dlq() dry-run gate 追加

**修正箇所**: `/opt/shared/scripts/x_swarm_dispatcher.py` lines 646-649

**修正内容**: `save_dlq(remaining)` 呼び出しを `if not dry_run:` でガード。

```python
    if not dry_run:
        save_dlq(remaining)
    print(f"DLQ残り: {len(remaining)}件")
```

**検証**: `grep -n 'if not dry_run' /opt/shared/scripts/x_swarm_dispatcher.py` → line 646 ✅

---

## Fix 3 — dispatch_one() thread失敗HTTPコード伝播修正

**修正箇所**: `/opt/shared/scripts/x_swarm_dispatcher.py` line 419

**修正内容**: `thread_results[0].get("error", True)` → `if thread_results else True` でNoneGuard付き。

```python
error_http = thread_results[0].get("error", True) if thread_results else True
return {"error": error_http, "format": fmt, "content": content}
```

**検証**: `grep -n 'error_http' /opt/shared/scripts/x_swarm_dispatcher.py` → line 419 ✅

---

## Fix 4 — run_cycle() 403 DLQスキップ

**修正箇所**: `/opt/shared/scripts/x_swarm_dispatcher.py` lines 510-515

**修正内容**: `error_code == 403` の場合は DLQ に追加せず `continue`（再試行しても意味がないため）。

```python
elif error_code == 403:
    # 403 = duplicate content / policy violation - retry won't help, skip DLQ
    print(f"  ❌ 403 Forbidden (duplicate/policy). DLQに追加しない。")
    continue
```

**検証**: `grep -n '403 Forbidden' /opt/shared/scripts/x_swarm_dispatcher.py` → line 513 ✅

---

## After 状態（修正後）

```
=== DLQ CURRENT STATE ===
DLQ items: 0
DLQは空です。
```

**確認方法（2026-03-28 実行）**:
```bash
ssh root@163.44.124.123 "python3 -c \"
import json
dlq = json.load(open('/opt/shared/scripts/x_dlq.json'))
print('DLQ items:', len(dlq))
\""
# → DLQ items: 0
```

---

## 関数エントリーポイント一覧（参照用）

| 関数 | 開始行 |
|------|--------|
| `dispatch_one()` | line 356 |
| `run_cycle()` | line 449 |
| `retry_dlq()` | line 576 |

---

## REQ-010 完了条件チェックリスト

- [x] before の DLQ 件数を記録した（5件、all `error: True`）
- [x] failure type を分類した（全件 `error: True` = Fix 3 根本原因）
- [x] low-risk fix 4件を適用した
- [x] DLQ = 0 を確認した（after状態）
- [x] 4修正箇所それぞれを grep で確認した
- [x] docs を更新した（本ファイル + VERIFICATION_LOG + WEEK1_EXECUTION_STATUS + FINAL_HANDOFF）

---

*作成: 2026-03-28 REQ-010 クロージャー | Engineer: Claude Code (local)*
