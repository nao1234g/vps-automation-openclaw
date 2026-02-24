#!/usr/bin/env python3
"""
Deploy prediction_page_builder.py to VPS via SSH/SFTP and execute it.
"""
import paramiko
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = "163.44.124.123"
USER = "root"
PASSWORD = "MySecurePass2026!"
LOCAL_FILE = r"c:\Users\ewg2106-01\Desktop\vps-automation-openclaw-main\scripts\prediction_page_builder.py"
REMOTE_FILE = "/opt/shared/scripts/prediction_page_builder.py"


def run_command(ssh, cmd, timeout=120):
    """Execute a command via SSH and return stdout/stderr."""
    print(f"\n{'='*60}")
    print(f"[CMD] {cmd}")
    print('='*60)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if out:
        print(f"[STDOUT]\n{out}")
    if err:
        print(f"[STDERR]\n{err}")
    print(f"[EXIT CODE] {exit_code}")
    return out, err, exit_code


def main():
    # --- Connect ---
    print(f"Connecting to {HOST} as {USER}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("SSH connection established.")

    # --- SFTP Upload ---
    print(f"\nUploading {LOCAL_FILE} -> {REMOTE_FILE} ...")
    sftp = ssh.open_sftp()
    sftp.put(LOCAL_FILE, REMOTE_FILE)
    remote_stat = sftp.stat(REMOTE_FILE)
    print(f"Upload complete. Remote file size: {remote_stat.st_size} bytes")
    sftp.close()

    # --- Make executable ---
    run_command(ssh, f"chmod +x {REMOTE_FILE}")

    # --- Step 1: Run --report (test mode) ---
    print("\n" + "#"*60)
    print("# STEP 1: Running --report (test / dry-run)")
    print("#"*60)
    out, err, rc = run_command(ssh, f"python3 {REMOTE_FILE} --report", timeout=180)

    if rc != 0:
        print(f"\n[ERROR] --report exited with code {rc}. Aborting --update.")
        ssh.close()
        sys.exit(1)

    # --- Step 2: Run --update (actual Ghost page update) ---
    print("\n" + "#"*60)
    print("# STEP 2: Running --update (Ghost page update)")
    print("#"*60)
    out, err, rc = run_command(ssh, f"python3 {REMOTE_FILE} --update", timeout=180)

    if rc != 0:
        print(f"\n[ERROR] --update exited with code {rc}.")
        ssh.close()
        sys.exit(1)

    print("\n" + "#"*60)
    print("# ALL DONE - deployment and execution complete")
    print("#"*60)

    ssh.close()
    print("SSH connection closed.")


if __name__ == "__main__":
    main()
