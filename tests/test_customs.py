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
    REGISTRY_SOURCE,
    UnknownHsCodeError,
    VERIFIED_DUTY_LINES,
    VAT_RATE,
    calculate_duty,
    calculate_vat,
    customs_breakdown,
    customs_value,
    lookup_duty_rate_pct,
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


class TestModuleVersion(unittest.TestCase):
    def test_versions_stamp_both_modules(self):
        stamp = customs.module_versions()
        self.assertIn("tools/landed_cost.py v", stamp)
        self.assertIn("tools/customs.py v", stamp)


if __name__ == "__main__":
    unittest.main()
