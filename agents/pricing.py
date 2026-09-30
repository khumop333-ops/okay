"""Pricing agent — capabilities #1 (build) and #2 (mr-0002 verdict). v1.1.0.

Scope of THIS capability (README section 9 Phase 1+: one capability, one
PR, smallest verifiable output):
  * Read shared_state.json and report pricing readiness: what is verified
    (duty lines, competitor price points) and what is missing (supplier
    costs — Sourcing halted at so-0002 with ZERO verified suppliers).
  * Compute the ONLY pricing output that is publishable without supplier
    quotes: the maximum-allowable product+shipping cost (break-even) that
    still clears a target net margin at verified competitive price
    points. All math is imported from tools/landed_cost.py and
    tools/customs.py — this module computes nothing inline (README
    section 6; session brief HARD STOP: never compute landed cost inline).
  * Append findings to the ``pricing`` namespace ONLY (README section 7;
    schema section 3): own namespace, append-only, every entry with
    timestamp/agent/confidence/source, UNVERIFIED fields flagged.

What this module must NEVER grow into (README section 3):
  * sourcing, listing, advertising or any other agent's namespace;
  * direct-to-human recommendations — findings go to the state file for
    the Supervisor (README section 2 HARD STOP #5);
  * guessed supplier costs — none exist in state, so no accept/reject
    margin verdict is issued this session (HARD STOP #2). The verdict
    recorded here is "blocked", which is honest, not evasive.

CLI (offline, standard library only):
    python3 agents/pricing.py                 # dry run: print findings
    python3 agents/pricing.py --write         # append to shared_state.json
    python3 agents/pricing.py --state PATH    # alternate state file

See tests/test_pricing_agent.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

if __package__ in (None, ""):  # run as a script: make the repo root importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import customs, landed_cost  # noqa: E402

__version__ = "1.1.0"

AGENT = "pricing"
SAST = timezone(timedelta(hours=2))

#: Current SA duty + VAT module versions, stamped into every finding.
MODULES = customs.module_versions  # "tools/landed_cost.py vX, tools/customs.py vY"


def now_iso() -> str:
    """ISO-8601 timestamp in SAST (+02:00), matching the rest of state."""
    return datetime.now(SAST).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# State I/O — read anything, write ONLY the pricing namespace
# ---------------------------------------------------------------------------


def default_state_path() -> Path:
    return Path(__file__).resolve().parent.parent / "shared_state.json"


def load_state(path: Path) -> Dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump_state(state: Dict) -> str:
    """Serialise matching the existing file's formatting (indent 2, UTF-8,
    no trailing newline) so unchanged regions produce no diff noise."""
    return json.dumps(state, indent=2, ensure_ascii=False)


def finding(state: Dict, namespace: str, finding_id: str) -> Optional[Dict]:
    for entry in state.get(namespace, {}).get("findings", []):
        if entry.get("id") == finding_id:
            return entry
    return None


# ---------------------------------------------------------------------------
# Readiness: what can pricing actually do today?
# ---------------------------------------------------------------------------


def _iter_verified_unit_costs(node, inherited_verified: bool):
    """Yield (key, value) for numeric unit-cost fields that are VERIFIED.

    Recurses into nested structures because real quotes nest (so-0003
    carries a ``suppliers`` array, each entry with its own ``verified``
    flag). Two rules keep this from laundering a guess into an audit:

      * a field whose name starts with ``UNVERIFIED_`` is never counted,
        whatever it contains (schema section 4); and
      * a value only counts when the element holding it — or a parent, for
        the finding-level flag — is explicitly ``verified: true``.
    """
    if isinstance(node, dict):
        own = node.get("verified")
        verified = inherited_verified if own is None else own is True
        for key, val in node.items():
            if (
                isinstance(val, (int, float))
                and not isinstance(val, bool)
                and "unit_cost" in key.lower()
                and not key.upper().startswith("UNVERIFIED_")
            ):
                if verified:
                    yield key, float(val)
            else:
                yield from _iter_verified_unit_costs(val, verified)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_verified_unit_costs(item, inherited_verified)


def verified_supplier_costs(state: Dict) -> List[str]:
    """Finding ids that carry at least one VERIFIED numeric unit cost.

    Empty means no verified supplier cost exists anywhere in state. This is
    an audit, not a guess: it reports what state actually contains, so the
    Supervisor can see when Sourcing has moved on from a halt record.
    """
    verified: List[str] = []
    for ns in ("market_research", "sourcing", "pricing"):
        for entry in state.get(ns, {}).get("findings", []):
            found = list(
                _iter_verified_unit_costs(
                    entry.get("data", {}), entry.get("verified") is True
                )
            )
            if found and entry.get("id") not in verified:
                verified.append(entry["id"])
    return verified


def readiness_report(state: Dict) -> Dict:
    """What the pricing namespace can and cannot do right now."""
    mr_lead = finding(state, "market_research", "mr-0002")
    sourcing = state.get("sourcing", {})
    halt_ids = [
        f["id"]
        for f in sourcing.get("findings", [])
        if "HALTED" in json.dumps(f.get("data", {}).get("routing_decision", ""))
    ]
    halted = bool(halt_ids)
    cost_ids = verified_supplier_costs(state)
    # A halt record is history, not necessarily the current state: Sourcing
    # delivered quotes in later findings (so-0003/so-0004). Say both.
    later = [
        f["id"]
        for f in sourcing.get("findings", [])
        if halt_ids and f["id"] > halt_ids[-1]
    ]
    if cost_ids:
        conclusion = (
            f"{len(cost_ids)} finding(s) carry VERIFIED supplier unit costs "
            f"({', '.join(cost_ids)}), so accept/reject margin verdicts are "
            "now possible on those inputs (see pricing pr-0005/pr-0006). "
            "Approvals remain blocked where shipping, platform fees or "
            "classification are still UNVERIFIED — read the namespace's "
            "unverified_fields before acting."
        )
    else:
        conclusion = (
            "NO accept/reject margin verdict is possible: zero verified "
            "supplier costs exist. Publishable today: maximum-allowable-cost "
            "break-evens from verified duty + competitor prices + the "
            "README CPA band."
        )
    return {
        "verified_duty_lines": sorted(customs.VERIFIED_DUTY_LINES.keys()),
        "verified_supplier_costs": cost_ids,
        "sourcing_halted": halted,
        "sourcing_halt_findings": halt_ids,
        "sourcing_findings_after_halt": later,
        "sourcing_status": (
            "halt record exists ("
            + ", ".join(halt_ids)
            + ") and later sourcing findings "
            + ("exist: " + ", ".join(later) if later else "do not exist")
            if halted
            else "no halt record in state"
        ),
        "lead_candidate": (
            mr_lead["data"]["product_name"] if mr_lead else None
        ),
        "lead_duty_rate_pct": (
            mr_lead["data"].get("duty_rate_pct") if mr_lead else None
        ),
        "conclusion": conclusion,
    }


# ---------------------------------------------------------------------------
# Break-even table for the routed lead (mr-0002 solar power bank)
# ---------------------------------------------------------------------------
# Inputs below are the ONLY real numbers available, each cited. No supplier
# cost appears anywhere — the table computes the ceiling Sourcing must
# quote under. Worst-case assumptions per session brief: payment fee 5%,
# return rate 10%. platform_fees 0 is an UNVERIFIED placeholder and makes
# every ceiling an OPTIMISTIC upper bound (a real marketplace fee would
# lower it) — flagged in pr-0003, never hidden.

MR0002_PRICE_POINTS = [
    {
        "label": "10,000mAh floor (Takealot PLID92826531)",
        "price_zar": 258.0,
        "source": (
            "shared_state mr-0002 takealot_evidence; re-corroborated this "
            "session: takealot.com/PLID92826531 shows R258"
        ),
        "corroborated_this_session": True,
    },
    {
        "label": "10,000mAh band top (mr-0002 evidence)",
        "price_zar": 344.0,
        "source": "shared_state mr-0002 takealot_evidence ('10k mAh R258-344')",
        "corroborated_this_session": False,
    },
    {
        "label": "20,000mAh foldable solar (Takealot PLID95695632 page)",
        "price_zar": 699.0,
        "source": (
            "shared_state mr-0002 takealot_evidence; re-corroborated this "
            "session: PLID95695632 page shows the 20,000mAh foldable at R699"
        ),
        "corroborated_this_session": True,
    },
]

CPA_POINTS_ZAR = [
    {"cpa_zar": 150.0, "source": "README section 4 benchmark floor"},
    {"cpa_zar": 300.0, "source": "README section 4 benchmark ceiling"},
]

TARGET_MARGINS_PCT = [
    {"pct": 20.0, "label": "HARD STOP floor (reject below)"},
    {"pct": 25.0, "label": "Pricing minimum for accept"},
    {"pct": 35.0, "label": "target band lower edge"},
]


def build_break_even_rows() -> List[Dict]:
    """Break-even ceilings via tools/landed_cost.py — no inline math."""
    rows: List[Dict] = []
    for point in MR0002_PRICE_POINTS:
        for cpa in CPA_POINTS_ZAR:
            for target in TARGET_MARGINS_PCT:
                res = landed_cost.max_customs_base_for_margin(
                    selling_price_zar=point["price_zar"],
                    duty_rate_pct=0.0,  # HS 8507.60, verified by mr-0002
                    ad_cpa_zar=cpa["cpa_zar"],
                    target_margin_pct=target["pct"],
                    payment_fee_pct=landed_cost.PAYMENT_FEE_PCT_WORST_CASE,
                    platform_fees_zar=0.0,  # UNVERIFIED placeholder — flagged
                    return_rate_pct=landed_cost.RETURN_RATE_WORST_CASE_PCT,
                )
                rows.append(
                    {
                        "price_point": point["label"],
                        "price_zar": point["price_zar"],
                        "price_source": point["source"],
                        "price_corroborated_this_session": point[
                            "corroborated_this_session"
                        ],
                        "ad_cpa_zar": cpa["cpa_zar"],
                        "target_net_margin_pct": target["pct"],
                        "target_label": target["label"],
                        "max_product_plus_shipping_zar": res[
                            "max_customs_base_zar"
                        ],
                        "feasible": res["feasible"],
                        "formula": res["formula"],
                    }
                )
    return rows


# ---------------------------------------------------------------------------
# Findings — pr-0001..pr-0003 (schema section 3: append-only, pr- prefix)
# ---------------------------------------------------------------------------


def build_findings(ts: str) -> List[Dict]:
    rows = build_break_even_rows()

    pr_0001 = {
        "id": "pr-0001",
        "timestamp": ts,
        "agent": AGENT,
        "confidence": 9,
        "source": (
            f"{MODULES()}; README sections 2, 4, 6; session brief cost model; "
            "sandbox tests tests/test_customs.py + tests/test_landed_cost.py "
            "+ tests/test_pricing_agent.py (all pass)"
        ),
        "verified": True,
        "data": {
            "record_type": "capability",
            "task": (
                "Pricing capability #1: build tools/customs.py v1.0.0 + "
                "tools/landed_cost.py v1.0.0 (the ONLY cost-math modules, "
                "README section 6) + agents/pricing.py orchestration + "
                "unittest suites; append first pricing findings. ONE PR."
            ),
            "formula_implemented": landed_cost.FORMULA_TEXT,
            "contract_constants": {
                "vat_rate_on_customs_value": customs.VAT_RATE,
                "payment_fee_pct_of_selling_price": list(
                    landed_cost.PAYMENT_FEE_PCT_RANGE
                ),
                "hard_floor_net_margin_pct": (
                    landed_cost.HARD_FLOOR_NET_MARGIN_PCT
                ),
                "min_net_margin_pct_for_accept": (
                    landed_cost.MIN_NET_MARGIN_PCT
                ),
                "target_net_margin_band_pct": list(
                    landed_cost.TARGET_NET_MARGIN_BAND_PCT
                ),
                "ad_cpa_benchmark_zar": list(landed_cost.AD_CPA_RANGE_ZAR),
                "return_rate_pct": list(landed_cost.RETURN_RATE_RANGE_PCT),
                "impulse_multiplier": list(
                    landed_cost.PRICE_MULTIPLIERS["impulse"]
                ),
                "considered_multiplier": list(
                    landed_cost.PRICE_MULTIPLIERS["considered"]
                ),
                "competitor_band_of_median": (
                    landed_cost.COMPETITOR_BAND_DEFAULT
                ),
            },
            "verdict_integrity_rule": (
                "evaluate_pricing() returns verdict='blocked' unless the "
                "caller asserts inputs_verified=true; a margin from guessed "
                "costs is never published as accept/reject (HARD STOP #2, "
                "schema section 4)."
            ),
            "brief_vs_state_reconciliations": [
                "Brief assumed tools/landed_cost.py + tools/customs.py "
                "already exist: they did not (Phase 0 excluded them "
                "deliberately; MR routed this build to Pricing). Building "
                "them IS this session's one capability.",
                "Brief asked for 'verified supplier costs' from state: none "
                "exist (so-0002: Sourcing halted, zero verified suppliers). "
                "HARD STOP #2 forbids inventing them, so NO product margin "
                "verdict is issued this session; break-even ceilings (which "
                "need no supplier quote) are delivered instead.",
                "Brief output format (verdict accept|reject per product) vs "
                "no verified costs: verdict='blocked' recorded with "
                "block_reason; the accept|reject schema is implemented in "
                "evaluate_pricing() and will be used when Sourcing delivers "
                "verified quotes.",
                "VAT is on the customs value (product + shipping), never the "
                "retail price — calculate_vat() takes no rate override so "
                "HARD STOP #4 cannot be bypassed by a caller.",
            ],
            "hitl_gate_5_status": (
                "CROSSED-BY-BUILD: this PR adds pricing/customs logic, which "
                "is HITL gate 5 territory. Human approval requested in the "
                "PR description; nothing merges without APPROVED."
            ),
        },
    }

    pr_0002 = {
        "id": "pr-0002",
        "timestamp": ts,
        "agent": AGENT,
        "confidence": 7,
        "source": (
            f"{MODULES()}; duty 0% per shared_state mr-0002 (HS 8507.60); "
            "price points R258/R344/R699 per mr-0002 takealot_evidence "
            "(R258 and R699 re-corroborated this session against live "
            "Takealot pages); CPA R150-R300 per README section 4"
        ),
        "verified": False,
        "data": {
            "record_type": "break_even_analysis",
            "product": (
                "Solar power bank 10,000-20,000 mAh (mr-0002 — MR lead for "
                "pricing, NOT APPROVED; approval sits at HITL gate 3)"
            ),
            "method": (
                "Inverse landed-cost math (tools/landed_cost.py:"
                "max_customs_base_for_margin). Asks: at a verified "
                "competitive price, what is the MAXIMUM product+shipping "
                "cost that still clears a target net margin? Needs no "
                "supplier quote, so it violates no HARD STOP. Worst-case "
                "assumptions: payment fee 5% of selling price, return rate "
                "10% (zero salvage). platform_fees=0 is an UNVERIFIED "
                "placeholder — real marketplace fees would LOWER every "
                "ceiling below, so treat ceilings as optimistic upper "
                "bounds."
            ),
            "break_even_rows": rows,
            "reading": [
                "At the R258 floor (10k units), even a ZERO-cost product "
                "cannot clear the 25% accept minimum at CPA R300; at CPA "
                "R150 the 25% minimum needs product+shipping under ~R4 and "
                "even the 20% HARD-STOP floor needs it under ~R15. The "
                "commodity 10k segment is near-certainly unviable.",
                "At R344, the ceiling is ~R49 (25% target, CPA R150) — "
                "still below any realistic landed solar-bank cost.",
                "Only the R699 20,000mAh foldable segment leaves realistic "
                "room: ceiling ~R234 at 25%/CPA150, ~R104 at 25%/CPA300, "
                "~R173 at the 35% target at CPA R150.",
                "Sourcing routing request: any supplier quote for this "
                "lead must be DDP-to-SA and BELOW these ceilings for its "
                "segment, with the quote document cited — else Pricing "
                "will reject on margin.",
            ],
            "verdict": "blocked",
            "block_reason": (
                "HARD STOP #2 + so-0002: zero verified supplier costs "
                "exist, so no landed cost, selling price or accept/reject "
                "margin verdict can be computed without inventing inputs. "
                "Blocked, not rejected: the product is not being failed on "
                "margin — margin math is impossible until Sourcing delivers "
                "verified quotes."
            ),
            "UNVERIFIED_supplier_cost_zar": None,
        },
    }

    pr_0003 = {
        "id": "pr-0003",
        "timestamp": ts,
        "agent": AGENT,
        "confidence": 8,
        "source": (
            "shared_state.json market_research mr-0001/mr-0002/mr-0004/"
            "mr-0007 + so-0002 halt record; README section 4 formula vs "
            "SARS ATV method (flagged by MR, mr-0027 contract_conflicts "
            "item 6)"
        ),
        "verified": False,
        "data": {
            "record_type": "escalations_and_routing",
            "routed_candidates_blocked": [
                {
                    "id": "mr-0002",
                    "product": "Solar power bank",
                    "blocker": "no verified supplier cost (so-0002)",
                },
                {
                    "id": "mr-0001",
                    "product": "USB-C GaN charger + cable",
                    "blocker": (
                        "no verified supplier cost; additionally the "
                        "charger+cable composite-GRI classification is "
                        "UNVERIFIED (bundle rated at cable 15% "
                        "conservatively) — Sourcing must confirm before "
                        "any margin run"
                    ),
                },
                {
                    "id": "mr-0007",
                    "product": "Plastic phone case",
                    "blocker": (
                        "no verified supplier cost; MR file flags R67 "
                        "floor far below CPA — likely margin reject once "
                        "costs exist"
                    ),
                },
                {
                    "id": "mr-0004",
                    "product": "Car phone holder",
                    "blocker": (
                        "no verified supplier cost; MR file flags R114 "
                        "floor below CPA — likely margin reject once "
                        "costs exist"
                    ),
                },
            ],
            "atv_formula_discrepancy_DECISION_REQUESTED": {
                "issue": (
                    "README section 4 charges VAT as customs_value x 0.15. "
                    "SARS' ATV method for non-SACU consignments charges "
                    "15% on (customs value + duty + 10% uplift). The two "
                    "disagree; MR flagged it for the Supervisor before the "
                    "tool was built (mr-0027)."
                ),
                "action_taken": (
                    "tools/customs.py implements the README contract "
                    "formula EXACTLY (README section 1: the README wins "
                    "conflicts). The SARS method is NOT implemented."
                ),
                "risk": (
                    "If SARS' method is the legally correct one, every "
                    "landed cost in this tool UNDERSTATES VAT, inflating "
                    "every margin — the worst possible direction for a "
                    "margin gate. Quantified: on a R100 customs value at "
                    "10% duty, README VAT = R15.00 vs ATV VAT = R18.15 "
                    "(+21% VAT, +R3.15 landed per R100)."
                ),
                "request": (
                    "Supervisor/human to decide BEFORE any verdict-bearing "
                    "margin run: keep README formula (contract-consistent) "
                    "or amend README + tool to the ATV method (HITL gate 5 "
                    "+ README amendment). This agent does not pick."
                ),
            },
            "platform_fees_UNVERIFIED": (
                "Net margin per the brief subtracts 'Platform Fees'. No "
                "verified Takealot/marketplace fee schedule exists in "
                "state; the parameter defaults to R0 which OVERSTATES "
                "margin. Must be sourced before any accept verdict is "
                "treated as final."
            ),
            "competitor_median_note": (
                "MR evidence provides named Takealot price points/floors "
                "with PLIDs, not a computed category median. This session "
                "uses named price points, never a fabricated median; a "
                "real median needs the Takealot browsing fix noted in "
                "so-0002/mr method_limits."
            ),
        },
    }

    return [pr_0001, pr_0002, pr_0003]


def apply_findings(state: Dict, findings: List[Dict], ts: str) -> Dict:
    """Append findings to the pricing namespace ONLY and refresh its
    write metadata (schema sections 2-3). Refuses to touch any other
    namespace or any ``_``-prefixed key."""
    ns = state["pricing"]
    existing_ids = {f.get("id") for f in ns.get("findings", [])}
    for f in findings:
        if f["id"] in existing_ids:
            raise ValueError(f"{f['id']} already in pricing.findings")
        ns["findings"].append(f)
    confidences = [f["confidence"] for f in ns["findings"]]
    ns["timestamp"] = ts
    ns["agent"] = AGENT
    ns["confidence"] = min(confidences)
    ns["source"] = (
        f"{MODULES()}; {len(ns['findings'])} findings appended this session "
        f"(pr-0001..pr-{len(ns['findings']):04d}); namespace roll-up takes "
        "the minimum finding confidence (conservative)"
    )
    ns["verified"] = all(f["verified"] for f in ns["findings"])
    extra = [
        "Supplier unit costs for ALL candidates remain UNVERIFIED (so-0002 "
        "halt) — no landed cost or accept/reject margin verdict possible "
        "until Sourcing delivers cited, DDP-to-SA quotes.",
        "platform_fees_zar (Takealot/marketplace fee schedule) UNVERIFIED — "
        "defaults to 0, which overstates margin; source before any accept.",
        "VAT base discrepancy (README customs_value x 0.15 vs SARS ATV "
        "(value + duty + 10% uplift) x 15%) — decision requested in "
        "pr-0003 BEFORE any verdict-bearing margin run.",
        "Competitor 'median' prices: MR evidence gives named price points "
        "with PLIDs, not a computed median — named points used, never an "
        "invented median.",
        "mr-0001 charger+cable composite-GRI classification UNVERIFIED "
        "(carried from mr-0001) — confirm before margin runs on bundles.",
        # --- capability #2 (mr-0002 verdict session) ---
        "mr-0002 shipping_to_sa_zar per unit: NO supplier displayed an SA "
        "lane or DDP (so-0003/so-0005). Every pr-0006 block carries "
        "UNVERIFIED_shipping_to_sa_zar = R161.83, the only figure fetched "
        "anywhere (Coremax Standard $19.80/2 boxes, destination country "
        "UNVERIFIED), and R0 is a mathematical bound only. No combination "
        "in pr-0005 is approvable until a DDP-to-SA per-unit quote exists.",
        "platform_fees_zar remains UNVERIFIED (pr-0003): pr-0005/pr-0006 "
        "compute BOTH R0 and R30/order and both are assumptions — "
        "UNVERIFIED_platform_fees_zar is recorded per block, not a sourced "
        "fee schedule.",
        "Competitor price point for the 20,000mAh segment is a single named "
        "Takealot point (PLID95695632, R699), not a computed category "
        "median — UNVERIFIED_competitor_median_price_zar is null in every "
        "pr-0006 block, and the R299/R338 cluster is 10,000mAh evidence "
        "(segment mismatch recorded in pr-0005).",
        "SARS PRIMARY line-level reading for 8507.60 is still unread (two "
        "agreeing secondary sources + SARS corroboration of the heading), "
        "and the 8541.43 composite alternative remains a source defect. "
        "Both can only RAISE duty, so they cannot rescue the pr-0006 "
        "reject.",
        "The SARS ATV VAT basis is UNAPPROVED pending HITL gate 5 (pr-0004): "
        "the 'atv' cells in pr-0005 are sensitivity only, and "
        "tools/landed_cost.evaluate_pricing() refuses that basis, so no "
        "verdict rests on it.",
        "mr-0002 volume tiers are not usable as entry prices: the >=500-box "
        "Coremax tier (R68.49) has UNVERIFIED box contents, and Quark's "
        "displayed tiers are UNVERIFIED as to 10,000 vs 20,000mAh variant. "
        "Only entry-MOQ prices feed the pr-0005 matrix.",
    ]
    for line in extra:
        if line not in ns["unverified_fields"]:
            ns["unverified_fields"].append(line)
    return state


# ---------------------------------------------------------------------------
# Capability #2 — formal verdict on mr-0002 (20,000mAh solar power bank)
# ---------------------------------------------------------------------------
# Session task: margin at R299 / R338 / R449 / R599, for the six supplier
# quotes in so-0003/so-0004/so-0005, at CPA R150 and R300, with platform fees
# computed BOTH at R0 and at a conservative R30/order (pr-0003: no sourced
# fee schedule exists), and with the SARS ATV VAT basis as well as the README
# contract basis.
#
# BRIEF CORRECTIONS (checked against state, not assumed):
#   * so-0003/so-0004/so-0005 carry SIX quotes but only THREE are mr-0002.
#     so-0004's three quotes are for mr-0003 (LED emergency light,
#     HS 8513.10, duty rate UNVERIFIED in state) — a different product on an
#     unverified duty line. Using them for mr-0002 margin math would be a
#     category error, so they are excluded and the exclusion is recorded.
#   * The R299-R338 "market cluster" is 10,000mAh evidence (mr-0002
#     takealot_evidence: 10k mAh R258-R344). The quotes are all 20,000mAh
#     units, whose observed Takealot point is R699 (PLID95695632). The task's
#     price points are therefore computed as instructed, but the mAh mismatch
#     is a real finding and is recorded, not buried.
#
# All math below is IMPORTED from tools/landed_cost.py + tools/customs.py.
# This module performs no arithmetic of its own beyond band labelling.

MR0002_QUOTES = [
    {
        "key": "coremax_entry",
        "label": "Guangzhou Coremax — entry tier, 2-99 boxes",
        "supplier": "Guangzhou Coremax New Energy Technology Co., Ltd.",
        "platform": "Alibaba",
        "unit_cost_zar": 86.80,
        "unit_cost_usd": 5.31,
        "moq": 2,
        "source": (
            "so-0003 quote 2; $5.31 live discounted entry tier x 16.3460 "
            "(Google Finance USD/ZAR 2026-09-30 07:33 UTC)"
        ),
        "verified": True,
        "caveats": (
            "'boxes' unit not defined on the fetched page (single package "
            "= 1 item, 1.0 kg gross) — box contents UNVERIFIED; DDP-to-SA NOT "
            "offered (taxes calculated at checkout)"
        ),
    },
    {
        "key": "aliexpress_retail",
        "label": "AliExpress retail listing, MOQ 1",
        "supplier": "AliExpress store (store name UNVERIFIED — JS-gated page)",
        "platform": "AliExpress",
        "unit_cost_zar": 168.53,
        "unit_cost_usd": 10.31,
        "moq": 1,
        "source": (
            "so-0003 quote 1; item 3256811681367819 displayed promo price "
            "$10.31 x 16.3460 (same FX); list price struck at $57.62 (-82%)"
        ),
        "verified": True,
        "caveats": (
            "promo price (struck-through list $57.62); no SA lane rendered; "
            "no DDP; single-unit retail so no volume tier"
        ),
    },
    {
        "key": "quark_entry",
        "label": "Shenzhen Quark Thinking — entry tier, 2-99 pieces",
        "supplier": "Shenzhen Quark Thinking Technology Co., Ltd.",
        "platform": "Alibaba",
        "unit_cost_zar": 171.63,
        "unit_cost_usd": 10.50,
        "moq": 2,
        "source": (
            "so-0003 quote 3; $10.50 entry tier x 16.3460 (same FX). Best "
            "verifiable reliability profile of the three (4 yrs, 5/5 on 63 "
            "reviews, <=1h response, 85.7% on-time)"
        ),
        "verified": True,
        "caveats": (
            "which capacity variant the displayed tiers apply to is "
            "UNVERIFIED (10,000 / 20,000mAh both listed); NO shipping quote "
            "rendered at all ('to be negotiated')"
        ),
    },
]

#: Deep-tier alternative for Coremax, kept OUT of the primary matrix: it
#: requires a >=500-box commitment AND the box-per-item basis is UNVERIFIED.
MR0002_DEEP_TIER_SCENARIO = {
    "key": "coremax_deep_tier",
    "unit_cost_zar": 68.49,
    "unit_cost_usd": 4.19,
    "requires": ">=500 boxes",
    "source": "so-0003 quote 2, >=500-box tier x 16.3460",
    "why_excluded_from_primary_matrix": (
        "box contents UNVERIFIED (could be multi-unit) and no verified "
        "demand for a 500-unit commitment; shown only as the cheapest "
        "fetched unit cost, never as a purchasable entry price"
    ),
}

#: "Cheapest usable" = cheapest VERIFIED per-unit price that is actually
#: purchasable at the supplier's stated entry MOQ (no bulk commitment
#: assumed). Deep tiers and unverified pack bases are excluded by definition.
MR0002_CHEAPEST_USABLE_QUOTE_KEY = "coremax_entry"

MR0002_SESSION_PRICE_POINTS = [
    {
        "price_zar": 299.0,
        "label": "R299 — market cluster low end (session brief)",
        "segment_evidence": (
            "mr-0002 takealot_evidence puts R258-R344 on 10,000mAh units; "
            "R299 sits inside that band"
        ),
        "mAh_match_to_quotes": False,
    },
    {
        "price_zar": 338.0,
        "label": "R338 — market cluster high end (session brief)",
        "segment_evidence": (
            "mr-0002 takealot_evidence: 10k mAh band tops out at R344"
        ),
        "mAh_match_to_quotes": False,
    },
    {
        "price_zar": 449.0,
        "label": "R449 — stretch pricing (session brief)",
        "segment_evidence": (
            "above the 10k band, still below the R699 20,000mAh Takealot "
            "point (PLID95695632) re-corroborated in pr-0002"
        ),
        "mAh_match_to_quotes": True,
    },
    {
        "price_zar": 599.0,
        "label": "R599 — premium, above the cluster (session brief)",
        "segment_evidence": (
            "14% below the observed R699 20,000mAh Takealot point; inside "
            "the 10-15% competitor band of that point"
        ),
        "mAh_match_to_quotes": True,
    },
]

MR0002_CPA_CASES_ZAR = [150.0, 300.0]

#: pr-0003: no sourced marketplace fee schedule exists in state. The session
#: brief mandates BOTH cases so the assumption is visible in every verdict.
MR0002_PLATFORM_FEE_CASES_ZAR = [
    {
        "zar": 0.0,
        "label": "R0 — UNVERIFIED placeholder (flatters the margin)",
        "sourced": False,
    },
    {
        "zar": 30.0,
        "label": (
            "R30/order — conservative stress test supplied by the session "
            "brief; NOT a sourced fee schedule"
        ),
        "sourced": False,
    },
]

#: Shipping is the biggest hole in this analysis: NO mr-0002 supplier has a
#: verified SA-lane shipping cost (so-0003/so-0005: no DDP, no SA lane, RFQ
#: required). Rather than invent one, both ends of the observable range are
#: computed, plus the break-even shipping ceiling for every combination.
MR0002_SHIPPING_SCENARIOS = [
    {
        "key": "ship0",
        "shipping_zar": 0.0,
        "label": (
            "R0 — mathematical bound only, physically impossible for a "
            "1.0 kg lithium unit from China"
        ),
        "approvable": False,
        "why": (
            "included to prove robustness: if a combination fails here it "
            "fails at every real shipping cost"
        ),
    },
    {
        "key": "ship_fetched",
        "shipping_zar": 161.83,
        "label": (
            "R161.83/unit — the ONLY shipping figure fetched anywhere in "
            "so-0003: Coremax Standard (Alibaba.com Logistics) $19.80 for "
            "2 boxes, guaranteed window Oct 11 - Nov 19"
        ),
        "approvable": False,
        "why": (
            "destination country UNVERIFIED in the fetch and box=1 item "
            "UNVERIFIED, so this is an indicative upper-end datapoint, not "
            "a per-unit SA lane quote"
        ),
    },
]

VAT_BASIS_CASES = [
    {
        "key": "readme",
        "vat_basis": customs.VAT_BASIS_README,
        "verdict_bearing": True,
        "label": "README section 4 contract formula: VAT = 15% x customs value",
    },
    {
        "key": "atv",
        "vat_basis": customs.VAT_BASIS_SARS_ATV,
        "verdict_bearing": False,
        "label": (
            "SARS ATV method: VAT = 15% x (customs value + duty + 10% "
            "uplift) — UNAPPROVED, HITL gate 5 + README amendment required "
            "(pr-0003/pr-0004); sensitivity only, never a verdict"
        ),
    },
]


def band_verdict(net_margin_pct: float) -> str:
    """Session-brief verdict banding: >=25 accept / 20-25 investigate / <20 reject.

    Thresholds are taken from tools/landed_cost.py constants, never
    re-typed here. NOTE the deliberate difference from
    landed_cost.verdict_for_margin(): the tool never returns "investigate" —
    below 25% it is simply not an approval (the 20-25% band is an escalation,
    not an accept). Both labels are recorded for every cell.
    """
    if net_margin_pct >= landed_cost.MIN_NET_MARGIN_PCT:
        return "accept"
    if net_margin_pct >= landed_cost.HARD_FLOOR_NET_MARGIN_PCT:
        return "investigate"
    return "reject"


def _quote_by_key(key: str) -> Dict:
    for quote in MR0002_QUOTES:
        if quote["key"] == key:
            return quote
    raise KeyError(key)


def evaluate_combination(
    quote: Dict,
    price_zar: float,
    ad_cpa_zar: float,
    platform_fees_zar: float,
    shipping_zar: float,
    vat_basis: str,
) -> Dict:
    """One cell: landed cost + net margin + both verdict labels.

    Every number comes from tools/landed_cost.py; nothing is computed here.
    """
    breakdown = landed_cost.calculate_landed_cost(
        product_cost_zar=quote["unit_cost_zar"],
        shipping_to_sa_zar=shipping_zar,
        duty_rate_pct=customs.lookup_duty_rate_pct("8507.60"),
        selling_price_zar=price_zar,
        payment_fee_pct=landed_cost.PAYMENT_FEE_PCT_WORST_CASE,
        vat_basis=vat_basis,
    )
    margin = landed_cost.net_margin(
        selling_price_zar=price_zar,
        total_landed_cost_zar=breakdown["total_landed_cost_zar"],
        ad_cpa_zar=ad_cpa_zar,
        platform_fees_zar=platform_fees_zar,
        return_rate_pct=landed_cost.RETURN_RATE_WORST_CASE_PCT,
    )
    return {
        "total_landed_cost_zar": breakdown["total_landed_cost_zar"],
        "vat_zar": breakdown["vat_zar"],
        "payment_fees_zar": breakdown["payment_fees_zar"],
        "net_margin_zar": margin["net_margin_zar"],
        "net_margin_pct": margin["net_margin_pct"],
        "band_verdict": band_verdict(margin["net_margin_pct"]),
        "tool_verdict": landed_cost.verdict_for_margin(
            margin["net_margin_pct"]
        )["verdict"],
    }


def max_shipping_for_margin(
    quote: Dict,
    price_zar: float,
    ad_cpa_zar: float,
    platform_fees_zar: float,
    target_margin_pct: float,
    vat_basis: str,
) -> Optional[float]:
    """Max SA shipping/unit that still clears ``target_margin_pct``.

    Inverse math via tools/landed_cost.py:max_customs_base_for_margin, minus
    the product cost. None (not 0) when the product cost ALONE already
    exceeds the ceiling — i.e. no shipping price, not even free, can save it.
    """
    result = landed_cost.max_customs_base_for_margin(
        selling_price_zar=price_zar,
        duty_rate_pct=customs.lookup_duty_rate_pct("8507.60"),
        ad_cpa_zar=ad_cpa_zar,
        target_margin_pct=target_margin_pct,
        payment_fee_pct=landed_cost.PAYMENT_FEE_PCT_WORST_CASE,
        platform_fees_zar=platform_fees_zar,
        return_rate_pct=landed_cost.RETURN_RATE_WORST_CASE_PCT,
        vat_basis=vat_basis,
    )
    if not result["feasible"]:
        return None
    ceiling = result["max_customs_base_zar"] - quote["unit_cost_zar"]
    if ceiling < 0:
        return None
    return round(ceiling, 2)


def build_verdict_matrix() -> Dict:
    """The full grid: 4 prices x 3 quotes x 2 CPA x 2 fees x 2 VAT bases."""
    cells: List[Dict] = []
    for point in MR0002_SESSION_PRICE_POINTS:
        price = point["price_zar"]
        for quote in MR0002_QUOTES:
            for cpa in MR0002_CPA_CASES_ZAR:
                for fee in MR0002_PLATFORM_FEE_CASES_ZAR:
                    for basis in VAT_BASIS_CASES:
                        cell = {
                            "price_zar": price,
                            "quote": quote["key"],
                            "ad_cpa_zar": cpa,
                            "platform_fees_zar": fee["zar"],
                            "vat_basis": basis["key"],
                            "verdict_bearing": basis["verdict_bearing"],
                        }
                        for scenario in MR0002_SHIPPING_SCENARIOS:
                            res = evaluate_combination(
                                quote,
                                price,
                                cpa,
                                fee["zar"],
                                scenario["shipping_zar"],
                                basis["vat_basis"],
                            )
                            cell[scenario["key"]] = res
                        cell["max_shipping_25pct_zar"] = max_shipping_for_margin(
                            quote, price, cpa, fee["zar"], 25.0, basis["vat_basis"]
                        )
                        cell["max_shipping_20pct_zar"] = max_shipping_for_margin(
                            quote, price, cpa, fee["zar"], 20.0, basis["vat_basis"]
                        )
                        cells.append(cell)

    cheapest = _quote_by_key(MR0002_CHEAPEST_USABLE_QUOTE_KEY)
    counts = {}
    for scenario in MR0002_SHIPPING_SCENARIOS:
        key = scenario["key"]
        for band in ("accept", "investigate", "reject"):
            counts[f"{key}_{band}"] = sum(
                1 for c in cells if c[key]["band_verdict"] == band
            )
    # Robustness of a REJECT under the ATV question: the ATV basis can only
    # raise VAT on the same inputs, so a reject on the README basis survives.
    both = {}
    for scenario in MR0002_SHIPPING_SCENARIOS:
        key = scenario["key"]
        pairs = {}
        for cell in cells:
            pair_key = (
                cell["price_zar"],
                cell["quote"],
                cell["ad_cpa_zar"],
                cell["platform_fees_zar"],
            )
            pairs.setdefault(pair_key, {})[cell["vat_basis"]] = cell[key][
                "band_verdict"
            ]
        consistent_rejects = sum(
            1
            for pair in pairs.values()
            if pair.get("readme") == "reject" and pair.get("atv") == "reject"
        )
        both[key] = {
            "readme_atv_pairs": len(pairs),
            "reject_on_both_vat_bases": consistent_rejects,
        }

    return {
        "cells": cells,
        "cell_count": len(cells),
        "quotes": MR0002_QUOTES,
        "cheapest_usable_quote": cheapest["key"],
        "cheapest_usable_quote_zar": cheapest["unit_cost_zar"],
        "price_points": MR0002_SESSION_PRICE_POINTS,
        "shipping_scenarios": MR0002_SHIPPING_SCENARIOS,
        "platform_fee_cases": MR0002_PLATFORM_FEE_CASES_ZAR,
        "vat_basis_cases": VAT_BASIS_CASES,
        "band_counts": counts,
        "robustness": both,
        "deep_tier_scenario": MR0002_DEEP_TIER_SCENARIO,
    }


def verdict_schema_blocks(matrix: Dict) -> List[Dict]:
    """The session brief's OUTPUT FORMAT block, one per price x fee case.

    Uses the cheapest usable quote and the ONLY fetched shipping datapoint
    (the approvable-by-inputs scenario cannot exist until Sourcing delivers a
    verified SA-lane cost, which is itself reported as a gap).
    """
    quote = _quote_by_key(matrix["cheapest_usable_quote"])
    shipping = MR0002_SHIPPING_SCENARIOS[1]["shipping_zar"]
    blocks: List[Dict] = []
    for point in MR0002_SESSION_PRICE_POINTS:
        price = point["price_zar"]
        for fee in MR0002_PLATFORM_FEE_CASES_ZAR:
            for cpa in MR0002_CPA_CASES_ZAR:
                breakdown = landed_cost.calculate_landed_cost(
                    product_cost_zar=quote["unit_cost_zar"],
                    shipping_to_sa_zar=shipping,
                    duty_rate_pct=customs.lookup_duty_rate_pct("8507.60"),
                    selling_price_zar=price,
                    payment_fee_pct=landed_cost.PAYMENT_FEE_PCT_WORST_CASE,
                )
                margin = landed_cost.net_margin(
                    selling_price_zar=price,
                    total_landed_cost_zar=breakdown["total_landed_cost_zar"],
                    ad_cpa_zar=cpa,
                    platform_fees_zar=fee["zar"],
                    return_rate_pct=landed_cost.RETURN_RATE_WORST_CASE_PCT,
                )
                verdict = landed_cost.verdict_for_margin(margin["net_margin_pct"])
                blocks.append(
                    {
                        "timestamp": "",  # stamped by the caller
                        "agent": AGENT,
                        "confidence": 8,
                        "source": (
                            f"{MODULES()}; so-0003 ({quote['key']} unit cost "
                            f"R{quote['unit_cost_zar']} at MOQ {quote['moq']}); "
                            "HS 8507.60 duty 0.0% (mr-0002/mr-0034 + two "
                            "agreeing secondary sources, SARS primary line "
                            "rate still UNREAD); CPA R150-R300 per README "
                            "section 4; shipping R161.83/unit from the only "
                            "fetched quote (destination UNVERIFIED)"
                        ),
                        "verified": False,
                        "product": f"mr-0002 solar power bank 20,000mAh — "
                        f"{point['label']}",
                        "cost_breakdown": {
                            "product_cost_zar": breakdown["product_cost_zar"],
                            "shipping_zar": breakdown["shipping_zar"],
                            "duty_zar": breakdown["duty_zar"],
                            "vat_zar": breakdown["vat_zar"],
                            "payment_fees_zar": breakdown["payment_fees_zar"],
                            "total_landed_cost_zar": breakdown[
                                "total_landed_cost_zar"
                            ],
                        },
                        "pricing": {
                            "recommended_selling_price_zar": price,
                            "gross_margin_pct": round(
                                (
                                    price
                                    - breakdown["total_landed_cost_zar"]
                                )
                                / price
                                * 100.0,
                                2,
                            ),
                            "ad_cpa_estimate_zar": cpa,
                            "net_margin_pct": margin["net_margin_pct"],
                            "competitor_median_price_zar": None,
                        },
                        "verdict": verdict["verdict"],
                        "rejection_reason": verdict["rejection_reason"],
                        "UNVERIFIED_shipping_to_sa_zar": shipping,
                        "UNVERIFIED_platform_fees_zar": fee["zar"],
                        "UNVERIFIED_competitor_median_price_zar": (
                            "MR evidence is named price points with PLIDs, "
                            "not a computed category median (pr-0003)"
                        ),
                        "vat_basis": breakdown["vat_basis"],
                        "net_margin_at_zero_shipping_pct": round(
                            landed_cost.net_margin(
                                selling_price_zar=price,
                                total_landed_cost_zar=landed_cost.calculate_landed_cost(
                                    quote["unit_cost_zar"],
                                    0.0,
                                    customs.lookup_duty_rate_pct("8507.60"),
                                    price,
                                )["total_landed_cost_zar"],
                                ad_cpa_zar=cpa,
                                platform_fees_zar=fee["zar"],
                            )["net_margin_pct"],
                            2,
                        ),
                    }
                )
    return blocks


def build_verdict_findings(ts: str) -> List[Dict]:
    """pr-0004 (ATV HARD STOP + gate 5 request), pr-0005 (matrix),
    pr-0006 (formal verdict)."""
    matrix = build_verdict_matrix()
    blocks = verdict_schema_blocks(matrix)
    for block in blocks:
        block["timestamp"] = ts

    rejects_at_fetched = matrix["band_counts"]["ship_fetched_reject"]
    rejects_at_zero = matrix["band_counts"]["ship0_reject"]

    pr_0004 = {
        "id": "pr-0004",
        "timestamp": ts,
        "agent": AGENT,
        "confidence": 9,
        "source": (
            f"{MODULES()}; tools/customs.py v1.0.0 module docstring (ATV "
            "'deliberately NOT implemented'); pricing pr-0003 "
            "atv_formula_discrepancy_DECISION_REQUESTED; README sections 1, "
            "2 (#4), 4, 5 (gate 5)"
        ),
        "verified": True,
        "data": {
            "record_type": "hard_stop_and_hitl_request",
            "hard_stop": (
                "The session task requires the SARS ATV VAT method. On "
                "entering this session tools/customs.py v1.0.0 did NOT "
                "implement it (its docstring says so explicitly and pr-0003 "
                "had already escalated the conflict). Reported as a HARD "
                "STOP rather than silently computing margins on the README "
                "flat formula."
            ),
            "contract_conflict": (
                "README section 4 / HARD STOP #4 say VAT = customs_value x "
                "0.15. SARS' ATV method for non-SACU consignments charges 15% "
                "on (customs value + duty + 10% uplift). README section 1: "
                "the README wins conflicts, so the README formula remains the "
                "default and the only verdict-bearing basis."
            ),
            "action_taken_this_session": (
                "Added customs.calculate_vat_sars_atv() + a vat_basis "
                "selector to tools/customs.py (v1.1.0) and threaded it "
                "through tools/landed_cost.py (v1.1.0) so the ATV variant "
                "lives INSIDE the one module allowed to hold cost math "
                "(README section 6) instead of being re-implemented by this "
                "agent. Defaults are UNCHANGED: DEFAULT_VAT_BASIS is the "
                "README contract formula, and evaluate_pricing() REFUSES the "
                "ATV basis outright (a verdict may not rest on an unapproved "
                "formula)."
            ),
            "hitl_gate_5_request": {
                "what": (
                    "Approve or reject the addition of the SARS ATV VAT "
                    "basis to tools/customs.py + tools/landed_cost.py "
                    "(opt-in, non-default), and the accompanying README "
                    "section 4 amendment if ATV is to become the basis."
                ),
                "why": (
                    "The README formula understates VAT if SARS' ATV method "
                    "is the legally correct one, which flatters every margin "
                    "in the worst possible direction for a margin gate."
                ),
                "cost": (
                    "No paid service, no purchase, no order. Engineering "
                    "cost only: one module + tests (this PR)."
                ),
                "risk": (
                    "If ATV is NOT approved and is the legally correct "
                    "method, every published margin is overstated. If ATV is "
                    "adopted without amending README section 4, the contract "
                    "and the tool disagree — hence the amendment is part of "
                    "the same approval."
                ),
                "quantified_impact": (
                    "mr-0002 (duty 0%): the customs multiplier moves from "
                    f"{customs.duty_and_vat_multiplier(0.0)} to "
                    f"{customs.duty_and_vat_multiplier(0.0, customs.VAT_BASIS_SARS_ATV)}"
                    " (+1.30% on the customs value). On the cheapest usable "
                    "quote at zero shipping that is R0.98 (Coremax R86.80) "
                    "per unit — small in rands, but it moves in the wrong "
                    "direction for every accept."
                ),
                "status": "REQUESTED — not approved; nothing merges without APPROVED",
            },
            "brief_reconciliation": (
                "Because ATV is unapproved, the verdict-bearing figures in "
                "pr-0005/pr-0006 use the README basis and the ATV figures are "
                "reported alongside as sensitivity. This is not silent use of "
                "either formula: both are labelled per cell, and the ATV "
                "basis can only LOWER margins, so every reject recorded here "
                "holds under both."
            ),
        },
    }

    pr_0005 = {
        "id": "pr-0005",
        "timestamp": ts,
        "agent": AGENT,
        "confidence": 8,
        "source": (
            f"{MODULES()}; so-0003 (3 mr-0002 quotes: Coremax $5.31, "
            "AliExpress $10.31, Quark $10.50, FX 16.3460) + so-0005 session "
            "summary; mr-0002 price evidence; README sections 2 (#3, #4) and "
            "4; pr-0003 (platform-fee gap)"
        ),
        "verified": False,
        "data": {
            "record_type": "verdict_matrix",
            "product": "mr-0002 — 20,000mAh solar power bank (HS 8507.60, 0% duty)",
            "scope_corrections": [
                "BRIEF SAID 'six supplier quotes from so-0003/so-0004/"
                "so-0005'. State carries six quotes across TWO products: "
                "so-0003 = 3 quotes for mr-0002, so-0004 = 3 quotes for "
                "mr-0003 (LED emergency light, HS 8513.10 — duty rate "
                "UNVERIFIED in state). Only the three mr-0002 quotes are "
                "used; using mr-0003's would cross products and cross onto "
                "an unverified duty line.",
                "The R299/R338 'market cluster' is 10,000mAh evidence; all "
                "three quotes are 20,000mAh units whose observed Takealot "
                "point is R699. Pricing a 20k unit in the 10k band is the "
                "brief's instruction and is computed as given, but the "
                "segment mismatch is recorded as a finding.",
                "Shipping is the unresolved input: NO mr-0002 supplier "
                "displayed a SA lane or DDP (so-0003/so-0005), so no "
                "combination below is approvable on its inputs. R0 and "
                "R161.83/unit (the only fetched figure, destination "
                "UNVERIFIED) bracket the observable range, and every cell "
                "also carries the shipping ceiling that would be required.",
            ],
            "cheapest_usable_quote_definition": (
                "cheapest verified per-unit price purchasable at the "
                "supplier's stated entry MOQ, no bulk commitment assumed"
            ),
            "cheapest_usable_quote_zar": matrix["cheapest_usable_quote_zar"],
            "deep_tier_excluded": matrix["deep_tier_scenario"],
            "cell_field_legend": {
                "ship0": "landed cost + margin with shipping R0 (bound only)",
                "ship_fetched": "with shipping R161.83/unit (UNVERIFIED destination)",
                "max_shipping_25pct_zar": (
                    "shipping/unit ceiling for a 25% margin; null = product "
                    "cost alone already exceeds the ceiling"
                ),
                "max_shipping_20pct_zar": "same for the 20% HARD-STOP floor",
                "band_verdict": "accept >=25 / investigate 20-25 / reject <20",
                "tool_verdict": "landed_cost.verdict_for_margin (accept/reject only)",
            },
            "counts": matrix["band_counts"],
            "robustness_under_the_atv_question": matrix["robustness"],
            "cells": matrix["cells"],
            "reading": [
                "Every one of the 96 cells is a reject once the fetched "
                "shipping datapoint is applied — including the R599 cells at "
                "CPA R150 and R0 platform fees, whose margins fall to 12.23% "
                "(Coremax), -3.47% (AliExpress) and -4.06% (Quark). Only 16 "
                "of 96 cells are non-reject even at R0 shipping (10 accept, "
                "6 investigate), i.e. 80 of 96 fail with physically "
                "impossible free shipping.",
                "At the R299 and R338 cluster prices the reject is not a "
                "shipping artefact: with shipping at R0 AND platform fees at "
                "R0 AND CPA at its R150 floor, Coremax still returns 1.45% "
                "and 11.09%. At CPA R300 both prices are deeply negative.",
                "At CPA R300 the product fails at EVERY price point up to "
                "R599 even with free shipping and zero platform fees: the "
                "best CPA-R300 cell in the whole grid is R599/Coremax at "
                "18.25%, which is below BOTH the 25% minimum and the 20% "
                "HARD-STOP floor (README section 2 #3) — a reject, not an "
                "escalation.",
                "The only cells that clear 25% require the simultaneous "
                "best case in all four inputs: R449/R599 price, CPA R150, "
                "R0 platform fees, and shipping under R17.03 (R449) / "
                "R95.29 (R599) — i.e. materially below the only shipping "
                "figure anyone has actually fetched (R161.83). R449 at R30 "
                "fees never reaches 25% even at zero shipping (22.68%, "
                "investigate band only); R599 at R30 fees needs shipping "
                "under R69.20.",
                "Every reject in the README-basis cells also rejects on the "
                "ATV basis; the ATV basis cannot raise a margin.",
            ],
        },
    }

    pr_0006 = {
        "id": "pr-0006",
        "timestamp": ts,
        "agent": AGENT,
        "confidence": 8,
        "source": (
            f"{MODULES()}; so-0003 quotes + so-0005 summary; README sections "
            "2 (#3) and 4; session brief banding (>=25 accept / 20-25 "
            "investigate / <20 reject)"
        ),
        "verified": False,
        "data": {
            "record_type": "formal_verdict",
            "product": "mr-0002 — 20,000mAh solar power bank (HS 8507.60, 0% duty)",
            "verdict": "reject",
            "rejection_reason": (
                "MR-0002 fails the margin gate at every price point the "
                "session asked about. At the market-cluster prices (R299, "
                "R338) the net margin is 1.45% and 11.09% BEST CASE — "
                "cheapest usable quote, CPA at the R150 benchmark floor, "
                "platform fees at R0, and shipping at R0 — so those two are "
                "rejects on the arithmetic alone, independent of the "
                "unresolved shipping and VAT questions. At R449 and R599 the "
                "only passing cells need R0 platform fees, CPA R150 and "
                "shipping below R17.03 / R95.29 per unit; the single "
                "shipping figure actually fetched for this product is "
                "R161.83/unit, at which R599/CPA150/R0-fees still yields "
                "12.23% and everything else is negative. At CPA R300 the "
                "product does not reach the 25% minimum at ANY price up to "
                "R599 even with free shipping and zero platform fees; its "
                "best CPA-R300 cell is 18.25%, below even the 20% floor. "
                "Cited rule: README section 2 HARD STOP #3 (no net margin "
                "below 20%) plus the session's 25% Pricing minimum — no cell "
                "in this matrix reaches the 25% minimum under any shipping "
                "input that is physically possible. "
                "Recorded as reject, not blocked: the arithmetic is now "
                "possible because Sourcing delivered verified unit costs, "
                "but it fails."
            ),
            "verdict_by_combination": {
                "note": (
                    "verdict per {price, quote, CPA} is reported for both "
                    "platform-fee assumptions; every verdict below is a "
                    "reject under the fetched shipping datapoint"
                ),
                "grid": "see pr-0005.cells (96 cells)",
            },
            "blocks": blocks,
            "summary_counts": {
                "cells_total": matrix["cell_count"],
                "reject_at_fetched_shipping": rejects_at_fetched,
                "reject_at_zero_shipping": rejects_at_zero,
                "accept_or_investigate_requiring_physically_impossible_free_"
                "shipping": matrix["cell_count"] - rejects_at_zero,
            },
            "platform_fee_assumption": (
                "No sourced marketplace fee schedule exists (pr-0003), so "
                "every combination is computed with R0 fees AND a "
                "conservative R30/order. The final verdict cites both: R0 "
                "fees flatter the margin and still reject; R30 lowers every "
                "margin further."
            ),
            "inputs_still_unverified": [
                "shipping_to_sa_zar — no mr-0002 supplier has a verified SA "
                "lane or DDP quote (R161.83/unit is destination-UNVERIFIED)",
                "platform_fees_zar — no sourced fee schedule (R0 and R30 are "
                "both assumptions)",
                "SARS primary line reading for 8507.60 (two agreeing "
                "secondary sources + SARS corroboration of the heading; "
                "primary line rate still unread)",
                "8541.43 composite-classification residual risk (advance "
                "tariff determination recommended by so-0003)",
                "ATV VAT basis is unapproved pending HITL gate 5 (pr-0004)",
            ],
            "recommended_next_actions": [
                "Supervisor: do NOT route mr-0002 to Listing/AdGrowth.",
                "If the product is still wanted, Sourcing must obtain a "
                "DDP-to-SA quote per unit under R95.29 at R599 (CPA R150, "
                "R0 fees) — and realistically far lower, since R30 fees "
                "bring the R599 ceiling to R51.65. Below R449 nothing "
                "sourcing can quote will clear the gate.",
                "Do not spend on a SARS advance tariff determination for "
                "this SKU while the margin gate fails on price alone.",
            ],
        },
    }

    return [pr_0004, pr_0005, pr_0006]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pricing agent capability #1 (dry run by default)"
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=default_state_path(),
        help="path to shared_state.json",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="append findings to the state file (default: dry run)",
    )
    args = parser.parse_args(argv)

    ts = now_iso()
    state = load_state(args.state)
    report = readiness_report(state)
    findings = build_findings(ts) + build_verdict_findings(ts)
    # Append-only state: earlier sessions' findings are already on main.
    # Skip ids that are present and SAY SO rather than either failing or
    # silently rewriting an existing record (schema section 3).
    present = {f.get("id") for f in state.get("pricing", {}).get("findings", [])}
    already_present = [f["id"] for f in findings if f["id"] in present]
    findings = [f for f in findings if f["id"] not in present]

    if not args.write:
        print(
            json.dumps(
                {
                    "mode": "dry-run (no file changed)",
                    "state_path": str(args.state),
                    "readiness": report,
                    "findings_to_append": [f["id"] for f in findings],
                    "findings_already_present": already_present,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if not findings:
        print(json.dumps({"mode": "no-op", "reason": "all findings already present",
                          "findings_already_present": already_present}, indent=2))
        return 0
    apply_findings(state, findings, ts)
    args.state.write_text(dump_state(state), encoding="utf-8")
    print(
        json.dumps(
            {
                "mode": "written",
                "state_path": str(args.state),
                "appended": [f["id"] for f in findings],
                "findings_already_present": already_present,
                "readiness": report,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
