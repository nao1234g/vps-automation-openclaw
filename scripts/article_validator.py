#!/usr/bin/env python3
"""
article_validator.py — 記事公開前バリデーションゲート v2.0

taxonomy.json駆動のSTRICTバリデーション。
不正タグ → 即ブロック + 有効タグ一覧をエラーメッセージで返す。

breaking_pipeline_helper.py から呼ばれる（Step 0）。

5層防御の第2層:
  Layer 0: NEO指示書にタグ一覧（プロンプトレベル — 無視される可能性あり）
  Layer 1: ★このスクリプト★（コードレベル — 回避不可能）
  Layer 2: publisher.py STRICT validation（投稿時の二重チェック）
  Layer 3: SDK Hooks（Ghost直接API呼び出しをブロック）
  Layer 4: 投稿後監査cron（安全網）

使い方:
  python3 article_validator.py /tmp/article_12345.json          # チェックのみ
  python3 article_validator.py /tmp/article_12345.json --strict  # 不合格時に exit(1)

戻り値:
  0 = 合格（公開OK）
  1 = 不合格（公開ブロック）
"""

import json
import os
import sys
import subprocess

TELEGRAM_SCRIPT = "/opt/shared/scripts/send-telegram-message.py"
TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nowpattern_taxonomy.json")

# ============================================================
# Taxonomy Loading — Single Source of Truth
# ============================================================

_VALID_GENRES = {}      # name_en -> slug
_VALID_EVENTS = {}      # name_en -> slug
_VALID_DYNAMICS = {}    # name_en -> slug
_TAG_LOOKUP = {}        # any_name_or_slug -> {"name_en": ..., "slug": ..., "type": ...}
_TAXONOMY_LOADED = False


def _load_taxonomy():
    """taxonomy.jsonを読み込み、全タグの逆引きテーブルを構築する。"""
    global _VALID_GENRES, _VALID_EVENTS, _VALID_DYNAMICS, _TAG_LOOKUP, _TAXONOMY_LOADED

    if _TAXONOMY_LOADED:
        return

    if not os.path.exists(TAXONOMY_PATH):
        print(f"WARNING: taxonomy.json not found at {TAXONOMY_PATH}")
        _TAXONOMY_LOADED = True
        return

    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        tax = json.load(f)

    for g in tax.get("genres", []):
        _VALID_GENRES[g["name_en"]] = g["slug"]
        _TAG_LOOKUP[g["name_en"]] = {"name_en": g["name_en"], "slug": g["slug"], "type": "genre"}
        _TAG_LOOKUP[g["name_en"].lower()] = {"name_en": g["name_en"], "slug": g["slug"], "type": "genre"}
        _TAG_LOOKUP[g["name_ja"]] = {"name_en": g["name_en"], "slug": g["slug"], "type": "genre"}
        _TAG_LOOKUP[g["slug"]] = {"name_en": g["name_en"], "slug": g["slug"], "type": "genre"}

    for e in tax.get("events", []):
        _VALID_EVENTS[e["name_en"]] = e["slug"]
        _TAG_LOOKUP[e["name_en"]] = {"name_en": e["name_en"], "slug": e["slug"], "type": "event"}
        _TAG_LOOKUP[e["name_en"].lower()] = {"name_en": e["name_en"], "slug": e["slug"], "type": "event"}
        _TAG_LOOKUP[e["name_ja"]] = {"name_en": e["name_en"], "slug": e["slug"], "type": "event"}
        _TAG_LOOKUP[e["slug"]] = {"name_en": e["name_en"], "slug": e["slug"], "type": "event"}

    for d in tax.get("dynamics", []):
        _VALID_DYNAMICS[d["name_en"]] = d["slug"]
        _TAG_LOOKUP[d["name_en"]] = {"name_en": d["name_en"], "slug": d["slug"], "type": "dynamics"}
        _TAG_LOOKUP[d["name_en"].lower()] = {"name_en": d["name_en"], "slug": d["slug"], "type": "dynamics"}
        _TAG_LOOKUP[d["name_ja"]] = {"name_en": d["name_en"], "slug": d["slug"], "type": "dynamics"}
        _TAG_LOOKUP[d["slug"]] = {"name_en": d["name_en"], "slug": d["slug"], "type": "dynamics"}

    _TAXONOMY_LOADED = True


def _resolve_tag(input_tag: str) -> dict | None:
    """任意の入力（name_en, name_ja, slug）を正規タグに解決する。"""
    _load_taxonomy()
    if input_tag in _TAG_LOOKUP:
        return _TAG_LOOKUP[input_tag]
    if input_tag.lower() in _TAG_LOOKUP:
        return _TAG_LOOKUP[input_tag.lower()]
    return None


def _parse_tag_string(tag_value) -> list[str]:
    """タグ値を個別タグのリストに分解する。
    入力形式: 文字列（"A / B" or "A × B" or "A, B"）またはリスト
    """
    if isinstance(tag_value, list):
        return [str(t).strip() for t in tag_value if str(t).strip()]

    if isinstance(tag_value, str):
        # まずスラッシュで分割、次に「×」で分割
        parts = tag_value.replace("×", "/").replace(",", "/").split("/")
        return [p.strip() for p in parts if p.strip()]

    return []


# ============================================================
# Validation
# ============================================================

# v4.0 必須フィールド
REQUIRED_V4_FIELDS = [
    "bottom_line",
    "bottom_line_pattern",
    "bottom_line_scenario",
    "bottom_line_watch",
    "between_the_lines",
    "open_loop_trigger",
    "open_loop_series",
]

# 既存の必須フィールド
REQUIRED_BASE_FIELDS = [
    "title",
    "language",
    "why_it_matters",
    "facts",
    "dynamics_tags",
    "dynamics_summary",
    "dynamics_sections",
    "scenarios",
    "genre_tags",
    "event_tags",
    "source_urls",
    "x_comment",
]


def _validate_tag_list(tags: list[str], tag_type: str, valid_set: dict) -> list[str]:
    """タグリストをバリデーション。不正タグごとにエラーメッセージを返す。"""
    errors = []
    for tag in tags:
        resolved = _resolve_tag(tag)
        if resolved is None:
            errors.append(
                f"INVALID_{tag_type.upper()}: '{tag}' はタクソノミーに存在しません。"
                f" 有効な{tag_type}タグ: {', '.join(sorted(valid_set.keys()))}"
            )
        elif resolved["type"] != tag_type:
            errors.append(
                f"WRONG_TYPE: '{tag}' は {resolved['type']} タグです（{tag_type} ではありません）。"
                f" 有効な{tag_type}タグ: {', '.join(sorted(valid_set.keys()))}"
            )
    return errors


def validate_article(article_data, strict=False):
    """記事JSONをバリデーション。

    Returns:
        (is_valid, errors, warnings)
    """
    _load_taxonomy()
    errors = []
    warnings = []

    title = article_data.get("title", "無題")

    # ============================================================
    # 1. 必須フィールドチェック
    # ============================================================
    for field in REQUIRED_BASE_FIELDS:
        val = article_data.get(field)
        if not val or (isinstance(val, (list, dict)) and len(val) == 0):
            errors.append(f"必須フィールド '{field}' が空です")

    # v4.0 フィールドチェック
    missing_v4 = []
    for field in REQUIRED_V4_FIELDS:
        val = article_data.get(field, "")
        if not val or (isinstance(val, str) and len(val.strip()) < 5):
            missing_v4.append(field)

    if missing_v4:
        errors.append(f"v4.0必須フィールドが欠落: {', '.join(missing_v4)}")

    # ============================================================
    # 2. タクソノミー STRICT バリデーション（最重要）
    # ============================================================
    genre_tags = _parse_tag_string(article_data.get("genre_tags", ""))
    event_tags = _parse_tag_string(article_data.get("event_tags", ""))
    dynamics_tags = _parse_tag_string(article_data.get("dynamics_tags", ""))

    # ジャンルタグ検証
    if len(genre_tags) == 0:
        errors.append("genre_tags が空です（最低1個必要）")
    elif len(genre_tags) > 3:
        errors.append(f"genre_tags が{len(genre_tags)}個（最大3個）")
    errors.extend(_validate_tag_list(genre_tags, "genre", _VALID_GENRES))

    # イベントタグ検証
    if len(event_tags) == 0:
        errors.append("event_tags が空です（最低1個必要）")
    elif len(event_tags) > 3:
        errors.append(f"event_tags が{len(event_tags)}個（最大3個）")
    errors.extend(_validate_tag_list(event_tags, "event", _VALID_EVENTS))

    # 力学タグ検証
    if len(dynamics_tags) == 0:
        errors.append("dynamics_tags が空です（最低1個必要）")
    elif len(dynamics_tags) > 4:
        errors.append(f"dynamics_tags が{len(dynamics_tags)}個（最大4個）")
    errors.extend(_validate_tag_list(dynamics_tags, "dynamics", _VALID_DYNAMICS))

    # 力学セクション内のタグも検証
    for i, section in enumerate(article_data.get("dynamics_sections", [])):
        section_tag = section.get("tag", "")
        if section_tag:
            resolved = _resolve_tag(section_tag)
            if resolved is None:
                errors.append(
                    f"dynamics_sections[{i}].tag: '{section_tag}' はタクソノミーに存在しません。"
                    f" 有効な力学タグ: {', '.join(sorted(_VALID_DYNAMICS.keys()))}"
                )

    # ============================================================
    # 3. タイトルバリデーション
    # ============================================================
    if title:
        forbidden_title_patterns = ["観測ログ", "Speed Log", "Deep Pattern", "#00"]
        for pattern in forbidden_title_patterns:
            if pattern in title:
                errors.append(f"タイトルに禁止文字列 '{pattern}' が含まれています")

    # ============================================================
    # 4. シナリオチェック
    # ============================================================
    scenarios = article_data.get("scenarios", [])
    if len(scenarios) < 3:
        errors.append(f"シナリオが{len(scenarios)}件（最低3件必要）")
    else:
        total_prob = 0
        for s in scenarios:
            if isinstance(s, (list, tuple)) and len(s) >= 2:
                prob_str = str(s[1]).strip().replace("%", "")
                try:
                    prob = float(prob_str)
                    if prob > 1:
                        prob = prob / 100.0
                    total_prob += prob
                except ValueError:
                    warnings.append(f"シナリオ確率がパースできません: {s[1]}")
            elif isinstance(s, dict):
                prob_str = str(s.get("probability", "0")).strip().replace("%", "")
                try:
                    prob = float(prob_str)
                    if prob > 1:
                        prob = prob / 100.0
                    total_prob += prob
                except ValueError:
                    pass

        if abs(total_prob - 1.0) > 0.05:
            warnings.append(f"シナリオ確率の合計が{total_prob*100:.0f}%（100%にすべき）")

    # ============================================================
    # 5. その他のチェック
    # ============================================================
    triggers = article_data.get("triggers", [])
    if len(triggers) < 2:
        warnings.append(f"トリガーが{len(triggers)}件（2件以上推奨）")

    sources = article_data.get("source_urls", [])
    if len(sources) < 2:
        warnings.append(f"ソースが{len(sources)}件（2件以上推奨）")

    dynamics_sections = article_data.get("dynamics_sections", [])
    if len(dynamics_sections) < 2:
        errors.append(f"力学分析が{len(dynamics_sections)}セクション（最低2つ必要）")
    else:
        for i, section in enumerate(dynamics_sections):
            analysis = section.get("analysis", "")
            if len(analysis) < 200:
                warnings.append(f"力学分析{i+1}が{len(analysis)}字（300-500語推奨）")

    pattern_history = article_data.get("pattern_history", [])
    if len(pattern_history) < 1:
        warnings.append("パターン史が0件（最低1件推奨）")

    # ============================================================
    # 結果表示
    # ============================================================
    print(f"\n{'='*60}")
    print(f"  ARTICLE VALIDATOR v2.0 - taxonomy.json STRICT validation")
    print(f"{'='*60}")
    print(f"  記事: {title[:60]}")
    print(f"  タグ: {genre_tags} / {event_tags} / {dynamics_tags}")

    if errors:
        print(f"\n  {'='*56}")
        print(f"  BLOCKED: {len(errors)}件のエラー（公開不可）")
        print(f"  {'='*56}")
        for e in errors:
            print(f"  X  {e}")
    else:
        print(f"\n  PASSED: 全チェック合格")

    if warnings:
        print(f"\n  警告: {len(warnings)}件")
        for w in warnings:
            print(f"  !  {w}")

    is_valid = len(errors) == 0

    if not is_valid:
        _send_telegram_block(title, errors)

    return is_valid, errors, warnings


def _send_telegram_block(title, errors):
    """公開ブロック時のTelegram通知"""
    msg = f"ARTICLE BLOCKED\n\n"
    msg += f"記事: {title[:50]}\n"
    msg += f"エラー: {len(errors)}件\n\n"
    for e in errors[:10]:  # 最大10件
        msg += f"X {e}\n"
    if len(errors) > 10:
        msg += f"\n... 他{len(errors)-10}件\n"
    msg += f"\n修正してから再投稿してください。\n"
    msg += f"タグ一覧: /opt/shared/scripts/nowpattern_taxonomy.json\n"
    msg += f"指示書: /opt/shared/docs/NEO_INSTRUCTIONS_V2.md セクション3"
    try:
        if os.path.exists(TELEGRAM_SCRIPT):
            subprocess.run(
                ["python3", TELEGRAM_SCRIPT, msg],
                capture_output=True, text=True, timeout=15
            )
    except Exception:
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Article Validator v2.0 — taxonomy.json駆動STRICTバリデーション")
    parser.add_argument("json_file", help="記事JSONファイルのパス")
    parser.add_argument("--strict", action="store_true", help="不合格時に exit(1)")
    args = parser.parse_args()

    if not os.path.exists(args.json_file):
        print(f"ERROR: ファイルが見つかりません: {args.json_file}")
        sys.exit(1)

    with open(args.json_file, "r", encoding="utf-8") as f:
        article_data = json.load(f)

    is_valid, errors, warnings = validate_article(article_data, strict=args.strict)

    if args.strict and not is_valid:
        print(f"\nBLOCKED: {len(errors)}件のエラーを修正してください")
        sys.exit(1)
    elif is_valid:
        print(f"\nPASSED: 公開OK")


if __name__ == "__main__":
    main()
