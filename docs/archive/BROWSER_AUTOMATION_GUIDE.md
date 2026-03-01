# ブラウザ自動化ガイド（NeoとJarvis用）

## 原則

**🚫 人間に「コピペして」「設定して」と依頼してはいけない**

以下の作業は全て自動化すること：
- Webフォーム入力
- ボタンクリック
- ページ遷移
- テキストコピペ
- スクリーンショット取得

---

## Puppeteer使用例

### 1. Substack設定の自動化

#### VPSで実行（Neo/Jarvis）

**Aboutページ設定：**
```bash
node /opt/substack-auto-setup.js \
  --cookie "connect.sid=YOUR_COOKIE" \
  --about-file /opt/shared/reports/2026-02-14_aisa_substack_setup.md
```

**Welcome Email設定：**
```bash
node /opt/substack-auto-setup.js \
  --cookie "connect.sid=YOUR_COOKIE" \
  --welcome "Welcome to AISA! ..."
```

**両方同時：**
```bash
node /opt/substack-auto-setup.js \
  --cookie "connect.sid=YOUR_COOKIE" \
  --about "AISA — Asia Intelligence..." \
  --welcome "Welcome to AISA..."
```

---

### 2. Cookie取得方法

**人間が1回だけ実行（その後は自動化）：**

1. Substackにブラウザでログイン
2. F12 → Application → Cookies → substack.com
3. `connect.sid` の値をコピー
4. VPS `/opt/.substack-cookie` に保存

```bash
echo "connect.sid=YOUR_COOKIE_VALUE" > /opt/.substack-cookie
chmod 600 /opt/.substack-cookie
```

**以降、Neoが自動で使用：**
```bash
COOKIE=$(cat /opt/.substack-cookie | cut -d= -f2)
node /opt/substack-auto-setup.js --cookie "$COOKIE" --about "..."
```

---

### 3. 他のブラウザ自動化例

#### GitHub設定
```javascript
const puppeteer = require('puppeteer');

async function setupGitHubRepo(repoUrl, description) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // GitHub tokenでログイン
  await page.goto(repoUrl + '/settings');

  // Description変更
  await page.type('input[name="repository[description]"]', description);
  await page.click('button[type="submit"]');

  await browser.close();
}
```

#### N8N ワークフロー有効化
```javascript
async function enableN8NWorkflow(workflowId) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('http://localhost:5678/workflows');
  await page.click(`button[data-workflow-id="${workflowId}"]`);

  await browser.close();
}
```

---

## OpenClawからの呼び出し

### Jarvisがスクリプトを実行

```javascript
// OpenClaw skill内で実行
const { exec } = require('child_process');

async function setupSubstackAuto(aboutText, welcomeText) {
  const cookie = await readFile('/opt/.substack-cookie');

  const command = `node /opt/substack-auto-setup.js \
    --cookie "${cookie}" \
    --about "${aboutText}" \
    --welcome "${welcomeText}"`;

  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}
```

---

## ベストプラクティス

### ✅ 正しい例

**Neo/Jarvisがやるべきこと：**
```
1. Substackテンプレート作成
2. Puppeteerスクリプト実行
3. 結果確認
4. ユーザーに「設定完了」報告
```

### ❌ 間違った例

**やってはいけないこと：**
```
1. Substackテンプレート作成
2. ユーザーに「Telegramに送ったのでSubstackに貼り付けてください」
   → ❌ これは自動化すべき！
```

---

## トラブルシューティング

### Puppeteerエラー
```bash
# Headless Chromeの依存関係インストール
apt-get update
apt-get install -y chromium-browser
```

### Cookie期限切れ
```bash
# 新しいCookieを取得して更新
echo "connect.sid=NEW_VALUE" > /opt/.substack-cookie
```

---

## まとめ

**原則：人間がやらなくていいことは、絶対に人間に依頼しない**

- ブラウザ操作 → Puppeteer
- API操作 → HTTP/REST
- ファイル操作 → Read/Write/Edit
- コマンド → Bash

**人間に依頼して良いのは、戦略判断・予算承認・最終GO/NO GOのみ**

---

*最終更新: 2026-02-15 — 自律性の原則を徹底*
