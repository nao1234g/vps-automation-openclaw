"""
Nowpattern Article Builder v3.0
2モード制（Deep Pattern + Speed Log）対応 Ghost記事HTMLビルダー。

責務: HTML生成のみ。Ghost投稿・X投稿・インデックス更新は nowpattern_publisher.py が担当。

使い方:
  from nowpattern_article_builder import build_deep_pattern_html, build_speed_log_html

  # Deep Pattern（6,000-7,000語の本格分析記事）
  html = build_deep_pattern_html(
      title="EUがAppleに2兆円の制裁金を課した構造",
      why_it_matters="App Store独占の30年が終わる可能性がある。...",
      facts=[("2026年2月", "EUがAppleに18億ユーロの制裁金を正式決定"), ...],
      big_picture_history="Appleが30年間守り続けた「30%税」にEUが初めてメスを入れた。...",
      stakeholder_map=[("Apple", "イノベーション保護", "収益構造維持", "$85B/年のエコシステム", "手数料収入30%減"), ...],
      data_points=[("$85B", "App Store年間取引額"), ...],
      delta="表面上はEU vs Appleに見えるが、本質は「プラットフォーム税は誰が決めるのか」という権力の問題だ。",
      dynamics_tags="プラットフォーム支配 × 規制の捕獲",
      dynamics_summary="場を持つ者がルールを書き、規制者を取り込む構造が限界に達した。",
      dynamics_sections=[
          {
              "tag": "プラットフォーム支配",
              "subheader": "App Store税の構造",
              "lead": "Appleはアプリ配信という場を独占し...",
              "quotes": [("Appleの手数料は...", "Reuters, 2026-02-18")],
              "analysis": "この引用が示しているのは...",
          },
      ],
      dynamics_intersection="2つの力学は独立した現象ではない。...",
      pattern_history=[
          {"year": 2020, "title": "Google独禁法訴訟", "content": "DOJがGoogleを...", "similarity": "同じプラットフォーム支配の構造"},
      ],
      history_pattern_summary="歴史が示すのは...",
      scenarios=[
          ("基本シナリオ", "55-65%", "Appleが手数料を22%に引き下げ...", "手数料引き下げに備え、Apple依存度を下げるポートフォリオ構築"),
          ("楽観シナリオ", "15-25%", "各国がEUに追随し...", "規制関連銘柄への投資を検討"),
          ("悲観シナリオ", "15-25%", "Appleが上訴で勝利し...", "DMA関連の投資判断を保留"),
      ],
      triggers=[("Apple上訴判決", "2026年Q4に欧州裁判所の判断。勝敗でシナリオが確定"), ...],
      genre_tags="テクノロジー / 経済・金融",
      event_tags="司法・制裁 / 標準化・独占",
      source_urls=[("EU公式プレスリリース", "https://ec.europa.eu/..."), ...],
      related_articles=[("Google独禁法訴訟のNOW PATTERN", "https://nowpattern.com/google-antitrust/"), ...],
      diagram_html='<img src="..." alt="力学ダイアグラム">',
  )

  # Speed Log（200-400語の観測ログ）
  html = build_speed_log_html(
      title="Apple制裁金速報",
      why_it_matters="EU初のDMA制裁。",
      facts=[("EU", "Apple制裁金€1.8B"), ("Apple", "即座に上訴表明")],
      dynamics_tag="プラットフォーム支配",
      dynamics_one_liner="App Store独占にEUが初のメス。",
      base_scenario="手数料22%に引き下げ、開発者に年間$5B還元",
      genre_tags="テクノロジー",
      event_tags="司法・制裁",
      source_url="https://ec.europa.eu/...",
      deep_pattern_url="https://nowpattern.com/eu-apple-fine-structure/",
  )
"""

from __future__ import annotations


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
}


# ---------------------------------------------------------------------------
# Tag badge builder (plain #text style, no backgrounds)
# ---------------------------------------------------------------------------

def _build_tag_badges(genre_tags: str, event_tags: str, dynamics_tags: str) -> str:
    """3種類のタグを #テキスト形式（色付き、枠なし）で表示するHTMLを生成"""
    rows = []

    def slugify(name: str) -> str:
        import unicodedata
        s = unicodedata.normalize("NFKC", name.lower())
        s = s.replace(" ", "-").replace("・", "-").replace("　", "-").replace("/", "-")
        s = s.replace("、", "-").replace("。", "").replace("（", "").replace("）", "")
        s = "".join(c for c in s if c.isalnum() or c in "-_")
        return s.strip("-") or "tag"

    genres = [g.strip() for g in genre_tags.replace("/", ",").replace("、", ",").split(",") if g.strip()]
    if genres:
        spans = "".join(f'<a href="/tag/{slugify(g)}/" {_STYLES["tag_genre"]}>#{g}</a>' for g in genres)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>ジャンル:</span>{spans}</div>')

    events = [e.strip() for e in event_tags.replace("/", ",").replace("、", ",").split(",") if e.strip()]
    if events:
        spans = "".join(f'<a href="/tag/{slugify(e)}/" {_STYLES["tag_event"]}>#{e}</a>' for e in events)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>イベント:</span>{spans}</div>')

    dynamics = [d.strip() for d in dynamics_tags.replace(" × ", ",").replace("×", ",").replace("/", ",").replace("、", ",").split(",") if d.strip()]
    if dynamics:
        spans = "".join(f'<a href="/tag/{slugify(d)}/" {_STYLES["tag_dynamics"]}>#{d}</a>' for d in dynamics)
        rows.append(f'<div {_STYLES["tag_row"]}><span {_STYLES["tag_label"]}>力学:</span>{spans}</div>')

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# HTML builders — Deep Pattern sections
# ---------------------------------------------------------------------------

def _build_facts_html(facts: list[tuple[str, str]]) -> str:
    """事実セクションのHTMLを生成（Semafor THE NEWS式）"""
    items = []
    for bold_part, detail in facts:
        items.append(f'<li><strong>{bold_part}</strong> \u2014 {detail}</li>')
    return f'<ul {_STYLES["fact_list"]}>{"".join(items)}</ul>'


def _build_stakeholder_html(stakeholder_map: list[tuple[str, str, str, str, str]]) -> str:
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
        f'<th {_STYLES["stakeholder_th"]}>アクター</th>'
        f'<th {_STYLES["stakeholder_th"]}>建前</th>'
        f'<th {_STYLES["stakeholder_th"]}>本音</th>'
        f'<th {_STYLES["stakeholder_th"]}>得るもの</th>'
        f'<th {_STYLES["stakeholder_th"]}>失うもの</th>'
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


def _build_dynamics_section_html(dynamics_sections: list[dict], dynamics_intersection: str) -> str:
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
        parts.append(f'<h3 {_STYLES["pattern_h3"]}>力学の交差点</h3>')
        for para in dynamics_intersection.split("\n\n"):
            if para.strip():
                parts.append(f'<p style="color: #ffffff; line-height: 1.7;">{para.strip()}</p>')

    return "\n".join(parts)


def _build_pattern_history_html(pattern_history: list[dict], history_pattern_summary: str) -> str:
    """歴史的並行事例セクションのHTMLを生成"""
    if not pattern_history:
        return ""
    parts = []
    for case in pattern_history:
        year = case.get("year", "")
        title = case.get("title", "")
        content = case.get("content", "")
        similarity = case.get("similarity", "")
        parts.append(f'<h3 {_STYLES["h2"]}>{year}年: {title}</h3>')
        for para in content.split("\n\n"):
            if para.strip():
                parts.append(f'<p>{para.strip()}</p>')
        if similarity:
            parts.append(f'<p><em>今回との構造的類似点: {similarity}</em></p>')

    if history_pattern_summary:
        parts.append(f'<h3 {_STYLES["h2"]}>歴史が示すパターン</h3>')
        for para in history_pattern_summary.split("\n\n"):
            if para.strip():
                parts.append(f'<p>{para.strip()}</p>')

    return "\n".join(parts)


def _build_scenarios_html(scenarios: list, triggers: list[tuple[str, str]] | None = None) -> str:
    """What's NextセクションのHTMLを生成（Axios式拡張: 確率+示唆+トリガー）
    scenariosはtupleまたはdict形式の両方に対応:
    - tuple: (label, probability, content, action)
    - dict: {"label": ..., "probability": ..., "title": ..., "content": ..., "action": ...}
    """
    parts = []
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

        heading = f"{label}シナリオ" if title == "" else f"{label} — {title}"
        parts.append(
            f'<h3 {_STYLES["h2"]}>{heading}（確率: {probability}）</h3>'
            f'<p>{content}</p>'
        )
        if action:
            parts.append(f'<p><strong>投資/行動への示唆:</strong> {action}</p>')

    if triggers:
        parts.append(f'<h3 {_STYLES["h2"]}>注目すべきトリガー</h3>')
        items = []
        for trigger_name, trigger_detail in triggers:
            items.append(f'<li><strong>{trigger_name}</strong>: {trigger_detail}</li>')
        parts.append(f'<ul {_STYLES["fact_list"]}>{"".join(items)}</ul>')

    return "\n".join(parts)


def _build_sources_html(source_urls: list[tuple[str, str]]) -> str:
    """ソース一覧のHTMLを生成"""
    if not source_urls:
        return ""
    items = []
    for title, url in source_urls:
        items.append(f'<li><a href="{url}" {_STYLES["footer_link"]}>{title}</a></li>')
    return f'<p><strong>Sources:</strong></p><ul>{"".join(items)}</ul>'


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
) -> str:
    """Deep Pattern記事のHTMLを生成する（6,000-7,000語対応）"""

    facts_html = _build_facts_html(facts)
    stakeholder_html = _build_stakeholder_html(stakeholder_map or [])
    data_html = _build_data_points_html(data_points or [])
    dynamics_body_html = _build_dynamics_section_html(dynamics_sections or [], dynamics_intersection)
    history_html = _build_pattern_history_html(pattern_history or [], history_pattern_summary)
    scenarios_html = _build_scenarios_html(scenarios or [], triggers)
    sources_html = _build_sources_html(source_urls or [])
    related_html = _build_related_html(related_articles or [])

    big_picture_paragraphs = ""
    for para in big_picture_history.split("\n\n"):
        if para.strip():
            big_picture_paragraphs += f"<p>{para.strip()}</p>\n"

    delta_html = ""
    if delta:
        delta_html = f'<p><strong>The delta:</strong> <em>{delta}</em></p>'

    diagram_section = ""
    if diagram_html:
        diagram_section = f'<div {_STYLES["diagram"]}>{diagram_html}</div>'

    tag_badges_html = _build_tag_badges(genre_tags, event_tags, dynamics_tags)

    template = f"""<!-- Tag Badges -->
<div style="margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 1px solid #e0dcd4;">
{tag_badges_html}
</div>

<!-- Why it matters (Axios式) -->
<blockquote {_STYLES["why_box"]}>
  <strong {_STYLES["why_strong"]}>Why it matters:</strong> {why_it_matters}
</blockquote>

<hr {_STYLES["hr"]}>

<!-- Section 2: THE NEWS (Semafor式) -->
<h2 {_STYLES["h2"]}>What happened</h2>
{facts_html}

<hr {_STYLES["hr"]}>

<!-- Section 3: THE BIG PICTURE -->
<h2 {_STYLES["h2"]}>The Big Picture</h2>

<h3 {_STYLES["h2"]}>歴史的文脈</h3>
{big_picture_paragraphs}

{f'<h3 {_STYLES["h2"]}>利害関係者マップ</h3>' + stakeholder_html if stakeholder_html else ''}

{f'<h3 {_STYLES["h2"]}>データで見る構造</h3>' + data_html if data_html else ''}

{delta_html}

<hr {_STYLES["hr"]}>

<!-- Section 4: NOW PATTERN -->
<div {_STYLES["pattern_box"]}>
  <h2 {_STYLES["pattern_h2"]}>NOW PATTERN</h2>
  <p {_STYLES["pattern_tag"]}>
    {dynamics_tags}
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

<!-- Section 5: PATTERN HISTORY -->
<h2 {_STYLES["h2"]}>Pattern History</h2>
{history_html}

<hr {_STYLES["hr"]}>

<!-- Section 6: WHAT'S NEXT -->
<h2 {_STYLES["h2"]}>What's Next</h2>
{scenarios_html}

<hr {_STYLES["hr"]}>

<!-- Section 7: FOOTER -->
<div {_STYLES["footer"]}>
  <p><strong>Tags:</strong> {genre_tags} / {event_tags}</p>
  <p><strong>NOW PATTERN:</strong> {dynamics_tags}</p>
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
) -> str:
    """Speed Log記事のHTMLを生成する（200-400語対応）"""

    facts_html = _build_facts_html(facts)

    deep_link = ""
    if deep_pattern_url:
        deep_link = f'<p><strong>Deep Pattern:</strong> <a href="{deep_pattern_url}" {_STYLES["footer_link"]}>詳細分析はこちら</a></p>'

    source_line = ""
    if source_url:
        source_line = f'<p><strong>Source:</strong> <a href="{source_url}" {_STYLES["footer_link"]}>{source_url}</a></p>'

    return f"""<!-- Why it matters -->
<blockquote {_STYLES["why_box"]}>
  <strong {_STYLES["why_strong"]}>Why it matters:</strong> {why_it_matters}
</blockquote>

<hr {_STYLES["hr"]}>

<h2 {_STYLES["h2"]}>What happened</h2>
{facts_html}

<hr {_STYLES["hr"]}>

<div {_STYLES["pattern_box"]}>
  <h2 {_STYLES["pattern_h2"]}>NOW PATTERN</h2>
  <p {_STYLES["pattern_tag"]}>{dynamics_tag}</p>
  <p {_STYLES["pattern_body"]}>{dynamics_one_liner}</p>
</div>

<hr {_STYLES["hr"]}>

<h2 {_STYLES["h2"]}>What's Next</h2>
<p><strong>基本シナリオ:</strong> {base_scenario}</p>

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

    print("=== Nowpattern Article Builder v3.0 ===")
    print("2モード制: Deep Pattern (6,000-7,000語) + Speed Log (200-400語)")
    print()
    print("利用可能な関数:")
    print("  build_deep_pattern_html()  - Deep Pattern記事HTML生成")
    print("  build_speed_log_html()     - Speed Log記事HTML生成")
    print("  build_article_html()       - 旧API互換（Deep Patternにマップ）")
    print()
    print("Ghost投稿は nowpattern_publisher.py を使用してください。")
