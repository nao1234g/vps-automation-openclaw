#!/usr/bin/env python3
"""
SSH into VPS and add inject_live_panel.py to crontab,
scheduled 5 minutes after polymarket_monitor.py runs.
"""

import paramiko
import sys

HOST = "163.44.124.123"
USER = "root"
PASSWORD = "MySecurePass2026!"

CRON_LINE = "0 15,21,3,9 * * * /usr/bin/python3 /opt/shared/scripts/inject_live_panel.py >> /opt/shared/polymarket/live_panel.log 2>&1 && systemctl restart ghost-nowpattern"


def ssh_exec(client, cmd):
    """Execute a command and return stdout, stderr, exit code."""
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err, exit_code


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"[1] Connecting to {USER}@{HOST} ...")
    try:
        client.connect(HOST, port=22, username=USER, password=PASSWORD, timeout=15)
    except Exception as e:
        print(f"ERROR: SSH connection failed: {e}")
        sys.exit(1)
    print("    Connected successfully.")

    # Step 2: Show current crontab and find polymarket_monitor.py lines
    print("\n[2] Checking current crontab for polymarket_monitor.py ...")
    current_crontab, err, rc = ssh_exec(client, "crontab -l 2>/dev/null || true")

    monitor_lines = [l for l in current_crontab.splitlines() if "polymarket_monitor" in l]
    if monitor_lines:
        print("    Found polymarket_monitor.py schedule(s):")
        for line in monitor_lines:
            print(f"      {line}")
    else:
        print("    WARNING: No polymarket_monitor.py entries found in crontab.")
        print("    Will still proceed with adding inject_live_panel.py entry.")

    # Step 3: Check if inject_live_panel.py already exists in crontab
    print("\n[3] Checking if inject_live_panel.py is already in crontab ...")
    if "inject_live_panel.py" in current_crontab:
        existing = [l for l in current_crontab.splitlines() if "inject_live_panel" in l]
        print("    Already exists in crontab:")
        for line in existing:
            print(f"      {line}")
        print("    Skipping addition to avoid duplicates.")
    else:
        # Step 4: Add the new cron line
        print("    Not found. Adding new cron entry ...")

        # Ensure crontab ends with newline before appending
        new_crontab = current_crontab.rstrip("\n") + "\n" + CRON_LINE + "\n"

        # Write to a temp file and load via crontab command
        # This avoids shell escaping issues with pipe approach
        write_cmd = f"""
TMPFILE=$(mktemp)
crontab -l 2>/dev/null > "$TMPFILE" || true
echo '{CRON_LINE}' >> "$TMPFILE"
crontab "$TMPFILE"
rm -f "$TMPFILE"
"""
        out, err, rc = ssh_exec(client, write_cmd)
        if rc != 0:
            print(f"    ERROR: Failed to update crontab (exit code {rc})")
            print(f"    stderr: {err}")
            client.close()
            sys.exit(1)
        print("    Cron entry added successfully.")

    # Step 5: Show polymarket-related cron entries for verification
    print("\n[4] Verifying: all polymarket/inject_live_panel related cron entries:")
    print("    " + "-" * 70)
    updated_crontab, _, _ = ssh_exec(client, "crontab -l 2>/dev/null || true")
    relevant = [l for l in updated_crontab.splitlines()
                if "polymarket" in l.lower() or "inject_live_panel" in l.lower()]
    if relevant:
        for line in relevant:
            print(f"    {line}")
    else:
        print("    (none found)")
    print("    " + "-" * 70)

    client.close()
    print("\n[Done] SSH session closed.")


if __name__ == "__main__":
    main()
