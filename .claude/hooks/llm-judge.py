#!/usr/bin/env python3
"""
LLM-as-Judge — PreToolUse Hook (ECC Pipeline拡張: 意味レベル検知)
======================================================================
既知パターンはregexで防げる。しかし未知ミスは防げない。
LLM-as-Judgeはコードの「意味」を理解して、
regexが見逃すパターンバリエーション・設計ミスを事前に検知する。

世界水準の根拠:
  OpenAI Self-Evolving Agents: LLM-as-judge for iterative improvement
  Google SRE: "Catch errors at source, before they cascade"
  Anthropic Constitutional AI: Inference-time rule enforcement

動作条件 (ALL必須):
  - tool: Edit または Write
  - 変更サイズ: new_string/content が 200文字以上
  - ファイル種別: .py または .sh
  - GEMINI_API_KEY: 環境変数 or .env に設定済み

タイムアウト: 8秒（遅い場合は通過させる。ガードは非同期の補完層）
"""
import json
import os
import sys
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
STATE_DIR = PROJECT_DIR / ".claude" / "hooks" / "state"
PATTERNS_FILE = STATE_DIR / "mistake_patterns.json"
MISTAKES_FILE = PROJECT_DIR / "docs" / "KNOWN_MISTAKES.md"
LOG_FILE = STATE_DIR / "llm_judge_log.json"

# ── しきい値 ────────────────────────────────────────────────────────────────
MIN_CHANGE_LEN = 200   # これ以下の変更はスキップ（小さな編集は対象外）
CODE_EXTENSIONS = {".py", ".sh"}  # コード変更のみ対象
MAX_CONTENT_CHARS = 1500  # Geminiに送る最大文字数

# ── .envからAPIキー読み込み ─────────────────────────────────────────────────
def load_api_key() -> str:
    # 1. 環境変数を優先
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    # 2. .envファイルから読む
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GOOGLE_API_KEY=") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and not val.startswith("$"):
                        return val
        except Exception:
            pass
    return ""


# ── 既知パターンのサマリー（プロンプト用）──────────────────────────────────
def load_pattern_summary() -> str:
    patterns = []
    if PATTERNS_FILE.exists():
        try:
            raw = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
            for p in raw[:15]:  # 最大15パターン（プロンプト節約）
                name = p.get("name", "?")
                feedback = p.get("feedback", "").replace("⛔ ", "")[:80]
                example = p.get("example", "")[:60]
                patterns.append(f"- {name}: {feedback}")
                if example:
                    patterns.append(f"  例: {example}")
        except Exception:
            pass
    if not patterns:
        return "(パターンなし)"
    return "\n".join(patterns[:30])


# ── Gemini API 呼び出し ─────────────────────────────────────────────────────
def ask_gemini(api_key: str, prompt: str) -> dict:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.0-flash:generateContent?key={api_key}"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256,
            "responseMimeType": "application/json"
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read().decode("utf-8"))
            text = resp["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except (urllib.error.URLError, TimeoutError):
        return {"violation": False, "skip_reason": "timeout"}
    except Exception as e:
        return {"violation": False, "skip_reason": str(e)[:50]}


# ── ログ記録 ────────────────────────────────────────────────────────────────
def log_judgment(file_path: str, result: dict) -> None:
    try:
        entries = []
        if LOG_FILE.exists():
            try:
                entries = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            except Exception:
                entries = []
        entries.append({
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "file": str(file_path),
            "violation": result.get("violation", False),
            "pattern": result.get("pattern"),
            "reason": result.get("reason", "")[:100],
            "skip_reason": result.get("skip_reason", ""),
        })
        if len(entries) > 500:
            entries = entries[-500:]
        LOG_FILE.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# ── メイン ──────────────────────────────────────────────────────────────────
def main():
    # stdin からツール入力を読む
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    # ファイルパスと変更内容を取得
    file_path = tool_input.get("file_path", "")
    ext = Path(file_path).suffix.lower()

    if ext not in CODE_EXTENSIONS:
        sys.exit(0)  # .py/.sh 以外はスキップ

    # 変更内容を取得
    if tool_name == "Edit":
        content = tool_input.get("new_string", "")
    else:  # Write
        content = tool_input.get("content", "")

    if len(content) < MIN_CHANGE_LEN:
        sys.exit(0)  # 小さすぎる変更はスキップ

    # APIキー確認
    api_key = load_api_key()
    if not api_key:
        sys.exit(0)  # キーなし → 通過（ガードは補完層）

    # パターンサマリー取得
    pattern_summary = load_pattern_summary()

    # プロンプト構築
    content_preview = content[:MAX_CONTENT_CHARS]
    prompt = f"""あなたはコードレビューのAIガードです。
以下のコード変更が、既知のアンチパターンに違反していないか確認してください。

# 既知アンチパターン一覧
{pattern_summary}

# 確認するコード変更
ファイル: {file_path}
変更内容:
```
{content_preview}
```

# 回答形式 (JSONのみ、説明不要)
{{
  "violation": true or false,
  "pattern": "違反したパターン名 or null",
  "reason": "違反理由を20字以内で（違反なしなら空文字）",
  "confidence": 0.0〜1.0
}}

注意: 明確に違反している場合のみ violation: true にしてください。
      可能性があるだけでは false にしてください。
      confidence が 0.8未満なら false にしてください。"""

    # Gemini呼び出し
    result = ask_gemini(api_key, prompt)

    # ログ記録（violation有無に関わらず）
    log_judgment(file_path, result)

    # 判定
    if result.get("violation") and result.get("confidence", 0) >= 0.8:
        pattern = result.get("pattern", "UNKNOWN")
        reason = result.get("reason", "LLM判定による違反")
        print(f"🤖 [LLM-Judge] 意味レベル違反検知: {pattern}")
        print(f"   理由: {reason}")
        print(f"   ファイル: {file_path}")
        print(f"   → この変更はKNOWN_MISTAKESのパターンに違反している可能性があります。")
        print(f"   → 変更内容を再確認してください。問題なければ続行できます。")
        # exit(1)でブロック（exit(2)は物理停止 — LLMは確信度が低いため警告に留める）
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
