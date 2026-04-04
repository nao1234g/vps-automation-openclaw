# Code Review Request (2026-03-29 19:44:34)

## Files changed
.claude/hooks/fact-checker.py

## Diff (2002 lines)
```diff
diff --git a/.claude/hooks/fact-checker.py b/.claude/hooks/fact-checker.py
index 3ff0da2..2938023 100644
--- a/.claude/hooks/fact-checker.py
+++ b/.claude/hooks/fact-checker.py
@@ -1,969 +1,1037 @@
-#!/usr/bin/env python3
-"""
-FACT CHECKER — Stop Hook
-=======================
-Claudeが回答を生成した後、既知の誤りパターンを検出して訂正を促す。
-exit code 2 = Claude Codeが強制的に再生成（feedback付き）
-
-VPS健全性チェック (vps-health-gate.py との連携):
-  PostToolUse hookがVPS変更後にsite_health_check.pyを実行し、
-  FAIL > 0 の場合は state/vps_health.json に記録する。
-  このStopフックはその状態を読んで、FAILが残っている間はexit(2)でブロック。
-"""
+#!/usr/bin/env python3
+"""
+FACT CHECKER — Stop Hook
+=======================
+Claudeが回答を生成した後、既知の誤りパターンを検出して訂正を促す。
+exit code 2 = Claude Codeが強制的に再生成（feedback付き）
+
+VPS健全性チェック (vps-health-gate.py との連携):
+  PostToolUse hookがVPS変更後にsite_health_check.pyを実行し、
+  FAIL > 0 の場合は state/vps_health.json に記録する。
+  このStopフックはその状態を読んで、FAILが残っている間はexit(2)でブロック。
+"""
 import json
+import os
 import sys
 import re
 import time
 from datetime import datetime
 from pathlib import Path
-
-# ── Observability: timing log ─────────────────────────────────────────────────
-_HOOK_START = time.time()
-_TIMINGS_LOG = Path(__file__).parent / "state" / "hook_timings.jsonl"
-
-
-def _write_timing(exit_code: int, check_name: str = "OK") -> None:
-    """Append a timing entry to hook_timings.jsonl (never raises)."""
-    try:
-        elapsed_ms = int((time.time() - _HOOK_START) * 1000)
-        entry = {
-            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
-            "hook": "fact-checker",
-            "check": check_name,
-            "elapsed_ms": elapsed_ms,
-            "exit_code": exit_code,
-        }
-        with open(_TIMINGS_LOG, "a", encoding="utf-8") as f:
-            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
-    except Exception:
-        pass  # タイミングログ失敗でも本体は止めない
-# ─────────────────────────────────────────────────────────────────────────────
-
-
-def log_prevention(pattern_name: str, message_preview: str = "") -> None:
-    """fact-checker.py が exit(2) を発火した時に prevention_log.json に記録する"""
-    log_path = Path(__file__).parent / "state" / "prevention_log.json"
-    try:
-        entries = []
-        if log_path.exists():
-            try:
-                entries = json.loads(log_path.read_text(encoding="utf-8"))
-            except Exception:
-                entries = []
-        entries.append({
-            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
-            "pattern": pattern_name,
-            "preview": message_preview[:120]
-        })
-        if len(entries) > 1000:
-            entries = entries[-1000:]
-        log_path.write_text(
-            json.dumps(entries, ensure_ascii=False, indent=2),
-            encoding="utf-8"
-        )
-    except Exception:
-        pass  # ログ失敗でも本体の exit(2) は止めない
-    _write_timing(2, pattern_name)
-
-# トランスクリプト解析: 検証が必要なファイル拡張子（スクリプト・コード + ビジュアル系）
-# .css/.hbs/.html はスクリーンショット検証が必要（語彙チェックでは捕捉不可能な視覚バグ対策）
-_TC_REQUIRES_VERIFICATION = re.compile(r"\.(py|sh|js|ts|rb|go|rs|php|css|hbs|html)$", re.IGNORECASE)
-
-# トランスクリプト解析: 検証スキップ対象（ドキュメント・設定・メモリ系）
-_TC_SKIP_VERIFICATION = re.compile(
-    r"(CLAUDE\.md|KNOWN_MISTAKES|AGENT_WISDOM|"
-    r"settings.*\.json|config.*\.json|package.*\.json|tsconfig.*\.json|"
-    r"[/\\]docs[/\\]|[/\\]memory[/\\]|\.claude[/\\]rules[/\\]|"
-    r"hooks[/\\]state[/\\]|"
-    r"\.md$|\.txt$|\.yml$|\.yaml$|\.json$|\.lock$|\.toml$)",
-    re.IGNORECASE
+from guard_pattern_utils import extract_guard_pattern_names
+
+# ── Observability: timing log ─────────────────────────────────────────────────
+_HOOK_START = time.time()
+_TIMINGS_LOG = Path(__file__).parent / "state" / "hook_timings.jsonl"
+
+
+def _write_timing(exit_code: int, check_name: str = "OK") -> None:
+    """Append a timing entry to hook_timings.jsonl (never raises)."""
+    try:
+        elapsed_ms = int((time.time() - _HOOK_START) * 1000)
+        entry = {
+            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
+            "hook": "fact-checker",
+            "check": check_name,
+            "elapsed_ms": elapsed_ms,
+            "exit_code": exit_code,
+        }
+        with open(_TIMINGS_LOG, "a", encoding="utf-8") as f:
+            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
+    except Exception:
+        pass  # タイミングログ失敗でも本体は止めない
+# ─────────────────────────────────────────────────────────────────────────────
+
+
+def log_prevention(pattern_name: str, message_preview: str = "") -> None:
+    """fact-checker.py が exit(2) を発火した時に prevention_log.json に記録する"""
+    log_path = Path(__file__).parent / "state" / "prevention_log.json"
+    try:
+        entries = []
+        if log_path.exists():
+            try:
+                entries = json.loads(log_path.read_text(encoding="utf-8"))
+            except Exception:
+                entries = []
+        entries.append({
+            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
+            "pattern": pattern_name,
+            "preview": message_preview[:120]
+        })
+        if len(entries) > 1000:
+            entries = entries[-1000:]
+        log_path.write_text(
+            json.dumps(entries, ensure_ascii=False, indent=2),
+            encoding="utf-8"
+        )
+    except Exception:
+        pass  # ログ失敗でも本体の exit(2) は止めない
+    _write_timing(2, pattern_name)
+
+# トランスクリプト解析: 検証が必要なファイル拡張子（スクリプト・コード + ビジュアル系）
+# .css/.hbs/.html はスクリーンショット検証が必要（語彙チェックでは捕捉不可能な視覚バグ対策）
+_TC_REQUIRES_VERIFICATION = re.compile(r"\.(py|sh|js|ts|rb|go|rs|php|css|hbs|html)$", re.IGNORECASE)
+
+# トランスクリプト解析: 検証スキップ対象（ドキュメント・設定・メモリ系）
+_TC_SKIP_VERIFICATION = re.compile(
+    r"(CLAUDE\.md|KNOWN_MISTAKES|AGENT_WISDOM|"
+    r"settings.*\.json|config.*\.json|package.*\.json|tsconfig.*\.json|"
+    r"[/\\]docs[/\\]|[/\\]memory[/\\]|\.claude[/\\]rules[/\\]|"
+    r"hooks[/\\]state[/\\]|"
+    r"\.md$|\.txt$|\.yml$|\.yaml$|\.json$|\.lock$|\.toml$)",
+    re.IGNORECASE
+)
+
+# トランスクリプト解析: 検証Bashコマンドと認定するパターン
+_TC_VERIFICATION_COMMANDS = re.compile(
+    r"(^ssh\s|"
+    r"python3?\s.*(verify|check|test|health|validate|site_health)|"
+    r"pytest|unittest|"
+    r"bash\s.*(test|verify)|"
+    r"/opt/shared/scripts/|"
+    r"site_health_check|prediction_page_builder|"
+    r"ui_vrt|ui_vrt_runner|playwright_verify|site_visual_check|"  # VRT/スクリーンショット検証
+    r"systemctl\s+(status|is-active)|"
+    r"docker\s+(ps|inspect|logs)|"
+    r"curl\s.*(nowpattern|localhost|127\.0\.0\.1)|"
+    r"python3\s+-c\s+|"
+    r"python3?\s+[\"'].*(import|ast)|"
+    r"python3?\s+.*/\.claude/hooks/)",
+    re.IGNORECASE
+)
+
+# MCPスクリーンショットツール名パターン（Playwright MCP等）
+# transcript内のtool_useブロックのnameフィールドにマッチ
+_TC_MCP_SCREENSHOT = re.compile(
+    r"(browser_take_screenshot|browser_screenshot|"
+    r"mcp__playwright__|screenshot)",
+    re.IGNORECASE
+)
+
+
+def _tc_is_verification_required(file_path: str) -> bool:
+    """このファイルは変更後に検証Bashが必要か判定する"""
+    if _TC_SKIP_VERIFICATION.search(file_path):
+        return False
+    return bool(_TC_REQUIRES_VERIFICATION.search(file_path))
+
+
+def get_unverified_edits_from_transcript(transcript_path: str) -> list:
+    """
+    トランスクリプトJSONLを解析して、最後の検証Bash以降の未検証Edit/Writeを返す。
+    語彙に完全非依存 — ツール呼び出し系列（何を言ったか ではなく 何をしたか）で判定。
+
+    設計原則 (SWE-bench / Devin AI / GitHub CI 共通):
+      最後の「検証Bash」を基準点とし、その後に行われたEdit/Writeを「未検証」と判定。
+      「変更しました」等の言葉は一切参照しない。
+    """
+    if not transcript_path:
+        return []
+    try:
+        p = Path(transcript_path)
+        if not p.exists():
+            return []
+        tool_sequence = []
+        with open(p, "r", encoding="utf-8", errors="replace") as f:
+            for i, line in enumerate(f):
+                line = line.strip()
+                if not line:
+                    continue
+                try:
+                    entry = json.loads(line)
+                except json.JSONDecodeError:
+                    continue
+                if entry.get("type") == "assistant":
+                    content = entry.get("message", {}).get("content", [])
+                    if isinstance(content, list):
+                        for block in content:
+                            if block.get("type") == "tool_use":
+                                tool_sequence.append((
+                                    i,  # 行番号（時系列順）
+                                    block.get("name", ""),
+                                    block.get("input", {})
+                                ))
+        # 逆順で最後の検証Bash OR MCPスクリーンショットを探す
+        last_verified_seq_idx = -1
+        for seq_idx in range(len(tool_sequence) - 1, -1, -1):
+            _, tname, tinput = tool_sequence[seq_idx]
+            if tname == "Bash":
+                cmd = tinput.get("command", "")
+                if _TC_VERIFICATION_COMMANDS.search(cmd):
+                    last_verified_seq_idx = seq_idx
+                    break
+            elif _TC_MCP_SCREENSHOT.search(tname):
+                # Playwright MCP等のスクリーンショットツール呼び出し = 視覚確認済み
+                last_verified_seq_idx = seq_idx
+                break
+        # 検証Bash以降のEdit/Writeを収集（重複なし）
+        unverified = []
+        seen: set = set()
+        for seq_idx in range(last_verified_seq_idx + 1, len(tool_sequence)):
+            _, tname, tinput = tool_sequence[seq_idx]
+            if tname in ("Edit", "Write"):
+                fp = tinput.get("file_path", "")
+                if fp and fp not in seen and _tc_is_verification_required(fp):
+                    unverified.append(fp)
+                    seen.add(fp)
+        return unverified
+    except Exception:
+        return []
+
+# Windows cp932 環境での絵文字出力対応
+if hasattr(sys.stdout, "reconfigure"):
+    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
+if hasattr(sys.stderr, "reconfigure"):
+    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
+
+# 既知の誤りパターン（検出 → フィードバック）
+KNOWN_ERRORS = [
+    {
+        "pattern": r"X\s*API\s*(Basic|Pro|Free)?\s*[\$￥]\s*\d+\s*[/\/]?\s*[月月]",
+        "feedback": "⛔ FACT ERROR: X APIのサブスクリプション料金（$100/月等）は2026年に廃止されました。Pay-Per-Useのみです。FLASH_CARDSを確認してください。",
+        "name": "X_API_SUBSCRIPTION"
+    },
+    {
+        "pattern": r"X\s*API\s*(Basic|Pro|Enterprise)\s*(tier|plan|プラン)",
+        "feedback": "⛔ FACT ERROR: X APIのサブスクリプションプラン（Basic/Pro/Enterprise）は2026年に廃止されました。",
+        "name": "X_API_TIER"
+    },
+    {
+        "pattern": r"Anthropic\s*API\s*(課金|従量|を使用|を利用)",
+        "feedback": "⛔ FACT ERROR: Anthropic API従量課金は使用禁止です。Claude Max $200/月の定額サブスク経由のみ使用可能です。",
+        "name": "ANTHROPIC_API_BILLING"
+    },
+    {
+        "pattern": r"@aisaintel",
+        "feedback": "⛔ FACT ERROR: @aisaintelは廃止されたXアカウントです。現在は存在しません。",
+        "name": "AISAINTEL_GHOST"
+    },
+]
+
+# ── ECC Pipeline: mistake_patterns.json から動的ロード ────────────────────────
+# auto-codifier.py が KNOWN_MISTAKES.md の GUARD_PATTERN フィールドを自動登録する。
+# ここでそのパターンを KNOWN_ERRORS に合流させる（ハードコードなし）。
+def _path_from_env(env_name: str, default: Path) -> Path:
+    override = os.environ.get(env_name, "").strip()
+    return Path(override) if override else default
+
+
+_PATTERNS_FILE = _path_from_env(
+    "CLAUDE_FACT_CHECKER_PATTERNS_FILE",
+    Path(__file__).parent / "state" / "mistake_patterns.json",
 )
-
-# トランスクリプト解析: 検証Bashコマンドと認定するパターン
-_TC_VERIFICATION_COMMANDS = re.compile(
-    r"(^ssh\s|"
-    r"python3?\s.*(verify|check|test|health|validate|site_health)|"
-    r"pytest|unittest|"
-    r"bash\s.*(test|verify)|"
-    r"/opt/shared/scripts/|"
-    r"site_health_check|prediction_page_builder|"
-    r"ui_vrt|ui_vrt_runner|playwright_verify|site_visual_check|"  # VRT/スクリーンショット検証
-    r"systemctl\s+(status|is-active)|"
-    r"docker\s+(ps|inspect|logs)|"
-    r"curl\s.*(nowpattern|localhost|127\.0\.0\.1)|"
-    r"python3\s+-c\s+|"
-    r"python3?\s+[\"'].*(import|ast)|"
-    r"python3?\s+.*/\.claude/hooks/)",
-    re.IGNORECASE
+_KNOWN_MISTAKES_FILE = _path_from_env(
+    "CLAUDE_FACT_CHECKER_KNOWN_MISTAKES_FILE",
+    Path(__file__).parent.parent.parent / "docs" / "KNOWN_MISTAKES.md",
 )
-
-# MCPスクリーンショットツール名パターン（Playwright MCP等）
-# transcript内のtool_useブロックのnameフィールドにマッチ
-_TC_MCP_SCREENSHOT = re.compile(
-    r"(browser_take_screenshot|browser_screenshot|"
-    r"mcp__playwright__|screenshot)",
-    re.IGNORECASE
-)
-
-
-def _tc_is_verification_required(file_path: str) -> bool:
-    """このファイルは変更後に検証Bashが必要か判定する"""
-    if _TC_SKIP_VERIFICATION.search(file_path):
-        return False
-    return bool(_TC_REQUIRES_VERIFICATION.search(file_path))
-
-
-def get_unverified_edits_from_transcript(transcript_path: str) -> list:
-    """
-    トランスクリプトJSONLを解析して、最後の検証Bash以降の未検証Edit/Writeを返す。
-    語彙に完全非依存 — ツール呼び出し系列（何を言ったか ではなく 何をしたか）で判定。
-
-    設計原則 (SWE-bench / Devin AI / GitHub CI 共通):
-      最後の「検証Bash」を基準点とし、その後に行われたEdit/Writeを「未検証」と判定。
-      「変更しました」等の言葉は一切参照しない。
-    """
-    if not transcript_path:
-        return []
-    try:
-        p = Path(transcript_path)
-        if not p.exists():
-            return []
-        tool_sequence = []
-        with open(p, "r", encoding="utf-8", errors="replace") as f:
-            for i, line in enumerate(f):
-                line = line.strip()
-                if not line:
-                    continue
-                try:
-                    entry = json.loads(line)
-                except json.JSONDecodeError:
-                    continue
-                if entry.get("type") == "assistant":
-                    content = entry.get("message", {}).get("content", [])
-                    if isinstance(content, list):
-                        for block in content:
-                            if block.get("type") == "tool_use":
-                                tool_sequence.append((
-                                    i,  # 行番号（時系列順）
-                                    block.get("name", ""),
-                                    block.get("input", {})
-                                ))
-        # 逆順で最後の検証Bash OR MCPスクリーンショットを探す
-        last_verified_seq_idx = -1
-        for seq_idx in range(len(tool_sequence) - 1, -1, -1):
-            _, tname, tinput = tool_sequence[seq_idx]
-            if tname == "Bash":
-                cmd = tinput.get("command", "")
-                if _TC_VERIFICATION_COMMANDS.search(cmd):
-                    last_verified_seq_idx = seq_idx
-                    break
-            elif _TC_MCP_SCREENSHOT.search(tname):
-                # Playwright MCP等のスクリーンショットツール呼び出し = 視覚確認済み
-                last_verified_seq_idx = seq_idx
-                break
-        # 検証Bash以降のEdit/Writeを収集（重複なし）
-        unverified = []
-        seen: set = set()
-        for seq_idx in range(last_verified_seq_idx + 1, len(tool_sequence)):
-            _, tname, tinput = tool_sequence[seq_idx]
-            if tname in ("Edit", "Write"):
-                fp = tinput.get("file_path", "")
-                if fp and fp not in seen and _tc_is_verification_required(fp):
-                    unverified.append(fp)
-                    seen.add(fp)
-        return unverified
-    except Exception:
-        return []
-
-# Windows cp932 環境での絵文字出力対応
-if hasattr(sys.stdout, "reconfigure"):
-    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
-if hasattr(sys.stderr, "reconfigure"):
-    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
-
-# 既知の誤りパターン（検出 → フィードバック）
-KNOWN_ERRORS = [
-    {
-        "pattern": r"X\s*API\s*(Basic|Pro|Free)?\s*[\$￥]\s*\d+\s*[/\/]?\s*[月月]",
-        "feedback": "⛔ FACT ERROR: X APIのサブスクリプション料金（$100/月等）は2026年に廃止されました。Pay-Per-Useのみです。FLASH_CARDSを確認してください。",
-        "name": "X_API_SUBSCRIPTION"
-    },
-    {
-        "pattern": r"X\s*API\s*(Basic|Pro|Enterprise)\s*(tier|plan|プラン)",
-        "feedback": "⛔ FACT ERROR: X APIのサブスクリプションプラン（Basic/Pro/Enterprise）は2026年に廃止されました。",
-        "name": "X_API_TIER"
-    },
-    {
-        "pattern": r"Anthropic\s*API\s*(課金|従量|を使用|を利用)",
-        "feedback": "⛔ FACT ERROR: Anthropic API従量課金は使用禁止です。Claude Max $200/月の定額サブスク経由のみ使用可能です。",
-        "name": "ANTHROPIC_API_BILLING"
-    },
-    {
-        "pattern": r"@aisaintel",
-        "feedback": "⛔ FACT ERROR: @aisaintelは廃止されたXアカウントです。現在は存在しません。",
-        "name": "AISAINTEL_GHOST"
-    },
-]
-
-# ── ECC Pipeline: mistake_patterns.json から動的ロード ────────────────────────
-# auto-codifier.py が KNOWN_MISTAKES.md の GUARD_PATTERN フィールドを自動登録する。
-# ここでそのパターンを KNOWN_ERRORS に合流させる（ハードコードなし）。
-_PATTERNS_FILE = Path(__file__).parent / "state" / "mistake_patterns.json"
 if _PATTERNS_FILE.exists():
-    try:
-        _dynamic = json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
-        _existing_names = {e.get("name", "") for e in KNOWN_ERRORS}
-        for _p in _dynamic:
-            if _p.get("name", "") not in _existing_names and _p.get("pattern") and _p.get("feedback"):
-                KNOWN_ERRORS.append(_p)
-    except Exception:
-        pass  # パターンファイル読み込み失敗は無視（既存ガードは有効のまま）
-# ─────────────────────────────────────────────────────────────────────────────
-
-# ──────────────────────────────────────────────────────────────────────────────
-# 「実装したつもり」検出: Webアクセス可能なファイル/設定を
-# "実装完了" と報告する際に、検証証拠（curlの出力等）がない場合にブロック
-# ──────────────────────────────────────────────────────────────────────────────
-# 対象ファイル/エンドポイント（これらを「作った/設定した」と言う場合は証拠を要求）
-WEB_RESOURCE_CLAIM_PATTERN = re.compile(
-    r"(llms\.txt|robots\.txt|sitemap\.xml|\.well-known/|"
-    r"Caddyfile|caddy.*設定|ghost.*設定|nginx.*設定|"
-    r"自動投稿|cronを設定|cronを追加|cron.*設定|deploy|デプロイ)"
-    r".{0,200}"
-    r"(実装しました|作成しました|設定しました|完了しました|追加しました|"
-    r"デプロイしました|有効にしました|できました|しておきました)",
-    re.IGNORECASE | re.DOTALL
-)
-
-# 検証証拠として認められるパターン
-VERIFICATION_EVIDENCE_PATTERN = re.compile(
-    r"(curl\s|HTTP/[12]\.[01]|200 OK|404 Not Found|Content-Type:|"
-    r"確認しました.{0,50}(curl|アクセス|レスポンス|HTTP)|"
-    r"curl.*nowpattern|wget.*nowpattern|実際にアクセスして確認|"
-    r"テスト結果|エラーなし|正常に動作|稼働確認)",
-    re.IGNORECASE
-)
-
-# ──────────────────────────────────────────────────────────────────────────────
-# 「治った治った」虚偽報告検出:
-# バグ/問題/サービスが「直った/解決した」と報告するが証拠がない場合にブロック
-# ──────────────────────────────────────────────────────────────────────────────
-RUNTIME_CLAIM_PATTERN = re.compile(
-    r"("
-    r"直りました|治りました|"
-    r"正常に戻りました|正常に動くようになりました|"
-    r"(問題|エラー|バグ|不具合).{0,80}(直り|解決|修正)しました|"
-    r"解決しました.{0,80}(問題|エラー|バグ|不具合)|"
-    r"(再起動|リスタート|restart).{0,80}(しました|しておきました).{0,120}(正常|問題なく|動い|稼働)|"
-    r"(動作|稼働)を確認しました"
-    r")",
-    re.IGNORECASE | re.DOTALL
-)
-
-# 実行確認証拠（VERIFICATION_EVIDENCE_PATTERNと組み合わせて判定）
-RUNTIME_PROOF_PATTERN = re.compile(
-    r"("
-    r"Active: active|"
-    r"FAIL: ?0[^\d]|FAIL:0[^\d]|"
-    r"✅ \[自動検品 OK\]|"
-    r"動作確認済み|稼働確認済み|実際に確認|"
-    r"コマンドの出力|実行結果|以下の出力"
-    r")",
-    re.IGNORECASE
-)
-
-# ──────────────────────────────────────────────────────────────────────────────
-# 「件数思い込み」検出: データソース件数 ≠ 実際のシステム出力件数
-# 「N件確認済み」「全件適用」等を主張する場合、観測コマンドの出力を必須とする
-# 根本原因: prediction_db.json=7件 → ページ=19件 のような思い込みを物理ブロック
```
... truncated (2002 total lines). Read full diff with: git diff -- .claude/hooks/fact-checker.py

## Review checklist
1. Correctness: Does the logic do what it claims?
2. Security: Any injection, data leak, or auth bypass?
3. Nowpattern invariants: Does it violate prediction_db integrity or Brier Score rules?
4. Edge cases: What could break?
5. Suggestion: One concrete improvement.

Write your review to: .agent-mailbox/review-response.md
