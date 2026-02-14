#!/usr/bin/env python3
"""Patch orchestrator.py to add progress indicator with elapsed time."""

import ast
import sys

FILEPATH = "/opt/claude-code-telegram/src/bot/orchestrator.py"

with open(FILEPATH, "r") as f:
    content = f.read()

# Verify it parses
ast.parse(content)
print("Original file parses OK")

# 1. Add _progress_updater method before agentic_text
progress_method = '''
    async def _progress_updater(self, progress_msg, interval=8):
        """Update progress message with elapsed time."""
        phases = [
            (0, "\U0001f9e0 Thinking..."),
            (15, "\U0001f50d Researching..."),
            (30, "\U0001f4dd Composing..."),
            (60, "\u23f3 Still working..."),
            (120, "\U0001f504 Deep analysis..."),
        ]
        elapsed = 0
        try:
            while True:
                await asyncio.sleep(interval)
                elapsed += interval
                label = phases[0][1]
                for threshold, text in phases:
                    if elapsed >= threshold:
                        label = text
                status = f"{label} ({elapsed}s)"
                try:
                    await progress_msg.edit_text(status)
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass

'''

content = content.replace(
    "    async def agentic_text(",
    progress_method + "    async def agentic_text(",
    1
)

# 2. In agentic_text: add progress task
old1 = '        progress_msg = await update.message.reply_text("Working...")\n\n        claude_integration = context.bot_data.get("claude_integration")'
new1 = '        progress_msg = await update.message.reply_text("\U0001f9e0 Thinking...")\n\n        claude_integration = context.bot_data.get("claude_integration")'
content = content.replace(old1, new1, 1)

# Add progress_task creation after session_id line in agentic_text
old2 = '        session_id = context.user_data.get("claude_session_id")\n\n        success = True\n        try:\n            claude_response = await claude_integration.run_command('
new2 = '        session_id = context.user_data.get("claude_session_id")\n\n        progress_task = asyncio.create_task(self._progress_updater(progress_msg))\n\n        success = True\n        try:\n            claude_response = await claude_integration.run_command('
content = content.replace(old2, new2, 1)

# 3. Add progress_task.cancel() before progress_msg.delete() in agentic_text
old3 = '        await progress_msg.delete()\n\n        for i, message in enumerate(formatted_messages):\n            try:\n                await update.message.reply_text(\n                    message.text,\n                    parse_mode=message.parse_mode,\n                    reply_markup=None,  # No keyboards in agentic mode'
new3 = '        progress_task.cancel()\n        await progress_msg.delete()\n\n        for i, message in enumerate(formatted_messages):\n            try:\n                await update.message.reply_text(\n                    message.text,\n                    parse_mode=message.parse_mode,\n                    reply_markup=None,  # No keyboards in agentic mode'
content = content.replace(old3, new3, 1)

# 4. Fix document handler
old4 = '        progress_msg = await update.message.reply_text("Working...")\n\n        # Try enhanced file handler'
new4 = '        progress_msg = await update.message.reply_text("\U0001f9e0 Thinking...")\n        progress_task = asyncio.create_task(self._progress_updater(progress_msg))\n\n        # Try enhanced file handler'
content = content.replace(old4, new4, 1)

# Cancel in document success path
old5 = '            await progress_msg.delete()\n\n            for i, message in enumerate(formatted_messages):\n                await update.message.reply_text(\n                    message.text,\n                    parse_mode=message.parse_mode,\n                    reply_markup=None,\n                    reply_to_message_id=(update.message.message_id if i == 0 else None),\n                )\n                if i < len(formatted_messages) - 1:\n                    await asyncio.sleep(0.5)\n\n        except Exception as e:\n            from .handlers.message import _format_error_message\n\n            await progress_msg.edit_text(\n                _format_error_message(str(e)), parse_mode="HTML"\n            )\n            logger.error("Claude file processing failed"'
new5 = '            progress_task.cancel()\n            await progress_msg.delete()\n\n            for i, message in enumerate(formatted_messages):\n                await update.message.reply_text(\n                    message.text,\n                    parse_mode=message.parse_mode,\n                    reply_markup=None,\n                    reply_to_message_id=(update.message.message_id if i == 0 else None),\n                )\n                if i < len(formatted_messages) - 1:\n                    await asyncio.sleep(0.5)\n\n        except Exception as e:\n            progress_task.cancel()\n            from .handlers.message import _format_error_message\n\n            await progress_msg.edit_text(\n                _format_error_message(str(e)), parse_mode="HTML"\n            )\n            logger.error("Claude file processing failed"'
content = content.replace(old5, new5, 1)

# 5. Fix photo handler
old6 = '        progress_msg = await update.message.reply_text("Working...")\n\n        try:\n            photo = update.message.photo[-1]'
new6 = '        progress_msg = await update.message.reply_text("\U0001f9e0 Thinking...")\n        progress_task = asyncio.create_task(self._progress_updater(progress_msg))\n\n        try:\n            photo = update.message.photo[-1]'
content = content.replace(old6, new6, 1)

# Cancel in photo success path
old7 = '            await progress_msg.delete()\n\n            for i, message in enumerate(formatted_messages):\n                await update.message.reply_text(\n                    message.text,\n                    parse_mode=message.parse_mode,\n                    reply_markup=None,\n                    reply_to_message_id=(update.message.message_id if i == 0 else None),\n                )\n                if i < len(formatted_messages) - 1:\n                    await asyncio.sleep(0.5)\n\n        except Exception as e:\n            from .handlers.message import _format_error_message\n\n            await progress_msg.edit_text(\n                _format_error_message(str(e)), parse_mode="HTML"\n            )\n            logger.error(\n                "Claude photo processing failed"'
new7 = '            progress_task.cancel()\n            await progress_msg.delete()\n\n            for i, message in enumerate(formatted_messages):\n                await update.message.reply_text(\n                    message.text,\n                    parse_mode=message.parse_mode,\n                    reply_markup=None,\n                    reply_to_message_id=(update.message.message_id if i == 0 else None),\n                )\n                if i < len(formatted_messages) - 1:\n                    await asyncio.sleep(0.5)\n\n        except Exception as e:\n            progress_task.cancel()\n            from .handlers.message import _format_error_message\n\n            await progress_msg.edit_text(\n                _format_error_message(str(e)), parse_mode="HTML"\n            )\n            logger.error(\n                "Claude photo processing failed"'
content = content.replace(old7, new7, 1)

# Verify patched file parses
try:
    ast.parse(content)
    print("Patched file parses OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR in patched file: {e}")
    sys.exit(1)

with open(FILEPATH, "w") as f:
    f.write(content)

print("Patch applied successfully!")
