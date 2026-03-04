#!/usr/bin/env python3
"""
MISTAKE AUTO-GUARD — ECC Pipeline の欠落リンク
================================================
error-tracker.py から呼び出される。

役割:
  エラーテキスト → ミスタイプ分類 → GUARD_PATTERN JSON 自動生成

これが KNOWN_MISTAKES.md に書かれると:
  auto-codifier.py が mistake_patterns.json に登録
    → fact-checker.py が永久ブロック

設計原則:
  "LLMの宣言は信用しない。コードが強制する。"
  各ミスは1回発生したら2度と起きない仕組みに変換される。

世界標準の根拠:
  Google SRE: インシデント → 自動テスト化 (Error Budget + Postmortem)
  Reflexion (Stanford 2023): 失敗記憶 → 次回ブロック
  Netflix Chaos Engineering: 故障 → 防御コード追加
"""

import re
import json
from typing import Optional

# =========================================================================
# ミスタイプ定義ライブラリ (12種)
#
# 各エントリ:
#   id           : ミスの識別子
#   trigger      : エラーテキストにマッチする正規表現（これが出たらこのタイプ）
#   guard_pattern: GUARD_PATTERN フィールドに書く JSON
#     pattern  : Claude が書こうとするコードの危険なパターン（正規表現）
#     feedback : ブロック時に表示するメッセージ（何をすべきか）
#     name     : パターンの一意ID（重複チェックに使用）
# =========================================================================

MISTAKE_TYPES = [
    {
        "id": "LARGE_PAYLOAD_READ",
        "trigger": r"unterminated string|JSONDecodeError|json\.loads.*fail|json parse error",
        "guard_pattern": {
            "pattern": r"rfile\.read\s*\((?!.*min\()",
            "feedback": "大きなHTTPボディをmin()なしで全バイト読み込もうとしています。"
                        "MAX_READ=65536を設定してください: "
                        "read_size = min(content_length, MAX_READ)",
            "name": "LARGE_PAYLOAD_READ_UNGUARDED"
        }
    },
    {
        "id": "BROKEN_PIPE_RESPONSE",
        "trigger": r"BrokenPipeError|Errno 32|broken pipe",
        "guard_pattern": {
            "pattern": r"self\.wfile\.write|self\.send_response\b",
            "feedback": "HTTPレスポンス送信はBrokenPipeErrorをキャッチしてください。"
                        "try: self.send_response(200); ... except BrokenPipeError: pass",
            "name": "UNGUARDED_HTTP_RESPONSE_SEND"
        }
    },
    {
        "id": "FCNTL_NO_PLATFORM_CHECK",
        "trigger": r"fcntl.*module|has no attribute.*flock|ModuleNotFoundError.*fcntl",
        "guard_pattern": {
            "pattern": r"^import fcntl$",
            "feedback": "fcntlはLinux専用です。"
                        "使用前に import sys; if sys.platform == 'win32': ... のガードを追加してください",
            "name": "FCNTL_LINUX_ONLY"
        }
    },
    {
        "id": "GHOST_SOURCE_HTML_DEPRECATED",
        "trigger": r"\?source=html|source=html.*ghost|ghost.*source=html",
        "guard_pattern": {
            "pattern": r"\?source=html",
            "feedback": "Ghost 5.xでは?source=htmlは廃止済みです。"
                        "lexicalフォーマット（/ghost/api/admin/pages/{id}/?formats=lexical）を直接操作してください",
            "name": "GHOST_DEPRECATED_SOURCE_HTML"
        }
    },
    {
        "id": "PYTHON3_WINDOWS_ALIAS",
        "trigger": r"exit.*49|python3.*not found|python3.*command not found|WindowsError.*python3",
        "guard_pattern": {
            "pattern": r"\bpython3\b(?! /c/Program)",
            "feedback": "Windows環境ではpython3はダミーエイリアスです（exit 49）。"
                        "\"/c/Program Files/Python312/python.exe\" を使ってください",
            "name": "PYTHON3_WINDOWS_DUMMY"
        }
    },
    {
        "id": "GHOST_SSL_NO_VERIFY",
        "trigger": r"SSLCertVerificationError|CERTIFICATE_VERIFY_FAILED|ssl.*certificate",
        "guard_pattern": {
            "pattern": r"requests\.(get|post|put|patch|delete)\([^)]*https://nowpattern(?!.*verify=False)",
            "feedback": "Ghost CMS APIへのHTTPSリクエストにはverify=Falseが必要です。"
                        "urllib3.disable_warnings()も追加してください",
            "name": "GHOST_SSL_VERIFY_REQUIRED"
        }
    },
    {
        "id": "GHOST_API_403_NO_HOSTS",
        "trigger": r"403.*ghost|ghost.*403|forbidden.*ghost admin",
        "guard_pattern": {
            "pattern": r"https://nowpattern\.com.*ghost/api",
            "feedback": "Ghost Admin APIへのアクセスには /etc/hosts に "
                        "127.0.0.1 nowpattern.com の設定が必要です。"
                        "SSHでVPSにログインして確認してください",
            "name": "GHOST_ADMIN_API_HOSTS_REQUIRED"
        }
    },
    {
        "id": "OPENROUTER_ZAI_WRONG_PREFIX",
        "trigger": r"api.*undefined|openrouter.*glm|zhipuai.*openrouter",
        "guard_pattern": {
            "pattern": r"openrouter.*glm|GLM.*openrouter",
            "feedback": "GLM-4/GLM-5はOpenRouterではなくZhipuAI直接API（zai/プレフィックス）を使ってください。"
                        "ZAI_API_KEY環境変数を確認してください",
            "name": "GLM_VIA_OPENROUTER_WRONG"
        }
    },
    {
        "id": "ENV_EXPANSION_CRON",
        "trigger": r"source \.env.*cron|cron.*source.*env|env.*not expanded",
        "guard_pattern": {
            "pattern": r"source\s+['\"]?/opt/.*\.env['\"]?\s*&&",
            "feedback": "cronではsource .envが機能しません。"
                        "cronスクリプト内でAPIキーをインラインで指定するか、"
                        "/opt/cron-env.shをsourceしてください",
            "name": "CRON_ENV_SOURCE_BROKEN"
        }
    },
    {
        "id": "NOTE_COOKIE_EXPIRED",
        "trigger": r"note.*403|note.*cookie|note.*authentication|403.*note\.mu",
        "guard_pattern": {
            "pattern": r"note\.mu.*cookie|note.*requests\.post.*login",
            "feedback": "note.muのCookieが期限切れです。"
                        "Seleniumスクリプトで再ログイン → .note-cookies.jsonを更新してください",
            "name": "NOTE_COOKIE_EXPIRED_RELOGIN"
        }
    },
    {
        "id": "SPECULATION_IN_OUTPUT",
        "trigger": r"はずです|だと思います|おそらく〜|ようです.*確認",
        "guard_pattern": {
            "pattern": r"はずです|だと思います|のはずで",
            "feedback": "未確認情報の報告は禁止です。"
                        "「はずです」「だと思います」を使う前に、SSHで実際に確認してください",
            "name": "SPECULATION_UNVERIFIED_CLAIM"
        }
    },
    {
        "id": "DOCKER_NPM_INSTALL",
        "trigger": r"npm install.*docker|docker.*npm install.*\(not ci\)",
        "guard_pattern": {
            "pattern": r"\bnpm install\b(?!.*ci)",
            "feedback": "Dockerコンテナ内ではnpm installではなくnpm ciを使ってください（再現性のため）",
            "name": "DOCKER_NPM_INSTALL_NOT_CI"
        }
    },
]


def classify_mistake(tool_name: str, error_text: str) -> Optional[dict]:
    """
    エラーテキストからミスタイプを特定し、GUARD_PATTERN JSONを返す。
    マッチしない場合はNoneを返す。

    Args:
        tool_name: 失敗したツール名 (例: "Bash", "Edit", "Write")
        error_text: エラーメッセージ（最大500文字）

    Returns:
        GUARD_PATTERN dict (pattern, feedback, name) または None
    """
    combined = f"{tool_name} {error_text}".lower()

    for mistake_type in MISTAKE_TYPES:
        if re.search(mistake_type["trigger"], combined, re.IGNORECASE):
            return {
                "mistake_id": mistake_type["id"],
                "guard_pattern": mistake_type["guard_pattern"]
            }

    return None


def generate_guard_pattern_line(guard_pattern: dict) -> str:
    """
    KNOWN_MISTAKES.md に追記する GUARD_PATTERN フィールド行を生成する。

    Returns:
        "- **GUARD_PATTERN**: `{...}`" 形式の文字列
    """
    gp = guard_pattern["guard_pattern"]
    json_str = json.dumps(gp, ensure_ascii=False)
    return f"- **GUARD_PATTERN**: `{json_str}`"


if __name__ == "__main__":
    # テストモード: python3 mistake-auto-guard.py "BrokenPipeError" "Bash"
    import sys
    error = sys.argv[1] if len(sys.argv) > 1 else "BrokenPipeError: Errno 32"
    tool = sys.argv[2] if len(sys.argv) > 2 else "Bash"
    result = classify_mistake(tool, error)
    if result:
        print(f"[MATCH] Mistake type: {result['mistake_id']}")
        print(generate_guard_pattern_line(result))
    else:
        print("[NO MATCH] パターンに一致するミスタイプがありません")
