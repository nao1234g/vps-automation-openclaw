#!/usr/bin/env python3
"""Patch evolution_loop.py to add granular [calibration] observability logging"""

target = '/opt/shared/scripts/evolution_loop.py'

with open(target, encoding='utf-8') as f:
    content = f.read()

# Marker: start of update_calibration_rules function body
marker_enter = 'def update_calibration_rules(predictions):\n    # Gemini \u3092\u4f7f\u3063\u3066 calibration_rules.json \u3092\u81ea\u52d5\u66f4\u65b0\u3059\u308b\n    import json as _json\n    resolved = [p for p in predictions if p.get("brier_score") is not None]\n    if len(resolved) < 5:\n        logger.info("[calibration] Only %d resolved, skipping" % len(resolved))\n        return False'

replacement_enter = 'def update_calibration_rules(predictions):\n    # Gemini \u3092\u4f7f\u3063\u3066 calibration_rules.json \u3092\u81ea\u52d5\u66f4\u65b0\u3059\u308b\n    import json as _json\n    resolved = [p for p in predictions if p.get("brier_score") is not None]\n    logger.info("[calibration] enter, total=%d resolved=%d" % (len(predictions), len(resolved)))\n    if len(resolved) < 5:\n        logger.info("[calibration] Only %d resolved, skipping" % len(resolved))\n        return False'

# Marker: after building prompt
marker_prompt = '    prompt = build_calibration_prompt(resolved, current_rules)\n    gemini_model = "gemini-2.5-pro"'

replacement_prompt = '    prompt = build_calibration_prompt(resolved, current_rules)\n    logger.info("[calibration] prompt_built, len=%d" % len(prompt))\n    gemini_model = "gemini-2.5-pro"'

# Marker: before API call
marker_api_start = '        req = urllib.request.Request(\n            url, data=payload,\n            headers={"Content-Type": "application/json"}, method="POST"\n        )\n        with urllib.request.urlopen(req, timeout=60) as resp:\n            result = _json.loads(resp.read().decode())\n        response_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()\n        logger.info("[calibration] Gemini response: %s" % response_text[:200])'

replacement_api_start = '        logger.info("[calibration] api_call_start, model=%s" % gemini_model)\n        req = urllib.request.Request(\n            url, data=payload,\n            headers={"Content-Type": "application/json"}, method="POST"\n        )\n        with urllib.request.urlopen(req, timeout=60) as resp:\n            result = _json.loads(resp.read().decode())\n        response_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()\n        logger.info("[calibration] api_call_success, response_len=%d" % len(response_text))\n        logger.info("[calibration] Gemini response: %s" % response_text[:200])'

# Marker: after JSON parse success
marker_json_ok = '        new_params = _json.loads(json_match.group())\n    except Exception as e:\n        logger.error("[calibration] JSON parse error: %s" % e)\n        return False'

replacement_json_ok = '        new_params = _json.loads(json_match.group())\n        logger.info("[calibration] json_extract_success, keys=%s" % list(new_params.keys()))\n    except Exception as e:\n        logger.error("[calibration] JSON parse error: %s" % e)\n        logger.info("[calibration] json_extract_failure, return_value=False")\n        return False'

# Marker: write success
marker_write = '        logger.info(\n            "[calibration] Updated: CR-001 bf=%.3f br=%.3f CR-002 f=%.3f CR-003 f=%.3f | %s"\n            % (bf, br, f2, f3, rationale)\n        )\n        return True'

replacement_write = '        logger.info(\n            "[calibration] Updated: CR-001 bf=%.3f br=%.3f CR-002 f=%.3f CR-003 f=%.3f | %s"\n            % (bf, br, f2, f3, rationale)\n        )\n        logger.info("[calibration] write_success, return_value=True")\n        return True'

# Marker: write failure
marker_write_fail = '    except Exception as e:\n        logger.error("[calibration] Write error: %s" % e)\n        return False'

replacement_write_fail = '    except Exception as e:\n        logger.error("[calibration] Write error: %s" % e)\n        logger.info("[calibration] write_failure, return_value=False")\n        return False'

changes = [
    (marker_enter, replacement_enter, "enter log"),
    (marker_prompt, replacement_prompt, "prompt_built log"),
    (marker_api_start, replacement_api_start, "api_call_start/success log"),
    (marker_json_ok, replacement_json_ok, "json_extract_success/failure log"),
    (marker_write, replacement_write, "write_success log"),
    (marker_write_fail, replacement_write_fail, "write_failure log"),
]

applied = []
skipped = []
for old, new, name in changes:
    if old in content:
        content = content.replace(old, new)
        applied.append(name)
    elif new in content:
        skipped.append(name + " (already present)")
    else:
        skipped.append(name + " (MARKER NOT FOUND)")

with open(target, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied: %s" % applied)
print("Skipped: %s" % skipped)
