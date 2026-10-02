"""Tests for tools/complaint_tally.py (complaint-mining tally).

Standard library ``unittest`` only. Fixtures are synthetic; one integrity test
runs the tool over the real study under research/solar-complaint-mining and
asserts the evidence log validates cleanly.
"""

import datetime as dt
import inspect
import json
import os
import tempfile
import unittest

from tools import complaint_tally as ct

AS_OF = dt.date(2026, 10, 2)
TAGS = {"a": {"definition": "A"}, "b": {"definition": "B"}, "c": {"definition": "C"}}


def row(i, tags=("a",), community="C1", voice="owner", thread="t1", date="2026-06-01",
        window_hint=None, **kw):
    base = dict(id=f"E{i:03d}", community=community, voice=voice, source_type="reddit",
                venue="v", thread_key=thread, url=f"https://example.org/{i}",
                date=date, window_hint=window_hint, quote=f"quote {i}", tags=list(tags),
                spend=None, workaround=None, solutions_mentioned=[])
    base.update(kw)
    return base


def unit(community="C1", items=10, date="2026-06-01", hint=None, st="reddit"):
    return dict(community=community, source_type=st, venue="v", thread_key="x",
                url="https://example.org/u", date=date, window_hint=hint,
                items_read=items)


class MonthsBackTests(unittest.TestCase):
    def test_exact_year_and_two_years(self):
        self.assertEqual(ct.months_back(AS_OF, 12), dt.date(2025, 10, 2))
        self.assertEqual(ct.months_back(AS_OF, 24), dt.date(2024, 10, 2))

    def test_leap_day_clamps(self):
        self.assertEqual(ct.months_back(dt.date(2028, 2, 29), 12), dt.date(2027, 2, 28))
        self.assertEqual(ct.months_back(dt.date(2024, 3, 31), 1), dt.date(2024, 2, 29))

    def test_crosses_year_boundary(self):
        self.assertEqual(ct.months_back(dt.date(2026, 1, 15), 2), dt.date(2025, 11, 15))

    def test_window_starts(self):
        self.assertEqual(ct.window_starts(AS_OF),
                         (dt.date(2025, 10, 2), dt.date(2024, 10, 2)))


class ClassifyTests(unittest.TestCase):
    def test_boundaries_are_inclusive_at_the_start(self):
        self.assertEqual(ct.classify("2025-10-02", None, AS_OF), "strict")
        self.assertEqual(ct.classify("2025-10-01", None, AS_OF), "extended")
        self.assertEqual(ct.classify("2024-10-02", None, AS_OF), "extended")
        self.assertEqual(ct.classify("2024-10-01", None, AS_OF), "out")

    def test_future_and_today(self):
        self.assertEqual(ct.classify("2026-10-02", None, AS_OF), "strict")
        self.assertEqual(ct.classify("2026-10-03", None, AS_OF), "future")

    def test_undated_rows_need_a_hint(self):
        self.assertEqual(ct.classify(None, "strict", AS_OF), "strict")
        self.assertEqual(ct.classify(None, "extended", AS_OF), "extended")
        self.assertEqual(ct.classify(None, None, AS_OF), "undated")
        self.assertEqual(ct.classify(None, "whatever", AS_OF), "undated")


class SelectWindowTests(unittest.TestCase):
    def test_all_communities_at_minimum_keeps_strict_window(self):
        scanned = [unit("C1", 30), unit("C2", 30), unit("C3", 31)]
        sel = ct.select_window(scanned, AS_OF)
        self.assertEqual(sel["window"], "strict")
        self.assertEqual(sel["communities_below_minimum_in_strict"], [])

    def test_one_short_community_triggers_24_month_fallback(self):
        scanned = [unit("C1", 40), unit("C2", 29), unit("C3", 35)]
        sel = ct.select_window(scanned, AS_OF)
        self.assertEqual(sel["window"], "extended")
        self.assertEqual(sel["communities_below_minimum_in_strict"], ["C2"])
        self.assertIn("C2", sel["rule"])

    def test_extended_units_do_not_count_toward_the_strict_minimum(self):
        scanned = [unit("C1", 40), unit("C2", 20), unit("C2", 15, date="2025-02-01"),
                   unit("C3", 35)]
        sel = ct.select_window(scanned, AS_OF)
        self.assertEqual(sel["strict_scanned"]["C2"], 20)
        self.assertEqual(sel["extended_scanned"]["C2"], 35)
        self.assertEqual(sel["window"], "extended")

    def test_undated_units_use_their_hint(self):
        scanned = [unit("C1", 30, date=None, hint="strict"), unit("C2", 30),
                   unit("C3", 30)]
        self.assertEqual(ct.select_window(scanned, AS_OF)["window"], "strict")


class TallyTests(unittest.TestCase):
    def test_only_owner_and_prospective_count(self):
        ev = [row(1, voice="owner"), row(2, voice="prospective", thread="t2"),
              row(3, voice="bystander", thread="t3"), row(4, voice="trade", thread="t4")]
        out = ct.tally(ev, AS_OF, "strict")
        self.assertEqual(out["pains"][0]["count"], 2)
        self.assertEqual(out["excluded_by_voice"], {"bystander": 1, "trade": 1})
        self.assertEqual(out["bystander_or_trade_tags"][0]["owner_or_prospective_items"], 2)

    def test_multi_tag_rows_count_once_per_tag(self):
        ev = [row(1, tags=("a", "b")), row(2, tags=("a",), thread="t2")]
        counts = {p["tag"]: p["count"] for p in ct.tally(ev, AS_OF, "strict")["pains"]}
        self.assertEqual(counts, {"a": 2, "b": 1})

    def test_rank_ties_break_on_distinct_threads_then_spread_then_name(self):
        ev = [row(1, ("a",), thread="t1"), row(2, ("a",), thread="t1"),
              row(3, ("b",), thread="t2"), row(4, ("b",), thread="t3"),
              row(5, ("c",), thread="t4", community="C2"),
              row(6, ("c",), thread="t5", community="C3")]
        order = [p["tag"] for p in ct.tally(ev, AS_OF, "strict")["pains"]]
        # all tie on count=2; b and c have 2 threads; c spans 2 communities -> c, b, a
        self.assertEqual(order, ["c", "b", "a"])
        ev2 = [row(1, ("b",), thread="t1"), row(2, ("b",), thread="t2"),
               row(3, ("a",), thread="t3"), row(4, ("a",), thread="t4")]
        order2 = [p["tag"] for p in ct.tally(ev2, AS_OF, "strict")["pains"]]
        self.assertEqual(order2, ["a", "b"])           # full tie -> alphabetical

    def test_higher_count_always_wins(self):
        ev = [row(i, ("a",), thread=f"t{i}") for i in range(1, 4)] + [row(9, ("b",), thread="z")]
        self.assertEqual(ct.tally(ev, AS_OF, "strict")["pains"][0]["tag"], "a")

    def test_concentration_flag_is_strictly_more_than_40_percent(self):
        flagged = [row(1, thread="t1"), row(2, thread="t1"), row(3, thread="t1"),
                   row(4, thread="t2"), row(5, thread="t3")]          # 60%
        p = ct.tally(flagged, AS_OF, "strict")["pains"][0]
        self.assertTrue(p["concentration_flag"])
        self.assertEqual(p["top_thread"], "t1")
        edge = [row(1, thread="t1"), row(2, thread="t1"), row(3, thread="t2"),
                row(4, thread="t3"), row(5, thread="t4")]             # exactly 40%
        self.assertFalse(ct.tally(edge, AS_OF, "strict")["pains"][0]["concentration_flag"])

    def test_recurring_needs_two_items_in_two_threads(self):
        ev = [row(1, ("a",), thread="t1"), row(2, ("a",), thread="t1"),
              row(3, ("b",), thread="t2"), row(4, ("b",), thread="t3")]
        flags = {p["tag"]: p["recurring"] for p in ct.tally(ev, AS_OF, "strict")["pains"]}
        self.assertEqual(flags, {"a": False, "b": True})

    def test_strict_share_and_window_filtering(self):
        ev = [row(1, date="2026-05-01"), row(2, date="2026-01-01", thread="t2"),
              row(3, date="2025-11-01", thread="t3"), row(4, date="2025-03-01", thread="t4"),
              row(5, date="2024-01-01", thread="t5")]
        ext = ct.tally(ev, AS_OF, "extended")
        self.assertEqual(ext["pains"][0]["count"], 4)
        self.assertEqual(ext["pains"][0]["strict_count"], 3)
        self.assertEqual(ext["pains"][0]["strict_share"], 0.75)
        self.assertEqual(ext["dropped_by_window"], {"out": 1})
        strict = ct.tally(ev, AS_OF, "strict")
        self.assertEqual(strict["pains"][0]["count"], 3)

    def test_undated_rows_use_hint(self):
        ev = [row(1, date=None, window_hint="strict"),
              row(2, date=None, window_hint="extended", thread="t2")]
        self.assertEqual(ct.tally(ev, AS_OF, "strict")["pains"][0]["count"], 1)
        self.assertEqual(ct.tally(ev, AS_OF, "extended")["pains"][0]["count"], 2)

    def test_equal_weight_stops_a_big_community_dominating(self):
        ev = [row(i, ("y",), community="C1", thread=f"t{i}") for i in range(1, 6)]
        ev += [row(i, ("z",), community="C1", thread=f"u{i}") for i in range(6, 11)]
        ev += [row(20, ("x",), community="C2", thread="v1"),
               row(21, ("x",), community="C2", thread="v2")]
        pains = {p["tag"]: p for p in ct.tally(ev, AS_OF, "strict")["pains"]}
        self.assertGreater(pains["y"]["count"], pains["x"]["count"])   # pooled: y wins
        self.assertEqual(pains["x"]["rank_equal_weight"], 1)           # equal weight: x wins
        self.assertEqual(pains["x"]["equal_weight_score"], 0.5)

    def test_workarounds_spend_and_solutions_are_collected(self):
        spend = dict(zar=1700, kind="quoted_price", what="rent")
        ev = [row(1, workaround="bought outright", spend=spend, solutions_mentioned=["s1"]),
              row(2, thread="t2", workaround="bought outright", solutions_mentioned=["s2"])]
        p = ct.tally(ev, AS_OF, "strict")["pains"][0]
        self.assertEqual(p["workarounds"], ["bought outright"])
        self.assertEqual(p["spend"][0]["zar"], 1700)
        self.assertEqual(p["solutions_mentioned"], ["s1", "s2"])


class ClusterTests(unittest.TestCase):
    CL = {"after_sales": ["a", "b"], "money": ["c"]}

    def test_cluster_counts_distinct_rows_not_tag_sums(self):
        ev = [row(1, ("a", "b")),                       # both tags in one cluster -> counts once
              row(2, ("a",), thread="t2"), row(3, ("c",), thread="t3", community="C2"),
              row(4, ("a",), voice="bystander", thread="t4")]
        out = ct.tally(ev, AS_OF, "strict", self.CL)["clusters"]
        by = {c["cluster"]: c for c in out}
        self.assertEqual(by["after_sales"]["distinct_rows"], 2)
        self.assertEqual(by["after_sales"]["distinct_threads"], 2)
        self.assertEqual(by["money"]["community_counts"], {"C2": 1})
        self.assertEqual(out[0]["cluster"], "after_sales")          # sorted by rows desc

    def test_no_clusters_is_fine(self):
        self.assertEqual(ct.tally([row(1)], AS_OF, "strict")["clusters"], [])

    def test_unknown_cluster_tag_is_reported(self):
        probs = ct.validate_clusters({"x": ["a", "ghost"]}, TAGS)
        self.assertEqual(len(probs), 1)
        self.assertIn("ghost", probs[0])


class ValidateTests(unittest.TestCase):
    def check(self, **kw):
        return ct.validate([row(1, **kw)], TAGS, AS_OF)

    def test_clean_row_has_no_problems(self):
        self.assertEqual(self.check(), [])

    def test_unknown_tag(self):
        self.assertTrue(any("unknown tag" in p for p in self.check(tags=("zzz",))))

    def test_handle_in_quote(self):
        self.assertTrue(any("handle" in p for p in self.check(quote="thanks u/someone")))
        self.assertTrue(any("handle" in p for p in self.check(quote="ask @someone")))

    def test_quote_too_long(self):
        self.assertTrue(any("longer" in p for p in self.check(quote="x" * 321)))

    def test_undated_without_hint_and_future_date(self):
        self.assertTrue(any("date problem" in p for p in self.check(date=None)))
        self.assertTrue(any("date problem" in p for p in self.check(date="2027-01-01")))
        self.assertTrue(any("date problem" in p for p in self.check(date="not-a-date")))

    def test_bad_enums_and_spend(self):
        self.assertTrue(any("voice" in p for p in self.check(voice="shouting")))
        self.assertTrue(any("community" in p for p in self.check(community="C9")))
        self.assertTrue(any("source_type" in p for p in self.check(source_type="tiktok")))
        self.assertTrue(any("spend kind" in p for p in
                            self.check(spend=dict(zar=5, kind="guess", what="x"))))
        self.assertTrue(any("not numeric" in p for p in
                            self.check(spend=dict(zar="five", kind="stated_spend", what="x"))))

    def test_duplicates_detected(self):
        a = row(1)
        b = row(2, url=a["url"], quote=a["quote"])
        self.assertTrue(any("duplicate" in p for p in ct.validate([a, b], TAGS, AS_OF)))


class CoverageTests(unittest.TestCase):
    def test_items_read_by_community_and_source(self):
        scanned = [unit("C1", 12, st="reddit"), unit("C1", 8, st="forum"),
                   unit("C2", 5, st="review_site"), unit("C2", 99, date="2020-01-01")]
        cov = ct.coverage([row(1)], scanned, AS_OF, "strict")
        self.assertEqual(cov["table"]["C1"]["reddit"]["items_read"], 12)
        self.assertEqual(cov["table"]["C1"]["forum"]["items_read"], 8)
        self.assertEqual(cov["table"]["C2"]["review_site"]["items_read"], 5)
        self.assertEqual(cov["table"]["C1"]["reddit"]["counted_rows"], 1)
        self.assertIn("facebook", cov["source_types_with_zero_items"]["C1"])
        self.assertNotIn("reddit", cov["source_types_with_zero_items"]["C1"])


class CliTests(unittest.TestCase):
    def make_study(self, evidence, scanned):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "codebook.json"), "w") as fh:
            json.dump({"tags": TAGS}, fh)
        for name, rows in (("evidence.jsonl", evidence), ("scanned.jsonl", scanned)):
            with open(os.path.join(d, name), "w") as fh:
                fh.write("\n".join(json.dumps(r) for r in rows) + "\n")
        return d

    def test_end_to_end_outputs(self):
        d = self.make_study([row(1), row(2, thread="t2")],
                            [unit("C1", 30), unit("C2", 30), unit("C3", 30)])
        js, md = os.path.join(d, "o.json"), os.path.join(d, "o.md")
        code = ct.main(["--dir", d, "--as-of", "2026-10-02", "--out-json", js, "--out-md", md])
        self.assertEqual(code, 0)
        with open(js) as fh:
            data = json.load(fh)
        self.assertEqual(data["meta"]["window_used"], "strict")
        self.assertEqual(data["ranking"]["pains"][0]["tag"], "a")
        with open(md) as fh:
            text = fh.read()
        self.assertIn("Ranked pains", text)
        self.assertIn("`a`", text)

    def test_strict_flag_returns_nonzero_on_problems(self):
        d = self.make_study([row(1, tags=("nope",))], [unit("C1", 30)])
        args = ["--dir", d, "--as-of", "2026-10-02", "--out-json", os.path.join(d, "o.json")]
        self.assertEqual(ct.main(args), 0)
        self.assertEqual(ct.main(args + ["--strict"]), 1)


class GuardrailTests(unittest.TestCase):
    def test_module_is_offline_and_stdlib_only(self):
        src = inspect.getsource(ct)
        for banned in ("import requests", "urllib.request", "http.client", "import socket",
                       "import openai", "import anthropic"):
            self.assertNotIn(banned, src)


class RealStudyIntegrity(unittest.TestCase):
    """The committed evidence log must validate and obey the counting rules."""

    DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       ct.DEFAULT_DIR)

    @unittest.skipUnless(os.path.exists(os.path.join(DIR, "evidence.jsonl")),
                         "study data not present")
    def test_study_validates_cleanly(self):
        result = ct.build_result(self.DIR, dt.date(2026, 10, 2))
        self.assertEqual(result["meta"]["validation_problems"], [])
        self.assertIn(result["meta"]["window_used"], ("strict", "extended"))
        pains = result["ranking"]["pains"]
        self.assertTrue(pains)
        counts = [p["count"] for p in pains]
        self.assertEqual(counts, sorted(counts, reverse=True))
        for p in pains:
            self.assertTrue(set(p["voice_counts"]) <= set(ct.COUNTED_VOICES))


if __name__ == "__main__":
    unittest.main()
