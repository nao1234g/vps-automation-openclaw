#!/usr/bin/env python3
"""Deploy prediction_page_builder.py to VPS and run --report test."""
import paramiko
import sys
import os

# Fix Windows encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOST = "163.44.124.123"
USER = "root"
PASSWORD = "MySecurePass2026!"
LOCAL_FILE = r"c:\Users\ewg2106-01\Desktop\vps-automation-openclaw-main\scripts\prediction_page_builder.py"
REMOTE_FILE = "/opt/shared/scripts/prediction_page_builder.py"

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))

def main():
    safe_print(f"[1] Connecting to {HOST} via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=22, username=USER, password=PASSWORD, timeout=30)
    safe_print("    Connected OK")

    # Step 2: Upload file via SFTP
    safe_print(f"\n[2] Uploading {os.path.basename(LOCAL_FILE)} to VPS...")
    sftp = client.open_sftp()

    stdin, stdout, stderr = client.exec_command("mkdir -p /opt/shared/scripts /opt/shared/polymarket && echo OK")
    result = stdout.read().decode().strip()
    safe_print(f"    mkdir result: {result}")

    sftp.put(LOCAL_FILE, REMOTE_FILE)
    sftp.chmod(REMOTE_FILE, 0o755)
    safe_print(f"    Uploaded to {REMOTE_FILE}")

    stdin, stdout, stderr = client.exec_command(f"ls -la {REMOTE_FILE}")
    safe_print(f"    {stdout.read().decode().strip()}")
    sftp.close()

    # Step 3: Run --report mode
    safe_print(f"\n[3] Running: python3 {REMOTE_FILE} --report")
    safe_print("=" * 70)
    cmd = f"python3 {REMOTE_FILE} --report 2>&1"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    
    output = stdout.read().decode("utf-8", errors="replace")
    err_output = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()

    if output:
        for line in output.splitlines():
            safe_print(line)
    if err_output:
        safe_print("[STDERR]")
        for line in err_output.splitlines():
            safe_print(line)
    
    safe_print("=" * 70)
    safe_print(f"Exit code: {exit_code}")

    # Step 4: Check output file
    safe_print(f"\n[4] Checking output file...")
    stdin, stdout, stderr = client.exec_command(f"ls -la /opt/shared/polymarket/tracker_page_data.json 2>&1")
    safe_print(f"    {stdout.read().decode().strip()}")

    stdin, stdout, stderr = client.exec_command(f"cat /opt/shared/polymarket/tracker_page_data.json 2>&1")
    json_content = stdout.read().decode("utf-8", errors="replace").strip()
    if json_content:
        safe_print(f"\n[5] Output JSON content:")
        for line in json_content.splitlines()[:80]:
            safe_print(line)

    # Data file status
    safe_print(f"\n[6] Data file status:")
    for path in ["/opt/shared/scripts/prediction_db.json", "/opt/shared/polymarket/embed_data.json", "/opt/cron-env.sh"]:
        stdin, stdout, stderr = client.exec_command(f"ls -la {path} 2>&1")
        safe_print(f"    {stdout.read().decode().strip()}")

    client.close()
    safe_print("\nDone.")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
