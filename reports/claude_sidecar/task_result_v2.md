# Claude Code Sidecar -- Task Result v2
> Generated: 2026-04-04 | Agent: claude-opus-4-6 | Mission Contract: v3 | Lexicon: v4
> Version: v2 (slug-level precision, UTF-8 clean, implementation-ready)

---

## A. distribution_blocked 262 -- Slug-Level Audit

| Metric | Value |
|--------|-------|
| published_total | 474 |
| distribution_allowed | 212 (44.73%) |
| distribution_blocked | 262 (55.27%) |
| truth_blocked | 0 |
| policy_minimum | 30.0% (currently passing) |

### Category Breakdown

| Category | Count | % of Blocked | Lang-JA | Lang-EN |
|----------|-------|-------------|---------|---------|
| IC-1: WAR_CONFLICT + FINANCIAL_CRISIS | 196 | 74.8% | 45 | 151 |
| IC-2: WAR_CONFLICT only | 59 | 22.5% | 59 | 0 |
| IC-3: FINANCIAL_CRISIS only | 4 | 1.5% | 4 | 0 |
| Other: empty flags | 3 | 1.1% | 3 | 0 |
| **Total** | **262** | **100%** | | |

### Manifest Field Limitation Notice

The following fields are **NOT available** in `reports/article_release_manifest.json`:
- `external_url_count` -- computed in article_release_guard.py but not persisted
- `verified_external_source_count` -- computed but not persisted
- `title` / `html` / `plaintext` -- not included in manifest

IC-1 `estimated_rescue_count` and IC-3 `external_url_count` fallback cannot be precisely quantified from manifest alone. Codex must re-derive from Ghost post data during implementation.

---

### IC-1: Dual-Flag Threshold Relaxation (196 posts)

**Blocking rule**: `article_release_guard.py` L86-89
**Uniform error**: `EDITOR_REVIEW_REQUIRED:WAR_CONFLICT,FINANCIAL_CRISIS`
**Proposed change**: `verified_count >= 2` -> `>= 1`; return `editorial_review_advised`
**Risk**: low | **Estimated impact**: +20pp (44.73% -> ~65%)

#### IC-1 Slug List (196 posts)

<details>
<summary>Click to expand full slug list</summary>

- `24-us-states-tariff-lawsuits-constitutional`
- `attack-on-iranian-energy-facilities-middle-east`
- `australias-middle-east-evacuation-domestic-politics-weaponize-a-repatriation-crisis`
- `bei-zhao-xian-no-zhan-zheng-jing-ji-2zhao-yuan-zhi-cai-ti-zhi-wowu-li-hua-surujun-shi-manenogou-zao-zhuan-huan`
- `between-lines-what-reports-arent-saying`
- `bitcoin-breaks-72k-against-strong-dollar-the-decoupling-signal`
- `bitcoin-decouples-at-72k-digital-gold-thesis-survives-the-strong-dollar`
- `bitcoins-70k-breach-energy-shock-meets-monetary-paralysis`
- `bitcoins-dollar-defiance-crypto-decouples-from-risk-assets`
- `bitcoins-geopolitical-stress-test-oil-shocks-meet-digital-safe-haven`
- `bitcoins-war-premium-safe-haven-narrative-rewrites-the-crisis-playbook`
- `boj-holds-rates-amid-hormuz-crisis`
- `boj-holds-rates-amid-hormuz-crisis-path-dependency-traps-japans-exit-2`
- `boj-keeps-rates-unchanged-amid-hormuz-crisis-ge`
- `bojs-iran-dilemma-when-geopolitical-oil-shocks-collide-with-monetary-normalization`
- `btcgas-p500tojin-nilie-hou-dezitarugorudo-shen-hua-beng-huai-gabao-kuben-dang-nozheng-ti`
- `bundesbank-president-backs-euro-stablecoins-europe-declares-digital-monetary`
- `central-bank-super-week-seven-rate-decisions-collide-with-inflation-shock`
- `concerns-over-prolongation-of-us-iran-military-operations`
- `crude-oil-breaks`
- `crypto-for-the-stateless-when-financial-infrastructure-becomes-geopolitical-refuge`
- `cryptos-f1-gamble-war-exposes-the-fragility-of-gulf-sportswashing-deals`
- `demand-for-dispatch-of-warships-to-the-strait-of-horm`
- `ecb-holds-at-2-for-sixth-straight-meeting-path-dependency-traps-europes-central-bank`
- `ecb-holds-interest-rates-for-sixth-consecutive-time`
- `ecbjin-li-ju-ezhi-ki6lian-sok-enerugiwei-ji-gapo-ruzheng-ce-zhuan-huan-nofen-shui-ling`
- `en-24-states-vs-trump-tariffs-federalism-strikes-back-at-trade-unilateralism`
- `en-australias-16-5b-war-exposure-energy-dependency-meets-geopolitical-contagion`
- `en-bitcoin-breaks-72k-against-strong-dollar-the-decoupling-signal`
- `en-bitcoins-70k-breach-energy-shock-meets-monetary-paralysis`
- `en-bitcoins-dollar-defiance-crypto-decouples-from-equities-in-2026`
- `en-bitcoins-geopolitical-stress-test-oil-shocks-meet-digital-safe-haven-thesis`
- `en-bitcoins-geopolitical-stress-test-oil-shocks-meet-digital-safe-havens`
- `en-boj-holds-rates-amid-hormuz-crisis-path-dependency-traps-japans-exit`
- `en-boj-holds-rates-amid-hormuz-crisis-path-dependency-traps-japans-exit-2-2`
- `en-chinas-alliance-deficit-the-middle-east-war-reveals-a-superpower-without-partners`
- `en-chinas-energy-fortress-strategic-reserves-turn-crisis-into-leverage`
- `en-diego-garcia-strike-exit-signals-iran-tests-reach-as-us-seeks-off-ramp`
- `en-fed-holds-rates-amid-iran-energy-shock-path-dependency-traps-powell`
- `en-fed-holds-rates-steady-twice-middle-east-uncertainty-freezes-monetary-policy`
- `en-feds-iran-war-rate-freeze-when-geopolitics-traps-monetary-policy`
- `en-frbli-xia-gejian-song-rilian-sok-zhong-dong-risukutoinhurezai-ran-gafu-rujin-rong-zheng-ce-nojing-lu-yi-cun`
- `en-gulf-migrant-labor-crisis-when-geopolitics-exposes-the-kafala-systems-moral-hazard`
- `en-hormuz-chokepoint-crushes-south-asia-the-contagion-cascade-of-energy-dependence`
- `en-hormuz-strait-burden-sharing-trumps-naval-ultimatum-strains-allied-order`
- `en-hormuz-strait-crisis-trumps-burden-sharing-gambit-strains-alliances`
- `en-hormuz-strait-crisis-trumps-burden-sharing-ultimatum-reshapes-maritime-security`
- `en-hormuz-strait-ultimatum-trumps-48-hour-threat-triggers-escalation-spiral-with-iran`
- `en-iran-energy-infrastructure-under-fire-the-escalation-spiral-threatening-global-oil-markets`
- `en-iran-strikes-energy-shock-geopolitical-war-premium-returns-to-global-markets`
- `en-iran-war-energy-shock-the-contagion-cascade-toward-global-recession`
- `en-iran-war-oil-shock-the-contagion-cascade-threatening-global-growth`
- `en-iran-war-oil-shock-the-escalation-spiral-threatening-global-growth`
- `en-iran-wars-asian-shockwaves-how-a-gulf-conflict-rewires-indo-pacific-power`
- `en-japan-u-s-defense-talks-on-iran-the-hormuz-chokepoint-reshapes-alliance-dynamics`
- `en-japans-budget-gridlock-coalition-weakness-meets-fiscal-deadline-pressure`
- `en-japans-budget-impasse-coalition-fragility-meets-fiscal-deadline-pressure`
- `en-japans-oda-overhaul-strategic-aid-as-the-new-geopolitical-currency`
- `en-kelloggs-exit-interview-ceasefire-hinges-on-putins-land-calculus`
- `en-koizumi-hegseth-call-on-iran-alliance-coordination-under-strait-pressure`
- `en-koizumi-hegseth-call-on-iran-the-strait-of-hormuz-as-alliance-stress-test`
- `en-new-zealands-fuel-subsidy-when-energy-crises-birth-new-welfare-states`
- `en-new-zealands-fuel-subsidy-when-energy-crises-rewrite-the-social-contract`
- `en-oman-breaks-silence-on-iran-war-imperial-overreach-meets-alliance-strain`
- `en-orbans-eu90bn-veto-how-one-leader-holds-eu-unity-hostage`
- `en-pakistans-solar-leapfrog-when-grid-failure-births-distributed-energy-revolution`
- `en-pakistans-solar-leapfrog-when-grid-failure-sparks-a-decentralized-energy-revolution`
- `en-strait-of-hormuz-crisis-atlantic-alliance-fractures-over-iran-war`
- `en-strait-of-hormuz-crisis-europe-defects-from-us-imperial-overreach`
- `en-strait-of-hormuz-threat-irans-chokepoint-gambit-risks-global-energy-crisis`
- `en-transatlantic-fracture-europe-defies-trump-on-iran-and-redraws-alliance-lines`
- `en-trump-rejects-allied-support-on-iran-imperial-overreach-meets-alliance-fracture`
- `en-trumps-hormuz-ultimatum-alliance-strain-meets-energy-chokepoint-crisis`
- `en-trumps-voter-id-push-meets-congressional-reality-imperial-agenda-strains-alliance-architecture`
- `en-uk-breaks-ranks-on-iran-alliance-strain-exposes-imperial-overreach`
- `en-uk-oil-rationing-playbook-when-war-rewrites-the-rules-of-the-road`
- `en-us-china-paris-trade-talks-rare-earth-leverage-meets-tariff-escalation`
- `en-us-china-paris-trade-talks-rare-earths-as-the-new-leverage-battleground`
- `en-us-eases-iran-oil-sanctions-mid-war-escalation-meets-energy-realpolitik`
- `en-us-india-oil-waiver-sanctions-flexibility-reveals-empires-energy-dilemma`
- `en-us-iran-escalation-spiral-when-total-destruction-claims-meet-defiant-retaliation`
- `en-us-iran-war-exit-pressure-imperial-overreach-meets-internal-dissent`
- `en-us-oil-waiver-for-india-sanctions-flexibility-reveals-imperial-overreach-2`
- `en-us-rolls-back-russia-oil-sanctions-alliance-strain-meets-energy-realpolitik`
- `en-wti-crude-crashes-14-trumps-iran-pause-exposes-oils-geopolitical-fragility`
- `eu-australia-fta-concluded-the-structure-of`
- `eu-middle-east-paralysis-alliance-strain-exposes-europes-strategic-void`
- `eus-mica-crackdown-on-stablecoins-regulatory-capture-reshapes-global-crypto`
- `eus-middle-east-paralysis-alliance-strain-meets-institutional-decay`
- `fed-holds-interest-rates-iran-crisis-structurally-obstructs`
- `fed-holds-off-on-rate-cuts-for-second-consecutive`
- `frb2hui-he-lian-sok-li-xia-gejian-song-ri-zhong-dong-risukutoinhurezai-ran-gamiao-kujin-rong-zheng-ce-nojing-lu-yi-cun`
- `frbjin-li-ju-ezhi-ki-iranwei-ji-gali-xia-gelu-xian-wogou-zao-de-nizu-mudi-zheng-xue-risukunolian-suo`
- `frbli-xia-gedong-jie-noshen-ceng-zhong-dong-risukutoinhurezai-ran-gafu-rujin-rong-zheng-ce-nojing-lu-yi-cun`
- `frbli-xia-gedong-jie-noshen-ceng-zhong-dong-risukutoinhurezai-ran-gamiao-kujin-rong-zheng-ce-nojing-lu-yi-cun`
- `frbli-xia-gejian-song-rilian-sok-zhong-dong-risukutoinhurezai-ran-gafu-rujin-rong-zheng-ce-nojing-lu-yi-cun`
- `frbzheng-ce-jin-li-ju-ezhi-ki-iranwei-ji-gali-xia-gejing-lu-wofeng-zirugou-zao-de-zirenma`
- `gao-shi-shou-xiang-no-cheng-chang-zhan-lue-ximfwai-jiao-ri-ben-jing-ji-zheng-ce-nogou-zao-zhuan-huan-toguo-ji-jiao-she-nojiao-chai-dian`
- `gaza-ping-he-ping-yi-hui-guo-lian-chu-bao-gao-zheng-tong-xing-nakitong-zhi-gasheng-muzhong-dong-zhi-xu-nokong-bai`
- `guan-ce-rogu-0012-rubio-wang-yi-hui-tan-dui-hua-toxie-li-woqiang-hua-toiuyan-xie-noli-de-4yue-nofang-zhong-nixiang-ketadi-narasigajin-mu-guan-shui-tai-wan-ban-dao-ti-donowen-ti-woxian-n`
- `hegseths-hormuz-dismissal-imperial-overreach-meets-energy-reality`
- `hormuz-chokepoint-crushes-south-asia-the-contagion-cascade-of-energy-dependence`
- `hormuz-escalation-spiral-when-oil-chokepoints-become-battlefields`
- `hormuz-strait-attacks-oils-chokepoint-triggers-global-escalation-spiral`
- `hormuz-strait-attacks-the-escalation-spiral-that-reprices-global-energy`
- `hormuz-strait-blockade-imperial-overreach-meets-energy-contagion-cascade`
- `hormuz-strait-ultimatum-trumps-48-hour-threat-triggers-escalation-spiral-with-iran`
- `horumuzuhai-xia-feng-suo-nochang-qi-hua-quan-li-noguo-shen-zhan-gazhao-kuenerugizhi-xu-nobeng-huai`
- `horumuzuhai-xia-henojian-chuan-pai-qian-yao-qiu-ri-mi-tong-meng-no-dui-jia-gazhong-dong-nikuo-zhang-sarerugou-zao-zhuan-huan`
- `horumuzuhai-xia-jian-chuan-pai-qian-wen-ti-tong-meng-nogui-lie-gabao-kuenerugian-bao-nogou-zao-de-cui-ruo-xing`
- `horumuzuhai-xia-wei-ji-totoranpuno-fu-dan-gong-you-ya-li-tong-meng-gui-lie-gazi-yuan-wei-ji-wozeng-fu-surugou-zao`
- `iea-oil-reserve-release-energy-shock-doctrine-reshapes-crypto-corridors`
- `ieas-record-oil-release-strategic-reserves-as-geopolitical-currency`
- `ieas-record-oil-reserve-release-energy-crisis-meets-crypto-safe-haven`
- `imf-warns-on-middle-east-crisis-energy-shock-threatens-global-recovery`
- `iran-energy-infrastructure-under-fire-the-escalation-spiral-threatening-global-oil-markets`
- `iran-overreach-trap-how-us-middle-east-escalation-hands-china-a-strategic-gift`
- `iran-strikes-energy-shock-geopolitical-war-premium-returns-to-global-markets`
- `iran-strikes-taiwan-drift-how-us-overreach-hands-china-a-strategic-opening`
- `iran-strikes-trigger-australias-energy-deja-vu-the-contagion-cascade-returns`
- `iran-war-exit-pressure-imperial-overreach-meets-internal-dissent`
- `iran-war-oil-shock-americas-sanctions-dilemma-reveals-the-limits-of-maximum`
- `iran-war-ripples-through-asia-energy-shock-exposes-alliance-fragility`
- `iran-war-stockpile-crisis-imperial-overreach-meets-logistical-reality`
- `iran-wars-asian-shockwaves-how-a-gulf-conflict-rewires-indo-pacific-power`
- `israels-successor-hunt-decapitation-strategy-meets-imperial-overreach`
- `japan-us-defense-chiefs-discuss-iran-crisis`
- `japans-iran-diplomacy-gambit-energy-dependence-meets-alliance-strain`
- `kelloggs-exit-interview-ceasefire-hinges-on-putins-land-calculus`
- `kharg-island-strikes-the-escalation-spiral-that-rewrites-the-oil-order`
- `largest-sewage-spill-in-us-history-the-federal-government-owns-the-facility-its`
- `mi-iranjun-shi-chong-tu-nochang-qi-hua-tozheng-quan-nei-che-tui-lun-quan-li-noguo-shen-zhan-gazhao-kuzhong-dong-zhi-xu-nogou-zao-zhuan-huan`
- `mi-iranzhan-zheng-nochu-kou-nakimi-lu-toranpuzheng-quan-nei-bu-nizou-ru-quan-li-noguo-shen-zhan-nogui-lie`
- `mi-rodian-hua-hui-tan-toiranqing-shi-da-guo-jian-xie-diao-noli-niqian-muzhong-dong-zhi-xu-zai-bian-nogou-zao-li-xue`
- `new-zealands-fuel-subsidy-when-energy-crises-birth-new-welfare-states`
- `oil-vs-ai-how-middle-east-war-threatens-the-data-center-boom`
- `oman-breaks-silence-on-iran-war-imperial-overreach-meets-alliance-strain`
- `orbans-eu90bn-veto-how-one-leader-holds-eu-unity-hostage`
- `pakistans-solar-leapfrog-when-grid-failure-births-distributed-energy-revolution`
- `prime-minister-takaichis-growth-strategy-x-imf`
- `protraction-of-the-strait-of-hormuz-blockade`
- `putins-iran-nuclear-mediation-proposal-the-structure-of`
- `qantas-fare-hikes-when-war-reprices-the-cost-of-distance`
- `ri-yin-horumuzuwei-ji-xia-dejin-li-ju-ezhi-ki-di-zheng-xue-risukugajin-rong-zheng-ce-woren-zhi-niqu-rugou-zao`
- `ri-yin-horumuzuwei-ji-xia-dejin-li-ju-ezhi-ki-di-zheng-xue-risukugajin-rong-zheng-chang-hua-wodong-jie-surugou-zao`
- `ri-yin-ju-ezhi-kitohorumuzuwei-ji-di-zheng-xue-risukugajin-rong-zheng-chang-hua-wodong-jie-surugou-zao`
- `russias-oil-windfall-how-middle-east-war-fuels-moscows-war-machine`
- `russias-petro-lifeline-how-middle-east-war-rescues-a-flagging-war-machine`
- `russias-petrodollar-lifeline-how-middle-east-chaos-rescues-a-failing-war-economy`
- `russias-wartime-windfall-how-middle-east-chaos-funds-moscows-war-machine`
- `seven-central-banks-vs-inflation-bitcoins-macro-crucible-week`
- `seven-central-banks-vs-inflation-bitcoins-monetary-policy-stress-test`
- `strait-of-hormuz-crisis-and-trumps`
- `strait-of-hormuz-crisis-and-trumps-3`
- `strait-of-hormuz-crisis-europe-defects-from-us-imperial-overreach`
- `strait-of-hormuz-defense-and-alliance-fiss`
- `strait-of-hormuz-mining-the-escalation-spiral-that-threatens-global-oil`
- `strait-of-hormuz-naval-deployment-issue-alliance-cr`
- `strait-of-hormuz-the-escalation-spiral-that-threatens-global-energy`
- `structure-seen-through-data-6`
- `takaichis-growth-strategy-pivot-japans-sunday-power-play-signals-imf-alignment`
- `takaichis-sunday-agenda-japans-growth-strategy-meets-imf-scrutiny`
- `the-deeper-meaning-behind-the-feds-rate-cut-freeze`
- `the-exitless-maze-of-the-us-iran`
- `the-strait-of-hormuz-crisis-and-trumps-bur`
- `toranpu-cai-pan-suo-nidui-chu-suru-fa-yan-zui-gao-cai-guan-shui-wei-xian-pan-jue-gayao-rasusan-quan-nojun-heng`
- `toranpufang-zhong-hou-notai-wan-wu-qi-mai-que-mi-zhong-qu-yin-wai-jiao-gabao-kutong-meng-nocui-ruo-xing`
- `toranpugatong-shang-fa-di-122tiao-de10-dai-ti-guan-shui-150ri-noshi-xi`
- `toranpuguan-shui-zui-gao-cai-bai-bei-demotu-kijin-mu-xuan-yan-150ri-no`
- `toranpunoirandan-du-gong-ji-xuan-yan-tong-meng-ti-zhi-wogen-di-karayao-rugasu-quan-li-noguo-shen-zhan`
- `trump-advisors-push-exit-plan-imperial-overreach-meets-escalation-spiral-in-iran-war`
- `trump-advisors-push-for-iran-war-exit-imperial-overreach-meets-domestic-dissent`
- `trump-signals-massive-iran-strike-the-escalation-spiral-that-reshapes-the-middle-east`
- `trump-vs`
- `trumps-declaration-of-unilateral-attack-on-iran`
- `trumps-iran-endgame-imperial-overreach-meets-economic-blowback`
- `trumps-iran-gambit-how-middle-east-overreach-hands-china-its-taiwan-window`
- `uk-energy-bills-hit-by-iran-war-the-anatomy-of-a-political-price-trap`
- `uk-energy-bills-iran-war-the-geopolitical-tax-households-cannot-escape`
- `uk-fuel-price-crackdown-when-geopolitical-shocks-meet-domestic-political-theater`
- `uk-fuel-price-crackdown-when-geopolitical-shocks-meet-domestic-political-theatre`
- `uk-mortgage-shock-how-iran-war-risk-is-repricing-british-household-debt`
- `ukraine-ceasefire-negotiations-the-structural-stalemate`
- `us-china-paris-trade-talks-tariffs`
- `us-china-paris-trade-talks-tariffs-and-rare-earth`
- `us-india-oil-waiver-sanctions-pragmatism-meets-energy-realpolitik`
- `us-iran-military-conflict-destruction-complete`
- `us-iran-nuclear-talks-stall-in-oman-the-escalation-spiral-nobody-can-exit`
- `us-iran-war-exit-strategy-demanded-regime-cracks`
- `us-israel-strike-iran-the-escalation-spiral-that-reshapes-the-middle-east-order`
- `us-israel-strike-on-iran-international-laws-legitimacy-crisis-deepens`
- `us-sinks-iranian-warship-the-escalation-spiral-nobody-can-stop`
- `war-powers-revolt-congress-challenges-executive-military-authority-on-iran`
- `weaponisation-of-everything-how-trumps-return-rewrites-global-economic-rules`
- `zhong-dong-wei-ji-toenerugijia-ge-gao-teng-shi-jie-jing-ji-woshi-mu-dui-li-noluo-xuan-to-chuan-ran-nolian-suo`
- `zui-gao-cai-guan-shui-pan-jue-debtcyi-shi-6-8mo-dorufan-fa-shu-fen-dexiao-etashang-sheng-gabao-ku-dezitarugorudo-noxu-toben-dang`

</details>

#### IC-1 Tag Frequency (top 15)

| Tag | Count |
|-----|-------|
| deep-pattern | 196 |
| nowpattern | 196 |
| lang-en | 151 |
| genre-geopolitics | 144 |
| event-military | 115 |
| event-resource | 112 |
| p-escalation | 107 |
| genre-energy | 100 |
| p-path-dependency | 100 |
| p-overreach | 91 |
| p-alliance-strain | 74 |
| p-contagion | 66 |
| genre-economy | 52 |
| event-market | 47 |
| lang-ja | 45 |

---

### IC-2: WAR_CONFLICT-Only Single-Flag (59 posts)

**Blocking rule**: `article_release_guard.py` L90-91
**All lang-ja** (0 lang-en)
**Option A**: Narrow WAR_CONFLICT regex to compound phrases (risk: medium)
**Option B**: Add `external_url_count >= 2` fallback (risk: low)

#### Trigger Term Analysis

- Method: slug text keyword matching + tag_slugs inference (title not available in manifest)
- Slugs with English keyword hit: 3
- Slugs without keyword hit (tag-inferred): 56
- **Inference**: Most IC-2 posts are flagged via tag_slugs matching (event-military, genre-geopolitics) or JA-text regex (Japanese war terms in HTML), not English slug keywords

#### IC-2 Slug Table (59 posts)

| # | Slug | Trigger Source | Suspected Triggers |
|---|------|---------------|-------------------|
| 1 | `bei-zhao-xian-nozhan-zheng-jing-ji-2zhao-yuan-zhi-cai-ti-zhi` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 2 | `bei-zhao-xian-xin-xing-misairuri-ben-shang-kong-tong-guo-dui` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 3 | `denmakuzong-xuan-ju-nochong-ji-gurinrandofang-wei-gazhao-ita` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 4 | `du-wa-nodu-tokuremurin-nawarinuian-sha-nohua-xue-de-zheng-mi` | slug_keyword | war |
| 5 | `eu-vs-mi-guo-tetukuzhan-zheng-dmagayin-kiqi-kosugui-zhi-nodi` | tag_match_inference | (none detected) |
| 6 | `euhao-zhou-ftatuo-jie-toranpuguan-shui-gajia-su-saseta-tuo-m` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 7 | `gao-shi-fang-mi-ri-mi-shou-noy-hui-tan-tong-meng-no-dui-jia-` | slug_keyword | war |
| 8 | `gao-shi-fang-mi-tori-mi-shou-noy-hui-tan-tong-meng-zai-bian-` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 9 | `gao-shi-shou-xiang-cun-li-wei-ji-shi-tai-da-bian-mi-qing-bao` | tag_match_inference | event-alliance, genre-geopolitics, p-escalation |
| 10 | `gao-shi-shou-xiang-cun-li-wei-ji-shi-tai-da-bian-ri-mi-tong-` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 11 | `gao-shi-shou-xiang-no-5shi-jian-wai-jiao-teiruuaemerutugayin` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 12 | `gao-shi-shou-xiang-no-ji-shu-zhu-quan-wai-jiao-paranteiauaed` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 13 | `gao-shi-shou-xiang-no-ji-shu-zi-yuan-wai-jiao-ji-zhong-ri-ri` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 14 | `gao-shi-toranpushou-noy-hui-tan-ri-mi-tong-meng-nozai-ding-y` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 15 | `gao-shi-toranpushou-noy-hui-tan-tong-meng-nozai-jiao-she-toi` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 16 | `gaza-ping-he-ping-yi-hui-guo-lian-chu-bao-gao-zheng-tong-xin` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 17 | `hormuz-kaikyo-kiki-beikoku-iran-tairitsu` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 18 | `horumuzuhai-xia-fang-wei-totong-meng-nogui-lie-mi-guo-no-fu-` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 19 | `horumuzuhai-xia-jian-chuan-pai-qian-wen-ti-tong-meng-nogui-l` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 20 | `horumuzuhai-xia-wei-ji-mi-iran-dui-li-noluo-xuan-gaenerugizh` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 21 | `horumuzuhai-xia-wei-ji-mi-iran-dui-li-noluo-xuan-gazhong-don` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 22 | `horumuzuhai-xia-wei-ji-totoranpuno-fu-dan-gong-you-ya-li-ton` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 23 | `horumuzuno3shi-jian-shi-jie-noshi-you-20-gazhi-matutari` | tag_match_inference | event-military, p-escalation |
| 24 | `iranbao-fu-neng-li-da-fu-di-xia-fa-yan-mi-yuan-gao-guan-gami` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 25 | `iranenerugishi-she-gong-ji-zhong-dong-dui-li-noluo-xuan-gash` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 26 | `kerotugute-shi-tui-ren-toukurainating-zhan-putinno-guo-shen-` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 27 | `mi-24zhou-noguan-shui-su-song-da-tong-ling-quan-xian-noguo-s` | tag_match_inference | p-overreach |
| 28 | `mi-iranjun-shi-chong-tu-po-huai-wan-liao-xuan-yan-tobao-fu-n` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 29 | `mi-iranjun-shi-zuo-zhan-nochang-qi-hua-xuan-nian-quan-li-nog` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 30 | `mi-jun-nozhong-dong-bei-hai-risuku-toranpuno-che-tui-kakuo-d` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 31 | `mi-rodian-hua-hui-tan-toiranbao-wei-wang-da-guo-jian-qu-yin-` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 32 | `mi-ying-tong-meng-nogui-lie-toranpunoiranzuo-zhan-ganatojie-` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 33 | `mi-zhong-parimao-yi-xie-yi-guan-shui-toreaasugaying-suba-qua` | tag_match_inference | genre-geopolitics, p-escalation, p-overreach |
| 34 | `mi-zhong-parimao-yi-xie-yi-guan-shui-toreaasugaying-suba-qua` | tag_match_inference | genre-geopolitics, p-escalation, p-overreach |
| 35 | `nan-sinahai-hui-se-nochong-tu-mi-zhong-gahu-initui-kenaidui-` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 36 | `odashi-shi-ti-zhi-gai-ge-jing-ji-an-bao-shi-dai-noyuan-zhu-w` | tag_match_inference | genre-geopolitics |
| 37 | `odashi-shi-ti-zhi-gai-ge-jing-ji-an-quan-bao-zhang-shi-dai-n` | tag_match_inference | genre-geopolitics |
| 38 | `ou-mi-tong-meng-nogui-lie-rosiagashi-gua-keru-fen-duan-noqin` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 39 | `putinnoiranhe-zhong-jie-ti-an-xie-diao-noshi-bai-gasheng-muh` | tag_match_inference | event-alliance, genre-geopolitics, p-escalation |
| 40 | `ri-ben-no-zi-zhu-fang-wei-fa-an-zhan-hou-80nian-noan-quan-ba` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 41 | `ri-ben-nohorumuzuhai-xia-jian-chuan-pai-qian-tong-meng-nogui` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 42 | `ri-ben-nohorumuzuhai-xia-pai-qian-wen-ti-tong-meng-nodai-jia` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 43 | `ri-ben-noyu-suan-shen-yi-jiao-zhao-shao-shu-yu-dang-galu-che` | tag_match_inference | p-escalation |
| 44 | `ri-ben-noyu-suan-shen-yi-jiao-zhao-shao-shu-yu-dang-shi-dai-` | tag_match_inference | p-alliance-strain |
| 45 | `ri-mi-fang-wei-dian-hua-hui-tan-horumuzuhai-xia-wei-ji-gazhi` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 46 | `ri-mi-fang-wei-shou-noy-noiranwei-ji-xie-yi-horumuzuhai-xia-` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 47 | `ri-mi-fang-wei-xie-yi-toiranwei-ji-horumuzuhai-xia-womegurut` | tag_match_inference | event-alliance, event-military, genre-geopolitics |
| 48 | `ri-mi-shou-noy-hui-tan-2026nian-3yue-guan-shui-ya-li-xia-not` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 49 | `ri-mi-shou-noy-hui-tan-toiranwen-ti-tong-meng-no-dui-jia-gaw` | slug_keyword | war |
| 50 | `ri-mi-shou-noy-hui-tan-toiranwen-ti-tong-meng-no-zhong-cheng` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 51 | `rosia-iranjun-shi-lian-xi-noshen-hua-zerensukigabao-ku-er-zh` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 52 | `rosianohe-wei-xia-tori-ben-noan-bao-zhuan-huan-dui-li-noluo-` | tag_match_inference | event-military, genre-geopolitics, p-alliance-strain |
| 53 | `toranpu-orubanlian-dai-fei-riberarutong-meng-gayao-rugasueun` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 54 | `toranpu-orubanlian-dai-quan-wei-zhu-yi-netutowakugaeumin-zhu` | tag_match_inference | event-alliance, genre-geopolitics, p-alliance-strain |
| 55 | `toranpuno-he-kayuan-you-ka-er-ze-xuan-yan-enerugiba-quan-toz` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 56 | `ukurainating-zhan-jiao-she-putinno-quan-li-noguo-shen-zhan-g` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 57 | `wtiyuan-you-14-ji-luo-toranpunoirangong-ji-yan-qi-gabao-kuzh` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 58 | `yuan-you-90dorutu-po-horumuzuhai-xia-feng-suo-risukugashi-ji` | tag_match_inference | event-military, genre-geopolitics, p-escalation |
| 59 | `ziyunebuno6shi-jian-4nian-mu-nozhan-zheng-ga-jiao-she-woshi-` | tag_match_inference | event-alliance, event-military, p-escalation |

#### IC-2 Tag Frequency (top 10)

| Tag | Count |
|-----|-------|
| deep-pattern | 59 |
| lang-ja | 59 |
| nowpattern | 59 |
| genre-geopolitics | 52 |
| p-escalation | 38 |
| p-alliance-strain | 34 |
| event-military | 29 |
| event-alliance | 29 |
| p-overreach | 29 |
| p-path-dependency | 25 |

---

### IC-3: FINANCIAL_CRISIS-Only (4 posts)

**Blocking rule**: `article_release_guard.py` L90-91
**All lang-ja, all crypto-tagged**
**Proposed change**: `external_url_count >= 2` fallback
**Risk**: low

| # | Slug | Tags (non-standard) |
|---|------|-------------------|
| 1 | `gong-kai-qi-ye-btcbao-you-200mo-mei-tu-po-bu-ke-ni-nozhi-du-` | crypto, event-structural, finance, p-path-dependency |
| 2 | `guan-ce-rogu-fen-san-xing-qu-yin-suo-haiparikitudo-defiwoxun` | crypto, event-regulation, governance, p-capture |
| 3 | `suteburukoinshi-jia-zong-e-3000yi-dorutu-po-an-hao-zi-chan-n` | crypto, event-structural, p-contagion, p-path-dependency |
| 4 | `toranpujia-zu-noan-hao-zi-chan-samituto-gorudomanceokaranitu` | crypto, event-regulation, finance, p-capture |

---

### Other: Empty Risk Flags (3 posts)

These posts have `risk_flags: []` but `release_errors: ["EDITOR_REVIEW_REQUIRED:"]`. Edge case.

| # | Slug | Release Error |
|---|------|--------------|
| 1 | `fed-fomc-march-2026-rate-decision` | `EDITOR_REVIEW_REQUIRED:` |
| 2 | `gao-shi-shou-xiang-no-cheng-chang-zhan-lue-ri-yao-hui-he-jin` | `EDITOR_REVIEW_REQUIRED:` |
| 3 | `ri-ben-noyu-suan-zheng-zhi-zan-ding-yu-suan-fu-shang-gaying-` | `EDITOR_REVIEW_REQUIRED:` |

**Codex note**: Add guard in classify_release_lane -- if `not risk_flags`, skip `EDITOR_REVIEW_REQUIRED` injection.

---

## B. Mojibake Audit

**Scope**: All .py and .md files under scripts/, .claude/rules/, docs/, reports/claude_sidecar/
**Method**: grep for known Shift_JIS-to-UTF-8 double-encoding artifacts (hex: e7b8ba, e7b9a7, e89bbb, e8ae80e68786, e88ea0e59f9fe383b8e383ac)

### Source Files (6 audited)

| File | Result |
|------|--------|
| `scripts/canonical_public_lexicon.py` | CLEAN |
| `scripts/public_lexicon.py` | CLEAN |
| `scripts/product_lexicon.py` | CLEAN |
| `scripts/mission_contract.py` | CLEAN |
| `scripts/agent_bootstrap_context.py` | CLEAN |
| `scripts/lexicon_contract_audit.py` | CLEAN |

**Result**: ZERO mojibake findings in all 6 source files

### v1 Output Findings (2 files had mojibake)

| File | Line | Field | Issue |
|------|------|-------|-------|
| `reports/claude_sidecar/task_result.json` | 88 | mojibake_check_method | Raw mojibake marker chars embedded in JSON output value |
| `reports/claude_sidecar/task_result.md` | 96 | mojibake audit method description | Same raw marker chars in markdown text |

**v2 mitigation**: All marker references use ASCII hex codes or English descriptions. No raw CJK mojibake characters in this file.

---

## C. Vocabulary Drift Findings

### VD-1: identity hierarchy (info)

- **Finding**: Some docs use Nowpattern as OS name. Canonical: NAOTO OS = OS, Nowpattern = platform
- **Guard**: PROJECT_DRIFT_GUARD in mistake_patterns.json

### VD-2: Brier Score notation (info)

- **Finding**: Three Brier averages coexist: 0.1780/0.1828/0.4759. Canonical: binary n=53 avg=0.4759
- **Guard**: M006 in mistake_registry.json

### VD-3: PVQE V definition (info)

- **Finding**: mission_contract.py V=value_density vs NORTH_STAR.md V=improvement_speed. Canonical: mission_contract.py v3 is authoritative
- **Affected files**: .claude/rules/NORTH_STAR.md, .claude/rules/OPERATING_PRINCIPLES.md

---

## D. Codex Handoff (Priority Order)

| ID | File | Line | Priority | Risk | Estimated Impact |
|----|------|------|----------|------|-----------------|
| IC-1 | `scripts/article_release_guard.py` | 87 | high | low | +20pp (44.73% -> ~65%) |
| IC-3 | `scripts/article_release_guard.py` | 90-91 | medium | low | +1-2pp |
| IC-2 | `scripts/article_release_guard.py` | 45-52 | medium | medium | +5-10pp (regex-dependent) |
| OTHER-FIX | `scripts/article_release_guard.py` | L224-226 | low | low | +0.6pp (3 posts) |
| VD-3 | `.claude/rules/NORTH_STAR.md` | - | low | low | docs only |

### Cumulative Effect Projection

```
Current:                44.73%
After IC-1:             ~65%
After IC-1 + IC-3:      ~67%
After IC-1 + IC-2 + IC-3 + OTHER: ~75-80%
```

### Do Not Touch

- `data/prediction_db.json`
- `scripts/one_pass_completion_gate.py`
- `scripts/build_article_release_manifest.py (production runs only)`

### Verification Commands

```bash
# After IC-1/IC-2/IC-3 changes:
python3 /opt/shared/scripts/build_article_release_manifest.py
python3 /opt/shared/scripts/article_release_guard.py --report
# Verify: distribution_allowed_ratio_pct >= 65%
# Verify: truth_blocked == 0

# After VD-3 docs fix:
python3 /opt/shared/scripts/lexicon_contract_audit.py
```

---

## Completion Conditions

| Condition | Status |
|-----------|--------|
| blocked_rows_at_slug_granularity | PASS |
| mojibake_findings_with_file_line | PASS |
| utf8_clean_output | PASS |
| ic1_ic2_ic3_per_post_mapping | PASS |
| manifest_field_limitations_documented | PASS |

---

*End of sidecar task result v2. Machine-readable: `task_result_v2.json`*
