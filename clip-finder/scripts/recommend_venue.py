#!/usr/bin/env python3
"""Venue recommender — scores ANY venue, tried or not.

A ranked list of venues goes stale as soon as he works through it, so instead of
a lookup table this fits a model on the 41 observed uploads and uses it to score
venues he has never tried.

Two modes:

    python recommend_venue.py                  # what should he do next
    python recommend_venue.py "trampoline park"  # is this genre worth doing

Features (each 0-3, higher = more of it):
    stakes      how badly can this visibly go wrong
    physical    is failure spectacular and bodily
    esw         elevation / speed / water present
    social      crowds, strangers, alcohol
    skill       is there visible expertise to fail at
    supply      how much footage of this exists online
    saturation  how done-to-death this is in short-form comedy (penalised)

Fitted with ridge regression on log10(median views), validated leave-one-out.
"""
import math
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FEATURES = ["stakes", "physical", "esw", "social", "skill", "supply", "saturation"]

# --- Observed: venue -> (features, median views across his uploads) ----------
# Views are medians from data/catalogue.json. pub and pub/bar merged.
TRIED = {
    "parkour":            ([3, 3, 2, 0, 3, 3, 1], 219598),
    "fishing":            ([1, 2, 2, 1, 2, 3, 1],  43499),
    "pub":                ([2, 2, 0, 3, 0, 3, 1],  41234),
    "skateboarding":      ([3, 3, 1, 1, 3, 3, 2],  30854),
    "not being on land":  ([2, 3, 2, 1, 1, 2, 0],  28430),
    "mcdonalds":          ([1, 1, 0, 3, 0, 3, 2],  21621),
    "farming":            ([2, 2, 1, 0, 1, 2, 0],  17831),
    "hiking":             ([1, 1, 1, 0, 0, 2, 1],  14683),
    "disney land":        ([1, 1, 2, 2, 0, 2, 1],  14372),
    "house parties":      ([1, 1, 0, 3, 0, 3, 2],  14195),
    "driving instructor": ([2, 1, 1, 1, 2, 2, 1],  13786),
    "park":               ([0, 1, 0, 1, 0, 2, 1],  13012),
    "being spider-man":   ([1, 2, 1, 1, 1, 1, 1],  12974),
    "arcade":             ([0, 1, 0, 1, 1, 2, 1],  11247),
    "zoo":                ([1, 0, 0, 1, 0, 2, 1],   9619),
    "baby sitting":       ([1, 1, 0, 2, 1, 2, 1],   9359),
    "football":           ([1, 2, 1, 2, 2, 3, 2],   9323),
    "restaurants":        ([1, 1, 0, 2, 0, 2, 1],   8982),
    "shopping in public": ([0, 1, 0, 2, 0, 2, 2],   8013),
    "housekeeper":        ([0, 1, 0, 1, 0, 1, 1],   7141),
    "halloween":          ([1, 1, 0, 2, 0, 2, 1],   6665),
    "barbers":            ([1, 0, 0, 1, 2, 2, 2],   5866),
    "birthday parties":   ([0, 1, 0, 2, 0, 2, 1],   5415),
    "bridge jumping":     ([3, 3, 2, 1, 1, 2, 1],   4401),
    "traffic":            ([1, 0, 1, 1, 0, 2, 1],   4345),
    "bowling":            ([0, 1, 0, 1, 1, 2, 3],   3812),
    "public transport":   ([0, 1, 0, 2, 0, 2, 2],   3440),
    "mall":               ([0, 1, 0, 2, 0, 2, 2],   2792),
    "construction":       ([2, 2, 1, 0, 1, 2, 1],   2293),
    "gym":                ([1, 2, 0, 1, 2, 3, 3],   2269),
}

# --- Untried candidate library ----------------------------------------------
CANDIDATES = {
    "trampoline park":     [2, 3, 1, 2, 1, 3, 2],
    "go-karting":          [2, 2, 2, 2, 2, 3, 1],
    "ice skating":         [2, 3, 1, 2, 2, 3, 2],
    "water park":          [2, 3, 2, 2, 0, 3, 1],
    "skiing":              [3, 3, 2, 1, 3, 3, 1],
    "snowboarding":        [3, 3, 2, 1, 3, 3, 1],
    "surfing":             [3, 3, 2, 0, 3, 3, 1],
    "horse riding":        [3, 3, 1, 0, 3, 2, 0],
    "rock climbing":       [3, 2, 2, 0, 3, 2, 1],
    "laser tag":           [0, 1, 0, 2, 1, 1, 0],
    "paintball":           [2, 2, 1, 2, 1, 2, 1],
    "dirt bikes":          [3, 3, 2, 1, 3, 3, 1],
    "bmx":                 [3, 3, 2, 1, 3, 3, 1],
    "high diving":         [2, 3, 2, 1, 2, 2, 1],
    "jet skis":            [3, 3, 2, 1, 2, 2, 0],
    "wakeboarding":        [3, 3, 2, 1, 3, 2, 0],
    "rollerblading":       [2, 3, 1, 1, 2, 2, 1],
    "boxing":              [3, 3, 0, 1, 3, 3, 2],
    "rugby":               [2, 3, 1, 2, 2, 2, 1],
    "obstacle course":     [2, 3, 2, 1, 3, 2, 1],
    "zip lining":          [2, 2, 2, 1, 0, 2, 0],
    "bungee jumping":      [3, 2, 2, 1, 0, 2, 1],
    "fairground":          [2, 2, 2, 2, 0, 2, 1],
    "camping":             [1, 2, 1, 1, 1, 2, 1],
    "diy at home":         [2, 2, 1, 0, 2, 3, 2],
    "moving house":        [2, 2, 1, 1, 1, 2, 1],
    "weddings":            [1, 1, 0, 3, 0, 3, 2],
    "festivals":           [1, 2, 0, 3, 0, 2, 1],
    "nightclub":           [2, 2, 0, 3, 0, 3, 2],
    "karaoke":             [0, 0, 0, 3, 1, 2, 1],
    "driving range":       [1, 2, 1, 1, 2, 3, 1],
    "tennis":              [1, 2, 1, 1, 2, 2, 1],
    "swimming baths":      [2, 2, 2, 2, 1, 3, 2],
    "quad biking":         [3, 3, 2, 1, 2, 2, 0],
    "soft play":           [1, 2, 1, 2, 0, 2, 1],
    "crazy golf":          [0, 1, 0, 2, 1, 2, 1],
    "escape room":         [0, 0, 0, 2, 1, 1, 0],
    "sledging":            [2, 3, 2, 1, 1, 2, 0],
    "inflatable assault course": [1, 3, 1, 2, 0, 2, 1],
    "roller disco":        [2, 3, 1, 2, 2, 2, 0],
    "canoeing":            [2, 3, 2, 1, 2, 2, 0],
    "scooters":            [2, 3, 1, 1, 2, 2, 1],
    "airport":             [1, 1, 1, 2, 0, 2, 1],
    "the dentist":         [1, 0, 0, 1, 1, 2, 1],
    "archery":             [2, 1, 0, 1, 2, 2, 0],
    "axe throwing":        [3, 1, 0, 2, 2, 2, 0],
}


# --- Linear algebra (pure stdlib) -------------------------------------------
def solve(A, b):
    """Gaussian elimination with partial pivoting."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            continue
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def ridge(X, y, lam=1.0):
    """Fit with an intercept. Ridge because n=30 and p=7 would overfit badly."""
    Xb = [[1.0] + row for row in X]
    p = len(Xb[0])
    A = [[sum(Xb[i][a] * Xb[i][b] for i in range(len(Xb))) + (lam if a == b and a > 0 else 0.0)
          for b in range(p)] for a in range(p)]
    rhs = [sum(Xb[i][a] * y[i] for i in range(len(Xb))) for a in range(p)]
    return solve(A, rhs)


def predict(w, feats):
    return w[0] + sum(w[i + 1] * f for i, f in enumerate(feats))


def spearman(a, b):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((x - mb) ** 2 for x in rb))
    return num / den if den else 0.0


def tier(views):
    if views >= 100_000:
        return "A"
    if views >= 15_000:
        return "B"
    if views >= 6_000:
        return "C"
    return "D"


def fit_and_validate():
    names = list(TRIED)
    X = [TRIED[n][0] for n in names]
    y = [math.log10(TRIED[n][1]) for n in names]

    # Leave-one-out: the honest read on whether this generalises.
    preds = []
    for i in range(len(names)):
        Xi = X[:i] + X[i + 1:]
        yi = y[:i] + y[i + 1:]
        preds.append(predict(ridge(Xi, yi), X[i]))
    rho = spearman(preds, y)
    mae = sum(abs(preds[i] - y[i]) for i in range(len(y))) / len(y)

    w = ridge(X, y)
    return w, rho, mae, names, X, y, preds


def show_model(w, rho, mae):
    print("=" * 62)
    print("MODEL  — ridge on log10(median views), n={}".format(len(TRIED)))
    print("=" * 62)
    print("\nLeave-one-out validation:")
    print("  Spearman rank correlation : {:+.2f}".format(rho))
    print("  Median abs error          : {:.2f} log10 ({:.1f}x)".format(mae, 10 ** mae))
    if rho >= 0.6:
        verdict = "usable for ranking"
    elif rho >= 0.4:
        verdict = "weak but directional - treat output as a shortlist, not gospel"
    else:
        verdict = "NOT predictive - do not trust the rankings below"
    print("  Verdict                   : {}".format(verdict))

    print("\nFeature weights (per +1 point, in log10 views):")
    for i, f in enumerate(FEATURES):
        bar = "#" * int(abs(w[i + 1]) * 25)
        print("  {:<12}{:+.3f}  {}".format(f, w[i + 1], bar))


def show_residuals(names, y, preds):
    print("\nBiggest misses (where the model is wrong, and why that matters):")
    res = sorted(range(len(names)), key=lambda i: abs(preds[i] - y[i]), reverse=True)[:5]
    for i in res:
        direction = "over" if preds[i] > y[i] else "under"
        print("  {:<20} actual {:>9,}  predicted {:>9,}  ({}-predicted)".format(
            names[i], int(10 ** y[i]), int(10 ** preds[i]), direction))


def recommend(w, top=12):
    scored = []
    for name, feats in CANDIDATES.items():
        p = predict(w, feats)
        scored.append((10 ** p, name, feats))
    scored.sort(reverse=True)

    print("\n" + "=" * 62)
    print("RECOMMENDED NEXT VENUES  (untried)")
    print("=" * 62)
    print("\n  {:<26}{:>12}  {:<6}{}".format("venue", "predicted", "tier", "driver"))
    print("  " + "-" * 58)
    for pred, name, feats in scored[:top]:
        d = dict(zip(FEATURES, feats))
        driver = max(("stakes", "physical", "esw", "social", "skill"),
                     key=lambda k: d[k] * w[FEATURES.index(k) + 1])
        print("  {:<26}{:>12,}  {:<6}{}".format(name, int(pred), tier(pred), driver))

    print("\n  Proven repeat: parkour (2.5M, then 219k and 74k on repeats).")
    print("  Repeats hold up on winners - keep it in rotation alongside these.")


def evaluate(query, w):
    name, feats, was_tried, estimated = lookup(query)
    hit = None if estimated else (name, feats, was_tried)

    print("=" * 62)
    print('GENRE CHECK: "{}"'.format(query))
    print("=" * 62)

    if not hit:
        print("\n  Not in the library. Score it on these 0-3 and re-run with")
        print("  --features s,p,e,so,sk,su,sat :\n")
        for f in FEATURES:
            print("    {}".format(f))
        print("\n  (In the built tool Claude scores these from the venue name")
        print("   automatically - this script is the offline version.)")
        return

    name, feats, was_tried = hit
    pred = 10 ** predict(w, feats)
    print("\n  Matched   : {}".format(name))
    print("  Features  : {}".format(", ".join(
        "{}={}".format(f, v) for f, v in zip(FEATURES, feats))))
    print("  Predicted : {:,} views  (tier {})".format(int(pred), tier(pred)))

    if was_tried:
        actual = TRIED[name][1]
        print("  ACTUAL    : {:,} views  (tier {}) - he has already done this".format(
            actual, tier(actual)))
        if actual < 6000:
            print("\n  >> Already tried and it underperformed. Not worth repeating.")
        else:
            print("\n  >> Already tried and it worked. Repeats hold up on winners.")
    else:
        d = dict(zip(FEATURES, feats))
        if d["saturation"] >= 3:
            print("\n  >> Warning: heavily saturated in short-form. Expect a discount.")
        if d["stakes"] <= 1 and d["physical"] <= 1:
            print("\n  >> Warning: low stakes and low physicality. Nothing can go")
            print("     catastrophically wrong here, so the clips will top out mild.")
        print("\n  Verdict: {}".format(
            "worth doing" if pred >= 15000 else
            "marginal" if pred >= 6000 else "skip it"))


# --- Feature estimation for venues not in the library -----------------------
# Crude keyword scoring so the model can rate ANY scenario a user types.
# Clearly worse than a hand-scored entry; results are labelled "estimated".
KEYWORDS = {
    "esw": ["water", "swim", "surf", "dive", "boat", "jet", "wake", "canoe", "kayak",
            "ski", "snow", "sled", "slide", "jump", "height", "cliff", "bungee", "zip",
            "fly", "race", "speed", "kart", "bike", "motor", "quad", "rapid"],
    "skill": ["ski", "surf", "skate", "board", "bike", "climb", "golf", "tennis",
              "box", "martial", "dance", "gymnast", "juggl", "trick", "parkour",
              "ride", "shoot", "archery", "instrument", "cook"],
    "social": ["party", "pub", "bar", "club", "wedding", "festival", "crowd", "public",
               "restaurant", "date", "karaoke", "family", "friends", "night out"],
    "physical": ["jump", "fall", "run", "climb", "skate", "board", "wrestl", "box",
                 "tackle", "flip", "slip", "crash", "sport", "gym", "lift"],
    "stakes": ["cliff", "height", "fire", "knife", "traffic", "road", "danger",
               "extreme", "wild", "animal", "electric", "power tool", "roof"],
}
SATURATED = ["gym", "bowling", "mall", "prank", "gaming", "food", "makeup", "car",
             "dog", "cat", "baby", "school", "office", "football", "soccer",
             "basketball", "workout", "cooking", "shopping"]
HIGH_SUPPLY = ["ski", "snow", "surf", "skate", "bike", "football", "gym", "car",
               "dog", "wedding", "golf", "box", "fish", "swim", "dance", "run"]


def estimate_features(text):
    """Best-effort feature vector for an arbitrary scenario string."""
    t = text.lower()
    f = {k: 0 for k in FEATURES}
    for feat, words in KEYWORDS.items():
        hits = sum(1 for w in words if w in t)
        f[feat] = min(hits + (1 if hits else 0), 3)
    f["supply"] = 3 if any(w in t for w in HIGH_SUPPLY) else 2
    f["saturation"] = 3 if any(w in t for w in SATURATED) else 1
    if f["physical"] == 0 and f["skill"] > 0:
        f["physical"] = 2
    return [f[k] for k in FEATURES]


def lookup(query):
    """Resolve a scenario string. Returns (name, features, tried, estimated)."""
    q = query.lower().strip()

    def phrase_in(needle, haystack):
        return re.search(r"\b{}\b".format(re.escape(needle)), haystack) is not None

    matches = []
    for pool, tried in ((TRIED, True), (CANDIDATES, False)):
        for name in pool:
            feats = pool[name][0] if tried else pool[name]
            if q == name:
                matches.append((1000, name, feats, tried))
            elif phrase_in(name, q) or phrase_in(q, name):
                matches.append((len(name), name, feats, tried))
    matches.sort(reverse=True)
    if matches:
        _, name, feats, tried = matches[0]
        return name, feats, tried, False
    return query, estimate_features(query), False, True


def assess(query):
    """Full verdict for any scenario. Used by the web app."""
    w, rho, mae, *_ = fit_and_validate()
    name, feats, tried, estimated = lookup(query)
    pred = 10 ** predict(w, feats)
    d = dict(zip(FEATURES, feats))
    warnings = []
    if d["saturation"] >= 3:
        warnings.append("Heavily saturated in short-form — expect a discount.")
    if d["supply"] <= 1:
        warnings.append("Little footage likely available; sourcing will be hard.")
    if d["skill"] == 0 and d["physical"] <= 1:
        warnings.append("No visible skill to fail at — clips will top out mild.")
    actual = TRIED[name][1] if tried else None
    if tried:
        warnings.append(
            "Already done: {:,} views (tier {}). {}".format(
                actual, tier(actual),
                "Repeats hold up on winners." if actual >= 15000
                else "It underperformed — not worth repeating."))
    return {
        "query": query, "matched": name, "estimated": estimated,
        "features": d, "predicted": int(pred), "tier": tier(pred),
        "actual": actual, "warnings": warnings,
        "model_rho": round(rho, 2),
        "verdict": ("worth doing" if pred >= 15000
                    else "marginal" if pred >= 6000 else "skip it"),
    }


def main():
    w, rho, mae, names, X, y, preds = fit_and_validate()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        evaluate(" ".join(args), w)
    else:
        show_model(w, rho, mae)
        show_residuals(names, y, preds)
        recommend(w)


if __name__ == "__main__":
    main()
