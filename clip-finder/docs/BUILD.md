# Clip Finder — build plan

A funnel with a taste model at the end. Search is the easy part; the value is in
everything that throws candidates away.

Decided: scout + human review board (nothing ships unapproved) · YouTube + Reddit
only (real APIs, in ToS, least watermarked) · taste rubric first, backtested
before any pipeline code.

## Stage 1 — Discovery

YouTube Data API v3 `search.list` + Reddit API, seeded from `genres/*.yaml`.

Quota is the hard ceiling: 10,000 units/day, `search` costs 100 → ~100 queries
per day total. Budget them per genre, cache every response, and run discovery on
a schedule rather than on demand.

Reddit earns its place by giving virality for free (upvote velocity) and serving
clean `v.redd.it` files. Cross-posting is the strongest signal in the system: the
same clip on three subreddits is proven, not predicted.

Deliberately NOT scraping TikTok/Instagram — no real API, breaks constantly,
against ToS, and it's the watermarked pool we're trying to escape anyway.

## Stage 2 — Watermark & repost filter

Tiered, cheapest first, fail fast. This is a distribution requirement: he
cross-posts to TikTok, and reuploads carrying a competitor watermark get
suppressed.

1. Shape check — 9:16 padded into 16:9 with blurred side bars is a repost tell
   even with no logo. Edge/variance on the side bands. Nearly free.
2. Corner temporal variance — sample ~30 frames, find regions that DON'T change
   while the frame does. Catches logos with no template. TikTok's mark alternates
   between two corner anchors on a cycle, so sample across >=10s and check both.
3. OCR (PaddleOCR) on sampled frames — catches the @handle text and wordmarks.
4. Template match against a logo library (TikTok, Reels, Snap, Kwai, Likee,
   CapCut) for semi-transparent cases.

Add a trained classifier only if precision is bad after those four. It likely
won't be.

## Stage 3 — Scoring

Two independent signal classes, deliberately not blended into one number:

Extrinsic (viral-worthy): views-per-hour since publish, like ratio, comment
velocity, cross-post count.

Intrinsic (funny, and funny for HIM): keyframes + Whisper transcript + audio
energy spikes → Claude, with `taste/sango_taste.md` as the rubric, returning
`taste/clip_schema.json`.

Cost control: Haiku 4.5 triages ~500/day down to ~50; Opus/Sonnet 5 judges the
survivors. Keeps the bill trivial.

## Stage 4 — Moment finding

PySceneDetect + audio spikes propose windows; the model picks one.

Short-form pacing inverts the usual advice: the title card does the setup, so the
clip must NOT. Land on the punch within 0.5-1.0s, total 2-6s. Long-form reaction
pre-roll is wrong here.

Also enforce: legible with sound off, and crop-safe under a 9:16 centre crop.

## Stage 5 — Pack assembly

Not a ranked list — a two-act structure. Ranking by raw funniness produces eight
chaos clips and no first act, and the joke dies.

- Fill `first_day` and `last_day` to the genre config's target counts
- Order `last_day` by escalating severity, biggest last
- Dedupe on perceptual hash + audio fingerprint so the same fail from three
  reuploaders doesn't appear three times
- Cap clips per source channel
- A pack that can't fill both acts is INVALID — report the gap, don't ship it

Each clip carries source URL, creator handle, timestamp, watermark report, and a
riff line.

## Stage 6 — Review board

Keyboard-driven: J/K to skim, A/R to decide. 200 clips in ten minutes, because
his time is the bottleneck. Every decision appends to `taste/decisions.jsonl`
with the full feature vector — that log is what makes the rubric his instead of
mine.

## Rights hygiene

Reaction/commentary leans on transformative-use norms. Keep source URL + creator
handle on every clip for credit and permission DMs, and maintain a do-not-use
list for creators who have issued strikes.

## Order of work

Phase 0  Taste rubric, catalogue pull, venue model        DONE
Phase 1  Search UI: scenario -> ranked clips + a pick     DONE
Phase 2  Claude taste judge (looks at frames)             DONE (unverified, see below)
Phase 3  Real video frames + moment finder + download     <- next
Phase 4  Review board + decisions.jsonl feedback loop
Phase 5  Two-act pack assembly (first_day / last_day)

## The judge (scripts/judge.py)

YouTube exposes four frames per video with no download and no ffmpeg:

    hqdefault.jpg  poster        hq2.jpg  ~50%
    hq1.jpg        ~25%          hq3.jpg  ~75%

The Messages API takes image blocks by URL, so those go straight to
`claude-opus-5` with `taste/sango_taste.md` as a cached system prompt and a
Pydantic schema via `messages.parse()`. The rubric IS the judge; judge.py is
plumbing.

What this buys over the heuristic:

- **Watermark detection that actually looks.** The model checks frame corners
  for TikTok / Reels / Snap / Kwai / CapCut marks and burned-in @handles. Not a
  full CV filter - a watermark absent from all four sampled frames is missed -
  but far better than matching on titles.
- **Genre verification with evidence.** `genre_match` + `genre_evidence` forces
  it to name what it saw, so "wakeboarding" cannot quietly return jet skis.
- **Brand and skill-showcase rejection by sight**, not by channel blocklist.
- **Slot assignment** (first_day / last_day) for two-act pack assembly.

### The honest limit

Four stills is not watching. It can tell what a clip IS; it cannot see timing,
motion, or where the punch lands. Frame-accurate in/out points need real video
(yt-dlp + ffmpeg, neither installed here) - that is Phase 3.

### Cost and caching

8 clips judged per search (heuristic picks the 8; judging all 24 is waste, not
taste). Roughly $0.02 a clip, so ~$0.15 a search, falling after the first call
as the rubric cache warms. Judgements cache to `data/judgements/<video_id>.json`
so a repeat search costs nothing. Calls run concurrently - sequentially this is
a minute of dead UI.

Without ANTHROPIC_API_KEY the app falls back to heuristic ranking and says so in
a banner rather than failing.

### What runs today

    python app.py        ->  http://localhost:8000

Type any scenario. Returns a tier verdict from the venue model plus ranked
YouTube candidates with one suggested pick. Standard library only; needs
YOUTUBE_API_KEY in .env. ~200 quota units per new scenario, cached 24h.

### Scoring, as built

The heuristic in `score_clip()` is a placeholder for the Claude judge, but it
already encodes three findings that the naive version got wrong:

1. **Views are scored on a band, not a curve.** A 60M-view Red Bull clip is
   worse than a 100k amateur fail — the audience has seen it and the rights
   holder will claim it. Peak reward sits at 20k-3M.
2. **Licensing agencies and brand channels are penalised** (ViralHog, Jukin,
   Caters, Red Bull, GoPro, Daily Mail...). Claim risk and wrong tone.
3. **Skill showcase is not comedy.** "Epic tricks", "world record", "craziest
   stunt" score negative unless a failure word also appears. Impressive and
   funny are different genres, and only one of them is his.

Every clip carries its reasons and flags so a bad ranking is debuggable.

Phase 0 is the de-risker. Run the rubric against clips he ALREADY used, mixed
with decoys, and check it ranks the real ones top. If it can't retrodict his
published videos it won't predict his next one — and that's a cheap thing to
learn before building any CV.

## Stack

Python. yt-dlp, ffmpeg, OpenCV, PaddleOCR, faster-whisper, Claude API.
SQLite + a worker loop — skip Celery/Redis, the scale doesn't justify it.
FastAPI + HTMX for the review board.
