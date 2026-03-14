# Truth Protocol — 予測の真実性を保証するプロトコル

> 「予測プラットフォームの命は信頼性。一度の改ざんで全トラックレコードが無効になる。」

---

## なぜ Truth Protocol が必要か

Nowpatternの競争優位（モート）は「3年分の改ざん不可能な予測トラックレコード」だ。
これが価値を持つのは、**予測がされた時点の記録が変更されない**ことが保証されているからだ。

予測確率をあとから変えることは、後から日記を書き直すことと同じだ。
そのような記録には価値がない。

---

## 4層の真実保証

### Layer 1: 予測DB（prediction_db.json）

```python
# apps/nowpattern/prediction_tracker.py
def add_prediction(...) -> Dict:
    # 一度追加された予測の確率(our_pick_prob)は変更不可
    # resolve_prediction() は結果(result)と解決日だけを追加する
```

**何が不変か:**
- `our_pick_prob`（予測確率）
- `registered_at`（登録日時）
- `our_pick`（YES/NO予測）

**変更可能なもの:**
- `status`: open → resolved
- `result`: 実際の結果
- `brier_score`: 計算されたスコア
- `triggers[].actual`: 実際のトリガーイベント

### Layer 2: OTSタイムスタンプ（prediction_timestamper.py）

```bash
# VPS cron: 毎時実行
python3 /opt/shared/scripts/prediction_timestamper.py
```

全予測データのハッシュをBitcoin OpenTimestamps（OTS）プロトコルでタイムスタンプする。
これにより、「この予測は○月○日より前に存在していた」ことをブロックチェーンで証明できる。

**改ざん検知:** OTSファイルと現在のDBハッシュが一致しない場合、Telegram警告。

### Layer 3: 自動検証（prediction_auto_verifier.py）

```bash
# VPS cron: 毎日 JST 04:00
python3 /opt/shared/scripts/prediction_auto_verifier.py
```

**検証プロセス:**
1. `status=open` かつ `triggers[].date` が過去の予測を抽出
2. Grok API で実際の結果を検索
3. Claude Opus 4.6 が YES/NO を判定
4. 判定結果を `resolve_prediction()` で記録（確率は不変）

**閾値:** 2件以上の情報源が一致した場合のみ自動解決。それ以外は `status=needs_review` でNaotoに送信。

### Layer 4: Ghost Webhook 改ざん検知

```python
# VPS: /opt/shared/scripts/ghost_page_guardian.py (port 8765)
# Ghost CMS の page.published.edited イベントを監視
PROTECTED_SLUGS = {"predictions", "en-predictions"}
# → 改ざんを検知したらTelegram即通知
```

---

## Brier Score の計算ルール

```python
def calculate_brier(probability: float, outcome: bool) -> float:
    """
    標準Brierスコア計算

    Args:
        probability: 予測確率（0〜1）
        outcome: 実際の結果（True=YES, False=NO）

    Returns:
        Brier Score（0〜1、低いほど良い）
    """
    p = probability / 100.0  # パーセントを比率に変換
    o = 1.0 if outcome else 0.0
    return round((p - o) ** 2, 4)
```

**ルール:**
- 解決後のBrierスコアは変更禁止
- 解決前に確率を変更することも禁止（手動による後知恵防止）
- Brierスコアの計算は `truth_engine/brier_score.py` の `BrierCalculator` が担当

---

## 予測品質の最低基準

予測がprediction_dbに登録されるには以下の全条件を満たすこと:

```python
MINIMUM_QUALITY = {
    "has_resolution_question": True,    # 判定質問が明確（YES/NO答えられる）
    "has_deadline": True,               # 判定期限が設定されている
    "probability_in_range": True,       # 5% ≤ prob ≤ 95%
    "evidence_quality_not_wishful": True,  # WISHFULな根拠は禁止
    "has_hit_condition": True,          # 的中条件が明文化されている
}
```

これらが欠けた予測は `PredictionTracker.add_prediction()` が ValueError を発生させる。

---

## 解決の手順（Resolver Protocol）

予測の解決は以下の順序で行う:

```
Step 1: prediction_auto_verifier.py が自動判定を試みる
   ↓ 判定できた場合 → Step 3
   ↓ 判定できない場合 → Step 2

Step 2: Naotoが手動で結果を確認
   → `python3 prediction_tracker.py --resolve <id> --result YES`

Step 3: resolve_prediction() が記録する
   - result = "YES" / "NO"
   - brier_score = 計算値
   - resolved_at = 現在時刻

Step 4: prediction_page_builder.py が /predictions/ を更新
   - cronが翌日07:00 JSTに実行 or 手動で即時実行

Step 5: OTSタイムスタンプで解決記録を証明
   - prediction_timestamper.py が次の定時実行で処理
```

---

## 審判の独立性（No Conflict of Interest）

予測の**発行者**（Nowpattern/NEO）と**検証者**（auto_verifier/Naoto）は独立していなければならない。

- NEO-ONE/TWOが書いた予測を、同じNEOが解決してはいけない（自己採点禁止）
- `prediction_auto_verifier.py` は独立したスクリプトとして実行される
- 解決結果に疑義がある場合、Naotoが最終判断者

---

## 既知の例外ケース

| ケース | 対処 |
|--------|------|
| 判定質問が曖昧（YES/NOが決められない） | `status=ambiguous` で保留。Naotoが質問を再定義 |
| 予測期限が延長された（政治的延期等） | `triggers[0].date` を更新可能（確率は不変） |
| 外部APIが間違った情報を返した | 手動で `result=null` にリセット → 再解決 |
| 市場自体がなくなった（Polymarket終了等） | `status=cancelled` で無効化 |

---

*最終更新: 2026-03-14 — Truth Protocol 初版。AI Civilization OS 実装に合わせて作成*
