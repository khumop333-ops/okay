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
from tools import customs, landed_cost


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

    def test_verified_supplier_costs_finds_nested_quotes(self):
        """so-0003 nests its quotes; the audit must not report zero just
        because the unit cost is inside a ``suppliers`` array."""
        state = synthetic_state()
        state["sourcing"]["findings"] = [
            {
                "id": "so-9002",
                "agent": "sourcing",
                "verified": True,
                "data": {
                    "suppliers": [
                        {"unit_cost_zar": 86.80, "verified": True},
                        {"unit_cost_zar": 999.0, "verified": False},
                        {"UNVERIFIED_unit_cost_zar": 1.0, "verified": True},
                        {"unit_cost_zar": None, "verified": True},
                    ]
                },
            }
        ]
        self.assertEqual(pricing.verified_supplier_costs(state), ["so-9002"])

    def test_unverified_finding_does_not_count_as_a_verified_cost(self):
        state = synthetic_state()
        state["sourcing"]["findings"] = [
            {
                "id": "so-9003",
                "agent": "sourcing",
                "verified": False,
                "data": {"unit_cost_zar": 12.34},
            }
        ]
        self.assertEqual(pricing.verified_supplier_costs(state), [])

    def test_conclusion_changes_when_verified_costs_exist(self):
        state = synthetic_state()
        state["sourcing"]["findings"] = [
            {
                "id": "so-9002",
                "agent": "sourcing",
                "verified": True,
                "data": {"unit_cost_zar": 86.80},
            }
        ]
        report = pricing.readiness_report(state)
        self.assertEqual(report["verified_supplier_costs"], ["so-9002"])
        self.assertIn("VERIFIED supplier unit costs", report["conclusion"])
        self.assertNotIn("NO accept/reject margin verdict is possible",
                         report["conclusion"])

    def test_halt_record_is_reported_as_history_not_current_state(self):
        state = synthetic_state()
        state["sourcing"]["findings"].append(
            {"id": "so-9002", "agent": "sourcing", "verified": True,
             "data": {"unit_cost_zar": 86.80}}
        )
        report = pricing.readiness_report(state)
        self.assertEqual(report["sourcing_halt_findings"], ["so-9001"])
        self.assertEqual(report["sourcing_findings_after_halt"], ["so-9002"])

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

    def test_appends_capability_findings_with_ids(self):
        pricing.apply_findings(self.state, self.findings, "2026-09-29T23:00:00+02:00")
        ids = [f["id"] for f in self.state["pricing"]["findings"]]
        self.assertEqual(ids, ["pr-0001", "pr-0002", "pr-0003"])

    def test_full_session_append_is_six_findings(self):
        all_findings = self.findings + pricing.build_verdict_findings(
            "2026-09-30T12:00:00+02:00"
        )
        pricing.apply_findings(self.state, all_findings, "2026-09-30T12:00:00+02:00")
        ids = [f["id"] for f in self.state["pricing"]["findings"]]
        self.assertEqual(
            ids, ["pr-0001", "pr-0002", "pr-0003", "pr-0004", "pr-0005", "pr-0006"]
        )

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

    def test_session_two_unverified_gaps_are_recorded(self):
        """Schema section 4: every UNVERIFIED_ field in the new findings
        must also appear in the namespace's unverified_fields array."""
        allf = self.findings + pricing.build_verdict_findings("x")
        pricing.apply_findings(self.state, allf, "x")
        joined = " ".join(self.state["pricing"]["unverified_fields"])
        for needle in (
            "shipping_to_sa_zar per unit",
            "UNVERIFIED_platform_fees_zar",
            "UNVERIFIED_competitor_median_price_zar",
            "SARS PRIMARY line-level reading",
            "UNAPPROVED pending HITL gate 5",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, joined)


class TestVerdictMatrix(unittest.TestCase):
    """mr-0002: 4 prices x 3 quotes x 2 CPA x 2 fee cases x 2 VAT bases.

    The arithmetic is in tools/landed_cost.py; these tests pin the agent's
    use of it: the grid is complete, the cheapest usable quote is chosen by
    a stated rule, nothing is approvable on unverified shipping, and no
    verdict rests on the unapproved ATV basis.
    """

    @classmethod
    def setUpClass(cls):
        cls.matrix = pricing.build_verdict_matrix()

    def test_grid_is_complete(self):
        # 4 x 3 x 2 x 2 x 2 = 96 cells, each with 2 shipping scenarios.
        self.assertEqual(self.matrix["cell_count"], 96)
        self.assertEqual(len(self.matrix["cells"]), 96)
        # Every (price, quote, CPA) combination appears exactly 4 times:
        # 2 platform-fee cases x 2 VAT bases.
        seen = {}
        for cell in self.matrix["cells"]:
            with self.subTest(cell=cell):
                self.assertIn("ship0", cell)
                self.assertIn("ship_fetched", cell)
                self.assertIn("vat_basis", cell)
                self.assertIn("max_shipping_25pct_zar", cell)
                key = (cell["price_zar"], cell["quote"], cell["ad_cpa_zar"])
                seen[key] = seen.get(key, 0) + 1
        self.assertEqual(len(seen), 24)
        self.assertEqual(set(seen.values()), {4})

    def test_cheapest_usable_quote_rule(self):
        self.assertEqual(
            self.matrix["cheapest_usable_quote"], "coremax_entry"
        )
        self.assertEqual(self.matrix["cheapest_usable_quote_zar"], 86.80)
        # The deep tier is retained but never promoted to the entry price.
        self.assertEqual(
            self.matrix["deep_tier_scenario"]["unit_cost_zar"], 68.49
        )
        self.assertNotIn(
            self.matrix["deep_tier_scenario"]["unit_cost_zar"],
            [q["unit_cost_zar"] for q in self.matrix["quotes"]],
        )

    def test_every_cell_rejects_at_the_fetched_shipping_datapoint(self):
        self.assertEqual(self.matrix["band_counts"]["ship_fetched_reject"], 96)
        self.assertEqual(self.matrix["band_counts"]["ship_fetched_accept"], 0)
        self.assertEqual(self.matrix["band_counts"]["ship_fetched_investigate"], 0)

    def test_market_cluster_rejects_even_with_free_shipping(self):
        # R299 / R338 must reject on the arithmetic alone, no matter how the
        # shipping and platform-fee questions resolve.
        for cell in self.matrix["cells"]:
            if cell["price_zar"] in (299.0, 338.0):
                with self.subTest(cell=cell):
                    self.assertEqual(cell["ship0"]["band_verdict"], "reject")

    def test_cpa_ceiling_fails_at_every_price(self):
        best = max(
            c["ship0"]["net_margin_pct"]
            for c in self.matrix["cells"]
            if c["ad_cpa_zar"] == 300.0
        )
        self.assertLess(best, landed_cost.HARD_FLOOR_NET_MARGIN_PCT)

    def test_rejects_are_robust_under_the_atv_question(self):
        """The real invariant: the ATV basis can only RAISE VAT, so it can
        never turn a README-basis reject into a non-reject. Derived from the
        cells here, then compared to the recorded summary."""
        for scenario in ("ship0", "ship_fetched"):
            pairs = {}
            for cell in self.matrix["cells"]:
                key = (
                    cell["price_zar"],
                    cell["quote"],
                    cell["ad_cpa_zar"],
                    cell["platform_fees_zar"],
                )
                pairs.setdefault(key, {})[cell["vat_basis"]] = cell[scenario][
                    "band_verdict"
                ]
            self.assertEqual(len(pairs), 48)
            readme_rejects = sum(
                1 for p in pairs.values() if p["readme"] == "reject"
            )
            both_rejects = sum(
                1
                for p in pairs.values()
                if p["readme"] == "reject" and p["atv"] == "reject"
            )
            with self.subTest(scenario=scenario):
                self.assertEqual(readme_rejects, both_rejects)
                self.assertEqual(
                    self.matrix["robustness"][scenario][
                        "reject_on_both_vat_bases"
                    ],
                    both_rejects,
                )
        # And at the only shipping figure actually fetched, everything is a
        # reject on both bases anyway.
        self.assertEqual(
            self.matrix["robustness"]["ship_fetched"][
                "reject_on_both_vat_bases"
            ],
            self.matrix["robustness"]["ship_fetched"]["readme_atv_pairs"],
        )

    def test_band_verdict_thresholds_match_the_brief(self):
        self.assertEqual(pricing.band_verdict(25.0), "accept")
        self.assertEqual(pricing.band_verdict(20.0), "investigate")
        self.assertEqual(pricing.band_verdict(19.99), "reject")
        self.assertEqual(pricing.band_verdict(-5.0), "reject")

    def test_shipping_ceilings_are_none_not_zero_when_infeasible(self):
        for cell in self.matrix["cells"]:
            if cell["price_zar"] == 299.0 and cell["ad_cpa_zar"] == 150.0 \
                    and cell["quote"] == "coremax_entry" \
                    and cell["platform_fees_zar"] == 0.0 \
                    and cell["vat_basis"] == "readme":
                # Product alone (R86.80) exceeds the 25%/20% ceiling at R299.
                self.assertIsNone(cell["max_shipping_25pct_zar"])
                self.assertIsNone(cell["max_shipping_20pct_zar"])

    def test_shipping_ceiling_known_value(self):
        cell = next(
            c for c in self.matrix["cells"]
            if c["price_zar"] == 599.0 and c["quote"] == "coremax_entry"
            and c["ad_cpa_zar"] == 150.0 and c["platform_fees_zar"] == 0.0
            and c["vat_basis"] == "readme"
        )
        self.assertEqual(cell["max_shipping_25pct_zar"], 95.29)
        self.assertEqual(cell["max_shipping_20pct_zar"], 121.33)


class TestVerdictFindings(unittest.TestCase):
    def setUp(self):
        self.findings = pricing.build_verdict_findings("2026-09-30T12:00:00+02:00")
        self.by_id = {f["id"]: f for f in self.findings}

    def test_ids_and_required_fields(self):
        self.assertEqual(list(self.by_id), ["pr-0004", "pr-0005", "pr-0006"])
        for f in self.findings:
            with self.subTest(finding=f["id"]):
                for key in ("id", "timestamp", "agent", "confidence",
                            "source", "data"):
                    self.assertIn(key, f)
                self.assertEqual(f["agent"], "pricing")

    def test_pr_0004_reports_the_hard_stop_and_requests_gate_5(self):
        data = self.by_id["pr-0004"]["data"]
        self.assertIn("HARD STOP", data["hard_stop"])
        self.assertEqual(
            data["hitl_gate_5_request"]["status"],
            "REQUESTED — not approved; nothing merges without APPROVED",
        )
        self.assertIn("README", data["contract_conflict"])

    def test_pr_0005_counts_match_the_matrix(self):
        data = self.by_id["pr-0005"]["data"]
        self.assertEqual(data["counts"]["ship_fetched_reject"], 96)
        self.assertEqual(len(data["cells"]), 96)
        # The brief's "six quotes" correction must be recorded, not ignored.
        self.assertTrue(
            any("so-0004" in line for line in data["scope_corrections"])
        )

    def test_pr_0006_verdict_is_reject_and_cites_the_assumption(self):
        data = self.by_id["pr-0006"]["data"]
        self.assertEqual(data["verdict"], "reject")
        self.assertIn("HARD STOP", data["rejection_reason"])
        self.assertIn("R30", data["platform_fee_assumption"])
        self.assertIn("R0", data["platform_fee_assumption"])

    def test_schema_blocks_cover_every_price_and_fee_case(self):
        data = self.by_id["pr-0006"]["data"]
        blocks = data["blocks"]
        self.assertEqual(len(blocks), 16)  # 4 prices x 2 fee cases x 2 CPA
        # Both platform-fee cases are represented in the verdict blocks.
        self.assertEqual(
            sorted({b["UNVERIFIED_platform_fees_zar"] for b in blocks}),
            [0.0, 30.0],
        )
        self.assertEqual(
            sorted({b["pricing"]["ad_cpa_estimate_zar"] for b in blocks}),
            [150.0, 300.0],
        )
        for block in blocks:
            with self.subTest(block=block["product"]):
                for key in ("timestamp", "agent", "confidence", "source",
                            "verified", "product", "cost_breakdown",
                            "pricing", "verdict", "rejection_reason"):
                    self.assertIn(key, block)
                self.assertEqual(block["verdict"], "reject")
                # Verdict-bearing blocks must use the README basis.
                self.assertEqual(block["vat_basis"], customs.VAT_BASIS_README)
                # Each block records its own fee assumption as UNVERIFIED
                # (pr-0003: no sourced schedule exists).
                self.assertIn(
                    block["UNVERIFIED_platform_fees_zar"], (0.0, 30.0)
                )

    def test_duty_zero_vat_nonzero_in_every_breakdown(self):
        # HARD STOP #4: a 0% duty line still pays VAT on the customs value.
        for block in self.by_id["pr-0006"]["data"]["blocks"]:
            with self.subTest(block=block["product"]):
                self.assertEqual(block["cost_breakdown"]["duty_zar"], 0.0)
                self.assertGreater(block["cost_breakdown"]["vat_zar"], 0.0)


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
        self.assertEqual(
            ids, ["pr-0001", "pr-0002", "pr-0003", "pr-0004", "pr-0005", "pr-0006"]
        )
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
