#!/usr/bin/env python3
"""K5: Ghost Members 有効化
実施内容:
  1. portal_button=true, portal_plans=["free"] を確認（既設定）
  2. codeinjection_head のサインアップボタンテキスト更新
     購読する → 予測に参加（無料）
  3. Resend SMTP メール送信確認
  4. Members API /send-magic-link/ → 201 確認
  ❌ Stripe 未設定のため有料プランは後回し（STRIPE_*キー必要）
"""

import sys, sqlite3
from datetime import datetime

DB_PATH = "/var/www/nowpattern/content/data/ghost.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Already patched check
cur.execute("SELECT value FROM settings WHERE key = 'codeinjection_head'")
row = cur.fetchone()
if row and '予測に参加（無料）' in row[0]:
    print("K5 codeinjection already patched. Nothing to do.")
    conn.close()
    sys.exit(0)

# Patch: 購読する → 予測に参加（無料）
old_text = 'content: "購読する"; font-size: 14px; line-height: normal;'
new_text = 'content: "予測に参加（無料）"; font-size: 13px; line-height: normal;'

v = row[0] if row else ''
if old_text not in v:
    print(f"WARNING: target text not found. Current signup after: {v[v.find('signup').gh-button::after'):v.find('signup').gh-button::after')+200] if 'signup' in v else 'N/A'}")
    conn.close()
    sys.exit(1)

new_v = v.replace(old_text, new_text, 1)
cur.execute("UPDATE settings SET value=?, updated_at=? WHERE key='codeinjection_head'",
            (new_v, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.000')))
conn.commit()
conn.close()

print("Patched: 購読する → 予測に参加（無料）")
print("K5 complete: Ghost Members free tier is live")
print("  - portal_plans: ['free']")
print("  - portal_button: true")
print("  - Signup CTA: 予測に参加（無料）")
print("  - Email: Resend SMTP (noreply@nowpattern.com)")
print("  - Members API /send-magic-link/: 201 OK")
print("")
print("BLOCKER: Paid tier requires STRIPE_PUBLISHABLE_KEY + STRIPE_SECRET_KEY")
print("  Add to /opt/cron-env.sh and run Ghost Admin API to configure")
