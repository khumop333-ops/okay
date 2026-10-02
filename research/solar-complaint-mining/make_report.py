#!/usr/bin/env python3
"""Builds REPORT.md for the solar complaint-mining study.

Numbers, tables, quotes and flags are computed from the study files through
tools/complaint_tally.py.  The per-pain analysis text (who / workaround /
willingness to pay / existing solutions) is written by hand in NOTES below and
is tied to evidence ids.  Nothing here proposes a product.

Run from the repo root:  python3 research/solar-complaint-mining/make_report.py
"""

import collections
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from tools import complaint_tally as ct  # noqa: E402

AS_OF = dt.date(2026, 10, 2)
FETCHED = "2026-10-02"


def jl(name):
    return ct.load_jsonl(os.path.join(HERE, name))


# --------------------------------------------------------------- hand-written analysis
# Each entry is grounded in evidence rows (ids) and in pages fetched on 2026-10-02.
NOTES = {
 "warranty_repair_delay_runaround": dict(
  title="Brand/distributor warranty repair drags on for months with no answers",
  wtp_short="UNVERIFIED", solved_short="No (on this evidence)",
  pain="After an inverter or battery fails under warranty, the brand or distributor repair/replacement stretches to months: parts are 'awaited', job numbers cannot be traced, emails and WhatsApps go unanswered, and claims are handed between installer, distributor and brand. Examples: a swollen battery with no replacement after 7 months (E015); a unit not heard about for almost 3 months (E016); three failed repairs in five months (E014); a 10-year-warranty system defective in year 3 with no acknowledgement even after escalation to the global CEO (E019).",
  who="Installer-installed homeowners (C1) and hands-on/enthusiast owners (C2). Brands named: Sunsynk (most), Deye, Pylontech; installers named: Solar Advice, NCSP. 16 of the items are Hello Peter reviews, one is an app review; all are inside the last 12 months.",
  workaround="Owners route everything through their installer, who chases the brand; accept an installer-supplied loan unit where one exists (E014); escalate to senior staff or the CEO (E015, E019); and post public reviews. One owner was told testing an in-warranty inverter would cost labour and could leave them on Eskom power for up to 21 days (E040).",
  wtp="UNVERIFIED: no row states what an owner would pay for faster repair. Observed spend is being charged, not offering to pay: a labour quote of R6,000 to test an in-warranty inverter plus about R2,000 for a WiFi-controller job (E040, quoted_price) and repeated installer call-out fees with no amount stated (E014).",
  existing=[
   ("Consumer Protection Act s56 (six-month right to repair/replace/refund at the consumer's election, supplier's risk and expense)","https://thencc.org.za/wp-content/uploads/2023/11/Explanatory-Note-7-of-2023.pdf",True,"Fetched. National Consumer Commission note quotes s56(2). It covers only the first six months after delivery; later failures rest on the manufacturer's contractual warranty."),
   ("Consumer Goods and Services Ombud (free escalation after a supplier complaint)","https://www.cgso.org.za/",True,"Fetched. Whether a given solar supplier is a registered participant is UNVERIFIED; only one counted row (E044) reports using it, and no outcome is reported."),
   ("Solar Deity 'Pylontech Official Repair Center' (claims under-7-day turnaround and a loan battery)","https://solardeity.co.za/pylontech-servicesupport/",True,"Fetched. Vendor claims only; unverified. Hello Peter 'Pylontech' reviews (E047-E050) describe a claim open for more than six months (E048), a month-plus wait for stock (E050) and rejections for 'misuse' (E047, E049), via a different local agent."),
  ],
  solves="No on this evidence. A legal right and an ombud exist, but 16 Hello Peter reviews from the last 12 months describe the same months-long pattern; Hello Peter shows Sunsynk NPS -67 (14-15 reviews; page fetched), Deye -100 (8) and Pylontech -100 (5) (the last two from search excerpts of their pages)."),
 "monitoring_app_issues": dict(
  title="Monitoring app/portal is unreliable or too complex (concentrated on one vendor app)",
  wtp_short="Workaround spend only (enthusiasts)", solved_short="Partly (technical owners only)",
  pain="The inverter vendor's monitoring app is unreliable or hard to use: 'service error' screens, previous days' numbers gone after an update (E066), sign-in broken after updates in July 2026 (E061, E063), grid-outage notifications not working for 'more than a month' (E065), an electrical engineer calling it 'incredibly complex' (E054), and a WiFi dongle that stopped in week one (E055). One enthusiast did not notice for three weeks that their batteries never reached 100% (E056). An undated review on the same ZA listing (not counted) adds 'service error' screens and daily statistics resetting to 0.",
  who="Sunsynk owners. 9 of 12 items are Apple App Store reviews from the South African storefront (that listing: 2.2/5 from 243 ratings, fetched 2026-10-02), plus two Hello Peter reviews and one forum post. C1 and C2. Because 75% of the items come from one app listing this is a single-product finding, not an industry-wide one.",
  workaround="Wait for the next update, create a new account (E067), read figures off the inverter's own display (said by an undated ZA App Store review, not counted), or add third-party monitoring and automations (Solar Assistant, Home Assistant). One forum owner says Home Assistant is 'too complicated to run for the end user'.",
  wtp="Stated spend exists for the workaround, not for a fixed app: one owner paid R990 once-off for Solar Assistant (self-reported, MyBroadband Aug 2025); a vendor change to USD14/year for updates was called 'not too bad' by the thread opener while several owners opted out to keep free lifetime updates; two enthusiasts said they would subscribe if specific features were added (conditional, no amount). Enthusiasts only and outside the strict window; UNVERIFIED for mainstream owners.",
  existing=[
   ("SolarAssistant (local Raspberry-Pi monitoring/automation; Deye listed as supported; remote inverter-setting changes)","https://solar-assistant.io/",True,"Fetched, plus its shop page (South Africa local shipping in ZAR). Price not visible in the fetched chunk; R990 and USD14/yr are user-reported."),
   ("SMH 'Solar Management Hub' by Centurion Solar (Pi-based; app with Telegram fault/outage alerts)","https://centurionsolar.co.za/solar-management-hub/",False,"NOT fetched (search excerpt, 2023 crawl). An App Store ZA reviewer names it as better than the vendor app. Current availability and price UNVERIFIED."),
  ],
  solves="Partly. Third-party tools are used and praised by enthusiasts, but they need a Raspberry Pi and set-up; no app-store reviewer in the sample says they use one. Fit for non-technical owners: UNVERIFIED."),
 "installer_aftersales_unresponsive": dict(
  title="Installer stops answering after payment",
  wtp_short="UNVERIFIED", solved_short="Unclear",
  pain="After payment and installation the installer or seller stops answering: calls and WhatsApps unanswered (E022), warranty repairs 'handed off to someone else' with no updates (E039), tickets signed off as complete while the fault remains (E043), blame placed on the owner (E024). One owner is 'still paying for the solar system while also having to purchase electricity when the system is not operating properly' (E022).",
  who="C1 and C3. Named: Solar Advice, NCSP, Invert Solar, GoSolr (two rows) and one GoSolr customer on Reddit. 8 of 9 items are Hello Peter reviews; 78% fall in the last 12 months.",
  workaround="Chase by call, WhatsApp, email and app tickets; post public reviews; keep paying while the system is down; one GoSolr customer took two days of leave around a cancelled-then-rescheduled visit (E041).",
  wtp="UNVERIFIED. Sunk amounts are stated (R100,000 system price in E038; R20,700 paid to cancel a rental contract in E041) but they are what owners paid, not what they would pay to fix the problem.",
  existing=[
   ("Hello Peter public reviews (GoSolr replies to 99% of negative reviews in about 13 hours; Sunsynk 54%)","https://www.hellopeter.com/gosolr",True,"Fetched (GoSolr page; Sunsynk page also fetched). A reply is not a resolution; reply rates are the platform's own."),
   ("PV GreenCard (voluntary SAPVIA programme: as-built report, directory of certified companies, 'third party system check available', 'dispute resolution service')","https://pvgreencard.co.za/",True,"Fetched. States 442 certified installation companies. Effectiveness for owners UNVERIFIED: no row in this study mentions it."),
  ],
  solves="Unclear. A vetted-installer directory and ombud channels exist, but owners in the sample rely on public reviews instead; no row reports using the directory."),
 "financing_rent_to_own_terms": dict(
  title="Rent-to-own / subscription terms: price, escalation, buy-out and exit fees",
  wtp_short="Stated spend (payments, exit fee)", solved_short="Partly / unclear",
  pain="People on or considering rent-to-own solar describe a monthly price above the bill it replaces (R1,700 quoted, E003), escalation (about R1,740 to R1,830, E005), buy-outs priced at '300+% markup' (E005) or R340,000 for a two-year-old system (E042), exit fees (R20,700 paid, E041; 'a 40k uninstall fee', E010; R35,400 charged against a R30,000 tier, E042), minimum terms, and 'fine print' they distrust (E004).",
  who="C3 (7 of 8: rent-to-own customers and prospects, mostly GoSolr/'GoSolar') plus one cash buyer in C1. Reddit 5, Hello Peter 2, MyBroadband 1; only half of the items fall in the last 12 months.",
  workaround="Buy outright after research (E004); extend the bond and pay upfront (advice in the same thread); a landlord installed systems for all tenants at his own cost (E003); install your own (E010); for exit disputes, legal advice, a CGSO complaint and a consumer-journalist referral (E044); one customer declined a R340,000 buy-out and bought a new R225,000 system (E042).",
  wtp="Stated spend: R1,830/month paid (E005), a R1,700/month quote (E003), R20,700 paid to exit (E041, revealed willingness to pay to leave). A R340,000 buy-out was declined (E042). Willingness to pay for better terms: UNVERIFIED.",
  existing=[
   ("Alumo rent-to-own and subscription plans","https://alumo.co.za/plans-pricing/",True,"Fetched. Rent-to-own from R1,449 p/m + R700 initiation fee (3/5/7 years; buy out and upgrade anytime; maintenance and insurance included); subscription from R1,499 p/m with option to cancel after 24 months. Vendor shows 4.9 Google / 9.2 Hello Peter: NOT verified."),
   ("Bank solar loans / home-loan top-up (named by commenters)","https://energybee.co.za/tools/solar-financing-calculator",False,"NOT verified at source. A commercial comparison site quotes 2026 rates (Nedbank Prime-0.5, FNB Prime+1, Absa Prime+2) - treat as UNVERIFIED."),
  ],
  solves="Partly/unclear. Offers with different published terms exist (buy out anytime; cancel after 24 months). I found no dated customer evidence on how they work out in practice; one Reddit commenter (read, not logged as a complaint) calls Alumo's after-sales good (r/askSouthAfrica 1v1cfnj, 2026-07-20)."),
 "inverter_fault_recurring": dict(
  title="Inverter faults that recur after repair",
  wtp_short="UNVERIFIED", solved_short="No (on this evidence)",
  pain="Inverters that keep faulting: error codes (F20 on an 8 kW unit, E23 on a 12 kW unit), unstable power, flickering lights and unexpected shutdowns (E014), a unit 'sent away for repairs four times' (E022), and repair visits that are charged but do not fix the fault (E037).",
  who="C1 only (5 of 5 are Hello Peter reviews): Sunsynk, Deye (two), NCSP and Solar Advice customers.",
  workaround="Installer loan units where available (E014), repeated call-outs, returns to the brand; owners keep paying for the system while buying grid power (E022).",
  wtp="UNVERIFIED. Call-out charges appear (E014, E037) but no amount is stated and none is framed as willingness to pay.",
  existing=[
   ("Manufacturer warranty plus installer loan units (as described by reviewers; no independent diagnostic service verified)","https://www.hellopeter.com/deye-inverters",False,"Search excerpt of Hello Peter 'Ningbo Deye' only (NPS -100, 8 reviews in 12 months; one review praises an in-warranty repair at a service centre). Not fetched."),
  ],
  solves="No evidence that it is solved: all five describe a fault that stayed unresolved after at least one repair or visit, or no action at all (E038)."),
 "battery_failure_degradation": dict(
  title="Batteries that swell, lose BMS communication or fail early",
  wtp_short="UNVERIFIED", solved_short="No (on this evidence)",
  pain="Batteries that swell or fail early and then take months to replace: one swollen 5 kWh battery with no replacement after 7 months (E015), two swollen 5 kWh batteries awaiting replacement for more than 6 months (E048), two of four batteries dead within about five years with a month-plus wait and a higher electricity bill meanwhile (E050), and a retail-bought battery with BMS problems and a refused refund (E026, Oct 2024).",
  who="C1 (3) and C2 (1); all Hello Peter; Sunsynk, Pylontech and a CFE-brand battery bought from a retailer.",
  workaround="Installer escalation and waiting; one owner bought another battery elsewhere after refusal of a refund (E026).",
  wtp="UNVERIFIED.",
  existing=[
   ("Solar Deity Pylontech repair centre (vendor claims under 7 days and a loan battery)","https://solardeity.co.za/pylontech-servicesupport/",True,"Fetched; vendor claims are unverified and not borne out by 2026 Hello Peter reviews of the brand's local warranty channel (waits of one to six-plus months)."),
   ("Consumer Protection Act s56","https://thencc.org.za/wp-content/uploads/2023/11/Explanatory-Note-7-of-2023.pdf",True,"Fetched. Six-month window only, so it does not reach failures in year 2-5."),
  ],
  solves="No on this evidence: claims were still open after 6-7 months in 2026 (E015, E048)."),
 "savings_below_expectation": dict(
  title="Owners do not see the bill fall",
  wtp_short="UNVERIFIED", solved_short="Unclear",
  pain="Owners cannot see the saving: 'still buying the same amount of unit... all I have managed to do is add an expense' (E001); a Solar Advice customer whose system 'was costing me way more money than I was paying without the oversize...' (the excerpt is cut off, E035); installer-set discharge and overnight grid-charge settings that removed the saving (E027); and a rental customer whose municipal bill treated generation as consumption, with a self-estimated overpayment of about R30,000 (E044).",
  who="C1 (3) and C3 (1); Reddit 2, Hello Peter 1, MyBroadband 1; 100% inside the last 12 months.",
  workaround="Geyser timers, an ET-12 load meter feeding the inverter or an inverter per phase (advice in E001's thread); changing settings oneself (E027); switching from post-paid to prepaid, legal advice and a CGSO complaint (E044).",
  wtp="UNVERIFIED. The R30,000 is the poster's own estimate of overpayment (stated_spend), not a willingness to pay.",
  existing=[
   ("No product verified. Commenters name geyser controllers (Geyserwise, Sonoff, CBI), the ET-12 meter and Solar Assistant / Home Assistant.","https://solar-assistant.io/",True,"Only SolarAssistant's page was fetched (see monitoring row); the others are named by commenters and not verified."),
  ],
  solves="Unclear. Fixes described are DIY and depend on owner skill; none verified as effective."),
 "workmanship_defects": dict(
  title="Installation defects with safety consequences",
  wtp_short="UNVERIFIED", solved_short="Unclear",
  pain="Defects with safety consequences: an array 'left ungrounded for over a month' causing a DC fuse to catch fire on a R159,000 job (E023); wiring that burned on installation with the repair done wrongly and tickets 'signed off as complete' (E043); a main-DB switch rated for 3-phase on a single-phase home (E005); walls left damaged and an oven and stove not working after a de-installation (E041).",
  who="C3 (3, rent/subscription customers) and C1 (1); Hello Peter 3, Reddit 1.",
  workaround="Second electricians, escalation and public warnings.",
  wtp="UNVERIFIED (R159,000 and R20,700 are amounts already paid).",
  existing=[
   ("Certificate of Compliance for the wiring (required for registration per Eskom's page)","https://www.eskom.co.za/solar-pv-registration-legal-compliance-campaign-update-act-now-stay-legal-stay-safe-eskom-continues-to-provide-up-to-r10000-assistance/",True,"Fetched. Yet E023 says the independent CoC electrician 'didn't even check the work'."),
   ("PV GreenCard as-built report and 'third party system check available'","https://pvgreencard.co.za/",True,"Fetched; no row shows an owner using it to resolve a defect."),
  ],
  solves="Unclear to no: the compliance paperwork exists, but the cited failure is that it was not checked."),
 "sseg_registration_burden": dict(
  title="Grid-registration (SSEG) is seen as costly, pointless or unenforced",
  wtp_short="Unwilling (self-selected poll)", solved_short="Not on this evidence",
  pain="Owners treat SSEG registration as costly, pointless or unenforced and many do not do it. In a MyBroadband poll (74 voters, self-selected) 45 of the 46 voters who have home solar had not registered. Owner comments: 'I tried at the time, they ignored me' (E029), 'I will rather upgrade my small system than register' (E030), 'Eskom must pay us R5000.00 to reg' (E031), 'Just don't register if you are in JHB' (E032). Two bystander Reddit comments on the August 2026 R30,000-fines story are excluded from the count.",
  who="C1 (3) and C2 (1); all forum posts from Sep-Oct 2026; 75% of the items come from one thread.",
  workaround="Do not register; fit an NRS-approved inverter and get a CoC only (advice in the same PowerForum thread as E032/E034); expand the system or go off-grid to avoid the grid (E030, E032); on Cape Town, one owner says the municipality is strict (E032) while a bystander says none of about 15 Cape Town owners they know is registered (E034, excluded).",
  wtp="Evidence points to unwillingness: no owner states a price they would pay and one expects to be paid R5,000 (E031). Eskom waived fees of up to R10,000 until 31 Mar 2026 (fetched); a waiver to 30 Sep 2026 appears only in secondary sources, and the position after 30 Sep 2026 is UNVERIFIED.",
  existing=[
   ("Eskom registration: online Customer Application Tool, fee waiver, simplified sign-off by a DoEL-registered person since 1 Oct 2025","https://www.eskom.co.za/solar-pv-registration-legal-compliance-campaign-update-act-now-stay-legal-stay-safe-eskom-continues-to-provide-up-to-r10000-assistance/",True,"Fetched (statement dated 14 Jan 2026). Municipal customers must use their municipality; penalties are described inconsistently by secondary sources (UNVERIFIED)."),
  ],
  solves="Not on this evidence. The process, tool and a fee waiver exist, yet the poll shows 45 of 46 solar owners unregistered (self-selected) and owners describe not trusting or not bothering."),
 "installer_trust_scam_fear": dict(
  title="Buyers cannot tell which installer or finance provider to trust",
  wtp_short="UNVERIFIED", solved_short="Unclear",
  pain="Buyers cannot tell which installers or finance providers to trust: 'the reviews on Hello Peter make me suspicious' (E002), 'the fine print... just seems very suspicious' (E004), and a financed customer calling the experience 'dishonest' (E036).",
  who="C3 (2) and C1 (1); Reddit 2, Hello Peter 1; 67% of the items come from the July 2026 rent-to-own thread.",
  workaround="Read Hello Peter, ask Reddit, buy outright after research (E004).",
  wtp="UNVERIFIED.",
  existing=[
   ("PV GreenCard directory of certified installation companies","https://pvgreencard.co.za/",True,"Fetched (442 companies). No owner in the sample mentions using it."),
   ("Hello Peter reviews","https://www.hellopeter.com/gosolr",True,"Fetched. The complaint is that the reviews themselves raise suspicion."),
  ],
  solves="Unclear. Both exist; whether buyers use the directory is unverified."),
}

NEXT_UP = {  # one-line gloss for the 'beyond the top 10' list
 "billing_debit_order_errors": "debits after cancellation, refunds promised but not paid (rent-to-own)",
 "coc_compliance_integrity": "CoC electrician did not check the work (E023)",
 "firmware_update_failure": "remote firmware update left a working inverter dead (E017)",
 "grid_connection_cost_delay": "R150k-R200k new grid connection avoided by going off-grid (E007)",
 "grid_voltage_issues": "high municipal voltage cited with an inverter fault (E022)",
 "municipal_billing_metering_mismatch": "municipality billed generation as consumption (E044)",
 "refund_returns_refused": "refund refused on a battery with BMS faults (E026)",
 "replacement_unit_quality": "replacement inverter was a used, different-brand unit that also failed (E025)",
 "warranty_verification_serial": "cannot verify an inverter serial/warranty; passed between ten people (E020)",
 "repeat_callout_fees": "repeat call-out/labour charges for unresolved or in-warranty faults",
 "cannot_verify_installation_quality": "owner cannot tell if the install or settings are right (E001, E057)",
 "installation_delays_lead_time": "late arrivals / slow installs",
 "installer_misconfiguration_settings": "installer-set discharge %, grid-charge or CT-clamp errors found later",
 "municipal_fixed_charge_solar_owners": "fixed municipal/connection charges that stay with solar (R1,000/month stated in E006)",
 "inverter_battery_compat_config": "inverter/battery/logger compatibility problems (C2 only)",
 "repair_downtime_no_fallback": "no power while a unit is away for repair",
 "system_overpromised_mismatch": "delivered capacity does not match what was sold",
 "warranty_claim_rejected": "claim rejected with vague reasons ('misuse')",
}


# --------------------------------------------------------------- helpers
def pct(x):
    return f"{round(x * 100)}%"


def link(row):
    return f"[{row['venue']}]({row['url']})"


def when(row):
    if row.get("date"):
        return row["date"]
    return {"strict": "last-12-months label", "extended": "24-month window (date not shown)"}.get(row.get("window_hint"), "undated")


def main():
    evidence = jl("evidence.jsonl")
    scanned = jl("scanned.jsonl")
    queries = jl("queries.jsonl")
    ctx = jl("context.jsonl")
    by_id = {e["id"]: e for e in evidence}
    res = ct.build_result(HERE, AS_OF)
    meta, rank, cov = res["meta"], res["ranking"], res["coverage"]
    assert not meta["validation_problems"], meta["validation_problems"]
    pains = rank["pains"]
    top = pains[:10]
    missing = [p["tag"] for p in top if p["tag"] not in NOTES]
    assert not missing, f"write analysis notes for: {missing}"
    window = meta["window_used"]
    strict_only = ct.tally(evidence, AS_OF, "strict")["pains"]
    top_pooled = {p["tag"] for p in top}
    top_ew = {p["tag"] for p in sorted(pains, key=lambda p: p["rank_equal_weight"])[:10]}
    top_strict = {p["tag"] for p in strict_only[:10]}
    in_win = [e for e in evidence if ct.in_window(e, AS_OF, window)]
    counted = [e for e in in_win if e["voice"] in ct.COUNTED_VOICES]
    comm_tot = collections.Counter(e["community"] for e in counted)
    n_threads = len({e["thread_key"] for e in counted})

    q_fb = [q for q in queries if "facebook" in q["query"].lower() or "facebook.com" in q["query"].lower()]
    q_x = [q for q in queries if "x.com" in q["query"].lower() or "xcancel" in q["query"].lower() or "twitter" in q["query"].lower()]
    q_tk = [q for q in queries if "takealot" in q["query"].lower()]

    L = []
    w = L.append
    w("# Solar owners in South Africa: complaint mining")
    w("")
    w(f"*Ranked pain points with demand evidence. Data as of {AS_OF.isoformat()}. Evidence fetched 2026-10-02. This is a list of what people complain about, not a list of things to build; no solutions are proposed.*")
    w("")
    w("## 1. The ranked list (top 10)")
    w("")
    w(f"Ranking basis: **{meta['window_used']}** window ({meta['strict_start'] if window == 'strict' else meta['extended_start']} to {meta['as_of']}); {rank['counted_rows']} owner/prospective evidence rows from {n_threads} distinct sources (threads/pages/app listings). Only first-hand voices count; installers/sellers and bystander opinion are logged separately ({rank['excluded_by_voice']}). **Counts are sample counts of complaint items, not prevalence among owners.**")
    w("")
    w("| # | Pain | Items (sources) | Who (C1/C2/C3) | In last 12 mo | Would pay? | Existing fix solves it? |")
    w("|---|---|---|---|---|---|---|")
    for p in top:
        n = NOTES[p["tag"]]
        cc = p["community_counts"]
        who = "/".join(str(cc.get(c, 0)) for c in ("C1", "C2", "C3"))
        flag = " ⚑" if p["concentration_flag"] else ""
        w(f"| {p['rank']} | {n['title']} | {p['count']} ({p['distinct_threads']}){flag} | {who} | {pct(p['strict_share'])} | {n['wtp_short']} | {n['solved_short']} |")
    w("")
    w("⚑ = one source supplies more than 40% of the items (see section 5). C1 = homeowners with installer-installed systems; C2 = DIY and enthusiast owners; C3 = rent-to-own / financed / subscription customers.")
    w("")
    cl = {c["cluster"]: c["distinct_rows"] for c in rank["clusters"]}
    others = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(cl.items(), key=lambda kv: -kv[1]) if k != "after_sales_and_warranty")
    w(f"**Reading it in one paragraph.** After-sales is the dominant theme: warranty repair, an unresponsive installer, repeat call-outs, replacement units and refused claims together touch {cl['after_sales_and_warranty']} of the {rank['counted_rows']} counted rows (post-hoc cluster of distinct rows; other clusters: {others}). "
      "Monitoring-app complaints rank second as a single tag but come almost entirely from one vendor app's reviews. Rent-to-own terms and exit fees are almost all C3. Grid registration (SSEG) is a live grievance voiced in forum threads, not in reviews. For willingness to pay, the honest answer for most pains is **UNVERIFIED**: people state what they already paid or were charged, rarely what they would pay to make the problem stop.")
    w("")
    w("### Top pains inside each community (owner/prospective items)")
    w("")
    w("| Community | Counted rows | Most frequent pains (items) |")
    w("|---|---|---|")
    for c in ("C1", "C2", "C3"):
        cnt = collections.Counter(t for e in counted if e["community"] == c for t in e["tags"])
        w(f"| {c} | {comm_tot[c]} | " + "; ".join(f"`{t}` ({n})" for t, n in cnt.most_common(5)) + " |")
    w("")
    w("## 2. How this was done (and where it falls short)")
    w("")
    w("**Niche:** people with solar installations in South Africa (your answer to the niche question; the brief's niche was an unfilled placeholder). **Access:** your answer to the access question was '.', so I used the stated default: use reachable sources, report real coverage, never pad. That assumption is mine.")
    w("")
    w("**Three communities** (audience segments assigned from the author's own role cues, not by venue; when a post gave no cue it defaulted to C1):")
    w("")
    w("| | Community | Why this one |")
    w("|---|---|---|")
    w("| C1 | Homeowners with installer-installed systems | The largest group; their complaints surface in reviews and Reddit. |")
    w("| C2 | DIY, self-install and enthusiast owners | Distinct vocabulary (firmware, BMS, apps, registration avoidance); active on forums. |")
    w("| C3 | Rent-to-own / financed / subscription customers | A distinct buyer with different complaints (buy-out, escalation, exit fees); heavily discussed in 2026. |")
    w("")
    w("**Tested and rejected:** *small businesses/farms* (3 searches; no usable owner complaints, only installer marketing and pre-2025 homeowner threads) and *body-corporate/estate residents* (5 SA Reddit threads, all before the window, one about solar). C3 replaced the originally planned small-business/farm community after those tests; the swap was made during collection, not in advance.")
    w("")
    w(f"**Window rule (fixed before tallying):** strict = last 12 months ({meta['strict_start']} onward). If any community has fewer than 30 scanned items in the strict window, every community is ranked on the 24-month window and each pain's strict share is shown. Strict-window scanned items were C1 {meta['scanned_items_strict']['C1']}, C2 {meta['scanned_items_strict']['C2']}, C3 {meta['scanned_items_strict']['C3']}, so **the 24-month window applies** (C2 reaches {meta['scanned_items_extended']['C2']} only on 24 months). Older items were excluded.")
    w("")
    w("**Counting rules (fixed before tallying):** owner/prospective voices only; rank by item count, tie-break on distinct sources, then community spread; flag a pain when one source supplies more than 40% of its items. A row can carry several tags and counts once per tag. `tools/complaint_tally.py` implements this with unit tests. **Added after seeing counts:** the theme clusters (interpretation only, never used for ranking). **Added before the first tally:** an equal-community-weight score, to show whether the big community drives the order.")
    w("")
    w("### Coverage: items actually read, by community and source (window used)")
    w("")
    w("| Community | Reddit | Forums | Review sites | App reviews | Facebook | X | Product reviews | Total read | Strict-window read |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for c in ("C1", "C2", "C3"):
        t = cov["table"][c]
        total = sum(t[s]["items_read"] for s in ct.SOURCE_TYPES)
        w(f"| {c} | {t['reddit']['items_read']} | {t['forum']['items_read']} | {t['review_site']['items_read']} | {t['app_review']['items_read']} | {t['facebook']['items_read']} | {t['x']['items_read']} | {t['product_review']['items_read']} | {total} | {meta['scanned_items_strict'][c]} |")
    w("")
    w("**Gaps against what you asked for:**")
    w("")
    w(f"- **Public Facebook groups: 0 items.** {len(q_fb)} searches; facebook.com returns 403 and search surfaces no usable public SA posts. A 2024 forum post confirms an active 'Sunsynk Users & Installers' group exists, but it is not publicly readable here.")
    w(f"- **Twitter/X: 0 items.** x.com returns 403; {len(q_x)} searches returned organisation accounts and articles only; the one X mirror tried (XCancel) is suspended. Two user replies under an Eskom post were questions, not complaints.")
    w(f"- **Product reviews: only app-store reviews.** One app (Sunsynk Connect, Apple App Store, South African storefront, newest 9 reviews). Takealot ({len(q_tk)} attempts: a search and a product-page fetch) shows a rating but no review text; Google Play ratings are global and cannot be verified as South African, so they are not counted.")
    w("- **Reddit and forums** were read through a public Reddit mirror and MyBroadband/PowerForum pages; many threads were read only in their first chunk, so quiet comments deeper in long threads were not seen.")
    w(f"- **Scan size:** the brief asked for 30-50 items per community. C1 ({meta['scanned_items_extended']['C1']}) and C3 ({meta['scanned_items_extended']['C3']}) exceed 50 because items are counted from whole threads/pages once opened; C2 reached {meta['scanned_items_extended']['C2']} and only on the 24-month window.")
    w("")
    w("## 3. The top 10, one by one")
    w("")
    for p in top:
        n = NOTES[p["tag"]]
        w(f"### {p['rank']}. {n['title']}")
        w("")
        w(f"`{p['tag']}` | **{p['count']} items from {p['distinct_threads']} sources** | communities {p['community_counts']} | sources {p['source_counts']} | {pct(p['strict_share'])} in the last 12 months | equal-weight rank {p['rank_equal_weight']}" + (f" | ⚑ {pct(p['top_thread_share'])} from `{p['top_thread']}`" if p['concentration_flag'] else ""))
        w("")
        w(f"- **What the pain is.** {n['pain']}")
        w(f"- **Who is complaining.** {n['who']}")
        w(f"- **What they do about it now.** {n['workaround']}")
        w(f"- **What they would pay to make it stop.** {n['wtp']}")
        ex = []
        for name, url, fetched, said in n["existing"]:
            said = re.sub(r"^(Fetched[.;,]?\s*|NOT fetched\s*)", "", said)
            ex.append(f"  - [{name}]({url}) - {'fetched ' + FETCHED if fetched else 'NOT fetched'}: {said}")
        w("- **Does an existing product or service already solve it well?** " + n["solves"])
        w("\n".join(ex))
        seen, shown = set(), []
        for i in p["evidence_ids"]:
            if by_id[i]["thread_key"] not in seen and len(shown) < 3:
                seen.add(by_id[i]["thread_key"]); shown.append(by_id[i])
        for i in p["evidence_ids"]:
            if len(shown) < 3 and by_id[i] not in shown:
                shown.append(by_id[i])
        w("- **Evidence (verbatim; ids in `evidence.jsonl`).**")
        for r in shown:
            q = r["quote"].replace("\n", " ")
            w(f"  - {r['id']} ({r['community']}, {r['voice']}, {when(r)}, {link(r)}): \"{q}\"")
        w("")
    w("## 4. Below the top 10")
    w("")
    for p in pains[10:]:
        gloss = NEXT_UP.get(p["tag"], ct_def(res, p["tag"]) if False else res["tag_definitions"].get(p["tag"], ""))
        rec = "" if p["recurring"] else " (single source)"
        w(f"- `{p['tag']}` - {p['count']} item(s){rec}: {gloss}")
    w("")
    w("## 5. Robustness: how much to trust the order")
    w("")
    w(f"- **Small numbers.** The top pain has {top[0]['count']} items; ranks 5-9 sit at 3-5 items, so differences of one item are noise. Ties were broken by the pre-set rules, not by judgement.")
    w(f"- **Equal community weight.** Pooled counts are dominated by C1 ({comm_tot['C1']} of {rank['counted_rows']} counted rows; C2 {comm_tot['C2']}, C3 {comm_tot['C3']}). On an equal-weight score the top 10 {'is the same set' if top_pooled == top_ew else 'differs: out ' + ', '.join(sorted(top_pooled - top_ew)) + '; in ' + ', '.join(sorted(top_ew - top_pooled))}.")
    w(f"- **Strict 12-month window only.** The top 10 {'is the same set' if top_pooled == top_strict else 'differs: out ' + ', '.join(sorted(top_pooled - top_strict)) + '; in ' + ', '.join(sorted(top_strict - top_pooled))} (the strict ranking is computed by the same tool).")
    w("- **Source concentration.** Flagged pains: " + ", ".join(f"`{p['tag']}` ({pct(p['top_thread_share'])} from `{p['top_thread']}`)" for p in top if p["concentration_flag"]) + ". For review sites a 'source' is the business page, so concentration there is a conservative measure.")
    w("- **Platform bias.** Review sites and app stores collect complaints by design; Reddit and forums collect advice-seeking. Counts therefore measure how often a complaint recurs among people who write, not how many owners suffer it. No count here should be read as 'X% of owners'.")
    w(f"- **Excluded voices.** {rank['excluded_by_voice']}. Bystander/installer tags that no owner row echoes: " + (", ".join(f"`{b['tag']}`" for b in rank['bystander_or_trade_tags'] if b['owner_or_prospective_items'] == 0) or "none") + ".")
    w("")
    w("### Dates")
    w("")
    basis = collections.Counter()
    for e in in_win:
        b = e["date_basis"] or ""
        if b.startswith("hp_recent"):
            basis["Hello Peter 'last 12 months' label (no per-review date seen)"] += 1
        elif b.startswith(("text_inferred", "listing_year", "attachment", "item_year", "text_today")):
            basis["inferred from text/attachment/site convention"] += 1
        elif b in ("thread", "page_age"):
            basis["thread or page date"] += 1
        else:
            basis["exact item date"] += 1
    for k, v in basis.most_common():
        w(f"- {k}: {v} rows")
    w("")
    w("## 6. What this does not show")
    w("")
    n_unv = sum(1 for p in top if NOTES[p["tag"]]["wtp_short"] == "UNVERIFIED")
    w(f"- Prevalence, market size, or willingness to pay for any improvement. Willingness to pay is **UNVERIFIED** for {n_unv} of the 10 pains; the other {10 - n_unv} have only indirect evidence: spend on a workaround (Solar Assistant, R990), sunk payments (rent-to-own R1,830/month, R20,700 exit fee) and stated unwillingness (registration).")
    w("- Anything about small businesses or farms, which could not be sampled. Anything from Facebook or X.")
    w("- Whether the ombud/legal routes work for solar disputes: only one row reports using the CGSO and no outcome is reported. This is not legal advice; the CPA reading is the National Consumer Commission's own note.")
    w("- Near-identical Hello Peter reviews were counted once (four Deye reviews with the same 'third year of a 10-year warranty' story); a cross-posted Reddit question was counted once.")
    w("- The tag taxonomy was built while collecting (definitions in `codebook.json`); one definition was broadened once (`warranty_repair_delay_runaround` now includes unhelpful agents).")
    w("")
    w("## 7. Existing-solution register")
    w("")
    w("| Kind | Page | Fetched? | What it says / status |")
    w("|---|---|---|---|")
    for c in ctx:
        if c["kind"] in ("verified_solution", "vendor_claim", "secondary"):
            fetched = "yes, " + c["retrieved"] if c["fact"].startswith("FETCHED") else "no"
            fact = c["fact"].replace("FETCHED. ", "").replace("NOT FETCHED ", "").replace("|", "/")
            w(f"| {c['kind']} | {c['url']} | {fetched} | {fact[:330]}{'...' if len(fact) > 330 else ''} |")
    w("")
    w("## 8. Files and how to reproduce")
    w("")
    w("- `research/solar-complaint-mining/evidence.jsonl` - one row per complaint-bearing item (verbatim quote <= 320 chars, community, voice, date and date basis, tags, spend, workaround). No usernames or personal names (POPIA).")
    w("- `scanned.jsonl` (items read per page/thread), `queries.jsonl` (every search/fetch attempt), `context.jsonl` (ratings, official statements, WTP signals; never counted), `codebook.json` (tag definitions, post-hoc clusters), `tally.json` / `tally.md` (tool output).")
    w("- `python3 tools/complaint_tally.py --dir research/solar-complaint-mining --as-of 2026-10-02 --out-json research/solar-complaint-mining/tally.json --out-md research/solar-complaint-mining/tally.md --strict`")
    w("- `python3 research/solar-complaint-mining/make_report.py` regenerates this file; `python3 -m unittest discover -s tests` runs the tests.")
    w("")
    return "\n".join(L) + "\n"


def ct_def(res, tag):  # kept tiny; definitions come from the codebook
    return res["tag_definitions"].get(tag, "")


if __name__ == "__main__":
    text = main()
    with open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote REPORT.md", len(text.split()), "words")
