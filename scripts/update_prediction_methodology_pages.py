#!/usr/bin/env python3
"""Create/update the six reader-facing prediction methodology pages.

These pages are distinct from the legacy /forecast-rules/, /scoring-guide/,
and /integrity-audit/ pages. They are source-controlled and use the current
canonical public score snapshot rather than hardcoded counts.
"""

from __future__ import annotations

import html
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_page_builder import (  # noqa: E402
    _canonical_public_stats,
    _public_score_value,
    ghost_request,
    load_env,
    load_prediction_db,
)
from prediction_state_utils import PUBLIC_STATE_MODEL_VERSION  # noqa: E402


SITE_URL = "https://nowpattern.com"
TRACKER_PATHS = {"ja": "/predictions/", "en": "/en/predictions/"}
LEGACY_PATHS = {
    "rules": {"ja": "/forecast-rules/", "en": "/en/forecast-rules/"},
    "scoring": {"ja": "/scoring-guide/", "en": "/en/scoring-guide/"},
    "audit": {"ja": "/integrity-audit/", "en": "/en/integrity-audit/"},
}
PAGE_SPECS = (
    {
        "key": "methodology",
        "lang": "ja",
        "slug": "forecasting-methodology",
        "title": "予測手法 — Nowpatternはどう予測を作るか",
        "path": "/forecasting-methodology/",
        "tags": ["nowpattern", "lang-ja", "prediction-methodology"],
    },
    {
        "key": "methodology",
        "lang": "en",
        "slug": "en-forecasting-methodology",
        "title": "Forecasting Methodology — How Nowpattern Builds Forecasts",
        "path": "/en/forecasting-methodology/",
        "tags": ["nowpattern", "lang-en", "prediction-methodology"],
    },
    {
        "key": "scoring",
        "lang": "ja",
        "slug": "forecast-scoring-and-resolution",
        "title": "採点と判定 — Brier Scoreと解決プロセス",
        "path": "/forecast-scoring-and-resolution/",
        "tags": ["nowpattern", "lang-ja", "prediction-methodology"],
    },
    {
        "key": "scoring",
        "lang": "en",
        "slug": "en-forecast-scoring-and-resolution",
        "title": "Scoring and Resolution — Brier Score and Outcome Rules",
        "path": "/en/forecast-scoring-and-resolution/",
        "tags": ["nowpattern", "lang-en", "prediction-methodology"],
    },
    {
        "key": "integrity",
        "lang": "ja",
        "slug": "forecast-integrity-and-audit",
        "title": "予測整合性と監査 — 改ざん耐性と限界",
        "path": "/forecast-integrity-and-audit/",
        "tags": ["nowpattern", "lang-ja", "prediction-methodology"],
    },
    {
        "key": "integrity",
        "lang": "en",
        "slug": "en-forecast-integrity-and-audit",
        "title": "Forecast Integrity and Audit — Tamper Resistance and Limits",
        "path": "/en/forecast-integrity-and-audit/",
        "tags": ["nowpattern", "lang-en", "prediction-methodology"],
    },
)


def _canonical_url(path: str) -> str:
    return f"{SITE_URL}{path}"


def _pair_path(path: str, lang: str) -> str:
    if lang == "ja":
        return "/en" + path if not path.startswith("/en/") else path
    if path.startswith("/en/"):
        return path[3:]
    return path


def _hreflang_head(path: str, lang: str) -> str:
    ja_path = path if lang == "ja" else _pair_path(path, lang)
    en_path = _pair_path(path, "ja") if lang == "ja" else path
    return (
        f'<link rel="canonical" href="{_canonical_url(path)}" />\n'
        f'<link rel="alternate" hreflang="ja" href="{_canonical_url(ja_path)}" />\n'
        f'<link rel="alternate" hreflang="en" href="{_canonical_url(en_path)}" />\n'
        f'<link rel="alternate" hreflang="x-default" href="{_canonical_url(ja_path)}" />'
    )


def _snapshot() -> dict[str, object]:
    pred_db = load_prediction_db()
    stats = _canonical_public_stats(pred_db)
    return {
        "total": int(stats["total"]),
        "resolved": int(stats["resolved"]),
        "scorable": int(stats["scorable"]),
        "not_scorable": int(stats["not_scorable"]),
        "binary_hit": int(stats["accuracy_binary_hit"]),
        "binary_miss": int(stats["accuracy_binary_miss"]),
        "binary_n": int(stats["accuracy_binary_n"]),
        "accuracy_pct": float(stats["accuracy_pct"]),
        "avg_brier": float(stats["public_brier_avg"] or 0.0),
        "public_index": float(_public_score_value(stats["public_brier_avg"]) or 0.0),
        "score_tier": str(stats["public_score_tier"]),
        "last_updated": str(stats["last_updated"]),
    }


def _metric_strip(snapshot: dict[str, object], lang: str) -> str:
    if lang == "ja":
        labels = (
            ("登録予測", snapshot["total"]),
            ("解決済", snapshot["resolved"]),
            ("公開採点", snapshot["scorable"]),
            ("Brier Index", f'{snapshot["public_index"]:.1f}%'),
        )
    else:
        labels = (
            ("Registered forecasts", snapshot["total"]),
            ("Resolved", snapshot["resolved"]),
            ("Publicly scored", snapshot["scorable"]),
            ("Brier Index", f'{snapshot["public_index"]:.1f}%'),
        )
    items = "".join(
        '<div style="border:1px solid #E2E8F0;border-radius:16px;padding:14px 16px;background:#fff">'
        f'<div style="font-size:1.45em;font-weight:800;color:#0F172A">{html.escape(str(value))}</div>'
        f'<div style="font-size:0.8em;color:#64748B;margin-top:4px">{html.escape(label)}</div>'
        '</div>'
        for label, value in labels
    )
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;'
        'margin:20px 0 24px">'
        f"{items}"
        "</div>"
    )


def _note_box(text: str, tone: str = "info") -> str:
    palette = {
        "info": ("#EFF6FF", "#1D4ED8", "#BFDBFE"),
        "warn": ("#FFF7ED", "#C2410C", "#FED7AA"),
        "muted": ("#F8FAFC", "#475569", "#CBD5E1"),
    }
    bg, fg, border = palette[tone]
    return (
        f'<div style="background:{bg};border:1px solid {border};color:{fg};'
        'border-radius:14px;padding:16px 18px;line-height:1.75;margin:18px 0">'
        f"{text}"
        "</div>"
    )


def _link_row(lang: str) -> str:
    links = (
        (("予測トラッカー", TRACKER_PATHS["ja"]), ("既存ルール", LEGACY_PATHS["rules"]["ja"]), ("既存ガイド", LEGACY_PATHS["scoring"]["ja"]))
        if lang == "ja"
        else (("Prediction Tracker", TRACKER_PATHS["en"]), ("Legacy Rules", LEGACY_PATHS["rules"]["en"]), ("Legacy Guide", LEGACY_PATHS["scoring"]["en"]))
    )
    return '<p>' + " | ".join(f'<a href="{href}">{label}</a>' for label, href in links) + "</p>"


def build_methodology_html(lang: str, snapshot: dict[str, object]) -> str:
    if lang == "ja":
        intro = (
            "<h2>なぜ予測プラットフォームなのか</h2>"
            "<p>Nowpatternは分析で終わらず、問い・確率・判定基準・判定記録を一つの公開系でつなぐために予測トラッカーを運用しています。"
            "現在の公開面では <strong>{total}</strong> 件を登録し、そのうち <strong>{resolved}</strong> 件を解決済みとして示しています。</p>"
        ).format(**snapshot)
        requirements = (
            "<h2>有効な予測に必要な5条件</h2>"
            "<ol>"
            "<li>後から第三者が読める判定質問であること</li>"
            "<li>初期確率を固定し、後から採点式に使う値を差し替えないこと</li>"
            "<li>判定期限と外部参照先が明示されていること</li>"
            "<li>的中も外れも公開面に残ること</li>"
            "<li>採点対象外を除外理由つきで示すこと</li>"
            "</ol>"
        )
        categories = (
            "<h2>カテゴリ別の予測手法</h2>"
            "<p>地政学は政策転換点と市場の反応、経済は制度変更と波及経路、テクノロジーはプロダクト出荷・規制・採用速度を重視します。"
            "どのカテゴリでも、最初に解像度の高い判定質問を決め、そのあとに確率を置く順番を守ります。</p>"
        )
        evolution = (
            "<h2>改善サイクル</h2>"
            "<p>公開スコアは EvolutionLoop の入力でもあります。低確率HITや高確率MISSがどこに偏っているかを見て、"
            "カテゴリ別にキャリブレーションを補正します。今の公開 Brier Index は <strong>{public_index:.1f}%</strong>、"
            "raw Brier は <strong>{avg_brier:.4f}</strong> です。</p>"
        ).format(**snapshot)
        comparison = (
            "<h2>外部比較の考え方</h2>"
            "<p>Metaculus や Good Judgment のような優れた予測コミュニティと比べて、Nowpattern はまだ track record の積み上げ段階です。"
            "だから総件数よりも、公開採点 <strong>{scorable}</strong> 件の質と増え方を重視します。</p>"
        ).format(**snapshot)
        note = _note_box(
            "ここで見るべきKPIは総予測数ではなく、公開採点に到達した件数とその精度です。"
            "総数が大きくても、採点済みが薄ければ moat にはなりません。",
            tone="info",
        )
    else:
        intro = (
            "<h2>Why a forecasting platform?</h2>"
            "<p>Nowpattern is designed to keep the question, probability, resolution rule, and public result in one visible system."
            " The public tracker currently carries <strong>{total}</strong> registered forecasts, of which <strong>{resolved}</strong> are resolved.</p>"
        ).format(**snapshot)
        requirements = (
            "<h2>The five requirements for a valid forecast</h2>"
            "<ol>"
            "<li>A resolution question that an outside reader can judge later</li>"
            "<li>A locked initial probability that is not swapped after the fact</li>"
            "<li>A visible deadline and external resolution source</li>"
            "<li>Hits and misses both remain on the public surface</li>"
            "<li>Non-scorable cases are excluded with an explicit reason</li>"
            "</ol>"
        )
        categories = (
            "<h2>Methodology by category</h2>"
            "<p>Geopolitics emphasizes regime incentives and market reaction, economics emphasizes policy transmission, and technology emphasizes shipping, regulation, and adoption speed."
            " Across categories, the judgment question comes first and probability comes second.</p>"
        )
        evolution = (
            "<h2>How the loop improves</h2>"
            "<p>The public score is an EvolutionLoop input. We watch where low-probability hits and high-confidence misses cluster, then adjust calibration by category."
            " The current public Brier Index is <strong>{public_index:.1f}%</strong>, from a raw Brier average of <strong>{avg_brier:.4f}</strong>.</p>"
        ).format(**snapshot)
        comparison = (
            "<h2>How to compare us externally</h2>"
            "<p>Compared with mature forecasting communities, Nowpattern is still in the corpus-building phase."
            " That is why the important moat number is not total forecasts, but the <strong>{scorable}</strong> publicly scored cases and how that sample grows.</p>"
        ).format(**snapshot)
        note = _note_box(
            "The honest KPI here is not total predictions. It is the size and quality of the publicly scored sample.",
            tone="info",
        )

    return _metric_strip(snapshot, lang) + intro + note + requirements + categories + evolution + comparison + _link_row(lang)


def build_scoring_html(lang: str, snapshot: dict[str, object]) -> str:
    if lang == "ja":
        intro = (
            "<h2>ブライアスコアとは</h2>"
            "<p>Nowpattern は内部の raw Brier を保持しつつ、公開面では理解しやすい Brier Index を表示します。"
            "現在の公開採点は <strong>{scorable}</strong> 件、二値判定のサンプルは <strong>{binary_n}</strong> 件です。</p>"
        ).format(**snapshot)
        formula = (
            "<h2>計算式</h2>"
            "<pre><code>BS = (initial_prob / 100 - actual_outcome)^2</code></pre>"
            "<p>HIT なら outcome=1、MISS なら outcome=0 です。公開 Brier Index は <code>(1 - sqrt(Brier)) * 100</code> で表示します。</p>"
            "<ul>"
            "<li>NP-2026-0001 が 75% で HIT → 0.0625</li>"
            "<li>NP-2026-0001 が 75% で MISS → 0.5625</li>"
            "<li>NP-2026-0921 が 11% で HIT → 0.7921</li>"
            "</ul>"
        )
        process = (
            "<h2>解決プロセス</h2>"
            "<ol>"
            "<li>予測はまず event pending として公開されます</li>"
            "<li>期限通過後は awaiting evidence に移ります</li>"
            "<li>客観証拠が揃うと verdict を HIT / MISS / NOT_SCORED に固定します</li>"
            "<li>公開面では Binary Judged Accuracy と Public Brier Index を別々に見せます</li>"
            "</ol>"
        )
        tiers = (
            "<h2>スコアの精度ティア</h2>"
            "<p>現在の公開ティアは <strong>{score_tier}</strong> です。これは「スコアがある」ことと「完全証跡がある」ことを分けて表示するためです。</p>"
        ).format(**snapshot)
        disclosure = _note_box(
            "現在のすべての予測スコアは暫定計算値です。ブロックチェーン確認待ちのため。"
            " Binary Accuracy は {hit} hit / {miss} miss / n={n}、Public Brier Index は {index:.1f}% "
            "(raw Brier {brier:.4f} / n={scorable}) で計算しています。".format(
                hit=snapshot["binary_hit"],
                miss=snapshot["binary_miss"],
                n=snapshot["binary_n"],
                index=snapshot["public_index"],
                brier=snapshot["avg_brier"],
                scorable=snapshot["scorable"],
            ),
            tone="warn",
        )
    else:
        intro = (
            "<h2>What is a Brier Score?</h2>"
            "<p>Nowpattern keeps the raw Brier value internally and shows a reader-facing Brier Index publicly."
            " The current public sample is <strong>{scorable}</strong> scored forecasts, with a binary judged sample of <strong>{binary_n}</strong>.</p>"
        ).format(**snapshot)
        formula = (
            "<h2>Formula</h2>"
            "<pre><code>BS = (initial_prob / 100 - actual_outcome)^2</code></pre>"
            "<p>For HIT, outcome=1. For MISS, outcome=0. The public Brier Index is shown as <code>(1 - sqrt(Brier)) * 100</code>.</p>"
            "<ul>"
            "<li>NP-2026-0001 at 75% and HIT → 0.0625</li>"
            "<li>NP-2026-0001 at 75% and MISS → 0.5625</li>"
            "<li>NP-2026-0921 at 11% and HIT → 0.7921</li>"
            "</ul>"
        )
        process = (
            "<h2>Resolution process</h2>"
            "<ol>"
            "<li>A forecast starts in an event-pending state</li>"
            "<li>After the deadline passes, it moves to awaiting evidence</li>"
            "<li>Once objective evidence is available, the verdict is locked as HIT, MISS, or NOT_SCORED</li>"
            "<li>Public pages separate Binary Judged Accuracy from Public Brier Index</li>"
            "</ol>"
        )
        tiers = (
            "<h2>Score provenance tiers</h2>"
            "<p>The current public tier is <strong>{score_tier}</strong>. This is how we separate “a score exists” from “the strongest proof chain exists.”</p>"
        ).format(**snapshot)
        disclosure = _note_box(
            "All current prediction scores are provisional pending blockchain timestamp confirmation. "
            "Binary Accuracy is {hit} hit / {miss} miss / n={n}. Public Brier Index is {index:.1f}% "
            "(raw Brier {brier:.4f} / n={scorable}).".format(
                hit=snapshot["binary_hit"],
                miss=snapshot["binary_miss"],
                n=snapshot["binary_n"],
                index=snapshot["public_index"],
                brier=snapshot["avg_brier"],
                scorable=snapshot["scorable"],
            ),
            tone="warn",
        )

    tracker_link = PUBLIC_STATE_MODEL_VERSION
    if lang == "ja":
        footer = (
            f"<p>公開表示は {html.escape(str(tracker_link))} の状態モデルに基づき、event pending / awaiting evidence / resolved を分離しています。"
            f" 詳細な公開面は <a href=\"{TRACKER_PATHS['ja']}\">予測トラッカー</a> と <a href=\"/forecast-integrity-and-audit/\">整合性・監査</a> を参照してください。</p>"
        )
    else:
        footer = (
            f"<p>The public surface is rendered from the {html.escape(str(tracker_link))} state model, which separates event pending, awaiting evidence, and resolved states."
            f" See the <a href=\"{TRACKER_PATHS['en']}\">prediction tracker</a> and <a href=\"/en/forecast-integrity-and-audit/\">integrity page</a> for the live surface.</p>"
        )
    return _metric_strip(snapshot, lang) + intro + disclosure + formula + process + tiers + footer


def build_integrity_html(lang: str, snapshot: dict[str, object]) -> str:
    if lang == "ja":
        intro = (
            "<h2>誠実性の誓い</h2>"
            "<p>Nowpattern は的中だけでなく外れも残し、採点対象外も理由つきで公開します。"
            " 現在の公開状態は resolved={resolved} / publicly scorable={scorable} / excluded={not_scorable} です。</p>"
        ).format(**snapshot)
        mechanisms = (
            "<h2>改ざん防止の仕組み</h2>"
            "<ol>"
            "<li><strong>initial_prob write-once</strong> — 採点に使う初期確率は publish 後に差し替えない</li>"
            "<li><strong>prediction ledger</strong> — 追記型イベント列で登録・解決を残す</li>"
            "<li><strong>integrity hash / OTS</strong> — より強い証跡へ段階的に昇格させる</li>"
            "</ol>"
        )
        limitations = _note_box(
            "現在の予測スコアは、2026年3月29日の後付けバックフィルに基づいています。"
            " そのため公開ティアは PROVISIONAL が中心です。証跡が十分なものだけを MIGRATED_OFFICIAL / VERIFIED_OFFICIAL に昇格させます。",
            tone="warn",
        )
        verification = (
            "<h2>読者が自分で確かめる方法</h2>"
            "<p>各カードの score disclaimer、resolution evidence、公開 Brier sample を見れば、"
            "何が採点対象で何が除外かを追えます。旧 overview は <a href=\"/integrity-audit/\">整合性・監査</a> に残し、"
            "このページではより技術的な監査導線をまとめています。</p>"
        )
    else:
        intro = (
            "<h2>Integrity pledge</h2>"
            "<p>Nowpattern keeps hits, misses, and excluded cases visible. The current public state is "
            "resolved={resolved}, publicly scorable={scorable}, excluded={not_scorable}.</p>"
        ).format(**snapshot)
        mechanisms = (
            "<h2>Anti-tampering mechanisms</h2>"
            "<ol>"
            "<li><strong>initial_prob write-once</strong> — the probability used for scoring is not swapped after publication</li>"
            "<li><strong>prediction ledger</strong> — append-only event records preserve registration and resolution flow</li>"
            "<li><strong>integrity hash / OTS</strong> — stronger evidence tiers are earned, not assumed</li>"
            "</ol>"
        )
        limitations = _note_box(
            "Current prediction scores are based on a 2026-03-29 backfill of legacy records. "
            "That is why PROVISIONAL remains the dominant public tier until stronger timestamp proofs are attached.",
            tone="warn",
        )
        verification = (
            "<h2>How readers can verify independently</h2>"
            "<p>Use the score disclaimer, resolution evidence, and public Brier sample on each card to see what is scored and what is excluded."
            " The legacy overview remains at <a href=\"/en/integrity-audit/\">Integrity &amp; Audit</a>; this page is the deeper technical path.</p>"
        )

    state_model = (
        "<h2>Public state model</h2>"
        f"<p>The current reader-facing state contract version is <code>{html.escape(PUBLIC_STATE_MODEL_VERSION)}</code>. "
        "It splits forecast lifecycle, resolution lifecycle, and language-specific publication state so that counts and meaning stay aligned.</p>"
    )
    return _metric_strip(snapshot, lang) + intro + mechanisms + limitations + state_model + verification + _link_row(lang)


def _page_html(spec: dict[str, object], snapshot: dict[str, object]) -> str:
    lang = str(spec["lang"])
    builders = {
        "methodology": build_methodology_html,
        "scoring": build_scoring_html,
        "integrity": build_integrity_html,
    }
    body = builders[str(spec["key"])](lang, snapshot)
    return (
        '<div style="max-width:860px;margin:0 auto;padding:8px 0 28px">'
        '<div style="background:linear-gradient(135deg,#fffaf0 0%,#f8fafc 100%);border:1px solid #E5E7EB;'
        'border-radius:18px;padding:28px 24px;box-shadow:0 10px 28px rgba(15,23,42,.06);margin-bottom:18px">'
        '<div style="font-size:0.78em;letter-spacing:.08em;text-transform:uppercase;color:#64748B;font-weight:700">Nowpattern</div>'
        f'<h2 style="font-size:2em;line-height:1.15;margin:8px 0 10px;color:#111827">{html.escape(str(spec["title"]))}</h2>'
        '<p style="margin:0;color:#475569;line-height:1.7;font-size:1em">'
        + (
            "公開スコア・判定・整合性を別々に説明する reader-facing methodology page です。"
            if lang == "ja"
            else "A reader-facing methodology page that separates scoring, resolution, and integrity."
        )
        + '</p></div>'
        '<div style="background:#fff;border:1px solid #E5E7EB;border-radius:18px;padding:28px 24px;'
        'box-shadow:0 10px 28px rgba(15,23,42,.04);line-height:1.85;color:#1f2937">'
        f"{body}"
        "</div></div>"
    )


def _fetch_page(api_key: str, slug: str) -> dict | None:
    try:
        result = ghost_request("GET", f"/pages/slug/{slug}/?formats=html", api_key)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    pages = result.get("pages") or []
    return pages[0] if pages else None


def _upsert_page(api_key: str, spec: dict[str, object], snapshot: dict[str, object]) -> None:
    path = str(spec["path"])
    html_body = _page_html(spec, snapshot)
    payload_page = {
        "title": spec["title"],
        "slug": spec["slug"],
        "status": "published",
        "html": html_body,
        "tags": [{"name": tag} for tag in spec["tags"]],
        "canonical_url": _canonical_url(path),
        "codeinjection_head": _hreflang_head(path, str(spec["lang"])),
    }
    current = _fetch_page(api_key, str(spec["slug"]))
    if current:
        payload_page["updated_at"] = current["updated_at"]
        ghost_request(
            "PUT",
            f"/pages/{current['id']}/?source=html",
            api_key,
            {"pages": [payload_page]},
        )
        print(f"Updated {path}")
        return
    ghost_request(
        "POST",
        "/pages/?source=html",
        api_key,
        {"pages": [payload_page]},
    )
    print(f"Created {path}")


def main() -> int:
    env = load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        return 1

    snapshot = _snapshot()
    print(json.dumps({"snapshot": snapshot}, ensure_ascii=False))
    for spec in PAGE_SPECS:
        _upsert_page(api_key, spec, snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
