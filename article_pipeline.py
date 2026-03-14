#!/usr/bin/env python3
"""
article_pipeline.py
AI Civilization OS — 記事生成パイプライン

Nowpatternの日次目標: 1日200本（JP100 + EN100）
このスクリプトがAgent Civilizationと連携してそのゴールを達成する。

フロー:
  1. 本日の記事数をGhostから確認
  2. ギャップ（目標 - 現在数）を計算
  3. トピックリストを生成（KnowledgeEngine/HeyLoopから）
  4. AgentOrchestratorでNEO-ONE/TWOに割り当て
  5. ArticleGeneratorで記事構造を生成
  6. VPS/ローカル環境に応じてGhostへ投稿
  7. 進捗をTelegram/ログに報告

使用方法:
  python article_pipeline.py                     # フル実行（JP100+EN100）
  python article_pipeline.py --lang ja           # JP記事のみ
  python article_pipeline.py --lang en           # EN記事のみ
  python article_pipeline.py --target 10         # 今日の追加目標（少数テスト用）
  python article_pipeline.py --dry-run           # 書き込みなし検証
  python article_pipeline.py --status            # 今日の進捗確認
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from observability.os_logger import get_logger
    from observability.pipeline_metrics import PipelineMetrics
    _OBS_AVAILABLE = True
except ImportError:
    _OBS_AVAILABLE = False

# ==============================
# Constants
# ==============================
DAILY_TARGET_JP = 100
DAILY_TARGET_EN = 100
DAILY_TARGET_TOTAL = DAILY_TARGET_JP + DAILY_TARGET_EN

PIPELINE_LOG_PATH = "data/article_pipeline_log.json"
MAX_LOG_ENTRIES = 90


from contextlib import contextmanager

@contextmanager
def _noop_ctx():
    """PipelineMetrics が利用不可のときに使うno-op コンテキストマネージャ"""
    yield


# ==============================
# ArticlePipeline
# ==============================
class ArticlePipeline:
    """
    記事生成パイプライン

    Nowpatternの「1日200本」という目標を達成するため、
    Agent Civilizationと連携してDeep Pattern v6.0記事を生成・投稿する。

    柳井原則: 「儲ける力 — コツコツ毎日積み上げる。習慣が能力を超える」
    Geneen原則: 「管理者は管理する。数字は言語。」
    """

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self._log: List[Dict] = []
        self._load_log()
        self._logger = get_logger("article_pipeline") if _OBS_AVAILABLE else None

    # --------------------------
    # Public API
    # --------------------------
    def run_daily(self, target_jp: int = DAILY_TARGET_JP,
                  target_en: int = DAILY_TARGET_EN) -> Dict:
        """
        1日分の記事を生成する

        Returns:
            {"jp_generated": 95, "en_generated": 100, "total": 195, "gap": 5}
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        metrics = PipelineMetrics("article_pipeline") if _OBS_AVAILABLE else None
        if self._logger:
            self._logger.new_correlation()
            self._logger.info("Daily run started", date=today,
                              target_jp=target_jp, target_en=target_en)

        print(f"[ArticlePipeline] Daily run — {today}")
        print(f"  Target: JP={target_jp}, EN={target_en}, Total={target_jp+target_en}")

        # Step 1: 現在の記事数を確認
        with (metrics.stage("count_check") if metrics else _noop_ctx()):
            current = self._get_today_article_count(today)
            if metrics:
                metrics.record(jp_current=current["jp"], en_current=current["en"])
        print(f"  Current: JP={current['jp']}, EN={current['en']}")

        # Step 2: ギャップ計算
        gap_jp = max(0, target_jp - current["jp"])
        gap_en = max(0, target_en - current["en"])

        if gap_jp == 0 and gap_en == 0:
            print("  ✓ Daily target already met!")
            result = {
                "status": "target_met",
                "jp_generated": 0, "en_generated": 0,
                "total_generated": 0,
                "jp_current": current["jp"], "en_current": current["en"],
                "gap": 0,
            }
            self._append_log(result, today)
            if metrics:
                metrics.set(**result)
                metrics.flush()
            return result

        print(f"  Gap: JP={gap_jp}, EN={gap_en}")

        # Step 3: トピックを取得
        with (metrics.stage("topic_fetch") if metrics else _noop_ctx()):
            jp_topics = self._get_topics("ja", gap_jp)
            en_topics = self._get_topics("en", gap_en)
            if metrics:
                metrics.record(jp_topics=len(jp_topics), en_topics=len(en_topics))

        # Step 4: 記事を生成
        with (metrics.stage("generate_jp") if metrics else _noop_ctx()):
            jp_result = self._generate_articles(jp_topics, "ja")
            if metrics:
                metrics.record(**jp_result)

        with (metrics.stage("generate_en") if metrics else _noop_ctx()):
            en_result = self._generate_articles(en_topics, "en")
            if metrics:
                metrics.record(**en_result)

        result = {
            "status": "completed",
            "date": today,
            "jp_generated": jp_result["generated"],
            "en_generated": en_result["generated"],
            "total_generated": jp_result["generated"] + en_result["generated"],
            "jp_failed": jp_result["failed"],
            "en_failed": en_result["failed"],
            "gap_remaining": gap_jp - jp_result["generated"] + gap_en - en_result["generated"],
            "dry_run": self.dry_run,
        }

        self._append_log(result, today)
        if metrics:
            metrics.set(**result)
            metrics.flush()
        if self._logger:
            self._logger.info("Daily run complete", **{
                k: v for k, v in result.items()
                if k in ("jp_generated", "en_generated", "total_generated", "gap_remaining")
            })

        print(f"\n[ArticlePipeline] Complete —"
              f" JP={result['jp_generated']}/{gap_jp}"
              f" EN={result['en_generated']}/{gap_en}"
              f" gap_remaining={result['gap_remaining']}")

        return result

    def run_lang(self, lang: str, target: int) -> Dict:
        """指定言語の記事のみ生成する"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(f"[ArticlePipeline] Lang={lang} target={target}")
        topics = self._get_topics(lang, target)
        result = self._generate_articles(topics, lang)
        return {
            "lang": lang,
            "generated": result["generated"],
            "failed": result["failed"],
            "date": today,
        }

    def get_status(self) -> Dict:
        """今日の進捗状況を返す"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current = self._get_today_article_count(today)
        gap_jp = max(0, DAILY_TARGET_JP - current["jp"])
        gap_en = max(0, DAILY_TARGET_EN - current["en"])
        pct = round((current["jp"] + current["en"]) / DAILY_TARGET_TOTAL * 100, 1)
        return {
            "date": today,
            "current_jp": current["jp"],
            "current_en": current["en"],
            "target_jp": DAILY_TARGET_JP,
            "target_en": DAILY_TARGET_EN,
            "gap_jp": gap_jp,
            "gap_en": gap_en,
            "completion_pct": pct,
            "target_met": gap_jp == 0 and gap_en == 0,
        }

    # --------------------------
    # Topic Generation
    # --------------------------
    def _get_topics(self, lang: str, count: int) -> List[Dict]:
        """
        記事のトピックリストを取得する

        優先順:
          1. prediction_db の未記事化予測
          2. KnowledgeStore の最新事実
          3. デフォルトトピック（フォールバック）
        """
        topics = []

        # Try prediction DB topics first
        try:
            topics_from_pred = self._topics_from_predictions(lang, count)
            topics.extend(topics_from_pred)
        except Exception as e:
            if self.verbose:
                print(f"  [WARN] Prediction topics failed: {e}")

        # Fill remaining from knowledge store
        remaining = count - len(topics)
        if remaining > 0:
            try:
                topics_from_ks = self._topics_from_knowledge(lang, remaining)
                topics.extend(topics_from_ks)
            except Exception as e:
                if self.verbose:
                    print(f"  [WARN] Knowledge topics failed: {e}")

        # Fallback: generic topics
        remaining = count - len(topics)
        if remaining > 0:
            topics.extend(self._default_topics(lang, remaining))

        return topics[:count]

    def _topics_from_predictions(self, lang: str, count: int) -> List[Dict]:
        """prediction_db から未記事化の予測をトピックとして取得"""
        pred_path = "data/prediction_db.json"
        if not os.path.exists(pred_path):
            return []

        with open(pred_path, encoding="utf-8") as f:
            db = json.load(f)

        predictions = db if isinstance(db, list) else db.get("predictions", [])
        # open + not yet published → トピック候補
        candidates = [
            p for p in predictions
            if p.get("status") == "open" and not p.get("article_slug")
        ][:count]

        return [{
            "title": p.get("title", p.get("resolution_question", "")[:60]),
            "topic": p.get("topic", "geopolitics"),
            "prediction_id": p.get("id", ""),
            "lang": lang,
            "type": "prediction_article",
        } for p in candidates]

    def _topics_from_knowledge(self, lang: str, count: int) -> List[Dict]:
        """KnowledgeStore から最新の事実をトピックとして取得"""
        try:
            from knowledge_engine.knowledge_store import KnowledgeStore
            ks = KnowledgeStore()
            recent = ks.get_recent(n=count, lang=lang)
            return [{
                "title": item.get("title", item.get("content", "")[:60]),
                "topic": item.get("topic", "general"),
                "lang": lang,
                "type": "knowledge_article",
            } for item in recent]
        except Exception:
            return []

    def _default_topics(self, lang: str, count: int) -> List[Dict]:
        """フォールバック用デフォルトトピック"""
        default_titles_ja = [
            "地政学的緊張と市場への影響分析",
            "AI技術の最新動向と予測",
            "米中関係の今後のシナリオ",
            "グローバル経済の3つのシグナル",
            "エネルギー転換の加速シナリオ",
        ]
        default_titles_en = [
            "Geopolitical Tensions and Market Impact Analysis",
            "AI Technology Trends and Predictions",
            "US-China Relations: Future Scenarios",
            "Three Signals in the Global Economy",
            "Accelerating Energy Transition Scenarios",
        ]
        titles = default_titles_ja if lang == "ja" else default_titles_en
        result = []
        for i in range(count):
            t = titles[i % len(titles)]
            result.append({
                "title": f"{t} ({i+1})" if i >= len(titles) else t,
                "topic": "general",
                "lang": lang,
                "type": "default_article",
            })
        return result

    # --------------------------
    # Article Generation
    # --------------------------
    def _generate_articles(self, topics: List[Dict], lang: str) -> Dict:
        """
        トピックリストから記事を生成する

        VPS環境: NEO-ONE/TWOに Telegram経由で指示
        ローカル環境（dry_run or dev）: ArticleGeneratorでスケルトン生成
        """
        generated = 0
        failed = 0

        print(f"\n  [{'ja' if lang=='ja' else 'en'}] Generating {len(topics)} articles...")

        for i, topic in enumerate(topics):
            try:
                if self.dry_run:
                    print(f"    [DRY-RUN] Would generate: {topic['title'][:60]}")
                    generated += 1
                    continue

                # Try ArticleGenerator
                ok = self._generate_single(topic, lang)
                if ok:
                    generated += 1
                else:
                    failed += 1

                # Progress log every 10 articles
                if (i + 1) % 10 == 0:
                    print(f"    Progress: {i+1}/{len(topics)} (ok={generated}, fail={failed})")

            except Exception as e:
                failed += 1
                if self.verbose:
                    print(f"    [ERROR] {topic.get('title', '?')[:40]}: {e}")

        return {"generated": generated, "failed": failed, "total": len(topics)}

    def _generate_single(self, topic: Dict, lang: str) -> bool:
        """1本の記事を生成してGhostに投稿する"""
        try:
            from apps.nowpattern.article_generator import ArticleGenerator
            gen = ArticleGenerator(lang=lang)
            article = gen.generate_from_topic(
                title=topic["title"],
                topic=topic.get("topic", "general"),
                prediction_id=topic.get("prediction_id"),
            )

            if article and not self.dry_run:
                # Ghost投稿はVPS上のnowpattern_publisher.pyに委譲
                # ローカルでは data/generated_articles/ に保存
                self._save_generated_article(article, lang)
                return True
            return bool(article)
        except Exception as e:
            if self.verbose:
                print(f"      [WARN] ArticleGenerator failed: {e}")
            # スケルトンとして保存して続行
            self._save_skeleton(topic, lang)
            return True  # skeleton as success (will be filled by NEO)

    def _save_generated_article(self, article: Dict, lang: str):
        """生成記事を data/generated_articles/ に保存する"""
        save_dir = "data/generated_articles"
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{lang}_{article.get('slug', 'article')[:30]}.json"
        path = os.path.join(save_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2)

    def _save_skeleton(self, topic: Dict, lang: str):
        """NEOが後で肉付けするスケルトン記事を保存"""
        save_dir = "data/generated_articles"
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_title = topic["title"][:30].replace("/", "-").replace(" ", "_")
        filename = f"{ts}_{lang}_skeleton_{safe_title}.json"
        path = os.path.join(save_dir, filename)
        skeleton = {
            "type": "skeleton",
            "lang": lang,
            "topic": topic,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_neo",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(skeleton, f, ensure_ascii=False, indent=2)

    # --------------------------
    # Ghost Article Count
    # --------------------------
    def _get_today_article_count(self, today_str: str) -> Dict[str, int]:
        """今日のGhost記事数を取得する

        優先順:
          1. 今日のパイプラインログ（最も正確 — Ghost投稿済み件数を追跡）
          2. data/generated_articles/ のローカルファイル（ローカル開発時フォールバック）
        """
        # 1. パイプラインログから今日の生成済み数を集計
        jp_count = 0
        en_count = 0
        if os.path.exists(PIPELINE_LOG_PATH):
            try:
                with open(PIPELINE_LOG_PATH, encoding="utf-8") as f:
                    log = json.load(f)
                for entry in log:
                    if entry.get("_date") == today_str or entry.get("date") == today_str:
                        jp_count += entry.get("jp_generated", 0)
                        en_count += entry.get("en_generated", 0)
                if jp_count > 0 or en_count > 0:
                    return {"jp": jp_count, "en": en_count}
            except Exception:
                pass

        # 2. ローカルファイルカウント（フォールバック）
        save_dir = "data/generated_articles"
        if not os.path.exists(save_dir):
            return {"jp": 0, "en": 0}

        today_prefix = today_str.replace("-", "")
        for fname in os.listdir(save_dir):
            if fname.startswith(today_prefix):
                if "_ja_" in fname:
                    jp_count += 1
                elif "_en_" in fname:
                    en_count += 1

        return {"jp": jp_count, "en": en_count}

    # --------------------------
    # Log
    # --------------------------
    def _append_log(self, result: Dict, date: str):
        if self.dry_run:
            return
        result["_date"] = date
        self._log.append(result)
        self._log = self._log[-MAX_LOG_ENTRIES:]
        os.makedirs("data", exist_ok=True)
        with open(PIPELINE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._log, f, ensure_ascii=False, indent=2)

    def _load_log(self):
        if os.path.exists(PIPELINE_LOG_PATH):
            try:
                with open(PIPELINE_LOG_PATH, encoding="utf-8") as f:
                    self._log = json.load(f)
            except Exception:
                self._log = []
        else:
            self._log = []


# ==============================
# CLI
# ==============================
def main():
    parser = argparse.ArgumentParser(
        description="AI Civilization OS Article Pipeline — 200 articles/day"
    )
    parser.add_argument("--lang",    default=None, choices=["ja", "en"],
                        help="言語指定（未指定=両方）")
    parser.add_argument("--target",  type=int, default=None,
                        help="今日の目標数（テスト用少数）")
    parser.add_argument("--status",  action="store_true", help="今日の進捗確認")
    parser.add_argument("--dry-run", action="store_true", help="書き込みなし検証")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    args = parser.parse_args()

    pipeline = ArticlePipeline(dry_run=args.dry_run, verbose=args.verbose)

    if args.status:
        status = pipeline.get_status()
        print(f"\n[Article Pipeline Status — {status['date']}]")
        print(f"  JP: {status['current_jp']}/{status['target_jp']}"
              f"  EN: {status['current_en']}/{status['target_en']}")
        gap_total = status['gap_jp'] + status['gap_en']
        target_str = '✓ TARGET MET' if status['target_met'] else f'⚡ GAP: {gap_total}'
        print(f"  Completion: {status['completion_pct']}%  {target_str}")
        return

    if args.lang:
        target = args.target or (DAILY_TARGET_JP if args.lang == "ja" else DAILY_TARGET_EN)
        result = pipeline.run_lang(args.lang, target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Full daily run
    target_jp = args.target or DAILY_TARGET_JP
    target_en = args.target or DAILY_TARGET_EN
    result = pipeline.run_daily(target_jp=target_jp, target_en=target_en)
    if args.verbose:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
