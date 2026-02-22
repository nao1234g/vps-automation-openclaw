#!/usr/bin/env python3
"""NEO-ONE system_prompt にタクソノミー v3.0 情報を追加するパッチスクリプト"""

filepath = '/opt/claude-code-telegram/src/claude/sdk_integration.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_end = '- Claude Codeは画像ファイルを直接読める（マルチモーダル対応）"""'

taxonomy_block = """- Claude Codeは画像ファイルを直接読める（マルチモーダル対応）

# Nowpattern タクソノミー v3.0（記事執筆時のタグ制約）
## 力学タグ（16個 = 4x4、これ以外は使用禁止）
- 支配: プラットフォーム支配 / 規制の捕獲 / 物語の覇権 / 権力の過伸展
- 対立: 対立の螺旋 / 同盟の亀裂 / 経路依存 / 揺り戻し
- 崩壊: 制度の劣化 / 協調の失敗 / モラルハザード / 伝染の連鎖
- 転換: 危機便乗 / 後発逆転 / 勝者総取り / 正統性の空白

## イベントタグ（19個、これ以外は使用禁止）
軍事衝突 / 制裁・経済戦争 / 貿易・関税 / 規制・法改正 / 選挙・政権交代 / 市場ショック / 技術進展 / 条約・同盟変動 / 資源・エネルギー危機 / 司法・裁判 / 災害・事故 / 健康危機・感染症 / サイバー攻撃 / 社会不安・抗議 / 構造シフト / 事業再編・取引 / 競争・シェア争い / スキャンダル・信頼危機 / 社会変動・世論

## ジャンルタグ（12個）
政治・政策 / 地政学・安全保障 / 経済・金融 / ビジネス・企業 / テクノロジー / 暗号資産・Web3 / 科学・医療 / エネルギー・環境 / 社会・人口 / 文化・メディア / スポーツ / エンタメ

## 記事フォーマット
- Deep Pattern一択（Speed Log廃止済み）
- 詳細: /opt/shared/docs/NEO_INSTRUCTIONS_V2.md
- タクソノミー定義: /opt/shared/scripts/nowpattern_taxonomy.json\"\"\""""

if old_end in content:
    content = content.replace(old_end, taxonomy_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: NEO-ONE system_prompt updated with taxonomy v3.0')
else:
    print('ERROR: Could not find target string')
    # Check if taxonomy already added
    if 'タクソノミー v3.0' in content:
        print('INFO: Taxonomy v3.0 already present in system_prompt')
    else:
        # Show what we have near the end marker
        idx = content.find('マルチモーダル対応')
        if idx >= 0:
            print('DEBUG: Found marker at index', idx)
            print('DEBUG: Context:', repr(content[idx:idx+100]))
