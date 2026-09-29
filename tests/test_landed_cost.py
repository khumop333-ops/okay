"""Tests for tools/landed_cost.py (Pricing capability #1).

Standard library ``unittest`` only. All fixtures are synthetic ("Test
Widget"): HARD STOP #2 governs real-world claims and none are made here.
"""

import unittest

from tools import customs, landed_cost as lc
from tools.landed_cost import (
    clamp_to_competitor_band,
    calculate_landed_cost,
    evaluate_pricing,
    max_customs_base_for_margin,
    net_margin,
    recommend_price_fixed_point,
    verdict_for_margin,
)


class TestConstantsMatchContract(unittest.TestCase):
    def test_vat_is_imported_not_duplicated(self):
        self.assertIs(lc.VAT_RATE, customs.VAT_RATE)
        self.assertEqual(lc.VAT_RATE, 0.15)

    def test_margin_floors(self):
        self.assertEqual(lc.HARD_FLOOR_NET_MARGIN_PCT, 20.0)
        self.assertEqual(lc.MIN_NET_MARGIN_PCT, 25.0)
        self.assertEqual(lc.TARGET_NET_MARGIN_BAND_PCT, (35.0, 40.0))

    def test_fee_and_cpa_and_return_bands(self):
        self.assertEqual(lc.PAYMENT_FEE_PCT_RANGE, (3.0, 5.0))
        self.assertEqual(lc.PAYMENT_FEE_PCT_WORST_CASE, 5.0)
        self.assertEqual(lc.AD_CPA_RANGE_ZAR, (150.0, 300.0))
        self.assertEqual(lc.AD_CPA_WORST_CASE_ZAR, 300.0)
        self.assertEqual(lc.RETURN_RATE_RANGE_PCT, (5.0, 10.0))
        self.assertEqual(lc.RETURN_RATE_WORST_CASE_PCT, 10.0)

    def test_price_multipliers_and_band(self):
        self.assertEqual(lc.PRICE_MULTIPLIERS["impulse"], (2.5, 3.0))
        self.assertEqual(lc.PRICE_MULTIPLIERS["considered"], (2.0, 2.5))
        self.assertEqual(lc.COMPETITOR_BAND_DEFAULT, 0.125)
        self.assertEqual(lc.COMPETITOR_BAND_RANGE, (0.10, 0.15))


class TestLandedCost(unittest.TestCase):
    def test_worked_example(self):
        # 100 product + 50 shipping, 20% duty, price 500, fee 5% of price:
        #   customs value 150 -> duty 30 + VAT 22.50; fee 25 -> total 227.50
        b = calculate_landed_cost(100.0, 50.0, 20.0, 500.0)
        self.assertEqual(b["customs_value_zar"], 150.0)
        self.assertEqual(b["duty_zar"], 30.0)
        self.assertEqual(b["vat_zar"], 22.5)
        self.assertEqual(b["payment_fees_zar"], 25.0)
        self.assertEqual(b["total_landed_cost_zar"], 227.5)

    def test_payment_fee_is_pct_of_selling_price(self):
        # Same costs, different prices -> same duty/VAT, different fee.
        low = calculate_landed_cost(100.0, 50.0, 20.0, 300.0)
        high = calculate_landed_cost(100.0, 50.0, 20.0, 900.0)
        self.assertEqual(low["vat_zar"], high["vat_zar"])
        self.assertEqual(low["payment_fees_zar"], 15.0)
        self.assertEqual(high["payment_fees_zar"], 45.0)

    def test_duty_free_line_still_charges_vat(self):
        b = calculate_landed_cost(100.0, 50.0, 0.0, 500.0)
        self.assertEqual(b["duty_zar"], 0.0)
        self.assertEqual(b["vat_zar"], 22.5)  # 15% of 150, not of 500

    def test_fee_pct_enforced_to_session_band(self):
        for bad in (2.9, 5.1, -1.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calculate_landed_cost(10, 10, 0.0, 100.0, bad)
        # Endpoints are legal.
        for edge in (3.0, 5.0):
            calculate_landed_cost(10, 10, 0.0, 100.0, edge)

    def test_negative_costs_rejected(self):
        with self.assertRaises(ValueError):
            calculate_landed_cost(-1.0, 10.0, 0.0, 100.0)


class TestNetMargin(unittest.TestCase):
    def test_worked_example_with_returns(self):
        # price 699, landed 250, CPA 150, returns 10% (zero salvage):
        #   base 299; return allowance 69.90; adjusted 229.10 (32.78%)
        m = net_margin(699.0, 250.0, 150.0)
        self.assertEqual(m["base_net_margin_zar"], 299.0)
        self.assertEqual(m["return_allowance_zar"], 69.9)
        self.assertEqual(m["net_margin_zar"], 229.1)
        self.assertEqual(m["net_margin_pct"], 32.78)

    def test_platform_fees_subtracted(self):
        with_pf = net_margin(500.0, 100.0, 150.0, platform_fees_zar=50.0)
        without_pf = net_margin(500.0, 100.0, 150.0)
        self.assertAlmostEqual(
            with_pf["net_margin_zar"], without_pf["net_margin_zar"] - 50.0, 2
        )

    def test_return_rate_bounds(self):
        for bad in (4.9, 10.1, -1):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    net_margin(100.0, 50.0, 10.0, return_rate_pct=bad)

    def test_zero_price_rejected(self):
        with self.assertRaises(ValueError):
            net_margin(0.0, 50.0, 10.0)


class TestVerdictForMargin(unittest.TestCase):
    def test_accept_at_and_above_minimum(self):
        self.assertEqual(verdict_for_margin(25.0)["verdict"], "accept")
        self.assertEqual(verdict_for_margin(35.0)["verdict"], "accept")

    def test_escalation_band_20_to_25_is_reject(self):
        v = verdict_for_margin(24.99)
        self.assertEqual(v["verdict"], "reject")
        self.assertIn("escalation band", v["rejection_reason"])
        # Exactly 20% is NOT below the floor, but IS below the minimum.
        v20 = verdict_for_margin(20.0)
        self.assertEqual(v20["verdict"], "reject")
        self.assertIn("escalation band", v20["rejection_reason"])
        self.assertNotIn("automatic reject", v20["rejection_reason"])

    def test_below_floor_is_hard_stop(self):
        v = verdict_for_margin(19.99)
        self.assertEqual(v["verdict"], "reject")
        self.assertIn("HARD STOP", v["rejection_reason"])
        v = verdict_for_margin(-5.0)
        self.assertIn("HARD STOP", v["rejection_reason"])


class TestRecommendPriceFixedPoint(unittest.TestCase):
    def test_price_is_self_consistent(self):
        # price = m x (base + f x price) must hold exactly at the result.
        for m, f_pct in ((2.5, 5.0), (3.0, 5.0), (2.0, 3.0), (2.5, 3.0)):
            with self.subTest(m=m, f=f_pct):
                price = recommend_price_fixed_point(100.0, m, f_pct)
                landed = 100.0 + price * f_pct / 100.0
                self.assertAlmostEqual(price, m * landed, delta=0.02)

    def test_known_value(self):
        # 2.5 x 100 / (1 - 0.125) = 285.71
        self.assertEqual(recommend_price_fixed_point(100.0, 2.5, 5.0), 285.71)

    def test_no_solution_when_multiplier_eats_the_price(self):
        with self.assertRaises(ValueError):
            recommend_price_fixed_point(100.0, 25.0, 5.0)  # m x f >= 1

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            recommend_price_fixed_point(100.0, -1.0, 5.0)
        with self.assertRaises(ValueError):
            recommend_price_fixed_point(100.0, 2.5, 9.9)  # outside 3-5 band


class TestCompetitorBandClamp(unittest.TestCase):
    def test_clamps_both_sides(self):
        self.assertEqual(clamp_to_competitor_band(400.0, 300.0), 337.5)
        self.assertEqual(clamp_to_competitor_band(200.0, 300.0), 262.5)
        self.assertEqual(clamp_to_competitor_band(300.0, 300.0), 300.0)

    def test_band_width_validation(self):
        for bad in (0.09, 0.16):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    clamp_to_competitor_band(300.0, 300.0, band=bad)

    def test_zero_median_rejected(self):
        with self.assertRaises(ValueError):
            clamp_to_competitor_band(300.0, 0.0)


class TestMaxCustomsBase(unittest.TestCase):
    """The inverse question: max product+shipping cost at a fixed price."""

    def test_known_values_duty_free(self):
        # (699 x (1 - 0.10 - 0.05 - 0.25) - 150) / 1.15 = 234.26
        r = max_customs_base_for_margin(699.0, 0.0, 150.0, 25.0)
        self.assertTrue(r["feasible"])
        self.assertEqual(r["max_customs_base_zar"], 234.26)
        # (699 x 0.60 - 300) / 1.15 = 103.83
        r = max_customs_base_for_margin(699.0, 0.0, 300.0, 25.0)
        self.assertEqual(r["max_customs_base_zar"], 103.83)

    def test_duty_shrinks_the_ceiling(self):
        # (699 x 0.60 - 150) / (1 + 0.20 + 0.15) = 199.56
        r = max_customs_base_for_margin(699.0, 20.0, 150.0, 25.0)
        self.assertEqual(r["max_customs_base_zar"], 199.56)

    def test_infeasible_is_none_not_zero(self):
        # At the R258 floor with CPA at the R300 ceiling, even a free
        # product cannot reach 25% — that must surface, not silently zero.
        r = max_customs_base_for_margin(258.0, 0.0, 300.0, 25.0)
        self.assertFalse(r["feasible"])
        self.assertIsNone(r["max_customs_base_zar"])

    def test_round_trip_with_forward_margin(self):
        # Break-even base must reproduce the target margin exactly.
        target = 25.0
        r = max_customs_base_for_margin(699.0, 0.0, 150.0, target)
        base = r["max_customs_base_zar"]
        landed = base * 1.15 + 0.05 * 699.0  # duty+VAT (duty 0) + fee
        m = net_margin(699.0, landed, 150.0)
        self.assertAlmostEqual(m["net_margin_pct"], target, delta=0.1)


class TestEvaluatePricing(unittest.TestCase):
    def test_blocks_unverified_inputs(self):
        out = evaluate_pricing(50.0, 50.0, 0.0, inputs_verified=False)
        self.assertEqual(out["verdict"], "blocked")
        self.assertIn("HARD STOP #2", out["rejection_reason"])
        self.assertNotIn("cost_breakdown", out)

    def test_accept_scenario_on_synthetic_costs(self):
        # Test Widget: 20 + 20 product+shipping, duty-free, median R400.
        # Multiplier price clamps up into the band: R350.
        # Landed = 46 + 17.50 fee = 63.50; margin 350-63.50-150 = 136.50;
        # after 10% returns 101.50 -> 29.0% -> accept.
        out = evaluate_pricing(
            20.0,
            20.0,
            0.0,
            inputs_verified=True,
            competitor_median_price_zar=400.0,
            ad_cpa_zar=150.0,
            input_sources={"product_name": "Test Widget"},
        )
        self.assertEqual(out["verdict"], "accept")
        self.assertEqual(out["pricing"]["recommended_selling_price_zar"], 350.0)
        self.assertEqual(out["pricing"]["net_margin_pct"], 29.0)
        self.assertEqual(out["cost_breakdown"]["total_landed_cost_zar"], 63.5)
        self.assertTrue(
            any("clamped" in w for w in out["warnings"])
        )

    def test_reject_scenario_names_hard_stop(self):
        # Thicker costs under a low median with CPA ceiling: doomed.
        out = evaluate_pricing(
            150.0,
            100.0,
            0.0,
            inputs_verified=True,
            competitor_median_price_zar=300.0,
            ad_cpa_zar=300.0,
        )
        self.assertEqual(out["verdict"], "reject")
        self.assertIn("HARD STOP", out["rejection_reason"])
        self.assertLess(out["pricing"]["net_margin_pct"], 20.0)

    def test_zero_platform_fee_carries_warning(self):
        out = evaluate_pricing(20.0, 20.0, 0.0, inputs_verified=True)
        self.assertTrue(
            any("platform_fees" in w for w in out["warnings"])
        )

    def test_unknown_buy_type_rejected(self):
        with self.assertRaises(KeyError):
            evaluate_pricing(
                20.0, 20.0, 0.0, inputs_verified=True, buy_type="luxury"
            )


if __name__ == "__main__":
    unittest.main()
