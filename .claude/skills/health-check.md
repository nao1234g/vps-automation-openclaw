# /health-check skill

Run site health check and report results.

## Steps

1. Run quick health check:
   ```bash
   ssh root@163.44.124.123 "python3 /opt/shared/scripts/site_health_check.py --quick 2>&1 | tail -20"
   ```

2. If any FAIL, run full check:
   ```bash
   ssh root@163.44.124.123 "python3 /opt/shared/scripts/site_health_check.py 2>&1 | tail -40"
   ```

3. Check prediction page:
   ```bash
   ssh root@163.44.124.123 "curl -s -o /dev/null -w '%{http_code}' https://nowpattern.com/predictions/"
   ```

4. Check EN predictions:
   ```bash
   ssh root@163.44.124.123 "curl -s -o /dev/null -w '%{http_code}' https://nowpattern.com/en/predictions/"
   ```

## Pass Criteria
- All health checks: PASS (0 FAIL)
- /predictions/ HTTP: 200
- /en/predictions/ HTTP: 200

## On Failure
Report specific failures with context. Do not say "fixed" without verifying.
