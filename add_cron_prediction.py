#!/usr/bin/env python3
"""SSH into VPS and add prediction_page_builder.py to crontab."""

import paramiko
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HOST = "163.44.124.123"
USER = "root"
PASSWORD = "MySecurePass2026!"

CRON_LINE = "0 22 * * * /usr/bin/python3 /opt/shared/scripts/prediction_page_builder.py --update >> /opt/shared/polymarket/prediction_page.log 2>&1"


def ssh_exec(client, cmd):
    """Execute a command via SSH and return stdout/stderr."""
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    return out, err, exit_code


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"[1] Connecting to {HOST} as {USER}...")
    try:
        client.connect(HOST, port=22, username=USER, password=PASSWORD, timeout=15)
    except Exception as e:
        print(f"ERROR: SSH connection failed: {e}")
        sys.exit(1)
    print("    Connected successfully.\n")

    # Step 2: Show current crontab
    print("[2] Current crontab:")
    print("-" * 70)
    out, err, rc = ssh_exec(client, "crontab -l 2>/dev/null || true")
    current_crontab = out
    print(current_crontab if current_crontab.strip() else "(empty)")
    print("-" * 70)
    print()

    # Step 3: Check if cron line already exists
    if CRON_LINE in current_crontab:
        print("[3] The cron line already exists. No changes needed.")
        client.close()
        return

    # Add the new cron line
    print("[3] Adding new cron line...")
    print(f"    {CRON_LINE}")

    # Use ( crontab -l; echo "new line" ) | crontab - pattern
    append_cmd = '( crontab -l 2>/dev/null; echo "' + CRON_LINE + '" ) | crontab -'
    out, err, rc = ssh_exec(client, append_cmd)
    if rc != 0:
        print(f"    ERROR: Failed to update crontab (exit code {rc})")
        print(f"    stderr: {err}")
        client.close()
        sys.exit(1)
    print("    Cron line added successfully.\n")

    # Step 4: Verify updated crontab
    print("[4] Updated crontab:")
    print("-" * 70)
    out, err, rc = ssh_exec(client, "crontab -l 2>/dev/null || true")
    print(out if out.strip() else "(empty)")
    print("-" * 70)

    # Verify the line is present
    if CRON_LINE in out:
        print("\n    VERIFIED: The new cron line is present.")
    else:
        print("\n    WARNING: The new cron line was NOT found in the updated crontab.")

    client.close()
    print("\nDone. SSH connection closed.")


if __name__ == "__main__":
    main()
