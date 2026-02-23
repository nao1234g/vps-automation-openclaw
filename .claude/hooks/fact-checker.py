#!/usr/bin/env python3
"""
FACT CHECKER — Stop Hook
=======================
Claudeが回答を生成した後、既知の誤りパターンを検出して訂正を促す。
exit code 2 = Claude Codeが強制的に再生成（feedback付き）
"""
import json
import sys
import re

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

    sys.exit(0)

if __name__ == "__main__":
    main()
