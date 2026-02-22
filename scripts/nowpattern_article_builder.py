"""
Nowpattern Article Builder v4.0
2モード制（Deep Pattern + Speed Log）対応 Ghost記事HTMLビルダー。
v3.1: language パラメータ追加（"ja" / "en" 切り替え）
v3.2: taxonomy.json lookup方式（slugify廃止 → 正式slug参照）
v4.0: Flywheel Format — Bottom Line, Between the Lines, Open Loop, 予測追跡ID

責務: HTML生成のみ。Ghost投稿・X投稿・インデックス更新は nowpattern_publisher.py が担当。

使い方:
  from nowpattern_article_builder import build_deep_pattern_html, build_speed_log_html

  # Deep Pattern（1,500-2,500語の本格分析記事）
  html = build_deep_pattern_html(
      title="The Structure Behind EU's €1.8B Apple Fine",
      language="en",   # ← "ja" or "en"
      why_it_matters="The 30-year App Store monopoly may be coming to an end.",
      bottom_line="Apple faces its biggest regulatory threat...",
      between_the_lines="What the EU isn't saying: this is really about...",
      open_loop_trigger="Watch for: March 15 FOMC statement",
      open_loop_series="Next in Platform Power series: Google's antitrust ruling",
      ...
  )
"""

from __future__ import annotations
import json
import os


# ---------------------------------------------------------------------------
# Taxonomy lookup (slug resolution from tag name)
# ---------------------------------------------------------------------------

_TAXONOMY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nowpattern_taxonomy.json")
_TAXONOMY_CACHE: dict | None = None


def _load_taxonomy() -> dict:
    """Load taxonomy.json and build name→slug lookup tables + translation tables."""
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is not None:
        return _TAXONOMY_CACHE

    lookup = {"genre": {}, "event": {}, "dynamics": {}}
    # Bidirectional translation: en↔ja for all 3 layers
    translate = {"en_to_ja": {}, "ja_to_en": {}}
    try:
        with open(_TAXONOMY_PATH, encoding="utf-8") as f:
            tax = json.load(f)
        for g in tax.get("genres", []):
            lookup["genre"][g["name_ja"]] = g["slug"]
            lookup["genre"][g["name_en"]] = g["slug"]
            translate["en_to_ja"][g["name_en"]] = g["name_ja"]
            translate["ja_to_en"][g["name_ja"]] = g["name_en"]
        for e in tax.get("events", []):
            lookup["event"][e["name_ja"]] = e["slug"]
            lookup["event"][e["name_en"]] = e["slug"]
            translate["en_to_ja"][e["name_en"]] = e["name_ja"]
            translate["ja_to_en"][e["name_ja"]] = e["name_en"]
        for d in tax.get("dynamics", []):
            lookup["dynamics"][d["name_ja"]] = d["slug"]
            lookup["dynamics"][d["name_en"]] = d["slug"]
            translate["en_to_ja"][d["name_en"]] = d["name_ja"]
            translate["ja_to_en"][d["name_ja"]] = d["name_en"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    lookup["_translate"] = translate
    _TAXONOMY_CACHE = lookup
    return lookup


def _localize_tag(name: str, language: str) -> str:
    """Translate a tag name to the target language using taxonomy.json.
    If already in target language or unknown, returns as-is."""
    lookup = _load_taxonomy()
    translate = lookup.get("_translate", {})
    if language == "ja":
        return translate.get("en_to_ja", {}).get(name, name)
    elif language == "en":
        return translate.get("ja_to_en", {}).get(name, name)
    return name


def _localize_tags_string(tags_str: str, language: str) -> str:
    """Translate a ×/comma-separated tag string to target language."""
    tags = [t.strip() for t in tags_str.replace(" × ", ",").replace("×", ",").replace("/", ",").replace("、", ",").split(",") if t.strip()]
    translated = [_localize_tag(t, language) for t in tags]
    return " × ".join(translated)


def _resolve_slug(name: str, layer: str) -> str:
    """Resolve a tag name to its taxonomy slug. Falls back to simple slugify."""
    lookup = _load_taxonomy()
    table = lookup.get(layer, {})
    if name in table:
        return table[name]
    # Fallback: simple ASCII slugify for unknown tags
    import unicodedata
    s = unicodedata.normalize("NFKC", name.lower())
    s = s.replace(" ", "-").replace("・", "-").replace("　", "-").replace("/", "-")
    s = s.replace("、", "-").replace("。", "").replace("（", "").replace("）", "")
    s = "".join(c for c in s if c.isalnum() or c in "-_")
    return s.strip("-") or "tag"


# ---------------------------------------------------------------------------
# Bilingual labels (ja / en)
# ---------------------------------------------------------------------------

_LABELS = {
    "ja": {
        "genre": "ジャンル:",
        "event": "イベント:",
        "dynamics": "力学(Nowpattern):",
        "bottom_line": "BOTTOM LINE",
        "bottom_line_pattern": "パターン:",
        "bottom_line_scenario": "基本シナリオ:",
        "bottom_line_watch": "注目:",
        "why_it_matters": "なぜ重要か:",
        "what_happened": "何が起きたか",
        "the_big_picture": "全体像",
        "between_the_lines": "行間を読む — 報道が言っていないこと",
        "now_pattern": "NOW PATTERN",
        "pattern_history": "パターン史",
        "whats_next": "今後のシナリオ",
        "open_loop_heading": "追跡ポイント",
        "open_loop_next_trigger": "次のトリガー:",
        "open_loop_series": "このパターンの続き:",
        "historical_context": "歴史的文脈",
        "stakeholder_map": "利害関係者マップ",
        "actor": "アクター",
        "public_position": "建前",
        "private_interest": "本音",
        "gains": "得るもの",
        "loses": "失うもの",
        "by_the_numbers": "データで見る構造",
        "intersection": "力学の交差点",
        "triggers_to_watch": "注目すべきトリガー",
        "structural_similarity": "今回との構造的類似点",
        "pattern_shows": "歴史が示すパターン",
        "scenario_suffix": "シナリオ",
        "probability": "確率",
        "action_implication": "投資/行動への示唆:",
        "deep_link_text": "詳細分析はこちら",
        "base_scenario": "基本シナリオ:",
        "sources": "ソース:",
        # v5.0: Delta section
        "delta_heading": "DELTA — 前回からの変化",
        "delta_prev_article": "前回の分析:",
        "delta_scenario": "シナリオ",
        "delta_prev": "前回",
        "delta_now": "今回",
        "delta_change": "変化",
        "delta_why": "なぜ変わったか:",
        "delta_chain": "このトピック{n}回目の分析",
        "delta_first": "このトピック初の分析（今後の差分の起点）",
    },
    "en": {
        "genre": "Genre:",
        "event": "Event:",
        "dynamics": "Dynamics(Nowpattern):",
        "bottom_line": "BOTTOM LINE",
        "bottom_line_pattern": "The Pattern:",
        "bottom_line_scenario": "Base case:",
        "bottom_line_watch": "Watch for:",
        "why_it_matters": "Why it matters:",
        "what_happened": "What Happened",
        "the_big_picture": "The Big Picture",
        "between_the_lines": "Between the Lines",
        "now_pattern": "NOW PATTERN",
        "pattern_history": "Pattern History",
        "whats_next": "What's Next",
        "open_loop_heading": "What to Watch Next",
        "open_loop_next_trigger": "Next trigger:",
        "open_loop_series": "Next in this series:",
        "historical_context": "Historical Context",
        "stakeholder_map": "Stakeholder Map",
        "actor": "Actor",
        "public_position": "Public Position",
        "private_interest": "Private Interest",
        "gains": "Gains",
        "loses": "Loses",
        "by_the_numbers": "By the Numbers",
        "intersection": "Intersection",
        "triggers_to_watch": "Triggers to Watch",
        "structural_similarity": "Structural similarity",
        "pattern_shows": "The Pattern History Shows",
        "scenario_suffix": "",
        "probability": "Probability",
        "action_implication": "Investment/Action Implications:",
        "deep_link_text": "Read the full analysis",
        "base_scenario": "Base case:",
        "sources": "Sources:",
        # v5.0: Delta section
        "delta_heading": "DELTA — What Changed",
        "delta_prev_article": "Previous analysis:",
        "delta_scenario": "Scenario",
        "delta_prev": "Previous",
        "delta_now": "Current",
        "delta_change": "Change",
        "delta_why": "What changed:",
        "delta_chain": "Update #{n} on this topic",
        "delta_first": "First analysis on this topic (future delta baseline)",
    },
}


def _L(key: str, language: str = "ja") -> str:
    """Get label for given language (falls back to ja)"""
    return _LABELS.get(language, _LABELS["ja"]).get(key, _LABELS["ja"].get(key, key))


# ---------------------------------------------------------------------------
# CSS class + inline style helpers (Ghost互換: 両方出力)
# ---------------------------------------------------------------------------

_STYLES = {
    "why_box": 'class="np-why-box" style="border-left: 4px solid #c9a84c; padding: 12px 16px; margin: 0 0 24px 0; background: #f8f6f0;"',
    "why_strong": 'style="color: #c9a84c;"',
    "hr": 'class="np-section-hr" style="border: none; border-top: 1px solid #e0dcd4; margin: 24px 0;"',
    "h2": 'style="font-size: 1.3em; color: #121e30; margin-top: 32px;"',
    "pattern_box": 'class="np-pattern-box" style="background: #121e30; border-radius: 8px; padding: 24px 28px; margin: 24px 0;"',
    "pattern_h2": 'style="font-size: 1.3em; color: #c9a84c; margin: 0 0 12px 0; letter-spacing: 0.1em;"',
    "pattern_tag": 'class="np-pattern-tag" style="color: #c9a84c; font-size: 1.1em; font-weight: bold; margin: 0 0 16px 0;"',
    "pattern_summary": 'class="np-pattern-summary" style="color: #e0dcd4; font-style: italic; margin: 0 0 16px 0;"',
    "pattern_body": 'class="np-pattern-body" style="color: #ffffff; line-height: 1.7;"',
    "pattern_strong": 'style="color: #c9a84c;"',
    "pattern_h3": 'style="color: #c9a84c; font-size: 1.1em; margin: 24px 0 12px 0;"',
    "pattern_quote": 'style="border-left: 3px solid #c9a84c; padding: 8px 16px; margin: 16px 0; color: #b0b0b0; font-style: italic;"',
    "footer": 'class="np-footer" style="font-size: 0.9em; color: #666; padding-top: 8px;"',
    "footer_link": 'style="color: #c9a84c;"',
    "diagram": 'class="np-diagram" style="text-align: center; margin: 24px 0;"',
    "fact_list": 'style="line-height: 1.8; padding-left: 20px;"',
    "tag_row": 'style="margin: 0 0 6px 0; font-size: 0.85em; line-height: 1.8;"',
    "tag_label": 'style="color: #888; font-size: 0.8em; margin-right: 6px;"',
    "tag_genre": 'style="color: #2563eb; font-weight: 600; margin-right: 8px; text-decoration: none;"',
    "tag_event": 'style="color: #16a34a; font-weight: 600; margin-right: 8px; text-decoration: none;"',
    "tag_dynamics": 'style="color: #FF1A75; font-weight: 600; margin-right: 8px; text-decoration: none;"',
    "stakeholder_table": 'style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.95em;"',
    "stakeholder_th": 'style="background: #121e30; color: #c9a84c; padding: 8px 12px; text-align: left; border: 1px solid #e0dcd4;"',
    "stakeholder_td": 'style="padding: 8px 12px; border: 1px solid #e0dcd4;"',
    # v4.0: Bottom Line TL;DR box
    "bottom_line_box": 'class="np-bottom-line" style="background: linear-gradient(135deg, #121e30, #1a2940); border-radius: 8px; padding: 20px 24px; margin: 0 0 24px 0; border-left: 4px solid #c9a84c;"',
    "bottom_line_h3": 'style="color: #c9a84c; font-size: 0.85em; letter-spacing: 0.15em; text-transform: uppercase; margin: 0 0 12px 0;"',
    "bottom_line_text": 'style="color: #ffffff; font-size: 1.05em; line-height: 1.6; margin: 0 0 8px 0;"',
    "bottom_line_meta": 'style="color: #b0b0b0; font-size: 0.9em; margin: 4px 0 0 0;"',
    # v4.0: Between the Lines callout
    "between_lines_box": 'class="np-between-lines" style="background: #fff8e6; border: 1px solid #f0d060; border-radius: 6px; padding: 16px 20px; margin: 24px 0;"',
    "between_lines_h3": 'style="color: #8a6d00; font-size: 0.95em; font-weight: 700; margin: 0 0 8px 0;"',
    "between_lines_text": 'style="color: #4a3d00; line-height: 1.7; margin: 0;"',
    # v4.0: Open Loop (forward-looking teaser)
    "open_loop_box": 'class="np-open-loop" style="background: #f0f4f8; border-radius: 8px; padding: 16px 20px; margin: 24px 0; border-top: 3px solid #c9a84c;"',
    "open_loop_h3": 'style="color: #121e30; font-size: 1em; margin: 0 0 8px 0;"',
    "open_loop_text": 'style="color: #333; line-height: 1.6; margin: 4px 0;"',
    "open_loop_link": 'style="color: #c9a84c; font-weight: 600;"',
    # v5.0: Delta section
    "delta_box": 'class="np-delta" style="background: linear-gradient(135deg, #0d1b2a, #1b2838); border-radius: 8px; padding: 20px 24px; margin: 0 0 24px 0; border-left: 4px solid #00d4ff;"',
    "delta_h3": 'style="color: #00d4ff; font-size: 0.85em; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 12px 0;"',
    "delta_prev_link": 'style="color: #00d4ff; text-decoration: underline;"',
    "delta_table": 'style="width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.9em;"',
    "delta_th": 'style="background: #0a1628; color: #00d4ff; padding: 6px 10px; text-align: center; border: 1px solid #1e3a5f;"',
    "delta_td": 'style="padding: 6px 10px; text-align: center; color: #e0e0e0; border: 1px solid #1e3a5f;"',
    "delta_td_up": 'style="padding: 6px 10px; text-align: center; color: #4CAF50; font-weight: bold; border: 1px solid #1e3a5f;"',
    "delta_td_down": 'style="padding: 6px 10px; text-align: center; color: #FF5252; font-weight: bold; border: 1px solid #1e3a5f;"',
    "delta_td_neutral": 'style="padding: 6px 10px; text-align: center; color: #888; border: 1px solid #1e3a5f;"',
    "delta_why_text": 'style="color: #b0c4de; line-height: 1.6; margin: 8px 0 0 0; font-size: 0.95em;"',
    "delta_chain_badge": 'style="display: inline-block; background: #00d4ff; color: #0a0a23; font-size: 0.75em; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin-left: 8px;"',
    "delta_first_badge": 'style="color: #888; font-size: 0.8em; font-style: italic; margin-top: 4px;"',
}


# ---------------------------------------------------------------------------
# Tag badge builder (plain #text style, no backgrounds)
# ---------------------------------------------------------------------------

def _build_tag_badges(genre_tags: str, event_tags: str, dynamics_tags: str, language: str = "ja") -> str:
    """3種類のタグを #テキスト形式（色付き、枠なし）で表示するHTMLを生成。
    タグ名はtaxonomy.jsonから正式slugを引く（404回避）。
    表示名はlanguageに応じて自動翻訳（EN→JA / JA→EN）。
    """
    rows = []

    genres = [g.strip() for g in genre_tags.replace("/", ",").replace("、", ",").split(",") if g.strip()]
    if genres:
        spans = "".join(f'<a href="/tag/{_resolve_slug(g, "genre")}/" {_STYLES["tag_genre"]}>#{_localize_tag(g, language)}</a>' for g in genres)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>{_L("genre", language)}</span>{spans}</div>')

    events = [e.strip() for e in event_tags.replace("/", ",").replace("、", ",").split(",") if e.strip()]
    if events:
        spans = "".join(f'<a href="/tag/{_resolve_slug(e, "event")}/" {_STYLES["tag_event"]}>#{_localize_tag(e, language)}</a>' for e in events)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>{_L("event", language)}</span>{spans}</div>')

    dynamics = [d.strip() for d in dynamics_tags.replace(" × ", ",").replace("×", ",").replace("/", ",").replace("、", ",").split(",") if d.strip()]
    if dynamics:
        spans = "".join(f'<a href="/tag/{_resolve_slug(d, "dynamics")}/" {_STYLES["tag_dynamics"]}>#{_localize_tag(d, language)}</a>' for d in dynamics)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>{_L("dynamics", language)}</span>{spans}</div>')

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# HTML builders — Delta section (v5.0)
# ---------------------------------------------------------------------------

def _build_delta_section_html(delta_data: dict | None, language: str = "ja") -> str:
    """構造化されたDeltaセクションのHTMLを生成。

    delta_data format:
    {
        "prev_article_title": "トランプ関税150日の時限爆弾",
        "prev_article_url": "https://nowpattern.com/trump-tariff-150/",
        "prev_article_date": "2026-02-21",
        "prev_scenarios": [
            {"label": "楽観", "probability": "30%"},
            {"label": "基本", "probability": "50%"},
            {"label": "悲観", "probability": "20%"},
        ],
        "current_scenarios": [
            {"label": "楽観", "probability": "35%"},
            {"label": "基本", "probability": "55%"},
            {"label": "悲観", "probability": "10%"},
        ],
        "delta_reason": "最高裁判決でX条項が無効化、悲観の前提条件が崩れた",
        "chain_count": 3,  # このトピックN回目の分析（1 = 初回）
    }

    chain_count=1 の場合は「初回分析バッジ」を表示（差分テーブルなし）。
    delta_data=None の場合は空文字を返す（セクション自体を非表示）。
    """
    if not delta_data:
        return ""

    chain_count = delta_data.get("chain_count", 1)

    # --- 初回分析（差分なし、起点バッジのみ） ---
    if chain_count <= 1 or not delta_data.get("prev_scenarios"):
        first_label = _L("delta_first", language)
        return (
            f'<div {_STYLES["delta_box"]}>'
            f'<p {_STYLES["delta_first_badge"]}>{first_label}</p>'
            f'</div>'
        )

    # --- 差分あり ---
    parts = []
    heading = _L("delta_heading", language)
    chain_label = _L("delta_chain", language).format(n=chain_count)
    parts.append(
        f'<h3 {_STYLES["delta_h3"]}>{heading}'
        f'<span {_STYLES["delta_chain_badge"]}>{chain_label}</span>'
        f'</h3>'
    )

    # Previous article link
    prev_title = delta_data.get("prev_article_title", "")
    prev_url = delta_data.get("prev_article_url", "")
    prev_date = delta_data.get("prev_article_date", "")
    prev_label = _L("delta_prev_article", language)
    if prev_url:
        parts.append(
            f'<p style="color: #b0b0b0; font-size: 0.9em; margin: 0 0 8px 0;">'
            f'{prev_label} <a href="{prev_url}" {_STYLES["delta_prev_link"]}>{prev_title}</a>'
            f' ({prev_date})</p>'
        )

    # Scenario change table
    prev_scenarios = delta_data.get("prev_scenarios", [])
    curr_scenarios = delta_data.get("current_scenarios", [])

    if prev_scenarios and curr_scenarios:
        lbl_sc = _L("delta_scenario", language)
        lbl_prev = _L("delta_prev", language)
        lbl_now = _L("delta_now", language)
        lbl_chg = _L("delta_change", language)

        table_rows = []
        for prev_s, curr_s in zip(prev_scenarios, curr_scenarios):
            label = prev_s.get("label", "")
            prev_prob = prev_s.get("probability", "")
            curr_prob = curr_s.get("probability", "")

            # Calculate delta (handle both "30%" and "0.30" formats)
            try:
                pv = float(str(prev_prob).replace("%", ""))
                cv = float(str(curr_prob).replace("%", ""))
                # Normalize to percentage if needed
                if pv <= 1 and cv <= 1:
                    pv *= 100
                    cv *= 100
                diff = cv - pv
                if diff > 0:
                    delta_str = f"▲ +{diff:.0f}pp"
                    td_style = _STYLES["delta_td_up"]
                elif diff < 0:
                    delta_str = f"▼ {diff:.0f}pp"
                    td_style = _STYLES["delta_td_down"]
                else:
                    delta_str = "— 0pp"
                    td_style = _STYLES["delta_td_neutral"]
            except (ValueError, TypeError):
                delta_str = "—"
                td_style = _STYLES["delta_td_neutral"]

            # Ensure display as percentage
            prev_disp = f"{prev_prob}" if "%" in str(prev_prob) else f"{prev_prob}%"
            curr_disp = f"{curr_prob}" if "%" in str(curr_prob) else f"{curr_prob}%"

            table_rows.append(
                f'<tr>'
                f'<td {_STYLES["delta_td"]}>{label}</td>'
                f'<td {_STYLES["delta_td"]}>{prev_disp}</td>'
                f'<td {_STYLES["delta_td"]}>{curr_disp}</td>'
                f'<td {td_style}>{delta_str}</td>'
                f'</tr>'
            )

        parts.append(
            f'<table {_STYLES["delta_table"]}>'
            f'<thead><tr>'
            f'<th {_STYLES["delta_th"]}>{lbl_sc}</th>'
            f'<th {_STYLES["delta_th"]}>{lbl_prev}</th>'
            f'<th {_STYLES["delta_th"]}>{lbl_now}</th>'
            f'<th {_STYLES["delta_th"]}>{lbl_chg}</th>'
            f'</tr></thead>'
            f'<tbody>{"".join(table_rows)}</tbody>'
            f'</table>'
        )

    # Delta reason
    delta_reason = delta_data.get("delta_reason", "")
    if delta_reason:
        why_label = _L("delta_why", language)
        parts.append(
            f'<p {_STYLES["delta_why_text"]}><strong style="color: #00d4ff;">{why_label}</strong> {delta_reason}</p>'
        )

    return f'<div {_STYLES["delta_box"]}>{"".join(parts)}</div>'


# ---------------------------------------------------------------------------
# HTML builders — Deep Pattern sections
# ---------------------------------------------------------------------------

def _build_facts_html(facts: list[tuple[str, str]]) -> str:
    """事実セクションのHTMLを生成（Semafor THE NEWS式）"""
    items = []
    for bold_part, detail in facts:
        items.append(f'<li><strong>{bold_part}</strong> \u2014 {detail}</li>')
    return f'<ul {_STYLES["fact_list"]}>{"".join(items)}</ul>'


def _build_stakeholder_html(stakeholder_map: list[tuple[str, str, str, str, str]], language: str = "ja") -> str:
    """利害関係者マップのHTMLテーブルを生成"""
    if not stakeholder_map:
        return ""
    rows = []
    for actor, public_pos, private_int, gains, loses in stakeholder_map:
        rows.append(
            f'<tr>'
            f'<td {_STYLES["stakeholder_td"]}><strong>{actor}</strong></td>'
            f'<td {_STYLES["stakeholder_td"]}>{public_pos}</td>'
            f'<td {_STYLES["stakeholder_td"]}>{private_int}</td>'
            f'<td {_STYLES["stakeholder_td"]}>{gains}</td>'
            f'<td {_STYLES["stakeholder_td"]}>{loses}</td>'
            f'</tr>'
        )
    return (
        f'<table {_STYLES["stakeholder_table"]}>'
        f'<tr>'
        f'<th {_STYLES["stakeholder_th"]}>{_L("actor", language)}</th>'
        f'<th {_STYLES["stakeholder_th"]}>{_L("public_position", language)}</th>'
        f'<th {_STYLES["stakeholder_th"]}>{_L("private_interest", language)}</th>'
        f'<th {_STYLES["stakeholder_th"]}>{_L("gains", language)}</th>'
        f'<th {_STYLES["stakeholder_th"]}>{_L("loses", language)}</th>'
        f'</tr>'
        f'{"".join(rows)}'
        f'</table>'
    )


def _build_data_points_html(data_points: list[tuple[str, str]]) -> str:
    """データポイントのHTMLを生成（Axios By the numbers式）"""
    if not data_points:
        return ""
    items = []
    for number, meaning in data_points:
        items.append(f'<li><strong>{number}</strong> \u2014 {meaning}</li>')
    return f'<ul {_STYLES["fact_list"]}>{"".join(items)}</ul>'


def _build_dynamics_section_html(dynamics_sections: list[dict], dynamics_intersection: str, language: str = "ja") -> str:
    """NOW PATTERNの力学分析セクションHTMLを生成（Stratechery引用→分析パターン）"""
    parts = []
    for section in dynamics_sections:
        tag = section.get("tag", "")
        subheader = section.get("subheader", "")
        # "explanation" キーも "lead" として扱う（後方互換）
        explanation = section.get("explanation", "")
        lead = section.get("lead", explanation)
        quotes = section.get("quotes", [])
        analysis = section.get("analysis", "")

        if subheader:
            parts.append(f'<h3 {_STYLES["pattern_h3"]}>{tag}: {subheader}</h3>')
        else:
            parts.append(f'<h3 {_STYLES["pattern_h3"]}>{tag}</h3>')
        if lead:
            parts.append(f'<p style="color: #ffffff; line-height: 1.7;">{lead}</p>')

        for quote_text, quote_source in quotes:
            parts.append(
                f'<blockquote {_STYLES["pattern_quote"]}>'
                f'{quote_text}<br>'
                f'<span style="color: #888; font-size: 0.9em;">\u2014 {quote_source}</span>'
                f'</blockquote>'
            )

        if analysis:
            for para in analysis.split("\n\n"):
                if para.strip():
                    parts.append(f'<p style="color: #ffffff; line-height: 1.7;">{para.strip()}</p>')

    if dynamics_intersection:
        parts.append(f'<h3 {_STYLES["pattern_h3"]}>{_L("intersection", language)}</h3>')
        for para in dynamics_intersection.split("\n\n"):
            if para.strip():
                parts.append(f'<p style="color: #ffffff; line-height: 1.7;">{para.strip()}</p>')

    return "\n".join(parts)


def _build_pattern_history_html(pattern_history: list[dict], history_pattern_summary: str, language: str = "ja") -> str:
    """歴史的並行事例セクションのHTMLを生成"""
    if not pattern_history:
        return ""
    parts = []
    for case in pattern_history:
        year = case.get("year", "")
        title = case.get("title", "")
        content = case.get("content", "")
        similarity = case.get("similarity", "")
        if language == "ja":
            parts.append(f'<h3 {_STYLES["h2"]}>{year}年: {title}</h3>')
        else:
            parts.append(f'<h3 {_STYLES["h2"]}>{year}: {title}</h3>')
        for para in content.split("\n\n"):
            if para.strip():
                parts.append(f'<p>{para.strip()}</p>')
        if similarity:
            parts.append(f'<p><em>{_L("structural_similarity", language)}: {similarity}</em></p>')

    if history_pattern_summary:
        parts.append(f'<h3 {_STYLES["h2"]}>{_L("pattern_shows", language)}</h3>')
        for para in history_pattern_summary.split("\n\n"):
            if para.strip():
                parts.append(f'<p>{para.strip()}</p>')

    return "\n".join(parts)


def _build_scenarios_html(scenarios: list, triggers: list[tuple[str, str]] | None = None, language: str = "ja") -> str:
    """What's NextセクションのHTMLを生成（Axios式拡張: 確率+示唆+トリガー）
    scenariosはtupleまたはdict形式の両方に対応:
    - tuple: (label, probability, content, action)
    - dict: {"label": ..., "probability": ..., "title": ..., "content": ..., "action": ...}
    """
    parts = []
    scenario_suffix = _L("scenario_suffix", language)
    prob_label = _L("probability", language)
    action_label = _L("action_implication", language)

    for scenario in scenarios:
        if isinstance(scenario, dict):
            label = scenario.get("label", "")
            probability = scenario.get("probability", "")
            title = scenario.get("title", "")
            content = scenario.get("content", "")
            action = scenario.get("action", "")
        else:
            label, probability, content, action = scenario
            title = ""

        if title:
            heading = f"{label} — {title}"
        elif scenario_suffix and scenario_suffix not in label:
            heading = f"{label}{scenario_suffix}"
        else:
            heading = label

        parts.append(
            f'<h3 {_STYLES["h2"]}>{heading}（{prob_label}: {probability}）</h3>'
            f'<p>{content}</p>'
        )
        if action:
            parts.append(f'<p><strong>{action_label}</strong> {action}</p>')

    if triggers:
        parts.append(f'<h3 {_STYLES["h2"]}>{_L("triggers_to_watch", language)}</h3>')
        items = []
        for trigger_name, trigger_detail in triggers:
            items.append(f'<li><strong>{trigger_name}</strong>: {trigger_detail}</li>')
        parts.append(f'<ul {_STYLES["fact_list"]}>{"".join(items)}</ul>')

    return "\n".join(parts)


def _build_sources_html(source_urls: list[tuple[str, str]], language: str = "ja") -> str:
    """ソース一覧のHTMLを生成"""
    if not source_urls:
        return ""
    items = []
    for title, url in source_urls:
        items.append(f'<li><a href="{url}" {_STYLES["footer_link"]}>{title}</a></li>')
    lbl = _L("sources", language)
    return f'<p><strong>{lbl}</strong></p><ul>{"".join(items)}</ul>'


def _build_related_html(related_articles: list[tuple[str, str]]) -> str:
    """関連記事リンクのHTMLを生成（Stratechery式自己参照）"""
    if not related_articles:
        return ""
    links = []
    for title, url in related_articles:
        links.append(f'<a href="{url}" {_STYLES["footer_link"]}>{title}</a>')
    return f'<p><strong>Related patterns:</strong> {" | ".join(links)}</p>'


# ---------------------------------------------------------------------------
# Deep Pattern HTML builder (6,000-7,000語)
# ---------------------------------------------------------------------------

def build_deep_pattern_html(
    title: str,
    why_it_matters: str,
    facts: list[tuple[str, str]],
    big_picture_history: str,
    stakeholder_map: list[tuple[str, str, str, str, str]] | None = None,
    data_points: list[tuple[str, str]] | None = None,
    delta: str = "",
    delta_data: dict | None = None,
    dynamics_tags: str = "",
    dynamics_summary: str = "",
    dynamics_sections: list[dict] | None = None,
    dynamics_intersection: str = "",
    pattern_history: list[dict] | None = None,
    history_pattern_summary: str = "",
    scenarios: list[tuple[str, str, str, str]] | None = None,
    triggers: list[tuple[str, str]] | None = None,
    genre_tags: str = "",
    event_tags: str = "",
    source_urls: list[tuple[str, str]] | None = None,
    related_articles: list[tuple[str, str]] | None = None,
    diagram_html: str = "",
    language: str = "ja",
    # v4.0 Flywheel additions
    bottom_line: str = "",
    bottom_line_pattern: str = "",
    bottom_line_scenario: str = "",
    bottom_line_watch: str = "",
    between_the_lines: str = "",
    open_loop_trigger: str = "",
    open_loop_series: str = "",
    prediction_id: str = "",
) -> str:
    """Deep Pattern記事のHTMLを生成する（v4.0 Flywheel Format）
    language: "ja" = 日本語見出し, "en" = 英語見出し

    v4.0 additions:
    - bottom_line: 記事冒頭のTL;DR（1-2文）
    - bottom_line_pattern: パターン名（力学タグ要約）
    - bottom_line_scenario: 基本シナリオの一文要約
    - bottom_line_watch: 次の注目ポイント
    - between_the_lines: 公式発表が「言っていないこと」（1段落）
    - open_loop_trigger: 次のトリガーイベント+日付
    - open_loop_series: このパターンの次の追跡テーマ
    - prediction_id: 予測追跡システム用ID
    """

    facts_html = _build_facts_html(facts)
    stakeholder_html = _build_stakeholder_html(stakeholder_map or [], language=language)
    data_html = _build_data_points_html(data_points or [])
    dynamics_body_html = _build_dynamics_section_html(dynamics_sections or [], dynamics_intersection, language=language)
    history_html = _build_pattern_history_html(pattern_history or [], history_pattern_summary, language=language)
    scenarios_html = _build_scenarios_html(scenarios or [], triggers, language=language)
    sources_html = _build_sources_html(source_urls or [], language=language)
    related_html = _build_related_html(related_articles or [])

    big_picture_paragraphs = ""
    for para in big_picture_history.split("\n\n"):
        if para.strip():
            big_picture_paragraphs += f"<p>{para.strip()}</p>\n"

    # --- v5.0: Structured Delta section (placed after Bottom Line) ---
    delta_section_html = _build_delta_section_html(delta_data, language=language)

    # Legacy: simple delta text (kept for backward compat, placed in Big Picture)
    delta_html = ""
    if delta and not delta_data:
        delta_html = f'<p><strong>The delta:</strong> <em>{delta}</em></p>'

    diagram_section = ""
    if diagram_html:
        diagram_section = f'<div {_STYLES["diagram"]}>{diagram_html}</div>'

    tag_badges_html = _build_tag_badges(genre_tags, event_tags, dynamics_tags, language=language)

    # Translate dynamics_tags string for NOW PATTERN section display
    dynamics_tags_display = _localize_tags_string(dynamics_tags, language) if dynamics_tags else ""

    # Labels for this language
    lbl_hist = _L("historical_context", language)
    lbl_stake = _L("stakeholder_map", language)
    lbl_data = _L("by_the_numbers", language)

    # --- v4.0: Bottom Line TL;DR ---
    bottom_line_html = ""
    if bottom_line:
        bl_parts = []
        bl_parts.append(f'<h3 {_STYLES["bottom_line_h3"]}>{_L("bottom_line", language)}</h3>')
        bl_parts.append(f'<p {_STYLES["bottom_line_text"]}>{bottom_line}</p>')
        if bottom_line_pattern:
            bl_parts.append(f'<p {_STYLES["bottom_line_meta"]}><strong {_STYLES["pattern_strong"]}>{_L("bottom_line_pattern", language)}</strong> {bottom_line_pattern}</p>')
        if bottom_line_scenario:
            bl_parts.append(f'<p {_STYLES["bottom_line_meta"]}><strong {_STYLES["pattern_strong"]}>{_L("bottom_line_scenario", language)}</strong> {bottom_line_scenario}</p>')
        if bottom_line_watch:
            bl_parts.append(f'<p {_STYLES["bottom_line_meta"]}><strong {_STYLES["pattern_strong"]}>{_L("bottom_line_watch", language)}</strong> {bottom_line_watch}</p>')
        bottom_line_html = f'<div {_STYLES["bottom_line_box"]}>{"".join(bl_parts)}</div>'

    # --- v4.0: Between the Lines ---
    between_lines_html = ""
    if between_the_lines:
        between_lines_html = (
            f'<div {_STYLES["between_lines_box"]}>'
            f'<h3 {_STYLES["between_lines_h3"]}>{_L("between_the_lines", language)}</h3>'
            f'<p {_STYLES["between_lines_text"]}>{between_the_lines}</p>'
            f'</div>'
        )

    # --- v4.0: Open Loop ---
    open_loop_html = ""
    if open_loop_trigger or open_loop_series:
        ol_parts = [f'<h3 {_STYLES["open_loop_h3"]}>{_L("open_loop_heading", language)}</h3>']
        if open_loop_trigger:
            ol_parts.append(f'<p {_STYLES["open_loop_text"]}><strong>{_L("open_loop_next_trigger", language)}</strong> {open_loop_trigger}</p>')
        if open_loop_series:
            ol_parts.append(f'<p {_STYLES["open_loop_text"]}><strong>{_L("open_loop_series", language)}</strong> {open_loop_series}</p>')
        if prediction_id:
            ol_parts.append(f'<p style="color: #888; font-size: 0.8em; margin-top: 8px;">Prediction ID: {prediction_id}</p>')
        open_loop_html = f'<div {_STYLES["open_loop_box"]}>{"".join(ol_parts)}</div>'

    # Section heading labels (language-aware)
    lbl_why = _L("why_it_matters", language)
    lbl_what = _L("what_happened", language)
    lbl_big = _L("the_big_picture", language)
    lbl_pattern = _L("now_pattern", language)
    lbl_phist = _L("pattern_history", language)
    lbl_next = _L("whats_next", language)

    template = f"""<!-- v5.0: Bottom Line TL;DR -->
{bottom_line_html}

<!-- v5.0: Delta — What Changed -->
{delta_section_html}

<!-- Tag Badges -->
<div style="margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 1px solid #e0dcd4;">
{tag_badges_html}
</div>

<!-- Why it matters -->
<blockquote {_STYLES["why_box"]}>
  <strong {_STYLES["why_strong"]}>{lbl_why}</strong> {why_it_matters}
</blockquote>

<hr {_STYLES["hr"]}>

<!-- Section 2: What happened -->
<h2 {_STYLES["h2"]}>{lbl_what}</h2>
{facts_html}

<hr {_STYLES["hr"]}>

<!-- Section 3: The Big Picture -->
<h2 {_STYLES["h2"]}>{lbl_big}</h2>

<h3 {_STYLES["h2"]}>{lbl_hist}</h3>
{big_picture_paragraphs}

{f'<h3 {_STYLES["h2"]}>{lbl_stake}</h3>' + stakeholder_html if stakeholder_html else ''}

{f'<h3 {_STYLES["h2"]}>{lbl_data}</h3>' + data_html if data_html else ''}

{delta_html}

<!-- v4.0: Between the Lines -->
{between_lines_html}

<hr {_STYLES["hr"]}>

<!-- Section 4: NOW PATTERN -->
<div {_STYLES["pattern_box"]}>
  <h2 {_STYLES["pattern_h2"]}>{lbl_pattern}</h2>
  <p {_STYLES["pattern_tag"]}>
    {dynamics_tags_display}
  </p>
  <p {_STYLES["pattern_summary"]}>
    {dynamics_summary}
  </p>
  <div {_STYLES["pattern_body"]}>
    {dynamics_body_html}
  </div>
</div>

{diagram_section}

<hr {_STYLES["hr"]}>

<!-- Section 5: Pattern History -->
<h2 {_STYLES["h2"]}>{lbl_phist}</h2>
{history_html}

<hr {_STYLES["hr"]}>

<!-- Section 6: What's Next -->
<h2 {_STYLES["h2"]}>{lbl_next}</h2>
{scenarios_html}

<!-- v4.0: Open Loop -->
{open_loop_html}

<hr {_STYLES["hr"]}>

<!-- Section 7: FOOTER -->
<div {_STYLES["footer"]}>
  {related_html}
  {sources_html}
</div>"""

    return template


# ---------------------------------------------------------------------------
# Speed Log HTML builder (200-400語)
# ---------------------------------------------------------------------------

def build_speed_log_html(
    title: str,
    why_it_matters: str,
    facts: list[tuple[str, str]],
    dynamics_tag: str = "",
    dynamics_one_liner: str = "",
    base_scenario: str = "",
    genre_tags: str = "",
    event_tags: str = "",
    source_url: str = "",
    deep_pattern_url: str = "",
    language: str = "ja",
) -> str:
    """Speed Log記事のHTMLを生成する（200-400語対応）"""

    facts_html = _build_facts_html(facts)

    deep_link = ""
    if deep_pattern_url:
        deep_link_text = _L("deep_link_text", language)
        deep_link = f'<p><strong>Deep Pattern:</strong> <a href="{deep_pattern_url}" {_STYLES["footer_link"]}>{deep_link_text}</a></p>'

    source_line = ""
    if source_url:
        source_line = f'<p><strong>Source:</strong> <a href="{source_url}" {_STYLES["footer_link"]}>{source_url}</a></p>'

    base_label = _L("base_scenario", language)

    lbl_why = _L("why_it_matters", language)
    lbl_what = _L("what_happened", language)
    lbl_pattern = _L("now_pattern", language)
    lbl_next = _L("whats_next", language)

    return f"""<!-- Why it matters -->
<blockquote {_STYLES["why_box"]}>
  <strong {_STYLES["why_strong"]}>{lbl_why}</strong> {why_it_matters}
</blockquote>

<hr {_STYLES["hr"]}>

<h2 {_STYLES["h2"]}>{lbl_what}</h2>
{facts_html}

<hr {_STYLES["hr"]}>

<div {_STYLES["pattern_box"]}>
  <h2 {_STYLES["pattern_h2"]}>{lbl_pattern}</h2>
  <p {_STYLES["pattern_tag"]}>{dynamics_tag}</p>
  <p {_STYLES["pattern_body"]}>{dynamics_one_liner}</p>
</div>

<hr {_STYLES["hr"]}>

<h2 {_STYLES["h2"]}>{lbl_next}</h2>
<p><strong>{base_label}</strong> {base_scenario}</p>

<hr {_STYLES["hr"]}>

<div {_STYLES["footer"]}>
  <p><strong>Tags:</strong> {genre_tags} / {event_tags}</p>
  {deep_link}
  {source_line}
</div>"""


# ---------------------------------------------------------------------------
# Legacy compatibility: old build_article_html maps to build_deep_pattern_html
# ---------------------------------------------------------------------------

def build_article_html(
    title: str,
    why_it_matters: str,
    facts: list[tuple[str, str]],
    big_picture: str,
    dynamics_tags: str,
    dynamics_summary: str,
    now_pattern_html: str,
    scenarios: list[tuple[str, str]],
    genre_tags: str,
    event_tags: str,
    source_url: str = "",
    related_articles: list[tuple[str, str]] | None = None,
) -> str:
    """後方互換: 旧APIから新Deep Pattern形式に変換"""
    return build_deep_pattern_html(
        title=title,
        why_it_matters=why_it_matters,
        facts=facts,
        big_picture_history=big_picture.replace("<p>", "").replace("</p>", "\n\n").replace("<strong>", "").replace("</strong>", ""),
        dynamics_tags=dynamics_tags,
        dynamics_summary=dynamics_summary,
        dynamics_sections=[{
            "tag": dynamics_tags.split(" × ")[0] if " × " in dynamics_tags else dynamics_tags,
            "subheader": "",
            "lead": "",
            "quotes": [],
            "analysis": now_pattern_html.replace("<p>", "").replace("</p>", "\n\n").replace("<strong>", "").replace("</strong>", "").replace(f"<strong style='color: #c9a84c;'>", "").replace("</strong>", ""),
        }],
        scenarios=[(label, "", content, "") for label, content in scenarios],
        genre_tags=genre_tags,
        event_tags=event_tags,
        source_urls=[("Source", source_url)] if source_url else [],
        related_articles=related_articles,
    )


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Nowpattern Article Builder v5.0 (Delta) ===")
    print("2モード制: Deep Pattern (6,000-7,000語) + Speed Log (200-400語)")
    print("language パラメータ: 'ja' (日本語見出し) / 'en' (英語見出し)")
    print()
    print("利用可能な関数:")
    print("  build_deep_pattern_html(language='en')  - Deep Pattern記事HTML生成")
    print("  build_speed_log_html(language='en')     - Speed Log記事HTML生成")
    print("  build_article_html()       - 旧API互換（Deep Patternにマップ）")
    print()
    print("Ghost投稿は nowpattern_publisher.py を使用してください。")
