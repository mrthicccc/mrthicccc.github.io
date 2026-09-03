# Venue backlog — ranked on evidence

Source: 41 `first & last day` uploads, 2026-06-28 to 2026-09-02.
2026 channel baseline median = **4,538 views**. All multiples below are against
that baseline, so they are era-controlled.

## Tier A — proven, repeat it

| Venue | Views | Note |
|---|---:|---|
| parkour | **2,495,039** / 219,598 / 74,324 | 550x baseline. His only 2026 hit. Repeated twice and both repeats still beat baseline hard. |

Parkour is not a fluke and not a one-off: three uploads, all three above baseline,
two of them far above. This is the shape to look for.

## Tier B — above baseline, worth more attempts

| Venue | Views | vs base |
|---|---:|---:|
| fishing | 67,722 / 19,277 | 15x / 4x |
| the pub | 57,389 | 13x |
| skateboarding | 56,927 / 4,782 | 13x / 1x |
| not being on land (boat) | 28,430 | 6x |
| pub/bar | 25,080 | 6x |
| Disney Land | 24,151 / 4,593 | 5x / 1x |
| McDonalds | 21,621 | 5x |
| farming | 17,831 | 4x |

## Tier C — around baseline, low priority

hiking (14.7k) · house parties (14.2k) · driving instructor (13.8k) · park (13.0k) ·
Spider-Man (13.0k) · shopping in public (12.1k / 3.9k) · arcade (11.2k) ·
baby sitting (10.1k / 8.6k) · zoo (9.6k) · football (9.3k) · restaurants (9.0k)

## Tier D — tried, did not work, stop

| Venue | Views | Note |
|---|---:|---|
| bowling | 23,744 → 3,812 → 2,051 | **Three attempts, each worse than the last.** |
| Halloween | 6,665 | |
| barbers | 5,866 | |
| birthday parties | 5,415 | |
| bridge jumping | 4,401 | Surprising miss given Tier A pattern |
| traffic | 4,345 | |
| public transport | 3,440 | |
| the mall | 2,792 | |
| gym / gyms | 2,760 / 1,778 | Worst of all 41 |
| construction | 2,293 | |
| housekeeper | 7,141 | |

## The pattern

SUPERSEDED — an earlier version of this file claimed the rule was "can something
go catastrophically wrong here". Fitting a model over all 30 venues
(`scripts/recommend_venue.py`) shows that is false. Stakes carry a weight of
-0.02, i.e. nothing. Bridge jumping has maximum stakes and did 4,401 views;
construction did 2,293. The pub has no stakes at all and did 41,234.

The rule that actually fits:

| Feature | Weight | Reading |
|---|---:|---|
| saturation | **-0.33** | Being done-to-death is the single biggest killer |
| supply | **+0.29** | Footage has to exist in volume to find good clips |
| skill | +0.14 | Visible expertise to fail at helps |
| social | +0.09 | |
| height/speed/water | +0.06 | |
| physical | +0.03 | |
| stakes | -0.02 | No effect |

**Selection rule: is there a lot of footage of this, in a genre short-form has
not already exhausted, where you can see someone failing at a real skill?**

That explains the two worst venues directly — gym and bowling are the most
saturated genres in short-form comedy. It is not that nothing funny happens in a
gym; it is that every version of the joke has already been posted.

## What the model cannot do

It under-predicts parkour by 10x (predicts 21k, actual 220k) and over-predicts
construction, bridge jumping and gym. Leave-one-out Spearman is +0.43 — weak.

So: **venue choice sets the floor, clip quality creates the hit.** Use this
tiering to avoid duds, not to pick winners. The upside is in clip selection.

## Repeat rule

Repeats track the original. parkour...again did 74k off a 2.5M original;
bowling...again did 3.8k off a 23.7k original that was already fading.

**Repeat winners, retire losers.** Bowling was attempted three times and declined
each time — that is three uploads spent on a venue the data had already rejected
after the second.
