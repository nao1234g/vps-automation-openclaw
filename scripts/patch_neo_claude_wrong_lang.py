#!/usr/bin/env python3
"""NEO-ONE CLAUDE.md に wrong_lang ルールを追加するパッチスクリプト"""
import sys

PATH = "/opt/claude-code-telegram/CLAUDE.md"
SEARCH = "| NEO指示を実行しない | system_promptにタスク実行指示がない | system_promptに「メッセージ=実行指示」と明示 |"
ADD = "| **EN予測のghost_url誤り** | ENのghost_urlにJA記事URLを設定 | EN予測は必ず `https://nowpattern.com/en/{slug}/` 形式。JA記事URLを流用しない |"

with open(PATH) as f:
    content = f.read()

if ADD in content:
    print("Already patched. Nothing to do.")
    sys.exit(0)

if SEARCH not in content:
    print(f"ERROR: target line not found in {PATH}")
    sys.exit(1)

new_content = content.replace(SEARCH, SEARCH + "\n" + ADD)
with open(PATH, "w") as f:
    f.write(new_content)
print("Patched successfully:", PATH)
print("Added rule: EN予測のghost_url誤り対策")
