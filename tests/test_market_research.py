"""Tests for agents/market_research.py (capability #1).

Standard library ``unittest`` only — this repo intentionally has no test
runner dependency (see requirements.txt).

All fixtures are synthetic ("Test Widget ...") and obviously fake: HARD
STOP #2 governs real-world claims, and nothing here claims to be one.
"""

import unittest

from agents.market_research import (
    CUSTOMS_ELIMINATE_ABOVE_PCT,
    HIGH_COMPETITION_SELLERS,
    MARGIN_FLOOR_PCT,
    Candidate,
    classify_competition,
    classify_customs_risk,
    rank_candidates,
)


class TestClassifyCustomsRisk(unittest.TestCase):
    def test_duty_free_is_low(self):
        v = classify_customs_risk(0.0)
        self.assertEqual(v.risk, "low")
        self.assertFalse(v.eliminate)

    def test_mid_band_is_medium(self):
        for rate in (5.0, 15.0, 20.0, CUSTOMS_ELIMINATE_ABOVE_PCT):
            with self.subTest(rate=rate):
                v = classify_customs_risk(rate)
                self.assertEqual(v.risk, "medium")
                self.assertFalse(v.eliminate)

    def test_boundary_is_exclusive(self):
        # Rule is "duty > 25%", so exactly 25% must NOT eliminate.
        v = classify_customs_risk(CUSTOMS_ELIMINATE_ABOVE_PCT)
        self.assertFalse(v.eliminate)
        v = classify_customs_risk(CUSTOMS_ELIMINATE_ABOVE_PCT + 0.01)
        self.assertTrue(v.eliminate)
        self.assertEqual(v.risk, "high")

    def test_above_threshold_eliminates(self):
        v = classify_customs_risk(30.0)
        self.assertEqual(v.risk, "high")
        self.assertTrue(v.eliminate)

    def test_unverified_duty_is_unknown_never_eliminated(self):
        v = classify_customs_risk(None)
        self.assertEqual(v.risk, "unknown")
        self.assertFalse(v.eliminate)
        self.assertIn("UNVERIFIED", v.reason)

    def test_apparel_always_high_risk(self):
        for category in ("apparel", "Textiles", "clothing", "garments"):
            with self.subTest(category=category):
                v = classify_customs_risk(0.0, category=category)
                self.assertEqual(v.risk, "high")
                self.assertTrue(v.eliminate)

    def test_negative_duty_rejected(self):
        with self.assertRaises(ValueError):
            classify_customs_risk(-1.0)


class TestClassifyCompetition(unittest.TestCase):
    def test_threshold_is_high(self):
        v = classify_competition(HIGH_COMPETITION_SELLERS)
        self.assertEqual(v.level, "high")

    def test_above_threshold_is_high(self):
        v = classify_competition(25)
        self.assertEqual(v.level, "high")

    def test_below_threshold_is_not_split(self):
        # No low/medium invention: anything under the HIGH rule is
        # honestly labelled below-threshold.
        for n in (0, 1, 9):
            with self.subTest(n=n):
                v = classify_competition(n)
                self.assertEqual(v.level, "below-threshold")

    def test_unobserved_is_unknown(self):
        v = classify_competition(None)
        self.assertEqual(v.level, "unknown")
        self.assertIn("UNVERIFIED", v.reason)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            classify_competition(-1)


class TestRankCandidates(unittest.TestCase):
    def test_unverified_margin_is_refused(self):
        cands = [Candidate(product_name="Test Widget A")]
        out = rank_candidates(cands)
        self.assertEqual(out["ranked"], [])
        self.assertEqual(len(out["unranked"]), 1)
        self.assertIn("HARD STOP #3", out["unranked"][0].reason)

    def test_verified_margins_rank_highest_first(self):
        cands = [
            Candidate(product_name="Test Widget Low", net_margin_pct=21.0),
            Candidate(product_name="Test Widget High", net_margin_pct=45.0),
        ]
        out = rank_candidates(cands)
        self.assertEqual(
            [r.product_name for r in out["ranked"]],
            ["Test Widget High", "Test Widget Low"],
        )
        self.assertEqual(out["unranked"], [])

    def test_sub_floor_margin_is_flagged_not_approved(self):
        cands = [Candidate(product_name="Test Widget Thin", net_margin_pct=12.0)]
        out = rank_candidates(cands)
        self.assertEqual(len(out["ranked"]), 1)
        self.assertFalse(out["ranked"][0].meets_margin_floor)
        self.assertLess(out["ranked"][0].net_margin_pct, MARGIN_FLOOR_PCT)

    def test_floor_boundary_counts_as_meeting(self):
        cands = [
            Candidate(product_name="Test Widget Edge", net_margin_pct=MARGIN_FLOOR_PCT)
        ]
        out = rank_candidates(cands)
        self.assertTrue(out["ranked"][0].meets_margin_floor)

    def test_mixed_verified_and_unverified(self):
        cands = [
            Candidate(product_name="Test Widget Known", net_margin_pct=30.0),
            Candidate(product_name="Test Widget Unknown"),
        ]
        out = rank_candidates(cands)
        self.assertEqual(len(out["ranked"]), 1)
        self.assertEqual(len(out["unranked"]), 1)

    def test_empty_input(self):
        out = rank_candidates([])
        self.assertEqual(out, {"ranked": [], "unranked": []})


class TestCandidateRecord(unittest.TestCase):
    def test_unverified_fields_default_to_none(self):
        c = Candidate(product_name="Test Widget")
        self.assertIsNone(c.hs_code)
        self.assertIsNone(c.duty_rate_pct)
        self.assertIsNone(c.net_margin_pct)
        self.assertIsNone(c.established_seller_count)


if __name__ == "__main__":
    unittest.main()
