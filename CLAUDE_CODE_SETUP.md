ls -la ~/.claude/
# Claude Code - 最強設定完了 ✅

## インストール済み

### 1. everything-claude-code (Anthropic Hackathon優勝者の設定)
**場所**: `~/.claude/`

#### インストールされた内容:
- **Rules** (ルール - 常に従うガイドライン)
  - `security.md` - セキュリティチェック
  - `coding-style.md` - コーディングスタイル
  - `testing.md` - テスト要件
  - `git-workflow.md` - Git ワークフロー
  - `agents.md` - エージェント委譲
  - `performance.md` - パフォーマンス最適化

- **Agents** (専門サブエージェント)
  - `planner.md` - 機能実装計画
  - `architect.md` - システム設計
  - `tdd-guide.md` - テスト駆動開発
  - `code-reviewer.md` - コードレビュー
  - `security-reviewer.md` - セキュリティレビュー
  - `build-error-resolver.md` - ビルドエラー解決
  - その他10以上のエージェント

- **Commands** (スラッシュコマンド)
  - `/tdd` - テスト駆動開発
  - `/plan` - 実装計画
  - `/code-review` - コードレビュー
  - `/build-fix` - ビルドエラー修正
  - その他15以上のコマンド

- **Skills** (ワークフロー定義)
  - `coding-standards/` - 言語別ベストプラクティス
  - `backend-patterns/` - API/DB/キャッシュパターン
  - `frontend-patterns/` - React/Next.jsパターン
  - `security-review/` - セキュリティチェックリスト
  - `tdd-workflow/` - TDD方法論
  - その他30以上のスキル

### 2. awesome-claude-skills (コミュニティベストスキル集)
**場所**: `~/awesome-claude-skills/` (参照用)

利用可能なスキル:
- Docker管理
- SSH/VPS管理
- システムデバッグ
- インフラ自動化
- セキュリティテスト

## プロジェクト固有の設定

**場所**: `.claude/CLAUDE.md`

このプロジェクト用に最適化:
- VPS管理 (ConoHa)
- Docker containerization
- OpenClaw/MultiBot deployment
- セキュリティファースト
- 防御的スクリプティング

## 使い方

### コマンドの使用例:
```bash
# Claude Code内で使用
/plan "DockerでOpenClawをデプロイ"
/code-review
/tdd
```

### エージェントの利用:
Claude Codeが自動的に適切なエージェントに委譲します。
- 複雑な設計 → architect
- セキュリティチェック → security-reviewer
- ビルドエラー → build-error-resolver

### ルールの効果:
すべてのコードは自動的に以下をチェック:
✓ セキュリティ (ハードコードされた秘密情報なし)
✓ コーディングスタイル (イミュータビリティ、ファイル制限)
✓ テストカバレッジ (80%以上)
✓ Git ワークフロー (適切なコミットフォーマット)

## 次のステップ

### オプション1: プラグインとしてインストール (推奨)
```bash
# VS Code Codespaces内
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
```

### オプション2: 必要なスキルだけ追加
awesome-claude-skillsから必要なものをピックアップ:
- `webapp-testing` - Webアプリテスト
- `systematic-debugging` - デバッグ
- `defense-in-depth` - 多層セキュリティ

## 機能強化のポイント

1. **トークン最適化**
   - 適切なモデル選択 (Sonnet 4.5 vs Haiku)
   - コンテキストウィンドウ管理

2. **メモリ永続化**
   - セッション間で学習内容を保持
   - パターンの自動抽出

3. **検証ループ**
   - 継続的評価
   - チェックポイントベースのテスト

4. **並列化**
   - Gitワークツリーの活用
   - カスケード方式

## トラブルシューティング

### Claude Codeが設定を認識しない場合:
1. VS Code Codespacesをリロード
2. `~/.claude/` ディレクトリの権限確認
3. `.claude/CLAUDE.md` がプロジェクトルートにあることを確認

### コマンドが見つからない場合:
```bash
ls ~/.claude/commands/
```

### ルールが適用されない場合:
```bash
ls ~/.claude/rules/
```

## 参考リンク

- [Shorthand Guide](https://github.com/affaan-m/everything-claude-code) - 基礎と哲学
- [Longform Guide](https://github.com/affaan-m/everything-claude-code) - 高度な最適化
- [awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills) - コミュニティスキル

---

## NEO-GPT — Codex CLI バックアップエージェント

NEO-1/2 (Claude Code) 停止時のフェイルオーバーとして、OpenAI Codex CLI をバックエンドに使う Telegram bot。

| 項目 | 値 |
|------|-----|
| Bot | `@neogpt_nn_bot` |
| サブスク | ChatGPT Pro $200/月 |
| バックエンド | `codex exec --full-auto` |
| VPSパス | `/opt/neo3-codex/` |
| systemd | `neo3-telegram.service` |

### デプロイ手順
```bash
# 1. セットアップスクリプト実行
scp scripts/setup_neo3.sh root@163.44.124.123:/tmp/
ssh root@163.44.124.123 'bash /tmp/setup_neo3.sh'

# 2. Codex CLI 認証（初回のみ）
ssh root@163.44.124.123 'codex login --device-auth'

# 3. サービス起動
ssh root@163.44.124.123 'systemctl enable --now neo3-telegram'
```

### NEO-1/2 ↔ NEO-GPT 切替
```bash
# NEO-1/2 停止 → NEO-GPT 起動
systemctl stop claude-telegram && systemctl start neo3-telegram

# NEO-GPT 停止 → NEO-1/2 復帰
systemctl stop neo3-telegram && systemctl start claude-telegram
```

---

**ステータス**: ✅ 完全セットアップ完了
**Claude Code機能**: 🚀 最高レベルに強化済み
**次のアクション**: VPS/OpenClaw自動化を開始できます！
