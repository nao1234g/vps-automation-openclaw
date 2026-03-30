#!/usr/bin/env python3
"""
breaking_pipeline_helper.py — NEOが生成した記事JSONをGhostに投稿 + キュー更新

NEOが記事を分析・執筆した後、このスクリプトを呼び出して:
1. 記事JSONからHTML生成（nowpattern_article_builder.py）
2. Ghost CMSに投稿（nowpattern_publisher.py）
3. breaking_queue.jsonを更新（status → article_ready）
4. X引用リポスト用コメントを保存

使い方（NEOが実行）:
  python3 breaking_pipeline_helper.py /tmp/article_12345.json
  python3 breaking_pipeline_helper.py /tmp/article_12345.json --dry-run

JSON入力フォーマット:
{
  "tweet_id": "123456789",
  "title": "記事タイトル",
  "language": "ja",
  "why_it_matters": "なぜ重要か（2-3文）",
  "facts": [["ラベル", "内容"], ...],
  "big_picture_history": "歴史的背景（段落テキスト）",
  "stakeholder_map": [["アクター", "建前", "本音", "得るもの", "リスク"], ...],
  "data_points": [["数字", "意味"], ...],
  "dynamics_tags": "力学タグ × 力学タグ2",
  "dynamics_summary": "力学の要約",
  "dynamics_sections": [{"tag": "...", "subheader": "...", "lead": "...", "analysis": "..."}],
  "dynamics_intersection": "力学の交差分析",
  "pattern_history": [{"year": 2020, "title": "...", "content": "...", "similarity": "..."}],
  "history_pattern_summary": "パターン史まとめ",
  "scenarios": [["楽観", "30%", "内容", "示唆"], ["基本", "50%", "...", "..."], ["悲観", "20%", "...", "..."]],
  "triggers": [["トリガー", "時期"], ...],
  "genre_tags": "テクノロジー",
  "event_tags": "規制・法改正",
  "source_urls": [["名前", "URL"], ...],
  "x_comment": "引用リポスト用コメント（200字以内）"
}
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone

from article_release_guard import evaluate_release_blockers

QUEUE_FILE = "/opt/shared/scripts/breaking_queue.json"
SCRIPTS_DIR = "/opt/shared/scripts"

# Ghost設定
GHOST_URL = "https://nowpattern.com"


def load_env():
    """cron-env.sh から環境変数を読み込む"""
    env_file = "/opt/cron-env.sh"
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    key_val = line[7:]  # remove "export "
                    key, val = key_val.split("=", 1)
                    val = val.strip('"').strip("'")
                    os.environ[key] = val


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def build_html(article_data):
    """nowpattern_article_builder.py を使ってHTML生成"""
    sys.path.insert(0, SCRIPTS_DIR)
    from nowpattern_article_builder import build_deep_pattern_html

    # dynamics_sections にquotesが無い場合は空リストを追加
    for section in article_data.get("dynamics_sections", []):
        if "quotes" not in section:
            section["quotes"] = []

    html = build_deep_pattern_html(
        title=article_data["title"],
        why_it_matters=article_data["why_it_matters"],
        facts=[tuple(f) for f in article_data["facts"]],
        big_picture_history=article_data.get("big_picture_history", ""),
        stakeholder_map=[tuple(s) for s in article_data.get("stakeholder_map", [])],
        data_points=[tuple(d) for d in article_data.get("data_points", [])],
        dynamics_tags=article_data.get("dynamics_tags", ""),
        dynamics_summary=article_data.get("dynamics_summary", ""),
        dynamics_sections=article_data.get("dynamics_sections", []),
        dynamics_intersection=article_data.get("dynamics_intersection", ""),
        pattern_history=article_data.get("pattern_history", []),
        history_pattern_summary=article_data.get("history_pattern_summary", ""),
        scenarios=[tuple(s) for s in article_data.get("scenarios", [])],
        triggers=[tuple(t) for t in article_data.get("triggers", [])],
        genre_tags=article_data.get("genre_tags", ""),
        event_tags=article_data.get("event_tags", ""),
        source_urls=[tuple(s) for s in article_data.get("source_urls", [])],
        related_articles=article_data.get("related_articles", []),
        diagram_html=article_data.get("diagram_html", ""),
        language=article_data.get("language", "ja"),
        # v4.0 Flywheel additions
        bottom_line=article_data.get("bottom_line", ""),
        bottom_line_pattern=article_data.get("bottom_line_pattern", ""),
        bottom_line_scenario=article_data.get("bottom_line_scenario", ""),
        bottom_line_watch=article_data.get("bottom_line_watch", ""),
        between_the_lines=article_data.get("between_the_lines", ""),
        open_loop_trigger=article_data.get("open_loop_trigger", ""),
        open_loop_series=article_data.get("open_loop_series", ""),
        prediction_id=article_data.get("prediction_id", ""),
    )
    return html


def publish_to_ghost(article_data, html, dry_run=False):
    """Ghost CMSに投稿

    v3.0変更点:
    - タグはtaxonomy.jsonに基づいてSTRICTバリデーション
    - 不正タグがあれば投稿をブロック（ValueErrorを送出）
    - 実際のGhost APIレスポンスURLを使用（slug truncation防止）
    """
    sys.path.insert(0, SCRIPTS_DIR)
    from nowpattern_publisher import publish_deep_pattern, generate_article_id

    admin_api_key = os.environ.get("NOWPATTERN_GHOST_ADMIN_API_KEY", "")
    if not admin_api_key:
        print("ERROR: NOWPATTERN_GHOST_ADMIN_API_KEY が設定されていません")
        return None

    article_id = generate_article_id("deep_pattern")
    lang = article_data.get("language", "ja")

    # タグをリストに変換（区切り文字: "/" or "×"）
    genre_list = [t.strip() for t in article_data.get("genre_tags", "").split("/") if t.strip()]
    event_list = [t.strip() for t in article_data.get("event_tags", "").split("/") if t.strip()]
    dynamics_list = [t.strip() for t in article_data.get("dynamics_tags", "").replace("×", "/").split("/") if t.strip()]

    if dry_run:
        print(f"  [DRY-RUN] Ghost投稿: {article_data['title']}")
        print(f"  [DRY-RUN] Article ID: {article_id}")
        print(f"  [DRY-RUN] Tags: {genre_list + event_list + dynamics_list}")
        return {
            "url": f"https://nowpattern.com/dry-run-{article_id}/",
            "article_id": article_id,
        }

    # publish_deep_pattern()がSTRICTバリデーションを行い、
    # 不正タグがあればValueErrorで投稿をブロックする
    release_block = evaluate_release_blockers(
        title=article_data["title"],
        html=html,
        source_urls=[u[1] if isinstance(u, (list, tuple)) else u for u in article_data.get("source_urls", [])],
        tags=genre_list + event_list + dynamics_list + [f"lang-{lang}"],
        site_url=GHOST_URL,
        status="published",
        channel="public",
        require_external_sources=True,
        check_source_fetchability=True,
    )
    blocking_errors = [
        err for err in release_block["errors"]
        if not err.startswith("HUMAN_APPROVAL_REQUIRED:")
    ]
    if blocking_errors:
        raise ValueError("release blocker: " + ", ".join(blocking_errors))

    publish_status = "published"
    if release_block["human_approval_required"] and not release_block["human_approval_present"]:
        publish_status = "draft"
        print(f"  High-risk article forced to DRAFT pending human approval: {release_block['risk_flags']}")

    result = publish_deep_pattern(
        article_id=article_id,
        title=article_data["title"],
        html=html,
        genre_tags=genre_list,
        event_tags=event_list,
        dynamics_tags=dynamics_list,
        dynamics_tags_en=[],
        source_urls=[u[1] if isinstance(u, (list, tuple)) else u for u in article_data.get("source_urls", [])],
        related_article_ids=[],
        pattern_history_cases=article_data.get("pattern_history", []),
        word_count_ja=len(html) // 3,  # rough estimate
        title_en=article_data["title"] if lang == "en" else "",
        ghost_url=GHOST_URL,
        admin_api_key=admin_api_key,
        status=publish_status,
        index_path="/opt/shared/scripts/nowpattern_article_index.json",
    )

    return result


def update_queue(tweet_id, ghost_url, x_comment, dry_run=False):
    """breaking_queue.json のステータスを article_ready に更新"""
    queue = load_queue()
    updated = False

    for item in queue:
        if item.get("tweet_id") == tweet_id:
            item["status"] = "article_ready"
            item["ghost_url"] = ghost_url
            item["x_comment"] = x_comment
            item["article_completed_at"] = datetime.now(timezone.utc).isoformat()
            updated = True
            break

    if updated and not dry_run:
        save_queue(queue)
        print(f"  ✅ キュー更新: tweet_id={tweet_id} → article_ready")
    elif not updated:
        print(f"  ⚠️ tweet_id={tweet_id} がキューに見つかりません")

    return updated


def main():
    parser = argparse.ArgumentParser(description="Breaking Pipeline Helper — 記事JSON → Ghost投稿 + キュー更新")
    parser.add_argument("json_file", help="NEOが生成した記事JSONファイルのパス")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずに確認のみ")
    args = parser.parse_args()

    # 環境変数読み込み
    load_env()

    # JSON読み込み
    if not os.path.exists(args.json_file):
        print(f"ERROR: ファイルが見つかりません: {args.json_file}")
        sys.exit(1)

    with open(args.json_file, "r", encoding="utf-8") as f:
        article_data = json.load(f)

    tweet_id = article_data.get("tweet_id", "")
    title = article_data.get("title", "無題")
    x_comment = article_data.get("x_comment", "")

    print(f"📝 記事処理開始: {title}")
    print(f"   tweet_id: {tweet_id}")

    # Step 0: v4.0 フォーマットバリデーション（公開ゲート）
    print("  Step 0: フォーマットバリデーション...")
    try:
        sys.path.insert(0, SCRIPTS_DIR)
        from article_validator import validate_article
        is_valid, errors, warnings = validate_article(article_data)
        if not is_valid:
            print(f"  🚫 バリデーション不合格 — 公開ブロック")
            print(f"     エラー: {'; '.join(errors)}")
            print(f"     → ARTICLE_FORMAT_SPEC.md を参照してv4.0フィールドを追加してください")
            sys.exit(1)
        print(f"  → バリデーション合格 ✅")
    except ImportError:
        print(f"  ⚠️ article_validator.py が見つかりません（バリデーション スキップ）")

    # Step 1: HTML生成
    print("  Step 1: HTML生成中...")
    try:
        html = build_html(article_data)
        print(f"  → HTML生成完了（{len(html):,} bytes）")
    except Exception as e:
        print(f"  ❌ HTML生成失敗: {e}")
        sys.exit(1)

    # Step 2: Ghost投稿
    print("  Step 2: Ghost投稿中...")
    try:
        result = publish_to_ghost(article_data, html, dry_run=args.dry_run)
        if result:
            ghost_url = result.get("url", "")
            print(f"  → Ghost投稿完了: {ghost_url}")
        else:
            print("  ❌ Ghost投稿失敗")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ Ghost投稿失敗: {e}")
        sys.exit(1)

    # Step 3: キュー更新
    print("  Step 3: キュー更新中...")
    update_queue(tweet_id, ghost_url, x_comment, dry_run=args.dry_run)

    # Step 4: 予測追跡DBに記録（v4.0 Flywheel）
    print("  Step 4: 予測追跡DB記録中...")
    try:
        from prediction_tracker import record_prediction, update_ghost_url
        prediction_id = record_prediction(args.json_file)
        if prediction_id and ghost_url:
            update_ghost_url(prediction_id, ghost_url)
            # 記事JSONにprediction_idを書き戻し（テンプレートに反映用）
            article_data["prediction_id"] = prediction_id
        print(f"  → 予測記録完了: {prediction_id}")
    except Exception as e:
        print(f"  ⚠️ 予測記録失敗（記事投稿には影響なし）: {e}")

    print(f"\n=== 完了 ===")
    print(f"  記事: {title}")
    print(f"  URL: {ghost_url}")
    if article_data.get("prediction_id"):
        print(f"  Prediction ID: {article_data['prediction_id']}")
    print(f"  X引用コメント: {x_comment[:80]}...")


if __name__ == "__main__":
    main()
