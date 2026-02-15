# OpenClaw Skill Template

> このテンプレートは Google Antigravity の SKILL.md フォーマットをベースに、OpenClaw の skills/ ディレクトリ用に最適化したものです。

---

## ファイル構造

```
skills/
└── your-skill-name/
    ├── SKILL.md          # スキル定義（このテンプレート）
    ├── examples/         # （オプション）実装例
    ├── templates/        # （オプション）コードテンプレート
    └── scripts/          # （オプション）補助スクリプト
```

---

## SKILL.md テンプレート

```markdown
---
name: your-skill-name
description: "One-sentence summary under 150 characters describing what this skill does"
source: community
risk: safe
tags:
  - tag1
  - tag2
related_skills:
  - @another-skill
  - @yet-another-skill
---

# Your Skill Name

## Overview

2-4 sentences explaining:
- What this skill helps you accomplish
- Why it's useful
- When you should use it

## When to Use This Skill

Use this skill when you need to:
- ✅ Specific scenario 1
- ✅ Specific scenario 2
- ✅ Specific scenario 3

Trigger keywords: `keyword1`, `keyword2`, `keyword3`

## How It Works

### Step 1: Initial Setup

Provide clear, actionable instructions with specific commands or code.

```bash
# Example command
docker compose up -d
```

### Step 2: Configuration

Explain what needs to be configured and why.

```yaml
# Example configuration
service:
  enabled: true
  option: value
```

### Step 3: Execution

Describe how to execute the main task.

```javascript
// Example code
const result = await doSomething();
```

## Examples

### Example 1: Basic Use Case

```bash
# Realistic example with expected output
openclaw agents list
# Output:
# jarvis-cso (default)
# alice-research
```

### Example 2: Advanced Use Case

```python
# More complex example
from substack import Api

api = Api(cookies_string=COOKIES)
post = api.create_post(title="Hello World")
```

## Best Practices

### ✅ Do This
- Use specific, actionable verbs
- Include error handling
- Validate inputs before execution
- Test in development first

### ❌ Avoid This
- Vague or ambiguous instructions
- Silent failures without error messages
- Running destructive commands without confirmation
- Skipping validation steps

## Common Pitfalls

### Problem: Error message or symptom

**Root Cause:** Why this happens

**Solution:**
```bash
# Specific command to fix it
fix-command --with-options
```

**Prevention:** How to avoid this in the future

---

### Problem: Another common issue

**Root Cause:** Explanation

**Solution:** Step-by-step fix

**Prevention:** Best practice to prevent

## Configuration Reference

### Required Environment Variables

```bash
REQUIRED_VAR=value          # Description of what this does
ANOTHER_VAR=value           # Another required variable
```

### Optional Environment Variables

```bash
OPTIONAL_VAR=default_value  # Description and default
```

## Related Skills

- `@related-skill-1` - Brief description of how it relates
- `@related-skill-2` - Another related skill
- See also: [Official Documentation](https://example.com/docs)

## Troubleshooting

### Issue 1: Specific error message

**Symptoms:**
- What you see when this happens

**Diagnosis:**
```bash
# Commands to diagnose the problem
docker logs container-name
```

**Fix:**
```bash
# Commands to resolve the issue
docker restart container-name
```

### Issue 2: Another common issue

[Same structure as Issue 1]

## Advanced Usage

### Custom Integration

For advanced users who need to integrate with other systems:

```javascript
// Example of advanced integration
const customSetup = {
  // Advanced configuration
};
```

### Performance Optimization

Tips for optimizing performance:
- Tip 1 with specific metrics
- Tip 2 with configuration example
- Tip 3 with command

## References

- [Official Documentation](https://example.com)
- [GitHub Repository](https://github.com/example/repo)
- [Community Forum](https://forum.example.com)
- Related: `docs/ANOTHER_DOC.md`

---

*Last updated: YYYY-MM-DD — Brief description of what changed*
```

---

## フィールド説明

### YAMLフロントマター

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | ✅ | スキル名（小文字、ハイフン区切り、フォルダ名と一致） |
| `description` | ✅ | 150文字以内の1行説明 |
| `source` | ⬜️ | 出典（community, official, custom） |
| `risk` | ⬜️ | リスクレベル（safe, none, critical, offensive） |
| `tags` | ⬜️ | 検索用タグ配列 |
| `related_skills` | ⬜️ | 関連スキル（@skill-name形式） |

### セクション優先度

| セクション | 優先度 | 説明 |
|-----------|--------|------|
| Overview | 🔴 必須 | 2-4文でスキルの目的を説明 |
| When to Use | 🔴 必須 | 具体的な使用シナリオ |
| How It Works | 🔴 必須 | ステップバイステップの手順 |
| Examples | 🟡 推奨 | 2-3個の実用的なコード例 |
| Best Practices | 🟡 推奨 | Do/Don'tリスト |
| Common Pitfalls | 🟡 推奨 | よくある問題と解決策 |
| Configuration Reference | ⬜️ 任意 | 設定オプションの詳細 |
| Troubleshooting | ⬜️ 任意 | 問題診断と修正手順 |
| Advanced Usage | ⬜️ 任意 | 上級者向けのヒント |
| References | ⬜️ 任意 | 外部ドキュメントへのリンク |

---

## 作成ガイドライン

### 1. 明確で具体的な指示を書く

❌ **悪い例：**
> "設定ファイルを適切に構成してください"

✅ **良い例：**
> "openclaw.json の `gateway.auth.token` フィールドに、`openssl rand -hex 32` で生成した64文字のトークンを設定してください"

### 2. 実行可能なコード例を含める

すべてのコードブロックに言語指定を付ける：

```bash
# Bash commands
docker compose up -d
```

```python
# Python code
result = api.call()
```

```yaml
# YAML configuration
key: value
```

### 3. エラーハンドリングを明示する

```bash
# Good: Explicit error checking
if [ ! -f ".env" ]; then
  echo "Error: .env file not found"
  exit 1
fi
```

### 4. 非エンジニア向けに書く

- 専門用語は必ず説明を付ける
- コマンドの**目的**を先に説明してから実行方法を示す
- 期待される出力を例示する

### 5. 安全性を最優先する

- 破壊的な操作の前に確認ステップを入れる
- `--dry-run` オプションを推奨する
- バックアップ手順を明記する

---

## OpenClaw固有の注意事項

### 設定変更

OpenClawの設定は **openclaw.json** で行う（CLIフラグや環境変数ではない）：

```json
{
  "gateway": {
    "auth": {
      "mode": "token",
      "token": "your-token-here"
    }
  }
}
```

### サブエージェント委任

Jarvisから他のエージェントにタスクを委任する例：

```markdown
## When to Use This Skill

Jarvis が複雑なタスクを分割して、専門エージェントに委任する際に使用：

- リサーチ → Alice
- コーディング → CodeX
- 執筆 → Luna
```

### Docker統合

OpenClawはDocker環境で動作するため、コンテナ操作を含める：

```bash
# Restart OpenClaw to apply changes
docker restart openclaw-agent

# View logs
docker logs openclaw-agent --tail 50
```

---

## 既存スキル例

参考として、実際のOpenClawスキルを確認：

```bash
ls -la skills/
```

既存のスキル構造：
- `skills/*.js` - JavaScript形式のスキル（従来型）
- `skills/*/SKILL.md` - Markdown形式のスキル（新型・推奨）

---

## チェックリスト

スキル作成後、以下を確認：

- [ ] フォルダ名とYAML `name` が一致している
- [ ] `description` が150文字以内
- [ ] Overviewセクションが2-4文で簡潔
- [ ] How It Worksに具体的な手順がある
- [ ] コードブロックに言語指定がある
- [ ] エラーハンドリングが含まれている
- [ ] 実際に動作するコード例である
- [ ] 非エンジニアでも理解できる説明
- [ ] 安全性チェック（破壊的操作の確認ステップ）
- [ ] 最終更新日が記載されている

---

## 参考リンク

- [Antigravity Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills)
- [SKILL_ANATOMY.md](https://github.com/sickn33/antigravity-awesome-skills/blob/main/docs/SKILL_ANATOMY.md)
- [OpenClaw Documentation](https://github.com/openclaw/openclaw)
- `docs/KNOWN_MISTAKES.md` - 過去のミスから学ぶ

---

*最終更新: 2026-02-14 — antigravity-awesome-skills調査結果を反映*
