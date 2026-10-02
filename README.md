```markdown
# SA DROPSHIP AGENT CREW — OPERATING CONTRACT

> ⚠️ **ARENA AGENT MODE: READ THIS FILE IN FULL BEFORE WRITING ANY CODE.**
> This README is the source of truth. If a prompt, instruction, or your own
> reasoning conflicts with this file, **this file wins**. Ask the human
> operator to resolve the conflict before proceeding.

---

## 1. MISSION

Build a modular, mostly-free multi-agent system that identifies, validates,
sources, prices, lists, advertises, and supports products **specifically for
the South African market**, under one of three viable business models:

1. **Local SA dropshipping.** A South African supplier holds the stock and
   ships to our customer.
2. **High-ticket items.** Few, high-value sales where one order carries the
   margin.
3. **Digital products.** Delivered electronically, with no physical stock.

The order above is not a priority order. The operator chooses the starting
model; the current choice is recorded in `shared_state.json`
(`state.supervisor.findings`), not in this contract.

**Retired model: import-from-China dropshipping.** The operator has confirmed
there is no capital for bulk import, so this model is retired and must not be
revived without an operator amendment to this section. The research built for
it is archived as background in `shared_state.json` and is not live pipeline
input.

This is a **software engineering project**, not a get-rich-quick scheme.
Optimize for correctness, verifiability, and reversibility — never for speed
at the cost of accuracy.

---

## 2. NON-NEGOTIABLE RULES (HARD STOPS)

Arena must STOP and ask the human operator before proceeding if any of these
would be violated:

1. **No autonomous spending.** Never call a paid API, place a sample order,
   launch an ad, or commit to a financial transaction without explicit
   written approval in the current session.
2. **No guessed data.** Never invent HS codes, duty rates, supplier costs,
   shipping times, or competitor prices. If a value cannot be verified from
   a real source, mark it `UNVERIFIED` and stop.
3. **No margin < 20%.** Never approve a product whose net margin (after
   product + shipping + duty + 15% VAT + payment fees + ad CPA) is below 20%.
   Reject it and explain why.
4. **No skipping VAT.** Every landed-cost calculation MUST include 15% VAT
   on the customs value. There are no exceptions.
5. **No direct-to-human sub-agent output.** Sub-agents report to the
   Supervisor Agent. Only the Supervisor Agent addresses the human.
6. **No destructive git operations.** Never force-push, never delete
   branches, never rewrite history.
7. **No secrets in the repo.** Never commit API keys, tokens, credentials,
   or `.env` files. Use `.env.example` and `.gitignore`.
8. **No session without a state file.** See §8, Session Precondition. If
   `shared_state.json` does not exist on `main`, do not open a sub-agent
   session. Run the Supervisor scaffold first.
9. **No unmerged carry-over.** A session's PR must be merged to `main`
   before the next session opens. Unmerged branches do not carry forward.

---

## 3. AGENT ROSTER & BOUNDARIES

| Agent | Owns | Must NEVER do |
|---|---|---|
| **Supervisor** | Task decomposition, routing, final briefing, top-level state structure | Execute sub-agent tasks directly |
| **MarketResearch** | SA product discovery, customs viability | Recommend without verified HS code |
| **Sourcing** | Supplier verification, sample planning | Commit to purchases |
| **Pricing** | Landed cost, margin math, price setting | Approve margin < 20% |
| **Listing** | SEO copy, product descriptions | Make unverifiable claims |
| **AdGrowth** | Campaign design, ad copy, budgets | Launch campaigns without approval |
| **Support** | Ticket handling, FAQs | Promise refunds/replacements |

Each agent lives in `agents/` as its own module. No agent imports another
agent directly — all coordination flows through the Supervisor via
`shared_state.json`.

---

## 4. SOUTH AFRICA COMPLIANCE RULES

- **VAT:** 15% on customs value. Always.
- **Import Duty:** Look up the real HS code on the SARS tariff database.
  Apparel/textiles run 40–45% — treat as HIGH RISK.
- **Landed Cost Formula:**
```

product + shipping + (customs_value × duty) + (customs_value × 0.15)

· payment_fees + ad_cpa

```
- **Ad CPA benchmark (ZA):** R150–R300 per conversion.
- **Shipping reality:** Customs clearance adds 5–15 business days. Flag any
  supplier whose total delivery exceeds 21 days.
- **Load-shedding:** Consider it for electronics and ad scheduling.
- **Language:** SA English ("colour", "organise"). Rand pricing. Mention
  Takealot, WhatsApp, PayFast, SnapScan where relevant.
- **Priority categories:** Unpowered accessories (often 0% duty) > everything
  else. Avoid high-duty categories unless margin is exceptional.

### Model-Specific Rules

The import math in this README — HS-code lookup, SARS duty, import VAT
(customs-value or ATV basis), the landed-cost formula, and the clearance-delay
flag — applies only to a product a model actually imports. A product that is
not imported is not subject to it, but §2 still binds every model, including
the 20% margin floor and the no-guessed-data rule. Compliance detail for each
model lives in that model's agent prompts, not here.

**Local dropship.** A South African supplier holds the stock and ships to our
customer. We do not import, so the import math above does not apply.

**High-ticket.** Few, high-value sales where one order carries the margin. The
import math above applies only if the item is imported.

**Digital.** Products delivered electronically, with no physical stock,
shipping, or customs. The import math above does not apply.

---

## 5. HUMAN-IN-THE-LOOP GATES

Arena must pause and request approval at every one of these gates:

1. Before writing code that calls any paid service
2. Before placing any sample order
3. Before recommending a product to launch
4. Before launching any ad campaign
5. Before merging a PR that touches pricing logic or customs math
6. Before any refund, replacement, or customer-facing commitment

Approval format: the agent states **what it wants to do, why, the cost, and
the risk**. The human replies with `APPROVED` or `REJECTED` plus reason.

---

## 6. REPOSITORY STRUCTURE

```

/
├── README.md                  ← this contract
├── shared_state.json          ← inter-agent state (single source of truth)
├── shared_state.schema.md     ← field documentation
├── agents/
│   ├── supervisor.py
│   ├── market_research.py
│   ├── sourcing.py
│   ├── pricing.py
│   ├── listing.py
│   ├── ad_growth.py
│   └── support.py
├── tools/
│   ├── customs.py             ← HS code + duty + VAT calculator
│   ├── landed_cost.py         ← single source of truth for cost math
│   └── scrapers/
├── listings/
├── campaigns/
├── support_logs/
├── tests/
├── requirements.txt
├── .gitignore
└── .env.example

```

**Rule:** `tools/landed_cost.py` and `tools/customs.py` are the ONLY places
cost math may live. Every agent imports from them. No duplicate formulas.

---

## 7. SHARED STATE CONTRACT

`shared_state.json` is the single coordination surface. Rules:

- Only the Supervisor writes the top-level structure.
- Sub-agents append only to their own namespaced key (e.g., `state.market_research`).
- Every write includes: `timestamp`, `agent`, `confidence` (1–10), `source`, `verified`.
- Any field marked `UNVERIFIED` must be surfaced to the human, not silently used.

Top-level namespaces: `supervisor`, `market_research`, `sourcing`, `pricing`,
`listing`, `ad_growth`, `support`.

---

## 8. SESSION WORKFLOW (ARENA AGENT MODE)

### Session Precondition (READ BEFORE OPENING A SESSION)

Before opening **any** Agent Mode session that is not a Supervisor bootstrap
session, confirm the `main` branch contains `shared_state.json`. If it does
not, **do not open the session**. The correct action is to run a Supervisor
bootstrap session first (§9, Phase 0).

A sub-agent session against an empty tree is contractually forbidden and must
halt without opening a PR. Repeating this halt across sessions is a process
bug, not agent behavior.

### Branch Naming

Preferred: `feat/{agent}-{short-task}`.

**Exception:** When the execution harness pins a branch name (e.g.
`arena/{session-id}`), that pinned name takes precedence. The safety intent
of this rule — no commits to `main`, one PR per session, one agent per
session — still applies and must not be violated. If a harness pins the
session to `main`, that is a real violation: halt.

### At the Start of Every Session

1. Read this README in full.
2. Read `shared_state.json`.
3. State which agent it is acting as, and which task it is doing.
4. Confirm it has not violated any HARD STOP rule.
5. Confirm the task fits in ONE PR this session.

### During the Session

- Work on the harness-provided or `feat/` branch.
- Write tests for any new logic in `tools/`.
- Use the sandbox to run tests before committing.

### At the End of Every Session

- ONE PR per session, maximum.
- PR description must include: what changed, why, tests run, risks, and
  which HARD STOP rules were relevant.
- Update `shared_state.json` with the session's output.
- Push the branch to remote BEFORE the session ends. Arena sandboxes are
  ephemeral — a local commit that is not pushed is permanently lost when
  the session closes. Push is not optional.
- **Merge rule:** the human operator must merge this PR to `main` before the
  next session opens. Unmerged PRs do not carry forward. This is the only
  manual step in the loop, and it is non-optional.

---

## 9. BUILD PHASES

### Phase 0 — Bootstrap (ONE consolidated PR, Supervisor only)

Purpose: produce the minimum viable foundation so sub-agent sessions can
start against a real tree. This phase deliberately overrides the "one agent
at a time" rule, because none of the items below are agent logic.

Single PR scope:
- `shared_state.json` with all seven namespaces and the metadata schema
- `shared_state.schema.md`
- Directory skeleton per §6
- `.gitignore`, `.env.example`, `requirements.txt`

No agent code. No `tools/` cost math. No scrapers.

### Phase 1+ — One Agent, One Capability, One PR

After Phase 0 is merged:

1. Supervisor routes the first goal.
2. Sub-agents are built one capability at a time, in dependency order:
   Market Research → Sourcing → Pricing → Listing → Ad Growth → Support.
3. Each capability is its own PR, merged to `main` before the next opens.

Do not build a "complete agent" in one session. Build the smallest capability
that produces a verifiable output and exercises the state contract.

---

## 10. DEFINITION OF DONE

A task is only "done" when ALL of these are true:

- [ ] Code runs in the sandbox without errors
- [ ] Tests pass (for `tools/` logic)
- [ ] No secrets committed
- [ ] SA compliance rules respected (VAT, duty, language)
- [ ] `shared_state.json` updated with timestamped, sourced output
- [ ] PR opened with full description
- [ ] PR **merged to `main`** before the next session opens
- [ ] Human approval obtained if a HITL gate was crossed

---

## 11. ANTI-PATTERNS — ARENA, DO NOT DO THESE

- ❌ Do not generate a "complete working system" in one shot.
- ❌ Do not hallucinate supplier names, prices, or HS codes to fill a schema.
- ❌ Do not write marketing copy that promises results.
- ❌ Do not add dependencies without listing them in `requirements.txt`.
- ❌ Do not refactor unrelated files in the same PR.
- ❌ Do not "improve" the cost formula. It lives in `tools/landed_cost.py`.
- ❌ Do not open a sub-agent session against an empty `shared_state.json`.
- ❌ Do not accumulate unmerged branches. Merge or close, then move on.
- ❌ Do not treat this README as optional context. It is the contract.

---

## 12. IF IN DOUBT

Stop. Ask the human operator. A paused session costs nothing.

**The goal is a system that a human can trust to make correct decisions —
not a system that acts fast and hopes for the best.**
```

---