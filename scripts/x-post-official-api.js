#!/usr/bin/env node
/**
 * X（Twitter）公式API投稿スクリプト（OAuth 1.0a）
 *
 * 使い方:
 * node x-post-official-api.js "ツイート内容"
 *
 * 環境変数:
 * TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
 */

const { TwitterApi } = require('twitter-api-v2');

// 環境変数から認証情報を取得
const client = new TwitterApi({
  appKey: process.env.TWITTER_API_KEY,
  appSecret: process.env.TWITTER_API_SECRET,
  accessToken: process.env.TWITTER_ACCESS_TOKEN,
  accessSecret: process.env.TWITTER_ACCESS_SECRET,
});

const rwClient = client.readWrite;

async function postTweet(text) {
  if (!text || text.trim().length === 0) {
    console.error('❌ エラー: ツイート内容が空です');
    process.exit(1);
  }

  if (text.length > 280) {
    console.error(`❌ エラー: ツイートが長すぎます（${text.length}文字 / 280文字）`);
    process.exit(1);
  }

  try {
    console.log('🐦 X（Twitter）に投稿中...');
    console.log(`📝 内容: ${text}`);

    const tweet = await rwClient.v2.tweet(text);

    console.log('✅ 投稿成功！');
    console.log(`🔗 URL: https://x.com/aisaintel/status/${tweet.data.id}`);
    console.log(`📊 Tweet ID: ${tweet.data.id}`);

    return tweet;
  } catch (error) {
    console.error('❌ 投稿失敗:', error.message);

    if (error.code === 401) {
      console.error('⚠️  認証エラー: APIキーまたはトークンが無効です');
    } else if (error.code === 403) {
      console.error('⚠️  権限エラー: このアカウントには投稿権限がありません');
    } else if (error.code === 429) {
      console.error('⚠️  レート制限: 投稿しすぎです。しばらく待ってから再試行してください');
    }

    throw error;
  }
}

// メイン処理
async function main() {
  // 環境変数チェック
  const requiredEnvVars = [
    'TWITTER_API_KEY',
    'TWITTER_API_SECRET',
    'TWITTER_ACCESS_TOKEN',
    'TWITTER_ACCESS_SECRET'
  ];

  const missingVars = requiredEnvVars.filter(v => !process.env[v]);

  if (missingVars.length > 0) {
    console.error('❌ エラー: 以下の環境変数が設定されていません:');
    missingVars.forEach(v => console.error(`  - ${v}`));
    console.error('\n環境変数を設定してから再実行してください。');
    process.exit(1);
  }

  // コマンドライン引数からツイート内容を取得
  const tweetText = process.argv.slice(2).join(' ');

  if (!tweetText) {
    console.error('使い方: node x-post-official-api.js "ツイート内容"');
    console.error('\n例:');
    console.error('  node x-post-official-api.js "Hello from AISA! 🚀"');
    process.exit(1);
  }

  await postTweet(tweetText);
}

// 実行
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { postTweet };
