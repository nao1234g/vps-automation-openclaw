# OpenClaw スキルディレクトリ

## 📖 概要

このディレクトリには、OpenClaw AIエージェントが使用するカスタムスキル（機能拡張）を配置します。

スキルは、OpenClawが実行できるタスクを定義したJavaScriptモジュールです。

## 📦 含まれるスキル

### 1. N8N Integration (`n8n-integration.js`)

N8Nワークフローとの連携を提供します。

**機能:**
- ワークフローのトリガー
- データの送信
- 実行結果の取得

**使用例:**
```javascript
await trigger_n8n_workflow({
  workflowId: "abc123",
  data: {
    task: "send_email",
    to: "user@example.com"
  }
});
```

### 2. OpenNotebook Integration (`opennotebook-integration.js`)

OpenNotebook（NotebookLM代替）との連携を提供します。

**機能:**
- ノートの作成
- ノートの検索
- メタデータ管理

**使用例:**
```javascript
await create_notebook({
  title: "研究メモ",
  content: "# 概要\n...",
  sources: ["https://example.com"],
  tags: ["AI", "Research"]
});
```

### 3. VPS Maintenance (`vps-maintenance.js`)

VPSサーバーのメンテナンスタスクを自動化します。

**機能:**
- ヘルスチェック
- バックアップ実行
- セキュリティスキャン
- システムメンテナンス
- Dockerコンテナステータスチェック
- 週次メンテナンスタスク

**使用例:**
```javascript
// ヘルスチェック
await vps_maintenance.healthCheck();

// 完全バックアップ
await vps_maintenance.runBackup({ type: 'full' });

// セキュリティスキャン
await vps_maintenance.securityScan({ scope: 'all' });

// 週次メンテナンス（全タスク実行）
await vps_maintenance.weeklyMaintenance();
```

## 🔧 スキルの作成方法

### 基本構造

```javascript
module.exports = {
  name: "your_skill_name",
  description: "スキルの説明",

  async execute(params) {
    // スキルのロジックをここに実装
    try {
      // 処理
      return {
        success: true,
        data: result
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  },

  examples: [
    {
      description: "使用例の説明",
      usage: {
        // パラメータ例
      }
    }
  ]
};
```

### ベストプラクティス

1. **エラーハンドリング**
   - すべての非同期処理にtry-catchを使用
   - エラー時は`success: false`を返す

2. **戻り値の標準化**
   - 成功時: `{ success: true, data: ... }`
   - 失敗時: `{ success: false, error: ... }`

3. **ドキュメント**
   - JSDocコメントで関数を説明
   - `examples`に使用例を記載

4. **環境変数の使用**
   - 設定値は環境変数から取得
   - デフォルト値を設定

5. **セキュリティ**
   - 入力値のバリデーション
   - APIキーの適切な管理

## 🌐 統合ワークフロー例

### 1. 研究ノート自動作成

```javascript
// Telegramから指示を受ける
"最新のAI論文を調査してノートにまとめて"

// OpenClawがWeb検索を実行
const papers = await search_web("latest AI papers 2024");

// OpenNotebookにノート作成
await create_notebook({
  title: "2024年最新AI論文まとめ",
  content: papers.summary,
  tags: ["AI", "Research"],
  sources: papers.urls
});

// N8Nで通知
await trigger_n8n_workflow({
  workflowId: "slack-notify",
  data: {
    channel: "#research",
    message: "新しい研究ノートを作成しました"
  }
});
```

### 2. VPSメンテナンス自動化

```javascript
// Cronで毎週日曜3:00AMに実行
const results = await vps_maintenance.weeklyMaintenance();

// 結果をOpenNotebookに保存
await create_notebook({
  title: `VPSメンテナンスレポート ${new Date().toLocaleDateString('ja-JP')}`,
  content: formatMaintenanceReport(results),
  tags: ["VPS", "Maintenance", "Report"]
});

// Telegramで通知
if (!results.success) {
  await sendTelegramMessage({
    text: "⚠️ メンテナンスタスクが一部失敗しました。"
  });
}
```

### 3. GitHubイシュー自動対応

```javascript
// GitHub Webhookから通知
const issue = await getGitHubIssue(issueId);

// OpenClawがコード修正
const fix = await generateCodeFix(issue.description);

// テスト実行
const testResult = await runTests();

if (testResult.success) {
  // PRを作成
  await createPullRequest({
    title: `Fix: ${issue.title}`,
    body: fix.description
  });

  // N8Nでレビュー依頼
  await trigger_n8n_workflow({
    workflowId: "pr-review-request",
    data: { prUrl: pr.url }
  });
}
```

## 📚 参考リンク

- [OpenClaw公式ドキュメント](https://github.com/Sh-Osakana/open-claw)
- [N8N公式ドキュメント](https://docs.n8n.io/)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)

## 🤝 貢献

新しいスキルを追加したい場合は、以下の手順で貢献できます：

1. このリポジトリをフォーク
2. 新しいスキルファイルを`skills/`に追加
3. `README.md`に説明を追加
4. プルリクエストを作成

---

**💡 Tip**: スキルの開発時は、まず小さなタスクから始めて、段階的に機能を拡張していくことをお勧めします。
