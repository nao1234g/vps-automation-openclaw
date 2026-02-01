/**
 * N8N Workflow Integration Skill
 * OpenClawからN8Nワークフローをトリガー
 */

module.exports = {
  name: "trigger_n8n_workflow",
  description: "N8Nワークフローをトリガーして自動化タスクを実行する",
  
  parameters: {
    workflowId: {
      type: "string",
      description: "N8NワークフローのWebhook ID",
      required: true
    },
    data: {
      type: "object",
      description: "ワークフローに渡すデータ",
      required: false,
      default: {}
    }
  },

  async execute({ workflowId, data = {} }) {
    const n8nBaseUrl = process.env.N8N_BASE_URL || "http://localhost:5678";
    const webhookUrl = `${n8nBaseUrl}/webhook/${workflowId}`;

    try {
      const response = await fetch(webhookUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        throw new Error(`N8N Webhook failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      return {
        success: true,
        workflowId,
        result,
        message: "N8Nワークフローが正常に実行されました"
      };
    } catch (error) {
      return {
        success: false,
        workflowId,
        error: error.message,
        message: "N8Nワークフローの実行に失敗しました"
      };
    }
  },

  // 使用例
  examples: [
    {
      input: {
        workflowId: "abc123",
        data: {
          task: "send_email",
          to: "user@example.com",
          subject: "Test Email"
        }
      },
      output: {
        success: true,
        message: "N8Nワークフローが正常に実行されました"
      }
    }
  ]
};

