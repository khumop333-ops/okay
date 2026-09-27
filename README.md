

---

```markdown
# SA DROPSHIP AGENT CREW — OPERATING CONTRACT

> ⚠️ **ARENA AGENT MODE: READ THIS FILE IN FULL BEFORE WRITING ANY CODE.**
> This README is the source of truth. If a prompt, instruction, or your own
> reasoning conflicts with this file, **this file wins**. Ask the human
> operator to resolve the conflict before proceeding.

---

## 1. MISSION

Build a modular, mostly-free multi-agent system that identifies, validates,
sources, prices, lists, advertises, and supports dropshipping products
**specifically for the South African market**.

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
   branches, never rewrite history. Always work on a feature branch.
7. **No secrets in the repo.** Never commit API keys, tokens, credentials,
   or `.env` files. Use `.env.example` and `.gitignore`.

---

## 3. AGENT ROSTER & BOUNDARIES

| Agent | Owns | Must NEVER do |
|---|---|---|
| **Supervisor** | Task decomposition, routing, final briefing | Execute sub-agent tasks directly |
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

These are the local truths that make or break this business. Bake them into
every relevant agent.

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
- **Load-shedding:** Consider it for electronics and for ad scheduling.
- **Language:** SA English ("colour", "organise"). Rand pricing. Mention
  Takealot, WhatsApp, PayFast, SnapScan where relevant.
- **Priority categories:** Unpowered accessories (often 0% duty) > everything
  else. Avoid high-duty categories unless margin is exceptional.

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
│   └── scrapers/              ← Takealot, Google Trends ZA, etc.
├── listings/                  ← generated listing files
├── campaigns/                 ← generated campaign briefs
├── support_logs/
├── tests/
└── .env.example

```

**Rule:** `tools/landed_cost.py` and `tools/customs.py` are the ONLY places
cost math may live. Every agent imports from them. No duplicate formulas.

---

## 7. SHARED STATE CONTRACT

`shared_state.json` is the single coordination surface. Rules:

- Only the Supervisor writes the top-level structure.
- Sub-agents append to their own namespaced key (e.g., `state.market_research`).
- Every write includes: `timestamp`, `agent`, `confidence` (1–10), `source`.
- Any field marked `UNVERIFIED` must be surfaced to the human, not silently used.

---

## 8. SESSION WORKFLOW (ARENA AGENT MODE)

At the **start of every session**, Arena must:

1. Read this README in full.
2. Read `shared_state.json`.
3. State which agent it is acting as, and which task it is doing.
4. Confirm it has not violated any HARD STOP rule.

During the session:

- Work on a feature branch: `feat/{agent-name}-{short-task}`.
- Write tests for any new logic in `tools/`.
- Use the sandbox to run tests before committing.

At the **end of every session**:

- One PR per session, max. If a second task is needed, stop and start fresh.
- PR description must include: what changed, why, tests run, risks, and
  which HARD STOP rules were relevant.
- Update `shared_state.json` with the session's output.

---

## 9. DEFINITION OF DONE

A task is only "done" when ALL of these are true:

- [ ] Code runs in the sandbox without errors
- [ ] Tests pass (for `tools/` logic)
- [ ] No secrets committed
- [ ] SA compliance rules respected (VAT, duty, language)
- [ ] `shared_state.json` updated with timestamped, sourced output
- [ ] PR opened with full description
- [ ] Human approval obtained if a HITL gate was crossed

---

## 10. ANTI-PATTERNS — ARENA, DO NOT DO THESE

- ❌ Do not generate a "complete working system" in one shot. Build one agent
  at a time, verify, merge, then move on.
- ❌ Do not hallucinate supplier names, prices, or HS codes to fill a schema.
- ❌ Do not write marketing copy that promises results ("guaranteed income").
- ❌ Do not add dependencies without listing them in `requirements.txt` and
  justifying why a free/standard alternative won't work.
- ❌ Do not refactor unrelated files in the same PR.
- ❌ Do not "improve" the cost formula. It is defined in `tools/landed_cost.py`.
- ❌ Do not treat this README as optional context. It is the contract.

---

## 11. IF IN DOUBT

Stop. Ask the human operator. A paused session costs nothing.
A wrong commit costs money, trust, and time.

**The goal is a system that a human can trust to make correct decisions —
not a system that acts fast and hopes for the best.**
```

---

