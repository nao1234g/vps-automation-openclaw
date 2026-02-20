#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEO-GPT Orchestrator — Telegram Bot backed by OpenAI Codex CLI
==============================================================
NEO-1/2 (Claude Code) のバックアップとして機能する。
Telegram メッセージを受信 → codex exec で処理 → 結果を返信。

Usage on VPS:
    export TELEGRAM_BOT_TOKEN="8403014876:AAHZOPGq1lsvfh_Wgncu5YzEpfdb6WHc9L0"
    export ALLOWED_USERS="your_telegram_user_id"
    python3 neo3_orchestrator.py
"""

import asyncio
import html
import logging
import os
import signal
import sys
import time
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ──────────────────────────── Config ────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "")  # comma-separated user IDs
CODEX_TIMEOUT = int(os.environ.get("CODEX_TIMEOUT", "300"))  # seconds
CODEX_MODEL = os.environ.get("CODEX_MODEL", "o4-mini")  # default model
WORK_DIR = os.environ.get("CODEX_WORK_DIR", "/opt/neo3-codex/workspace")
LOG_DIR = Path(os.environ.get("LOG_DIR", "/opt/neo3-codex/logs"))
TELEGRAM_MAX_MSG = 4096

# ──────────────────────────── Logging ───────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "neo3.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("neo3")


# ──────────────────────────── Auth ──────────────────────────────
def is_allowed(user_id: int) -> bool:
    """Check if user is in the allow-list."""
    if not ALLOWED_USERS:
        return True  # no restriction if not set
    allowed = [int(uid.strip()) for uid in ALLOWED_USERS.split(",") if uid.strip()]
    return user_id in allowed


# ──────────────────────────── Codex CLI ─────────────────────────
async def run_codex(prompt: str, timeout: int = CODEX_TIMEOUT) -> tuple[bool, str]:
    """
    Run `codex exec` non-interactively and return (success, output).
    Uses --full-auto approval mode for autonomous operation.
    """
    cmd = [
        "codex",
        "exec",
        prompt,
        "--full-auto",
        "--model", CODEX_MODEL,
    ]

    logger.info(f"Running codex: {' '.join(cmd[:4])}...")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORK_DIR,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return False, f"⏰ タイムアウト ({timeout}秒) — タスクが長すぎます。"

        output = stdout.decode("utf-8", errors="replace").strip()
        errors = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            result = output if output else "(完了 — 出力なし)"
            logger.info(f"Codex OK: {len(result)} chars")
            return True, result
        else:
            error_msg = errors or output or f"Exit code: {proc.returncode}"
            logger.warning(f"Codex failed: {error_msg[:200]}")
            return False, f"❌ Codex エラー:\n{error_msg}"

    except FileNotFoundError:
        return False, "❌ `codex` コマンドが見つかりません。インストールを確認してください。"
    except Exception as e:
        logger.exception("Codex execution error")
        return False, f"❌ 実行エラー: {e}"


# ──────────────────────────── Progress ──────────────────────────
async def progress_updater(msg, start_time: float):
    """Update progress message every 8 seconds."""
    dots = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    try:
        while True:
            await asyncio.sleep(8)
            elapsed = int(time.time() - start_time)
            spinner = dots[i % len(dots)]
            try:
                await msg.edit_text(f"{spinner} NEO-GPT 処理中... ({elapsed}s)")
            except Exception:
                pass
            i += 1
    except asyncio.CancelledError:
        pass


# ──────────────────────────── Message Split ─────────────────────
def split_message(text: str, limit: int = TELEGRAM_MAX_MSG) -> list[str]:
    """Split long text into Telegram-safe chunks."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to split at newline
        split_pos = text.rfind("\n", 0, limit)
        if split_pos == -1:
            split_pos = limit
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    return chunks


# ──────────────────────────── Handlers ──────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ アクセス権がありません。")
        return

    await update.message.reply_text(
        "🤖 *NEO-GPT* へようこそ！\n\n"
        "OpenAI Codex CLI をバックエンドに使用しています。\n"
        "メッセージを送ると、Codex が処理して結果を返します。\n\n"
        "📋 *コマンド:*\n"
        "/start — このメッセージ\n"
        "/status — ステータス確認\n"
        "/model — 現在のモデル表示\n",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    if not is_allowed(update.effective_user.id):
        return

    # Check if codex is available
    try:
        proc = await asyncio.create_subprocess_exec(
            "codex", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        version = stdout.decode().strip() if proc.returncode == 0 else "不明"
    except FileNotFoundError:
        version = "未インストール"

    await update.message.reply_text(
        f"✅ *NEO-GPT ステータス*\n\n"
        f"🔧 Codex CLI: `{version}`\n"
        f"🧠 モデル: `{CODEX_MODEL}`\n"
        f"⏰ タイムアウト: {CODEX_TIMEOUT}s\n"
        f"📂 作業ディレクトリ: `{WORK_DIR}`\n",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /model command."""
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        f"🧠 現在のモデル: `{CODEX_MODEL}`\n"
        f"利用可能: `o3`, `o4-mini`, `codex-mini`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages — route to Codex CLI."""
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ アクセス権がありません。")
        return

    prompt = update.message.text
    if not prompt or not prompt.strip():
        return

    logger.info(f"[{user.id}] {user.first_name}: {prompt[:80]}...")

    # Send typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    # Send progress message
    start_time = time.time()
    progress_msg = await update.message.reply_text("⏳ NEO-GPT 処理中... (0s)")
    progress_task = asyncio.create_task(progress_updater(progress_msg, start_time))

    try:
        # Run Codex CLI
        success, result = await run_codex(prompt)

        # Cancel progress
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

        # Delete progress message
        try:
            await progress_msg.delete()
        except Exception:
            pass

        # Send result
        elapsed = int(time.time() - start_time)
        header = f"✅ 完了 ({elapsed}s)" if success else f"⚠️ エラー ({elapsed}s)"

        chunks = split_message(f"{header}\n\n{result}")
        for chunk in chunks:
            await update.message.reply_text(chunk)

    except Exception as e:
        progress_task.cancel()
        logger.exception("Message handling error")
        try:
            await progress_msg.edit_text(f"❌ エラー: {e}")
        except Exception:
            pass


# ──────────────────────────── Main ──────────────────────────────
def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN が設定されていません")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("NEO-GPT Orchestrator 起動")
    logger.info(f"  Bot Token: {BOT_TOKEN[:8]}...")
    logger.info(f"  Model: {CODEX_MODEL}")
    logger.info(f"  Timeout: {CODEX_TIMEOUT}s")
    logger.info(f"  Work Dir: {WORK_DIR}")
    logger.info("=" * 50)

    # Ensure work directory exists
    Path(WORK_DIR).mkdir(parents=True, exist_ok=True)

    # Build application
    app = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run
    logger.info("Polling 開始...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
