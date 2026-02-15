#!/usr/bin/env python3
"""Final fix: Add error logging and ensure progress updates work."""

# Read orchestrator.py
with open("/opt/claude-code-telegram/src/bot/orchestrator.py", "r") as f:
    lines = f.readlines()

# Find and replace the update_progress_message function with one that logs errors
new_function = '''async def update_progress_message(message, start_time: float, task_name: str = "Processing"):
    """Background task to update progress message with elapsed time."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        while True:
            elapsed = int(time.time() - start_time)
            new_text = f"⏳ {task_name}... ({elapsed}s)"
            try:
                await message.edit_text(new_text)
                logger.info(f"Progress updated: {new_text}")
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")
            await asyncio.sleep(5)  # Update every 5 seconds
    except asyncio.CancelledError:
        logger.info("Progress task cancelled")
    except Exception as e:
        logger.error(f"Progress task error: {e}")

'''

# Find the function and replace it
in_function = False
function_start = -1
function_end = -1

for i, line in enumerate(lines):
    if "async def update_progress_message" in line:
        function_start = i
        in_function = True
    elif in_function and (line.startswith("class ") or line.startswith("async def ") or line.startswith("def ")):
        function_end = i
        break

if function_start >= 0:
    if function_end < 0:
        # Find next empty line or class
        for i in range(function_start + 1, len(lines)):
            if lines[i].strip() == "" and i > function_start + 5:
                function_end = i
                break

    # Replace the function
    lines = lines[:function_start] + [new_function] + lines[function_end:]

# Write back
with open("/opt/claude-code-telegram/src/bot/orchestrator.py", "w") as f:
    f.writelines(lines)

print("✅ Added error logging to progress function")
print("   Check logs with: journalctl -u neo-telegram.service -f")
