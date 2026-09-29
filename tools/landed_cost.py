"""Landed cost, margin and price math. tools/landed_cost.py v1.0.0.

Scope (README section 6): together with tools/customs.py this is the ONLY
place cost math may live. agents/pricing.py (and every later agent) calls
these functions; nobody re-implements the formula (README section 10).

The contract formula, implemented verbatim from README section 4 and the
session brief:

    LANDED COST (ZAR) = product cost
                      + shipping to SA
                      + (customs value x duty)
                      + (customs value x 0.15 VAT)
                      + payment processing fee (3-5% OF SELLING PRICE)

    NET MARGIN (ZAR)  = selling price - landed cost - ad CPA - platform fees
    AD CPA (ZA)       = R150-R300 benchmark per conversion
    RETURNS           = factor 5-10% return/refund rate into margin

SA-specific rules encoded here (README section 4):
  * VAT is charged on the customs value, NEVER on the retail price —
    tools/customs.calculate_vat is the only VAT implementation.
  * Net margin < 20% is an automatic reject (README section 2 HARD STOP
    #3). The Pricing session minimum for an ACCEPT is 25%; 20-25% is the
    escalation band, not an approval. Target band 35-40%.
  * ZA ad CPA benchmark R150-R300.

Verdict integrity (HARD STOP #2 + schema section 4):
  :func:`evaluate_pricing` returns ``verdict="blocked"`` unless the caller
  asserts ``inputs_verified=True``. A margin computed from unverified
  supplier costs must never be published as accept/reject — as of
  shared_state.json so-0002, ZERO supplier costs are verified, so every
  product verdict in state this session is blocked, not approved.

Also provided: :func:`max_customs_base_for_margin` — the inverse question
\"given a competitive price and CPA, what is the MAXIMUM product+shipping
cost that still clears a margin?\". This needs no supplier quote, so it is
the only pricing output publishable while supplier costs are unverified.

The pricing multipliers (2.5-3.0x impulse / 2.0-2.5x considered) are
solved as a fixed point because the payment fee depends on the selling
price: price = m x (base + f x price)  =>  price = m x base / (1 - m x f),
where base = product + shipping + duty + VAT.

Standard library only. See tests/test_landed_cost.py.
"""

from __future__ import annotations

from typing import Dict, Optional

from tools import customs
from tools.customs import VAT_RATE  # re-exported: single definition

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Constants — each cites its authority. README wins on any conflict.
# ---------------------------------------------------------------------------

#: Session brief: payment processing fee is 3-5% OF THE SELLING PRICE.
PAYMENT_FEE_PCT_RANGE = (3.0, 5.0)
#: Verdicts use the WORST case (5%) — never the optimistic end.
PAYMENT_FEE_PCT_WORST_CASE = 5.0

#: README section 2 HARD STOP #3: below this, automatic reject. Nothing
#: may approve below it — not even the escalation band below.
HARD_FLOOR_NET_MARGIN_PCT: float = 20.0
#: Session brief Pricing minimum for an ACCEPT verdict.
MIN_NET_MARGIN_PCT: float = 25.0
#: Session brief Pricing target band (reported, not verdict-changing).
TARGET_NET_MARGIN_BAND_PCT = (35.0, 40.0)

#: README section 4: ZA ad CPA benchmark per conversion.
AD_CPA_RANGE_ZAR = (150.0, 300.0)
#: Verdicts use the WORST case (R300) unless the caller proves better.
AD_CPA_WORST_CASE_ZAR = 300.0

#: Session brief: price at 2.5-3.0x landed cost (impulse) or
#: 2.0-2.5x (considered).
PRICE_MULTIPLIERS = {
    "impulse": (2.5, 3.0),
    "considered": (2.0, 2.5),
}

#: Session brief: set price within 10-15% of the Takealot median. The
#: band is a range, so the default is its midpoint; callers may tighten
#: to 0.10 or 0.15 but never widen past 0.15.
COMPETITOR_BAND_RANGE = (0.10, 0.15)
COMPETITOR_BAND_DEFAULT = 0.125

#: Session brief: factor 5-10% return/refund rate into margin. Verdicts
#: use the worst case (10%) with ZERO salvage (a return refunds the price
#: while the unit, payment fee and ad spend stay sunk).
RETURN_RATE_RANGE_PCT = (5.0, 10.0)
RETURN_RATE_WORST_CASE_PCT = 10.0

#: The contract formula, for embedding in reports (README section 4).
FORMULA_TEXT: str = (
    "LANDED COST (ZAR) = product + shipping "
    "+ (customs_value x duty) + (customs_value x 0.15 VAT) "
    "+ payment_fee (3-5% of selling price); "
    "NET MARGIN = price - landed_cost - ad_cpa - platform_fees"
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _money(value: float, name: str) -> float:
    return customs._validate_amount(value, name)


def _validate_payment_fee_pct(payment_fee_pct: float) -> float:
    pct = float(payment_fee_pct)
    lo, hi = PAYMENT_FEE_PCT_RANGE
    if pct != pct or not (lo <= pct <= hi):
        raise ValueError(
            f"payment_fee_pct must be within {lo}-{hi} (session brief); "
            f"got {payment_fee_pct}. A different real-world rate is a "
            "contract change: HITL gate 5, not a caller override."
        )
    return pct


def _validate_return_rate_pct(return_rate_pct: float) -> float:
    pct = float(return_rate_pct)
    lo, hi = RETURN_RATE_RANGE_PCT
    if pct != pct or not (lo <= pct <= hi):
        raise ValueError(
            f"return_rate_pct must be within {lo}-{hi} (session brief); "
            f"got {return_rate_pct}"
        )
    return pct


# ---------------------------------------------------------------------------
# Landed cost — the contract formula
# ---------------------------------------------------------------------------


def calculate_landed_cost(
    product_cost_zar: float,
    shipping_to_sa_zar: float,
    duty_rate_pct: float,
    selling_price_zar: float,
    payment_fee_pct: float = PAYMENT_FEE_PCT_WORST_CASE,
) -> Dict[str, float]:
    """Full landed cost (ZAR) per the README section 4 formula.

    Duty and VAT are computed on the customs value (product + shipping)
    by tools/customs.py — this module never re-implements them. The
    payment fee is a percentage OF THE SELLING PRICE, so the selling
    price is required even though it is not itself a cost.

    Returns the ``cost_breakdown`` schema used by the pricing output
    format, plus the customs value for auditability.
    """
    _validate_payment_fee_pct(payment_fee_pct)
    breakdown = customs.customs_breakdown(
        product_cost_zar, shipping_to_sa_zar, duty_rate_pct
    )
    price = _money(selling_price_zar, "selling_price_zar")
    payment_fees = round(price * payment_fee_pct / 100.0, 2)
    total = round(
        breakdown["customs_value_zar"]
        + breakdown["duty_zar"]
        + breakdown["vat_zar"]
        + payment_fees,
        2,
    )
    return {
        "product_cost_zar": round(float(product_cost_zar), 2),
        "shipping_zar": round(float(shipping_to_sa_zar), 2),
        "customs_value_zar": breakdown["customs_value_zar"],
        "duty_rate_pct": breakdown["duty_rate_pct"],
        "duty_zar": breakdown["duty_zar"],
        "vat_rate": breakdown["vat_rate"],
        "vat_zar": breakdown["vat_zar"],
        "payment_fee_pct": payment_fee_pct,
        "payment_fees_zar": payment_fees,
        "total_landed_cost_zar": total,
    }


# ---------------------------------------------------------------------------
# Margin
# ---------------------------------------------------------------------------


def net_margin(
    selling_price_zar: float,
    total_landed_cost_zar: float,
    ad_cpa_zar: float,
    platform_fees_zar: float = 0.0,
    return_rate_pct: float = RETURN_RATE_WORST_CASE_PCT,
) -> Dict[str, float]:
    """Net margin before and after the return/refund allowance.

    Return model (deliberately conservative, zero salvage): a returned
    order refunds the price while the unit, payment fee, platform fee and
    ad spend stay sunk. Expected margin per order is therefore
    ``price - landed - cpa - platform_fees - (return_rate x price)``.
    """
    _validate_return_rate_pct(return_rate_pct)
    _money(ad_cpa_zar, "ad_cpa_zar")
    _money(platform_fees_zar, "platform_fees_zar")
    price = _money(selling_price_zar, "selling_price_zar")
    if price == 0:
        raise ValueError("selling_price_zar must be > 0")
    landed = _money(total_landed_cost_zar, "total_landed_cost_zar")

    base = round(price - landed - ad_cpa_zar - platform_fees_zar, 2)
    returns_hit = round(price * return_rate_pct / 100.0, 2)
    adjusted = round(base - returns_hit, 2)
    return {
        "base_net_margin_zar": base,
        "return_allowance_zar": returns_hit,
        "net_margin_zar": adjusted,
        "net_margin_pct": round(adjusted / price * 100.0, 2),
        "return_rate_pct": float(return_rate_pct),
    }


def verdict_for_margin(
    net_margin_pct: float,
) -> Dict[str, str]:
    """Map a net margin percentage to the contract verdict.

    >= 25%       -> accept (session Pricing minimum)
    20% - 25%    -> reject, escalation band note (above the HARD STOP
                    floor, below the Pricing minimum — the Supervisor may
                    escalate, this agent may not approve)
    < 20%        -> reject, README section 2 HARD STOP #3
    """
    pct = float(net_margin_pct)
    if pct >= MIN_NET_MARGIN_PCT:
        return {"verdict": "accept", "rejection_reason": ""}
    if pct >= HARD_FLOOR_NET_MARGIN_PCT:
        return {
            "verdict": "reject",
            "rejection_reason": (
                f"net margin {pct:.2f}% is below the {MIN_NET_MARGIN_PCT:.0f}% "
                f"Pricing minimum (above the {HARD_FLOOR_NET_MARGIN_PCT:.0f}% "
                "HARD STOP floor — escalation band, not approvable by "
                "Pricing)"
            ),
        }
    return {
        "verdict": "reject",
        "rejection_reason": (
            f"HARD STOP (README section 2 #3): net margin {pct:.2f}% is "
            f"below the {HARD_FLOOR_NET_MARGIN_PCT:.0f}% floor — automatic "
            "reject"
        ),
    }


# ---------------------------------------------------------------------------
# Price recommendation — fixed point (payment fee depends on price)
# ---------------------------------------------------------------------------


def recommend_price_fixed_point(
    base_landed_cost_zar: float,
    multiplier: float,
    payment_fee_pct: float = PAYMENT_FEE_PCT_WORST_CASE,
) -> float:
    """Solve price = multiplier x (base + payment_fee_pct x price).

    ``base`` is product + shipping + duty + VAT (everything except the
    payment fee, which depends on the unknown price). The closed form is
    ``price = m x base / (1 - m x f)``. Raises if ``m x f >= 1`` (no
    solution) or the multiplier is not positive.
    """
    base = _money(base_landed_cost_zar, "base_landed_cost_zar")
    _validate_payment_fee_pct(payment_fee_pct)
    m = float(multiplier)
    if m != m or m <= 0:
        raise ValueError(f"multiplier must be > 0 (got {multiplier})")
    f = payment_fee_pct / 100.0
    if m * f >= 1:
        raise ValueError(
            f"no solution: multiplier {m} x payment fee {payment_fee_pct}% "
            "consumes the whole price (m x f >= 1)"
        )
    return round(m * base / (1.0 - m * f), 2)


def clamp_to_competitor_band(
    price_zar: float,
    competitor_median_zar: float,
    band: float = COMPETITOR_BAND_DEFAULT,
) -> float:
    """Clamp a price into [median x (1-band), median x (1+band)].

    Session brief: set price within 10-15% of the Takealot median.
    ``band`` must stay within COMPETITOR_BAND_RANGE.
    """
    lo_band, hi_band = COMPETITOR_BAND_RANGE
    if band != band or not (lo_band <= band <= hi_band):
        raise ValueError(
            f"band must be within {lo_band}-{hi_band} (session brief "
            "10-15% of Takealot median); got {band}".format(band=band)
        )
    median = _money(competitor_median_zar, "competitor_median_zar")
    if median == 0:
        raise ValueError("competitor_median_zar must be > 0")
    _money(price_zar, "price_zar")
    lo = round(median * (1.0 - band), 2)
    hi = round(median * (1.0 + band), 2)
    return max(lo, min(hi, round(float(price_zar), 2)))


# ---------------------------------------------------------------------------
# Break-even: the maximum allowable cost for a given competitive price
# ---------------------------------------------------------------------------


def max_customs_base_for_margin(
    selling_price_zar: float,
    duty_rate_pct: float,
    ad_cpa_zar: float,
    target_margin_pct: float,
    payment_fee_pct: float = PAYMENT_FEE_PCT_WORST_CASE,
    platform_fees_zar: float = 0.0,
    return_rate_pct: float = RETURN_RATE_WORST_CASE_PCT,
) -> Dict:
    """Maximum product+shipping (= customs base) that still clears a
    target net margin at a given competitive price.

    Inverse of the contract formula:
        base_max = (P(1 - r - f - t) - CPA - platform_fees) / (1 + d + VAT)
    where t is the target margin. Needs NO supplier quote, so it is the
    only pricing output publishable while supplier costs are unverified
    (it constrains Sourcing instead of guessing a cost — HARD STOP #2).

    Returns ``feasible=False, max_customs_base_zar=None`` when even a
    zero-cost product cannot reach the target (e.g. floor price at CPA
    ceiling): that is a real finding, never silently zeroed.
    """
    _validate_payment_fee_pct(payment_fee_pct)
    _validate_return_rate_pct(return_rate_pct)
    price = _money(selling_price_zar, "selling_price_zar")
    if price == 0:
        raise ValueError("selling_price_zar must be > 0")
    cpa = _money(ad_cpa_zar, "ad_cpa_zar")
    pf = _money(platform_fees_zar, "platform_fees_zar")
    t = float(target_margin_pct)
    if t != t or not (0 <= t < 100):
        raise ValueError(f"target_margin_pct must be within [0, 100); got {t}")
    d = float(duty_rate_pct)
    if d != d or d < 0 or d > 100:
        raise ValueError(f"duty_rate_pct must be within 0-100; got {duty_rate_pct}")

    r = return_rate_pct / 100.0
    f = payment_fee_pct / 100.0
    numerator = price * (1.0 - r - f - t / 100.0) - cpa - pf
    denominator = 1.0 + d / 100.0 + VAT_RATE
    base_max = numerator / denominator
    feasible = base_max >= 0
    return {
        "selling_price_zar": price,
        "duty_rate_pct": d,
        "ad_cpa_zar": cpa,
        "platform_fees_zar": pf,
        "payment_fee_pct": payment_fee_pct,
        "return_rate_pct": return_rate_pct,
        "target_net_margin_pct": t,
        "max_customs_base_zar": round(base_max, 2) if feasible else None,
        "feasible": feasible,
        "formula": (
            "base_max = (P(1 - r - f - t) - CPA - platform_fees) "
            "/ (1 + d + 0.15)"
        ),
    }


# ---------------------------------------------------------------------------
# Full evaluation -> the session brief's pricing output schema
# ---------------------------------------------------------------------------


def evaluate_pricing(
    product_cost_zar: float,
    shipping_to_sa_zar: float,
    duty_rate_pct: float,
    inputs_verified: bool,
    selling_price_zar: Optional[float] = None,
    competitor_median_price_zar: Optional[float] = None,
    buy_type: str = "impulse",
    ad_cpa_zar: float = AD_CPA_WORST_CASE_ZAR,
    platform_fees_zar: float = 0.0,
    payment_fee_pct: float = PAYMENT_FEE_PCT_WORST_CASE,
    return_rate_pct: float = RETURN_RATE_WORST_CASE_PCT,
    competitor_band: float = COMPETITOR_BAND_DEFAULT,
    input_sources: Optional[dict] = None,
) -> Dict:
    """Evaluate one product and return the session's pricing output block.

    Verdict integrity: unless ``inputs_verified=True`` (caller asserts
    every cost input traces to a real source), the verdict is
    ``"blocked"`` and NO accept/reject is issued — a margin from guessed
    costs must never be published (HARD STOP #2; schema section 4).

    When ``selling_price_zar`` is None, a price is recommended from the
    session multipliers for ``buy_type``, clamped into the competitor
    band when a median is given; the verdict uses the WORST-case price of
    the resulting range (low end) so an accept is robust, never lucky.
    """
    result: Dict = {
        "agent": "pricing",
        "product_input": {
            "product_cost_zar": product_cost_zar,
            "shipping_to_sa_zar": shipping_to_sa_zar,
            "duty_rate_pct": duty_rate_pct,
            "competitor_median_price_zar": competitor_median_price_zar,
            "buy_type": buy_type,
        },
        "input_sources": input_sources or {},
        "inputs_verified": bool(inputs_verified),
        "module_versions": customs.module_versions(),
        "formula": FORMULA_TEXT,
        "warnings": [],
    }
    if platform_fees_zar == 0:
        result["warnings"].append(
            "platform_fees_zar=0 is a placeholder, not a real rate — "
            "marketplace/success fees are UNVERIFIED in shared_state; any "
            "accept is provisional until they are sourced"
        )

    if not inputs_verified:
        result.update(
            {
                "verdict": "blocked",
                "rejection_reason": (
                    "cost inputs not verified (HARD STOP #2): no verified "
                    "supplier cost exists in shared_state.json as of so-0002; "
                    "no accept/reject may be issued from guessed costs"
                ),
            }
        )
        return result

    _money(product_cost_zar, "product_cost_zar")
    _money(shipping_to_sa_zar, "shipping_to_sa_zar")

    # --- price selection -------------------------------------------------
    if selling_price_zar is not None:
        price_low = price_high = round(float(selling_price_zar), 2)
        price_basis = "caller-supplied selling price"
    else:
        lo_m, hi_m = PRICE_MULTIPLIERS[buy_type]
        cv = customs.customs_value(product_cost_zar, shipping_to_sa_zar)
        base = round(
            cv
            + customs.calculate_duty(cv, duty_rate_pct)
            + customs.calculate_vat(cv),
            2,
        )
        price_low = recommend_price_fixed_point(base, lo_m, payment_fee_pct)
        price_high = recommend_price_fixed_point(base, hi_m, payment_fee_pct)
        price_basis = (
            f"{buy_type} multiplier {lo_m}-{hi_m}x solved as fixed point "
            f"(payment fee {payment_fee_pct}% of selling price)"
        )
    if competitor_median_price_zar is not None:
        clamped_low = clamp_to_competitor_band(
            price_low, competitor_median_price_zar, competitor_band
        )
        clamped_high = clamp_to_competitor_band(
            price_high, competitor_median_price_zar, competitor_band
        )
        if clamped_low != price_low or clamped_high != price_high:
            result["warnings"].append(
                "recommended price was clamped into the competitor band "
                f"(x1-{competitor_band} of Takealot median)"
            )
        price_low, price_high = clamped_low, clamped_high

    # --- worst-case verdict at the low price ------------------------------
    breakdown = calculate_landed_cost(
        product_cost_zar,
        shipping_to_sa_zar,
        duty_rate_pct,
        price_low,
        payment_fee_pct,
    )
    margin = net_margin(
        price_low,
        breakdown["total_landed_cost_zar"],
        ad_cpa_zar,
        platform_fees_zar,
        return_rate_pct,
    )
    verdict = verdict_for_margin(margin["net_margin_pct"])
    in_target = (
        TARGET_NET_MARGIN_BAND_PCT[0]
        <= margin["net_margin_pct"]
        <= TARGET_NET_MARGIN_BAND_PCT[1]
    )

    result.update(
        {
            "product": input_sources.get("product_name", "")
            if input_sources
            else "",
            "cost_breakdown": breakdown,
            "pricing": {
                "recommended_selling_price_zar": price_low,
                "price_range_considered_zar": [price_low, price_high],
                "price_basis": price_basis,
                "gross_margin_pct": round(
                    (price_low - breakdown["total_landed_cost_zar"])
                    / price_low
                    * 100.0,
                    2,
                ),
                "ad_cpa_estimate_zar": ad_cpa_zar,
                "platform_fees_zar": platform_fees_zar,
                "net_margin_pct": margin["net_margin_pct"],
                "net_margin_zar": margin["net_margin_zar"],
                "competitor_median_price_zar": competitor_median_price_zar,
                "in_target_band_35_40": in_target,
            },
            "verdict": verdict["verdict"],
            "rejection_reason": verdict["rejection_reason"],
        }
    )
    return result
