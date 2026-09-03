#!/usr/bin/env python3
"""Claude taste judge — actually looks at the clip.

YouTube exposes three frames sampled through every video plus the poster frame:

    https://i.ytimg.com/vi/<id>/hqdefault.jpg   poster
    https://i.ytimg.com/vi/<id>/hq1.jpg         ~25% through
    https://i.ytimg.com/vi/<id>/hq2.jpg         ~50%
    https://i.ytimg.com/vi/<id>/hq3.jpg         ~75%

The Messages API accepts image blocks by URL, so we hand those four straight to
Claude — no yt-dlp, no ffmpeg, no downloading. Four stills is genuinely less than
watching: it can see what a clip IS and whether a watermark is burned in, but it
cannot see timing or motion. Frame-accurate moment-finding still needs real video.

`taste/sango_taste.md` is loaded as the system prompt, so the rubric is the
product and this file is only plumbing. It is cached across calls.
"""
import json
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel, Field

ROOT = pathlib.Path(__file__).resolve().parent.parent
JUDGEMENTS = ROOT / "data" / "judgements"
JUDGEMENTS.mkdir(parents=True, exist_ok=True)
MODEL = "claude-opus-5"

HUMOUR = Literal["physical_incompetence", "confident_setup_failure",
                 "unexpected_competence", "collateral_chaos", "deadpan_reaction",
                 "elder_or_child", "equipment_malfunction", "social_chaos"]
RISK = Literal["possible_real_injury", "cruelty", "non_consenting_subject",
               "minor_present", "sexual_content", "looks_staged",
               "demonetisation_risk", "brand_or_pro_content"]


class ClipJudgement(BaseModel):
    """What Claude returns after looking at the four frames."""
    genre_match: bool = Field(description="Do the frames actually show the searched scenario?")
    genre_evidence: str = Field(description="The specific thing you saw that proves it, or what you saw instead.")

    watermark_visible: bool = Field(description="Is a platform logo or @handle burned into any frame?")
    watermark_detail: str = Field(description="Which platform and where, or 'none seen in these frames'.")

    slot: Literal["first_day", "last_day", "either", "none"]
    funny_score: float = Field(ge=0, le=10, description="Funny for THIS channel, per the rubric. Not funny in general.")
    humour_type: List[HUMOUR]
    why_funny: str = Field(max_length=200)

    sound_off_legible: bool = Field(description="Does the joke read with no audio?")
    crop_safe: bool = Field(description="Does it survive a 9:16 centre crop of a 16:9 frame?")
    escalation_severity: float = Field(ge=0, le=10, description="For last_day ordering. How big is the disaster.")

    risk_flags: List[RISK]
    verdict: Literal["accept", "manual_review", "reject"]
    reason: str = Field(max_length=300, description="One sentence for the verdict.")


INSTRUCTIONS = """You are the taste judge for the clip finder described above.

You are shown FOUR STILL FRAMES sampled through a short video (poster, ~25%,
~50%, ~75%) plus its metadata. You are not watching it — you cannot see motion
or timing. Judge what you can actually see and say so when frames are
inconclusive; guessing is worse than a low confidence score.

Apply the rubric above. Two things matter most:

1. `funny_score` means funny FOR THIS CHANNEL — physical, language-independent,
   legible with sound off. An impressive trick is not funny. A professionally
   produced brand clip is not funny. Score those low and flag
   `brand_or_pro_content`.
2. `watermark_visible` — look at the corners of every frame for TikTok,
   Instagram Reels, Snapchat, Kwai, Likee or CapCut marks and for @handles
   burned into the picture. A watermark is a hard reject: he cross-posts, and
   reuploads carrying a competitor's mark get suppressed.

Reject outright on `possible_real_injury`. If someone might genuinely be hurt,
it does not matter how funny it looks."""


def frame_urls(video_id):
    return ["https://i.ytimg.com/vi/{}/{}.jpg".format(video_id, n)
            for n in ("hqdefault", "hq1", "hq2", "hq3")]


def load_rubric():
    return (ROOT / "taste" / "sango_taste.md").read_text(encoding="utf-8")


def judge_clip(client, clip, scenario, use_cache=True):
    """Judge one clip. Cached on disk by video id — re-searches cost nothing."""
    cached = JUDGEMENTS / "{}.json".format(clip["video_id"])
    if use_cache and cached.exists():
        return ClipJudgement(**json.loads(cached.read_text(encoding="utf-8")))

    content = [{"type": "image", "source": {"type": "url", "url": u}}
               for u in frame_urls(clip["video_id"])]
    content.append({"type": "text", "text":
        "Scenario searched: {}\n\nTitle: {}\nChannel: {}\nViews: {:,}\n"
        "Duration: {}s\n\nThe four images above are frames from this video, in "
        "order.".format(scenario, clip["title"], clip.get("channel", "?"),
                        clip.get("views", 0), clip.get("duration_s", 0))})

    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=[
            {"type": "text", "text": load_rubric(),
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": INSTRUCTIONS},
        ],
        messages=[{"role": "user", "content": content}],
        output_format=ClipJudgement,
    )
    result = response.parsed_output
    cached.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def judge_batch(clips, scenario, limit=8, workers=6, api_key=None):
    """Judge the top `limit` clips. Returns (judged_clips, error_or_None).

    The heuristic score is the prefilter; Claude is the judge. Judging 24 clips
    per search when the heuristic already sorts out the obvious rubbish is
    wasted spend, not better taste.

    Judgements are independent, so they run concurrently — sequentially this is
    the better part of a minute of dead UI.
    """
    try:
        client = (anthropic.Anthropic(api_key=api_key) if api_key
                  else anthropic.Anthropic())
    except Exception as exc:
        return clips, "Anthropic client init failed: {}".format(exc)

    targets = clips[:limit]
    if not targets:
        return clips, None

    errors = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(judge_clip, client, c, scenario): c for c in targets}
        for fut in as_completed(futures):
            clip = futures[fut]
            try:
                clip["judgement"] = fut.result().model_dump()
                clip["judged"] = True
            except Exception as exc:
                clip["judge_error"] = str(exc)[:200]
                errors.append(str(exc))

    # Every call failing means a config problem (no key, bad model), not a
    # per-clip issue — surface that rather than showing a silently unjudged list.
    if len(errors) == len(targets):
        return clips, errors[0][:300]
    return clips, None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    scenario = sys.argv[1] if len(sys.argv) > 1 else "wakeboarding"
    cache_file = ROOT / "data" / "cache" / "{}.json".format(scenario)
    if not cache_file.exists():
        sys.exit("No cached search for '{}'. Run a search in the app first.".format(scenario))

    clips = json.loads(cache_file.read_text(encoding="utf-8"))
    clips = [c for c in clips if c.get("views")][:3]
    client = anthropic.Anthropic()
    for c in clips:
        print("\n" + "=" * 60)
        print(c["title"][:70])
        j = judge_clip(client, c, scenario)
        print("  genre_match     ", j.genre_match, "-", j.genre_evidence[:70])
        print("  watermark       ", j.watermark_visible, "-", j.watermark_detail[:60])
        print("  funny_score     ", j.funny_score, j.humour_type)
        print("  why             ", j.why_funny[:90])
        print("  slot / severity ", j.slot, "/", j.escalation_severity)
        print("  sound-off/crop  ", j.sound_off_legible, "/", j.crop_safe)
        print("  risks           ", j.risk_flags)
        print("  VERDICT         ", j.verdict.upper(), "-", j.reason[:90])
