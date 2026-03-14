"""
apps/nowpattern/article_generator.py
記事生成器 — Agent Civilization → Deep Pattern v6.0 記事構造へ変換

AI Civilization OSの分析結果を、Nowpatternの記事フォーマット（v6.0）に整形する。
"""

import sys
import json
import os
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Deep Pattern v6.0 セクション定義
ARTICLE_SECTIONS = {
    "fast_read": "⚡ FAST READ",
    "signal": "📡 シグナル — 何が起きたか",
    "between_lines": "🔍 行間を読む — 報道が言っていないこと",
    "now_pattern": "NOW PATTERN",
    "pattern_history": "📚 パターンの歴史",
    "what_next": "🔮 次のシナリオ",
    "open_loop": "🔄 追跡ループ",
    "oracle": "🎯 オラクル宣言",
}

EN_SECTIONS = {
    "fast_read": "⚡ FAST READ",
    "signal": "📡 THE SIGNAL",
    "between_lines": "🔍 BETWEEN THE LINES",
    "now_pattern": "NOW PATTERN",
    "pattern_history": "📚 PATTERN HISTORY",
    "what_next": "🔮 WHAT'S NEXT",
    "open_loop": "🔄 OPEN LOOP",
    "oracle": "🎯 ORACLE STATEMENT",
}


class ArticleGenerator:
    """
    AI Civilization OS の分析結果から Deep Pattern v6.0 記事を生成する

    入力: agent_debate_loop.py の出力（ConsensusResult + DebateResult）
    出力: Ghost CMS に投稿可能な HTML + 記事メタデータ
    """

    def __init__(self, lang: str = "ja"):
        self.lang = lang
        self.sections = ARTICLE_SECTIONS if lang == "ja" else EN_SECTIONS
        self._output_dir = "data/generated_articles"
        os.makedirs(self._output_dir, exist_ok=True)

    # ── メイン生成メソッド ──────────────────────────────────────

    def generate(self,
                 topic: str,
                 tags: List[str],
                 debate_result: Dict,
                 consensus_result: Dict,
                 historical_parallels: Optional[str] = None,
                 oracle_block: Optional[str] = None) -> Dict:
        """
        完全な記事を生成する

        Args:
            topic: 記事のトピック（タイトルになる）
            tags: タクソノミータグ
            debate_result: DebateEngine の出力
            consensus_result: ConsensusEngine の出力
            historical_parallels: CivilizationPatterns の HTML出力（セクション4用）
            oracle_block: ORACLE STATEMENT HTML（prediction_db連動）

        Returns:
            {"title", "html", "tags", "meta", "word_count"}
        """
        prob = consensus_result.get("final_probability", 50)
        pick = consensus_result.get("final_pick", "UNCERTAIN")
        insights = debate_result.get("key_insights", [])
        rounds = debate_result.get("rounds", [])
        quality = debate_result.get("debate_quality", "MEDIUM")

        # 各セクションを生成
        fast_read_html = self._generate_fast_read(topic, tags, prob, pick, insights)
        signal_html = self._generate_signal(topic, rounds)
        between_lines_html = self._generate_between_lines(insights, quality)
        now_pattern_html = self._generate_now_pattern(tags, rounds)
        pattern_history_html = historical_parallels or self._generate_placeholder_history()
        what_next_html = self._generate_what_next(consensus_result)
        open_loop_html = self._generate_open_loop(topic, tags)
        oracle_html = oracle_block or self._generate_oracle_placeholder(topic, prob, pick)

        # 全セクション結合
        html = "\n\n".join([
            fast_read_html,
            signal_html,
            between_lines_html,
            now_pattern_html,
            pattern_history_html,
            what_next_html,
            open_loop_html,
            oracle_html,
        ])

        article = {
            "title": topic,
            "html": html,
            "tags": tags,
            "lang": self.lang,
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "consensus_probability": prob,
                "consensus_pick": pick,
                "debate_quality": quality,
                "agent_count": len(debate_result.get("rounds", [{}])[0].get("positions", [])) if rounds else 0,
            },
            "word_count": len(html.replace("<", " <").split()),
        }

        # ファイルに保存
        self._save(article)
        return article

    # ── セクション生成 ──────────────────────────────────────

    def _generate_fast_read(self, topic: str, tags: List[str],
                             prob: float, pick: str, insights: List[str]) -> str:
        """FAST READ セクション（1分要約 + タグバッジ + 確率サマリー）"""
        # タグバッジ HTML
        tag_badges = " ".join(
            f'<span class="np-tag-badge" style="background:#f0f4ff;border:1px solid #c7d2fe;'
            f'border-radius:4px;padding:2px 8px;font-size:0.72em;font-weight:600;">'
            f'{t}</span>'
            for t in tags[:5]
        )

        pick_emoji = "✅" if pick == "YES" else ("❌" if pick == "NO" else "⚖️")
        top_insight = insights[0] if insights else "エージェント分析中..."

        section_title = self.sections["fast_read"]

        return f"""<div class="np-fast-read" style="background:#f8faff;border-left:4px solid #2563eb;padding:20px 24px;border-radius:8px;margin-bottom:24px;">
<h2 style="margin:0 0 12px;font-size:1.1em;font-weight:700;color:#1e40af;">{section_title}</h2>
<p style="margin:0 0 12px;font-size:0.95em;color:#374151;">{top_insight}</p>
<div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap;">
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 16px;text-align:center;">
    <div style="font-size:0.7em;color:#888;letter-spacing:.08em;">AI予測</div>
    <div style="font-size:1.4em;font-weight:700;color:#2563eb;">{prob:.0f}%</div>
    <div style="font-size:0.85em;">{pick_emoji} {pick}</div>
  </div>
</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;">{tag_badges}</div>
</div>"""

    def _generate_signal(self, topic: str, rounds: List[Dict]) -> str:
        """シグナルセクション（何が起きたか）"""
        section_title = self.sections["signal"]

        # デベートの第1ラウンドから引用
        positions_text = ""
        if rounds:
            first_round = rounds[0]
            positions = first_round.get("positions", [])
            for pos in positions[:2]:
                agent = pos.get("agent", "")
                reasoning = pos.get("reasoning", "")
                if reasoning:
                    positions_text += f"<li><strong>{agent}</strong>: {reasoning}</li>\n"

        return f"""<h2 class="np-signal">{section_title}</h2>
<p>「{topic}」について、AI文明OSのエージェントが分析した重要シグナルを報告する。</p>
<ul>
{positions_text or "<li>分析データを処理中...</li>"}
</ul>"""

    def _generate_between_lines(self, insights: List[str], quality: str) -> str:
        """行間を読むセクション"""
        section_title = self.sections["between_lines"]
        quality_label = {"HIGH": "高品質", "MEDIUM": "中品質", "LOW": "要再分析"}.get(quality, quality)

        insights_html = "\n".join(f"<li>{ins}</li>" for ins in insights[:3]) or "<li>分析継続中</li>"

        return f"""<h2 class="np-between-lines">{section_title}</h2>
<p>エージェントディベートから導出されたインサイト（ディベート品質: {quality_label}）:</p>
<ul>
{insights_html}
</ul>"""

    def _generate_now_pattern(self, tags: List[str], rounds: List[Dict]) -> str:
        """NOW PATTERN セクション（力学分析）"""
        section_title = self.sections["now_pattern"]

        # 力学タグを抽出
        dynamics_tags = [t for t in tags if t not in ["nowpattern", "deep-pattern", "lang-ja", "lang-en"]]

        # ディベートの収束過程
        convergence_text = ""
        if len(rounds) >= 2:
            round_probs = []
            for r in rounds:
                probs = [p.get("probability", 50) for p in r.get("positions", [])]
                if probs:
                    avg = sum(probs) / len(probs)
                    round_probs.append(f"Round {r.get('round_number', '?')}: {avg:.1f}%")
            convergence_text = f"<p>確率収束: {' → '.join(round_probs)}</p>"

        tags_display = " / ".join(dynamics_tags[:3]) if dynamics_tags else "分析中"

        return f"""<h2 class="np-now-pattern">{section_title}</h2>
<p>検出された力学パターン: <strong>{tags_display}</strong></p>
{convergence_text}
<p>6専門エージェント（歴史家・科学者・経済学者・戦略家・実装者・監査官）が
多角的に分析し、力学の交差点を特定した。</p>"""

    def _generate_placeholder_history(self) -> str:
        """パターンの歴史（プレースホルダー）"""
        section_title = self.sections["pattern_history"]
        return f"""<h2>{section_title}</h2>
<p>歴史的並行事例をKnowledgeGraphから抽出中...</p>
<p><em>civilization_patterns.py に登録されたパターンが自動挿入されます。</em></p>"""

    def _generate_what_next(self, consensus_result: Dict) -> str:
        """次のシナリオセクション（3シナリオ）"""
        section_title = self.sections["what_next"]
        prob = consensus_result.get("final_probability", 50)

        optimistic_prob = min(95, prob + 15)
        base_prob = prob
        pessimistic_prob = max(5, prob - 20)

        return f"""<h2>{section_title}</h2>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;">
  <div style="background:#f0fdf4;border-radius:8px;padding:16px;border:1px solid #86efac;">
    <div style="font-size:0.75em;color:#166534;font-weight:600;">楽観シナリオ</div>
    <div style="font-size:1.4em;font-weight:700;color:#16a34a;">{optimistic_prob}%</div>
    <div style="font-size:0.85em;color:#374151;">ベストケースが実現</div>
  </div>
  <div style="background:#eff6ff;border-radius:8px;padding:16px;border:1px solid #93c5fd;">
    <div style="font-size:0.75em;color:#1e40af;font-weight:600;">基本シナリオ</div>
    <div style="font-size:1.4em;font-weight:700;color:#2563eb;">{base_prob}%</div>
    <div style="font-size:0.85em;color:#374151;">現在の趨勢が続く</div>
  </div>
  <div style="background:#fef2f2;border-radius:8px;padding:16px;border:1px solid #fca5a5;">
    <div style="font-size:0.75em;color:#991b1b;font-weight:600;">悲観シナリオ</div>
    <div style="font-size:1.4em;font-weight:700;color:#dc2626;">{pessimistic_prob}%</div>
    <div style="font-size:0.85em;color:#374151;">リスク要因が顕在化</div>
  </div>
</div>"""

    def _generate_open_loop(self, topic: str, tags: List[str]) -> str:
        """追跡ループセクション（LIKING原則込み）"""
        section_title = self.sections["open_loop"]
        tag_display = " / ".join(tags[:3]) if tags else "予測"

        return f"""<h2 class="np-open-loop">{section_title}</h2>
<p>「{topic}」の次のトリガー:</p>
<ul>
<li>関連指標: {tag_display} の動向を追跡中</li>
<li>判定日になったら自動でBrier Scoreを更新します</li>
</ul>
<p style="margin-top:16px;padding:12px;background:#f9fafb;border-radius:8px;font-size:0.9em;">
🤔 <strong>あなたはどう読みますか？</strong>
<a href="/predictions/" style="color:#2563eb;">予測に参加 →</a>
</p>"""

    def _generate_oracle_placeholder(self, topic: str, prob: float, pick: str) -> str:
        """ORACLE STATEMENT プレースホルダー"""
        section_title = self.sections["oracle"]
        return f"""<div class="np-oracle" style="border:2px solid #e5e7eb;border-radius:8px;padding:20px;margin-top:24px;">
<h2 style="margin:0 0 12px;">{section_title}</h2>
<pre style="font-family:monospace;font-size:0.85em;color:#374151;">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ORACLE STATEMENT — この予測の追跡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
判定質問: {topic} は実現するか？
Nowpatternの予測: {pick} — {prob:.0f}%確率
市場の予測（Polymarket）: 未取得
判定日: TBD
的中条件: 判定日時点での結果
↳ 予測一覧: nowpattern.com/predictions/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
</pre>
</div>"""

    def _save(self, article: Dict):
        """記事をJSONファイルに保存する"""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        safe_title = re.sub(r'[^\w\-]', '_', article['title'][:30])
        filename = f"{ts}_{self.lang}_{safe_title}.json"
        filepath = os.path.join(self._output_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(article, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] ArticleGenerator save error: {e}")


if __name__ == "__main__":
    gen = ArticleGenerator(lang="ja")
    demo = gen.generate(
        topic="米中関税戦争：2026年の分岐点",
        tags=["経済・金融", "地政学・安全保障", "対立の螺旋"],
        debate_result={
            "key_insights": ["関税引き上げは双方の経済を傷つける", "選挙前に妥協は困難"],
            "rounds": [{"round_number": 1, "positions": [
                {"agent": "historian", "reasoning": "貿易戦争は歴史的に長期化する", "probability": 65},
                {"agent": "economist", "reasoning": "市場は45%の確率を織り込み済み", "probability": 45},
            ]}],
            "debate_quality": "HIGH",
        },
        consensus_result={
            "final_probability": 58,
            "final_pick": "YES",
            "consensus_level": "MODERATE",
        },
    )
    print(f"記事生成完了: {demo['title']}, {demo['word_count']}語")
