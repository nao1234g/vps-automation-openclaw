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

# トランスクリプト解析: 検証が必要なファイル拡張子（スクリプト・コード + ビジュアル系）
# .css/.hbs/.html はスクリーンショット検証が必要（語彙チェックでは捕捉不可能な視覚バグ対策）
_TC_REQUIRES_VERIFICATION = re.compile(r"\.(py|sh|js|ts|rb|go|rs|php|css|hbs|html)$", re.IGNORECASE)

# トランスクリプト解析: 検証スキップ対象（ドキュメント・設定・メモリ系）
_TC_SKIP_VERIFICATION = re.compile(
    r"(CLAUDE\.md|KNOWN_MISTAKES|AGENT_WISDOM|"
    r"settings.*\.json|config.*\.json|package.*\.json|tsconfig.*\.json|"
    r"[/\\]docs[/\\]|[/\\]memory[/\\]|\.claude[/\\]rules[/\\]|"
    r"hooks[/\\]state[/\\]|"
    r"\.md$|\.txt$|\.yml$|\.yaml$|\.json$|\.lock$|\.toml$)",
    re.IGNORECASE
)

# トランスクリプト解析: 検証Bashコマンドと認定するパターン
_TC_VERIFICATION_COMMANDS = re.compile(
    r"(^ssh\s|"
    r"python3?\s.*(verify|check|test|health|validate|site_health)|"
    r"pytest|unittest|"
    r"bash\s.*(test|verify)|"
    r"/opt/shared/scripts/|"
    r"site_health_check|prediction_page_builder|"
    r"ui_vrt|ui_vrt_runner|playwright_verify|site_visual_check|"  # VRT/スクリーンショット検証
    r"systemctl\s+(status|is-active)|"
    r"docker\s+(ps|inspect|logs)|"
    r"curl\s.*(nowpattern|localhost|127\.0\.0\.1)|"
    r"python3\s+-c\s+|"
    r"python3?\s+[\"'].*(import|ast)|"
    r"python3?\s+.*/\.claude/hooks/)",
    re.IGNORECASE
)

# MCPスクリーンショットツール名パターン（Playwright MCP等）
# transcript内のtool_useブロックのnameフィールドにマッチ
_TC_MCP_SCREENSHOT = re.compile(
    r"(browser_take_screenshot|browser_screenshot|"
    r"mcp__playwright__|screenshot)",
    re.IGNORECASE
)


def _tc_is_verification_required(file_path: str) -> bool:
    """このファイルは変更後に検証Bashが必要か判定する"""
    if _TC_SKIP_VERIFICATION.search(file_path):
        return False
    return bool(_TC_REQUIRES_VERIFICATION.search(file_path))


def get_unverified_edits_from_transcript(transcript_path: str) -> list:
    """
    トランスクリプトJSONLを解析して、最後の検証Bash以降の未検証Edit/Writeを返す。
    語彙に完全非依存 — ツール呼び出し系列（何を言ったか ではなく 何をしたか）で判定。

    設計原則 (SWE-bench / Devin AI / GitHub CI 共通):
      最後の「検証Bash」を基準点とし、その後に行われたEdit/Writeを「未検証」と判定。
      「変更しました」等の言葉は一切参照しない。
    """
    if not transcript_path:
        return []
    try:
        p = Path(transcript_path)
        if not p.exists():
            return []
        tool_sequence = []
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "assistant":
                    content = entry.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if block.get("type") == "tool_use":
                                tool_sequence.append((
                                    i,  # 行番号（時系列順）
                                    block.get("name", ""),
                                    block.get("input", {})
                                ))
        # 逆順で最後の検証Bash OR MCPスクリーンショットを探す
        last_verified_seq_idx = -1
        for seq_idx in range(len(tool_sequence) - 1, -1, -1):
            _, tname, tinput = tool_sequence[seq_idx]
            if tname == "Bash":
                cmd = tinput.get("command", "")
                if _TC_VERIFICATION_COMMANDS.search(cmd):
                    last_verified_seq_idx = seq_idx
                    break
            elif _TC_MCP_SCREENSHOT.search(tname):
                # Playwright MCP等のスクリーンショットツール呼び出し = 視覚確認済み
                last_verified_seq_idx = seq_idx
                break
        # 検証Bash以降のEdit/Writeを収集（重複なし）
        unverified = []
        seen: set = set()
        for seq_idx in range(last_verified_seq_idx + 1, len(tool_sequence)):
            _, tname, tinput = tool_sequence[seq_idx]
            if tname in ("Edit", "Write"):
                fp = tinput.get("file_path", "")
                if fp and fp not in seen and _tc_is_verification_required(fp):
                    unverified.append(fp)
                    seen.add(fp)
        return unverified
    except Exception:
        return []

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
# 「件数思い込み」検出: データソース件数 ≠ 実際のシステム出力件数
# 「N件確認済み」「全件適用」等を主張する場合、観測コマンドの出力を必須とする
# 根本原因: prediction_db.json=7件 → ページ=19件 のような思い込みを物理ブロック
# ──────────────────────────────────────────────────────────────────────────────
COUNT_CLAIM_PATTERN = re.compile(
    r"(全\d+件|"
    r"\d+件(全て|すべて|確認済み|に適用|を確認|が確認|正常|が正しく)|"
    r"全件.{0,5}(確認|適用|修正|パッチ|処理|対応)|"
    r"全(カード|予測|記事|ページ)(に|が|を|は|の).{0,20}(確認|適用|修正|正常))",
    re.IGNORECASE
)

# 観測証拠として認められるパターン（実際のシステム出力）
COUNT_EVIDENCE_PATTERN = re.compile(
    r"(Total rows\s*[：:]\s*\d+|"
    r"From prediction_db\s*[：:]\s*\d+|"
    r"From Ghost HTML\s*[：:]\s*\d+|"
    r"wc\s*-l|"
    r"合計\s*\d+件.{0,10}(確認|取得|出力)|"
    r"実際の(件数|カード数|合計|行数)|"
    r"ビルド(出力|結果)|"
    r"コマンド(出力|実行結果)|"
    r"```[^`]*Total rows[^`]*```)",
    re.IGNORECASE | re.DOTALL
)

# ──────────────────────────────────────────────────────────────────────────────
# 「作業完了詐称」汎用検出:
#   「パッチ適用しました」「全部直しました」「実装完了です」
#   → WEB_RESOURCE/RUNTIME/COUNT/UIの既存チェックでカバーされない3パターン
# 原則: 「Xしました」はコマンド出力・スクリプト出力・ユーザー委任で証拠必須
# ──────────────────────────────────────────────────────────────────────────────
WORK_COMPLETE_CLAIM_PATTERN = re.compile(
    r"("
    # パッチ適用系（WEB_RESOURCEがカバーしない汎用パッチ）
    r"パッチ.{0,30}(適用|当て)(しました|済み|できました)|"
    # 全部系（transitive: 自分で直した）── 「直りました」(intransitive)はRUNTIMEが担当
    r"全(部|て).{0,60}(直し|修正し|適用し|対応し)(ました|完了)|"
    # 実装完了（WEB_RESOURCEがカバーしない非Web文脈）
    r"実装(完了です|完了しました|しました|できました)"
    r")",
    re.IGNORECASE
)

# 作業証拠として認められるパターン
WORK_COMPLETE_PROOF_PATTERN = re.compile(
    r"("
    # パッチスクリプトの成功出力
    r"PATCH [A-F] OK|"
    # ✅ チェックマーク付き成功（既存スクリプト出力）
    r"✅ .{0,80}(OK|PASS|成功|installed|完了)|"
    # コードブロック内に50文字以上の内容（SSH/コマンド実行結果）
    r"```[\s\S]{50,}```|"
    # シェルの正常終了・systemctlの成功
    r"exit\s+0|Active:\s*active|"
    # FAILなし（ヘルスチェック通過）
    r"FAIL:\s*0[^\d]|FAIL:0[^\d]|"
    # ユーザー委任（確認依頼は許容）
    r"確認してください|ブラウザで確認|実際に確認|以下の出力|以下で確認"
    r")",
    re.IGNORECASE | re.DOTALL
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

    # ── 「件数思い込み」チェック ─────────────────────────────────────────────
    # 「全件確認済み」「N件に適用」等の件数主張に、観測コマンド出力がない場合にブロック
    if COUNT_CLAIM_PATTERN.search(last_message):
        if not COUNT_EVIDENCE_PATTERN.search(last_message):
            print(
                "⛔ 件数未確認エラー: 件数・カード数・合計数を主張する前に、\n"
                "  実際のシステムから直接観測した出力を回答に含めてください。\n"
                "\n"
                "  ❌ 禁止（データソース確認 = 思い込みの元）:\n"
                "    python3 -c \"len(data['predictions'])\"  # JSONの件数はページ表示件数ではない\n"
                "\n"
                "  ✅ 必須（実際のシステム出力を確認）:\n"
                "    予測ページ: python3 /opt/shared/scripts/prediction_page_builder.py 2>&1 | grep 'Total rows'\n"
                "    記事件数:   curl Ghost Admin API | jq '.meta.pagination.total'\n"
                "    サービス:   systemctl list-units --state=running | wc -l\n"
                "\n"
                "  原則: 数字を主張するなら、その数字を生成したコマンド出力を必ず貼ること。\n"
                "        「データソースを見た」は証拠にならない。「システムに聞いた」が証拠。"
            )
            sys.exit(2)

    # ── 「作業完了詐称」汎用チェック ─────────────────────────────────────────
    # 「パッチ適用しました」「全部直しました」「実装完了です」等の
    # 作業完了主張に証拠（コマンド出力/スクリプト出力）がない場合にブロック
    if WORK_COMPLETE_CLAIM_PATTERN.search(last_message):
        if not WORK_COMPLETE_PROOF_PATTERN.search(last_message):
            # 既存チェックで既にカバーされているケースは二重ブロックを避ける
            already_covered = (
                WEB_RESOURCE_CLAIM_PATTERN.search(last_message) or
                RUNTIME_CLAIM_PATTERN.search(last_message)
            )
            if not already_covered:
                print(
                    "⛔ 作業完了未検証エラー: 「パッチ適用」「全部修正」「実装完了」を報告する前に、\n"
                    "  実際に実行したコマンドの出力を回答に含めてください。\n"
                    "\n"
                    "  ❌ 禁止（証拠なし完了報告）:\n"
                    "    「パッチを適用しました」\n"
                    "    「全部直しました」\n"
                    "    「実装完了です」\n"
                    "\n"
                    "  ✅ 必須（コマンド出力を貼る）:\n"
                    "    パッチ: ssh root@163.44.124.123 'python3 patch.py' → PATCH X OK を確認\n"
                    "    修正:   ssh root@163.44.124.123 'python3 verify.py' → エラー0件を確認\n"
                    "    実装:   実行結果のコードブロック（```出力内容```）を含める\n"
                    "\n"
                    "  原則: 「Xしました」=「Xの証拠を提示した」と同義にする。\n"
                    "        証拠なしの完了報告は虚偽報告として扱われる。"
                )
                sys.exit(2)

    # ── 「変更後未検証」状態ベースチェック ────────────────────────────────────────
    # change-tracker.py が Edit/Write 時に記録した pending_verification.json を読む。
    # Bash 検証コマンドが実行されていない場合、語彙に関係なくブロックする。
    #
    # これが「テキストベース」チェックと根本的に異なる点:
    #   テキスト: 「変更しました」という言葉を探す → 語彙変更で突破可能
    #   状態ベース: 「実際に Edit/Write した」という事実を追跡 → 語彙に依存しない
    #
    # カバーする語彙バイパスの例（これらは既存パターンでは検知できない）:
    #   「変更しました」「更新しました」「対応しました」「反映しました」
    #   「修正を加えました」「調整しました」「コードを書きました」
    #
    # 組み合わせチェック（誤検知を防ぐため）:
    #   条件1: 変更後に検証Bashが実行されていない（状態）
    #   条件2: 回答が完了を示す言葉を含む（テキスト、広め）
    #   → 両方満たした場合のみブロック

    # ── 世界最高基準 語彙網羅パターン v2 ─────────────────────────────────────────
    # 根拠: CI/CD (GitHub Actions) + Devin AI + SWE-bench の共通原則
    #   「語彙に依存するな。しかし語彙ベースチェックが必要なら網羅しろ」
    #
    # v1 からの改善点（語彙ギャップを根本解決）:
    #   v1 で未検知だったケース: 「修正しました」（単体）「書きました」「直しました」
    #   「完了です」「終わりました」「やりました」「削除しました」「置き換えました」
    #   「済みです」「編集しました」「解消しました」等
    #   → v2 は日本語の全完了形動詞を網羅する。「した/済み/完了/しています」は全て捕捉。
    BROAD_COMPLETION_PATTERN = re.compile(
        r"("
        # ─ 変更・書き換え系（バイパス常習犯） ─
        r"変更しました|変更できました|変更済み|"
        r"更新しました|更新できました|更新済み|"
        r"修正しました|修正できました|修正済み|修正を(加え|行い|施し)(ました)?|"
        r"書きました|書き換えました|書き直しました|書き込みました|"
        r"直しました|直せました|直してあります|直しておきました|"
        r"対応しました|対応できました|対応済み|対処しました|"
        r"調整しました|調整済み|反映しました|反映済み|"
        r"編集しました|編集済み|"
        # ─ 完了・終了系 ─
        r"完了しました|完了できました|完了です|完了済み|完了しています|"
        r"終わりました|終了しました|終えました|終わっています|"
        r"済みました|済みです|済んでいます|"
        r"以上で(完了|終了|対応|修正)|"
        r"これで(完了|できました|修正完了)|"
        # ─ 実施・実行系 ─
        r"実装しました|実装できました|実装済み|"
        r"設定しました|設定できました|設定済み|"
        r"追加しました|追加できました|追加済み|"
        r"削除しました|削除できました|削除済み|"
        r"置き換えました|置き換え済み|"
        r"整理しました|整えました|"
        r"保存しました|適用しました|組み込みました|"
        r"やりました|やっておきました|しておきました|してあります|"
        r"解消しました|解決できました|"
        # ─ 対象+動詞 パターン ─
        r"(コード|スクリプト|ファイル|設定|フック|パターン|関数|クラス).{0,30}"
        r"(変更|修正|更新|追記|削除|置き換え|追加|整理|保存|適用)(しました|できました|完了|済み)"
        r")",
        re.IGNORECASE
    )

    # 証拠として認められるパターン（実行証拠 + ユーザー確認依頼）
    # ポリシー: 「Bashで確認してください」型の返答は許容する（ユーザーへの委譲）
    ANY_PROOF_PATTERN = re.compile(
        r"(```[\s\S]{40,}```|"
        r"PATCH [A-F] OK|"
        r"✅ .{0,80}(OK|PASS|成功)|"
        r"Active:\s*active|FAIL:\s*0[^\d]|FAIL:0[^\d]|"
        r"exit\s+0|HTTP/[12]|200 OK|"
        r"確認してください|ブラウザで確認|実際に確認|以下の出力|以下で確認|"
        r"見てみてください|開いて確認|URLで確認|"
        r"実行してください|試してみてください|テストしてください|"
        r"以下のコマンドを実行|確認をお願いします)",
        re.IGNORECASE | re.DOTALL
    )

    # ── トランスクリプト解析ベース チェック（語彙完全非依存・最高精度）────────────
    # 設計: 「何を言ったか」ではなく「ツール呼び出し系列」で判定（SWE-bench方式）
    #   1. transcript_path JSONLを全行パース
    #   2. assistantメッセージ内のtool_useブロックを時系列で抽出
    #   3. 最後の「検証Bash」（ssh/pytest/site_health_check等）を基準点とする
    #   4. その後のEdit/Writeを「未検証ファイル」とみなす
    #   5. 未検証ファイルがあり、かつ ANY_PROOF_PATTERN がない → exit(2)
    #
    # 「無言バイパス」も完全ブロック:
    #   ANY_PROOF_PATTERN を含まない限り、何も言わなくてもブロック
    #   （vocabulary-based checkと根本的に異なる）
    transcript_unverified = get_unverified_edits_from_transcript(
        data.get("transcript_path", "")
    )
    if transcript_unverified:
        if not ANY_PROOF_PATTERN.search(last_message):
            files = [Path(f).name for f in transcript_unverified[:3]]
            file_list = ", ".join(files)
            # CSS/HTML/テンプレート変更の場合はスクリーンショット検証を優先案内
            is_visual_change = any(
                str(f).lower().endswith((".css", ".hbs", ".html"))
                for f in transcript_unverified
            )
            if is_visual_change:
                visual_hint = (
                    f"  【ビジュアル変更 — スクリーンショット検証が必要】\n"
                    f"  CSSやテンプレートの変更は、コード実行では検証できません。\n"
                    f"  必ず目で見て確認してください。\n"
                    f"\n"
                    f"  → 以下のいずれかでスクリーンショットを取得:\n"
                    f"    全ページ確認: python3 scripts/site_visual_check.py\n"
                    f"    クイック確認: python3 scripts/site_visual_check.py --quick\n"
                    f"    Playwright: browser_take_screenshot (MCPツール)\n"
                    f"    または: 「以下のコマンドを実行してください: [コマンド]」と伝える\n"
                )
            else:
                visual_hint = (
                    f"  → 以下のいずれかを実行してください:\n"
                    f"    構文確認: python3 -c \"import ast; ast.parse(open('{files[0]}').read()); print('OK')\"\n"
                    f"    VPS検証:  ssh root@163.44.124.123 'python3 /opt/...'\n"
                    f"    または:   「以下のコマンドを実行してください: [コマンド]」と伝える\n"
                )
            print(
                f"⛔ 変更後未検証（トランスクリプト解析・語彙完全非依存）:\n"
                f"  変更ファイル: {file_list}\n"
                f"  最後の検証コマンド以降、動作確認が実行されていません。\n"
                f"\n"
                f"  【語彙に依存しない純粋状態ベース検証】\n"
                f"  「変更しました」「修正しました」等の言葉は関係ありません。\n"
                f"  何も言わなくても、検証なしでは完了できません。\n"
                f"\n"
                + visual_hint +
                f"\n"
                f"  ✅ 検証コマンド実行後は自動的にロックが解除されます。"
            )
            sys.exit(2)

    pending_verif_path = Path(__file__).parent / "state" / "pending_verification.json"
    if pending_verif_path.exists():
        try:
            p_file_age = time.time() - pending_verif_path.stat().st_mtime
            if p_file_age < 7200:  # 2時間以内の状態のみ有効（10分→2時間: ロングセッション対応）
                p_state = json.loads(pending_verif_path.read_text(encoding="utf-8"))
                pending_edits = p_state.get("pending_edits", [])
                verified_at = p_state.get("verified_at", 0)
                now_ts = time.time()

                # verified_at より新しい、かつ1時間以内の未検証変更（10分→1時間）
                recent_unverified = [
                    e for e in pending_edits
                    if e.get("at", 0) > verified_at and (now_ts - e.get("at", 0)) < 3600
                ]

                if recent_unverified and BROAD_COMPLETION_PATTERN.search(last_message):
                    if not ANY_PROOF_PATTERN.search(last_message):
                        files = [Path(e["file"]).name for e in recent_unverified[:3]]
                        file_list = ", ".join(files)
                        # state をクリア（無限ループ防止）
                        p_state["pending_edits"] = [
                            e for e in pending_edits if e not in recent_unverified
                        ]
                        pending_verif_path.write_text(
                            json.dumps(p_state, ensure_ascii=False, indent=2),
                            encoding="utf-8"
                        )
                        print(
                            f"⛔ 変更後未検証（状態ベース）: 以下のファイルを変更しましたが、\n"
                            f"  動作確認コマンドが実行されていません:\n"
                            f"  変更ファイル: {file_list}\n"
                            f"\n"
                            f"  これは語彙バイパス防止の状態ベース検証です。\n"
                            f"  「変更しました」「更新しました」「対応しました」等の言葉に\n"
                            f"  関係なく、Bash検証なしでは完了報告できません。\n"
                            f"\n"
                            f"  → 以下のいずれかを実行してから報告してください:\n"
                            f"    Pythonフック構文確認: python3 -c \"import ast; "
                            f"ast.parse(open('{files[0]}').read()); print('OK')\"\n"
                            f"    VPS検証:              ssh root@163.44.124.123 "
                            f"'python3 /opt/...スクリプトのパス'\n"
                            f"    ヘルスチェック:       ssh root@163.44.124.123 "
                            f"'python3 /opt/shared/scripts/site_health_check.py --quick'\n"
                            f"\n"
                            f"  ✅ 検証コマンド実行後は自動的にロックが解除されます。"
                        )
                        sys.exit(2)
        except Exception:
            pass  # 状態読み取り失敗はサイレント無視

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
