#!/bin/bash
# patch_caddy_ai_routes.sh
# Caddyfileに llms.txt / robots.txt / sitemap XML の配信ルートを追加する。
# VPS上で実行: bash /opt/shared/scripts/patch_caddy_ai_routes.sh
set -e

CADDYFILE="/etc/caddy/Caddyfile"
SHARED_DIR="/opt/shared"
BACKUP="${CADDYFILE}.bak.$(date +%Y%m%d%H%M%S)"

# --- 冪等チェック: 既にパッチ済みなら何もしない ---
if grep -q "llms.txt" "$CADDYFILE" 2>/dev/null; then
    echo "OK: Caddyfile already patched (llms.txt route exists). Nothing to do."
    exit 0
fi

echo "Backing up Caddyfile -> $BACKUP"
cp "$CADDYFILE" "$BACKUP"

# --- 追記するルート設定 ---
# nowpattern.com ブロック内の末尾（最後の "}" の直前）に挿入する
PATCH=$(cat <<'CADDY_PATCH'

    # ─── AI-optimized static files (added by patch_caddy_ai_routes.sh) ───
    handle /llms.txt {
        root * /opt/shared
        file_server
    }
    handle /robots.txt {
        root * /opt/shared
        file_server
    }
    handle /sitemap.xml {
        root * /opt/shared
        file_server
    }
    handle /sitemap-news.xml {
        root * /opt/shared
        file_server
    }
    # ─────────────────────────────────────────────────────────────────────
CADDY_PATCH
)

# nowpattern.com ブロックの最後の } の直前に挿入
# Caddyfileの構造: nowpattern.com { ... reverse_proxy ... \n}
python3 - <<PYEOF
import re, sys

with open("$CADDYFILE", "r") as f:
    content = f.read()

patch = '''$PATCH'''

# nowpattern.com { ... } ブロックを探して、閉じ括弧の直前に挿入
# 末尾の単独 } を探して挿入（最後のブロック終端）
new_content = re.sub(
    r'(\n\})\s*$',
    patch + r'\n}',
    content,
    count=1,
    flags=re.MULTILINE
)

if new_content == content:
    print("ERROR: Could not find insertion point in Caddyfile. Manual edit required.")
    sys.exit(1)

with open("$CADDYFILE", "w") as f:
    f.write(new_content)

print("OK: Caddyfile patched successfully.")
PYEOF

# --- 配信ファイルの存在確認 ---
echo ""
echo "Checking static files in $SHARED_DIR ..."
for f in llms.txt robots.txt sitemap.xml sitemap-news.xml; do
    if [ -f "$SHARED_DIR/$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ $f (NOT FOUND — run deploy_llms_txt() / generate_news_sitemap() first)"
    fi
done

# --- Caddy設定を検証して再起動 ---
echo ""
echo "Validating Caddyfile..."
caddy validate --config "$CADDYFILE" --adapter caddyfile

echo "Reloading Caddy..."
caddy reload --config "$CADDYFILE" --adapter caddyfile

echo ""
echo "=== Done! ==="
echo "Test URLs:"
echo "  curl -I https://nowpattern.com/llms.txt"
echo "  curl -I https://nowpattern.com/robots.txt"
echo "  curl -I https://nowpattern.com/sitemap.xml"
echo "  curl -I https://nowpattern.com/sitemap-news.xml"
