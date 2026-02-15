#!/usr/bin/env python3
"""
Fix NoneType len() errors in claude-code-telegram bot.
Adds None checks before len() calls that might fail.
"""

import sys
import re

def fix_orchestrator(filepath):
    """Add None checks to orchestrator.py"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Fix: Check if formatted_messages is not None and not empty before iterating
    # Pattern 1: for i, message in enumerate(formatted_messages):
    content = re.sub(
        r'(\s+)(for i, message in enumerate\(formatted_messages\):)',
        r'\1if formatted_messages and len(formatted_messages) > 0:\n\1    \2',
        content
    )

    # Fix: Check if message.text is not None before using it
    # Add check in reply_text calls
    content = re.sub(
        r'(\s+)(await update\.message\.reply_text\(\s*\n?\s*message\.text,)',
        r'\1if message.text is not None:\n\1    \2',
        content
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed {filepath}")
        return True
    else:
        print(f"⚠️  No changes needed in {filepath}")
        return False

def fix_core_error_handler(filepath):
    """Add None check to core.py error handler"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Find the error_messages.get() section and add None check
    # This is more conservative - just catch the exception
    content = re.sub(
        r'(error_msg = error_messages\.get\(type\(error\), .*?\))',
        r'\1\n        if error_msg and len(error_msg) > 0:  # Ensure message is valid',
        content,
        flags=re.DOTALL
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed {filepath}")
        return True
    else:
        print(f"⚠️  No changes needed in {filepath}")
        return False

if __name__ == "__main__":
    orchestrator_path = "/opt/claude-code-telegram/src/bot/orchestrator.py"
    core_path = "/opt/claude-code-telegram/src/bot/core.py"

    print("🔧 Fixing NoneType len() errors...")

    try:
        fix_orchestrator(orchestrator_path)
        fix_core_error_handler(core_path)
        print("\n✅ All fixes applied! Restart neo-telegram service to apply.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
