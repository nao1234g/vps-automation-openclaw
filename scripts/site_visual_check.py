#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
site_visual_check.py — nowpattern.com 全ページ視覚確認
=======================================================
VPS上でPlaywrightを実行し、主要ページのスクリーンショット（全体）を
ローカルに取得する。CSSやテンプレート変更後に必ず実行すること。

カバー範囲:
  PC (1280px): JA/EN トップ + 動的ページネーション + 予測トラッカー
  SP (390px):  JA/EN トップ（iPhone 14 幅）
  --full-audit: 全42記事を nowpattern_visual_verify.py --all で検証

Usage:
    python3 scripts/site_visual_check.py                 # 全ページ（PC+SP、自動ページネーション）
    python3 scripts/site_visual_check.py --quick         # JA/ENトップのみ（PC+SP 4枚）
    python3 scripts/site_visual_check.py --full-audit    # 全記事テキスト検証も追加
    python3 scripts/site_visual_check.py --no-mobile     # PC幅のみ

Exit codes:
    0 = 全ページ取得成功
    1 = 1件以上失敗
"""
import json
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import ssl
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VPS_HOST = "root@163.44.124.123"
BASE_URL  = "https://nowpattern.com"
LOCAL_DIR = Path(tempfile.gettempdir())

# SSL context（ローカルからのページネーション検出用）
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

# ─── ターゲット形式: (name, url, label, width, height, is_mobile) ─────────
# 動的ページネーションで上書きされるため、実行時に discover_pagination() で生成する

QUICK_TARGETS = [
    ("ja_top",   f"{BASE_URL}/",    "JA トップ PC",  1280, 900, False),
    ("ja_top_m", f"{BASE_URL}/",    "JA トップ SP",  390, 844, True),
    ("en_top",   f"{BASE_URL}/en/", "EN トップ PC",  1280, 900, False),
    ("en_top_m", f"{BASE_URL}/en/", "EN トップ SP",  390, 844, True),
]

FIXED_TARGETS = [
    ("ja_top",     f"{BASE_URL}/",                    "JA トップ PC",    1280, 900, False),
    ("ja_top_m",   f"{BASE_URL}/",                    "JA トップ SP",    390, 844, True),
    ("en_top",     f"{BASE_URL}/en/",                 "EN トップ PC",    1280, 900, False),
    ("en_top_m",   f"{BASE_URL}/en/",                 "EN トップ SP",    390, 844, True),
    ("prediction", f"{BASE_URL}/predictions/",         "予測トラッカー",  1280, 900, False),
]

# VPS側で実行するPlaywrightスクリプト（6-tuple形式対応）
VPS_SCRIPT_CONTENT = """\
import sys, json, time
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("PLAYWRIGHT_NOT_INSTALLED")
    sys.exit(1)

with open("/tmp/_site_visual_targets.json") as f:
    targets = json.load(f)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    for target in targets:
        name, url, label, width, height, is_mobile = target
        try:
            ctx_options = {
                "viewport": {"width": width, "height": height},
                "ignore_https_errors": True,
            }
            if is_mobile:
                ctx_options["is_mobile"] = True
                ctx_options["has_touch"] = True
                ctx_options["user_agent"] = MOBILE_UA
            ctx = browser.new_context(**ctx_options)
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
            path = f"/tmp/visual_{name}.png"
            page.screenshot(path=path, full_page=True)
            page.close()
            ctx.close()
            results.append({"name": name, "path": path, "ok": True})
            print(f"OK:{name}:{path}")
        except Exception as e:
            results.append({"name": name, "error": str(e), "ok": False})
            print(f"ERR:{name}:{str(e)[:120]}")
    browser.close()
"""


# ─────────────────────────────────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def ssh_run(cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=no",
         VPS_HOST, cmd],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=timeout
    )


def scp_to_vps(local: Path, remote: str) -> bool:
    r = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", str(local), f"{VPS_HOST}:{remote}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return r.returncode == 0


def scp_from_vps(remote: str, local: Path) -> bool:
    r = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", f"{VPS_HOST}:{remote}", str(local)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return r.returncode == 0


# ─────────────────────────────────────────────────────────────────────────────
# 動的ページネーション検出（ローカルから直接HTTP）
# ─────────────────────────────────────────────────────────────────────────────

def discover_pagination() -> dict:
    """
    JA: /page/N/  および  EN: /en/page/N/ を
    404 が出るまで連続チェックして最大ページ数を返す。
    """
    result = {"ja": 1, "en": 1}
    print("🔍 ページネーション自動検出中...")

    for prefix, key in [("/page/", "ja"), ("/en/page/", "en")]:
        for n in range(2, 50):
            url = f"{BASE_URL}{prefix}{n}/"
            try:
                req = urllib.request.Request(url, method="HEAD")
                req.add_header("User-Agent", "SiteVisualCheck/1.0")
                with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
                    if resp.status == 200:
                        result[key] = n
                    else:
                        break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
            except Exception:
                break
            time.sleep(0.05)

    print(f"   JA: 最終ページ {result['ja']}  |  EN: 最終ページ {result['en']}")
    return result


def build_targets(quick: bool, no_mobile: bool) -> list:
    """
    撮影ターゲットリストを組み立てる。
    ページネーションは自動検出した最大ページまでを追加。
    """
    if quick:
        targets = list(QUICK_TARGETS)
        if no_mobile:
            targets = [t for t in targets if not t[5]]
        return targets

    # フルモード: ページネーション自動検出
    pagination = discover_pagination()
    targets = list(FIXED_TARGETS)

    # JA ページネーション（/page/2 〜 最大ページ）
    for n in range(2, pagination["ja"] + 1):
        targets.append((
            f"ja_page{n}", f"{BASE_URL}/page/{n}/", f"JA ページ{n} PC", 1280, 900, False
        ))

    # EN ページネーション（/en/page/2 〜 最大ページ）
    for n in range(2, pagination["en"] + 1):
        targets.append((
            f"en_page{n}", f"{BASE_URL}/en/page/{n}/", f"EN ページ{n} PC", 1280, 900, False
        ))

    if no_mobile:
        targets = [t for t in targets if not t[5]]

    return targets


# ─────────────────────────────────────────────────────────────────────────────
# --full-audit モード: nowpattern_visual_verify.py --all 実行
# ─────────────────────────────────────────────────────────────────────────────

def run_full_audit():
    """
    VPS上の nowpattern_visual_verify.py --all を実行し、
    テキスト検証結果を表示する。
    """
    print()
    print("=" * 68)
    print("  🔬 --full-audit: 全42記事テキスト検証")
    print("     (nowpattern_visual_verify.py --all)")
    print("=" * 68)
    print("  ⏳ VPSで実行中（1〜3分かかります）...")

    try:
        r = ssh_run(
            "python3 /opt/shared/scripts/nowpattern_visual_verify.py --all 2>&1",
            timeout=300
        )
    except subprocess.TimeoutExpired:
        print("  ❌ タイムアウト（300秒）")
        return
    except Exception as e:
        print(f"  ❌ SSH エラー: {e}")
        return

    output = r.stdout or r.stderr
    # 先頭3000文字を表示
    print()
    for line in output[:3000].splitlines():
        print(f"  {line}")
    if len(output) > 3000:
        print(f"  ... (出力が長いため省略、全文はVPSで確認)")
    print()

    # 結果ファイルをダウンロード（存在すれば）
    report_path = LOCAL_DIR / "nowpattern_full_audit_report.txt"
    report_path.write_text(output, encoding="utf-8", errors="replace")
    print(f"  📄 フルレポート保存: {report_path}")
    print("=" * 68)


# ─────────────────────────────────────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    quick      = "--quick"      in args
    full_audit = "--full-audit" in args
    no_mobile  = "--no-mobile"  in args

    mode_parts = []
    if quick:
        mode_parts.append("クイック")
    else:
        mode_parts.append("フル")
    if not no_mobile:
        mode_parts.append("PC+SP")
    else:
        mode_parts.append("PCのみ")
    if full_audit:
        mode_parts.append("全記事監査")
    mode = " / ".join(mode_parts)

    print(f"📸 nowpattern.com 視覚確認 [{mode}]")
    print(f"   VPS: {VPS_HOST}")
    print(f"   保存先: {LOCAL_DIR}")
    print()

    # ターゲットリストを組み立て
    targets = build_targets(quick=quick, no_mobile=no_mobile)
    print(f"   ターゲット: {len(targets)}ページ")
    print()

    # ── Step 1: VPSにスクリプトと設定ファイルを転送 ──────────────────────
    script_local = LOCAL_DIR / "_site_visual_check_vps.py"
    script_local.write_text(VPS_SCRIPT_CONTENT, encoding="utf-8")

    targets_local = LOCAL_DIR / "_site_visual_targets.json"
    targets_local.write_text(json.dumps(targets, ensure_ascii=False), encoding="utf-8")

    print("📤 スクリプトをVPSに転送中...")
    if not scp_to_vps(script_local, "/tmp/_site_visual_check_vps.py"):
        print("❌ スクリプト転送失敗")
        sys.exit(1)
    if not scp_to_vps(targets_local, "/tmp/_site_visual_targets.json"):
        print("❌ 設定ファイル転送失敗")
        sys.exit(1)
    print("   完了\n")

    # ── Step 2: VPS上でPlaywrightを実行 ──────────────────────────────────
    print("🎭 VPS上でPlaywrightを実行中...")
    est_sec = len(targets) * 6
    print(f"   （予想 {est_sec}秒）")

    try:
        r = ssh_run("python3 /tmp/_site_visual_check_vps.py",
                    timeout=max(180, est_sec + 60))
    except subprocess.TimeoutExpired:
        print(f"❌ タイムアウト ({max(180, est_sec + 60)}秒)")
        sys.exit(1)
    except Exception as e:
        print(f"❌ SSH エラー: {e}")
        sys.exit(1)

    if "PLAYWRIGHT_NOT_INSTALLED" in r.stdout:
        print("❌ VPSにPlaywrightがインストールされていません")
        print("   → ssh root@163.44.124.123 "
              "'pip install playwright && playwright install chromium'")
        sys.exit(1)

    for line in r.stdout.splitlines():
        if line.startswith("OK:") or line.startswith("ERR:"):
            status = "✅" if line.startswith("OK:") else "❌"
            parts = line.split(":", 2)
            name = parts[1] if len(parts) > 1 else "?"
            info = parts[2] if len(parts) > 2 else ""
            print(f"   {status} {name}: {info}")
    if r.returncode != 0 and r.stderr:
        print(f"   ⚠️ stderr: {r.stderr[:200]}")
    print()

    # ── Step 3: スクリーンショットをローカルにSCP ─────────────────────
    print("📥 スクリーンショットをダウンロード中...")
    print()

    ok_count = 0
    local_paths = []

    for name, url, label, width, height, is_mobile in targets:
        vps_path   = f"/tmp/visual_{name}.png"
        local_path = LOCAL_DIR / f"nowpattern_visual_{name}.png"

        if scp_from_vps(vps_path, local_path) and local_path.exists():
            size_kb   = local_path.stat().st_size // 1024
            sp_marker = "📱" if is_mobile else "🖥️ "
            print(f"  ✅ {sp_marker} {label:<24} {size_kb:>5}KB  {local_path}")
            local_paths.append((label, url, str(local_path), is_mobile))
            ok_count += 1
        else:
            sp_marker = "📱" if is_mobile else "🖥️ "
            print(f"  ❌ {sp_marker} {label:<24} SCP失敗")

    print()
    print("=" * 68)
    print(f"  📊 結果: {ok_count}/{len(targets)} ページ取得成功")
    print()

    if local_paths:
        pc_list = [(l, u, p) for l, u, p, m in local_paths if not m]
        sp_list = [(l, u, p) for l, u, p, m in local_paths if m]

        if pc_list:
            print("  🖥️  PC幅 (1280px):")
            for label, url, path in pc_list:
                print(f"     {label}")
                print(f"       path: {path}")
                print(f"       URL:  {url}")
            print()

        if sp_list:
            print("  📱 SP幅 (390px — iPhone 14):")
            for label, url, path in sp_list:
                print(f"     {label}")
                print(f"       path: {path}")
                print(f"       URL:  {url}")
            print()

        print("  → full_page=True で撮影: スクロール全体が1枚の縦長画像に収録済み")
        print("  → Read tool で画像を渡せばClaudeが視覚確認できます")

    print("=" * 68)

    # ── Step 4: --full-audit モード ───────────────────────────────────
    if full_audit:
        run_full_audit()

    if ok_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
