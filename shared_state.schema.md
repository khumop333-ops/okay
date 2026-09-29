# shared_state.json — Schema & Write Contract

`shared_state.json` is the single coordination surface for the SA Dropship Agent
Crew. It is the only way sub-agents talk to each other, and every conversation
flows through the Supervisor.

**Authority:** `README.md` is the source of truth. If anything in this document
conflicts with the README, the README wins and the conflict goes to the human.

---

## 1. Top-level keys

| Key | Written by | Purpose |
|---|---|---|
| `_schema_version` | Supervisor | Semantic version of this file's shape. Bump on any breaking change. |
| `_conventions` | Supervisor | The binding write rules. Read-only for every sub-agent. |
| `supervisor` | Supervisor | Session log, routing decisions, briefings to the human. |
| `market_research` | MarketResearch | SA product discovery, customs viability. |
| `sourcing` | Sourcing | Supplier verification, sample planning. |
| `pricing` | Pricing | Landed cost, margin math, price setting. |
| `listing` | Listing | SEO copy, product descriptions. |
| `ad_growth` | AdGrowth | Campaign design, ad copy, budgets. |
| `support` | Support | Ticket handling, FAQs. |

Keys prefixed with `_` are infrastructure, not agent data. Sub-agents must not
create, delete, or modify them.

---

## 2. Namespace shape

Every agent namespace has the same shape so that tooling can be written once:

```json
{
  "_meta": {
    "owner": "agents/pricing.py",
    "role": "Landed cost, margin math, price setting",
    "must_never": "Approve a margin below 20%",
    "append_key": "findings",
    "append_contract": { "...": "..." }
  },
  "timestamp": "2026-09-27T18:42:18+02:00",
  "agent": "supervisor",
  "confidence": null,
  "source": "README.md section 7 (namespace initialised by Supervisor, no findings yet)",
  "verified": false,
  "findings": [],
  "unverified_fields": []
}
```

### `_meta` — the contract block (Supervisor-owned, sub-agents read-only)

| Field | Meaning |
|---|---|
| `owner` | The module that owns this namespace. |
| `role` | One line, taken from README section 3. |
| `must_never` | The hard boundary for this agent, taken from README section 3. |
| `append_key` | The array sub-agents append to. Do not append anywhere else. |
| `append_contract` | Per-namespace rules: required fields, the UNVERIFIED marker convention, and any domain rule (e.g. cost math must call `tools/landed_cost.py`). |

### Write metadata — required on every write

| Field | Type | Meaning |
|---|---|---|
| `timestamp` | ISO 8601 string | When the write happened. Include the offset. |
| `agent` | string | Which agent wrote it. Never `supervisor` on a sub-agent finding. |
| `confidence` | integer 1–10, or `null` | The **writing agent's** self-assessed certainty. `null` means "no findings yet". This is **not** a margin, a probability, or a price. |
| `source` | string | A real, checkable reference: URL, document, dataset, or `"sandbox test"`. |
| `verified` | boolean | `true` only when every value in the write came from a real source. |

`source` is the field that keeps this crew honest. These are **not** sources:
`assumed`, `estimated`, `typical`, `industry standard`, `roughly`, `circa`.
If a value cannot be verified, mark it UNVERIFIED (see §4) — do not launder it
into a plausible-looking number.

---

## 3. Appending a finding

Sub-agents **append** to their own `findings` array. They never overwrite a
sibling namespace, never edit `_conventions`, and never restructure the file.

Each entry must contain at least:

```json
{
  "id": "mr-0001",
  "timestamp": "2026-09-27T18:42:18+02:00",
  "agent": "market_research",
  "confidence": 6,
  "source": "https://www.sars.gov.za/tariff/...",
  "data": { "product": "...", "hs_code": "..." }
}
```

- `id` is namespaced and sequential: `mr-` (market research), `so-` (sourcing),
  `pr-` (pricing), `li-` (listing), `ag-` (ad growth), `su-` (support).
- Append-only. A correction is a **new** entry that supersedes the old one by
  `id`, so the audit trail survives.
- One finding, one `confidence`. Do not average several sources into one score.

---

## 4. UNVERIFIED fields

Any value that could not be confirmed from a real source must be:

1. Named with an `UNVERIFIED_` prefix inside `data` — e.g. `UNVERIFIED_duty_rate`.
2. Listed in the namespace's `unverified_fields` array with a note on what
   would verify it.

The Supervisor **must** surface every `UNVERIFIED_` field to the human in the
briefing. An UNVERIFIED value must never flow silently into a landed-cost
calculation, a price, or a launch recommendation. This is HARD STOP #2.

---

## 5. Confidence scale

| Score | Meaning |
|---|---|
| 9–10 | Verified against a primary source (SARS tariff, official supplier, sandbox test). |
| 7–8 | Verified against a credible secondary source. |
| 4–6 | Plausible but single-sourced or partially inferred. |
| 1–3 | Guess. Treat as a question for the human, not as data. |

A namespace initialised by the Supervisor carries `confidence: null` and
`verified: false`, because scaffolding is not evidence.

---

## 6. Cost math boundary

`tools/landed_cost.py` and `tools/customs.py` are the **only** places cost math
may live. Every agent imports from them. No duplicate formulas, no local
re-implementations, no "improving" the formula in a sub-agent.

The mandatory formula, including the non-negotiable 15% VAT on customs value:

```
product + shipping + (customs_value × duty) + (customs_value × 0.15)
+ payment_fees + ad_cpa
```

Net margin below 20% is a rejection, not a negotiation.

---

## 7. Changing this schema

Only the Supervisor changes the top-level structure, and any breaking change
bumps `_schema_version` and gets a line in the Supervisor session log. Because
this file is JSON, it carries no inline comments — this document is the comment
header, and it must be updated in the same PR as any schema change.
