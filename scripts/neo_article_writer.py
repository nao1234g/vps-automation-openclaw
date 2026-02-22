#!/usr/bin/env python3
"""
neo_article_writer.py — Breaking Pipeline Phase 2: NEOに記事生成を指示

breaking_queue.json の pending アイテムを取り出し、
元記事をスクレイプしてコンテキストを補強し、
NEO-ONE/TWO に Telethon 経由で記事執筆を指示する。

使い方:
  python3 neo_article_writer.py              # 1件処理
  python3 neo_article_writer.py --batch 5    # 5件まとめて指示
  python3 neo_article_writer.py --dry-run    # 指示内容を確認のみ
  python3 neo_article_writer.py --bot neo2   # NEO-TWOに指示

cron: */5 * * * * source /opt/cron-env.sh && python3 /opt/shared/scripts/neo_article_writer.py

フロー:
  breaking_queue.json (status=pending)
    → 元記事スクレイプ（URL取得）
    → NEOに Telethon で記事執筆指示
    → status を "writing" に変更
    → NEOが記事完成後に breaking_pipeline_helper.py を実行
    → status が "article_ready" に変わる
    → x_quote_repost.py が引用リポスト
"""

import asyncio
import json
import os
import sys
import subprocess
import argparse
from datetime import datetime, timezone, timedelta

QUEUE_FILE = "/opt/shared/scripts/breaking_queue.json"
SEND_SCRIPT = "/opt/shared/scripts/send-to-neo.py"
WRITING_TIMEOUT_MIN = 60  # writing状態で60分以上経過したら再送信

# カテゴリ → 日本語タクソノミーマッピング
CAT_TO_GENRE = {
    "総合": "社会",
    "経済": "経済・貿易",
    "金融": "金融・市場",
    "暗号資産": "暗号資産",
    "AI": "テクノロジー",
    "テック": "テクノロジー",
    "政治": "ガバナンス・法",
    "地政学": "地政学・安全保障",
    "国際": "地政学・安全保障",
    "速報": "社会",
    "エネルギー": "エネルギー",
}


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def get_pending_items(queue):
    """pending状態のアイテム（スコア順）"""
    pending = [q for q in queue if q.get("status") == "pending"]
    pending.sort(key=lambda x: (x.get("score", 0), x.get("likes", 0)), reverse=True)
    return pending


def get_stuck_writing(queue):
    """writing状態でタイムアウトしたアイテム"""
    now = datetime.now(timezone.utc)
    stuck = []
    for q in queue:
        if q.get("status") == "writing":
            started = q.get("writing_started_at", "")
            if started:
                try:
                    start_dt = datetime.fromisoformat(started)
                    if (now - start_dt) > timedelta(minutes=WRITING_TIMEOUT_MIN):
                        stuck.append(q)
                except (ValueError, TypeError):
                    stuck.append(q)
            else:
                stuck.append(q)
    return stuck


def extract_url(url_item):
    """article_urlsの要素からURL文字列を安全に取り出す"""
    if isinstance(url_item, str):
        return url_item
    if isinstance(url_item, dict):
        return url_item.get("url", url_item.get("expanded_url", ""))
    if isinstance(url_item, (list, tuple)) and len(url_item) > 0:
        return str(url_item[0])
    return str(url_item) if url_item else ""


def scrape_article_url(url, timeout=15):
    """元記事のURLからテキストを取得（ベストエフォート）"""
    if not url:
        return ""
    try:
        from curl_cffi import requests as cffi_requests
        from bs4 import BeautifulSoup

        resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "lxml")

        # 不要な要素を削除
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # article要素優先、なければbody
        article = soup.find("article")
        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # 長すぎる場合は切り詰め
        if len(text) > 5000:
            text = text[:5000] + "\n...(truncated)"

        return text.strip()
    except Exception as e:
        print(f"    スクレイプ失敗({url[:50]}): {e}")
        return ""


def _load_json(path):
    """JSONファイルを安全に読み込む"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_previous_article(item):
    """同じトピック（力学×ジャンル）の直近の前回記事を検索。

    Returns:
        dict or None: {
            "article_id", "title", "url", "published_at",
            "bottom_line", "scenarios", "dynamics_tags", "chain_count"
        }
    """
    cat = item.get("cat", "")
    genre = CAT_TO_GENRE.get(cat, "")
    if not genre:
        return None

    idx = _load_json("/opt/shared/nowpattern_article_index.json")
    db = _load_json("/opt/shared/scripts/prediction_db.json")

    # article_index のジャンルインデックスで同ジャンル記事を取得
    genre_article_ids = idx.get("genre_index", {}).get(genre, [])
    if not genre_article_ids:
        return None

    # 記事を日付降順でソート（最新が先頭）
    articles = idx.get("articles", [])
    genre_articles = []
    for a in articles:
        if a.get("article_id") in genre_article_ids:
            genre_articles.append(a)
    genre_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

    if not genre_articles:
        return None

    # 最新の記事を「前回」として返す
    prev = genre_articles[0]

    # prediction_dbから同記事のシナリオを検索
    prev_scenarios = []
    for p in db.get("predictions", []):
        if p.get("article_id") == prev.get("article_id"):
            prev_scenarios = p.get("scenarios", [])
            break

    # チェーンカウント: 同ジャンルの記事数 + 1（今回の記事）
    chain_count = len(genre_articles) + 1

    return {
        "article_id": prev.get("article_id", ""),
        "title": prev.get("title_ja", "") or prev.get("title_en", ""),
        "url": prev.get("url", ""),
        "published_at": prev.get("published_at", "")[:10],
        "bottom_line": prev.get("bottom_line", ""),
        "scenarios": prev_scenarios,
        "dynamics_tags": prev.get("dynamics_tags", []),
        "chain_count": chain_count,
    }


def build_delta_context(item):
    """NEOに渡すDelta差分情報のテキストと構造化データを生成。

    Returns:
        tuple: (delta_text: str, delta_data: dict or None)
        - delta_text: NEOへの指示に含めるテキスト
        - delta_data: article_builderに渡す構造化データ
    """
    prev = find_previous_article(item)
    if not prev:
        return "", None

    # 前回記事のシナリオが空の場合
    if not prev.get("scenarios"):
        delta_text = (
            f"【Delta — 前回記事との差分】\n"
            f"前回: {prev['title'][:60]} ({prev['published_at']})\n"
            f"URL: {prev['url']}\n"
            f"→ 前回の記事と比較して「何が変わったか」を具体的に分析してください。\n"
            f"→ delta_data の delta_reason に「なぜ変わったか」を1-2文で書いてください。\n"
            f"→ これはこのトピック{prev['chain_count']}回目の分析です。"
        )
        delta_data = {
            "prev_article_title": prev["title"][:60],
            "prev_article_url": prev["url"],
            "prev_article_date": prev["published_at"],
            "prev_scenarios": [],
            "current_scenarios": [],  # NEOが記事執筆時に埋める
            "delta_reason": "",  # NEOが記事執筆時に埋める
            "chain_count": prev["chain_count"],
        }
        return delta_text, delta_data

    # 前回シナリオありの場合: 構造化された差分情報を提供
    scenarios_str = ", ".join(
        f"{s.get('label', '')}({s.get('probability', 0)})"
        for s in prev["scenarios"]
    )
    bottom_line_str = f"前回のBOTTOM LINE: {prev['bottom_line']}" if prev.get("bottom_line") else ""

    delta_text = (
        f"【Delta — 前回記事との差分（重要: 必ず差分を分析すること）】\n"
        f"前回: {prev['title'][:60]} ({prev['published_at']})\n"
        f"URL: {prev['url']}\n"
        f"前回シナリオ: {scenarios_str}\n"
        f"{bottom_line_str}\n"
        f"\n"
        f"→ 前回のシナリオ確率と比較して、今回の分析で確率がどう変化したか明示してください。\n"
        f"→ delta_data の current_scenarios に今回の確率を入れてください。\n"
        f"→ delta_data の delta_reason に「なぜ確率が変わったか」を1-2文で書いてください。\n"
        f"→ これはこのトピック{prev['chain_count']}回目の分析です。"
    )
    delta_data = {
        "prev_article_title": prev["title"][:60],
        "prev_article_url": prev["url"],
        "prev_article_date": prev["published_at"],
        "prev_scenarios": [
            {"label": s.get("label", ""), "probability": s.get("probability", "")}
            for s in prev["scenarios"]
        ],
        "current_scenarios": [],  # NEOが記事執筆時に埋める
        "delta_reason": "",  # NEOが記事執筆時に埋める
        "chain_count": prev["chain_count"],
    }

    return delta_text, delta_data


def get_flywheel_context(item):
    """フライホイール: 同じカテゴリの過去予測と記事を取得してNEOに提供"""
    context_parts = []
    cat = item.get("cat", "")
    genre = CAT_TO_GENRE.get(cat, "")

    # 0. Delta（差分）情報
    delta_text, _delta_data = build_delta_context(item)
    if delta_text:
        context_parts.append(delta_text)

    # 1. prediction_db から同カテゴリのopen予測を検索
    try:
        db = _load_json("/opt/shared/scripts/prediction_db.json")
        related_preds = []
        for p in db.get("predictions", []):
            if p.get("status") == "open":
                p_genre = p.get("genre_tags", "")
                p_dynamics = p.get("dynamics_tags", "")
                if genre and (genre in p_genre or cat.lower() in p_dynamics.lower()):
                    related_preds.append(p)
        if related_preds:
            context_parts.append("\n【過去の関連予測（フライホイール参照）】")
            for rp in related_preds[:3]:
                scenarios_str = ", ".join(
                    f"{s.get('label','')}({s.get('probability',0)})"
                    for s in rp.get("scenarios", [])
                )
                context_parts.append(
                    f"- {rp['prediction_id']}: {rp.get('article_title','')[:60]}\n"
                    f"  シナリオ: {scenarios_str}\n"
                    f"  トリガー: {rp.get('open_loop_trigger','')[:80]}"
                )
            context_parts.append("→ 上記の予測を踏まえて、新しい記事の分析に活かしてください。")
    except Exception:
        pass

    # 2. article_index から同ジャンルの過去記事を検索
    try:
        idx = _load_json("/opt/shared/nowpattern_article_index.json")
        genre_articles = idx.get("genre_index", {}).get(genre, [])
        if genre_articles:
            context_parts.append(f"\n【同ジャンル({genre})の過去記事: {len(genre_articles)}件】")
            all_articles = idx.get("articles", [])
            for aid in genre_articles[-3:]:
                for a in all_articles:
                    if a.get("article_id") == aid:
                        context_parts.append(f"- {aid}: {a.get('title_ja','')[:50]} ({a.get('url','')})")
                        break
    except Exception:
        pass

    return "\n".join(context_parts)


def build_neo_instruction(item, scraped_text="", past_context=""):
    """NEOへの記事執筆指示メッセージを構築"""
    tweet_id = item.get("tweet_id", "")
    account = item.get("account", "?")
    lang = item.get("lang", "ja")
    cat = item.get("cat", "総合")
    text = item.get("text", "")
    tweet_url = item.get("tweet_url", "")
    article_urls = item.get("article_urls", [])
    likes = item.get("likes", 0)
    retweets = item.get("retweets", 0)
    genre = CAT_TO_GENRE.get(cat, "社会")

    # 記事言語の決定
    article_lang = "ja"  # nowpattern.comのメイン言語
    if lang == "en":
        article_lang = "ja"  # 英語ソースでも日本語記事を優先

    instruction = f"""■ ミッション: Nowpattern Breaking Pipeline — Now Report記事を執筆してGhostに投稿

【ツイートデータ】
- tweet_id: {tweet_id}
- tweet_url: {tweet_url}
- アカウント: @{account}
- 言語: {lang}
- カテゴリ: {cat}
- いいね: {likes} / RT: {retweets}
- テキスト:
{text}
"""

    if article_urls:
        instruction += f"\n【元記事URL】\n"
        for url_item in article_urls:
            url_str = extract_url(url_item)
            if url_str:
                instruction += f"- {url_str}\n"

    if scraped_text:
        instruction += f"\n【元記事本文（スクレイプ済み）】\n{scraped_text}\n"

    if past_context:
        instruction += f"\n{past_context}\n"

    instruction += f"""
【執筆要件 — Nowpattern v5.0 Delta Format】
1. 上記ツイート内容を分析し、Now Report（1,500-2,500語）を日本語で執筆
2. Deep Pattern v4.0フォーマットに従う:
   - BOTTOM LINE: 記事の核心を1文で（読者が3秒で理解）+ パターン名 + 基本シナリオ + 注目ポイント
   - 何が起きたか（事実の要約、300-400語）
   - なぜ重要か（構造的意味、300-400語）
   - Between the Lines: 公式発表が「言っていないこと」を1段落で。裏の力学、隠された意図を分析
   - パターンの正体（力学分析、400-500語）— 段落内の最重要フレーズを太字(strong)で強調
   - 主要プレイヤー（利害関係者、150-200語）
   - 今後の展望（3シナリオ+確率、200-300語）
   - Open Loop: 次のトリガーイベント+具体的日付、このパターンの追跡テーマ
3. 5要素チェック: 歴史・利害・論理・シナリオ・示唆
4. ジャンルタグ: {genre}
5. 力学タグ: 分析内容から最適な力学タグを1-2個選択
6. トーン: Matt Levine的な会話口調。読者の知性を尊重しつつ専門用語をかみ砕く。仮定対話OK。

【v5.0 フィールド（必ず埋めること）】
- bottom_line: 記事の核心を1文で
- bottom_line_pattern: 力学パターン名の要約
- bottom_line_scenario: 基本シナリオの一文要約
- bottom_line_watch: 次の注目イベント+日付
- between_the_lines: 報道が言っていない本当の話（1段落）
- open_loop_trigger: 次のトリガー+具体的日付
- open_loop_series: このパターンの次の追跡テーマ
- 各dynamics_sectionsのanalysis内で最重要フレーズをHTML <strong>タグで太字に

【v5.0 Delta（差分）フィールド】
- delta_data: 前回記事との差分情報（上記の【Delta】セクションに基づいて埋める）
  - current_scenarios: 今回の3シナリオ確率（前回との比較用）
  - delta_reason: 「なぜ確率が変わったか」を1-2文で
  ※ 前回記事がない場合は delta_data を空にする（chain_count: 1）
  ※ 前回記事がある場合、前回の確率と今回の確率を比較して変化量を明示する

【出力手順】
1. JSONテンプレートを読み込む:
   cat /opt/shared/scripts/breaking_article_template.json

2. テンプレートの各フィールドを記事内容で埋めて、以下のパスに保存:
   /tmp/article_{tweet_id}.json

   - tweet_id は "{tweet_id}" を使用
   - language は "{article_lang}"
   - genre_tags は "{genre}"
   - source_urls のURLは "{tweet_url}"
   - x_comment は200字以内の引用リポスト用コメント（裏読み型: 好奇心→分析→リンク→問いかけ）

3. Ghost投稿を実行:
   python3 /opt/shared/scripts/breaking_pipeline_helper.py /tmp/article_{tweet_id}.json

これによりGhostへの投稿とbreaking_queue.jsonの更新が自動で行われます。
完了後、記事URLを報告してください。"""

    return instruction


def send_to_neo(bot, message, dry_run=False):
    """Telethon経由でNEOにメッセージを送信"""
    if dry_run:
        print(f"  [DRY-RUN] {bot}への指示:")
        print(f"  {message[:200]}...")
        return True

    try:
        result = subprocess.run(
            ["python3", SEND_SCRIPT, "--bot", bot, "--msg", message],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"  ✅ {bot}に指示送信完了")
            return True
        else:
            print(f"  ❌ 送信失敗: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ 送信エラー: {e}")
        return False


def run_writer(batch_size=1, bot="neo1", dry_run=False):
    """メイン処理: キューからpendingを取り出してNEOに指示"""
    queue = load_queue()

    # 現在のステータス集計
    status_counts = {}
    for q in queue:
        s = q.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"📋 キュー状況: {len(queue)} 件")
    for s, c in sorted(status_counts.items()):
        print(f"   {s}: {c}")

    # タイムアウトした writing アイテムを pending に戻す
    stuck = get_stuck_writing(queue)
    if stuck:
        print(f"\n⚠️ {len(stuck)} 件が writing タイムアウト（{WRITING_TIMEOUT_MIN}分超過）→ pending に戻します")
        for item in stuck:
            item["status"] = "pending"
            item["writing_timeout_count"] = item.get("writing_timeout_count", 0) + 1
        if not dry_run:
            save_queue(queue)

    # pending アイテム取得
    pending = get_pending_items(queue)
    if not pending:
        print("\n処理対象がありません。")
        return

    print(f"\n📝 処理対象: {len(pending)} 件のうち {min(batch_size, len(pending))} 件を処理")

    # writing中のアイテム数を確認（同時に処理しすぎない）
    writing_count = sum(1 for q in queue if q.get("status") == "writing")
    max_concurrent = 3  # 同時writing上限
    available_slots = max(0, max_concurrent - writing_count)

    if available_slots == 0:
        print(f"\n⏳ 現在 {writing_count} 件が処理中（上限{max_concurrent}）。完了を待ちます。")
        return

    actual_batch = min(batch_size, len(pending), available_slots)
    sent_count = 0

    # NEO-ONE / NEO-TWO の交互使用
    bots = ["neo1", "neo2"]

    for i, item in enumerate(pending[:actual_batch]):
        tweet_id = item.get("tweet_id", "?")
        account = item.get("account", "?")
        text_preview = item.get("text", "")[:80]

        print(f"\n--- [{i+1}/{actual_batch}] @{account}: {text_preview}...")

        # 元記事スクレイプ（ベストエフォート）
        scraped_text = ""
        article_urls = item.get("article_urls", [])
        if article_urls:
            first_url = extract_url(article_urls[0])
            if first_url:
                print(f"  📰 元記事スクレイプ中: {first_url[:60]}...")
                scraped_text = scrape_article_url(first_url)
                if scraped_text:
                    print(f"  → {len(scraped_text)} 文字取得")
                else:
                    print(f"  → スクレイプ失敗（ツイートテキストのみで執筆）")

        # フライホイール: 同じ力学/ジャンルの過去予測を取得してNEOに提供
        past_context = get_flywheel_context(item)

        # NEO指示構築
        instruction = build_neo_instruction(item, scraped_text, past_context)

        # 送信先: 指定があればそれ、なければ交互
        target_bot = bot if bot != "auto" else bots[i % len(bots)]

        # 送信
        success = send_to_neo(target_bot, instruction, dry_run=dry_run)

        if success and not dry_run:
            item["status"] = "writing"
            item["writing_started_at"] = datetime.now(timezone.utc).isoformat()
            item["assigned_to"] = target_bot
            sent_count += 1

    if not dry_run:
        save_queue(queue)

    print(f"\n=== 完了: {sent_count} 件の記事執筆指示を送信 ===")


def main():
    parser = argparse.ArgumentParser(description="NEO記事生成トリガー（Breaking Pipeline Phase 2）")
    parser.add_argument("--batch", type=int, default=1, help="一度に処理する件数（デフォルト: 1）")
    parser.add_argument("--bot", default="neo1", choices=["neo1", "neo2", "auto"],
                        help="指示先（neo1/neo2/auto=交互）")
    parser.add_argument("--dry-run", action="store_true", help="送信せずに指示内容を確認のみ")
    args = parser.parse_args()

    run_writer(batch_size=args.batch, bot=args.bot, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
