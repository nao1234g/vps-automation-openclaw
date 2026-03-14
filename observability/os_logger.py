"""
observability/os_logger.py
AI Civilization OS — 構造化ロガー

設計原則:
  - 全ログは JSON Lines 形式（1行 = 1 JSON object）
  - run_id: OSブート毎にユニーク（UUID4）
  - correlation_id: 1つのパイプライン実行をまたぐ追跡ID
  - stage: ログを発生させたコンポーネント名
  - level: DEBUG / INFO / WARN / ERROR / CRITICAL

使い方:
  from observability.os_logger import get_logger
  log = get_logger("article_pipeline")
  log.info("Daily run started", run_id="abc123", target_jp=100)

Geneenの原則: 「数字は言語。メトリクスなきシステムは盲目のパイロット」
"""

import sys
import json
import os
import uuid
import traceback
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── グローバルセッション run_id（OSブート時に1回生成）────────────────────
_SESSION_RUN_ID: str = str(uuid.uuid4())[:8]

LOG_DIR = "data/logs"
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40, "CRITICAL": 50}
DEFAULT_MIN_LEVEL = "INFO"


def get_logger(stage: str, min_level: str = DEFAULT_MIN_LEVEL) -> "OSLogger":
    """ステージ名付きロガーを返す（シングルトンではなく軽量ファクトリ）"""
    return OSLogger(stage=stage, min_level=min_level)


class OSLogger:
    """
    構造化ロガー — JSON Lines 形式でファイルとstdoutに同時出力

    Attributes:
        stage: コンポーネント名（"article_pipeline", "board_meeting" 等）
        run_id: セッション全体を通じたID（_SESSION_RUN_ID を使用）
        correlation_id: 1パイプライン実行内のグループID（set_correlation で設定）
    """

    def __init__(self, stage: str, min_level: str = DEFAULT_MIN_LEVEL):
        self.stage = stage
        self.run_id = _SESSION_RUN_ID
        self.correlation_id: Optional[str] = None
        self._min_level_num = LOG_LEVELS.get(min_level.upper(), 20)
        self._log_path = self._resolve_log_path()

    def set_correlation(self, correlation_id: str) -> "OSLogger":
        """パイプライン実行IDを設定（メソッドチェーン対応）"""
        self.correlation_id = correlation_id
        return self

    def new_correlation(self) -> str:
        """新しい correlation_id を生成して設定する"""
        cid = str(uuid.uuid4())[:8]
        self.correlation_id = cid
        return cid

    # ── レベル別ショートカット ────────────────────────────────────────────

    def debug(self, message: str, **kwargs):
        self._emit("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        self._emit("INFO", message, **kwargs)

    def warn(self, message: str, **kwargs):
        self._emit("WARN", message, **kwargs)

    def error(self, message: str, exc: Optional[Exception] = None, **kwargs):
        if exc is not None:
            kwargs["exception"] = str(exc)
            kwargs["traceback"] = traceback.format_exc()
        self._emit("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._emit("CRITICAL", message, **kwargs)

    # ── コアエミッター ────────────────────────────────────────────────────

    def _emit(self, level: str, message: str, **kwargs):
        if LOG_LEVELS.get(level, 0) < self._min_level_num:
            return

        record: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "stage": self.stage,
            "run_id": self.run_id,
            "msg": message,
        }
        if self.correlation_id:
            record["cid"] = self.correlation_id

        # 追加フィールドをマージ（ts/level/stage/run_id/msg は上書き禁止）
        for k, v in kwargs.items():
            if k not in record:
                record[k] = v

        line = json.dumps(record, ensure_ascii=False, default=str)

        # stdout にも表示（WARN 以上）
        if LOG_LEVELS.get(level, 0) >= LOG_LEVELS["WARN"]:
            print(f"[{level}][{self.stage}] {message}", file=sys.stderr)

        # ファイルに追記
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass  # ログ書き込み失敗でもアプリは止めない

    # ── パス解決 ─────────────────────────────────────────────────────────

    def _resolve_log_path(self) -> str:
        """VPS/ローカル環境でログパスを解決する"""
        # VPS 環境
        vps_log = "/opt/shared/logs/os_structured.log"
        if os.path.isdir("/opt/shared/logs"):
            return vps_log

        # ローカル環境
        os.makedirs(LOG_DIR, exist_ok=True)
        return os.path.join(LOG_DIR, "os_structured.log")

    # ── ユーティリティ ────────────────────────────────────────────────────

    @staticmethod
    def get_session_run_id() -> str:
        return _SESSION_RUN_ID

    def tail(self, n: int = 20) -> list:
        """直近 n 件のログレコードを返す（デバッグ用）"""
        if not Path(self._log_path).exists():
            return []
        lines = []
        try:
            with open(self._log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass
        return lines[-n:]
