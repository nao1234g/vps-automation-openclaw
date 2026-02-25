#!/usr/bin/env python3
"""
FACT CHECKER — Stop Hook
=======================
Claudeが回答を生成した後、既知の誤りパターンを検出して訂正を促す。
exit code 2 = Claude Codeが強制的に再生成（feedback付き）

VPS健全性チェック (vps-health-gate.py との連携):
  PostToolUse hookがVPS変更後にsite_health_check.pyを実行し、
  FAIL > 0 の場合は state/vps_health.json に記録する。
  このStopフックはその状態を読んで、FAILが残っている間はexit(2)でブロック。
"""
import json
import sys
import re
import time
from pathlib import Path

# Windows cp932 環境での絵文字出力対応
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 既知の誤りパターン（検出 → フィードバック）
KNOWN_ERRORS = [
    {
        "pattern": r"X\s*API\s*(Basic|Pro|Free)?\s*[\$￥]\s*\d+\s*[/\/]?\s*[月月]",
        "feedback": "⛔ FACT ERROR: X APIのサブスクリプション料金（$100/月等）は2026年に廃止されました。Pay-Per-Useのみです。FLASH_CARDSを確認してください。",
        "name": "X_API_SUBSCRIPTION"
    },
    {
        "pattern": r"X\s*API\s*(Basic|Pro|Enterprise)\s*(tier|plan|プラン)",
        "feedback": "⛔ FACT ERROR: X APIのサブスクリプションプラン（Basic/Pro/Enterprise）は2026年に廃止されました。",
        "name": "X_API_TIER"
    },
    {
        "pattern": r"Anthropic\s*API\s*(課金|従量|を使用|を利用)",
        "feedback": "⛔ FACT ERROR: Anthropic API従量課金は使用禁止です。Claude Max $200/月の定額サブスク経由のみ使用可能です。",
        "name": "ANTHROPIC_API_BILLING"
    },
    {
        "pattern": r"@aisaintel",
        "feedback": "⛔ FACT ERROR: @aisaintelは廃止されたXアカウントです。現在は存在しません。",
        "name": "AISAINTEL_GHOST"
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# 「実装したつもり」検出: Webアクセス可能なファイル/設定を
# "実装完了" と報告する際に、検証証拠（curlの出力等）がない場合にブロック
# ──────────────────────────────────────────────────────────────────────────────
# 対象ファイル/エンドポイント（これらを「作った/設定した」と言う場合は証拠を要求）
WEB_RESOURCE_CLAIM_PATTERN = re.compile(
    r"(llms\.txt|robots\.txt|sitemap\.xml|\.well-known/|"
    r"Caddyfile|caddy.*設定|ghost.*設定|nginx.*設定|"
    r"自動投稿|cronを設定|cronを追加|cron.*設定|deploy|デプロイ)"
    r".{0,200}"
    r"(実装しました|作成しました|設定しました|完了しました|追加しました|"
    r"デプロイしました|有効にしました|できました|しておきました)",
    re.IGNORECASE | re.DOTALL
)

# 検証証拠として認められるパターン
VERIFICATION_EVIDENCE_PATTERN = re.compile(
    r"(curl\s|HTTP/[12]\.[01]|200 OK|404 Not Found|Content-Type:|"
    r"確認しました.{0,50}(curl|アクセス|レスポンス|HTTP)|"
    r"curl.*nowpattern|wget.*nowpattern|実際にアクセスして確認|"
    r"テスト結果|エラーなし|正常に動作|稼働確認)",
    re.IGNORECASE
)

# ──────────────────────────────────────────────────────────────────────────────
# 「治った治った」虚偽報告検出:
# バグ/問題/サービスが「直った/解決した」と報告するが証拠がない場合にブロック
# ──────────────────────────────────────────────────────────────────────────────
RUNTIME_CLAIM_PATTERN = re.compile(
    r"("
    r"直りました|治りました|"
    r"正常に戻りました|正常に動くようになりました|"
    r"(問題|エラー|バグ|不具合).{0,80}(直り|解決|修正)しました|"
    r"解決しました.{0,80}(問題|エラー|バグ|不具合)|"
    r"(再起動|リスタート|restart).{0,80}(しました|しておきました).{0,120}(正常|問題なく|動い|稼働)|"
    r"(動作|稼働)を確認しました"
    r")",
    re.IGNORECASE | re.DOTALL
)

# 実行確認証拠（VERIFICATION_EVIDENCE_PATTERNと組み合わせて判定）
RUNTIME_PROOF_PATTERN = re.compile(
    r"("
    r"Active: active|"
    r"FAIL: ?0[^\d]|FAIL:0[^\d]|"
    r"✅ \[自動検品 OK\]|"
    r"動作確認済み|稼働確認済み|実際に確認|"
    r"コマンドの出力|実行結果|以下の出力"
    r")",
    re.IGNORECASE
)

# ──────────────────────────────────────────────────────────────────────────────
# UI承認ゲート: CSS/HTML/ナビ変更後に「直りました」と自己申告することを禁止
# ユーザーがブラウザで確認して「OK」と言うまでブロック
# ──────────────────────────────────────────────────────────────────────────────
# UIの完了を自己申告するパターン（「ブラウザで確認してください」は許可）
UI_COMPLETION_CLAIM_PATTERN = re.compile(
    r"("
    r"直りました|治りました|修正(できました|しました|完了)|"
    r"(CSS|HTML|ナビ|nav|表示|レイアウト|スタイル|デザイン|カード).{0,80}"
    r"(直り|治り|修正し|解決し|正常に|正しく表示)(ました|できました)|"
    r"(直り|治り|修正し|解決し).{0,80}(CSS|HTML|ナビ|nav|表示|レイアウト)|"
    r"正常に表示されるようになりました|正しく表示されるようになりました|"
    r"表示されるようになりました"
    r")",
    re.IGNORECASE | re.DOTALL
)

# ユーザーへのブラウザ確認依頼（これがあればOK）
UI_VERIFICATION_REQUEST_PATTERN = re.compile(
    r"(ブラウザで確認|目視確認|実際に確認|確認してください"
    r"|ページを開いて|以下のURLで確認|アクセスして確認"
    r"|見てみてください|開いて確認)",
    re.IGNORECASE
)


def get_last_assistant_message(data: dict) -> str:
    """Stopフックのinputから最後のassistantメッセージを取得"""
    try:
        # Transcriptファイルパスから読み込む
        transcript_path = data.get("transcript_path", "")
        if transcript_path:
            with open(transcript_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # 最後のassistantメッセージを探す
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        content = entry.get("message", {}).get("content", "")
                        if isinstance(content, list):
                            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                            return " ".join(texts)
                        return str(content)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return ""

def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    last_message = get_last_assistant_message(data)
    if not last_message:
        sys.exit(0)

    # パターンマッチング
    found_errors = []
    for error in KNOWN_ERRORS:
        if re.search(error["pattern"], last_message, re.IGNORECASE):
            found_errors.append(error["feedback"])

    if found_errors:
        print("\n".join(found_errors))
        print("\n上記のFACT ERRORが検出されました。回答を修正してから再度応答してください。")
        sys.exit(2)  # exit code 2 = Claudeに再生成を強制

    # ── 「実装したつもり」チェック ────────────────────────────────────────────
    # Webアクセス可能なリソースの「実装完了」報告に検証証拠がない場合にブロック
    if WEB_RESOURCE_CLAIM_PATTERN.search(last_message):
        if not VERIFICATION_EVIDENCE_PATTERN.search(last_message):
            print(
                "⛔ 実装未検証エラー: Webアクセス可能なファイル・設定の「完了」を報告する前に、\n"
                "  必ずcurlで実際にアクセスして確認し、その出力を回答に含めてください。\n"
                "  例: curl -s https://nowpattern.com/llms.txt | head -5\n"
                "  VPSにSSH接続できない場合は「SSH接続できないため未検証、後ほど確認が必要」と明示してください。\n"
                "  ❌ 禁止: 検証せずに「〜しました」と報告すること"
            )
            sys.exit(2)

    # ── Playwright PASS の先読み（RUNTIME_CLAIM_PATTERN より先に実行）──────────
    # UIクレームに対して Playwright PASS が有効なら、RUNTIME_CLAIM_PATTERN を緩和する
    ui_verify_path = Path(__file__).parent / "state" / "ui_verification.json"
    playwright_passed = False
    if ui_verify_path.exists():
        try:
            uv_age = time.time() - ui_verify_path.stat().st_mtime
            if uv_age < 1800:  # 30分以内のみ有効
                uv = json.loads(ui_verify_path.read_text(encoding="utf-8"))
                playwright_passed = uv.get("all_pass", False)
        except Exception:
            pass

    # ── VRT Result 先読み（UI完了ゲートより先に実行）─────────────────────────
    vrt_result_path = Path(__file__).parent / "state" / "vrt_result.json"
    vrt_passed = False
    vrt_failed = False
    vrt_result_data = {}
    if vrt_result_path.exists():
        try:
            vrt_age = time.time() - vrt_result_path.stat().st_mtime
            if vrt_age < 7200:  # 2時間以内のみ有効
                vrt_result_data = json.loads(vrt_result_path.read_text(encoding="utf-8"))
                if vrt_result_data.get("verdict") == "PASS":
                    vrt_passed = True
                elif vrt_result_data.get("verdict") == "FAIL" and vrt_age < 3600:
                    vrt_failed = True  # 1時間以内のFAIL → UI完了ゲートで強制ブロック
        except Exception:
            pass

    # ── 「治った治った」虚偽報告チェック ─────────────────────────────────────
    # 「直りました」「解決しました」等の報告に実行証拠がない場合はブロック
    # ただし Playwright PASS / VRT PASS（UIテスト通過済み）は UI修正の証拠として認める
    if RUNTIME_CLAIM_PATTERN.search(last_message):
        _has_proof = (
            RUNTIME_PROOF_PATTERN.search(last_message)
            or VERIFICATION_EVIDENCE_PATTERN.search(last_message)
            or playwright_passed  # Playwright PASS は UI修正の証拠として有効
            or vrt_passed          # VRT PASS は更に強い証拠（URL+selector レベル）
        )
        # vrt_failed の場合: 後の UI完了ゲートで専用メッセージ（diff詳細付き）を出す
        if not _has_proof and not vrt_failed:
            print(
                "⛔ 動作未確認エラー: 「直りました」「解決しました」と報告する前に、\n"
                "  実際にコマンドを実行して結果を確認してください。\n"
                "  例: ssh root@163.44.124.123 'systemctl status neo-telegram'\n"
                "  例: ssh root@163.44.124.123 'python3 /opt/shared/scripts/site_health_check.py --quick'\n"
                "  例（UIの場合）: python3 scripts/playwright_verify.py → PLAYWRIGHT_PASS を確認\n"
                "  ❌ 禁止: 検証せずに「直りました」「問題が解決しました」と報告すること\n"
                "  ✅ 許可: コマンド実行結果（Active: active / FAIL:0 等）を本文に含める"
            )
            sys.exit(2)

    # ── VPS健全性チェック（vps-health-gate.py との連携） ─────────────────────
    # PostToolUse hookがVPS変更後にFAILを記録していたらブロック
    health_state_path = Path(__file__).parent / "state" / "vps_health.json"
    if health_state_path.exists():
        try:
            file_age = time.time() - health_state_path.stat().st_mtime
            if file_age < 3600:  # 1時間以内のチェック結果のみ有効
                health = json.loads(health_state_path.read_text(encoding="utf-8"))
                if not health.get("resolved", True) and health.get("fail", 0) > 0:
                    fail_count = health.get("fail", 0)
                    checked_at = health.get("checked_at", "不明")
                    print(
                        f"⛔ VPS健全性チェック FAIL ({fail_count}件) が未解決です。\n"
                        f"  検品時刻: {checked_at}\n"
                        f"  FAILを修正してから完了報告してください。\n"
                        f"  確認コマンド: ssh root@163.44.124.123 python3 /opt/shared/scripts/site_health_check.py --quick\n"
                        f"  FAIL 0件が確認されるまでこの回答は送信できません。"
                    )
                    sys.exit(2)  # Claudeに再生成を強制
        except Exception:
            pass  # state読み取り失敗は無視（壊れたstateでブロックしない）

    # ── UI承認ゲート（要件2 + 要件3）─────────────────────────────────────────
    # ui_task_pending=True かつ ui_approved=False のときに
    # 「直りました」等の自己申告をブロックし、ブラウザ確認依頼を要求する
    ui_state_path = Path(__file__).parent / "state" / "session.json"
    if ui_state_path.exists():
        try:
            ui_file_age = time.time() - ui_state_path.stat().st_mtime
            if ui_file_age < 7200:  # 2時間以内のみ有効
                ui_sess = json.loads(ui_state_path.read_text(encoding="utf-8"))
                if ui_sess.get("ui_task_pending") and not ui_sess.get("ui_approved"):
                    if UI_COMPLETION_CLAIM_PATTERN.search(last_message):
                        if not UI_VERIFICATION_REQUEST_PATTERN.search(last_message):
                            print(
                                "⛔ UI承認ゲート: UIの変更を自己申告する前に、ユーザーの目視確認が必要です。\n"
                                "  「直りました」ではなく、以下の形式で報告してください:\n"
                                "  ✅ 許可: 「コードを修正しました。ブラウザで [URL] を開いて確認してください」\n"
                                "  ❌ 禁止: 「直りました」「正常に表示されるようになりました」\n"
                                "  → ユーザーが「OK 確認した」と言うまで完了報告はできません。"
                            )
                            sys.exit(2)
        except Exception:
            pass  # state読み取り失敗はサイレント無視

    # ── VRT / Playwright UI検証ゲート ───────────────────────────────────────────
    # CSS/レイアウト/ナビ等のUI修正完了を主張する際の優先順位:
    #   1. VRT FAIL (1h以内) → 強制ブロック（外部崩壊あり）
    #   2. VRT PASS (2h以内) → 許可（最も強い証拠: URL+selector レベル）
    #   3. Playwright PASS (30m以内) → 許可（ヘルスチェック通過）
    #   4. 「ブラウザで確認してください」 → 許可（ユーザー確認依頼）
    #   5. それ以外 → ブロック
    if UI_COMPLETION_CLAIM_PATTERN.search(last_message):
        # 1. VRT FAIL → 即ブロック
        if vrt_failed:
            outside_pct = vrt_result_data.get("diff_ratio_outside", 0) * 100
            url       = vrt_result_data.get("url", "不明")
            selector  = vrt_result_data.get("selector", "不明")
            diff_path = vrt_result_data.get("diff_path", "なし")
            compared  = vrt_result_data.get("compared_at", "不明")
            print(
                f"⛔ VRT FAIL: 外部レイアウト崩壊が検出されました。\n"
                f"  対象URL:      {url}\n"
                f"  対象セレクタ: {selector}\n"
                f"  外部変化:     {outside_pct:.4f}% (許容: 0.10%)\n"
                f"  比較時刻:     {compared}\n"
                f"  差分画像:     {diff_path}\n"
                f"→ まず崩壊箇所を修正してから compare を実行してください:\n"
                f"    python scripts/ui_vrt_runner.py compare\n"
                f"→ VRT_PASS になってから完了報告してください。"
            )
            sys.exit(2)
        # 2〜4. VRT PASS / Playwright PASS / ブラウザ確認依頼 → OK
        if not (vrt_passed or playwright_passed or UI_VERIFICATION_REQUEST_PATTERN.search(last_message)):
            print(
                "⛔ UI検証なし: UIの修正を完了報告する前に、以下のいずれかを実行してください:\n"
                "  [推奨] VRT比較 (URL+selector レベルの精密検証):\n"
                "    python scripts/ui_vrt_runner.py compare\n"
                "    → VRT_PASS が出れば完了報告OK\n"
                "  [次点] Playwright 健全性チェック:\n"
                "    python scripts/playwright_verify.py\n"
                "    → PLAYWRIGHT_PASS が出れば完了報告OK\n"
                "  [代替] ユーザーへのブラウザ確認依頼:\n"
                "    「ブラウザで [URL] を開いて確認してください」\n"
                "  ❌ 禁止: 検証なしで「直りました」と報告すること"
            )
            sys.exit(2)

    # ── 訂正後の KNOWN_MISTAKES 記録チェック（feedback-trap.py との連携） ──────
    # feedback-trap.py が correction_needed=True を設定した後、
    # KNOWN_MISTAKES.md が更新されていなければブロック
    session_state_path = Path(__file__).parent / "state" / "session.json"
    if session_state_path.exists():
        try:
            sess = json.loads(session_state_path.read_text(encoding="utf-8"))
            if sess.get("correction_needed", False):
                baseline_mtime = sess.get("mistakes_mtime_at_correction", 0)
                known_mistakes = Path(__file__).parent.parent.parent / "docs" / "KNOWN_MISTAKES.md"
                current_mtime = known_mistakes.stat().st_mtime if known_mistakes.exists() else 0

                if current_mtime <= baseline_mtime:
                    correction_preview = sess.get("correction_preview", "（詳細不明）")
                    print(
                        "⛔ 記録未完了: ユーザーから訂正を受けましたが docs/KNOWN_MISTAKES.md がまだ更新されていません。\n"
                        f"  訂正内容: {correction_preview[:80]}\n"
                        "  → 解決した問題を KNOWN_MISTAKES.md に記録してから回答を終了してください。\n"
                        "  フォーマット:\n"
                        "    ### YYYY-MM-DD: タイトル\n"
                        "    - **症状**: / **根本原因**: / **正しい解決策**: / **教訓**:\n"
                        "  ❌ 禁止: 記録せずに「完了です」と報告すること"
                    )
                    sys.exit(2)
                else:
                    # KNOWN_MISTAKES.md が更新された → フラグをクリア
                    sess["correction_needed"] = False
                    session_state_path.write_text(json.dumps(sess, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # state読み取り失敗はサイレント無視

    sys.exit(0)

if __name__ == "__main__":
    main()
