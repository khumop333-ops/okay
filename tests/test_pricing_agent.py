"""Tests for agents/pricing.py (Pricing capability #1).

Standard library ``unittest`` only. ALL state fixtures here are
synthetic ("Test Widget", mr-0002, so-9001) — no test touches the real
shared_state.json, and the CLI is exercised against temp copies.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agents import pricing
from tools import customs


def synthetic_state():
    """A minimal, obviously-fake stand-in for shared_state.json."""
    return {
        "_schema_version": "1.0.0",
        "_conventions": {"description": "synthetic fixture"},
        "supervisor": {
            "sessions": [{"session_id": "test-0"}],
        },
        "market_research": {
            "findings": [
                {
                    "id": "mr-0002",
                    "agent": "market_research",
                    "verified": True,
                    "data": {
                        "product_name": "Test Widget",
                        "duty_rate_pct": "0%",
                        "UNVERIFIED_unit_cost_zar": None,
                    },
                }
            ],
        },
        "sourcing": {
            "findings": [
                {
                    "id": "so-9001",
                    "agent": "sourcing",
                    "verified": False,
                    "data": {
                        "routing_decision": "Sourcing HALTED this session",
                    },
                }
            ],
        },
        "pricing": {
            "_meta": {"append_key": "findings"},
            "timestamp": "2026-01-01T00:00:00+02:00",
            "agent": "supervisor",
            "confidence": None,
            "source": "initialised",
            "verified": False,
            "findings": [],
            "unverified_fields": [],
        },
    }


class TestReadiness(unittest.TestCase):
    def setUp(self):
        self.state = synthetic_state()

    def test_verified_supplier_costs_found_when_present(self):
        self.assertEqual(pricing.verified_supplier_costs(self.state), [])

    def test_sourcing_halt_detected(self):
        report = pricing.readiness_report(self.state)
        self.assertTrue(report["sourcing_halted"])
        self.assertIn("NO accept/reject", report["conclusion"])

    def test_lead_candidate_read(self):
        report = pricing.readiness_report(self.state)
        self.assertEqual(report["lead_candidate"], "Test Widget")


class TestBreakEvenRows(unittest.TestCase):
    """The one pricing output publishable without supplier quotes."""

    def setUp(self):
        self.rows = pricing.build_break_even_rows()

    def test_full_grid(self):
        # 3 price points x 2 CPA points x 3 target margins
        self.assertEqual(len(self.rows), 18)

    def test_known_hand_computed_values(self):
        def row(price, cpa, target):
            return next(
                r
                for r in self.rows
                if r["price_zar"] == price
                and r["ad_cpa_zar"] == cpa
                and r["target_net_margin_pct"] == target
            )

        self.assertEqual(
            row(699.0, 150.0, 25.0)["max_product_plus_shipping_zar"], 234.26
        )
        self.assertEqual(
            row(699.0, 300.0, 25.0)["max_product_plus_shipping_zar"], 103.83
        )
        self.assertEqual(
            row(344.0, 150.0, 25.0)["max_product_plus_shipping_zar"], 49.04
        )
        self.assertEqual(
            row(258.0, 150.0, 25.0)["max_product_plus_shipping_zar"], 4.17
        )

    def test_floor_price_infeasible_at_cpa_ceiling(self):
        dead = [
            r
            for r in self.rows
            if r["price_zar"] == 258.0
            and r["ad_cpa_zar"] == 300.0
            and r["feasible"] is False
        ]
        # Every target (20/25/35%) is impossible at the floor/ceiling
        # combo — even a free product cannot clear them.
        self.assertEqual(len(dead), 3)
        for r in dead:
            self.assertIsNone(r["max_product_plus_shipping_zar"])

    def test_every_row_carries_provenance(self):
        for r in self.rows:
            with self.subTest(row=r["price_point"]):
                self.assertIn("mr-0002", r["price_source"])
                self.assertIn("formula", r)


class TestApplyFindings(unittest.TestCase):
    def setUp(self):
        self.state = synthetic_state()
        self.findings = pricing.build_findings("2026-09-29T23:00:00+02:00")

    def test_appends_three_findings_with_ids(self):
        pricing.apply_findings(self.state, self.findings, "2026-09-29T23:00:00+02:00")
        ids = [f["id"] for f in self.state["pricing"]["findings"]]
        self.assertEqual(ids, ["pr-0001", "pr-0002", "pr-0003"])

    def test_write_metadata_refreshed(self):
        ns = pricing.apply_findings(
            self.state, self.findings, "2026-09-29T23:00:00+02:00"
        )["pricing"]
        self.assertEqual(ns["agent"], "pricing")
        # Namespace roll-up takes the MINIMUM finding confidence (7).
        self.assertEqual(ns["confidence"], 7)
        self.assertFalse(ns["verified"])  # pr-0002/0003 carry UNVERIFIED data

    def test_every_finding_has_required_fields(self):
        for f in self.findings:
            with self.subTest(finding=f["id"]):
                for key in ("id", "timestamp", "agent", "confidence",
                            "source", "data"):
                    self.assertIn(key, f)

    def test_duplicate_append_refused(self):
        pricing.apply_findings(self.state, self.findings, "x")
        with self.assertRaises(ValueError):
            pricing.apply_findings(self.state, self.findings, "y")

    def test_namespace_isolation(self):
        before_mr = json.dumps(self.state["market_research"])
        before_sup = json.dumps(self.state["supervisor"])
        before_conv = json.dumps(self.state["_conventions"])
        pricing.apply_findings(self.state, self.findings, "x")
        self.assertEqual(json.dumps(self.state["market_research"]), before_mr)
        self.assertEqual(json.dumps(self.state["supervisor"]), before_sup)
        self.assertEqual(json.dumps(self.state["_conventions"]), before_conv)

    def test_unverified_fields_extended(self):
        pricing.apply_findings(self.state, self.findings, "x")
        joined = " ".join(self.state["pricing"]["unverified_fields"])
        self.assertIn("Supplier unit costs", joined)
        self.assertIn("platform_fees", joined)
        self.assertIn("ATV", joined)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state_path = self.tmp / "shared_state.json"
        self.state_path.write_text(
            json.dumps(synthetic_state(), indent=2), encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_dry_run_leaves_file_byte_identical(self):
        before = self.state_path.read_bytes()
        rc = pricing.main(["--state", str(self.state_path)])
        self.assertEqual(rc, 0)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_write_appends_and_stays_valid_json(self):
        rc = pricing.main(["--state", str(self.state_path), "--write"])
        self.assertEqual(rc, 0)
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        ids = [f["id"] for f in data["pricing"]["findings"]]
        self.assertEqual(ids, ["pr-0001", "pr-0002", "pr-0003"])
        # Sibling namespaces untouched by the write.
        self.assertEqual(
            data["market_research"]["findings"][0]["id"], "mr-0002"
        )


class TestRealStateReadOnly(unittest.TestCase):
    """Read-only integration with the REAL shared_state.json in repo."""

    def test_real_state_loads_and_has_pricing_namespace(self):
        state = pricing.load_state(pricing.default_state_path())
        self.assertIn("pricing", state)
        self.assertIn("market_research", state)
        # The routed lead exists and its verified duty line is in the
        # registry at 0% — the break-even inputs stay traceable.
        lead = pricing.finding(state, "market_research", "mr-0002")
        self.assertIsNotNone(lead)
        self.assertEqual(lead["data"]["hs_code"], "8507.60")
        self.assertEqual(customs.lookup_duty_rate_pct("8507.60"), 0.0)


if __name__ == "__main__":
    unittest.main()
