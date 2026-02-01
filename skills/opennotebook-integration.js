/**
 * OpenNotebook Integration Skill
 * OpenClawからOpenNotebookにノートを作成・管理
 */

module.exports = {
  name: "manage_opennotebook",
  description: "OpenNotebookでノートの作成・検索・更新を行う",
  
  parameters: {
    action: {
      type: "string",
      description: "実行するアクション (create/search/update/delete)",
      required: true,
      enum: ["create", "search", "update", "delete"]
    },
    title: {
      type: "string",
      description: "ノートのタイトル",
      required: false
    },
    content: {
      type: "string",
      description: "ノートの内容",
      required: false
    },
    sources: {
      type: "array",
      description: "参照元のURL配列",
      required: false,
      default: []
    },
    notebookId: {
      type: "string",
      description: "ノートブックID（更新・削除時）",
      required: false
    }
  },

  async execute({ action, title, content, sources = [], notebookId }) {
    const opennotebookUrl = process.env.OPENNOTEBOOK_URL || "http://localhost:8080";
    const apiKey = process.env.OPENNOTEBOOK_API_KEY;

    const headers = {
      "Content-Type": "application/json"
    };

    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    try {
      switch (action) {
        case "create":
          return await this.createNotebook({ opennotebookUrl, headers, title, content, sources });
        
        case "search":
          return await this.searchNotebooks({ opennotebookUrl, headers, query: title });
        
        case "update":
          return await this.updateNotebook({ opennotebookUrl, headers, notebookId, title, content, sources });
        
        case "delete":
          return await this.deleteNotebook({ opennotebookUrl, headers, notebookId });
        
        default:
          throw new Error(`Unknown action: ${action}`);
      }
    } catch (error) {
      return {
        success: false,
        action,
        error: error.message,
        message: `OpenNotebook操作に失敗しました: ${action}`
      };
    }
  },

  async createNotebook({ opennotebookUrl, headers, title, content, sources }) {
    const response = await fetch(`${opennotebookUrl}/api/notebooks`, {
      method: "POST",
      headers,
      body: JSON.stringify({ title, content, sources })
    });

    if (!response.ok) {
      throw new Error(`Failed to create notebook: ${response.statusText}`);
    }

    const notebook = await response.json();
    
    return {
      success: true,
      action: "create",
      notebook,
      message: `ノート「${title}」を作成しました`
    };
  },

  async searchNotebooks({ opennotebookUrl, headers, query }) {
    const response = await fetch(`${opennotebookUrl}/api/notebooks/search?q=${encodeURIComponent(query)}`, {
      method: "GET",
      headers
    });

    if (!response.ok) {
      throw new Error(`Failed to search notebooks: ${response.statusText}`);
    }

    const notebooks = await response.json();
    
    return {
      success: true,
      action: "search",
      notebooks,
      count: notebooks.length,
      message: `${notebooks.length}件のノートが見つかりました`
    };
  },

  async updateNotebook({ opennotebookUrl, headers, notebookId, title, content, sources }) {
    const response = await fetch(`${opennotebookUrl}/api/notebooks/${notebookId}`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ title, content, sources })
    });

    if (!response.ok) {
      throw new Error(`Failed to update notebook: ${response.statusText}`);
    }

    const notebook = await response.json();
    
    return {
      success: true,
      action: "update",
      notebook,
      message: `ノートを更新しました`
    };
  },

  async deleteNotebook({ opennotebookUrl, headers, notebookId }) {
    const response = await fetch(`${opennotebookUrl}/api/notebooks/${notebookId}`, {
      method: "DELETE",
      headers
    });

    if (!response.ok) {
      throw new Error(`Failed to delete notebook: ${response.statusText}`);
    }
    
    return {
      success: true,
      action: "delete",
      notebookId,
      message: `ノートを削除しました`
    };
  },

  // 使用例
  examples: [
    {
      description: "新しいノートを作成",
      input: {
        action: "create",
        title: "AI研究ノート",
        content: "最新のトランスフォーマーモデルについての調査結果...",
        sources: ["https://arxiv.org/abs/1234.5678"]
      }
    },
    {
      description: "ノートを検索",
      input: {
        action: "search",
        title: "AI"
      }
    },
    {
      description: "ノートを更新",
      input: {
        action: "update",
        notebookId: "abc123",
        title: "更新されたタイトル",
        content: "更新された内容"
      }
    }
  ]
};

