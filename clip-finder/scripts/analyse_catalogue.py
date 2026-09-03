#!/usr/bin/env python3
"""Turn data/catalogue.json into the evidence that de-assumes the taste rubric.

v2 changes:
  - franchise regex widened (v1 required "day at/in" and missed "day doing X")
  - all recurring formats detected, not just first-and-last-day
  - performance is percentile rank within a publish cohort, not a ratio.
    Ratios explode when a cohort median is small (one video scored 2724x),
    which sorts by outlier noise rather than ranking anything.
  - per-format spread (best / median) to show whether the format or the
    individual clip is doing the work

Usage:  python analyse_catalogue.py
"""
import collections
import json
import pathlib
import re
import statistics
import sys
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "data" / "catalogue.json"
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]+")

# Recurring title formats, most specific first - a title takes the first match.
FORMATS = [
    ("first_last_day", re.compile(r"first\s*(?:&|and|n)\s*last\s+day", re.I)),
    ("who_won",        re.compile(r"^who\s+won", re.I)),
    ("oh_no",          re.compile(r"^oh\s+no\b", re.I)),
    ("true_or_false",  re.compile(r"^true\s+or\s+false", re.I)),
    ("reacting_with",  re.compile(r"^reacting\s+with", re.I)),
    ("rate_my",        re.compile(r"^rate\s+my", re.I)),
    ("that_went_well", re.compile(r"that went well|well that went|went as planned", re.I)),
    ("send_this_to",   re.compile(r"^send\s+this\s+to", re.I)),
]

# Venue inside a first-and-last-day title. Widened preposition set.
VENUE = re.compile(
    r"first\s*(?:&|and|n)\s*last\s+day\s+"
    r"(?:at|in|on|of|doing|playing|as|with|trying)?\s*"
    r"(?:an?|the|my)?\s*(.+)", re.I)


def clean(text):
    text = EMOJI.sub("", text)
    text = re.sub(r"#\w+", "", text)
    return re.sub(r"\s+", " ", text).strip(" -|.!?,")


def classify(title):
    t = clean(title)
    for name, pattern in FORMATS:
        if pattern.search(t):
            return name
    return "other"


def cohort_percentile(videos):
    """Percentile rank of views against everything published within 60 days.

    Rank-based, so a single 46M outlier cannot distort the scale the way a
    ratio does. 0.5 = median for its era, 1.0 = best of its era.
    """
    dated = []
    for v in videos:
        if not v.get("published_at"):
            continue
        try:
            v["_ts"] = datetime.fromisoformat(
                v["published_at"].replace("Z", "+00:00")).timestamp()
            dated.append(v)
        except ValueError:
            continue
    window = 60 * 86400
    for v in dated:
        peers = [p["views"] for p in dated if abs(p["_ts"] - v["_ts"]) <= window]
        if len(peers) < 5:            # too few neighbours to rank against
            v["pct"] = None
            continue
        below = sum(1 for x in peers if x < v["views"])
        v["pct"] = round(below / (len(peers) - 1), 3)


def fmt(n):
    if n >= 1_000_000:
        return "{:.1f}M".format(n / 1_000_000)
    if n >= 1_000:
        return "{:.0f}k".format(n / 1_000)
    return "{:,.0f}".format(n)


def main():
    if not CATALOGUE.exists():
        sys.exit("No catalogue yet. Run:  python scripts/fetch_catalogue.py @doctorsango")

    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    videos = [v for v in data["videos"] if v.get("views") is not None]
    cohort_percentile(videos)
    for v in videos:
        v["_format"] = classify(v["title"])

    by_format = collections.defaultdict(list)
    for v in videos:
        by_format[v["_format"]].append(v)

    L = []
    add = L.append
    add("# Catalogue report v2 - {}\n".format(data["channel"]))
    add("{} videos. Every one is a Short.\n".format(len(videos)))

    durations = sorted(v["duration_s"] for v in videos if v.get("duration_s"))
    med_dur = statistics.median(durations)
    add("## Duration\n")
    add("- median **{:.0f}s**, p25 {}s, p75 {}s, max {}s".format(
        med_dur, durations[len(durations) // 4],
        durations[3 * len(durations) // 4], max(durations)))
    under20 = sum(1 for d in durations if d <= 20) / len(durations)
    add("- **{:.0%} of uploads are 20s or under**\n".format(under20))
    add("> At 20s or less there is no montage. That is one clip plus a reaction,\n"
        "> not a pack of eight.\n")

    add("## Formats, ranked by median views\n")
    add("| Format | Videos | Median views | Best | Spread | Median dur |")
    add("|---|---:|---:|---:|---:|---:|")
    ranked = sorted(by_format.items(),
                    key=lambda kv: statistics.median([x["views"] for x in kv[1]]),
                    reverse=True)
    for name, vids in ranked:
        med = statistics.median([x["views"] for x in vids])
        best = max(x["views"] for x in vids)
        spread = best / med if med else 0
        d = statistics.median([x.get("duration_s", 0) for x in vids])
        add("| `{}` | {} | {} | {} | {:,.0f}x | {:.0f}s |".format(
            name, len(vids), fmt(med), fmt(best), spread, d))
    add("")
    add("> **Spread** is best divided by median within the format. A high number\n"
        "> means the format is not what makes a video work - the individual clip\n"
        "> is. That is precisely the gap a clip finder fills.\n")

    venues = collections.defaultdict(list)
    for v in by_format.get("first_last_day", []):
        m = VENUE.search(clean(v["title"]))
        if m:
            venue = re.sub(r"\s*\(.*?\)\s*", "", clean(m.group(1))).lower().strip()
            if venue:
                venues[venue].append(v)

    add("## first_last_day venues ({} videos, {} venues)\n".format(
        len(by_format.get("first_last_day", [])), len(venues)))
    solid = {k: v for k, v in venues.items() if len(v) >= 2}
    if solid:
        add("Venues with 2+ videos - the only ones with enough data to rank:\n")
        add("| Venue | Videos | Median views | Best |")
        add("|---|---:|---:|---:|")
        for venue, vids in sorted(
                solid.items(),
                key=lambda kv: statistics.median([x["views"] for x in kv[1]]),
                reverse=True):
            add("| {} | {} | {} | {} |".format(
                venue, len(vids),
                fmt(statistics.median([x["views"] for x in vids])),
                fmt(max(x["views"] for x in vids))))
        add("")
    singles = sorted(k for k, v in venues.items() if len(v) == 1)
    if singles:
        add("**Single-sample venues (n=1, cannot be ranked):** {}\n".format(
            ", ".join(singles)))

    add("## Top 20 by raw views\n")
    add("| Views | Pct | Dur | Format | Title |")
    add("|---:|---:|---:|---|---|")
    for v in sorted(videos, key=lambda x: x["views"], reverse=True)[:20]:
        p = "{:.2f}".format(v["pct"]) if v.get("pct") is not None else "-"
        add("| {} | {} | {}s | `{}` | {} |".format(
            fmt(v["views"]), p, v.get("duration_s", 0), v["_format"],
            clean(v["title"])[:55]))
    add("")

    add("## Hit rate\n")
    for threshold in (1_000_000, 100_000, 10_000):
        n = sum(1 for v in videos if v["views"] >= threshold)
        add("- **{}** videos over {} views ({:.1%})".format(
            n, fmt(threshold), n / len(videos)))
    add("")
    med_all = statistics.median([v["views"] for v in videos])
    mean_all = statistics.mean([v["views"] for v in videos])
    add("Median upload: **{} views**. Mean: {}. The gap between those two "
        "is the whole story.\n".format(fmt(med_all), fmt(mean_all)))

    out = ROOT / "data" / "catalogue_report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print("\n[written to {}]".format(out), file=sys.stderr)


if __name__ == "__main__":
    main()
