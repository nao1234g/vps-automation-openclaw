# /vps-status skill

Check the current state of the VPS and report key metrics.

## Steps

1. SSH and read SHARED_STATE:
   ```bash
   ssh root@163.44.124.123 "cat /opt/shared/SHARED_STATE.md"
   ```

2. Check critical services:
   ```bash
   ssh root@163.44.124.123 "systemctl is-active neo-telegram neo2-telegram neo3-telegram ghost-nowpattern ghost-page-guardian 2>&1"
   ```

3. Check disk space:
   ```bash
   ssh root@163.44.124.123 "df -h / | tail -1"
   ```

4. Check recent errors:
   ```bash
   ssh root@163.44.124.123 "journalctl -u ghost-page-guardian --since '1 hour ago' --no-pager -n 20 2>/dev/null || true"
   ```

## Report Format

```
📊 VPS Status — [timestamp]
Articles: JA:[n] EN:[n] Total:[n]
Services: NEO-ONE [OK/FAIL] | NEO-TWO [OK/FAIL] | Ghost [OK/FAIL] | Guardian [OK/FAIL]
Disk: [used]/[total] ([%])
Predictions: [n] | Brier: [score]
⚠️ Issues: [list any FAIL or errors]
```
