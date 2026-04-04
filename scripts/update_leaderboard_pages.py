#!/usr/bin/env python3
"""Source-controlled updater for /leaderboard/ and /en/leaderboard/ Ghost pages."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_page_builder import load_env, update_ghost_page  # noqa: E402


def _copy(lang: str) -> dict[str, str]:
    if lang == "ja":
        return {
            "title": "AI Benchmark Leaderboard",
            "subtitle": "AIの公開成績を基準に置きつつ、人間ランキングは十分なサンプル到達後に公開します。",
            "cta_title": "参加する",
            "cta_loading": "参加条件を読み込み中...",
            "cta_beta": (
                '<a href="https://nowpattern.com/predictions/" style="color:#2563eb;font-weight:700">'
                "予測一覧ページ</a>から参加できます。人間ランキングは "
                "{voters}人 / {votes}票 / {resolved}解決票 に達するまで beta 表示です。"
            ),
            "cta_live": (
                '<a href="https://nowpattern.com/predictions/" style="color:#2563eb;font-weight:700">'
                "予測一覧ページ</a>から参加できます。ランキング掲載には各予測者ごとに "
                "{min_resolved} 件以上の解決済み予測が必要です。"
            ),
            "loading": "ランキングを読み込み中...",
            "load_failed": "ランキングを読み込めませんでした。少し待ってから再試行してください。",
            "ai_heading": "Nowpattern AI",
            "ai_note": "公開採点対象の公式トラックレコード",
            "score": "Brier Index",
            "accuracy": "的中率",
            "resolved": "公開採点",
            "human_heading": "Human Forecasters",
            "beta_title": "AI benchmark only (beta)",
            "beta_body": (
                "人間ランキングは、十分な参加密度ができるまで公開競争として見せません。"
                "現在のサンプルは {sample_voters}人 / {sample_votes}票 / {sample_resolved}解決票 です。"
            ),
            "beta_thresholds": (
                "公開条件: {min_voters}人 / {min_votes}票 / {min_resolved_votes}解決票"
            ),
            "human_empty": "公開条件には到達しましたが、表示可能な人間ランキングはまだありません。",
            "rank_prefix": "順位",
            "votes": "総投票",
            "method": (
                "AIは公式 prediction_db の公開採点のみ、人間は synthetic/test を除外した reader votes のみで集計。"
            ),
        }
    return {
        "title": "AI Benchmark Leaderboard",
        "subtitle": "Nowpattern AI stays public; human rankings only unlock once the sample is genuinely meaningful.",
        "cta_title": "Join the Challenge",
        "cta_loading": "Loading participation criteria...",
        "cta_beta": (
            '<a href="https://nowpattern.com/en/predictions/" style="color:#2563eb;font-weight:700">'
            "Vote from the prediction tracker</a>. Human rankings stay in beta until the sample reaches "
            "{voters} unique voters / {votes} total votes / {resolved} resolved votes."
        ),
        "cta_live": (
            '<a href="https://nowpattern.com/en/predictions/" style="color:#2563eb;font-weight:700">'
            "Vote from the prediction tracker</a>. Each forecaster needs at least {min_resolved} resolved predictions "
            "to appear on the public ranking."
        ),
        "loading": "Loading leaderboard...",
        "load_failed": "Could not load the leaderboard right now. Please retry in a moment.",
        "ai_heading": "Nowpattern AI",
        "ai_note": "Official publicly scored track record",
        "score": "Brier Index",
        "accuracy": "Accuracy",
        "resolved": "Publicly scored",
        "human_heading": "Human Forecasters",
        "beta_title": "AI benchmark only (beta)",
        "beta_body": (
            "We do not present the human side as a real public contest until the sample is dense enough. "
            "Current sample: {sample_voters} unique voters / {sample_votes} votes / {sample_resolved} resolved votes."
        ),
        "beta_thresholds": (
            "Unlock threshold: {min_voters} unique voters / {min_votes} total votes / {min_resolved_votes} resolved votes"
        ),
        "human_empty": "The threshold is met, but there are still no human forecasters ready for public ranking.",
        "rank_prefix": "Rank",
        "votes": "Total votes",
        "method": (
            "AI uses the official prediction_db track record; humans use reader votes with synthetic/test accounts excluded."
        ),
    }


def _policy_links_html(lang: str) -> str:
    if lang == "ja":
        links = (
            ("予測手法", "/forecasting-methodology/"),
            ("採点と判定", "/forecast-scoring-and-resolution/"),
            ("整合性監査", "/forecast-integrity-and-audit/"),
        )
    else:
        links = (
            ("Forecasting methodology", "/en/forecasting-methodology/"),
            ("Scoring & resolution", "/en/forecast-scoring-and-resolution/"),
            ("Integrity & audit", "/en/forecast-integrity-and-audit/"),
        )
    return "".join(
        f'<a href="{href}" style="display:inline-flex;align-items:center;gap:6px;'
        f'padding:6px 10px;border-radius:9999px;border:1px solid rgba(148,163,184,.35);'
        f'color:#E2E8F0;text-decoration:none;font-size:0.8em;font-weight:700">{label} ↗</a>'
        for label, href in links
    )


def _leaderboard_script(lang: str) -> str:
    copy = json.dumps(_copy(lang), ensure_ascii=False)
    return (
        "<script>\n"
        "(function(){\n"
        f"  var copy = {copy};\n"
        "  var content = document.getElementById('np-lb-content');\n"
        "  var loading = document.getElementById('np-lb-loading');\n"
        "  var cta = document.getElementById('np-lb-cta-copy');\n"
        "  if (!content) return;\n"
        "  function esc(v){ return String(v == null ? '' : v).replace(/[&<>\\\"']/g, function(ch){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','\\\"':'&quot;',\"'\":'&#39;'}[ch]); }); }\n"
        "  function scoreColor(v){ if(v == null){ return '#94A3B8'; } if(v >= 70){ return '#16A34A'; } if(v >= 50){ return '#D97706'; } return '#DC2626'; }\n"
        "  function aiCard(ai){\n"
        "    var score = ai.avg_brier_index != null ? ai.avg_brier_index.toFixed(1) + '%' : '—';\n"
        "    var acc = ai.accuracy_pct != null ? ai.accuracy_pct.toFixed(1) + '%' : '—';\n"
        "    return '<div style=\"display:flex;align-items:flex-start;gap:14px;padding:18px;background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(15,23,42,.08);border-left:4px solid #b8860b;margin-bottom:14px\">'\n"
        "      + '<div style=\"font-size:1.3em;font-weight:800;color:#b8860b;min-width:34px\">#1</div>'\n"
        "      + '<div style=\"flex:1;min-width:0\">'\n"
        "      + '<div style=\"display:flex;align-items:center;gap:8px;flex-wrap:wrap\"><div style=\"font-size:1.05em;font-weight:800;color:#111827\">🤖 ' + copy.ai_heading + '</div><span style=\"font-size:0.7em;background:#FEF3C7;color:#92400E;padding:2px 8px;border-radius:999px\">AI benchmark</span></div>'\n"
        "      + '<div style=\"font-size:0.8em;color:#64748B;margin-top:4px\">' + copy.ai_note + '</div>'\n"
        "      + '<div style=\"display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;font-size:0.9em\">'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.score + ':</span> <b style=\"color:' + scoreColor(ai.avg_brier_index) + '\">' + score + '</b></div>'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.accuracy + ':</span> <b>' + acc + '</b></div>'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.resolved + ':</span> <b>' + esc(ai.resolved_count) + '</b></div>'\n"
        "      + '</div></div></div>';\n"
        "  }\n"
        "  function humanCard(rr, idx){\n"
        "    var score = rr.avg_brier_index != null ? rr.avg_brier_index.toFixed(1) + '%' : '—';\n"
        "    var acc = rr.accuracy_pct != null ? rr.accuracy_pct.toFixed(1) + '%' : '—';\n"
        "    var rank = rr.public_rank != null ? rr.public_rank : (idx + 2);\n"
        "    return '<div style=\"display:flex;align-items:flex-start;gap:14px;padding:16px;background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(15,23,42,.06);border-left:4px solid #CBD5E1;margin-bottom:10px\">'\n"
        "      + '<div style=\"font-size:1.1em;font-weight:800;color:#475569;min-width:34px\">#' + esc(rank) + '</div>'\n"
        "      + '<div style=\"flex:1;min-width:0\">'\n"
        "      + '<div style=\"font-size:0.98em;font-weight:700;color:#111827\">' + esc(rr.display_id || rr.voter_id || 'Forecaster') + '</div>'\n"
        "      + '<div style=\"display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:0.88em\">'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.score + ':</span> <b style=\"color:' + scoreColor(rr.avg_brier_index) + '\">' + score + '</b></div>'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.accuracy + ':</span> <b>' + acc + '</b></div>'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.resolved + ':</span> <b>' + esc(rr.resolved_count) + '</b></div>'\n"
        "      + '<div><span style=\"color:#64748B\">' + copy.votes + ':</span> <b>' + esc(rr.total_votes) + '</b></div>'\n"
        "      + '</div></div></div>';\n"
        "  }\n"
        "  Promise.all([\n"
        "    fetch('/reader-predict/leaderboard').then(function(r){ return r.json(); }),\n"
        "    fetch('/reader-predict/top-forecasters').then(function(r){ return r.json(); })\n"
        "  ]).then(function(results){\n"
        "    var lb = results[0] || {};\n"
        "    var top = results[1] || {};\n"
        "    var ai = lb.ai || {};\n"
        "    var human = top.human_competition || lb.human_competition || {ready:false,thresholds:{},sample:{}};\n"
        "    var thresholds = human.thresholds || {};\n"
        "    var sample = human.sample || {};\n"
        "    var humanRows = (top.human_public_forecasters || []).filter(function(r){ return !r.is_ai; });\n"
        "    if (cta) {\n"
        "      if (human.ready) {\n"
        "        cta.innerHTML = copy.cta_live\n"
        "          .replace('{min_resolved}', esc(thresholds.min_resolved_per_forecaster || 5));\n"
        "      } else {\n"
        "        cta.innerHTML = copy.cta_beta\n"
        "          .replace('{voters}', esc(thresholds.min_unique_voters || 25))\n"
        "          .replace('{votes}', esc(thresholds.min_total_votes || 200))\n"
        "          .replace('{resolved}', esc(thresholds.min_resolved_votes || 20));\n"
        "      }\n"
        "    }\n"
        "    var html = aiCard(ai);\n"
        "    html += '<div style=\"margin-top:10px;margin-bottom:10px\"><div style=\"font-size:0.86em;font-weight:800;color:#475569;letter-spacing:.04em;text-transform:uppercase\">' + copy.human_heading + '</div></div>';\n"
        "    if (!human.ready) {\n"
        "      html += '<div style=\"background:#EFF6FF;border:1px solid #BFDBFE;border-radius:12px;padding:16px 18px;color:#1E3A8A\">'\n"
        "        + '<div style=\"font-weight:800;margin-bottom:6px\">' + copy.beta_title + '</div>'\n"
        "        + '<div style=\"font-size:0.9em;line-height:1.6\">' + copy.beta_body\n"
        "            .replace('{sample_voters}', esc(sample.unique_voters || 0))\n"
        "            .replace('{sample_votes}', esc(sample.total_votes || 0))\n"
        "            .replace('{sample_resolved}', esc(sample.resolved_votes || 0))\n"
        "          + '</div>'\n"
        "        + '<div style=\"font-size:0.82em;color:#1D4ED8;margin-top:8px\">' + copy.beta_thresholds\n"
        "            .replace('{min_voters}', esc(thresholds.min_unique_voters || 25))\n"
        "            .replace('{min_votes}', esc(thresholds.min_total_votes || 200))\n"
        "            .replace('{min_resolved_votes}', esc(thresholds.min_resolved_votes || 20))\n"
        "          + '</div></div>';\n"
        "    } else if (!humanRows.length) {\n"
        "      html += '<div style=\"text-align:center;padding:28px;color:#64748B;background:#fff;border-radius:12px;border:1px dashed #CBD5E1\">' + copy.human_empty + '</div>';\n"
        "    } else {\n"
        "      humanRows.forEach(function(rr, idx){ html += humanCard(rr, idx); });\n"
        "    }\n"
        "    html += '<div style=\"font-size:0.8em;color:#64748B;margin-top:16px\">' + copy.method + '</div>';\n"
        "    content.innerHTML = html;\n"
        "    if (loading) loading.style.display = 'none';\n"
        "  }).catch(function(err){\n"
        "    if (loading) loading.style.display = 'none';\n"
        "    content.innerHTML = '<div style=\"background:#FEF2F2;border:1px solid #FECACA;color:#991B1B;border-radius:12px;padding:16px 18px\">' + copy.load_failed + '</div>';\n"
        "    console.error('[np-leaderboard] render failed', err);\n"
        "  });\n"
        "})();\n"
        "</script>"
    )


def build_leaderboard_page_html(lang: str) -> str:
    copy = _copy(lang)
    accent = "#b8860b" if lang == "ja" else "#2563eb"
    cta_loading = copy["cta_loading"]
    loading = copy["loading"]
    policy_links = _policy_links_html(lang)
    return f"""
<!-- NP-LEADERBOARD-SHELL-V1 -->
<div style="max-width:980px;margin:0 auto;padding:8px 0 28px">
  <div style="background:linear-gradient(135deg,#fffaf0 0%,#f8fafc 100%);border:1px solid #E5E7EB;border-radius:18px;padding:28px 24px;box-shadow:0 10px 28px rgba(15,23,42,.06);margin-bottom:18px">
    <div style="font-size:0.78em;letter-spacing:.08em;text-transform:uppercase;color:#64748B;font-weight:700">Nowpattern</div>
    <h2 style="font-size:2em;line-height:1.15;margin:8px 0 10px;color:#111827">{copy["title"]}</h2>
    <p style="margin:0;color:#475569;line-height:1.7;font-size:1em">{copy["subtitle"]}</p>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-bottom:18px">
    <div style="background:#fff;border:1px solid #E5E7EB;border-radius:14px;padding:18px 18px;box-shadow:0 2px 8px rgba(15,23,42,.05)">
      <div style="font-weight:800;color:#111827;margin-bottom:8px">{copy["cta_title"]}</div>
      <div id="np-lb-cta-copy" style="font-size:0.92em;color:#475569;line-height:1.7">{cta_loading}</div>
    </div>
    <div style="background:#0F172A;border:1px solid #1E293B;border-radius:14px;padding:18px 18px;color:#E2E8F0;box-shadow:0 2px 8px rgba(15,23,42,.12)">
      <div style="font-weight:800;margin-bottom:8px;color:#fff">Scoring policy</div>
      <div style="font-size:0.9em;line-height:1.7;color:#CBD5E1">AI and humans are not merged. AI uses the official public prediction record; human stats use reader votes only, with synthetic/test UUIDs excluded.</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">{policy_links}</div>
    </div>
  </div>
  <div id="np-lb-loading" style="padding:18px;color:{accent};font-weight:700">{loading}</div>
  <div id="np-lb-content"></div>
</div>
{_leaderboard_script(lang)}
""".strip()


def main() -> int:
    env = load_env()
    api_key = env.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY not found")
        return 1

    targets = [
        ("leaderboard", "Leaderboard | Nowpattern", "ja"),
        ("en-leaderboard", "Leaderboard | Nowpattern", "en"),
    ]
    for slug, title, lang in targets:
        html = build_leaderboard_page_html(lang)
        update_ghost_page(api_key, slug, html, title)
        print(f"Updated /{slug}/ ({lang})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
