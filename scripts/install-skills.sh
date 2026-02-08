#!/bin/bash
# OpenClaw Skills Installation Script
# Installs useful community skills

set -e

echo "📦 OpenClaw スキルインストール開始..."

# Step 1: List available skills
echo "📋 Step 1: 利用可能なスキル確認..."
openclaw skills list 2>/dev/null || echo "Skills listing not available"

# Step 2: Install recommended skills
echo "🔧 Step 2: 推奨スキルをインストール..."

# Headless Browser - Web automation
openclaw skills add headless-browser 2>/dev/null || echo "Headless browser skill skipped"

# Weather - 天気予報
openclaw skills add weather 2>/dev/null || echo "Weather skill skipped"

# Web Search - ウェブ検索（Brave連携）
openclaw skills add web-search 2>/dev/null || echo "Web search skill already installed"

# Calendar - カレンダー管理
openclaw skills add calendar 2>/dev/null || echo "Calendar skill skipped"

# Reminder - リマインダー
openclaw skills add reminder 2>/dev/null || echo "Reminder skill skipped"

# Step 3: Verify installed skills
echo "✅ Step 3: インストール済みスキル確認..."
openclaw skills list --installed 2>/dev/null || openclaw doctor

echo ""
echo "🎉 スキルインストール完了！"
echo ""
echo "確認コマンド:"
echo "  openclaw skills list --installed"
