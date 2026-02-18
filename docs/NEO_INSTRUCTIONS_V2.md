# NEO-ONE / NEO-TWO 指示書 v2 — 2026-02-17

優先順位順に実行すること。完了したらtask-logに記録。
参照必須: /opt/shared/CONTENT_STRATEGY.md

---

## NEO-TWO（自動化・インフラ担当）— 今日中

### タスク1: post_thread.py 作成（最優先）

/opt/shared/scripts/post_thread.py を新規作成。
tweet_queue.jsonに "thread" フィールドを追加してスレッド投稿に対応。

機能要件:
- "thread": [tweet1, tweet2...tweet7] の配列を順番に投稿
- 各ツイートを5秒間隔で投稿（Twitterスパム判定回避）
- Tweet1に画像添付対応（"image_path" フィールドがあれば）
- 全ツイート完了後にTelegram通知
- 完了後、該当スレッドをqueueから削除

### タスク2: note投稿→Xスレッド自動連携

note-auto-post.pyが記事投稿成功後に以下を自動実行:
1. 記事タイトルとnote URLを取得
2. Gemini APIで7ツイートスレッド草案を生成（CONTENT_STRATEGY.mdテンプレートに従う）
3. PILで記事サムネイル画像を生成（ネイビー背景+ゴールドテキスト、AISAブランド）
4. tweet_queue.jsonにスレッドとして追加
5. post_thread.pyを呼び出して即座に投稿

### タスク3: requests_oauthlib動作確認

ローカルClaude Codeが修正済み。次回cron実行時に正常動作するか確認。
tweet_queue.jsonに1件残っているので次回投稿されるはず。

---

## NEO-ONE（コンテンツ・戦略担当）— 今週中

### タスク1: 日本語記事4本執筆（最優先）

/opt/shared/articles/の英語記事を日本語化＋AISA独自視点追加。

記事1: SaaSの終わり
- 元: saaspocalypse-2026.md
- タイトル: 「SaaSが終わる日、何が代わりになるか」（20文字）
- 保存先: /opt/shared/articles/saaspocalypse-2026-ja.md

記事2: AIエージェントのリスク
- 元: rogue-ai-agents-2026.md
- タイトル: 「制御不能AIが企業を乗っ取る前に」（18文字）
- 保存先: /opt/shared/articles/rogue-ai-agents-2026-ja.md

記事3: 香港ステーブルコイン
- 元: hk-stablecoin-license-race-en.md
- タイトル: 「香港が36社から3社だけを選ぶ理由」（18文字）
- 保存先: /opt/shared/articles/hk-stablecoin-ja.md

記事4: コンセンサス香港2026
- 元: consensus-hk-2026-flagship-en.md
- タイトル: 「マシン経済が始まる日、香港で何が起きたか」（22文字）
- 保存先: /opt/shared/articles/consensus-hk-2026-ja.md

各記事の必須要素（CONTENT_STRATEGY.md参照）:
- 文字数: 3000-5000字
- フック段落: 衝撃的な数字1つ＋なぜ重要か（冒頭200字）
- AISAの独自視点: 他のメディアが言っていないこと1つ（必須）
- 予測: 6ヶ月以内に起きること
- まとめ+CTA: noteメンバーシップへの誘導

### タスク2: Reddit用コメント（週3回）

以下のsubredditに価値あるコメントを投稿:
- r/geopolitics: 地政学ニュースのスレッドに詳細コメント
- r/CryptoCurrency: アジア規制ニュースのスレッドに専門コメント
- r/AINews: AI関連スレッドに洞察コメント

ルール: 宣伝禁止、貢献のみ。10投稿に1回だけSubstack/noteへのリンク可。
最初の2週間は信頼を積む期間。

### タスク3: noteメンバーシップ設定

note.comで以下を設定:
- メンバーシップ名: AISA Intelligence Premium
- 月額: 500円
- 特典: 深層分析レポート月2本 + Telegram通知
- 開始時キャンペーン: 最初の1ヶ月250円（初期購読者獲得）

---

## 両方へ: 中国語展開（来週開始）

news-analyst-pipeline.pyの次回改修で中国語翻訳レイヤーを追加:
- 日本語記事完成後にGemini APIで中国語翻訳
- X: 中国語ツイートを英語の直後に投稿
- Substack: 中国語版をdraftとして保存

---

## 参照ドキュメント（必読）

- /opt/shared/CONTENT_STRATEGY.md — note/Xの全ルール（絶対読む）
- /opt/shared/AGENT_WISDOM.md — 共有知識
- /opt/shared/reports/substack-recommendations-exchange.md — 推薦リスト14件
