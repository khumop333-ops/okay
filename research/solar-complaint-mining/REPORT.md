# Solar owners in South Africa: complaint mining

*Ranked pain points with demand evidence. Data as of 2026-10-02. Evidence fetched 2026-10-02. This is a list of what people complain about, not a list of things to build; no solutions are proposed.*

## 1. The ranked list (top 10)

Ranking basis: **extended** window (2024-10-02 to 2026-10-02); 59 owner/prospective evidence rows from 20 distinct sources (threads/pages/app listings). Only first-hand voices count; installers/sellers and bystander opinion are logged separately ({'bystander': 7, 'trade': 1}). **Counts are sample counts of complaint items, not prevalence among owners.**

| # | Pain | Items (sources) | Who (C1/C2/C3) | In last 12 mo | Would pay? | Existing fix solves it? |
|---|---|---|---|---|---|---|
| 1 | Brand/distributor warranty repair drags on for months with no answers | 17 (6) ⚑ | 14/3/0 | 100% | UNVERIFIED | No (on this evidence) |
| 2 | Monitoring app/portal is unreliable or too complex (concentrated on one vendor app) | 12 (3) ⚑ | 9/3/0 | 100% | Workaround spend only (enthusiasts) | Partly (technical owners only) |
| 3 | Installer stops answering after payment | 9 (5) | 6/0/3 | 78% | UNVERIFIED | Unclear |
| 4 | Rent-to-own / subscription terms: price, escalation, buy-out and exit fees | 8 (5) | 1/0/7 | 50% | Stated spend (payments, exit fee) | Partly / unclear |
| 5 | Inverter faults that recur after repair | 5 (4) | 5/0/0 | 100% | UNVERIFIED | No (on this evidence) |
| 6 | Batteries that swell, lose BMS communication or fail early | 4 (3) ⚑ | 3/1/0 | 75% | UNVERIFIED | No (on this evidence) |
| 7 | Owners do not see the bill fall | 4 (3) ⚑ | 3/0/1 | 100% | UNVERIFIED | Unclear |
| 8 | Installation defects with safety consequences | 4 (3) ⚑ | 1/0/3 | 75% | UNVERIFIED | Unclear |
| 9 | Grid-registration (SSEG) is seen as costly, pointless or unenforced | 4 (2) ⚑ | 3/1/0 | 100% | Unwilling (self-selected poll) | Not on this evidence |
| 10 | Buyers cannot tell which installer or finance provider to trust | 3 (2) ⚑ | 1/0/2 | 100% | UNVERIFIED | Unclear |

⚑ = one source supplies more than 40% of the items (see section 5). C1 = homeowners with installer-installed systems; C2 = DIY and enthusiast owners; C3 = rent-to-own / financed / subscription customers.

**Reading it in one paragraph.** After-sales is the dominant theme: warranty repair, an unresponsive installer, repeat call-outs, replacement units and refused claims together touch 27 of the 59 counted rows (post-hoc cluster of distinct rows; other clusters: equipment faults 12, monitoring and alerts 12, financing and provider trust 10, install quality and verification 10, savings and billing 7, regulation and registration 4). Monitoring-app complaints rank second as a single tag but come almost entirely from one vendor app's reviews. Rent-to-own terms and exit fees are almost all C3. Grid registration (SSEG) is a live grievance voiced in forum threads, not in reviews. For willingness to pay, the honest answer for most pains is **UNVERIFIED**: people state what they already paid or were charged, rarely what they would pay to make the problem stop.

### Top pains inside each community (owner/prospective items)

| Community | Counted rows | Most frequent pains (items) |
|---|---|---|
| C1 | 38 | `warranty_repair_delay_runaround` (14); `monitoring_app_issues` (9); `installer_aftersales_unresponsive` (6); `inverter_fault_recurring` (5); `savings_below_expectation` (3) |
| C2 | 9 | `warranty_repair_delay_runaround` (3); `monitoring_app_issues` (3); `inverter_battery_compat_config` (2); `warranty_verification_serial` (1); `battery_failure_degradation` (1) |
| C3 | 12 | `financing_rent_to_own_terms` (7); `workmanship_defects` (3); `installer_aftersales_unresponsive` (3); `installer_trust_scam_fear` (2); `installation_delays_lead_time` (1) |

## 2. How this was done (and where it falls short)

**Niche:** people with solar installations in South Africa (your answer to the niche question; the brief's niche was an unfilled placeholder). **Access:** your answer to the access question was '.', so I used the stated default: use reachable sources, report real coverage, never pad. That assumption is mine.

**Three communities** (audience segments assigned from the author's own role cues, not by venue; when a post gave no cue it defaulted to C1):

| | Community | Why this one |
|---|---|---|
| C1 | Homeowners with installer-installed systems | The largest group; their complaints surface in reviews and Reddit. |
| C2 | DIY, self-install and enthusiast owners | Distinct vocabulary (firmware, BMS, apps, registration avoidance); active on forums. |
| C3 | Rent-to-own / financed / subscription customers | A distinct buyer with different complaints (buy-out, escalation, exit fees); heavily discussed in 2026. |

**Tested and rejected:** *small businesses/farms* (3 searches; no usable owner complaints, only installer marketing and pre-2025 homeowner threads) and *body-corporate/estate residents* (5 SA Reddit threads, all before the window, one about solar). C3 replaced the originally planned small-business/farm community after those tests; the swap was made during collection, not in advance.

**Window rule (fixed before tallying):** strict = last 12 months (2025-10-02 onward). If any community has fewer than 30 scanned items in the strict window, every community is ranked on the 24-month window and each pain's strict share is shown. Strict-window scanned items were C1 73, C2 17, C3 59, so **the 24-month window applies** (C2 reaches 35 only on 24 months). Older items were excluded.

**Counting rules (fixed before tallying):** owner/prospective voices only; rank by item count, tie-break on distinct sources, then community spread; flag a pain when one source supplies more than 40% of its items. A row can carry several tags and counts once per tag. `tools/complaint_tally.py` implements this with unit tests. **Added after seeing counts:** the theme clusters (interpretation only, never used for ranking). **Added before the first tally:** an equal-community-weight score, to show whether the big community drives the order.

### Coverage: items actually read, by community and source (window used)

| Community | Reddit | Forums | Review sites | App reviews | Facebook | X | Product reviews | Total read | Strict-window read |
|---|---|---|---|---|---|---|---|---|---|
| C1 | 22 | 14 | 29 | 8 | 0 | 0 | 0 | 73 | 73 |
| C2 | 0 | 31 | 3 | 1 | 0 | 0 | 0 | 35 | 17 |
| C3 | 29 | 25 | 11 | 0 | 0 | 0 | 0 | 65 | 59 |

**Gaps against what you asked for:**

- **Public Facebook groups: 0 items.** 4 searches; facebook.com returns 403 and search surfaces no usable public SA posts. A 2024 forum post confirms an active 'Sunsynk Users & Installers' group exists, but it is not publicly readable here.
- **Twitter/X: 0 items.** x.com returns 403; 4 searches returned organisation accounts and articles only; the one X mirror tried (XCancel) is suspended. Two user replies under an Eskom post were questions, not complaints.
- **Product reviews: only app-store reviews.** One app (Sunsynk Connect, Apple App Store, South African storefront, newest 9 reviews). Takealot (2 attempts: a search and a product-page fetch) shows a rating but no review text; Google Play ratings are global and cannot be verified as South African, so they are not counted.
- **Reddit and forums** were read through a public Reddit mirror and MyBroadband/PowerForum pages; many threads were read only in their first chunk, so quiet comments deeper in long threads were not seen.
- **Scan size:** the brief asked for 30-50 items per community. C1 (73) and C3 (65) exceed 50 because items are counted from whole threads/pages once opened; C2 reached 35 and only on the 24-month window.

## 3. The top 10, one by one

### 1. Brand/distributor warranty repair drags on for months with no answers

`warranty_repair_delay_runaround` | **17 items from 6 sources** | communities {'C1': 14, 'C2': 3} | sources {'review_site': 16, 'app_review': 1} | 100% in the last 12 months | equal-weight rank 1 | ⚑ 41% from `hp:sunsynk`

- **What the pain is.** After an inverter or battery fails under warranty, the brand or distributor repair/replacement stretches to months: parts are 'awaited', job numbers cannot be traced, emails and WhatsApps go unanswered, and claims are handed between installer, distributor and brand. Examples: a swollen battery with no replacement after 7 months (E015); a unit not heard about for almost 3 months (E016); three failed repairs in five months (E014); a 10-year-warranty system defective in year 3 with no acknowledgement even after escalation to the global CEO (E019).
- **Who is complaining.** Installer-installed homeowners (C1) and hands-on/enthusiast owners (C2). Brands named: Sunsynk (most), Deye, Pylontech; installers named: Solar Advice, NCSP. 16 of the items are Hello Peter reviews, one is an app review; all are inside the last 12 months.
- **What they do about it now.** Owners route everything through their installer, who chases the brand; accept an installer-supplied loan unit where one exists (E014); escalate to senior staff or the CEO (E015, E019); and post public reviews. One owner was told testing an in-warranty inverter would cost labour and could leave them on Eskom power for up to 21 days (E040).
- **What they would pay to make it stop.** UNVERIFIED: no row states what an owner would pay for faster repair. Observed spend is being charged, not offering to pay: a labour quote of R6,000 to test an in-warranty inverter plus about R2,000 for a WiFi-controller job (E040, quoted_price) and repeated installer call-out fees with no amount stated (E014).
- **Does an existing product or service already solve it well?** No on this evidence. A legal right and an ombud exist, but 16 Hello Peter reviews from the last 12 months describe the same months-long pattern; Hello Peter shows Sunsynk NPS -67 (14-15 reviews; page fetched), Deye -100 (8) and Pylontech -100 (5) (the last two from search excerpts of their pages).
  - [Consumer Protection Act s56 (six-month right to repair/replace/refund at the consumer's election, supplier's risk and expense)](https://thencc.org.za/wp-content/uploads/2023/11/Explanatory-Note-7-of-2023.pdf) - fetched 2026-10-02: National Consumer Commission note quotes s56(2). It covers only the first six months after delivery; later failures rest on the manufacturer's contractual warranty.
  - [Consumer Goods and Services Ombud (free escalation after a supplier complaint)](https://www.cgso.org.za/) - fetched 2026-10-02: Whether a given solar supplier is a registered participant is UNVERIFIED; only one counted row (E044) reports using it, and no outcome is reported.
  - [Solar Deity 'Pylontech Official Repair Center' (claims under-7-day turnaround and a loan battery)](https://solardeity.co.za/pylontech-servicesupport/) - fetched 2026-10-02: Vendor claims only; unverified. Hello Peter 'Pylontech' reviews (E047-E050) describe a claim open for more than six months (E048), a month-plus wait for stock (E050) and rejections for 'misuse' (E047, E049), via a different local agent.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E014 (C1, owner, 2026-08-24, [Hello Peter: Sunsynk](https://www.hellopeter.com/sunsynk/reviews/sunsynk-worst-company-service-6556639)): "Over the past 5 months, I have endured 3 failed repair attempts, multiple installer call-out fees, countless follow-ups, and still no resolution from Sunsynk."
  - E019 (C1, owner, 2026-07-14, [Hello Peter: Deye (Ningbo Deye)](https://www.hellopeter.com/deye-inverters)): "I'm sitting with a terribly defective 10-year warranty solar system which is only in its 3rd year of the warranty! I've reported the defect to their Midrand office, their Africa marketing manager and finally to their global CEO - all to no avail!"
  - E022 (C1, owner, last-12-months label, [Hello Peter: NCSP Solar Energy](https://www.hellopeter.com/ncsp-solar-energy)): "It has now been sent away for repairs four times... the company we bought the system from is not answering our calls or WhatsApp messages. We are still paying for the solar system while also having to purchase electricity when the system is not operating properly."

### 2. Monitoring app/portal is unreliable or too complex (concentrated on one vendor app)

`monitoring_app_issues` | **12 items from 3 sources** | communities {'C1': 9, 'C2': 3} | sources {'review_site': 2, 'forum': 1, 'app_review': 9} | 100% in the last 12 months | equal-weight rank 3 | ⚑ 75% from `app:sunsynk-connect-ios-za`

- **What the pain is.** The inverter vendor's monitoring app is unreliable or hard to use: 'service error' screens, previous days' numbers gone after an update (E066), sign-in broken after updates in July 2026 (E061, E063), grid-outage notifications not working for 'more than a month' (E065), an electrical engineer calling it 'incredibly complex' (E054), and a WiFi dongle that stopped in week one (E055). One enthusiast did not notice for three weeks that their batteries never reached 100% (E056). An undated review on the same ZA listing (not counted) adds 'service error' screens and daily statistics resetting to 0.
- **Who is complaining.** Sunsynk owners. 9 of 12 items are Apple App Store reviews from the South African storefront (that listing: 2.2/5 from 243 ratings, fetched 2026-10-02), plus two Hello Peter reviews and one forum post. C1 and C2. Because 75% of the items come from one app listing this is a single-product finding, not an industry-wide one.
- **What they do about it now.** Wait for the next update, create a new account (E067), read figures off the inverter's own display (said by an undated ZA App Store review, not counted), or add third-party monitoring and automations (Solar Assistant, Home Assistant). One forum owner says Home Assistant is 'too complicated to run for the end user'.
- **What they would pay to make it stop.** Stated spend exists for the workaround, not for a fixed app: one owner paid R990 once-off for Solar Assistant (self-reported, MyBroadband Aug 2025); a vendor change to USD14/year for updates was called 'not too bad' by the thread opener while several owners opted out to keep free lifetime updates; two enthusiasts said they would subscribe if specific features were added (conditional, no amount). Enthusiasts only and outside the strict window; UNVERIFIED for mainstream owners.
- **Does an existing product or service already solve it well?** Partly. Third-party tools are used and praised by enthusiasts, but they need a Raspberry Pi and set-up; no app-store reviewer in the sample says they use one. Fit for non-technical owners: UNVERIFIED.
  - [SolarAssistant (local Raspberry-Pi monitoring/automation; Deye listed as supported; remote inverter-setting changes)](https://solar-assistant.io/) - fetched 2026-10-02: plus its shop page (South Africa local shipping in ZAR). Price not visible in the fetched chunk; R990 and USD14/yr are user-reported.
  - [SMH 'Solar Management Hub' by Centurion Solar (Pi-based; app with Telegram fault/outage alerts)](https://centurionsolar.co.za/solar-management-hub/) - NOT fetched: (search excerpt, 2023 crawl). An App Store ZA reviewer names it as better than the vendor app. Current availability and price UNVERIFIED.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E054 (C2, owner, 2026-08-12, [Hello Peter: Sunsynk](https://www.hellopeter.com/sunsynk/reviews/poor-service-e61a9540d73eecb3e62c2e312abfefe560353514-6535638)): "Sadly Sunsynk's support has much to be desired. The agents are non attentive and appear to make up "stories" to justify the performance of my setup. Coupled with that the app and PC browser software is incredibly complex and not at all user friendly ,even for me an electrical engineer !"
  - E056 (C2, owner, 2025-10-09, [MyBroadband Forum](https://mybroadband.co.za/forum/threads/solar-assistant-paid-updates.1321938/)): "I've wasn't paying attention to anything and didn't realise the batteries had not reached 100% in 3 weeks!"
  - E059 (C1, owner, 2026-09-06, [Apple App Store ZA: Sunsynk Connect](https://itunes.apple.com/za/rss/customerreviews/page=1/id=1583953649/sortby=mostrecent/json)): "You cannot directly change the notification sound for the Sunsynk app on an iPhone. When is this going to be addressed!"

### 3. Installer stops answering after payment

`installer_aftersales_unresponsive` | **9 items from 5 sources** | communities {'C1': 6, 'C3': 3} | sources {'reddit': 1, 'review_site': 8} | 78% in the last 12 months | equal-weight rank 4

- **What the pain is.** After payment and installation the installer or seller stops answering: calls and WhatsApps unanswered (E022), warranty repairs 'handed off to someone else' with no updates (E039), tickets signed off as complete while the fault remains (E043), blame placed on the owner (E024). One owner is 'still paying for the solar system while also having to purchase electricity when the system is not operating properly' (E022).
- **Who is complaining.** C1 and C3. Named: Solar Advice, NCSP, Invert Solar, GoSolr (two rows) and one GoSolr customer on Reddit. 8 of 9 items are Hello Peter reviews; 78% fall in the last 12 months.
- **What they do about it now.** Chase by call, WhatsApp, email and app tickets; post public reviews; keep paying while the system is down; one GoSolr customer took two days of leave around a cancelled-then-rescheduled visit (E041).
- **What they would pay to make it stop.** UNVERIFIED. Sunk amounts are stated (R100,000 system price in E038; R20,700 paid to cancel a rental contract in E041) but they are what owners paid, not what they would pay to fix the problem.
- **Does an existing product or service already solve it well?** Unclear. A vetted-installer directory and ombud channels exist, but owners in the sample rely on public reviews instead; no row reports using the directory.
  - [Hello Peter public reviews (GoSolr replies to 99% of negative reviews in about 13 hours; Sunsynk 54%)](https://www.hellopeter.com/gosolr) - fetched 2026-10-02: (GoSolr page; Sunsynk page also fetched). A reply is not a resolution; reply rates are the platform's own.
  - [PV GreenCard (voluntary SAPVIA programme: as-built report, directory of certified companies, 'third party system check available', 'dispute resolution service')](https://pvgreencard.co.za/) - fetched 2026-10-02: States 442 certified installation companies. Effectiveness for owners UNVERIFIED: no row in this study mentions it.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E011 (C3, owner, 2025-02-23, [r/askSouthAfrica](https://www.reddit.com/r/askSouthAfrica/comments/1iw6oi7/people_that_use_gosolar_is_it_worth_it/)): "Installation was delayed and frustrating. Ongoing service is frustrating."
  - E022 (C1, owner, last-12-months label, [Hello Peter: NCSP Solar Energy](https://www.hellopeter.com/ncsp-solar-energy)): "It has now been sent away for repairs four times... the company we bought the system from is not answering our calls or WhatsApp messages. We are still paying for the solar system while also having to purchase electricity when the system is not operating properly."
  - E025 (C1, owner, 2026-03-05, [Hello Peter: Invert Solar](https://www.hellopeter.com/invert-solar)): "a replacement inverter of a different brand — which appears to be a used unit — was sent to me. Unfortunately, this inverter is also not functioning. I have attempted to engage [name] on several occasions regarding this matter, however my messages appear to be going unanswered."

### 4. Rent-to-own / subscription terms: price, escalation, buy-out and exit fees

`financing_rent_to_own_terms` | **8 items from 5 sources** | communities {'C1': 1, 'C3': 7} | sources {'reddit': 5, 'review_site': 2, 'forum': 1} | 50% in the last 12 months | equal-weight rank 2

- **What the pain is.** People on or considering rent-to-own solar describe a monthly price above the bill it replaces (R1,700 quoted, E003), escalation (about R1,740 to R1,830, E005), buy-outs priced at '300+% markup' (E005) or R340,000 for a two-year-old system (E042), exit fees (R20,700 paid, E041; 'a 40k uninstall fee', E010; R35,400 charged against a R30,000 tier, E042), minimum terms, and 'fine print' they distrust (E004).
- **Who is complaining.** C3 (7 of 8: rent-to-own customers and prospects, mostly GoSolr/'GoSolar') plus one cash buyer in C1. Reddit 5, Hello Peter 2, MyBroadband 1; only half of the items fall in the last 12 months.
- **What they do about it now.** Buy outright after research (E004); extend the bond and pay upfront (advice in the same thread); a landlord installed systems for all tenants at his own cost (E003); install your own (E010); for exit disputes, legal advice, a CGSO complaint and a consumer-journalist referral (E044); one customer declined a R340,000 buy-out and bought a new R225,000 system (E042).
- **What they would pay to make it stop.** Stated spend: R1,830/month paid (E005), a R1,700/month quote (E003), R20,700 paid to exit (E041, revealed willingness to pay to leave). A R340,000 buy-out was declined (E042). Willingness to pay for better terms: UNVERIFIED.
- **Does an existing product or service already solve it well?** Partly/unclear. Offers with different published terms exist (buy out anytime; cancel after 24 months). I found no dated customer evidence on how they work out in practice; one Reddit commenter (read, not logged as a complaint) calls Alumo's after-sales good (r/askSouthAfrica 1v1cfnj, 2026-07-20).
  - [Alumo rent-to-own and subscription plans](https://alumo.co.za/plans-pricing/) - fetched 2026-10-02: Rent-to-own from R1,449 p/m + R700 initiation fee (3/5/7 years; buy out and upgrade anytime; maintenance and insurance included); subscription from R1,499 p/m with option to cancel after 24 months. Vendor shows 4.9 Google / 9.2 Hello Peter: NOT verified.
  - [Bank solar loans / home-loan top-up (named by commenters)](https://energybee.co.za/tools/solar-financing-calculator) - NOT fetched: NOT verified at source. A commercial comparison site quotes 2026 rates (Nedbank Prime-0.5, FNB Prime+1, Absa Prime+2) - treat as UNVERIFIED.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E003 (C3, prospective, 2026-07-20, [r/askSouthAfrica](https://www.reddit.com/r/askSouthAfrica/comments/1v1cfnj/solar_panels_with_monthly_payments_worth_it/oymcipr/)): "I was looking at a renting option last year through GoSolar, I was looking at about R1700 a month which was more than what I was paying for electricity."
  - E005 (C3, owner, 2026-07-20, [r/southafrica](https://www.reddit.com/r/southafrica/comments/1v1cecl/solar_with_monthly_payments/oypgkgq/)): "Price did increase from what it was when I signed up (think 1740pm to now about 1830pm)... one of the switches on the main DB was for a 3 phase system instead of single phase residential... buyout price wasn't at 300+% markup for the entire system"
  - E009 (C3, prospective, 2025-02-23, [r/askSouthAfrica](https://www.reddit.com/r/askSouthAfrica/comments/1iw6oi7/people_that_use_gosolar_is_it_worth_it/)): "If we pay R1500 for electricity, and it is barley enough for a month. And the medium system cost R1740. I can't rap my head around it."

### 5. Inverter faults that recur after repair

`inverter_fault_recurring` | **5 items from 4 sources** | communities {'C1': 5} | sources {'review_site': 5} | 100% in the last 12 months | equal-weight rank 12

- **What the pain is.** Inverters that keep faulting: error codes (F20 on an 8 kW unit, E23 on a 12 kW unit), unstable power, flickering lights and unexpected shutdowns (E014), a unit 'sent away for repairs four times' (E022), and repair visits that are charged but do not fix the fault (E037).
- **Who is complaining.** C1 only (5 of 5 are Hello Peter reviews): Sunsynk, Deye (two), NCSP and Solar Advice customers.
- **What they do about it now.** Installer loan units where available (E014), repeated call-outs, returns to the brand; owners keep paying for the system while buying grid power (E022).
- **What they would pay to make it stop.** UNVERIFIED. Call-out charges appear (E014, E037) but no amount is stated and none is framed as willingness to pay.
- **Does an existing product or service already solve it well?** No evidence that it is solved: all five describe a fault that stayed unresolved after at least one repair or visit, or no action at all (E038).
  - [Manufacturer warranty plus installer loan units (as described by reviewers; no independent diagnostic service verified)](https://www.hellopeter.com/deye-inverters) - NOT fetched: Search excerpt of Hello Peter 'Ningbo Deye' only (NPS -100, 8 reviews in 12 months; one review praises an in-warranty repair at a service centre). Not fetched.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E014 (C1, owner, 2026-08-24, [Hello Peter: Sunsynk](https://www.hellopeter.com/sunsynk/reviews/sunsynk-worst-company-service-6556639)): "Over the past 5 months, I have endured 3 failed repair attempts, multiple installer call-out fees, countless follow-ups, and still no resolution from Sunsynk."
  - E021 (C1, owner, last-12-months label, [Hello Peter: Deye (Ningbo Deye)](https://www.hellopeter.com/deye-inverters)): "My 8Kwh invertor was installed and within 2 month it gave a F20 error (hardware issue to do with the transformer). It was taken to Deye for repairs (took 2 weeks) only to come back without anything being fixed. Multiple people have the same issue"
  - E022 (C1, owner, last-12-months label, [Hello Peter: NCSP Solar Energy](https://www.hellopeter.com/ncsp-solar-energy)): "It has now been sent away for repairs four times... the company we bought the system from is not answering our calls or WhatsApp messages. We are still paying for the solar system while also having to purchase electricity when the system is not operating properly."

### 6. Batteries that swell, lose BMS communication or fail early

`battery_failure_degradation` | **4 items from 3 sources** | communities {'C1': 3, 'C2': 1} | sources {'review_site': 4} | 75% in the last 12 months | equal-weight rank 8 | ⚑ 50% from `hp:pylontech`

- **What the pain is.** Batteries that swell or fail early and then take months to replace: one swollen 5 kWh battery with no replacement after 7 months (E015), two swollen 5 kWh batteries awaiting replacement for more than 6 months (E048), two of four batteries dead within about five years with a month-plus wait and a higher electricity bill meanwhile (E050), and a retail-bought battery with BMS problems and a refused refund (E026, Oct 2024).
- **Who is complaining.** C1 (3) and C2 (1); all Hello Peter; Sunsynk, Pylontech and a CFE-brand battery bought from a retailer.
- **What they do about it now.** Installer escalation and waiting; one owner bought another battery elsewhere after refusal of a refund (E026).
- **What they would pay to make it stop.** UNVERIFIED.
- **Does an existing product or service already solve it well?** No on this evidence: claims were still open after 6-7 months in 2026 (E015, E048).
  - [Solar Deity Pylontech repair centre (vendor claims under 7 days and a loan battery)](https://solardeity.co.za/pylontech-servicesupport/) - fetched 2026-10-02: vendor claims are unverified and not borne out by 2026 Hello Peter reviews of the brand's local warranty channel (waits of one to six-plus months).
  - [Consumer Protection Act s56](https://thencc.org.za/wp-content/uploads/2023/11/Explanatory-Note-7-of-2023.pdf) - fetched 2026-10-02: Six-month window only, so it does not reach failures in year 2-5.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E015 (C1, owner, 2026-08-18, [Hello Peter: Sunsynk](https://www.hellopeter.com/sunsynk/reviews/totally-useless-customer-service-167ab4325a3959b018e78e1a9981ef681e7d987f-6547432)): "My 5kWh battery was swelling and my installer returned it to Sunsynk for warranty replacement... That was in January (7 months ago!), and I still don't have a replacement"
  - E026 (C2, owner, 2024-10-24, [Hello Peter: Solar Deity (CFE batteries)](https://www.hellopeter.com/solar-deity-pty-ltd-cf-energy-coltd/reviews/bad-bad-experience-they-sell-cfe-5100s-batteries-5336725)): "I was told by multiple technicians that its a BMS problem and that the CFE 5100S batteries are substandard quality and that is the reason why I'm experiencing the hikes and the dips in percentages."
  - E048 (C1, owner, 2026-06-09, [Hello Peter: Pylontech](https://www.hellopeter.com/pylontech)): "Both batteries became swollen and were sent back for a warranty claim more than six (6) months ago. Despite this significant amount of time, we have not received our replacements or a proper resolution."

### 7. Owners do not see the bill fall

`savings_below_expectation` | **4 items from 3 sources** | communities {'C1': 3, 'C3': 1} | sources {'reddit': 2, 'review_site': 1, 'forum': 1} | 100% in the last 12 months | equal-weight rank 10 | ⚑ 50% from `reddit:1uejsus`

- **What the pain is.** Owners cannot see the saving: 'still buying the same amount of unit... all I have managed to do is add an expense' (E001); a Solar Advice customer whose system 'was costing me way more money than I was paying without the oversize...' (the excerpt is cut off, E035); installer-set discharge and overnight grid-charge settings that removed the saving (E027); and a rental customer whose municipal bill treated generation as consumption, with a self-estimated overpayment of about R30,000 (E044).
- **Who is complaining.** C1 (3) and C3 (1); Reddit 2, Hello Peter 1, MyBroadband 1; 100% inside the last 12 months.
- **What they do about it now.** Geyser timers, an ET-12 load meter feeding the inverter or an inverter per phase (advice in E001's thread); changing settings oneself (E027); switching from post-paid to prepaid, legal advice and a CGSO complaint (E044).
- **What they would pay to make it stop.** UNVERIFIED. The R30,000 is the poster's own estimate of overpayment (stated_spend), not a willingness to pay.
- **Does an existing product or service already solve it well?** Unclear. Fixes described are DIY and depend on owner skill; none verified as effective.
  - [No product verified. Commenters name geyser controllers (Geyserwise, Sonoff, CBI), the ET-12 meter and Solar Assistant / Home Assistant.](https://solar-assistant.io/) - fetched 2026-10-02: Only SolarAssistant's page was fetched (see monitoring row); the others are named by commenters and not verified.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E001 (C1, owner, 2026-06-24, [r/southafrica](https://www.reddit.com/r/southafrica/comments/1uejsus/not_seeing_solar_savings/)): "some how I am still buying the same amount of unit (I use a prepaid meter) as I did before solar. All I have managed to do is add an expense of the solar."
  - E035 (C1, owner, 2026-05-26, [Hello Peter: Solar Advice](https://www.hellopeter.com/solar-advice)): "customer service stinks as far as after sales support is concerned. I was disappointed by their technical and sales team who repeatedly failed to answer my request for help after I realised the solar system was costing me way more money than I was paying without the oversize"
  - E044 (C3, owner, 2026-03-02, [MyBroadband Forum](https://mybroadband.co.za/forum/threads/defective-solar-system-installation.1334046/)): "Due to an installation/ configuration defect the system has not been delivering the "promised bill savings" — municipal billing treated generation as grid consumption. After remedial re-wiring by Service provider— they proposed 4 months reimbursement - which I believe is inadequate."

### 8. Installation defects with safety consequences

`workmanship_defects` | **4 items from 3 sources** | communities {'C1': 1, 'C3': 3} | sources {'reddit': 1, 'review_site': 3} | 75% in the last 12 months | equal-weight rank 5 | ⚑ 50% from `hp:gosolr`

- **What the pain is.** Defects with safety consequences: an array 'left ungrounded for over a month' causing a DC fuse to catch fire on a R159,000 job (E023); wiring that burned on installation with the repair done wrongly and tickets 'signed off as complete' (E043); a main-DB switch rated for 3-phase on a single-phase home (E005); walls left damaged and an oven and stove not working after a de-installation (E041).
- **Who is complaining.** C3 (3, rent/subscription customers) and C1 (1); Hello Peter 3, Reddit 1.
- **What they do about it now.** Second electricians, escalation and public warnings.
- **What they would pay to make it stop.** UNVERIFIED (R159,000 and R20,700 are amounts already paid).
- **Does an existing product or service already solve it well?** Unclear to no: the compliance paperwork exists, but the cited failure is that it was not checked.
  - [Certificate of Compliance for the wiring (required for registration per Eskom's page)](https://www.eskom.co.za/solar-pv-registration-legal-compliance-campaign-update-act-now-stay-legal-stay-safe-eskom-continues-to-provide-up-to-r10000-assistance/) - fetched 2026-10-02: Yet E023 says the independent CoC electrician 'didn't even check the work'.
  - [PV GreenCard as-built report and 'third party system check available'](https://pvgreencard.co.za/) - fetched 2026-10-02: no row shows an owner using it to resolve a defect.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E005 (C3, owner, 2026-07-20, [r/southafrica](https://www.reddit.com/r/southafrica/comments/1v1cecl/solar_with_monthly_payments/oypgkgq/)): "Price did increase from what it was when I signed up (think 1740pm to now about 1830pm)... one of the switches on the main DB was for a 3 phase system instead of single phase residential... buyout price wasn't at 300+% markup for the entire system"
  - E023 (C1, owner, last-12-months label, [Hello Peter: NCSP Solar Energy](https://www.hellopeter.com/ncsp-solar-energy)): "I paid over R159,000 for a solar installation... They left the entire system ungrounded for over a month, which caused a DC fuse to catch fire... the solar array capacity they sold me does not match what the system can actually do"
  - E041 (C3, owner, 2025-07-01, [Hello Peter: GoSolr](https://www.hellopeter.com/gosolr/reviews/gosolrs-poor-service-cost-me-time-money-and-stress-5813706)): "I recently paid R20,700 to cancel my GoSolr contract and have the solar system removed... I was left with walls in a poor and unfinished state, requiring me to spend additional money to repair their damage... ever since the system was removed, my oven and stove have not been working."

### 9. Grid-registration (SSEG) is seen as costly, pointless or unenforced

`sseg_registration_burden` | **4 items from 2 sources** | communities {'C1': 3, 'C2': 1} | sources {'forum': 4} | 100% in the last 12 months | equal-weight rank 9 | ⚑ 75% from `mb:1347774`

- **What the pain is.** Owners treat SSEG registration as costly, pointless or unenforced and many do not do it. In a MyBroadband poll (74 voters, self-selected) 45 of the 46 voters who have home solar had not registered. Owner comments: 'I tried at the time, they ignored me' (E029), 'I will rather upgrade my small system than register' (E030), 'Eskom must pay us R5000.00 to reg' (E031), 'Just don't register if you are in JHB' (E032). Two bystander Reddit comments on the August 2026 R30,000-fines story are excluded from the count.
- **Who is complaining.** C1 (3) and C2 (1); all forum posts from Sep-Oct 2026; 75% of the items come from one thread.
- **What they do about it now.** Do not register; fit an NRS-approved inverter and get a CoC only (advice in the same PowerForum thread as E032/E034); expand the system or go off-grid to avoid the grid (E030, E032); on Cape Town, one owner says the municipality is strict (E032) while a bystander says none of about 15 Cape Town owners they know is registered (E034, excluded).
- **What they would pay to make it stop.** Evidence points to unwillingness: no owner states a price they would pay and one expects to be paid R5,000 (E031). Eskom waived fees of up to R10,000 until 31 Mar 2026 (fetched); a waiver to 30 Sep 2026 appears only in secondary sources, and the position after 30 Sep 2026 is UNVERIFIED.
- **Does an existing product or service already solve it well?** Not on this evidence. The process, tool and a fee waiver exist, yet the poll shows 45 of 46 solar owners unregistered (self-selected) and owners describe not trusting or not bothering.
  - [Eskom registration: online Customer Application Tool, fee waiver, simplified sign-off by a DoEL-registered person since 1 Oct 2025](https://www.eskom.co.za/solar-pv-registration-legal-compliance-campaign-update-act-now-stay-legal-stay-safe-eskom-continues-to-provide-up-to-r10000-assistance/) - fetched 2026-10-02: (statement dated 14 Jan 2026). Municipal customers must use their municipality; penalties are described inconsistently by secondary sources (UNVERIFIED).
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E029 (C1, owner, 2026-10-01, [MyBroadband Forum](https://mybroadband.co.za/forum/threads/have-you-registered-your-home-solar-with-eskom.1347774/)): "I tried at the time, they ignored me, now ****  them."
  - E032 (C2, owner, 2026-09-02, [PowerForum (SA)](https://powerforum.co.za/topic/34692-residential-solar-sseg-discussion/)): "Just don't register if you are in JHB. Problem solved. If in CPT, you don't have a choice coz the muni there is like a dictator. JHB and the rest the Munis aren't enforcing anything. Eskom has also basically shown they cant enforce anything also."
  - E030 (C1, owner, 2026-10-01, [MyBroadband Forum](https://mybroadband.co.za/forum/threads/have-you-registered-your-home-solar-with-eskom.1347774/)): "I will rather upgrade my small system than register. Eskom can then disconnect me."

### 10. Buyers cannot tell which installer or finance provider to trust

`installer_trust_scam_fear` | **3 items from 2 sources** | communities {'C1': 1, 'C3': 2} | sources {'reddit': 2, 'review_site': 1} | 100% in the last 12 months | equal-weight rank 7 | ⚑ 67% from `reddit:1v1cfnj`

- **What the pain is.** Buyers cannot tell which installers or finance providers to trust: 'the reviews on Hello Peter make me suspicious' (E002), 'the fine print... just seems very suspicious' (E004), and a financed customer calling the experience 'dishonest' (E036).
- **Who is complaining.** C3 (2) and C1 (1); Reddit 2, Hello Peter 1; 67% of the items come from the July 2026 rent-to-own thread.
- **What they do about it now.** Read Hello Peter, ask Reddit, buy outright after research (E004).
- **What they would pay to make it stop.** UNVERIFIED.
- **Does an existing product or service already solve it well?** Unclear. Both exist; whether buyers use the directory is unverified.
  - [PV GreenCard directory of certified installation companies](https://pvgreencard.co.za/) - fetched 2026-10-02: (442 companies). No owner in the sample mentions using it.
  - [Hello Peter reviews](https://www.hellopeter.com/gosolr) - fetched 2026-10-02: The complaint is that the reviews themselves raise suspicion.
- **Evidence (verbatim; ids in `evidence.jsonl`).**
  - E002 (C3, prospective, 2026-07-20, [r/askSouthAfrica](https://www.reddit.com/r/askSouthAfrica/comments/1v1cfnj/solar_panels_with_monthly_payments_worth_it/)): "Having a look at the reviews on Hello Peter makes me suspicious."
  - E036 (C3, owner, last-12-months label, [Hello Peter: Solar Advice](https://www.hellopeter.com/solar-advice)): "I engaged Solar Advice under the impression that they were a legitimate and trustworthy company, but my experience has been extremely disappointing. In April 2023, I financed a solar system through them and Merchant West"
  - E004 (C1, owner, 2026-07-20, [r/askSouthAfrica](https://www.reddit.com/r/askSouthAfrica/comments/1v1cfnj/solar_panels_with_monthly_payments_worth_it/oymdt7g/)): "If you look at the fine print on GoSolar and so on, it just seems very suspicious and not at all worth it, due to their buy-out clause"

## 4. Below the top 10

- `repeat_callout_fees` - 3 item(s): repeat call-out/labour charges for unresolved or in-warranty faults
- `cannot_verify_installation_quality` - 2 item(s): owner cannot tell if the install or settings are right (E001, E057)
- `installation_delays_lead_time` - 2 item(s): late arrivals / slow installs
- `installer_misconfiguration_settings` - 2 item(s): installer-set discharge %, grid-charge or CT-clamp errors found later
- `municipal_fixed_charge_solar_owners` - 2 item(s): fixed municipal/connection charges that stay with solar (R1,000/month stated in E006)
- `inverter_battery_compat_config` - 2 item(s): inverter/battery/logger compatibility problems (C2 only)
- `repair_downtime_no_fallback` - 2 item(s): no power while a unit is away for repair
- `warranty_claim_rejected` - 2 item(s) (single source): claim rejected with vague reasons ('misuse')
- `billing_debit_order_errors` - 1 item(s) (single source): debits after cancellation, refunds promised but not paid (rent-to-own)
- `coc_compliance_integrity` - 1 item(s) (single source): CoC electrician did not check the work (E023)
- `firmware_update_failure` - 1 item(s) (single source): remote firmware update left a working inverter dead (E017)
- `grid_connection_cost_delay` - 1 item(s) (single source): R150k-R200k new grid connection avoided by going off-grid (E007)
- `grid_voltage_issues` - 1 item(s) (single source): high municipal voltage cited with an inverter fault (E022)
- `municipal_billing_metering_mismatch` - 1 item(s) (single source): municipality billed generation as consumption (E044)
- `refund_returns_refused` - 1 item(s) (single source): refund refused on a battery with BMS faults (E026)
- `replacement_unit_quality` - 1 item(s) (single source): replacement inverter was a used, different-brand unit that also failed (E025)
- `system_overpromised_mismatch` - 1 item(s) (single source): delivered capacity does not match what was sold
- `warranty_verification_serial` - 1 item(s) (single source): cannot verify an inverter serial/warranty; passed between ten people (E020)

## 5. Robustness: how much to trust the order

- **Small numbers.** The top pain has 17 items; ranks 5-9 sit at 3-5 items, so differences of one item are noise. Ties were broken by the pre-set rules, not by judgement.
- **Equal community weight.** Pooled counts are dominated by C1 (38 of 59 counted rows; C2 9, C3 12). On an equal-weight score the top 10 differs: out inverter_fault_recurring; in inverter_battery_compat_config.
- **Strict 12-month window only.** The top 10 is the same set (the strict ranking is computed by the same tool).
- **Source concentration.** Flagged pains: `warranty_repair_delay_runaround` (41% from `hp:sunsynk`), `monitoring_app_issues` (75% from `app:sunsynk-connect-ios-za`), `battery_failure_degradation` (50% from `hp:pylontech`), `savings_below_expectation` (50% from `reddit:1uejsus`), `workmanship_defects` (50% from `hp:gosolr`), `sseg_registration_burden` (75% from `mb:1347774`), `installer_trust_scam_fear` (67% from `reddit:1v1cfnj`). For review sites a 'source' is the business page, so concentration there is a conservative measure.
- **Platform bias.** Review sites and app stores collect complaints by design; Reddit and forums collect advice-seeking. Counts therefore measure how often a complaint recurs among people who write, not how many owners suffer it. No count here should be read as 'X% of owners'.
- **Excluded voices.** {'bystander': 7, 'trade': 1}. Bystander/installer tags that no owner row echoes: none.

### Dates

- exact item date: 30 rows
- thread or page date: 14 rows
- Hello Peter 'last 12 months' label (no per-review date seen): 12 rows
- inferred from text/attachment/site convention: 11 rows

## 6. What this does not show

- Prevalence, market size, or willingness to pay for any improvement. Willingness to pay is **UNVERIFIED** for 7 of the 10 pains; the other 3 have only indirect evidence: spend on a workaround (Solar Assistant, R990), sunk payments (rent-to-own R1,830/month, R20,700 exit fee) and stated unwillingness (registration).
- Anything about small businesses or farms, which could not be sampled. Anything from Facebook or X.
- Whether the ombud/legal routes work for solar disputes: only one row reports using the CGSO and no outcome is reported. This is not legal advice; the CPA reading is the National Consumer Commission's own note.
- Near-identical Hello Peter reviews were counted once (four Deye reviews with the same 'third year of a 10-year warranty' story); a cross-posted Reddit question was counted once.
- The tag taxonomy was built while collecting (definitions in `codebook.json`); one definition was broadened once (`warranty_repair_delay_runaround` now includes unhelpful agents).

## 7. Existing-solution register

| Kind | Page | Fetched? | What it says / status |
|---|---|---|---|
| vendor_claim | https://solardeity.co.za/pylontech-servicesupport/ | no | Solar Deity 'Pylontech Official Repair Center' page (search excerpt, not fetched): claims repair turnaround under 7 days, loan battery service, remote diagnostics, firmware/BMS calibration, door-to-door pickup. Vendor marketing; not independently verified. |
| verified_solution | https://www.eskom.co.za/solar-pv-registration-legal-compliance-campaign-update-act-now-stay-legal-stay-safe-eskom-continues-to-provide-up-to-r10000-assistance/ | yes, 2026-10-02 | Eskom statement dated 14 Jan 2026: systems <100kVA must be registered with Eskom/municipality; fees up to R10,000 incl. free smart meter waived to 31 Mar 2026 for residential <=50kVA; since 1 Oct 2025 a DoEL-registered person may sign off (ECSA not mandatory); documents = CoC + NRS097-2-1 inverter certificate + SSEG commissionin... |
| verified_solution | https://www.cgso.org.za/ | yes, 2026-10-02 | Consumer Goods and Services Ombud: compulsory ombud scheme under the CPA; free for consumers; you must first complain to the supplier, then can escalate; applicability to any given solar supplier depends on that supplier being a registered participant - UNVERIFIED for solar firms (a MyBroadband poster says they lodged a CGSO com... |
| verified_solution | https://thencc.org.za/wp-content/uploads/2023/11/Explanatory-Note-7-of-2023.pdf | yes, 2026-10-02 | National Consumer Commission Explanatory Note 7 of 2023 quotes CPA s56(2): within six months after delivery the consumer may return defective goods without penalty at the supplier's risk and expense, and the supplier must, at the consumer's direction, repair/replace or refund. Consumer elects the remedy. Window is six months onl... |
| verified_solution | https://alumo.co.za/plans-pricing/ | yes, 2026-10-02 | Alumo (vendor page): rent-to-own from R1,449 p/m + R700 initiation fee (3/5/7 years; Solis 5kW + Eenovance 5.3kWh + 3 panels); buy out anytime; upgrade anytime; free annual maintenance; insurance included. Subscription from R1,499 p/m + R1,499 initiation fee (5kW/5.32kWh/7 panels), option to cancel after 24 months. Vendor shows ... |
| verified_solution | https://solar-assistant.io/ | yes, 2026-10-02 | SolarAssistant (vendor): local monitoring/automation on a Raspberry Pi, web/Android/iPhone, remote inverter-setting changes, Home Assistant integration, lists Deye among supported inverters. Shop page (fetched) offers South Africa local shipping in ZAR via The Courier Guy. PRICE not visible in fetched chunk - user-reported R990 ... |
| verified_solution | https://pvgreencard.co.za/ | yes, 2026-10-02 | PV GreenCard (SAPVIA-powered, voluntary): as-built report issued to the system owner by certified installation companies; public directory of certified companies; page states 442 certified installation companies, 21 approved training centres, 17 assessment centres; lists 'third party system check available' and 'dispute resoluti... |
| vendor_claim | https://solardeity.co.za/pylontech-servicesupport/ | yes, 2026-10-02 | Solar Deity 'Pylontech Official Repair Center' (vendor page): claims on-site assessment, pickup/delivery, repair turnaround under 7 days, loan battery service, BMS calibration/firmware; testimonials are unverifiable. Contrast: Hello Peter 'Pylontech' reviews (Nov'25-Oct'26, NPS -100) report a claim open >6 months (one review), a... |
| secondary | https://centurionsolar.co.za/solar-management-hub/ | no | (search excerpt, crawl 2023). Centurion Solar 'SMH' (Solar Management Hub): Raspberry-Pi based monitoring with mobile app, Telegram fault/outage notifications, mode switching and battery time-to-% display; an App Store ZA reviewer names it as an alternative for Sunsynk. Current availability/price UNVERIFIED. |
| secondary | https://energybee.co.za/tools/solar-financing-calculator | no | (search excerpt). Comparison site claims 2026 bank solar-loan rates: Nedbank GreenSave Prime-0.5 (10.75%), FNB Solar Prime+1 (12.25%), Absa Green Home Prime+2 (13.25%); rent-to-own modelled ~18% (Prime+6.75). Commercial site, assumptions unknown - UNVERIFIED at the banks. |

## 8. Files and how to reproduce

- `research/solar-complaint-mining/evidence.jsonl` - one row per complaint-bearing item (verbatim quote <= 320 chars, community, voice, date and date basis, tags, spend, workaround). No usernames or personal names (POPIA).
- `scanned.jsonl` (items read per page/thread), `queries.jsonl` (every search/fetch attempt), `context.jsonl` (ratings, official statements, WTP signals; never counted), `codebook.json` (tag definitions, post-hoc clusters), `tally.json` / `tally.md` (tool output).
- `python3 tools/complaint_tally.py --dir research/solar-complaint-mining --as-of 2026-10-02 --out-json research/solar-complaint-mining/tally.json --out-md research/solar-complaint-mining/tally.md --strict`
- `python3 research/solar-complaint-mining/make_report.py` regenerates this file; `python3 -m unittest discover -s tests` runs the tests.

