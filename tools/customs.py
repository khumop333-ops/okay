"""Customs math — HS-code duty rates + VAT. tools/customs.py v1.1.0.

Scope (README section 6): this module is ONE of the only two places cost
math may live. Every agent imports from here; no agent re-implements a
formula (README section 10 anti-patterns).

What lives here:
  * :data:`VAT_RATE` — 15%, applied to the customs value. README section 2
    HARD STOP #4: every landed-cost calculation MUST include 15% VAT on the
    customs value. There are no exceptions, so :func:`calculate_vat` takes
    no rate override parameter — the rate cannot be turned off by a caller.
  * :func:`customs_value` — the contract valuation base: product cost plus
    international transport to SA. VAT is charged on this, NEVER on the
    retail selling price (brief + README section 4).
  * :func:`calculate_duty` — customs value x duty.
  * :data:`VERIFIED_DUTY_LINES` — the SA duty rates verified this pipeline
    by Market Research findings mr-0001..mr-0022, each carrying its source
    and the finding that verified it. :func:`lookup_duty_rate_pct` refuses
    anything else (HARD STOP #2: never invent an HS code or duty rate).

Known discrepancy, now IMPLEMENTED BUT NOT DEFAULTED (HITL-gated):
  SARS' ATV method charges VAT on (customs value + duty + 10% uplift) for
  non-SACU consignments; the README contract formula charges
  ``customs_value x 0.15`` with no uplift. README section 1: the README wins
  conflicts, so the README formula remains the DEFAULT and the only basis a
  published verdict may rest on.

  v1.1.0 adds :func:`calculate_vat_sars_atv` and a ``vat_basis`` selector so
  the ATV variant can be QUANTIFIED INSIDE THIS MODULE (README section 6: no
  cost math anywhere else) instead of being re-implemented by a caller. Per
  pricing pr-0003 the change needs a README amendment + HITL gate 5 approval;
  until that lands, the ATV basis is an unapproved sensitivity, is never the
  default, and must not carry a verdict (pricing pr-0004).

Standard library only. See tests/test_customs.py.
"""

from __future__ import annotations

from typing import Dict, Union

__version__ = "1.1.0"

#: README section 2 HARD STOP #4 / section 4. Applied to the customs value.
VAT_RATE: float = 0.15

#: VAT-basis selectors. ``VAT_BASIS_README`` is the contract formula
#: (README section 4) and the DEFAULT for every function here. The SARS ATV
#: variant exists only as an opt-in sensitivity pending a README amendment +
#: HITL gate 5 (pricing pr-0003/pr-0004); README section 1 gives the README
#: priority on conflicts, so the default must not change without that gate.
VAT_BASIS_README: str = "readme_contract"
VAT_BASIS_SARS_ATV: str = "sars_atv"
VAT_BASIS_CHOICES = (VAT_BASIS_README, VAT_BASIS_SARS_ATV)
DEFAULT_VAT_BASIS: str = VAT_BASIS_README

#: SARS' 10% upliftment applied to the customs value in the value-for-VAT
#: (ATV) determination for non-SACU consignments. Source: fetched secondary
#: (jlog.co.za HS 8507.60 page, updated 2026-07-04, "VAT 15% on ATV with 10%
#: uplift", worked example R2,000 FOB -> R330 duty+VAT) + mr-0027 conflict
#: item 6 + pricing pr-0003 quantification. NOT primary-sourced in-repo;
#: carried as a flagged assumption of the unapproved ATV basis.
SARS_ATV_UPLIFT_PCT: float = 10.0

#: Source for every line in VERIFIED_DUTY_LINES (SARS-derived secondary
#: index, read by Market Research this pipeline). Primary-source (SARS
#: Schedule 1) confirmation of each line is still outstanding — see
#: shared_state.json market_research.unverified_fields.
_SECONDARY_SOURCE: str = (
    "https://tradecaravan.co.za/hs-codes/ "
    "(SARS-derived index, current 2026-08-06)"
)


class UnknownHsCodeError(KeyError):
    """Raised when an HS code is not in the verified registry.

    This refusal is the mechanical form of HARD STOP #2: a caller who
    believes a code applies must first get the rate verified into this
    registry (or pass a rate they can cite), never guess.
    """


# ---------------------------------------------------------------------------
# Verified SA duty lines — copied from shared_state.json market_research
# findings. Values are percentages (15.0 == 15%). Do not add a line without
# a real source and a finding id; an unverifiable entry would launder a
# guess into the one module allowed to hold duty rates.
# ---------------------------------------------------------------------------

VERIFIED_DUTY_LINES: Dict[str, Dict] = {
    "8507.60": {
        "description": "Electric accumulators (incl. portable power banks)",
        "duty_rate_pct": 0.0,
        "verified_by": "mr-0002",
        "note": (
            "Solar-integrated units could attract 8541.43 @10% on an "
            "essential-character argument — tariff determination required "
            "(mr-0002 classification_caveat)."
        ),
    },
    "8504.40": {
        "description": "Static converters (battery/phone chargers)",
        "duty_rate_pct": 0.0,
        "verified_by": "mr-0001",
    },
    "8544.42": {
        "description": "Electric conductors fitted with connectors (cables)",
        "duty_rate_pct": 15.0,
        "verified_by": "mr-0001",
        "note": (
            "Charger+cable bundles conservatively rated at this, the "
            "highest line, pending composite-GRI treatment (mr-0001)."
        ),
    },
    "3926.90": {
        "description": "Articles of plastics, nesoi (phone cases, mounts, "
                       "plastic kitchen tools)",
        "duty_rate_pct": 20.0,
        "verified_by": "mr-0004; mr-0007; mr-0022",
        "note": (
            "Metal-dominant variants may classify 8302/7616 or stainless "
            "7323.93 — material must be confirmed (mr-0004 caveat)."
        ),
    },
    "7323.93": {
        "description": "Table/kitchen articles, stainless steel",
        "duty_rate_pct": 20.0,
        "verified_by": "mr-0022",
    },
    "9503.00": {
        "description": "Toys, scale models, puzzles",
        "duty_rate_pct": 20.0,
        "verified_by": "mr-0015",
    },
    "8528.72": {
        "description": "Television receivers (colour)",
        "duty_rate_pct": 25.0,
        "verified_by": "mr-0014",
    },
    "6402.99": {
        "description": "Footwear, rubber/plastic uppers (other)",
        "duty_rate_pct": 30.0,
        "verified_by": "mr-0010",
        "note": (
            "Above the session 25% elimination band and subject to 20-50% "
            "anti-dumping risk on China origin — candidate mr-0010 rejected "
            "at Market Research; rate kept for reference only."
        ),
    },
}

#: Every registry line shares this source; recorded once to avoid drift.
REGISTRY_SOURCE: str = _SECONDARY_SOURCE


# ---------------------------------------------------------------------------
# Valuation + tax math. Keep tiny; tools/landed_cost.py composes these.
# ---------------------------------------------------------------------------


def _validate_amount(zar: float, name: str) -> float:
    """Reject non-numeric, negative or NaN money inputs."""
    if not isinstance(zar, (int, float)) or isinstance(zar, bool):
        raise TypeError(f"{name} must be a number, got {type(zar).__name__}")
    value = float(zar)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    if value < 0:
        raise ValueError(f"{name} must be >= 0 (got {value})")
    return value


def customs_value(product_cost_zar: float, shipping_to_sa_zar: float) -> float:
    """Contract customs value = product cost + transport to SA (ZAR).

    This is the base for BOTH duty and the 15% VAT. It is deliberately
    independent of the retail selling price: VAT is on customs value, not
    retail (README section 4).

    Note: SARS' ATV determination for non-SACU consignments adds a 10%
    uplift for VAT purposes. The README contract formula does not; the
    discrepancy is escalated, not silently implemented (module docstring).
    """
    product = _validate_amount(product_cost_zar, "product_cost_zar")
    shipping = _validate_amount(shipping_to_sa_zar, "shipping_to_sa_zar")
    return round(product + shipping, 2)


def calculate_duty(
    customs_value_zar: float, duty_rate_pct: float
) -> float:
    """Duty (ZAR) = customs value x duty rate. Rate is a percentage."""
    value = _validate_amount(customs_value_zar, "customs_value_zar")
    if not isinstance(duty_rate_pct, (int, float)) or isinstance(
        duty_rate_pct, bool
    ):
        raise TypeError("duty_rate_pct must be a number")
    rate = float(duty_rate_pct)
    if rate != rate or rate < 0 or rate > 100:
        raise ValueError(
            f"duty_rate_pct must be within 0-100 (got {duty_rate_pct})"
        )
    return round(value * rate / 100.0, 2)


def calculate_vat(customs_value_zar: float) -> float:
    """VAT (ZAR) = customs value x 0.15.

    No rate parameter exists ON PURPOSE (README section 2 HARD STOP #4:
    every landed-cost calculation MUST include 15% VAT on the customs
    value; there are no exceptions).
    """
    value = _validate_amount(customs_value_zar, "customs_value_zar")
    return round(value * VAT_RATE, 2)


def calculate_vat_sars_atv(
    customs_value_zar: float,
    duty_zar: float = 0.0,
    uplift_pct: float = SARS_ATV_UPLIFT_PCT,
) -> float:
    """VAT under SARS' ATV method — OPT-IN, UNAPPROVED, NOT the default.

        VAT = 15% x (customs value + duty + uplift_pct% x customs value)

    Rounding to the cent matches :func:`calculate_vat`.

    STATUS — read before calling (pricing pr-0003, pr-0004):
      * The README (section 4) contract formula is ``customs_value x 0.15``
        and README section 1 makes the README authoritative on conflicts.
        This function is therefore NOT the default basis anywhere, and
        :data:`DEFAULT_VAT_BASIS` must stay ``VAT_BASIS_README`` until a
        README amendment + HITL gate 5 approval change the contract.
      * It exists so the ATV discrepancy can be quantified INSIDE the one
        module allowed to hold customs math, rather than being
        re-implemented by an agent (README section 6 anti-pattern).
      * No verdict may REST on its output while it is unapproved; it is a
        sensitivity bound. It can only ever produce a HIGHER VAT than
        :func:`calculate_vat` on the same inputs (uplift >= 0, duty >= 0),
        so a margin that already fails on the README basis cannot be
        rescued by the ATV basis.

    The 10% upliftment is applied to the customs value (the standard SARS
    formulation). Note that with a 0% duty line — e.g. mr-0002's HS
    8507.60 — uplift-on-customs-value and uplift-on-(customs value + duty)
    give identical results, so classification-sensitive cases are not
    affected by that reading here.
    """
    value = _validate_amount(customs_value_zar, "customs_value_zar")
    duty = _validate_amount(duty_zar, "duty_zar")
    if duty > value:
        raise ValueError(
            "duty_zar greater than the customs value is not credible for a "
            "SA general-rate line (max 100%) — check the inputs"
        )
    uplift = float(uplift_pct)
    if uplift != uplift or not (0.0 <= uplift <= 100.0):
        raise ValueError(f"uplift_pct must be within 0-100; got {uplift_pct}")
    return round((value + duty + value * uplift / 100.0) * VAT_RATE, 2)


def validate_vat_basis(vat_basis: str) -> str:
    """Return a known VAT-basis selector or raise (never guess a basis)."""
    if vat_basis not in VAT_BASIS_CHOICES:
        raise ValueError(
            f"unknown vat_basis {vat_basis!r}; expected one of "
            f"{VAT_BASIS_CHOICES} (VAT_BASIS_SARS_ATV is unapproved pending "
            "HITL gate 5 and is opt-in only)"
        )
    return vat_basis


def duty_and_vat_multiplier(
    duty_rate_pct: float,
    vat_basis: str = DEFAULT_VAT_BASIS,
) -> float:
    """(duty + VAT) as a multiplier of the customs value.

    Lets the inverse margin math in tools/landed_cost.py stay consistent
    with the forward math here: ``duty + VAT = customs_value x (m - 1)``.

      * README basis: m = 1 + d + 0.15
      * ATV basis:    m = 1 + d + 0.15 x (1.10 + d)   [uplift on customs
        value; recomputed from :func:`calculate_vat_sars_atv`, not from a
        second hand-written formula]

    The ATV form is re-derived through the public functions so the two
    bases cannot drift apart.
    """
    validate_vat_basis(vat_basis)
    if not isinstance(duty_rate_pct, (int, float)) or isinstance(
        duty_rate_pct, bool
    ):
        raise TypeError("duty_rate_pct must be a number")
    rate = float(duty_rate_pct)
    if rate != rate or rate < 0 or rate > 100:
        raise ValueError(
            f"duty_rate_pct must be within 0-100 (got {duty_rate_pct})"
        )
    # Evaluate on a LARGE synthetic base so the result is the multiplier
    # itself. A unit base would quantise it to cents (0.165 -> 0.17) and
    # bias every inverse-margin ceiling; the large base keeps the cent
    # rounding in calculate_duty/calculate_vat below 1e-8 relative and the
    # ATV expression is still derived through those public functions
    # rather than a second hand-written formula.
    base = 1_000_000.0
    duty = calculate_duty(base, rate)
    vat = (
        calculate_vat(base)
        if vat_basis == VAT_BASIS_README
        else calculate_vat_sars_atv(base, duty)
    )
    return round((base + duty + vat) / base, 6)


def lookup_duty_rate_pct(hs_code: str) -> float:
    """Return the verified SA general duty rate (pct) for an HS code.

    Raises :class:`UnknownHsCodeError` for any code not in the verified
    registry. Callers must never fall back to a remembered or
    \"typical\" rate — HARD STOP #2.
    """
    if not isinstance(hs_code, str):
        raise TypeError("hs_code must be a string like '8507.60'")
    key = hs_code.strip()
    if key not in VERIFIED_DUTY_LINES:
        raise UnknownHsCodeError(
            f"HS code {hs_code!r} is not in VERIFIED_DUTY_LINES; get the SA "
            "rate verified from SARS Schedule 1 (or a cited secondary "
            "source) and add it with its source + finding id. Never guess."
        )
    return float(VERIFIED_DUTY_LINES[key]["duty_rate_pct"])


def customs_breakdown(
    product_cost_zar: float,
    shipping_to_sa_zar: float,
    duty_rate_pct: float,
    vat_basis: str = DEFAULT_VAT_BASIS,
) -> Dict[str, Union[float, None]]:
    """One composition of customs math, for audit trails.

    Returns the customs value, duty and 15% VAT that
    tools/landed_cost.py folds into the landed cost. ``duty_source`` is
    None here because this function accepts an already-verified rate;
    use :func:`lookup_duty_rate_pct` at the call site when the rate comes
    from an HS code, and record that provenance in the caller's output.

    ``vat_basis`` defaults to the README contract formula. Passing
    ``VAT_BASIS_SARS_ATV`` is an unapproved sensitivity (see
    :func:`calculate_vat_sars_atv`); the returned ``vat_basis`` field always
    records which basis produced ``vat_zar`` so no caller can do it
    silently.
    """
    validate_vat_basis(vat_basis)
    value = customs_value(product_cost_zar, shipping_to_sa_zar)
    duty = calculate_duty(value, duty_rate_pct)
    if vat_basis == VAT_BASIS_README:
        vat = calculate_vat(value)
        atv_uplift_pct = None
    else:
        vat = calculate_vat_sars_atv(value, duty)
        atv_uplift_pct = SARS_ATV_UPLIFT_PCT
    return {
        "customs_value_zar": value,
        "duty_zar": duty,
        "vat_zar": vat,
        "duty_rate_pct": float(duty_rate_pct),
        "vat_rate": VAT_RATE,
        "vat_basis": vat_basis,
        "atv_uplift_pct": atv_uplift_pct,
        "duty_and_vat_multiplier": duty_and_vat_multiplier(
            duty_rate_pct, vat_basis
        ),
    }


def module_versions() -> str:
    """Version stamp for state records, per the session brief format."""
    from tools import landed_cost  # local import: no circular at module load

    return (
        f"tools/landed_cost.py v{landed_cost.__version__}, "
        f"tools/customs.py v{__version__}"
    )
