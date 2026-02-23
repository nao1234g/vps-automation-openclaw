# Hey Loop v2.0 — 設計図

> **コア哲学**: 最高の知性（Opus 4.6）を最高の頻度で使い、閉ループで複利を回す
> **実装スクリプト**: `scripts/intelligence-feed-v2.py`
> **最終更新**: 2026-02-23

---

## なぜ v2.0 が必要か

| 項目 | v1（daily-learning.py） | v2.0（intelligence-feed-v2.py） |
|------|------------------------|--------------------------------|
| 判断エンジン | Gemini Flash（低品質） | **Opus 4.6（最高品質、定額）** |
| 収集頻度 | 1日4回（6時間ごと） | **30分〜1時間（最高頻度）** |
| AIツール追跡 | 一般的 | **Claude Code/OpenClaw 特別監視** |
| コンテキスト方式 | 50KBをプロンプトに直貼り | **ファイル経由（9割削減）** |
| 閉ループ | なし | **state.json で複利学習** |

---

## アーキテクチャ全体像

```
世界のシグナル
  [RSS 30分] [Reddit 1h] [HN 1h] [GitHub 3h] [Grok X 6h]
                     ↓
           raw_YYYY-MM-DD_HHmm.json
                     ↓
         claude --print "このファイルを読め"
           --allowedTools "Read"
         [Opus 4.6 — 全判断 — 3時間ごと]
           ↑ state.json（前回文脈）
                     ↓
           synthesis_YYYY-MM-DD_HH.json
                     ↓
         [Telegram → Naoto（200字以内）]
                     ↓
           state.json 更新（閉ループ）
                     ↓（週1回）
         [Opus 自己進化: 何が効いたか分析]
           → AGENT_WISDOM.md 更新
           → 収集トピック自動調整
```

---

## Layer 0: 収集ソース（Python only、LLMなし）

### 1. RSS フィード（30分ごと）

| フィード | URL | 目的 |
|---------|-----|------|
| Anthropic Blog | https://www.anthropic.com/rss.xml | **Claude/Claude Code 最新情報** |
| Hugging Face Blog | https://huggingface.co/blog.rss | モデルリリース、AI動向 |
| arXiv cs.AI | https://arxiv.org/rss/cs.AI | 研究動向（AGIへの道） |
| arXiv cs.LG | https://arxiv.org/rss/cs.LG | 機械学習論文 |
| VentureBeat AI | https://venturebeat.com/category/ai/feed/ | AI業界ニュース・資金調達 |
| TechCrunch AI | https://techcrunch.com/tag/artificial-intelligence/feed/ | 新サービス・スタートアップ |
| The Verge AI | https://www.theverge.com/ai-artificial-intelligence/rss/index.xml | 一般向けAI動向 |
| MIT Technology Review | https://www.technologyreview.com/tag/artificial-intelligence/feed/ | 深い分析・研究動向 |

### 2. Reddit（1時間ごと）

**AIツール追跡（最重要）**:
- `r/ClaudeAI` — Claude Code の実際の使い方・Tips・問題報告
- `r/LocalLLaMA` — オープンソースモデル動向（OpenClawの競合含む）
- `r/AIAgents` — AIエージェントツール比較・新サービス

**AI業界全般**:
- `r/MachineLearning`, `r/artificial`, `r/Singularity`

**収益シグナル**:
- `r/SideProject`, `r/SaaS`, `r/indiehackers`, `r/Entrepreneur`, `r/EntrepreneurRideAlong`

**インフラ**:
- `r/selfhosted`, `r/n8n`, `r/docker`

### 3. Hacker News（1時間ごと）

キーワード: `claude`, `claude code`, `open-claw`, `openclaw`, `ai agent`, `llm`, `gpt`, `gemini`, `grok`, `cursor`, `copilot`, `devin`, `automation`, `n8n`, `revenue`, `mrr`, `saas`, `newsletter`, `openai`, `anthropic`, `deepmind`, `model release`, `ai tool`, `indie hacker`

### 4. GitHub リリース監視（3時間ごと）

**最重要（Claude Code / OpenClaw 専用）**:
| リポジトリ | 理由 |
|------------|------|
| `anthropics/claude-code` | **Claude Code 本体** — 新機能・Breaking Change を即検知 |
| `open-claw/open-claw` | **OpenClaw** — セキュリティ修正・新機能 |
| `anthropics/anthropic-sdk-python` | SDK アップデート → NEO への影響確認 |

**AIエージェントツール比較（競合追跡）**:
| リポジトリ | 理由 |
|------------|------|
| `getcursor/cursor` | Cursor のアップデート速度 |
| `continuedev/continue` | VSCode AI完全代替候補 |
| `BerriAI/litellm` | LLMルーター（コスト最適化の鍵） |
| `langgenius/dify` | AIエージェント構築ツール |
| `microsoft/autogen` | Microsoftのマルチエージェント |
| `joaomdmoura/crewAI` | AIチーム構築フレームワーク |
| `n8n-io/n8n` | 使用中ツールの更新 |
| `Mintplex-Labs/anything-llm` | ローカルLLMツール |

### 5. Grok X/Twitter 検索（6時間ごと、xAI API）

> ⚠️ **【重要な使い分け — 絶対に混同しないこと】**
>
> | API | 用途 | 理由 |
> |-----|------|------|
> | **Grok / xAI API** | **X(Twitter)検索のみ** | xAI社とX Corp は同一オーナー。Grok APIはX投稿のリアルタイム検索に特権的アクセスを持つ。検索はこれが最安・最高精度。 |
> | **X API (v2)** | **投稿（ポスト）のみ** | 2026年にサブスクリプション廃止 → Pay-Per-Use（従量課金）に変更。「Free」は名前だけで実際は$5クレジット購入必須。検索には使わない。 |
>
> **まとめ: X(Twitter)の検索 = Grok API。X(Twitter)への投稿 = X API（Pay-Per-Use）。**
>
> ❌ 絶対に「X API Basic $100/月」のような情報を参照しないこと（2025年以前の古い情報）

4クエリをローテーション:
1. Claude Code 最新Tips・Power User報告（@cursor_ai vs @AnthropicAI 比較含む）
2. AI自動化で収益化した人の$MRR/収益報告
3. 新AIサービス・ツールのローンチ報告（Product Hunt風）
4. AIモデル料金変更・無料枠変更の報告

---

## Layer 1: Opus 4.6 全判断

### 「9割削減」技術

```python
# ❌ 旧方式: 50KBをプロンプトに直貼り → 12,500トークン
response = gemini(prompt=f"分析して: {50kb_of_data}")

# ✅ 新方式: ファイル経由 → プロンプト ~50トークン
with open("/opt/shared/intelligence/raw/latest.json", "w") as f:
    json.dump(collected_data, f)

result = subprocess.run([
    "claude", "--print",
    "Read /opt/shared/intelligence/raw/latest.json を読んで、"
    "JSON形式で分析を出力してください。",
    "--allowedTools", "Read",
    "--output-format", "text"
], capture_output=True, text=True)
```

- `claude --print` = 毎回新鮮セッション（前会話が蓄積しない）
- データはファイル → Read ツールで取得（プロンプトに含まれない）
- Opus は **全判断** を担当（フィルタ・優先順位・アクション提案）

### Opus が判断すること

1. **Claude Code/OpenClaw 変化検知**: 新バージョン、機能追加、Breaking Change
2. **AIエージェントツールの勢力図変化**: 「OpenClawより良いものが出た」を検知
3. **AI業界の重要発展**: 新モデル、料金変更、サービス廃止
4. **収益シグナル**: 誰がいくら稼いでいるか（手法付き）
5. **記事候補**: Nowpattern に最適なテーマ（力学・地政学的重要性）
6. **インフラアラート**: 使用ツールの更新・脆弱性
7. **Naotoへの今日の1アクション**: 最高価値の具体的行動1件

---

## Layer 2: Telegram 報告（3時間ごと）

```
🤖 Hey Loop Report 06:00 JST

🔥 最重要: Claude Code v1.3.0リリース — /project コマンド追加
   → 今すぐNEO-ONEのCLAUDE.mdでproject-specific rulesを設定すべき

📊 AI動向:
  • Anthropic、Claude 4 Opus料金40%値下げ（即時有効）
  • OpenClaw v2026.3.0 — セキュリティ修正3件（更新推奨）

💰 収益シグナル:
  • @ai_solobuilder が Substack AI Newsletter で $8k MRR達成

📰 記事候補:
  • 「AIエージェント戦争2026：Claude vs Cursor vs Devin」

─────────────────
[前回から変化なし: GitHub 12件 / Reddit 45件 / HN 8件 確認済]
```

**200字以内。読むのに10秒。**

---

## Layer 3: 閉ループ（state.json）

```json
{
  "last_synthesis": "2026-02-23T06:00:00+09:00",
  "acted_on": ["Claude Code v1.3.0 確認済み", "AGENT_WISDOM.md更新"],
  "skipped": ["n8nリリース — 当面変更不要"],
  "top_claude_code_version": "v1.2.5",
  "top_openclaw_version": "v2026.2.21",
  "known_best_ai_agent_tool": "open-claw",
  "article_pipeline": ["AIエージェント戦争2026（未着手）"],
  "next_context": "Claude 4 Opus値下げ後のコスト試算を次回確認すること"
}
```

次回 Opus はこの `state.json` を読んで文脈を引き継ぐ。

---

## Layer 4: 週1回 自己進化（日曜23時）

```
Opus が過去7日分の state.json を読む
  → 「何が役に立ったか / 立たなかったか」を分析
  → AGENT_WISDOM.md に追記
  → 収集クエリ自動調整（死んだトピック削除、新発見追加）
  → 週次サマリーを Telegram で Naoto に報告
```

---

## スケジュール（VPS cron）

```bash
# /opt/cron-env.sh 読み込み後
*/30 * * * *  python3 /opt/shared/scripts/intelligence-feed-v2.py --collect
0 */3 * * *   python3 /opt/shared/scripts/intelligence-feed-v2.py --synth
0 23 * * 0    python3 /opt/shared/scripts/intelligence-feed-v2.py --evolve
```

---

## ファイル構成（VPS）

```
/opt/shared/intelligence/
  raw/
    2026-02-23_0600.json    ← Layer 0 の収集結果（30分ごと上書き）
    2026-02-23_0630.json
    ...
  synthesis/
    2026-02-23_06.json      ← Opus の分析結果
    ...
  state.json                ← 閉ループ状態
  weekly/
    2026-02-23_weekly.json  ← 週次進化結果

/opt/shared/scripts/
  intelligence-feed-v2.py   ← 本スクリプト
```

---

## 廃止計画

| フェーズ | タイミング | アクション |
|----------|-----------|-----------|
| 移行期 | v2.0 稼働開始後2週間 | v1/v2 並行稼働（比較） |
| 統合 | 2週間後 | daily-learning.py を SUSPENDED に |
| 廃止 | 1ヶ月後 | daily-learning.py を削除 |

---

*設計確定: 2026-02-23 — Naoto承認済み*
