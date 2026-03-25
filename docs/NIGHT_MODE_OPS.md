# Night Mode Operations Guide

> **Night Mode = Claude Code の自律運転モード**
> Naotoが就寝・離席する間、Claude Code が確認なしに安全な範囲でタスクを実行する。

---

## 概要

| 項目 | 内容 |
|------|------|
| **対象** | ローカル Claude Code（VSCode） |
| **有効化** | `bash scripts/night-mode-on.sh` |
| **解除** | `bash scripts/night-mode-off.sh` |
| **フラグ** | `.claude/hooks/state/night_mode.flag` |
| **判定** | flash-cards-inject.sh が毎ターンフラグを確認 |

---

## Night Mode 中の行動ルール

### 禁止事項（フック強制）
- `AskUserQuestion` = 完全禁止 → 安全な選択を取って続行
- `EnterPlanMode` = 完全禁止 → 内部で計画して即実行
- 確認を求めるテキスト出力禁止
- `pvqe-p-gate.py` の証拠計画要件がバイパスされる

### 安全ガードレール（Night Mode でも有効）
- git push 禁止（朝にNaotoが確認してからpush）
- 本番DB削除禁止
- 大量publish禁止（pilot 10件まで、それ以上は朝承認）
- UIレイアウト変更禁止
- コスト発生操作禁止
- VPS構造変更禁止（LEVEL 3 操作）

### 推奨行動
- 調査 → 実装 → docs固定 → 検証 の流れを完遂
- エラーが出ても止まらない → ログして次タスクへスキップ
- 判断に迷ったらリスクの低い方を選ぶ
- ミスが出たら KNOWN_MISTAKES.md に即記録

---

## 有効化手順

### Step 1: 就寝前にNaotoが実行

```bash
# ローカル（VSCode ターミナル）
bash scripts/night-mode-on.sh
```

出力:
```
🌙 NIGHT MODE ON — 自律運転を開始します
  Claude Code は確認を求めず自律実行します。
  解除: bash scripts/night-mode-off.sh
  フラグ: .claude/hooks/state/night_mode.flag
```

### Step 2: タスク指示を残す

Night Mode 開始時に、その夜のタスクリストを会話に入力する。

**タスク指示テンプレート:**
```
Night Mode 実行指示（YYYY-MM-DD）

## 今夜のタスク（優先順）
1. [タスク名]: [具体的な内容]
2. [タスク名]: [具体的な内容]
...

## 安全制約
- publish上限: [N]件
- SSH操作: [許可/禁止]
- デプロイ: [許可/禁止]

## 朝のアウトプット
- docs/MORNING_HANDOFF_YYYY-MM-DD.md に引き継ぎレポートを書く
```

### Step 3: VSCode を開いたまま離席

Claude Code は指示に従い、夜間中に自律実行する。

---

## 解除手順

### 起床後にNaotoが実行

```bash
# ローカル（VSCode ターミナル）
bash scripts/night-mode-off.sh
```

出力:
```
☀️ NIGHT MODE OFF — 通常モードに戻りました
  Claude Code は確認フローを再び使います。
```

### 朝のチェックリスト

1. **引き継ぎレポートを読む**: `docs/MORNING_HANDOFF_*.md`
2. **朝の推奨アクション**を実行（レポートに記載）
3. **git status** で変更ファイルを確認
4. **VPS状態確認**: `ssh root@163.44.124.123 "cat /opt/shared/SHARED_STATE.md"`

---

## VPS側のNight Mode（現状と設計）

### 現状（2026-03-25）
- VPS上にNight Mode切替スクリプトは不要（NEOは常時自律稼働）
- Night Modeはローカル Claude Code 専用の機能
- VPS側の cron/service は 24時間稼働で変更なし

### NEO との関係
- NEO-ONE/TWO は systemd で常時稼働（Night Mode 関係なし）
- NEO への追加指示は Telegram 経由（Night Mode 中は不可）
- Night Mode 中に NEO を止める必要はない

---

## Night Mode タイミング設計（標準パターン）

### 推奨スケジュール

| フェーズ | 時刻 | 内容 |
|----------|------|------|
| **就寝前 (Day 0)** | 23:00〜24:00 JST | Night Mode ON + タスク指示入力 |
| **夜間実行** | 00:00〜06:00 JST | Claude Code 自律実行（NEO も並行稼働） |
| **朝起床後** | 07:00〜08:00 JST | Night Mode OFF + 引き継ぎレポート確認 |

### セッションタイミング記録フォーマット

引き継ぎレポートに必ず記載:

```
## セッションタイミング
- 開始: YYYY-MM-DD HH:MM JST
- 終了: YYYY-MM-DD HH:MM JST
- 経過: N時間M分
- チェックポイント:
  - HH:MM Track A 完了
  - HH:MM Track B 完了
  - HH:MM Track C 完了
```

### Night Mode の期待値

| 項目 | 目安 |
|------|------|
| 1 Track あたりの所要時間 | 30〜60分 |
| 5 Track セッション | 4〜6時間 |
| 最大 safe publish 件数 | 10件（承認待ち） |
| VPS 構造変更 | 禁止（朝承認後） |

---

## Morning Handoff 標準フォーマット

ファイル名: `docs/MORNING_HANDOFF_YYYY-MM-DD.md`

### 必須セクション構成

```markdown
# Morning Handoff — YYYY-MM-DD

## セッションタイミング
[上記フォーマット]

## 完了サマリー（1行/Track）
- Track A: ✅ 何をした
- Track B: ✅ 何をした（何件）
- Track C: ✅ 何を調査し何を発見した
- Track D: ✅ 何を作成した
- Track E: ✅ 何を確認した

## 朝の必須アクション（優先順）
1. **[RED: 即実行]** 何をする
2. **[ORANGE: 今日中]** 何をする
3. **[GREEN: 任意]** 何をする

## 承認待ち事項
| 操作 | 件数 | リスク | コマンド |
|------|------|--------|---------|
| EN draft publish | N件 | LOW | `python3 ... --fix-tags --limit 50` |

## 発見した問題
| 問題 | 深刻度 | 解決方法 |
|------|--------|---------|
| 問題内容 | HIGH/MID/LOW | 解決策 |

## 変更したファイル
- path/to/file.py: 何をした
```

---

## Night Mode 成果物の標準構成

| ファイル | 内容 |
|----------|------|
| `docs/MORNING_HANDOFF_YYYY-MM-DD.md` | 朝の引き継ぎレポート（メイン成果物） |
| `docs/PIPELINE_HEALTH_YYYY-MM-DD.md` | パイプライン健康状態（Track C実行時） |
| `scripts/[新規スクリプト].py` | 夜間に作成したスクリプト |
| `KNOWN_MISTAKES.md` への追記 | 夜間に発見したミス |

---

## トラブルシューティング

### Night Mode が効かない
```bash
# フラグが存在するか確認
ls -la .claude/hooks/state/night_mode.flag

# フックが動作しているか確認
tail -5 .claude/hooks/state/errors.log
```

### Claude Code が止まった
- VSCode のターミナルで Claude Code を再起動
- Night Mode フラグは残っているので自動的に再開される

### 朝にフラグが残っている
```bash
bash scripts/night-mode-off.sh
```

---

*Created: 2026-03-25 01:30 JST by Night Mode Track D*
