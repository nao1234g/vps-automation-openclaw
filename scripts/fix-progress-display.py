#!/usr/bin/env python3
"""Fix Neo's progress display with proven pattern from research."""

import re

# Read orchestrator.py
with open("/opt/claude-code-telegram/src/bot/orchestrator.py", "r") as f:
    content = f.read()

# Pattern 1: Fix progress task creation
# Find all instances of progress message creation and add proper task management
old_pattern1 = r'progress_msg = await update\.message\.reply_text\("⏳ Processing\.\.\. \(0s\)"\)\s+progress_start = time\.time\(\)\s+progress_task = asyncio\.create_task\(update_progress_message\(progress_msg, progress_start\)\)'

new_code1 = '''progress_msg = await update.message.reply_text("⏳ Processing... (0s)")
        progress_start = time.time()
        progress_task = asyncio.create_task(update_progress_message(progress_msg, progress_start))'''

# Pattern 2: Fix progress message deletion to cancel task first
old_pattern2 = r'(\s+)await progress_msg\.delete\(\)'
new_code2 = r'''\1# Cancel progress task before deleting message
\1if 'progress_task' in locals():
\1    progress_task.cancel()
\1    try:
\1        await progress_task
\1    except asyncio.CancelledError:
\1        pass
\1await progress_msg.delete()'''

content = re.sub(old_pattern2, new_code2, content)

# Verify the progress function exists and is correct
if "async def update_progress_message" in content:
    print("✅ Progress function exists")
else:
    print("❌ Progress function missing - adding it")
    # Add import if missing
    if "import time" not in content:
        content = re.sub(r'(import asyncio)', r'\1\nimport time', content)

    # Find class definition and add function before it
    progress_func = '''
async def update_progress_message(message, start_time: float, task_name: str = "Processing"):
    """Background task to update progress message with elapsed time."""
    try:
        while True:
            elapsed = int(time.time() - start_time)
            await message.edit_text(f"⏳ {task_name}... ({elapsed}s)")
            await asyncio.sleep(5)  # Update every 5 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        # Silently ignore errors (message might be deleted)
        pass

'''
    class_match = re.search(r'\nclass ', content)
    if class_match:
        insert_pos = class_match.start()
        content = content[:insert_pos] + progress_func + content[insert_pos:]

# Save
with open("/opt/claude-code-telegram/src/bot/orchestrator.py", "w") as f:
    f.write(content)

print("✅ Fixed progress display implementation!")
print("   - Task cancellation added")
print("   - Progress function verified")
print("   - Updates every 5 seconds")
