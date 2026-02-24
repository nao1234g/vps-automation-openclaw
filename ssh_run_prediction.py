#!/usr/bin/env python3
"""SSH into VPS and run prediction_page_builder.py --update"""

import paramiko
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = "163.44.124.123"
USER = "root"
PASSWORD = "MySecurePass2026!"

def run_command(client, cmd, timeout=120):
    """Execute a command via SSH and return stdout/stderr."""
    print(f"\n{'='*60}")
    print(f"[CMD] {cmd}")
    print('='*60)
    
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    
    if out:
        # Sanitize for Windows console
        safe_out = out.encode('ascii', errors='replace').decode('ascii')
        print(f"[STDOUT]\n{safe_out}")
    if err:
        safe_err = err.encode('ascii', errors='replace').decode('ascii')
        print(f"[STDERR]\n{safe_err}")
    print(f"[EXIT CODE] {exit_code}")
    
    return out, err, exit_code

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {USER}@{HOST}...")
    try:
        client.connect(
            hostname=HOST,
            username=USER,
            password=PASSWORD,
            timeout=30,
            look_for_keys=False,
            allow_agent=False,
        )
        print("SSH connection established.")
    except Exception as e:
        print(f"SSH connection failed: {e}")
        sys.exit(1)
    
    try:
        # Step 1: Check the script exists
        run_command(client, "ls -la /opt/shared/scripts/prediction_page_builder.py")
        
        # Step 2: Run prediction_page_builder.py --update
        out, err, exit_code = run_command(
            client,
            "cd /opt/shared/scripts && python3 prediction_page_builder.py --update",
            timeout=180
        )
        
        if exit_code != 0:
            print("\n[WARNING] Script exited with non-zero code. Checking details...")
        else:
            print("\n[SUCCESS] prediction_page_builder.py --update completed successfully.")
        
        # Step 3: Verify the /predictions/ page exists
        run_command(
            client,
            "curl -sk https://nowpattern.com/predictions/ | head -100"
        )
        
    finally:
        client.close()
        print("\nSSH connection closed.")

if __name__ == "__main__":
    main()
