# Sango Taste Rubric — v0.2

Rewritten against real catalogue data (493 uploads, pulled 2026-09-02).
v0.1 was inference. Claims below are now marked:

  (DATA)    — measured from the catalogue
  (ASSUMED) — still inference, still needs testing

## The channel context that drives everything

(DATA) Median views by year:

    2021    31 uploads    11,613
    2022   140 uploads    44,846
    2023    46 uploads    80,520   <- peak
    2024    16 uploads    15,115
    2025    37 uploads     7,912
    2026   223 uploads     4,538   <- 18x below peak, on 5x the volume

He is posting more than ever and reaching fewer people than ever. 2.2% of the
catalogue has cleared 1M views, and every one of those is from 2021-22.

This reframes the tool. It is not "help him make more videos" — volume is not
the constraint, he shipped ~20 uploads in the last week of August alone. It is
**raise the hit rate**, because at 223 uploads a year the sourcing effort is
already enormous and the return has collapsed.

## The format: first & last day at [venue]

(DATA) All 41 of these are from 2026-06-28 onward. This is his current active
format, and within 2026 it is the only one that works:

    first_last_day    41 uploads   median 10,073   2.2x baseline
    other            156 uploads   median  4,166   0.9x
    who_won            2 uploads   median  2,972   0.7x
    reacting_with      8 uploads   median  2,214   0.5x
    oh_no             15 uploads   median  1,619   0.4x

All six 2026 uploads above 50k views are this format. Both above 100k are too.
Nothing else on the channel is currently producing hits.

Note on `who_won`: it has the channel's two biggest videos ever (47M, 23M) but
both are 2021-22. Retried twice in May 2026 for 4,788 and 1,157 views. The
format is not the asset — the 2021-22 channel was. Do not chase it.

## Venue selection is the single biggest lever

(DATA) Same format, same creator, same nine weeks, same ~65s length:

    parkour        2,495,039 views
    gyms               1,778 views

A **1,400x spread** driven by nothing but venue and clip choice. This is the
whole argument for the tool. Full tiering in `genres/_backlog.md`.

(DATA) Selection rule, fitted over all 30 venues in `scripts/recommend_venue.py`:
**is there a lot of footage of this, in a genre short-form has not already
exhausted, where you can see someone failing at a real skill?**

    saturation  -0.33   <- biggest single factor, negative
    supply      +0.29
    skill       +0.14
    social      +0.09
    stakes      -0.02   <- no effect

An earlier draft of this file claimed the rule was "can something go
catastrophically wrong". That was generalised from parkour alone and the data
does not support it: bridge jumping has maximum stakes and did 4,401 views.
Saturation is why gym and bowling died — those genres are exhausted, not unfunny.

Repeat winners, retire losers. Bowling was tried three times (23.7k, 3.8k, 2.1k),
declining every time.

(DATA) The venue model explains the floor, not the ceiling — it under-predicts
parkour by 10x and its leave-one-out Spearman is only +0.43. Venue choice avoids
duds; **clip quality is what makes a hit.** That is where this tool earns out.

## Pack shape

(DATA) first_last_day uploads run **60-86s, median 66s** — much longer than the
21s channel-wide median, because this is the one montage format.

At ~5s a clip after a title card, that is **11-14 clips per pack**, not the 6-10
v0.1 assumed. Sourcing load is roughly 500 clips per 40 uploads.

Two-act structure (ASSUMED — from the title, not yet verified frame by frame):

    FIRST DAY  naive, hopeful, mildly incompetent. Things going OK.
    LAST DAY   escalation, chaos, damage, ejection.

Every clip gets `slot: first_day | last_day | either | none`. Ranking by raw
funniness alone yields all-chaos packs and kills the setup. Target ~40/60,
last_day ordered by escalating severity, biggest last. A pack that cannot fill
both acts is invalid.

## Pacing

(DATA) ~66s across 11-14 clips means each clip averages under 5 seconds.

- Land on the punch within 0.5-1.0s. The title card does the setup; the clip
  must not.
- 3-6s total. Anything needing more context than that is out.
- Legible with sound off.
- Crop-safe under a 9:16 centre crop.

## Humour that lands (ASSUMED)

Derived from the Tier A/B venues, not yet from frame-level review:

- Spectacular physical failure with real stakes and zero injury
- Confident setup into instant disaster (the "watch this" beat)
- Unexpected competence from someone who looks hopeless
- Collateral chaos — one mistake taking out a bystander or the equipment
- Deadpan or delayed reactions
- Water, height and speed all raise the ceiling; indoor and static lower it

## Automatic rejects

- Real injury. Blood, awkward limb angles, head impacts, anyone not getting up.
  Hard line — the Tier A venues (parkour, bridge jumping) make this a live risk,
  not a theoretical one.
- Cruelty, humiliation of someone not in on it, fights
- Sexual content, nudity, anything demonetising
- Slurs or profanity in the punch beat
- Identifiable people who clearly did not consent to being filmed
- Minors, unless unambiguously wholesome
- Visible platform watermark (see below)
- Staged content that reads as staged (ASSUMED)

## Watermarks are a distribution requirement

He cross-posts to TikTok (8.2M) and Snap (612k). A reupload carrying a
competitor's watermark gets algorithmically suppressed. This is reach, not
polish.

## Audience (ASSUMED)

26, from Kingston, England. UK venue vocabulary reads correctly (the pub,
McDonalds, Disney Land) but the 8.2M TikTok tail is global — so the humour has
to be physical and language-independent. Verbal punchlines are out.

## Feedback loop

Every approve/reject in the review UI appends to `taste/decisions.jsonl` with the
clip's feature vector. Regenerate this file every 100 decisions and bump the
version. The remaining (ASSUMED) tags are the backlog.
