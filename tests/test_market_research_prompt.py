"""Tests for the Market Research digital-native system prompt (sup-0004).

Prompt-CONTENT tests only, per the session scope:

* assert the prompt module loads and exposes the system prompt constant;
* assert the prompt contains the required model-specific must-never
  clauses (README §3, digital row) and the concrete "verified" definition
  (fetched URL + fetch date per field, no URL = UNVERIFIED, no exceptions);
* assert the output schema keeps the state.market_research shape with
  model-conditional verification_fields;
* assert the inactive model branches are kept but conditional (no prompt
  is issued for a non-active model — model-ambiguous work halts).

Deliberately NOT behavioural: nothing here performs a live fetch, calls a
paid service, or evaluates the prompt against a live model (HARD STOP #1:
no autonomous spending; README §10: no network in the test run).
"""

import unittest

from agents import market_research as mr
from agents.market_research import (
    ACTIVE_MODEL,
    INACTIVE_MODEL_BRANCHES,
    MARKET_RESEARCH_SYSTEM_PROMPT,
    MODEL_DIGITAL,
    MODEL_HIGH_TICKET,
    MODEL_IMPORT,
    MODEL_LOCAL_SA,
    get_system_prompt,
)

PROMPT = MARKET_RESEARCH_SYSTEM_PROMPT


class TestPromptModuleLoads(unittest.TestCase):
    def test_constant_is_a_nonempty_string(self):
        self.assertIsInstance(MARKET_RESEARCH_SYSTEM_PROMPT, str)
        self.assertGreater(len(MARKET_RESEARCH_SYSTEM_PROMPT.strip()), 0)

    def test_active_model_is_digital(self):
        # Operator-confirmed starting model (sup-0002). The prompt module
        # must not silently disagree with the state.
        self.assertEqual(ACTIVE_MODEL, MODEL_DIGITAL)
        self.assertIn("ACTIVE MODEL: DIGITAL", PROMPT)

    def test_retained_screening_helpers_still_exported(self):
        # The rewrite ADDS the prompt; it must not delete capability #1
        # (retained per sup-0002 for any model that imports).
        for name in (
            "Candidate",
            "CustomsVerdict",
            "CompetitionVerdict",
            "classify_customs_risk",
            "classify_competition",
            "rank_candidates",
            "MARGIN_FLOOR_PCT",
        ):
            self.assertTrue(hasattr(mr, name), f"agents.market_research lost {name}")


class TestDigitalNativePrompt(unittest.TestCase):
    def test_walls_off_import_concepts_for_digital(self):
        self.assertIn("Import concepts do NOT apply to a DIGITAL candidate", PROMPT)
        # The import-shaped terms appear only to say they do not apply.
        self.assertIn("no HS codes", PROMPT)
        self.assertIn("no SARS duty rates", PROMPT)
        self.assertIn("no DDP quotes", PROMPT)
        self.assertIn("no customs clearance delays", PROMPT)

    def test_declares_model_ambiguity_is_a_halt(self):
        self.assertIn("If the Supervisor has not told you the active model", PROMPT)
        self.assertIn("halt and ask", PROMPT)


class TestVerifiedDefinition(unittest.TestCase):
    """The four-field, fetch-cited definition of "verified" (session scope 2)."""

    def test_all_four_fields_defined(self):
        self.assertIn("product_exists — VERIFIED only when you fetched the marketplace listing", PROMPT)
        self.assertIn("creator_real — VERIFIED only when you fetched the creator's or seller's", PROMPT)
        self.assertIn("price_point — the price displayed on the fetched listing page", PROMPT)
        self.assertIn("reviews — the review count and the average rating displayed", PROMPT)

    def test_each_verification_requires_url_and_fetch_date(self):
        self.assertIn("cites the URL fetched and the fetch date (ISO 8601)", PROMPT)

    def test_no_url_is_unverified_no_exceptions(self):
        self.assertIn("No URL = UNVERIFIED. No exceptions.", PROMPT)

    def test_no_third_state_and_no_guessing(self):
        self.assertIn("there is no third state", PROMPT)
        self.assertIn("HARD STOP 2: no guessed data", PROMPT)

    def test_snippets_and_memory_are_not_fetches(self):
        self.assertIn("is not a fetch", PROMPT)


class TestMustNeverClauses(unittest.TestCase):
    """The model-specific must-never rules (README §3, digital row)."""

    def test_must_never_section_exists(self):
        self.assertIn("MUST NEVER DO (DIGITAL — README §3)", PROMPT)

    def test_no_unverifiable_claims_about_results(self):
        self.assertIn("No unverifiable claims about results", PROMPT)

    def test_no_fabricated_testimonials(self):
        self.assertIn("No fabricated testimonials", PROMPT)

    def test_no_copyrighted_material(self):
        self.assertIn("No copyrighted material (courses, templates, assets)", PROMPT)

    def test_no_recommendation_without_fetched_source_url(self):
        self.assertIn("No recommendation without a fetched source URL", PROMPT)


class TestOutputSchema(unittest.TestCase):
    """Same state.market_research shape, model-conditional verification_fields."""

    def test_finding_envelope_fields(self):
        for token in (
            '"id": "mr-XXXX"',
            '"timestamp"',
            '"agent": "market_research"',
            '"confidence"',
            '"source"',
            '"data"',
        ):
            self.assertIn(token, PROMPT)

    def test_verification_fields_are_model_conditional(self):
        self.assertIn("MODEL-CONDITIONAL verification_fields", PROMPT)
        self.assertIn("DIGITAL (ACTIVE)", PROMPT)
        self.assertIn("IMPORT-FROM-CHINA (RETIRED — do not emit)", PROMPT)
        self.assertIn("LOCAL_SA_DROPSHIPPING (DISABLED — do not emit)", PROMPT)
        self.assertIn("HIGH_TICKET (DISABLED — do not emit)", PROMPT)

    def test_unverified_marker_convention_preserved(self):
        self.assertIn("UNVERIFIED_", PROMPT)
        self.assertIn("unverified_fields", PROMPT)

    def test_margin_gate_belongs_to_pricing(self):
        # MarketResearch supplies verified inputs; it must not verdict.
        self.assertIn("No margin or price verdicts", PROMPT)
        self.assertIn("20% net after payment processing fees, platform fees, ad CPA", PROMPT)


class TestModelConditionalPromptSelection(unittest.TestCase):
    def test_active_model_returns_the_digital_prompt(self):
        self.assertIs(get_system_prompt(MODEL_DIGITAL), MARKET_RESEARCH_SYSTEM_PROMPT)

    def test_inactive_branches_are_kept_with_status(self):
        self.assertEqual(set(INACTIVE_MODEL_BRANCHES), {MODEL_IMPORT, MODEL_LOCAL_SA, MODEL_HIGH_TICKET})
        self.assertEqual(INACTIVE_MODEL_BRANCHES[MODEL_IMPORT]["status"], "RETIRED")
        self.assertEqual(INACTIVE_MODEL_BRANCHES[MODEL_LOCAL_SA]["status"], "DISABLED")
        self.assertEqual(INACTIVE_MODEL_BRANCHES[MODEL_HIGH_TICKET]["status"], "DISABLED")

    def test_inactive_models_refuse_a_prompt(self):
        # Model-ambiguous work halts; it is never served a wrong-model prompt.
        for model in (MODEL_IMPORT, MODEL_LOCAL_SA, MODEL_HIGH_TICKET):
            with self.subTest(model=model):
                with self.assertRaises(NotImplementedError):
                    get_system_prompt(model)

    def test_unknown_model_is_rejected(self):
        with self.assertRaises(ValueError):
            get_system_prompt("MOON_BASED_DROPSHIPPING")


if __name__ == "__main__":
    unittest.main()
