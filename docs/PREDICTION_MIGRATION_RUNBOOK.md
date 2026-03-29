# Prediction Platform Migration Runbook

> Step-by-step commands to run all Phase 1-3 migrations.
> All scripts are idempotent — safe to re-run.
> Last updated: 2026-03-29

---

## Prerequisites

- SSH access to VPS: `ssh root@163.44.124.123`
- Working directory: `/opt/shared/scripts/`
- Python 3: `python3 --version` ≥ 3.8
- prediction_db.json exists and is valid JSON

---

## Phase 3: initial_prob Provenance Backfill

**Script**: `/tmp/phase11_initial_prob_backfill.py`
**Status**: ✅ EXECUTED 2026-03-29T11:12:26Z
**Backup**: `prediction_db.json.bak-phase11-20260329-111226`

```bash
# Dry run (verify counts)
ssh root@163.44.124.123 "python3 /tmp/phase11_initial_prob_backfill.py --dry-run"
# Expected output:
#   To update: 1115
#   PROVISIONAL: 1111
#   NOT_SCORABLE: 4
#   Avg Brier: 0.4697

# Apply
ssh root@163.44.124.123 "python3 /tmp/phase11_initial_prob_backfill.py --apply"

# Verify
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
preds=db['predictions']
tiers={}
[tiers.update({p.get('official_score_tier','?'):tiers.get(p.get('official_score_tier','?'),0)+1}) for p in preds]
print('initial_prob set:', len([p for p in preds if p.get('initial_prob') is not None]), '/', len(preds))
print('Tiers:', tiers)
print('Brier avg:', db['meta'].get('official_brier_avg_initial_prob'))
\""
```

---

## Phase 2: Resolution Policy Schema

**Script**: `/tmp/phase12_resolution_policy.py`
**Status**: ✅ EXECUTED 2026-03-29T11:14:25Z
**Backup**: `prediction_db.json.bak-phase12-20260329-111425`

```bash
# Dry run
ssh root@163.44.124.123 "python3 /tmp/phase12_resolution_policy.py --dry-run"

# Apply
ssh root@163.44.124.123 "python3 /tmp/phase12_resolution_policy.py --apply"

# Verify
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
preds=db['predictions']
rc=sum(1 for p in preds if 'resolution_criteria' in p)
asy=sum(1 for p in preds if 'authoritative_sources' in p)
print('resolution_criteria:', rc, '/', len(preds))
print('authoritative_sources:', asy, '/', len(preds))
print('meta schema ver:', db['meta'].get('resolution_policy_schema_version'))
\""
```

---

## Phase 1: Canonical Schema Migration

**Script**: `/opt/shared/scripts/phase10_canonical_migration.py`
**Status**: 🔄 In progress (script being finalized)

```bash
# Dry run (check what will change)
ssh root@163.44.124.123 "cd /opt/shared/scripts && python3 phase10_canonical_migration.py --dry-run"

# Apply
ssh root@163.44.124.123 "cd /opt/shared/scripts && python3 phase10_canonical_migration.py --apply"

# Verify
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
preds=db['predictions']
qt={}
[qt.update({p.get('question_type',''):qt.get(p.get('question_type',''),0)+1}) for p in preds]
print('question_type distribution:', qt)
sk=sum(1 for p in preds if p.get('semantic_key'))
print('semantic_key set:', sk, '/', len(preds))
egd=sum(1 for p in preds if p.get('evidence_grace_days') is not None)
print('evidence_grace_days set:', egd, '/', len(preds))
\""
```

---

## Post-Migration Validation

After all three phases are complete:

```bash
ssh root@163.44.124.123 "python3 -c \"
import json
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
meta = db['meta']

print('=== Phase 1 (Canonical) ===')
qt = {}
for p in preds:
    v = p.get('question_type','')
    qt[v] = qt.get(v,0)+1
print('question_type:', qt)
sk = sum(1 for p in preds if p.get('semantic_key'))
egd = sum(1 for p in preds if p.get('evidence_grace_days') is not None)
print('semantic_key:', sk, '/', len(preds))
print('evidence_grace_days:', egd, '/', len(preds))

print()
print('=== Phase 2 (Resolution Policy) ===')
rc = sum(1 for p in preds if 'resolution_criteria' in p)
asy = sum(1 for p in preds if 'authoritative_sources' in p)
print('resolution_criteria:', rc, '/', len(preds))
print('authoritative_sources:', asy, '/', len(preds))

print()
print('=== Phase 3 (Score Provenance) ===')
ip = sum(1 for p in preds if p.get('initial_prob') is not None)
tiers = {}
for p in preds:
    t = p.get('official_score_tier','?')
    tiers[t] = tiers.get(t,0)+1
print('initial_prob:', ip, '/', len(preds))
print('tiers:', tiers)
print('brier_avg:', meta.get('official_brier_avg_initial_prob'))
print('brier_tier:', meta.get('official_brier_avg_initial_prob_tier'))
print('schema_version:', meta.get('schema_version'))
\""
```

Expected output after all phases:
```
=== Phase 1 (Canonical) ===
question_type: {'BINARY_BY_DEADLINE': 1115}
semantic_key: 1115 / 1115
evidence_grace_days: ~1100 / 1115 (some may lack event_cutoff_at)

=== Phase 2 (Resolution Policy) ===
resolution_criteria: 1115 / 1115
authoritative_sources: 1115 / 1115

=== Phase 3 (Score Provenance) ===
initial_prob: 1115 / 1115
tiers: {'PROVISIONAL': 1111, 'NOT_SCORABLE': 4}
brier_avg: 0.4697
brier_tier: PROVISIONAL
schema_version: 2.0
```

---

## Rebuilding Public Pages

After migrations complete, rebuild prediction pages:

```bash
# JA page
ssh root@163.44.124.123 "cd /opt/shared/scripts && nohup python3 prediction_page_builder.py --lang ja > /tmp/pb_ja.log 2>&1 &"

# EN page (may take 2+ minutes)
ssh root@163.44.124.123 "cd /opt/shared/scripts && nohup python3 prediction_page_builder.py --lang en > /tmp/pb_en.log 2>&1 &"

# Monitor
ssh root@163.44.124.123 "tail -f /tmp/pb_ja.log"
```

---

## Rollback Procedure

If any migration causes problems, rollback from backup:

```bash
# List backups
ssh root@163.44.124.123 "ls -la /opt/shared/scripts/prediction_db.json.bak-*"

# Rollback to specific backup
ssh root@163.44.124.123 "cp /opt/shared/scripts/prediction_db.json.bak-phase11-20260329-111226 /opt/shared/scripts/prediction_db.json"
```

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial runbook. Phase 2+3 complete. Phase 1 in progress. |
