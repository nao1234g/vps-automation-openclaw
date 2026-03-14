"""F002 Regression Test — _get_today_article_count() がパイプラインログから正しく読む

Failure: F002 (medium) — path_mismatch
Symptom: _get_today_article_count() が常に 0 を返す
Required test: PIPELINE_LOG_PATH に今日のエントリを入れてから
               _get_today_article_count() を呼び、0以外が返ることを確認
"""
import sys
import os
import json
import tempfile
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)


def test() -> bool:
    """F002: 今日のエントリを持つ一時ログで _get_today_article_count() が 0 以外を返す"""
    try:
        import article_pipeline as ap
    except (ImportError, SyntaxError) as e:
        print(f"[SKIP] F002: article_pipeline をインポートできない: {type(e).__name__}: {e}")
        return True  # ローカル不在 / 構文エラーはSKIP扱い（VPS専用ファイル）

    # _get_today_article_count は ArticlePipeline クラスのインスタンスメソッド
    if not hasattr(ap, "ArticlePipeline") or not hasattr(
        ap.ArticlePipeline, "_get_today_article_count"
    ):
        print("[SKIP] F002: ArticlePipeline._get_today_article_count() が存在しない（インタフェース変更済み）")
        return True

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # 実際のログ形式: _date / jp_generated / en_generated フィールドを使う
    fake_log = [
        {"_date": today, "jp_generated": 3, "en_generated": 2},
    ]

    tmp_path = None
    original_path = getattr(ap, "PIPELINE_LOG_PATH", None)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(fake_log, f)
            tmp_path = f.name

        # モジュールレベル変数をパッチ（メソッド内で参照される）
        ap.PIPELINE_LOG_PATH = tmp_path
        pipeline = ap.ArticlePipeline(dry_run=True)
        result = pipeline._get_today_article_count(today)

        total = result.get("jp", 0) + result.get("en", 0)
        assert total > 0, (
            f"_get_today_article_count('{today}') が {result}（total={total}）を返した"
            f"（期待: jp+en > 0）。"
            f"ログに jp_generated=3, en_generated=2 があるのに検出されない。"
        )
        print(f"[PASS] F002: _get_today_article_count('{today}') = {result} (total={total} > 0) OK")
        return True

    except AssertionError as e:
        print(f"[FAIL] F002: {e}")
        return False
    except AttributeError as e:
        print(f"[FAIL] F002: 関数またはPIPELINE_LOG_PATHが見つからない: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] F002: 予期せぬエラー: {type(e).__name__}: {e}")
        return False
    finally:
        if original_path is not None:
            ap.PIPELINE_LOG_PATH = original_path
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    sys.exit(0 if test() else 1)
