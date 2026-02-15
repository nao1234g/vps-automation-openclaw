#!/usr/bin/env node
/**
 * X（Twitter）自動投稿スクリプト（Puppeteer）
 *
 * 使い方:
 * node x-auto-post.js --cookie "auth_token=..." --tweet "ツイート内容"
 */

const puppeteer = require('puppeteer');

async function postToX(options) {
  const { cookie, tweetText } = options;

  console.log('🐦 X（Twitter）自動投稿を開始します...');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();

    // Cookieでログイン
    console.log('🔐 Cookieでログイン中...');
    await page.setCookie({
      name: 'auth_token',
      value: cookie,
      domain: '.x.com',
      path: '/',
      httpOnly: true,
      secure: true
    });

    // X.comに移動
    console.log('📱 X.comに移動中...');
    await page.goto('https://x.com/compose/tweet', { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(resolve => setTimeout(resolve, 3000));

    // ツイート入力
    console.log('✍️ ツイートを入力中...');
    const tweetBox = await page.$('[data-testid="tweetTextarea_0"]');
    if (tweetBox) {
      await tweetBox.click();
      await new Promise(resolve => setTimeout(resolve, 1000));
      await tweetBox.type(tweetText, { delay: 50 });
      console.log('✅ ツイートテキスト入力完了');
    } else {
      throw new Error('ツイート入力ボックスが見つかりません');
    }

    // 投稿ボタンをクリック
    console.log('🚀 投稿ボタンをクリック中...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const postButton = await page.$('[data-testid="tweetButtonInline"]');
    if (postButton) {
      await postButton.click();
      await new Promise(resolve => setTimeout(resolve, 3000));
      console.log('✅ ツイート投稿完了！');
    } else {
      throw new Error('投稿ボタンが見つかりません');
    }

    // スクリーンショット取得（確認用）
    await page.screenshot({ path: '/opt/shared/x-post-success.png' });
    console.log('📸 スクリーンショット保存: /opt/shared/x-post-success.png');

    console.log('🎉 X投稿完了！');

  } catch (error) {
    console.error('❌ エラー発生:', error.message);
    throw error;
  } finally {
    await browser.close();
  }
}

// コマンドライン引数をパース
const args = process.argv.slice(2);
const options = {};

for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace('--', '');
  const value = args[i + 1];

  if (key === 'cookie') options.cookie = value;
  if (key === 'tweet') options.tweetText = value;
}

if (!options.cookie || !options.tweetText) {
  console.error('使い方: node x-auto-post.js --cookie "auth_token=..." --tweet "ツイート内容"');
  process.exit(1);
}

postToX(options).catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
