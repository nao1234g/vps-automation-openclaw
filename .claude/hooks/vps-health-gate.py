#!/usr/bin/env python3
"""
vps-health-gate.py — PostToolUse Hook for Bash
===============================================
VPSを変更するBashコマンド（SCP/SSH書き込み）の後に
自動でsite_health_check.pyを実行する。

FAIL > 0 の場合:
  - Claudeのコンテキストに警告を注入（PostToolUse output）
  - state/vps_health.json に未解決FAILを記録
  - Stop hookのfact-checker.pyがexit(2)でブロック

解決された場合 (FAIL=0):
  - state/vps_health.json に resolved=True を記録
  - Stopフックはブロックしない
"""
import json
import sys
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
HEALTH_STATE = STATE_DIR / "vps_health.json"
VPS_IP = "163.44.124.123"

STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_input():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def is_vps_modifying(command: str) -> bool:
    """VPSにファイルを書き込む/スクリプトを実行するコマンドを検出"""
    # SCP to VPS (local → remote direction):  scp <file> root@IP:<path>
    if re.search(r'scp\s+\S.*root@' + re.escape(VPS_IP) + r':', command):
        return True

    # SSH to VPS with file-writing or script-running operations
    if f"root@{VPS_IP}" in command:
        modifying_patterns = [
            r'python3\s+/opt',           # スクリプト実行
            r'cat\s*>',                   # ファイル書き込み
            r'tee\s+',                    # ファイル書き込み
            r'\bcp\s+',                   # ファイルコピー
            r'\bmv\s+',                   # ファイル移動
            r'systemctl\s+(restart|start|stop|reload)',  # サービス操作
            r'docker\s+(restart|start|stop|exec)',       # Docker操作
            r'>\s*/opt',                  # /optへのリダイレクト
            r'>>\s*/opt',                 # /optへの追記
            r'bash\s+/opt',               # bashスクリプト実行
            r'chmod\s+',                  # 権限変更
            r'pip3?\s+install',           # パッケージインストール
        ]
        for pat in modifying_patterns:
            if re.search(pat, command):
                return True

    return False


def run_health_check():
    """
    VPS上でsite_health_check.pyを実行
    Returns: (connected: bool, fail: int, warn: int, ok: int, summary: str)
    """
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "ConnectTimeout=8",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                f"root@{VPS_IP}",
                "python3 /opt/shared/scripts/site_health_check.py --quick 2>&1"
            ],
            capture_output=True, text=True, timeout=50
        )
        output = result.stdout + result.stderr
        # ANSIコード除去
        clean = re.sub(r'\033\[[0-9;]*m', '', output)

        # FAIL/WARN/OK カウント（数字付き集計行から抽出）
        fail = 0
        warn = 0
        ok = 0
        # "FAIL:2 / WARN:5 / OK:10" のような集計行を探す
        summary_match = re.search(r'FAIL:(\d+).*?WARN:(\d+).*?OK:(\d+)', clean)
        if summary_match:
            fail = int(summary_match.group(1))
            warn = int(summary_match.group(2))
            ok = int(summary_match.group(3))
        else:
            # フォールバック: [ FAIL ] を数える
            fail = len(re.findall(r'\[\s*FAIL\s*\]', clean))
            warn = len(re.findall(r'\[\s*WARN\s*\]', clean))
            ok = len(re.findall(r'\[\s*OK\s*\]', clean))

        # FAIL行を抽出（通知用）
        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        fail_lines = [l for l in lines if '[ FAIL ]' in l or 'FAIL:' in l]
        summary = '\n'.join(fail_lines[:6]) if fail_lines else f"FAIL:{fail} WARN:{warn} OK:{ok}"

        return True, fail, warn, ok, summary

    except subprocess.TimeoutExpired:
        return False, 0, 0, 0, "SSH timeout (VPS unreachable)"
    except Exception as e:
        return False, 0, 0, 0, f"SSH error: {e}"


def save_state(fail, warn, ok, command):
    """健全性チェック結果をstateファイルに保存"""
    state = {
        "checked_at": datetime.now().isoformat(),
        "command_preview": command[:150],
        "fail": fail,
        "warn": warn,
        "ok": ok,
        "resolved": fail == 0
    }
    HEALTH_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    data = load_input()
    tool_name = data.get("tool_name", "")

    if tool_name != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # ── verify_ui.py 実行結果をローカルステートに保存 ──────────────────────────
    # Claudeが ssh ... verify_ui.py を実行したとき、出力から PASS/FAIL を抽出して
    # state/ui_verification.json に保存 → fact-checker.py が参照する
    if "verify_ui.py" in command:
        # tool_response は {"output": "..."} または {"content": [...]} など複数形式に対応
        tool_response = data.get("tool_response", {})
        output = ""
        if isinstance(tool_response, str):
            output = tool_response
        elif isinstance(tool_response, dict):
            output = tool_response.get("output", "")
            if not output:
                # content形式 ({"content": [{"type": "text", "text": "..."}]})
                content = tool_response.get("content", [])
                if isinstance(content, list):
                    output = " ".join(
                        str(c.get("text", "")) for c in content
                        if isinstance(c, dict)
                    )
                elif isinstance(content, str):
                    output = content
        output = str(output)

        ui_passed = "PLAYWRIGHT_PASS" in output
        ui_state = {
            "checked_at": datetime.now().isoformat(),
            "all_pass": ui_passed,
            "command_preview": command[:100],
            "output_preview": output[:600],
            "_debug_response_keys": list(tool_response.keys()) if isinstance(tool_response, dict) else str(type(tool_response))
        }
        (STATE_DIR / "ui_verification.json").write_text(
            json.dumps(ui_state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if ui_passed:
            print("✅ [Playwright] PLAYWRIGHT_PASS — UI検証済み（stateに保存）")
        else:
            print("❌ [Playwright] PLAYWRIGHT_FAIL — UI検証失敗（修正して再実行が必要）")
        sys.exit(0)

    if not is_vps_modifying(command):
        sys.exit(0)

    # VPS変更を検出 — 健全性チェック実行
    print(f"\n🔍 [自動検品] VPS変更を検出 → site_health_check.py 実行中...")
    sys.stdout.flush()

    connected, fail, warn, ok, summary = run_health_check()

    if not connected:
        print(f"⚠️ [自動検品] VPS接続エラー（{summary}）— チェックをスキップ")
        sys.exit(0)

    # 結果を保存（Stopフックが参照する）
    save_state(fail, warn, ok, command)

    if fail > 0:
        print(f"\n🚨 [自動検品 FAIL: {fail}件検出]")
        print(f"  FAIL:{fail} / WARN:{warn} / OK:{ok}")
        print(f"  問題箇所:")
        for line in summary.split('\n'):
            if line.strip():
                print(f"    {line}")
        print(f"\n  ❌ FAILを修正してから「完了」と報告してください。")
        print(f"  確認コマンド: ssh root@{VPS_IP} python3 /opt/shared/scripts/site_health_check.py --quick")
        # exit(1): PostToolUse の出力をClaudeのコンテキストに注入
        sys.exit(1)
    else:
        print(f"✅ [自動検品 OK] FAIL:0 / WARN:{warn} / OK:{ok}")
        sys.exit(0)


if __name__ == "__main__":
    main()
