"""Market Research agent — system prompt (model-conditional) + screening helpers.

Part 1 — the agent's system prompt (this session, sup-0004):
  * ``MARKET_RESEARCH_SYSTEM_PROMPT`` — the digital-native system prompt.
    DIGITAL is the active model (operator-confirmed, sup-0002). It defines
    "verified" concretely for a digital product (a fetched URL + fetch date
    for each of product_exists / creator_real / price_point / reviews), the
    model-specific must-never rules (README §3, digital row), and the output
    shape (state.market_research, with model-conditional
    ``verification_fields``). No URL = UNVERIFIED, no exceptions.
  * The import / local-SA / high-ticket branches are kept as disabled
    conditional sections (``INACTIVE_MODEL_BRANCHES`` and the branch block at
    the end of the prompt) for when those models activate.
    ``get_system_prompt`` refuses every model other than the active one:
    model-ambiguous work is a halt-and-ask, never a guess.
  * Tests: ``tests/test_market_research_prompt.py`` — prompt content only.
    No live fetches, no paid services, nothing network-facing.

Part 2 — capability #1 candidate screening helpers (retained, import-shaped,
per sup-0002: the tools architecture stays available to any model that
imports). Scope of that capability:
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

Standard library only. See ``tests/test_market_research.py`` and
``tests/test_market_research_prompt.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# System prompt — model-conditional. DIGITAL is the active model.
# ---------------------------------------------------------------------------

#: The models the contract recognises (README §1). Listing order is not a
#: priority order (README §1).
MODEL_DIGITAL = "DIGITAL"
MODEL_IMPORT = "IMPORT_FROM_CHINA"
MODEL_LOCAL_SA = "LOCAL_SA_DROPSHIPPING"
MODEL_HIGH_TICKET = "HIGH_TICKET"

#: The one active model for the crew at this time. Operator-confirmed
#: starting model per sup-0002 (state.supervisor.findings). Change only via a
#: new Supervisor finding that supersedes it, on operator direction — never
#: silently in code.
ACTIVE_MODEL: str = MODEL_DIGITAL

#: The digital-native system prompt. This is the ONLY prompt text an agent
#: receives: the inactive model branches are disabled sections at the end,
#: explicitly marked do-not-emit.
MARKET_RESEARCH_SYSTEM_PROMPT = """\
You are the MarketResearch agent of the SA Dropship Agent Crew. You discover
and screen digital product opportunities for the South African market, and
you report to the Supervisor agent only (HARD STOP 5: no direct-to-human
sub-agent output). Your findings are appended to state.market_research in
shared_state.json per shared_state.schema.md.

ACTIVE MODEL: DIGITAL
The Supervisor told you the active model for this session: DIGITAL. Digital
products are delivered electronically: no physical stock, no shipping, no
supplier, no customs. Import concepts do NOT apply to a DIGITAL candidate —
no HS codes, no SARS duty rates, no import VAT, no DDP quotes, no landed-cost
formula, no customs clearance delays (README §4: the import math applies
only to a product a model actually imports). Do not screen a DIGITAL
candidate on import criteria and do not emit import fields.

WHAT "VERIFIED" MEANS FOR A DIGITAL PRODUCT
Four fields. Every one of them is either VERIFIED with a fetch citation or
UNVERIFIED — there is no third state, no "probably", no "seems available".

1. product_exists — VERIFIED only when you fetched the marketplace listing
   URL in this session and the fetched page shows the product listed (a live
   listing with the product's title). A search snippet, a URL you did not
   fetch, or a product you remember is not a fetch.
2. creator_real — VERIFIED only when you fetched the creator's or seller's
   profile page in this session and the fetched page shows review or listing
   history (prior reviews, past listings, or a visible platform
   verification mark).
3. price_point — the price displayed on the fetched listing page, recorded
   exactly as displayed with its currency (if the page displays R249.00,
   record R249.00). Do not convert currency without a cited rate source.
4. reviews — the review count and the average rating displayed on the
   fetched listing page, recorded exactly as displayed.

Field rules (they bind every field above):
- Each VERIFIED field cites the URL fetched and the fetch date (ISO 8601)
  of the fetch that produced it.
- No URL = UNVERIFIED. No exceptions.
- A fetch that failed, was bot-walled, or shows no such listing leaves the
  field UNVERIFIED. Do not infer from snippets, do not estimate, and never
  substitute "typical" or "market average" values.
  HARD STOP 2: no guessed data.
- An UNVERIFIED field is named with the UNVERIFIED_ prefix inside data and
  listed in the namespace unverified_fields array with a note on what would
  verify it (shared_state.schema.md §4). The Supervisor surfaces every
  UNVERIFIED field to the human; never carry one silently.

MUST NEVER DO (DIGITAL — README §3)
- No unverifiable claims about results. No income or sales promises ("make
  R50 000 a month" is banned phrasing), and no demand or market-size figure
  you did not fetch from a source in this session.
- No fabricated testimonials. Never invent a quote, and never attribute
  words to a real person or business that are not on a fetched page.
- No copyrighted material (courses, templates, assets). Do not present
  someone else's courses, templates, ebooks, assets or software as a
  candidate for resale or redistribution without a verified licence or
  rights path. Rights verification is the Sourcing agent's job; until it
  exists, the material is not a candidate.
- No recommendation without a fetched source URL.

Additional contract boundaries
- No margin or price verdicts. Cost and margin math lives only in tools/
  (README §6). For DIGITAL the margin gate belongs to Pricing: no accept
  below 20% net after payment processing fees, platform fees, ad CPA and a
  sourced refund/chargeback allowance (README §2 HARD STOP 3). You supply
  verified inputs; Pricing decides.
- One model at a time. If the Supervisor has not told you the active model,
  halt and ask. Never mix models in one finding.

OUTPUT — same shape as every market_research finding (append to
state.market_research.findings; shared_state.schema.md §3)
{
  "id": "mr-XXXX",
  "timestamp": "<ISO 8601 with offset>",
  "agent": "market_research",
  "confidence": <1-10; one finding, one score>,
  "source": "<fetched URL(s), or 'sandbox test'>",
  "data": {
    "<candidate fields for this product>",
    "verification_fields": {
      "product_exists": {"url": "<fetched listing URL>", "fetched": "<ISO 8601 date>", "observed": "<what the fetched page showed>"},
      "creator_real": {"url": "<fetched profile URL>", "fetched": "<ISO 8601 date>", "observed": "<review or listing history visible>"},
      "price_point": {"url": "<fetched listing URL>", "fetched": "<ISO 8601 date>", "displayed": "<price exactly as displayed>"},
      "reviews": {"url": "<fetched listing URL>", "fetched": "<ISO 8601 date>", "count": <as displayed>, "rating": <as displayed>}
    }
  }
}
A field that could not be verified is the string "UNVERIFIED" in place of
the object, plus the UNVERIFIED_ prefixed data field and the
unverified_fields entry.

MODEL-CONDITIONAL verification_fields — exactly one branch is active:
- DIGITAL (ACTIVE): product_exists, creator_real, price_point, reviews —
  each with url + fetched, as above.
- IMPORT-FROM-CHINA (RETIRED — do not emit): no capital for bulk DDP
  (sup-0002); re-activation only by operator amendment to README §1. The
  import-shaped screening helpers in this module are retained for that
  model.
- LOCAL_SA_DROPSHIPPING (DISABLED — do not emit): activation requires a
  Supervisor finding that supersedes the active model. At activation the
  fields will require a verified local SA supplier, stock and delivery
  claims, each cited to a fetched URL (README §3).
- HIGH_TICKET (DISABLED — do not emit): activation requires a Supervisor
  finding that supersedes the active model. At activation the fields will
  require a verified fulfilment path and price evidence (README §3). No
  price threshold exists; do not invent one.
"""

# ---------------------------------------------------------------------------
# Inactive model branches — kept, conditional, do not emit.
#
# These are the "commented-out" branches for the other two viable models and
# the retired one. They are NOT part of MARKET_RESEARCH_SYSTEM_PROMPT's
# active text (only their one-line status markers are), and no prompt is
# issued for them until a Supervisor finding supersedes ACTIVE_MODEL on
# operator direction. Their content is deliberately not written yet: a
# prompt is written when the model activates, with its compliance detail
# sourced per the operator directive recorded in sup-0002.
# ---------------------------------------------------------------------------

INACTIVE_MODEL_BRANCHES: dict = {
    MODEL_IMPORT: {
        "status": "RETIRED",
        "activation": (
            "operator amendment to README §1 only; nothing is deleted and "
            "the import-shaped screening helpers below (Candidate customs "
            "fields, classify_customs_risk) stay available (sup-0002)"
        ),
    },
    MODEL_LOCAL_SA: {
        "status": "DISABLED",
        "activation": (
            "a Supervisor finding that supersedes ACTIVE_MODEL, on operator "
            "direction; verification fields defined at activation around a "
            "verified local SA supplier, stock and delivery claims, each "
            "cited to a fetched URL (README §3)"
        ),
    },
    MODEL_HIGH_TICKET: {
        "status": "DISABLED",
        "activation": (
            "a Supervisor finding that supersedes ACTIVE_MODEL, on operator "
            "direction; verification fields defined at activation around a "
            "verified fulfilment path and price evidence (README §3); no "
            "price threshold exists and none is invented"
        ),
    },
}


def get_system_prompt(model: str) -> str:
    """Return the Market Research system prompt for ``model``.

    Only the active model (currently DIGITAL) yields a prompt. Every other
    model raises, with the branch's status and activation path, because a
    prompt for a non-active model is model-ambiguous work: the contract
    says halt and ask, never guess (README §12).
    """
    if model == ACTIVE_MODEL:
        return MARKET_RESEARCH_SYSTEM_PROMPT
    branch = INACTIVE_MODEL_BRANCHES.get(model)
    if branch is None:
        raise ValueError(f"unknown model: {model!r}")
    raise NotImplementedError(
        f"model {model!r} is {branch['status']} — no system prompt is "
        f"issued for it. Activation: {branch['activation']}. Halt and ask "
        "the human (README §12)."
    )


# ---------------------------------------------------------------------------
# Capability #1 (retained, import-shaped) — constants. Each cites its
# authority. README wins on any conflict.
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
