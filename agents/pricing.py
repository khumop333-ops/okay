"""Pricing agent — capability #1. agents/pricing.py v1.0.0.

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

__version__ = "1.0.0"

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


def verified_supplier_costs(state: Dict) -> List[str]:
    """Supplier cost entries with a verified flag, across all namespaces.

    Returns a list of finding ids; empty means NONE verified — the
    so-0002 halt condition. This is an audit, not a guess.
    """
    verified: List[str] = []
    for ns in ("market_research", "sourcing", "pricing"):
        for entry in state.get(ns, {}).get("findings", []):
            data = entry.get("data", {})
            for key, val in data.items():
                if (
                    "unit_cost" in key.lower()
                    and isinstance(val, (int, float))
                    and entry.get("verified") is True
                ):
                    verified.append(entry["id"])
    return verified


def readiness_report(state: Dict) -> Dict:
    """What the pricing namespace can and cannot do right now."""
    mr_lead = finding(state, "market_research", "mr-0002")
    sourcing = state.get("sourcing", {})
    halted = any(
        "HALTED" in json.dumps(f.get("data", {}).get("routing_decision", ""))
        for f in sourcing.get("findings", [])
    )
    return {
        "verified_duty_lines": sorted(customs.VERIFIED_DUTY_LINES.keys()),
        "verified_supplier_costs": verified_supplier_costs(state),
        "sourcing_halted": halted,
        "lead_candidate": (
            mr_lead["data"]["product_name"] if mr_lead else None
        ),
        "lead_duty_rate_pct": (
            mr_lead["data"].get("duty_rate_pct") if mr_lead else None
        ),
        "conclusion": (
            "NO accept/reject margin verdict is possible: zero verified "
            "supplier costs exist (so-0002). Publishable today: "
            "maximum-allowable-cost break-evens from verified duty + "
            "competitor prices + the README CPA band."
        ),
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
    ]
    for line in extra:
        if line not in ns["unverified_fields"]:
            ns["unverified_fields"].append(line)
    return state


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
    findings = build_findings(ts)

    if not args.write:
        print(
            json.dumps(
                {
                    "mode": "dry-run (no file changed)",
                    "state_path": str(args.state),
                    "readiness": report,
                    "findings_to_append": [
                        f["id"] for f in findings
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    apply_findings(state, findings, ts)
    args.state.write_text(dump_state(state), encoding="utf-8")
    print(
        json.dumps(
            {
                "mode": "written",
                "state_path": str(args.state),
                "appended": [f["id"] for f in findings],
                "readiness": report,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
