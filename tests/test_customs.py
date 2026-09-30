"""Tests for tools/customs.py (Pricing capability #1).

Standard library ``unittest`` only — no test-runner dependency (see
requirements.txt). All fixtures are synthetic; the only real-world values
are the SA duty rates verified by Market Research (mr-0001..mr-0022),
whose provenance is asserted to stay in the registry.
"""

import inspect
import unittest

from tools import customs
from tools.customs import (
    DEFAULT_VAT_BASIS,
    REGISTRY_SOURCE,
    SARS_ATV_UPLIFT_PCT,
    UnknownHsCodeError,
    VAT_BASIS_CHOICES,
    VAT_BASIS_README,
    VAT_BASIS_SARS_ATV,
    VERIFIED_DUTY_LINES,
    VAT_RATE,
    calculate_duty,
    calculate_vat,
    calculate_vat_sars_atv,
    customs_breakdown,
    customs_value,
    duty_and_vat_multiplier,
    lookup_duty_rate_pct,
    validate_vat_basis,
)


class TestVatHardStop(unittest.TestCase):
    """HARD STOP #4: 15% VAT on customs value, no exceptions."""

    def test_rate_is_fifteen_percent(self):
        self.assertEqual(VAT_RATE, 0.15)

    def test_vat_on_customs_value(self):
        self.assertEqual(calculate_vat(1000.0), 150.0)
        self.assertEqual(calculate_vat(0.0), 0.0)

    def test_vat_signature_has_no_rate_override(self):
        # The rate cannot be turned off or changed by a caller: the
        # function must take exactly one argument (the customs value).
        params = inspect.signature(calculate_vat).parameters
        self.assertEqual(list(params), ["customs_value_zar"])

    def test_negative_customs_value_rejected(self):
        with self.assertRaises(ValueError):
            calculate_vat(-1.0)


class TestCustomsValue(unittest.TestCase):
    def test_is_product_plus_shipping(self):
        self.assertEqual(customs_value(100.0, 50.0), 150.0)
        self.assertEqual(customs_value(0.0, 0.0), 0.0)

    def test_independent_of_retail_price(self):
        # VAT lives on customs value, NEVER retail (README section 4).
        # There is deliberately no selling-price parameter here.
        params = inspect.signature(customs_value).parameters
        self.assertNotIn("selling_price", params)

    def test_negative_inputs_rejected(self):
        with self.assertRaises(ValueError):
            customs_value(-5.0, 10.0)
        with self.assertRaises(ValueError):
            customs_value(5.0, -10.0)

    def test_non_numeric_rejected(self):
        with self.assertRaises(TypeError):
            customs_value("100", 10.0)  # type: ignore[arg-type]


class TestDuty(unittest.TestCase):
    def test_known_rates(self):
        for rate in (0.0, 15.0, 20.0, 45.0):
            with self.subTest(rate=rate):
                self.assertEqual(
                    calculate_duty(200.0, rate), round(200.0 * rate / 100, 2)
                )

    def test_zero_duty_is_zero(self):
        self.assertEqual(calculate_duty(999.0, 0.0), 0.0)

    def test_invalid_rates_rejected(self):
        for bad in (-0.1, 100.01, float("nan")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calculate_duty(100.0, bad)


class TestVerifiedDutyRegistry(unittest.TestCase):
    """Duty rates verified by Market Research this pipeline (mr-0001..22).

    The registry is the mechanical form of HARD STOP #2 for duty: an
    unverified code must raise, never fall back to a remembered rate.
    """

    def test_verified_lines_return_verified_rates(self):
        expected = {
            "8507.60": 0.0,   # mr-0002 solar power bank
            "8504.40": 0.0,   # mr-0001 chargers
            "8544.42": 15.0,  # mr-0001 cables
            "3926.90": 20.0,  # mr-0004/0007/0022 plastics
            "7323.93": 20.0,  # mr-0022 stainless kitchenware
            "9503.00": 20.0,  # mr-0015 toys/puzzles
            "8528.72": 25.0,  # mr-0014 televisions
            "6402.99": 30.0,  # mr-0010 footwear (rejected candidate)
        }
        for code, rate in expected.items():
            with self.subTest(code=code):
                self.assertEqual(lookup_duty_rate_pct(code), rate)

    def test_unknown_code_raises_never_guesses(self):
        # 8513.10 is a real MR candidate whose SA rate stayed UNVERIFIED —
        # it must NOT be in the registry and must raise.
        self.assertNotIn("8513.10", VERIFIED_DUTY_LINES)
        with self.assertRaises(UnknownHsCodeError):
            lookup_duty_rate_pct("8513.10")

    def test_every_entry_carries_provenance(self):
        for code, entry in VERIFIED_DUTY_LINES.items():
            with self.subTest(code=code):
                self.assertIn("duty_rate_pct", entry)
                self.assertIn("verified_by", entry)
                self.assertTrue(entry["verified_by"].startswith("mr-"))
        self.assertIn("tradecaravan", REGISTRY_SOURCE)


class TestCustomsBreakdown(unittest.TestCase):
    def test_worked_example(self):
        # 100 product + 50 shipping @ 20% duty:
        #   customs value 150, duty 30, VAT 22.50 (15% of 150).
        out = customs_breakdown(100.0, 50.0, 20.0)
        self.assertEqual(out["customs_value_zar"], 150.0)
        self.assertEqual(out["duty_zar"], 30.0)
        self.assertEqual(out["vat_zar"], 22.5)
        self.assertEqual(out["vat_rate"], VAT_RATE)
        self.assertEqual(out["duty_rate_pct"], 20.0)

    def test_duty_free_line_still_charges_vat(self):
        # HARD STOP #4: 0% duty never means 0% VAT. Customs value is
        # still 150, so VAT is still 22.50.
        out = customs_breakdown(100.0, 50.0, 0.0)
        self.assertEqual(out["duty_zar"], 0.0)
        self.assertEqual(out["vat_zar"], 22.5)


class TestAtvVatBasis(unittest.TestCase):
    """SARS ATV method — OPT-IN, unapproved, never the default (pr-0004).

    The README contract formula stays authoritative (README section 1), so
    these tests pin both the ATV arithmetic AND the fact that the default
    cannot drift to it without a HITL gate 5 amendment.
    """

    def test_default_basis_is_the_readme_contract(self):
        self.assertEqual(DEFAULT_VAT_BASIS, VAT_BASIS_README)
        self.assertEqual(VAT_BASIS_CHOICES, (VAT_BASIS_README, VAT_BASIS_SARS_ATV))

    def test_worked_example_matches_the_cited_source(self):
        # jlog.co.za 8507.60 worked example: R2,000 FOB, duty-free
        # -> R330 duty + VAT  =>  VAT = 15% x (2000 + 200) = 330.
        self.assertEqual(calculate_vat_sars_atv(2000.0, 0.0), 330.0)

    def test_uplift_and_duty_are_both_in_the_base(self):
        # 100 CV + 20 duty + 10 uplift = 130 -> VAT 19.50 (vs 15.00 flat)
        self.assertEqual(calculate_vat_sars_atv(100.0, 20.0), 19.5)
        # uplift of 0 collapses to the flat formula for a duty-free line
        self.assertEqual(
            calculate_vat_sars_atv(100.0, 0.0, uplift_pct=0.0),
            calculate_vat(100.0),
        )

    def test_atv_never_lowers_vat(self):
        for cv in (0.0, 10.0, 86.8, 1000.0):
            for duty in (0.0, cv * 0.1, cv * 0.2):
                with self.subTest(cv=cv, duty=duty):
                    self.assertGreaterEqual(
                        calculate_vat_sars_atv(cv, duty), calculate_vat(cv)
                    )

    def test_validation(self):
        self.assertEqual(SARS_ATV_UPLIFT_PCT, 10.0)
        with self.assertRaises(ValueError):
            calculate_vat_sars_atv(-1.0)
        with self.assertRaises(ValueError):
            calculate_vat_sars_atv(100.0, -1.0)
        with self.assertRaises(ValueError):
            calculate_vat_sars_atv(100.0, 0.0, uplift_pct=-0.1)
        with self.assertRaises(ValueError):
            calculate_vat_sars_atv(100.0, 0.0, uplift_pct=100.1)

    def test_unknown_basis_raises_never_guesses(self):
        self.assertEqual(validate_vat_basis(VAT_BASIS_README), VAT_BASIS_README)
        with self.assertRaises(ValueError):
            validate_vat_basis("maybe_atv")

    def test_breakdown_records_the_basis_used(self):
        flat = customs_breakdown(100.0, 50.0, 0.0)
        self.assertEqual(flat["vat_basis"], VAT_BASIS_README)
        self.assertEqual(flat["vat_zar"], 22.5)
        self.assertIsNone(flat["atv_uplift_pct"])

        atv = customs_breakdown(100.0, 50.0, 0.0, VAT_BASIS_SARS_ATV)
        self.assertEqual(atv["vat_basis"], VAT_BASIS_SARS_ATV)
        self.assertEqual(atv["vat_zar"], 24.75)  # 15% of 150 x 1.10
        self.assertEqual(atv["atv_uplift_pct"], SARS_ATV_UPLIFT_PCT)
        with self.assertRaises(ValueError):
            customs_breakdown(100.0, 50.0, 0.0, "atv_ish")

    def test_multiplier_matches_forward_breakdown(self):
        for duty in (0.0, 10.0, 45.0):
            for basis in VAT_BASIS_CHOICES:
                with self.subTest(duty=duty, basis=basis):
                    m = duty_and_vat_multiplier(duty, basis)
                    out = customs_breakdown(800.0, 200.0, duty, basis)
                    self.assertAlmostEqual(
                        m, 1.0 + out["duty_zar"] / 1000.0 + out["vat_zar"] / 1000.0, 6
                    )

    def test_multiplier_known_values(self):
        self.assertEqual(duty_and_vat_multiplier(0.0), 1.15)
        self.assertEqual(duty_and_vat_multiplier(0.0, VAT_BASIS_SARS_ATV), 1.165)
        self.assertEqual(duty_and_vat_multiplier(20.0), 1.35)
        self.assertEqual(duty_and_vat_multiplier(20.0, VAT_BASIS_SARS_ATV), 1.395)
        with self.assertRaises(ValueError):
            duty_and_vat_multiplier(0.0, "nope")


class TestModuleVersion(unittest.TestCase):
    def test_versions_stamp_both_modules(self):
        stamp = customs.module_versions()
        self.assertIn("tools/landed_cost.py v", stamp)
        self.assertIn("tools/customs.py v", stamp)
        self.assertIn("v1.1.0", stamp)  # ATV basis added as opt-in in 1.1.0


if __name__ == "__main__":
    unittest.main()
