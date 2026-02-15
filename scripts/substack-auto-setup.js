#!/usr/bin/env node
/**
 * Substack自動設定スクリプト（Puppeteer）
 *
 * 使い方:
 * node substack-auto-setup.js --cookie "connect.sid=..." --about "テキスト" --welcome "テキスト"
 */

const puppeteer = require('puppeteer');
const fs = require('fs');

async function setupSubstack(options) {
  const { cookie, aboutText, welcomeText } = options;

  console.log('🚀 Substack自動設定を開始します...');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();

    // Cookieでログイン
    console.log('🔐 Cookieでログイン中...');
    await page.setCookie({
      name: 'connect.sid',
      value: cookie,
      domain: '.substack.com',
      path: '/',
      httpOnly: true,
      secure: true
    });

    // Aboutページ設定
    if (aboutText) {
      console.log('📝 Aboutページを設定中...');
      await page.goto('https://substack.com/settings', { waitUntil: 'networkidle2' });

      // Aboutタブをクリック
      await page.click('a[href*="about"]');
      await page.waitForTimeout(2000);

      // テキストエリアに入力
      const aboutTextarea = await page.$('textarea[name="about"]');
      if (aboutTextarea) {
        await aboutTextarea.click({ clickCount: 3 }); // 全選択
        await aboutTextarea.type(aboutText);
        console.log('✅ Aboutテキスト入力完了');
      }

      // 保存
      const saveButton = await page.$('button[type="submit"]');
      if (saveButton) {
        await saveButton.click();
        await page.waitForTimeout(2000);
        console.log('✅ About保存完了');
      }
    }

    // Welcome Email設定
    if (welcomeText) {
      console.log('📧 Welcome Emailを設定中...');
      await page.goto('https://substack.com/settings/emails', { waitUntil: 'networkidle2' });

      // Welcome Emailセクションを探す
      const welcomeToggle = await page.$('input[type="checkbox"][name="welcome_email_enabled"]');
      if (welcomeToggle) {
        const isChecked = await page.evaluate(el => el.checked, welcomeToggle);
        if (!isChecked) {
          await welcomeToggle.click();
          console.log('✅ Welcome Emailを有効化');
        }
      }

      // Welcome Emailテキストエリアに入力
      const welcomeTextarea = await page.$('textarea[name="welcome_email_body"]');
      if (welcomeTextarea) {
        await welcomeTextarea.click({ clickCount: 3 });
        await welcomeTextarea.type(welcomeText);
        console.log('✅ Welcome Emailテキスト入力完了');
      }

      // 保存
      const saveButton = await page.$('button[type="submit"]');
      if (saveButton) {
        await saveButton.click();
        await page.waitForTimeout(2000);
        console.log('✅ Welcome Email保存完了');
      }
    }

    console.log('🎉 Substack設定完了！');

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
  if (key === 'about') options.aboutText = value;
  if (key === 'welcome') options.welcomeText = value;
  if (key === 'about-file') options.aboutText = fs.readFileSync(value, 'utf8');
  if (key === 'welcome-file') options.welcomeText = fs.readFileSync(value, 'utf8');
}

if (!options.cookie) {
  console.error('使い方: node substack-auto-setup.js --cookie "connect.sid=..." --about "テキスト"');
  process.exit(1);
}

setupSubstack(options).catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
