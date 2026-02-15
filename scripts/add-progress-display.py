#!/usr/bin/env python3
"""Add dynamic progress display to Neo's Telegram orchestrator."""

import re

# Read orchestrator.py
with open("/opt/claude-code-telegram/src/bot/orchestrator.py", "r") as f:
    content = f.read()

# Add import statements at the top if not present
if "import time" not in content:
    # Find the import section and add time
    import_section = re.search(r"(import asyncio.*?\n)", content)
    if import_section:
        content = content.replace(import_section.group(1), import_section.group(1) + "import time\n")

# Add progress update function before the first class
progress_function = '''
async def update_progress_message(message, start_time: float, task_name: str = "Processing"):
    """Background task to update progress message with elapsed time."""
    try:
        while True:
            elapsed = int(time.time() - start_time)
            await message.edit_text(f"⏳ {task_name}... ({elapsed}s)")
            await asyncio.sleep(5)  # Update every 5 seconds
    except asyncio.CancelledError:
        pass
    except Exception:
        pass

'''

if "async def update_progress_message" not in content:
    # Find first class definition
    class_match = re.search(r"\nclass ", content)
    if class_match:
        insert_pos = class_match.start()
        content = content[:insert_pos] + progress_function + content[insert_pos:]

# Replace "Working..." with dynamic progress
old_pattern = r'progress_msg = await update\.message\.reply_text\("Working\.\.\."\)'
new_code = '''progress_msg = await update.message.reply_text("⏳ Processing... (0s)")
        progress_start = time.time()
        progress_task = asyncio.create_task(update_progress_message(progress_msg, progress_start))'''
content = re.sub(old_pattern, new_code, content)

# Cancel task before deleting progress message
old_delete = r'(\s+)await progress_msg\.delete\(\)'
new_delete = r'''\1if 'progress_task' in locals():
\1    progress_task.cancel()
\1    try:
\1        await progress_task
\1    except asyncio.CancelledError:
\1        pass
\1await progress_msg.delete()'''
content = re.sub(old_delete, new_delete, content)

# Save
with open("/opt/claude-code-telegram/src/bot/orchestrator.py", "w") as f:
    f.write(content)

print("✅ Progress display added successfully!")
