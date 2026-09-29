"""Market Research agent — capability #1: candidate screening helpers.

Scope (this capability only):
  * A :class:`Candidate` record that keeps verified values separate from
    judgment calls. Anything the crew could not verify from a real source
    stays ``None`` here and is exported with an ``UNVERIFIED_`` prefix when
    written to ``shared_state.json`` (see ``shared_state.schema.md`` §4).
  * :func:`classify_customs_risk` — README §4 rules only (apparel/textiles
    HIGH RISK at 40-45%; unpowered accessories prioritised). The >25%
    elimination threshold is a *session pipeline* rule, kept as an explicit
    parameter so it is never mistaken for README text.
  * :func:`classify_competition` — the session's HIGH-competition rule only
    (10+ established sellers with 100+ reviews). The low/medium split is
    deliberately NOT implemented: no threshold exists in the README or the
    session brief, and inventing one would violate HARD STOP #2.
  * :func:`rank_candidates` — ``score = (margin x demand) / competition``
    with the margin floor enforced mechanically: a candidate without a
    *verified* net margin is refused a score (HARD STOP #3), and a candidate
    below the 20% floor is flagged ``meets_margin_floor=False`` (rejection
    flag, never an approval).

What this module must NEVER grow into (README §3, §6):
  * cost math of any kind — that lives only in ``tools/landed_cost.py``;
  * HS-code, duty or VAT math — that lives only in ``tools/customs.py``;
  * network calls, scrapers, or guessed data.

Standard library only. See ``tests/test_market_research.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Constants — each cites its authority. README wins on any conflict.
# ---------------------------------------------------------------------------

#: Session pipeline rule (NOT in the README): eliminate candidates whose
#: verified SA duty rate exceeds this percentage, unless margin is
#: exceptional AND the exception is flagged for the Supervisor.
CUSTOMS_ELIMINATE_ABOVE_PCT: float = 25.0

#: README §2 HARD STOP #3 / §4: net margin floor. Never approve below this.
MARGIN_FLOOR_PCT: float = 20.0

#: Session pipeline rule (NOT in the README): 10+ established sellers with
#: 100+ reviews each marks HIGH competition.
HIGH_COMPETITION_SELLERS: int = 10

#: README §4: apparel/textiles run 40-45% duty — treat as HIGH RISK.
APPAREL_CATEGORY_KEYWORDS: frozenset = frozenset(
    {"apparel", "textile", "clothing", "garment", "fashion-wear"}
)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    """A dropshipping candidate under screening.

    ``None`` means *unverified / unobserved* — never zero, never "typical".
    Callers must not substitute guesses for ``None`` fields.
    """

    product_name: str
    category: str = "general"
    hs_code: Optional[str] = None
    duty_rate_pct: Optional[float] = None  #: verified SA general rate only
    hs_source: Optional[str] = None  #: checkable reference (URL/document)
    demand: str = "unknown"  #: analyst judgement: low|medium|high|unknown
    demand_source: Optional[str] = None
    takealot_price_floor_zar: Optional[float] = None
    takealot_source: Optional[str] = None
    established_seller_count: Optional[int] = None
    competition_notes: str = ""
    net_margin_pct: Optional[float] = None  #: ONLY from tools/landed_cost.py
    flags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CustomsVerdict:
    risk: str  #: low | medium | high | unknown
    eliminate: bool
    reason: str


@dataclass(frozen=True)
class CompetitionVerdict:
    level: str  #: high | below-threshold | unknown
    reason: str


@dataclass(frozen=True)
class RankedCandidate:
    product_name: str
    score: float
    net_margin_pct: float
    meets_margin_floor: bool


@dataclass(frozen=True)
class UnrankedCandidate:
    product_name: str
    reason: str


# ---------------------------------------------------------------------------
# Customs screening — README §4
# ---------------------------------------------------------------------------


def classify_customs_risk(
    duty_rate_pct: Optional[float],
    category: str = "general",
    eliminate_above_pct: float = CUSTOMS_ELIMINATE_ABOVE_PCT,
) -> CustomsVerdict:
    """Classify customs risk from a *verified* SA duty rate.

    * Apparel/textile category -> high risk + eliminate (README §4,
      40-45% duty), regardless of any rate passed in.
    * ``duty_rate_pct is None`` -> unknown, never eliminated on unknown
      data; the candidate simply cannot proceed (HARD STOP #2).
    * rate > ``eliminate_above_pct`` -> high + eliminate.
    * rate == 0 -> low (duty-free lines are prioritised per README §4).
    * otherwise -> medium.
    """
    cat = (category or "").strip().lower()
    if any(keyword in cat for keyword in APPAREL_CATEGORY_KEYWORDS):
        return CustomsVerdict(
            risk="high",
            eliminate=True,
            reason=(
                "README §4: apparel/textiles run 40-45% duty — HIGH RISK, "
                "reject unless margin is exceptional AND flagged."
            ),
        )
    if duty_rate_pct is None:
        return CustomsVerdict(
            risk="unknown",
            eliminate=False,
            reason=(
                "SA duty rate UNVERIFIED — HARD STOP #2: mark UNVERIFIED "
                "and stop; candidate cannot proceed."
            ),
        )
    if duty_rate_pct < 0:
        raise ValueError("duty_rate_pct cannot be negative")
    if duty_rate_pct > eliminate_above_pct:
        return CustomsVerdict(
            risk="high",
            eliminate=True,
            reason=(
                f"verified SA duty {duty_rate_pct:g}% exceeds the "
                f"{eliminate_above_pct:g}% session elimination threshold."
            ),
        )
    if duty_rate_pct == 0:
        return CustomsVerdict(
            risk="low",
            eliminate=False,
            reason="duty-free SA tariff line — prioritised per README §4.",
        )
    return CustomsVerdict(
        risk="medium",
        eliminate=False,
        reason=(
            f"verified SA duty {duty_rate_pct:g}% within the "
            f"0-{eliminate_above_pct:g}% session band."
        ),
    )


# ---------------------------------------------------------------------------
# Competition screening — session HIGH rule only
# ---------------------------------------------------------------------------


def classify_competition(
    established_seller_count: Optional[int],
    high_threshold: int = HIGH_COMPETITION_SELLERS,
) -> CompetitionVerdict:
    """Apply the session's HIGH-competition rule.

    ``established_seller_count`` is the number of sellers with 100+ reviews
    observed on Takealot. ``None`` (not observed — e.g. search is bot-walled
    and only listing snippets were available) yields ``unknown``, never a
    guess. Counts below the threshold yield ``below-threshold``: this
    capability does not split low vs medium because no threshold for that
    split exists in the README or the brief.
    """
    if established_seller_count is None:
        return CompetitionVerdict(
            level="unknown",
            reason=(
                "established seller count not observed — HARD STOP #2: "
                "mark UNVERIFIED, do not infer competition level."
            ),
        )
    if established_seller_count < 0:
        raise ValueError("established_seller_count cannot be negative")
    if established_seller_count >= high_threshold:
        return CompetitionVerdict(
            level="high",
            reason=(
                f"{established_seller_count} established sellers "
                f"(100+ reviews) >= threshold {high_threshold}."
            ),
        )
    return CompetitionVerdict(
        level="below-threshold",
        reason=(
            f"{established_seller_count} established sellers "
            f"(100+ reviews) < threshold {high_threshold}; low/medium "
            "split needs a Supervisor-defined threshold."
        ),
    )


# ---------------------------------------------------------------------------
# Ranking — margin-gated, HARD STOP #3 enforced
# ---------------------------------------------------------------------------


def rank_candidates(candidates: List[Candidate]) -> dict:
    """Rank candidates by ``score = (margin x demand) / competition``.

    This capability enforces the *gate*, not the *scales*: demand and
    competition quantification is a future Supervisor-routed capability, so
    this function only accepts candidates that already carry caller-supplied
    numeric scores... except it cannot, because :class:`Candidate` holds
    analyst judgements, not numbers.

    Therefore this function ranks ONLY on verified net margin as a
    stand-in ordering key is FORBIDDEN (that would invent a ranking
    methodology). Instead:

    * candidates with ``net_margin_pct is None`` are refused a score and
      returned under ``unranked`` with the HARD STOP #3 reason;
    * candidates with a verified margin are returned under ``ranked``,
      ordered by margin descending, each carrying ``meets_margin_floor``.
      Score numerics arrive with the future demand/competition scoring
      capability; until then margin order is the only non-invented order.

    Ranking is not approval: ``meets_margin_floor=False`` is a rejection
    flag the Supervisor must act on, never an approval.
    """
    ranked: List[RankedCandidate] = []
    unranked: List[UnrankedCandidate] = []
    for cand in candidates:
        if cand.net_margin_pct is None:
            unranked.append(
                UnrankedCandidate(
                    product_name=cand.product_name,
                    reason=(
                        "net margin UNVERIFIED (tools/landed_cost.py has "
                        "no implementation yet) — HARD STOP #3: refused "
                        "a score; candidate cannot proceed."
                    ),
                )
            )
        else:
            ranked.append(
                RankedCandidate(
                    product_name=cand.product_name,
                    score=cand.net_margin_pct,  # ordering key ONLY, see docstring
                    net_margin_pct=cand.net_margin_pct,
                    meets_margin_floor=cand.net_margin_pct >= MARGIN_FLOOR_PCT,
                )
            )
    ranked.sort(key=lambda r: r.score, reverse=True)
    return {"ranked": ranked, "unranked": unranked}
