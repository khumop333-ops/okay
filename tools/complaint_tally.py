"""Complaint-mining tally. tools/complaint_tally.py v1.0.0.

Aggregates the evidence log of a complaint-mining study (default study:
``research/solar-complaint-mining``) into a ranked list of pain points.  It
contains NO cost math and NO product ideas -- it only counts what people said.

Pre-committed counting rules (written before the data was tallied):

1. Only voices ``owner`` and ``prospective`` count toward ranking.  ``trade``
   (installers/sellers) and ``bystander`` (second-hand opinion) rows are logged
   but excluded; they are reported separately so the gap is visible.
2. Windows are derived from ``--as-of``: strict = last 12 months, extended =
   last 24 months.  Older rows are dropped.  If ANY community has fewer than
   ``--min-scanned`` (30) scanned items inside the strict window, every
   community is ranked on the 24-month window and each pain's strict-window
   share is shown.  Otherwise the strict window is used.
3. Ranking: item count (descending); tie-break on distinct threads, then on
   community spread, then tag name (so the output is deterministic).
4. A tag is flagged when ONE thread supplies MORE than 40% of its items.
5. An equal-community-weight score is reported next to the pooled count so a
   large community cannot silently dominate the ranking.

Standard library only (README requirements.txt).
"""

from __future__ import annotations

import argparse
import calendar
import collections
import datetime as dt
import json
import os
import re
import sys

VERSION = "1.0.0"
COUNTED_VOICES = ("owner", "prospective")
VOICES = ("owner", "prospective", "trade", "bystander")
COMMUNITIES = ("C1", "C2", "C3")
SOURCE_TYPES = ("reddit", "forum", "review_site", "facebook", "x",
                "app_review", "product_review")
SPEND_KINDS = ("stated_spend", "stated_wtp", "quoted_price")
MIN_SCANNED = 30
CONCENTRATION_LIMIT = 0.40
MAX_QUOTE = 320
HANDLE_RE = re.compile(r"(^|\s)u/\w+|@\w+")
DEFAULT_DIR = os.path.join("research", "solar-complaint-mining")


# ---------------------------------------------------------------- dates
def months_back(d: dt.date, n: int) -> dt.date:
    """``d`` minus ``n`` calendar months, clamping the day (29 Feb -> 28 Feb)."""
    idx = d.year * 12 + (d.month - 1) - n
    year, month = divmod(idx, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def window_starts(as_of: dt.date) -> tuple[dt.date, dt.date]:
    """(strict_start, extended_start) = as_of minus 12 / 24 months."""
    return months_back(as_of, 12), months_back(as_of, 24)


def classify(date_str, window_hint, as_of: dt.date) -> str:
    """'strict' | 'extended' | 'out' | 'future' | 'undated' for one row."""
    strict_start, extended_start = window_starts(as_of)
    if date_str:
        d = dt.date.fromisoformat(date_str)
        if d > as_of:
            return "future"
        if d >= strict_start:
            return "strict"
        if d >= extended_start:
            return "extended"
        return "out"
    if window_hint in ("strict", "extended"):
        return window_hint
    return "undated"


# ---------------------------------------------------------------- io
def load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_study(directory: str) -> dict:
    with open(os.path.join(directory, "codebook.json"), encoding="utf-8") as fh:
        codebook = json.load(fh)
    return {
        "codebook": codebook,
        "evidence": load_jsonl(os.path.join(directory, "evidence.jsonl")),
        "scanned": load_jsonl(os.path.join(directory, "scanned.jsonl")),
    }


# ---------------------------------------------------------------- validation
def validate(evidence: list[dict], tags: dict, as_of: dt.date) -> list[str]:
    """Return a list of human-readable problems (empty list = clean)."""
    problems: list[str] = []
    seen = set()
    for row in evidence:
        rid = row.get("id", "?")
        if row.get("community") not in COMMUNITIES:
            problems.append(f"{rid}: bad community {row.get('community')!r}")
        if row.get("voice") not in VOICES:
            problems.append(f"{rid}: bad voice {row.get('voice')!r}")
        if row.get("source_type") not in SOURCE_TYPES:
            problems.append(f"{rid}: bad source_type {row.get('source_type')!r}")
        if not row.get("tags"):
            problems.append(f"{rid}: no tags")
        for t in row.get("tags", []):
            if t not in tags:
                problems.append(f"{rid}: unknown tag {t!r}")
        quote = row.get("quote", "")
        if not quote:
            problems.append(f"{rid}: empty quote")
        if len(quote) > MAX_QUOTE:
            problems.append(f"{rid}: quote longer than {MAX_QUOTE} chars")
        if HANDLE_RE.search(quote):
            problems.append(f"{rid}: username/handle in quote")
        if not str(row.get("url", "")).startswith("http"):
            problems.append(f"{rid}: url missing")
        key = (row.get("url"), quote[:60])
        if key in seen:
            problems.append(f"{rid}: duplicate of an earlier row")
        seen.add(key)
        try:
            state = classify(row.get("date"), row.get("window_hint"), as_of)
        except ValueError:
            state = "badformat"
        if state in ("undated", "future", "badformat"):
            problems.append(f"{rid}: date problem ({state})")
        spend = row.get("spend")
        if spend is not None:
            if spend.get("kind") not in SPEND_KINDS:
                problems.append(f"{rid}: spend kind {spend.get('kind')!r} not allowed")
            if not isinstance(spend.get("zar"), (int, float)):
                problems.append(f"{rid}: spend amount not numeric")
    return problems


# ---------------------------------------------------------------- windows
def scanned_in_window(scanned: list[dict], as_of: dt.date, window: str) -> dict:
    """Items read per community inside ``window`` ('strict' or 'extended')."""
    allowed = {"strict"} if window == "strict" else {"strict", "extended"}
    out = {c: 0 for c in COMMUNITIES}
    for unit in scanned:
        state = classify(unit.get("date"), unit.get("window_hint"), as_of)
        if state in allowed and unit.get("community") in out:
            out[unit["community"]] += int(unit.get("items_read", 0))
    return out


def select_window(scanned: list[dict], as_of: dt.date,
                  min_scanned: int = MIN_SCANNED) -> dict:
    """Apply the pre-committed fallback rule."""
    strict_counts = scanned_in_window(scanned, as_of, "strict")
    short = sorted(c for c, n in strict_counts.items() if n < min_scanned)
    window = "extended" if short else "strict"
    return {
        "window": window,
        "strict_scanned": strict_counts,
        "extended_scanned": scanned_in_window(scanned, as_of, "extended"),
        "communities_below_minimum_in_strict": short,
        "min_scanned": min_scanned,
        "rule": ("24-month window used because " + ", ".join(short) +
                 f" had < {min_scanned} scanned items in the strict 12-month window"
                 if short else
                 "strict 12-month window used (every community >= "
                 f"{min_scanned} scanned items)"),
    }


# ---------------------------------------------------------------- tally
def in_window(row: dict, as_of: dt.date, window: str) -> str | None:
    """Return the row's state if it is inside ``window``, else None."""
    state = classify(row.get("date"), row.get("window_hint"), as_of)
    allowed = {"strict"} if window == "strict" else {"strict", "extended"}
    return state if state in allowed else None


def _top_thread_share(items: list[dict]) -> tuple[float, str]:
    counts = collections.Counter(r["thread_key"] for r in items)
    thread, n = counts.most_common(1)[0]
    return n / len(items), thread


def cluster_counts(counted_rows: list[dict], clusters: dict) -> list[dict]:
    """Post-hoc theme view: DISTINCT counted rows carrying >= 1 tag of a cluster.

    Interpretation aid only -- the ranking stays tag-level (rule 3).  A row with
    two tags of the same cluster counts once, so near-synonym tags cannot
    double-count one complaint.
    """
    out = []
    for name, members in (clusters or {}).items():
        rows = [r for r in counted_rows if set(r["tags"]) & set(members)]
        out.append({
            "cluster": name,
            "tags": list(members),
            "distinct_rows": len(rows),
            "distinct_threads": len({r["thread_key"] for r in rows}),
            "community_counts": dict(sorted(collections.Counter(
                r["community"] for r in rows).items())),
            "source_counts": dict(sorted(collections.Counter(
                r["source_type"] for r in rows).items())),
        })
    out.sort(key=lambda c: (-c["distinct_rows"], c["cluster"]))
    return out


def validate_clusters(clusters: dict, tags: dict) -> list[str]:
    return [f"cluster {name!r}: unknown tag {t!r}"
            for name, members in (clusters or {}).items()
            for t in members if t not in tags]


def tally(evidence: list[dict], as_of: dt.date, window: str,
          clusters: dict | None = None) -> dict:
    """Rank tags using the counting rules in the module docstring."""
    counted, excluded_voice, dropped = [], collections.Counter(), collections.Counter()
    for row in evidence:
        state = in_window(row, as_of, window)
        if state is None:
            dropped[classify(row.get("date"), row.get("window_hint"), as_of)] += 1
            continue
        if row["voice"] in COUNTED_VOICES:
            counted.append((row, state))
        else:
            excluded_voice[row["voice"]] += 1

    community_totals = collections.Counter(r["community"] for r, _ in counted)
    by_tag: dict[str, list[tuple[dict, str]]] = collections.defaultdict(list)
    for row, state in counted:
        for tag in row["tags"]:
            by_tag[tag].append((row, state))

    pains = []
    for tag, pairs in by_tag.items():
        items = [r for r, _ in pairs]
        strict_n = sum(1 for _, s in pairs if s == "strict")
        share, top_thread = _top_thread_share(items)
        comm_counts = collections.Counter(r["community"] for r in items)
        ew = sum(comm_counts.get(c, 0) / community_totals[c]
                 for c in COMMUNITIES if community_totals[c]) / max(
                     1, sum(1 for c in COMMUNITIES if community_totals[c]))
        threads = {r["thread_key"] for r in items}
        pains.append({
            "tag": tag,
            "count": len(items),
            "distinct_threads": len(threads),
            "communities": sorted(comm_counts),
            "community_counts": dict(sorted(comm_counts.items())),
            "voice_counts": dict(collections.Counter(r["voice"] for r in items)),
            "source_counts": dict(collections.Counter(r["source_type"] for r in items)),
            "strict_count": strict_n,
            "strict_share": round(strict_n / len(items), 2),
            "top_thread": top_thread,
            "top_thread_share": round(share, 2),
            "concentration_flag": share > CONCENTRATION_LIMIT,
            "recurring": len(items) >= 2 and len(threads) >= 2,
            "equal_weight_score": round(ew, 4),
            "evidence_ids": [r["id"] for r in items],
            "workarounds": sorted({r["workaround"] for r in items if r.get("workaround")}),
            "spend": [dict(s, id=r["id"], community=r["community"]) for r in items
                      if (s := r.get("spend"))],
            "solutions_mentioned": sorted({s for r in items
                                           for s in r.get("solutions_mentioned", [])}),
        })

    pains.sort(key=lambda p: (-p["count"], -p["distinct_threads"],
                              -len(p["communities"]), p["tag"]))
    for i, p in enumerate(pains, 1):
        p["rank"] = i
    ew_sorted = sorted(pains, key=lambda p: (-p["equal_weight_score"], p["tag"]))
    for i, p in enumerate(ew_sorted, 1):
        p["rank_equal_weight"] = i

    # tags that only bystanders / trade talk about (visible but not ranked)
    counted_tags = set(by_tag)
    other = collections.defaultdict(collections.Counter)
    for row in evidence:
        if in_window(row, as_of, window) and row["voice"] not in COUNTED_VOICES:
            for tag in row["tags"]:
                other[tag][row["voice"]] += 1
    non_counting = [{"tag": t, "voices": dict(c), "owner_or_prospective_items":
                     len(by_tag.get(t, []))} for t, c in sorted(other.items())]
    return {
        "pains": pains,
        "counted_rows": len(counted),
        "community_totals": dict(community_totals),
        "excluded_by_voice": dict(excluded_voice),
        "dropped_by_window": dict(dropped),
        "bystander_or_trade_tags": non_counting,
        "clusters": cluster_counts([r for r, _ in counted], clusters),
    }


def coverage(evidence: list[dict], scanned: list[dict], as_of: dt.date,
             window: str) -> dict:
    """Per community x source type: items read, evidence rows, counted rows."""
    table = {}
    for c in COMMUNITIES:
        row = {}
        for st in SOURCE_TYPES:
            read = sum(int(u.get("items_read", 0)) for u in scanned
                       if u["community"] == c and u["source_type"] == st
                       and in_window(u, as_of, window))
            ev_rows = [e for e in evidence if e["community"] == c
                       and e["source_type"] == st and in_window(e, as_of, window)]
            row[st] = {"items_read": read, "evidence_rows": len(ev_rows),
                       "counted_rows": sum(1 for e in ev_rows
                                           if e["voice"] in COUNTED_VOICES)}
        table[c] = row
    gaps = {c: [st for st in SOURCE_TYPES if table[c][st]["items_read"] == 0]
            for c in COMMUNITIES}
    return {"table": table, "source_types_with_zero_items": gaps}


def build_result(directory: str, as_of: dt.date,
                 min_scanned: int = MIN_SCANNED) -> dict:
    study = load_study(directory)
    tags = study["codebook"]["tags"]
    clusters = study["codebook"].get("clusters", {})
    problems = validate(study["evidence"], tags, as_of) + validate_clusters(clusters, tags)
    sel = select_window(study["scanned"], as_of, min_scanned)
    strict_start, extended_start = window_starts(as_of)
    result = tally(study["evidence"], as_of, sel["window"], clusters)
    return {
        "meta": {
            "tool": f"tools/complaint_tally.py v{VERSION}",
            "as_of": as_of.isoformat(),
            "strict_start": strict_start.isoformat(),
            "extended_start": extended_start.isoformat(),
            "window_used": sel["window"],
            "window_rule": sel["rule"],
            "scanned_items_strict": sel["strict_scanned"],
            "scanned_items_extended": sel["extended_scanned"],
            "evidence_rows_total": len(study["evidence"]),
            "validation_problems": problems,
        },
        "coverage": coverage(study["evidence"], study["scanned"], as_of, sel["window"]),
        "ranking": result,
        "tag_definitions": {t: d["definition"] for t, d in tags.items()},
    }


# ---------------------------------------------------------------- rendering
def render_markdown(result: dict, top: int = 10) -> str:
    meta, rank = result["meta"], result["ranking"]
    lines = [f"# Complaint tally (as of {meta['as_of']})", "",
             f"- Tool: `{meta['tool']}`",
             f"- Strict window starts {meta['strict_start']}; extended starts {meta['extended_start']}",
             f"- Window used for ranking: **{meta['window_used']}** - {meta['window_rule']}",
             f"- Scanned items, strict window: {meta['scanned_items_strict']}",
             f"- Scanned items, 24-month window: {meta['scanned_items_extended']}",
             f"- Evidence rows: {meta['evidence_rows_total']} total; "
             f"{rank['counted_rows']} owner/prospective rows counted; "
             f"excluded by voice {rank['excluded_by_voice']}; "
             f"dropped by window {rank['dropped_by_window']}",
             f"- Validation problems: {len(meta['validation_problems'])}", "",
             "## Ranked pains (owner/prospective items only)", "",
             "| Rank | Pain tag | Items | Threads | Communities | Strict share | Equal-weight rank | Flags |",
             "|---|---|---|---|---|---|---|---|"]
    for p in rank["pains"][:top]:
        flags = []
        if p["concentration_flag"]:
            flags.append(f"{int(p['top_thread_share'] * 100)}% from one thread")
        if not p["recurring"]:
            flags.append("not recurring")
        lines.append(f"| {p['rank']} | `{p['tag']}` | {p['count']} | {p['distinct_threads']} | "
                     f"{'/'.join(p['communities'])} | {int(p['strict_share'] * 100)}% | "
                     f"{p['rank_equal_weight']} | {'; '.join(flags) or '-'} |")
    if rank.get("clusters"):
        lines += ["", "## Theme clusters (post-hoc, interpretation only; distinct rows)", "",
                  "| Cluster | Distinct rows | Threads | By community |", "|---|---|---|---|"]
        for c in rank["clusters"]:
            lines.append(f"| {c['cluster']} | {c['distinct_rows']} | {c['distinct_threads']} | "
                         f"{c['community_counts']} |")
    rest = rank["pains"][top:]
    if rest:
        lines += ["", f"Below the top {top}: " + ", ".join(
            f"`{p['tag']}` ({p['count']})" for p in rest)]
    lines += ["", "## Coverage (items read in the window used)", "",
              "| Community | " + " | ".join(SOURCE_TYPES) + " |",
              "|---|" + "---|" * len(SOURCE_TYPES)]
    for c in COMMUNITIES:
        cells = [str(result["coverage"]["table"][c][st]["items_read"]) for st in SOURCE_TYPES]
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    if meta["validation_problems"]:
        lines += ["", "## Validation problems", ""] + [f"- {p}" for p in meta["validation_problems"]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- cli
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--as-of", default=dt.date.today().isoformat(),
                    help="YYYY-MM-DD used to derive the windows (default: today)")
    ap.add_argument("--min-scanned", type=int, default=MIN_SCANNED)
    ap.add_argument("--out-json")
    ap.add_argument("--out-md")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if validation finds any problem")
    args = ap.parse_args(argv)
    as_of = dt.date.fromisoformat(args.as_of)
    result = build_result(args.dir, as_of, args.min_scanned)
    md = render_markdown(result, args.top)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as fh:
            fh.write(md)
    if not (args.out_json or args.out_md):
        sys.stdout.write(md)
    problems = result["meta"]["validation_problems"]
    if problems:
        sys.stderr.write(f"{len(problems)} validation problem(s):\n" +
                         "\n".join(f"  - {p}" for p in problems) + "\n")
    return 1 if (problems and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
