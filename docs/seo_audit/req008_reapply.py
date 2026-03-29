#!/usr/bin/env python3
"""REQ-008 re-apply: Append FAQPage JSON-LD to /predictions/ and /en/predictions/ codeinjection_head."""

import jwt, time, requests, warnings, json
warnings.filterwarnings('ignore')

API_KEY = '6995030a3b8c7ab6f20bfe27:c071ad0cfe5b40b44a57890899d3edda40f6caede282ca2eda66a82980634d2c'
BASE_URL = 'https://nowpattern.com/ghost/api/admin'

def get_token():
    kid, secret = API_KEY.split(':')
    payload = {'iat': int(time.time()), 'exp': int(time.time()) + 300, 'aud': '/admin/'}
    return jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': kid})

def get_page(slug):
    token = get_token()
    r = requests.get(
        BASE_URL + '/pages/?filter=slug:' + slug + '&fields=id,slug,codeinjection_head,updated_at',
        headers={'Authorization': 'Ghost ' + token}, verify=False)
    pages = r.json().get('pages', [])
    return pages[0] if pages else None

def update_page_head(page_id, updated_at, new_head):
    token = get_token()
    payload = {'pages': [{'codeinjection_head': new_head, 'updated_at': updated_at}]}
    r = requests.put(
        BASE_URL + '/pages/' + page_id + '/',
        headers={'Authorization': 'Ghost ' + token, 'Content-Type': 'application/json'},
        json=payload, verify=False)
    return r.status_code

FAQ_JA = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Nowpatternの予測はどのように検証されますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Nowpatternの予測はprediction_auto_verifier.pyによって自動的に検証されます。判定日が過ぎた予測は、AIとニュース検索を組み合わせて的中・外れを自動判定し、Brier Scoreで精度を計算します。"
      }
    },
    {
      "@type": "Question",
      "name": "Brier Scoreとは何ですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Brier Scoreは予測精度を測る指標で、0に近いほど精度が高いことを示します。Nowpatternでは全予測の平均Brier Scoreを公開し、予測の信頼性を透明に示しています。0.00〜0.10が優秀（Excellent）、0.10〜0.20が良好（Good）です。"
      }
    },
    {
      "@type": "Question",
      "name": "予測に参加するにはどうすればいいですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "各予測カードにある投票ボタンから、楽観・基本・悲観シナリオのいずれかを選んで確率を投票できます。アカウント登録不要で、匿名（UUID）のまま参加可能です。"
      }
    },
    {
      "@type": "Question",
      "name": "過去の予測結果はどこで確認できますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "このページの「解決済み予測」セクションで、判定済みの全予測（的中・外れ・Brier Score）を確認できます。予測ごとに判定日、確率、最終結果が記録されています。"
      }
    }
  ]
}
</script>"""

FAQ_EN = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How are Nowpattern's predictions verified?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Nowpattern predictions are automatically verified by prediction_auto_verifier.py. After the resolution date passes, AI and news search are combined to judge hit or miss, and accuracy is calculated using Brier Score."
      }
    },
    {
      "@type": "Question",
      "name": "What is a Brier Score?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The Brier Score measures prediction accuracy — the closer to 0, the higher the accuracy. Nowpattern publishes the average Brier Score of all predictions to show reliability transparently. 0.00–0.10 is Excellent, 0.10–0.20 is Good."
      }
    },
    {
      "@type": "Question",
      "name": "How can I participate in predictions?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Use the vote button on each prediction card to select optimistic, base, or pessimistic scenario and submit your probability. No account registration required — you can participate anonymously via UUID."
      }
    },
    {
      "@type": "Question",
      "name": "Where can I check past prediction results?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "See the 'Resolved Predictions' section on this page for all judged predictions (hit/miss/Brier Score). Each prediction records the resolution date, probability, and final outcome."
      }
    }
  ]
}
</script>"""

results = {}

for slug, label, faq_block in [
    ('predictions', 'JA', FAQ_JA),
    ('en-predictions', 'EN', FAQ_EN),
]:
    p = get_page(slug)
    if not p:
        print(label + ': page not found')
        continue

    ci = p.get('codeinjection_head', '') or ''

    # Check if FAQPage already present
    if 'FAQPage' in ci:
        print(label + ': FAQPage already present (' + str(len(ci)) + ' chars). Skipping.')
        results[label] = 'already_present'
        continue

    # Append FAQPage block
    new_head = ci + '\n' + faq_block.strip()
    status = update_page_head(p['id'], p['updated_at'], new_head)

    if status == 200:
        print(label + ': FAQPage applied OK. New len=' + str(len(new_head)) + ' chars (was ' + str(len(ci)) + ')')
        results[label] = 'applied'
    else:
        print(label + ': FAILED status=' + str(status))
        results[label] = 'failed'

print('Done:', results)
