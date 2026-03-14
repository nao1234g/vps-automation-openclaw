"""
observability/pipeline_metrics.py
AI Civilization OS — パイプライン計測

各ステージの実行時間・成功率・件数を追跡し、
daily_metrics.json に蓄積する。

使い方:
  from observability.pipeline_metrics import PipelineMetrics
  m = PipelineMetrics("article_pipeline")
  with m.stage("generate_jp"):
      # ... 処理 ...
      m.record(generated=95, failed=5)
  m.flush()  # daily_metrics.json に書き込み

Geneenの原則: 「管理者は管理する。プロセスではなく結果を。」
"""

import sys
import json
import os
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from contextlib import contextmanager

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

METRICS_PATH = "data/daily_metrics.json"
MAX_METRICS_DAYS = 90


class PipelineMetrics:
    """
    パイプライン計測クラス

    - ステージ単位でレイテンシを計測
    - 成功/失敗カウンターを管理
    - daily_metrics.json に日次集計を保存
    """

    def __init__(self, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._stages: Dict[str, Dict[str, Any]] = {}
        self._current_stage: Optional[str] = None
        self._stage_start: Optional[float] = None
        self._extra: Dict[str, Any] = {}

    # ── ステージ計測 ───────────────────────────────────────────────────

    @contextmanager
    def stage(self, name: str):
        """ステージの実行時間を計測するコンテキストマネージャ"""
        self._current_stage = name
        self._stage_start = time.monotonic()
        self._stages[name] = {"status": "running", "started_at": time.monotonic()}
        try:
            yield self
            elapsed = time.monotonic() - self._stage_start
            self._stages[name]["status"] = "ok"
            self._stages[name]["elapsed_sec"] = round(elapsed, 3)
        except Exception as exc:
            elapsed = time.monotonic() - (self._stage_start or time.monotonic())
            self._stages[name]["status"] = "error"
            self._stages[name]["elapsed_sec"] = round(elapsed, 3)
            self._stages[name]["error"] = str(exc)
            raise
        finally:
            self._current_stage = None

    def record(self, **kwargs):
        """現在のステージにメトリクスを追記する"""
        if self._current_stage and self._current_stage in self._stages:
            self._stages[self._current_stage].update(kwargs)
        else:
            self._extra.update(kwargs)

    def set(self, **kwargs):
        """パイプライン全体のメトリクスを設定する"""
        self._extra.update(kwargs)

    # ── 集計 ──────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """パイプライン全体のサマリーを返す"""
        ended_at = datetime.now(timezone.utc).isoformat()
        all_ok = all(s.get("status") == "ok" for s in self._stages.values())
        total_elapsed = sum(
            s.get("elapsed_sec", 0) for s in self._stages.values()
        )
        return {
            "pipeline": self.pipeline_name,
            "started_at": self.started_at,
            "ended_at": ended_at,
            "total_elapsed_sec": round(total_elapsed, 3),
            "all_stages_ok": all_ok,
            "stages": self._stages,
            **self._extra,
        }

    def flush(self) -> Dict[str, Any]:
        """サマリーを daily_metrics.json に追記する"""
        summary = self.summary()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        metrics = {}
        if os.path.exists(METRICS_PATH):
            try:
                with open(METRICS_PATH, encoding="utf-8") as f:
                    metrics = json.load(f)
            except Exception:
                metrics = {}

        if today not in metrics:
            metrics[today] = {}

        pipeline_key = self.pipeline_name
        if pipeline_key not in metrics[today]:
            metrics[today][pipeline_key] = []

        metrics[today][pipeline_key].append(summary)

        # 90日ローテーション
        if len(metrics) > MAX_METRICS_DAYS:
            oldest_keys = sorted(metrics.keys())[:-MAX_METRICS_DAYS]
            for k in oldest_keys:
                del metrics[k]

        os.makedirs("data", exist_ok=True)
        try:
            with open(METRICS_PATH, "w", encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] PipelineMetrics flush failed: {e}", file=sys.stderr)

        return summary

    # ── クイックアクセス ───────────────────────────────────────────────

    @staticmethod
    def get_today_summary(pipeline_name: str) -> Optional[Dict]:
        """今日の最新メトリクスを返す"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not os.path.exists(METRICS_PATH):
            return None
        try:
            with open(METRICS_PATH, encoding="utf-8") as f:
                m = json.load(f)
            runs = m.get(today, {}).get(pipeline_name, [])
            return runs[-1] if runs else None
        except Exception:
            return None

    @staticmethod
    def get_stage_p95(pipeline_name: str, stage_name: str, last_days: int = 7) -> Optional[float]:
        """指定ステージの過去 N日 p95 レイテンシを返す（秒）"""
        if not os.path.exists(METRICS_PATH):
            return None
        try:
            with open(METRICS_PATH, encoding="utf-8") as f:
                m = json.load(f)
            elapsed_list = []
            for day_data in m.values():
                for run in day_data.get(pipeline_name, []):
                    s = run.get("stages", {}).get(stage_name, {})
                    if "elapsed_sec" in s:
                        elapsed_list.append(s["elapsed_sec"])
            if not elapsed_list:
                return None
            elapsed_list.sort()
            idx = int(len(elapsed_list) * 0.95)
            return elapsed_list[min(idx, len(elapsed_list) - 1)]
        except Exception:
            return None
