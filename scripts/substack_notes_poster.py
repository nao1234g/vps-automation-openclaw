#!/usr/bin/env python3
"""
substack_notes_poster.py — Substack Notes 自動ティーザー投稿

Ghost記事公開後に、Substack Notes形式のティーザーを生成して投稿する。
Substack Notes = Substackの #1 成長エンジン（購読者の70%がNotes経由）。

フロー:
  1. prediction_db.json / Ghost APIから最新記事を取得
  2. 記事サマリー → Notes形式のティーザーに変換
  3. Substack Notes APIに投稿（または手動投稿用テキスト生成）

使い方:
  python3 substack_notes_poster.py --generate       # ティーザーテキスト生成（投稿はしない）
  python3 substack_notes_poster.py --generate --count 3  # 最新3件分を生成
  python3 substack_notes_poster.py --post            # Substack Notes に投稿
  python3 substack_notes_poster.py --dry-run         # 確認のみ

Notes戦略:
  - 記事公開直後にティーザーを投稿（初速ブースト）
  - 1日1〜2本（多すぎると逆効果）
  - 「好奇心ギャップ」型：核心をチラ見せ → 「全文はこちら」
  - 予測要素があれば「あなたはどう思う？」で議論を促進
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from urllib.parse import urlparse

from mission_contract import assert_mission_handshake

MISSION_HANDSHAKE = assert_mission_handshake(
    "substack_notes_poster",
    "generate or post Substack notes only under the shared founder mission contract",
)
PREDICTION_DB = "/opt/shared/scripts/prediction_db.json"
GHOST_URL = "https://nowpattern.com"
RELEASE_MANIFEST = "/opt/shared/reports/article_release_manifest.json"


# ── ティーザー生成 ──────────────────────────────────────────────

def generate_teaser_ja(pred: dict) -> str:
    """日本語記事 → Substack Notes ティーザー"""
    title = pred.get("article_title", "")
    ghost_url = pred.get("ghost_url", "")
    scenarios = pred.get("scenarios", [])
    dynamics = pred.get("dynamics_tags", "")
    open_loop = pred.get("open_loop_trigger", "")

    # 好奇心ギャップ型テンプレート
    lines = []

    # Hook: 核心をチラ見せ
    if scenarios:
        best = max(scenarios, key=lambda s: s.get("probability", 0))
        worst = min(scenarios, key=lambda s: s.get("probability", 0))
        lines.append(f"📊 {title}")
        lines.append("")
        lines.append(f"最も可能性の高いシナリオ: {best.get('label', '')}（{int(best.get('probability', 0)*100)}%）")
        if worst.get("probability", 0) > 0:
            lines.append(f"最も危険なシナリオ: {worst.get('label', '')}（{int(worst.get('probability', 0)*100)}%）")
    else:
        lines.append(f"📊 {title}")

    # 力学タグ（専門性のシグナル）
    if dynamics:
        lines.append("")
        lines.append(f"🔍 力学: {dynamics}")

    # CTA（行動喚起）
    lines.append("")
    if open_loop:
        lines.append(f"⏰ 次のトリガー: {open_loop}")
        lines.append("")

    lines.append("あなたはどのシナリオが実現すると思いますか？")
    lines.append("")

    if ghost_url:
        lines.append(f"📖 全文分析（無料）:")
        lines.append(ghost_url)

    return "\n".join(lines)


def generate_teaser_en(pred: dict) -> str:
    """英語記事 → Substack Notes ティーザー"""
    title = pred.get("article_title", "")
    ghost_url = pred.get("ghost_url", "")
    scenarios = pred.get("scenarios", [])
    dynamics = pred.get("dynamics_tags", "")

    lines = []

    if scenarios:
        best = max(scenarios, key=lambda s: s.get("probability", 0))
        lines.append(f"📊 {title}")
        lines.append("")
        lines.append(f"Most likely scenario: {best.get('label', '')} ({int(best.get('probability', 0)*100)}%)")
    else:
        lines.append(f"📊 {title}")

    if dynamics:
        lines.append("")
        lines.append(f"🔍 Pattern dynamics: {dynamics}")

    lines.append("")
    lines.append("Which scenario do you think will play out?")
    lines.append("")

    if ghost_url:
        en_url = ghost_url.replace("nowpattern.com/", "nowpattern.com/en/") \
            if "/en/" not in ghost_url else ghost_url
        lines.append(f"📖 Full analysis (free):")
        lines.append(en_url)

    return "\n".join(lines)


# ── メイン ──────────────────────────────────────────────────────

def load_recent_predictions(count: int = 3) -> list:
    """最新の予測をロード"""
    if not os.path.exists(PREDICTION_DB):
        print(f"ERROR: {PREDICTION_DB} が見つかりません")
        return []

    with open(PREDICTION_DB, "r", encoding="utf-8") as f:
        data = json.load(f)

    preds = data.get("predictions", [])
    # published_at の新しい順にソート
    preds.sort(key=lambda p: p.get("published_at", ""), reverse=True)
    return preds[:count]


def load_release_manifest() -> dict:
    if not os.path.exists(RELEASE_MANIFEST):
        return {}
    with open(RELEASE_MANIFEST, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {row.get("slug", ""): row for row in data.get("posts", [])}


def slug_from_url(url: str) -> str:
    path = urlparse(url or "").path.strip("/")
    if not path:
        return ""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return ""
    if parts[0] == "en" and len(parts) > 1:
        return "en-" + parts[-1]
    return parts[-1]


def generate_notes(count: int = 3, lang: str = "both"):
    """Substack Notes ティーザーを生成"""
    preds = load_recent_predictions(count)
    manifest = load_release_manifest()

    if not preds:
        print("生成対象の予測がありません。")
        return []

    notes = []
    for i, pred in enumerate(preds):
        ghost_url = pred.get("ghost_url", "")
        slug = slug_from_url(ghost_url)
        manifest_row = manifest.get(slug, {})
        if not ghost_url or not manifest_row.get("distribution_allowed"):
            print(f"\n[SKIP] distribution blocked: {pred.get('prediction_id', '')} -> {ghost_url or 'no ghost_url'}")
            continue

        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(preds)}] {pred.get('prediction_id', '')} — {pred.get('article_title', '')[:50]}...")
        print(f"{'='*60}")

        if lang in ("ja", "both"):
            teaser_ja = generate_teaser_ja(pred)
            print("\n--- 日本語 Notes ---")
            print(teaser_ja)
            notes.append({
                "lang": "ja",
                "prediction_id": pred["prediction_id"],
                "text": teaser_ja,
                "ghost_url": ghost_url,
                "distribution_approved": True,
            })

        if lang in ("en", "both"):
            teaser_en = generate_teaser_en(pred)
            print("\n--- English Notes ---")
            print(teaser_en)
            notes.append({
                "lang": "en",
                "prediction_id": pred["prediction_id"],
                "text": teaser_en,
                "ghost_url": ghost_url,
                "distribution_approved": True,
            })

    return notes


def post_to_substack(notes: list, dry_run: bool = False):
    """Substack Notes API に投稿

    NOTE: Substack には公式の Notes API が存在しない（2026年3月時点）。
    投稿方法:
      1. 手動: generate で生成したテキストをSubstackアプリからコピペ
      2. 自動: Seleniumで自動投稿（Cookie認証）— 将来実装
      3. API: Substack が Notes API を公開した場合に対応
    """
    blocked = [note for note in notes if not note.get("distribution_approved")]
    if blocked:
        print(f"ERROR: {len(blocked)} note(s) are not approved for distribution")
        return

    if dry_run:
        print("\n[DRY RUN] 投稿をスキップ")
        return

    print("\n⚠️  Substack Notes には公式APIがありません（2026年3月時点）。")
    print("生成されたティーザーテキストを手動でSubstackアプリからコピペしてください。")
    print("\n代替自動化オプション:")
    print("  1. Selenium + connect.sid Cookie でブラウザ自動操作")
    print("  2. Substack の非公開 API エンドポイント利用（不安定）")
    print("  3. Substack が公式 Notes API を公開するのを待つ")

    # 将来の自動投稿用にJSONファイルに保存
    output_path = "/opt/shared/scripts/substack_notes_queue.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        print(f"\n📋 ティーザーキューを保存: {output_path}")
    except Exception:
        # ローカル実行時はスキップ
        pass


def main():
    parser = argparse.ArgumentParser(description="Substack Notes ティーザー自動生成")
    parser.add_argument("--generate", action="store_true", help="ティーザーテキスト生成")
    parser.add_argument("--post", action="store_true", help="Substack Notesに投稿")
    parser.add_argument("--count", type=int, default=3, help="処理する記事数")
    parser.add_argument("--lang", choices=["ja", "en", "both"], default="both",
                        help="言語（デフォルト: both）")
    parser.add_argument("--dry-run", action="store_true", help="確認のみ")
    args = parser.parse_args()

    if args.generate or args.post:
        notes = generate_notes(count=args.count, lang=args.lang)
        if args.post:
            post_to_substack(notes, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
