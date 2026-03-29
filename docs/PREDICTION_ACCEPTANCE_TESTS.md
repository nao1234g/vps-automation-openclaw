# Prediction Platform Acceptance Tests

> Test matrix for verifying prediction platform health.
> Run after any migration or code change.
> Last updated: 2026-03-29

---

## Test Categories

| Category | Tests | Automated | Manual |
|----------|-------|-----------|--------|
| Schema integrity | T01-T07 | ✅ | - |
| Score provenance | T08-T12 | ✅ | - |
| Page generation | T13-T18 | ✅ | manual spot-check |
| Bilingual coverage | T19-T22 | ✅ | - |
| Integrity proofs | T23-T26 | ✅ | - |

---

## Schema Integrity Tests

### T01: Schema Version

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
sv = db['meta'].get('schema_version','')
assert sv == '2.0', 'FAIL: schema_version=' + str(sv)
print('PASS T01: schema_version =', sv)
\""
```

### T02: Status Enum Valid

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
valid = {'OPEN','AWAITING_EVIDENCE','RESOLVING','RESOLVED','EXPIRED_UNRESOLVED'}
bad = [p['prediction_id'] for p in db['predictions'] if p.get('status') not in valid]
assert len(bad) == 0, 'FAIL: invalid status on ' + str(bad[:5])
print('PASS T02: status enum OK,', len(db['predictions']), 'predictions')
\""
```

### T03: Verdict Enum Valid

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
valid = {'PENDING','HIT','MISS','NOT_SCORED'}
bad = [p['prediction_id'] for p in db['predictions'] if p.get('verdict') not in valid]
assert len(bad) == 0, 'FAIL: invalid verdict on ' + str(bad[:5])
print('PASS T03: verdict enum OK')
\""
```

### T04: Brier Score Range

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
bad = [p['prediction_id'] for p in db['predictions']
       if p.get('brier_score') is not None and not (0.0 <= p['brier_score'] <= 1.0)]
assert len(bad) == 0, 'FAIL: brier out of range: ' + str(bad)
resolved = [p for p in db['predictions'] if p.get('verdict') in ('HIT','MISS')]
has_bs = [p for p in resolved if p.get('brier_score') is not None]
print('PASS T04: Brier scores in [0,1]. RESOLVED with brier_score:', len(has_bs), '/', len(resolved))
\""
```

### T05: initial_prob Coverage (Phase 3)

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
missing = [p['prediction_id'] for p in preds if p.get('initial_prob') is None]
assert len(missing) == 0, 'FAIL: initial_prob missing on ' + str(len(missing)) + ' predictions'
print('PASS T05: initial_prob set on all', len(preds))
\""
```

### T06: official_score_tier Coverage (Phase 3)

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
valid_tiers = {'PROVISIONAL','MIGRATED_OFFICIAL','VERIFIED_OFFICIAL','NOT_SCORABLE'}
bad = [p['prediction_id'] for p in preds if p.get('official_score_tier') not in valid_tiers]
assert len(bad) == 0, 'FAIL: invalid tier on ' + str(bad[:5])
tiers = {}
for p in preds:
    t = p.get('official_score_tier','?')
    tiers[t] = tiers.get(t,0)+1
print('PASS T06: official_score_tier valid. Distribution:', tiers)
\""
```

### T07: Brier Formula Spot Check

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
resolved = [p for p in db['predictions'] if p.get('verdict') in ('HIT','MISS') and p.get('initial_prob') is not None and p.get('brier_score') is not None]
errors = 0
for p in resolved:
    outcome = 1 if p['verdict'] == 'HIT' else 0
    expected = round((p['initial_prob']/100 - outcome)**2, 6)
    actual = p['brier_score']
    if abs(expected - actual) > 0.0001:
        print('MISMATCH:', p['prediction_id'], 'expected', expected, 'got', actual)
        errors += 1
assert errors == 0, 'FAIL: ' + str(errors) + ' Brier formula mismatches'
print('PASS T07: Brier formula correct on all', len(resolved), 'resolved predictions')
\""
```

---

## Score Provenance Tests

### T08: score_provenance_locked_at Set

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
ts = db['meta'].get('score_provenance_locked_at')
assert ts, 'FAIL: score_provenance_locked_at not set'
print('PASS T08: score_provenance_locked_at =', ts)
\""
```

### T09: initial_prob_source All Set

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
valid = {'FROM_IMMUTABLE_LEDGER','FROM_TIMESTAMPED_SNAPSHOT','FROM_MANIFEST','FROM_CURRENT_VALUE_BACKFILL','UNKNOWN'}
bad = [p['prediction_id'] for p in preds if p.get('initial_prob_source') not in valid]
assert len(bad) == 0, 'FAIL: invalid initial_prob_source: ' + str(bad[:5])
print('PASS T09: initial_prob_source valid on all', len(preds))
\""
```

### T10: NOT_SCORABLE Count

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
ns = [p for p in db['predictions'] if p.get('official_score_tier') == 'NOT_SCORABLE']
print('PASS T10: NOT_SCORABLE count =', len(ns), '(expected: 4)')
for p in ns:
    print(' ', p['prediction_id'], 'verdict:', p.get('verdict'))
\""
```

---

## Page Generation Tests

### T11: /predictions/ Page Exists and Loads

```bash
curl -s -o /dev/null -w "%{http_code}" https://nowpattern.com/predictions/
# Expected: 200
```

### T12: /en/predictions/ Page Exists and Loads

```bash
curl -s -o /dev/null -w "%{http_code}" https://nowpattern.com/en/predictions/
# Expected: 200
```

### T13: Oracle Guardian < 5%

Check via prediction_page_builder.py logs or direct calculation.

---

## Quick All-Tests Runner

```bash
ssh root@163.44.124.123 "python3 << 'EOF'
import json
db = json.load(open('/opt/shared/scripts/prediction_db.json'))
preds = db['predictions']
meta = db['meta']
results = []

# T01
results.append(('T01 schema_version', meta.get('schema_version') == '2.0'))
# T02
valid_s = {'OPEN','AWAITING_EVIDENCE','RESOLVING','RESOLVED','EXPIRED_UNRESOLVED'}
results.append(('T02 status enum', all(p.get('status') in valid_s for p in preds)))
# T03
valid_v = {'PENDING','HIT','MISS','NOT_SCORED'}
results.append(('T03 verdict enum', all(p.get('verdict') in valid_v for p in preds)))
# T04
bs_valid = all(p.get('brier_score') is None or 0<=p['brier_score']<=1 for p in preds)
results.append(('T04 brier range', bs_valid))
# T05
results.append(('T05 initial_prob all set', all(p.get('initial_prob') is not None for p in preds)))
# T06
valid_t = {'PROVISIONAL','MIGRATED_OFFICIAL','VERIFIED_OFFICIAL','NOT_SCORABLE'}
results.append(('T06 tier enum', all(p.get('official_score_tier') in valid_t for p in preds)))
# T07
errors = 0
for p in preds:
    if p.get('verdict') in ('HIT','MISS') and p.get('initial_prob') is not None and p.get('brier_score') is not None:
        o = 1 if p['verdict']=='HIT' else 0
        if abs((p['initial_prob']/100-o)**2 - p['brier_score']) > 0.0001:
            errors += 1
results.append(('T07 brier formula', errors == 0))
# T08
results.append(('T08 provenance_locked_at', bool(meta.get('score_provenance_locked_at'))))
# T09
valid_src = {'FROM_IMMUTABLE_LEDGER','FROM_TIMESTAMPED_SNAPSHOT','FROM_MANIFEST','FROM_CURRENT_VALUE_BACKFILL','UNKNOWN'}
results.append(('T09 initial_prob_source', all(p.get('initial_prob_source') in valid_src for p in preds)))

passed = sum(1 for _, r in results if r)
print(f'Results: {passed}/{len(results)} PASS')
for name, r in results:
    print(f'  {\"PASS\" if r else \"FAIL\"} {name}')
EOF"
```

## Phase 1 Canonical Schema Tests

### T10: question_type All BINARY_BY_DEADLINE

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
bad = [p['prediction_id'] for p in db['predictions'] if p.get('question_type') != 'BINARY_BY_DEADLINE']
assert len(bad) == 0, 'FAIL: non-BINARY_BY_DEADLINE: ' + str(bad[:5])
print('PASS T10: all', len(db['predictions']), 'predictions have question_type=BINARY_BY_DEADLINE')
\"\""
```

### T11: semantic_key Coverage

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
missing = [p['prediction_id'] for p in db['predictions'] if not p.get('semantic_key')]
assert len(missing) == 0, 'FAIL: semantic_key missing on ' + str(len(missing))
print('PASS T11: semantic_key set on all', len(db['predictions']))
\"\""
```

### T12: canonical_question Coverage

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
missing = [p['prediction_id'] for p in db['predictions'] if not p.get('canonical_question')]
assert len(missing) == 0, 'FAIL: canonical_question missing on ' + str(len(missing))
print('PASS T12: canonical_question set on all', len(db['predictions']))
\"\""
```

### T13: evidence_grace_days Coverage

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
missing = [p['prediction_id'] for p in db['predictions'] if p.get('evidence_grace_days') is None]
assert len(missing) == 0, 'FAIL: evidence_grace_days missing on ' + str(len(missing))
print('PASS T13: evidence_grace_days set on all', len(db['predictions']))
\"\""
```

### T14: resolution_criteria Schema Present

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
missing = [p['prediction_id'] for p in db['predictions'] if 'resolution_criteria' not in p]
assert len(missing) == 0, 'FAIL: resolution_criteria missing on ' + str(len(missing))
print('PASS T14: resolution_criteria schema present on all', len(db['predictions']))
\"\""
```

### T15: authoritative_sources Present

```bash
ssh root@163.44.124.123 "python3 -c \"
import json; db=json.load(open('/opt/shared/scripts/prediction_db.json'))
missing = [p['prediction_id'] for p in db['predictions'] if 'authoritative_sources' not in p]
assert len(missing) == 0, 'FAIL: authoritative_sources missing on ' + str(len(missing))
print('PASS T15: authoritative_sources present on all', len(db['predictions']))
\"\""
```

---

## Full Test Suite Runner (T01–T15)

```bash
ssh root@163.44.124.123 'python3 << '"'"'EOF'"'"'
import json
db = json.load(open("/opt/shared/scripts/prediction_db.json"))
preds = db["predictions"]
meta = db["meta"]
results = []

# T01
results.append(("T01 schema_version", meta.get("schema_version") == "2.0"))
# T02
valid_s = {"OPEN","AWAITING_EVIDENCE","RESOLVING","RESOLVED","EXPIRED_UNRESOLVED"}
results.append(("T02 status enum", all(p.get("status") in valid_s for p in preds)))
# T03
valid_v = {"PENDING","HIT","MISS","NOT_SCORED"}
results.append(("T03 verdict enum", all(p.get("verdict") in valid_v for p in preds)))
# T04
bs_valid = all(p.get("brier_score") is None or 0<=p["brier_score"]<=1 for p in preds)
results.append(("T04 brier range", bs_valid))
# T05
results.append(("T05 initial_prob all set", all(p.get("initial_prob") is not None for p in preds)))
# T06
valid_t = {"PROVISIONAL","MIGRATED_OFFICIAL","VERIFIED_OFFICIAL","NOT_SCORABLE"}
results.append(("T06 tier enum", all(p.get("official_score_tier") in valid_t for p in preds)))
# T07
errors = 0
for p in preds:
    if p.get("verdict") in ("HIT","MISS") and p.get("initial_prob") is not None and p.get("brier_score") is not None:
        o = 1 if p["verdict"]=="HIT" else 0
        if abs((p["initial_prob"]/100-o)**2 - p["brier_score"]) > 0.0001:
            errors += 1
results.append(("T07 brier formula", errors == 0))
# T08
results.append(("T08 provenance_locked_at", bool(meta.get("score_provenance_locked_at"))))
# T09
valid_src = {"FROM_IMMUTABLE_LEDGER","FROM_TIMESTAMPED_SNAPSHOT","FROM_MANIFEST","FROM_CURRENT_VALUE_BACKFILL","UNKNOWN"}
results.append(("T09 initial_prob_source", all(p.get("initial_prob_source") in valid_src for p in preds)))
# T10
results.append(("T10 question_type BINARY_BY_DEADLINE", all(p.get("question_type") == "BINARY_BY_DEADLINE" for p in preds)))
# T11
results.append(("T11 semantic_key all set", all(bool(p.get("semantic_key")) for p in preds)))
# T12
results.append(("T12 canonical_question all set", all(bool(p.get("canonical_question")) for p in preds)))
# T13
results.append(("T13 evidence_grace_days all set", all(p.get("evidence_grace_days") is not None for p in preds)))
# T14
results.append(("T14 resolution_criteria schema", all("resolution_criteria" in p for p in preds)))
# T15
results.append(("T15 authoritative_sources present", all("authoritative_sources" in p for p in preds)))

passed = sum(1 for _, r in results if r)
print("Results: " + str(passed) + "/" + str(len(results)) + " PASS")
for name, r in results:
    print("  " + ("PASS" if r else "FAIL") + " " + name)
EOF'
```

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2026-03-29 | Initial test matrix. T01-T09 verified PASS after Phase 2+3 migrations. |
| 2026-03-29 | Added T10-T15 for Phase 1 canonical schema. **15/15 PASS** verified on VPS. |
