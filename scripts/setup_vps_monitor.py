#!/usr/bin/env python
# G4セットアップ: Telegramトークンを設定ファイルに保存 + タスクスケジューラ登録
# 実行: python scripts/setup_vps_monitor.py
import json, os, subprocess, sys
from pathlib import Path

CONFIG_FILE = Path.home() / ".claude" / "vps_monitor_config.json"
SCRIPT = Path(__file__).parent / "vps_health_monitor.ps1"

def load_vps_env():
    """VPSからcron-env.shを読んでトークン取得"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
             "-o", "BatchMode=yes", "root@163.44.124.123",
             "grep -E 'TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID' /opt/cron-env.sh"],
            capture_output=True, text=True, timeout=15
        )
        env = {}
        for line in result.stdout.split("\n"):
            if "=" in line:
                line = line.replace("export ", "").strip()
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
        return env
    except Exception as e:
        print(f"SSH error: {e}")
        return {}

def main():
    print("G4 VPS Health Monitor セットアップ")
    print("=" * 40)

    # Telegramトークン取得
    print("VPSからTelegramトークンを取得中...")
    env = load_vps_env()
    bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")

    if not bot_token:
        print("ERROR: VPSからTOKEN取得失敗。手動入力してください。")
        bot_token = input("TELEGRAM_BOT_TOKEN: ").strip()
        chat_id = input("TELEGRAM_CHAT_ID: ").strip()

    # 設定ファイル保存
    config = {"bot_token": bot_token, "chat_id": chat_id}
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    print(f"設定保存: {CONFIG_FILE}")

    # タスクスケジューラ登録
    task_name = "VPSHealthMonitor"
    ps_path = str(SCRIPT.resolve())
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "{ps_path}"',
        "/sc", "MINUTE",
        "/mo", "5",
        "/f"  # 上書き
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"タスクスケジューラ登録完了: {task_name} (5分間隔)")
        else:
            print(f"タスクスケジューラ登録失敗: {result.stderr}")
            print(f"手動登録コマンド:")
            print(f'schtasks /create /tn "{task_name}" /tr "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File \\"{ps_path}\\"" /sc MINUTE /mo 5 /f')
    except Exception as e:
        print(f"schtasks error: {e}")

    # 動作テスト
    print("\n動作テスト実行中...")
    test_result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_path],
        capture_output=True, text=True, timeout=30
    )
    if test_result.stdout:
        print(test_result.stdout)
    if test_result.stderr:
        print(f"STDERR: {test_result.stderr[:200]}")

    print("\nG4 セットアップ完了！")
    print("5分ごとにVPS死活監視が実行されます。")
    print("3回連続失敗でTelegram通知が届きます。")

if __name__ == "__main__":
    main()
