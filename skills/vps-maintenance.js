/**
 * VPS Maintenance Skill
 * OpenClawでVPSのメンテナンスタスクを実行
 */

const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

module.exports = {
  name: "vps_maintenance",
  description: "VPSサーバーのメンテナンスタスク（更新、バックアップ、ヘルスチェック）を自動実行",

  /**
   * システムヘルスチェック
   *
   * @returns {Promise<Object>} ヘルスチェック結果
   */
  async healthCheck() {
    try {
      const scriptPath = '/opt/vps-automation-openclaw/scripts/health_check.sh';
      const { stdout, stderr } = await execAsync(`bash ${scriptPath}`);

      return {
        success: true,
        output: stdout,
        errors: stderr || null,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Health Check Error:', error);

      return {
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  },

  /**
   * バックアップを実行
   *
   * @param {Object} params - パラメータ
   * @param {string} [params.type='full'] - バックアップタイプ（full, db-only, volumes-only）
   * @returns {Promise<Object>} バックアップ結果
   */
  async runBackup({ type = 'full' } = {}) {
    try {
      const scriptPath = '/opt/vps-automation-openclaw/scripts/backup.sh';
      const options = {
        'full': '',
        'db-only': '--db-only',
        'volumes-only': '--volumes-only'
      };

      const option = options[type] || '';
      const { stdout, stderr } = await execAsync(`sudo bash ${scriptPath} ${option}`);

      return {
        success: true,
        type: type,
        output: stdout,
        errors: stderr || null,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Backup Error:', error);

      return {
        success: false,
        type: type,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  },

  /**
   * セキュリティスキャン
   *
   * @param {Object} params - パラメータ
   * @param {string} [params.scope='all'] - スキャン範囲（all, images-only, system-only）
   * @returns {Promise<Object>} スキャン結果
   */
  async securityScan({ scope = 'all' } = {}) {
    try {
      const scriptPath = '/opt/vps-automation-openclaw/scripts/security_scan.sh';
      const options = {
        'all': '--all',
        'images-only': '--images-only',
        'system-only': '--system-only'
      };

      const option = options[scope] || '--all';
      const { stdout, stderr } = await execAsync(`bash ${scriptPath} ${option}`);

      return {
        success: true,
        scope: scope,
        output: stdout,
        errors: stderr || null,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Security Scan Error:', error);

      return {
        success: false,
        scope: scope,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  },

  /**
   * システムメンテナンス
   *
   * @param {Object} params - パラメータ
   * @param {boolean} [params.dryRun=false] - ドライラン（実行せずにプレビュー）
   * @returns {Promise<Object>} メンテナンス結果
   */
  async runMaintenance({ dryRun = false } = {}) {
    try {
      const scriptPath = '/opt/vps-automation-openclaw/scripts/maintenance.sh';
      const option = dryRun ? '--dry-run' : '';
      const { stdout, stderr } = await execAsync(`sudo bash ${scriptPath} ${option}`);

      return {
        success: true,
        dryRun: dryRun,
        output: stdout,
        errors: stderr || null,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Maintenance Error:', error);

      return {
        success: false,
        dryRun: dryRun,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  },

  /**
   * Dockerコンテナステータスチェック
   *
   * @returns {Promise<Object>} コンテナステータス
   */
  async checkContainers() {
    try {
      const { stdout } = await execAsync('docker compose -f /opt/vps-automation-openclaw/docker-compose.production.yml ps --format json');

      const containers = stdout.trim().split('\n')
        .filter(line => line)
        .map(line => JSON.parse(line));

      const summary = {
        total: containers.length,
        running: containers.filter(c => c.State === 'running').length,
        stopped: containers.filter(c => c.State !== 'running').length,
        containers: containers.map(c => ({
          name: c.Name,
          service: c.Service,
          state: c.State,
          status: c.Status
        }))
      };

      return {
        success: true,
        ...summary,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Container Check Error:', error);

      return {
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  },

  /**
   * 週次メンテナンスタスク（自動実行用）
   *
   * @returns {Promise<Object>} 実行結果の集約
   */
  async weeklyMaintenance() {
    const results = {};

    // ヘルスチェック
    results.healthCheck = await this.healthCheck();

    // セキュリティスキャン
    results.securityScan = await this.securityScan({ scope: 'all' });

    // バックアップ
    results.backup = await this.runBackup({ type: 'full' });

    // コンテナステータス
    results.containers = await this.checkContainers();

    const allSuccess = Object.values(results).every(r => r.success);

    return {
      success: allSuccess,
      results: results,
      timestamp: new Date().toISOString(),
      summary: `週次メンテナンス${allSuccess ? '成功' : '一部失敗'}`
    };
  },

  /**
   * 使用例
   */
  examples: [
    {
      description: "ヘルスチェックを実行",
      usage: "healthCheck()"
    },
    {
      description: "完全バックアップ",
      usage: "runBackup({ type: 'full' })"
    },
    {
      description: "データベースのみバックアップ",
      usage: "runBackup({ type: 'db-only' })"
    },
    {
      description: "セキュリティスキャン（全体）",
      usage: "securityScan({ scope: 'all' })"
    },
    {
      description: "メンテナンス（ドライラン）",
      usage: "runMaintenance({ dryRun: true })"
    },
    {
      description: "週次メンテナンスタスク",
      usage: "weeklyMaintenance()"
    }
  ]
};
