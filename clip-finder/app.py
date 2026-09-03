#!/usr/bin/env python3
"""Clip Finder — local web UI.

Search any scenario, get candidate clips ranked, and one suggested pick.

Runs on the standard library only, so there is nothing to install:

    python app.py            then open http://localhost:8000

Needs YOUTUBE_API_KEY in clip-finder/.env (same key as fetch_catalogue.py).
It stays server-side and is never sent to the browser.

Quota: each new scenario costs ~200 units of the 10,000/day budget (two
search.list calls at 100 each, plus a videos.list at 1). Results are cached for
24h, so repeating a search is free.
"""
import hashlib
import hmac
import html
import http.cookies
import http.server
import json
import math
import os
import pathlib
import re
import secrets
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent


def load_env():
    """Push .env into the process environment.

    The Anthropic SDK resolves ANTHROPIC_API_KEY from the environment, not from
    our file, so it has to land in os.environ before any client is constructed.
    Real environment variables win over the file.
    """
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if value:
            os.environ.setdefault(name.strip(), value)


load_env()

sys.path.insert(0, str(ROOT / "scripts"))
import recommend_venue  # noqa: E402

try:                      # optional: the app still runs on heuristics without it
    import judge          # noqa: E402
except ImportError:
    judge = None

JUDGE_LIMIT = 8           # how many of the top clips Claude actually looks at

CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
API = "https://www.googleapis.com/youtube/v3"
PORT = 8000

# Query variants per scenario. More variants = better recall, more quota.
VARIANTS = ["{} fail funny", "{} gone wrong moment"]

# Strong comedic signal — something went physically wrong.
FAIL_WORDS = ["fail", "crash", "wipeout", "faceplant", "eject", "gone wrong",
              "falls off", "fell off", "wrecked", "disaster", "worst", "oops",
              "instant regret", "bad idea", "didn't end well", "went wrong"]
# Weaker but still positive.
GOOD_TITLE = ["funny", "hilarious", "wtf", "chaos", "panic", "scream", "lost it"]
# Skill showcase — impressive, not comedic. Wrong genre for a comedy channel.
SKILL_SHOWCASE = ["epic", "insane", "amazing", "awesome", "world record", "tricks",
                  "skills", "satisfying", "perfect", "pro ", "champion", "best of",
                  "how is this possible", "next level", "craziest", "stunt"]
BAD_TITLE = ["tutorial", "how to", "guide", "tips", "full episode", "podcast",
              "highlights", "documentary", "review", "explained", "training"]
WATERMARK_HINT = ["tiktok", "tik tok", "douyin", "kwai", "likee", "reels", "capcut"]

# Licensing agencies (they claim aggressively) and brand channels (wrong tone —
# polished promo, not amateur failure).
RIGHTS_RISK = ["viralhog", "jukin", "caters", "storyful", "barcroft", "newsflare",
               "rumble", "america's funniest", "afv", "red bull", "gopro",
               "daily mail", "ladbible", "unilad", "nbc", "espn", "sky ",
               "guinness world", "monster energy", "nitro circus"]


# --- Shared-passphrase gate -------------------------------------------------
# Unset APP_PASSPHRASE (the local default) leaves the app open. Set it on any
# deployment. SESSION_SECRET should also be set in production, otherwise it is
# regenerated on every boot and everyone is logged out by a restart.
PASSPHRASE = os.environ.get("APP_PASSPHRASE", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)
SESSION_DAYS = 30
COOKIE = "cf_session"

_attempts = {}                      # client ip -> (failures, window start)
_attempts_lock = threading.Lock()
MAX_ATTEMPTS, ATTEMPT_WINDOW = 8, 900


def make_token():
    """expiry.signature — stateless, so there is no session store to keep."""
    exp = str(int(time.time() + SESSION_DAYS * 86400))
    sig = hmac.new(SESSION_SECRET.encode(), exp.encode(), hashlib.sha256).hexdigest()
    return "{}.{}".format(exp, sig)


def valid_token(token):
    if not token or "." not in token:
        return False
    exp, _, sig = token.partition(".")
    expected = hmac.new(SESSION_SECRET.encode(), exp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        return int(exp) > time.time()
    except ValueError:
        return False


def client_ip(handler):
    fwd = handler.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() if fwd else handler.client_address[0]


def rate_limited(ip):
    with _attempts_lock:
        count, start = _attempts.get(ip, (0, time.time()))
        if time.time() - start > ATTEMPT_WINDOW:
            return False
        return count >= MAX_ATTEMPTS


def record_failure(ip):
    with _attempts_lock:
        count, start = _attempts.get(ip, (0, time.time()))
        if time.time() - start > ATTEMPT_WINDOW:
            count, start = 0, time.time()
        _attempts[ip] = (count + 1, start)


def is_authed(handler):
    if not PASSPHRASE:
        return True
    raw = handler.headers.get("Cookie", "")
    jar = http.cookies.SimpleCookie()
    try:
        jar.load(raw)
    except http.cookies.CookieError:
        return False
    morsel = jar.get(COOKIE)
    return bool(morsel) and valid_token(morsel.value)


# When true, keys in .env are ignored and every visitor must supply their own.
# Set this on any deployment that other people can reach, so nobody else can
# spend your quota or your API credits.
REQUIRE_USER_KEY = os.environ.get("REQUIRE_USER_KEY", "").lower() in ("1", "true", "yes")


def env_key(name):
    """Local convenience only — never consulted when REQUIRE_USER_KEY is set."""
    if REQUIRE_USER_KEY:
        return ""
    return os.environ.get(name, "")


def yt(endpoint, key, **params):
    params["key"] = key
    url = "{}/{}?{}".format(API, endpoint, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def iso_seconds(iso):
    if not iso.startswith("PT"):
        return 0
    total, num = 0, ""
    for ch in iso[2:]:
        if ch.isdigit():
            num += ch
        else:
            total += int(num or 0) * {"H": 3600, "M": 60, "S": 1}.get(ch, 0)
            num = ""
    return total


def decode_entities(clips):
    """YouTube returns HTML-escaped text ("Bangers &amp; Mash", "don&#39;t").

    Left alone it gets escaped a second time at render and shows as literal
    "&amp;". Decode once here so everything downstream holds real characters.
    """
    for c in clips:
        for field in ("title", "channel", "description"):
            if c.get(field):
                c[field] = html.unescape(c[field])
    return clips


def search_youtube(scenario, key):
    """Two search variants, merged and hydrated with stats. Cached 24h."""
    slug = re.sub(r"[^a-z0-9]+", "-", scenario.lower()).strip("-")[:60]
    cached = CACHE / "{}.json".format(slug)
    if cached.exists():
        age = datetime.now().timestamp() - cached.stat().st_mtime
        if age < 86400:
            return decode_entities(json.loads(cached.read_text(encoding="utf-8"))), 0

    found, units = {}, 0
    for pattern in VARIANTS:
        try:
            r = yt("search", key, part="snippet", q=pattern.format(scenario),
                   type="video", videoDuration="short", maxResults=25,
                   order="relevance", safeSearch="moderate")
            units += 100
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            if e.code in (400, 403):
                raise RuntimeError(
                    "YouTube rejected that key ({}). Check it's valid and that "
                    "YouTube Data API v3 is enabled for it.".format(e.code))
            raise RuntimeError("YouTube API {}: {}".format(e.code, body))
        for it in r.get("items", []):
            vid = it["id"]["videoId"]
            found[vid] = {
                "video_id": vid,
                "title": it["snippet"]["title"],
                "channel": it["snippet"]["channelTitle"],
                "published_at": it["snippet"]["publishedAt"],
                "description": it["snippet"].get("description", "")[:300],
                "thumb": it["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
            }

    ids = list(found)
    for i in range(0, len(ids), 50):
        r = yt("videos", key, part="statistics,contentDetails",
               id=",".join(ids[i:i + 50]))
        units += 1
        for it in r.get("items", []):
            v = found[it["id"]]
            st = it.get("statistics", {})
            v["views"] = int(st.get("viewCount", 0) or 0)
            v["likes"] = int(st.get("likeCount", 0) or 0)
            v["duration_s"] = iso_seconds(it["contentDetails"].get("duration", ""))

    clips = decode_entities([v for v in found.values() if "views" in v])
    cached.write_text(json.dumps(clips, ensure_ascii=False), encoding="utf-8")
    return clips, units


def score_clip(v):
    """Heuristic ranking. Stands in for the Claude taste judge until that lands.

    Deliberately transparent — every clip carries the reasons for its score so
    a bad ranking is debuggable rather than mysterious.
    """
    reasons, flags, s = [], [], 0.0
    text = (v["title"] + " " + v.get("description", "")).lower()
    chan = v.get("channel", "").lower()

    # Views are scored on a BAND, not a curve. A 60M-view Red Bull clip is worse
    # than a 100k amateur fail: the audience has already seen it, and the rights
    # holder will claim it. The useful zone is the mid-tail.
    views = v.get("views", 0)
    if views > 10_000_000:
        s += 0.5
        flags.append("everyone has seen this ({:,})".format(views))
    elif views > 3_000_000:
        s += 2.0
        reasons.append("{:,} views — widely seen".format(views))
    elif views >= 20_000:
        s += 3.2
        reasons.append("{:,} views — mid-tail, ideal".format(views))
    elif views >= 3_000:
        s += 2.0
        reasons.append("{:,} views — obscure but usable".format(views))
    else:
        s += 0.3
        flags.append("too obscure ({:,} views)".format(views))

    # Licensing agencies and brand channels: rights risk and wrong tone.
    if any(b in chan for b in RIGHTS_RISK):
        s -= 2.5
        flags.append("rights risk: {}".format(v.get("channel", "")))

    try:
        pub = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        age_days = max((datetime.now(timezone.utc) - pub).days, 1)
        if age_days < 120:
            s += 0.4
            reasons.append("recent")
    except (ValueError, KeyError):
        pass

    d = v.get("duration_s", 0)
    if 3 <= d <= 20:
        s += 1.8
        reasons.append("{}s — drops straight in".format(d))
    elif d <= 45:
        s += 0.9
        reasons.append("{}s — one trim needed".format(d))
    elif d <= 180:
        s += 0.2
        flags.append("{}s — heavy trimming".format(d))
    else:
        s -= 1.0
        flags.append("too long ({}s)".format(d))

    if v.get("views"):
        ratio = v.get("likes", 0) / v["views"]
        if ratio > 0.04:
            s += 1.0
            reasons.append("strong like ratio ({:.1%})".format(ratio))

    # Failure is the whole genre, so weight it heavily.
    fails = [w for w in FAIL_WORDS if w in text]
    if fails:
        s += 1.4 * min(len(fails), 3)
        reasons.append("failure signal: " + ", ".join(fails[:3]))
    hits = [w for w in GOOD_TITLE if w in text]
    if hits:
        s += 0.5 * len(hits)
        reasons.append("signals: " + ", ".join(hits[:3]))

    # Impressive != funny. A trick showcase is the wrong genre for this channel.
    showy = [w for w in SKILL_SHOWCASE if w in text]
    if showy and not fails:
        s -= 1.3 * min(len(showy), 3)
        flags.append("skill showcase, not comedy: " + ", ".join(showy[:2]))

    bad = [w for w in BAD_TITLE if w in text]
    if bad:
        s -= 1.2 * len(bad)
        flags.append("not clip-shaped: " + ", ".join(bad[:2]))

    marks = [w for w in WATERMARK_HINT if w in text]
    if marks:
        s -= 2.0
        flags.append("likely watermarked ({})".format(marks[0]))
    if re.search(r"@\w{3,}", v["title"]):
        s -= 1.0
        flags.append("handle in title — probable repost")

    v["score"] = round(s, 2)
    v["reasons"] = reasons
    v["flags"] = flags
    v["url"] = "https://www.youtube.com/watch?v=" + v["video_id"]
    return v


def find(scenario, yt_key, anthropic_key):
    verdict = recommend_venue.assess(scenario)
    if not yt_key:
        return {"scenario": scenario, "verdict": verdict, "clips": [],
                "suggested": None, "quota": 0, "needs_key": True,
                "error": "Add your own YouTube Data API key to search."}

    clips, units = search_youtube(scenario, yt_key)
    for c in clips:
        score_clip(c)
    clips.sort(key=lambda c: c["score"], reverse=True)

    # Cap two per channel so one uploader cannot dominate the pack.
    seen, spread = {}, []
    for c in clips:
        n = seen.get(c["channel"], 0)
        if n < 2:
            seen[c["channel"]] = n + 1
            spread.append(c)
    spread = spread[:24]

    # The heuristic is now only a prefilter. Claude looks at the frames and
    # decides. Judging all 24 when the heuristic already sorts out the obvious
    # rubbish is wasted spend, not better taste.
    judge_note = None
    if judge is None:
        judge_note = ("Claude judge not installed (pip install anthropic) — "
                      "heuristic ranking only.")
    elif not anthropic_key:
        judge_note = ("No Anthropic key supplied — heuristic ranking only. Add "
                      "one to have Claude look at the frames.")
    else:
        spread, err = judge.judge_batch(spread, scenario, limit=JUDGE_LIMIT,
                                        api_key=anthropic_key)
        if err:
            judge_note = ("Claude judge unavailable — showing heuristic ranking "
                          "only. {}".format(err[:160]))

    return {"scenario": scenario, "verdict": verdict, "quota": units,
            "clips": spread, "suggested": pick_suggested(spread),
            "judge_note": judge_note, "error": None}


def pick_suggested(clips):
    """Claude's verdict outranks the heuristic wherever a judgement exists."""
    judged = [c for c in clips if c.get("judgement")]
    if judged:
        good = [c for c in judged
                if c["judgement"]["verdict"] == "accept"
                and not c["judgement"]["watermark_visible"]
                and c["judgement"]["genre_match"]]
        if good:
            return max(good, key=lambda c: c["judgement"]["funny_score"])
        # Nothing cleared the bar — say so with the best of a bad set rather
        # than silently promoting a rejected clip.
        best = max(judged, key=lambda c: c["judgement"]["funny_score"])
        best["weak_pick"] = True
        return best
    clean = [c for c in clips if not any("watermark" in f or "repost" in f
                                         for f in c["flags"])]
    return (clean or clips or [None])[0]


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _login_page(self, message=""):
        page = (ROOT / "web" / "login.html").read_text(encoding="utf-8")
        return self._send(200, page.replace("<!--MSG-->", message),
                          "text/html; charset=utf-8")

    def do_POST(self):
        parts = urllib.parse.urlparse(self.path)
        if parts.path != "/login":
            return self._send(404, "not found", "text/plain")

        ip = client_ip(self)
        if rate_limited(ip):
            return self._login_page(
                "Too many attempts. Wait 15 minutes and try again.")

        length = min(int(self.headers.get("Content-Length") or 0), 4096)
        body = self.rfile.read(length).decode("utf-8", "replace")
        supplied = urllib.parse.parse_qs(body).get("passphrase", [""])[0]

        # compare_digest, not ==, so a wrong guess can't be narrowed down by
        # timing how long the comparison took.
        if not hmac.compare_digest(supplied, PASSPHRASE):
            record_failure(ip)
            return self._login_page("That passphrase isn't right.")

        token = make_token()
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie",
                         "{}={}; Path=/; HttpOnly; SameSite=Lax; Max-Age={}{}".format(
                             COOKIE, token, SESSION_DAYS * 86400, secure))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parts = urllib.parse.urlparse(self.path)

        if parts.path == "/logout":
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie",
                             "{}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0".format(COOKIE))
            self.send_header("Content-Length", "0")
            return self.end_headers()

        if not is_authed(self):
            if parts.path.startswith("/api/"):
                return self._send(401, json.dumps({"error": "Not signed in."}),
                                  "application/json")
            return self._login_page()

        if parts.path == "/":
            page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
            return self._send(200, page, "text/html; charset=utf-8")
        if parts.path == "/demo":
            page = (ROOT / "web" / "demo.html").read_text(encoding="utf-8")
            return self._send(200, page, "text/html; charset=utf-8")
        if parts.path == "/api/config":
            return self._send(200, json.dumps({
                "require_user_key": REQUIRE_USER_KEY,
                "server_has_youtube": bool(env_key("YOUTUBE_API_KEY")),
                "server_has_anthropic": bool(env_key("ANTHROPIC_API_KEY")),
            }), "application/json")

        if parts.path == "/api/search":
            q = urllib.parse.parse_qs(parts.query).get("q", [""])[0].strip()
            if not q:
                return self._send(400, json.dumps({"error": "empty query"}),
                                  "application/json")
            # Keys arrive as headers, never as query parameters — a query
            # string lands in browser history, referrers and access logs.
            # They are used for this request and never written anywhere.
            yt_key = self.headers.get("X-Youtube-Key", "").strip() \
                or env_key("YOUTUBE_API_KEY")
            an_key = self.headers.get("X-Anthropic-Key", "").strip() \
                or env_key("ANTHROPIC_API_KEY")
            try:
                result = find(q, yt_key, an_key)
            except Exception as exc:                     # surface it in the UI
                result = {"scenario": q, "error": str(exc), "clips": [],
                          "suggested": None, "verdict": None, "quota": 0}
            return self._send(200, json.dumps(result, ensure_ascii=False),
                              "application/json; charset=utf-8")
        self._send(404, "not found", "text/plain")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    # Hosts set PORT; binding 0.0.0.0 is required there and harmless locally
    # only because REQUIRE_USER_KEY is what actually protects the keys.
    PORT = int(os.environ.get("PORT", PORT))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"

    if REQUIRE_USER_KEY:
        print("REQUIRE_USER_KEY is on — .env keys ignored, every visitor "
              "supplies their own.\n")
    elif not env_key("YOUTUBE_API_KEY"):
        print("WARNING: no YOUTUBE_API_KEY found — scenario scoring will work, "
              "clip search will not.\n")

    print("Clip Finder running at http://localhost:{}".format(PORT))
    print("Ctrl+C to stop.\n")
    with Server((host, PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
