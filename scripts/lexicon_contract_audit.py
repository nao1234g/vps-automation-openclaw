#!/usr/bin/env python3
"""Audit that the public lexicon and mission contract remain aligned."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from canonical_public_lexicon import get_about_copy, get_brand_copy, get_tracker_copy  # noqa: E402
from mission_contract import get_mission_contract  # noqa: E402


EXPECTED_JA_TRACKER = {
    "view_in_play": "進行中",
    "view_awaiting": "判定待ち",
    "view_resolved": "判定済み",
}

EXPECTED_EN_TRACKER = {
    "view_in_play": "In Play",
    "view_awaiting": "Awaiting Verification",
    "view_resolved": "Resolved",
}

MOJIBAKE_MARKERS = ("縺", "繧", "蛻､", "讀懆", "莠域ｸｬ")


def audit() -> dict[str, object]:
    failures: list[str] = []
    contract = get_mission_contract()
    ja_brand = get_brand_copy("ja")
    en_brand = get_brand_copy("en")
    ja_tracker = get_tracker_copy("ja")
    en_tracker = get_tracker_copy("en")
    ja_about = get_about_copy("ja")
    en_about = get_about_copy("en")

    if contract["founder_os"]["canonical_name"] != "NAOTO OS":
        failures.append("founder_os_not_canonical")
    if contract["founder_os"]["pvqe"]["P"] != "判断精度":
        failures.append("pvqe_p_not_canonical")
    if contract["brand_contract"]["ja_platform_name"] != ja_brand["platform_name"]:
        failures.append("ja_platform_name_mismatch")
    if contract["brand_contract"]["en_platform_name"] != en_brand["platform_name"]:
        failures.append("en_platform_name_mismatch")

    for key, expected in EXPECTED_JA_TRACKER.items():
        if ja_tracker[key] != expected:
            failures.append(f"ja_tracker_{key}_not_canonical")
    for key, expected in EXPECTED_EN_TRACKER.items():
        if en_tracker[key] != expected:
            failures.append(f"en_tracker_{key}_not_canonical")

    if ja_about["hero_title"] != "検証可能な予測プラットフォーム":
        failures.append("ja_about_hero_not_canonical")
    if en_about["hero_title"] != "Verifiable Forecast Platform":
        failures.append("en_about_hero_not_canonical")

    for bucket_name, bucket in {
        "ja_brand": ja_brand,
        "ja_tracker": ja_tracker,
        "ja_about": ja_about,
    }.items():
        rendered = json.dumps(bucket, ensure_ascii=False)
        if any(marker in rendered for marker in MOJIBAKE_MARKERS):
            failures.append(f"{bucket_name}_contains_mojibake_markers")

    return {
        "checked": 12,
        "failures": failures,
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
