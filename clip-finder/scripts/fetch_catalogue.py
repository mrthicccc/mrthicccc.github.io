#!/usr/bin/env python3
"""Pull a channel's full upload catalogue from the YouTube Data API v3.

Quota cost for a ~1000-video channel is about 41 units of the 10,000/day budget:
  channels.list        1 unit   (resolve handle -> uploads playlist)
  playlistItems.list   1 unit   x ceil(n/50)  -> ids, titles, dates
  videos.list          1 unit   x ceil(n/50)  -> views, likes, duration

We deliberately avoid search.list, which costs 100 units a call.

Usage:
    python fetch_catalogue.py @doctorsango
"""
import json
import math
import os
import pathlib
import sys
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3"
ROOT = pathlib.Path(__file__).resolve().parent.parent
_quota = 0


def load_key() -> str:
    """Read YOUTUBE_API_KEY from the environment, falling back to clip-finder/.env."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key.strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "YOUTUBE_API_KEY":
                return value.strip().strip("'\"")
    sys.exit(
        "No API key found.\n"
        "  Put it in clip-finder/.env as:  YOUTUBE_API_KEY=your_key_here\n"
        "  (see .env.example). Never paste the key into a chat or commit it.")


def call(endpoint: str, cost: int = 1, **params) -> dict:
    global _quota
    params["key"] = load_key()
    url = f"{API}/{endpoint}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        sys.exit(f"YouTube API {e.code} on {endpoint}:\n{detail}")
    _quota += cost
    return body


def resolve_uploads_playlist(handle: str) -> tuple[str, str]:
    """Handle or channel id -> (uploads playlist id, channel title)."""
    if handle.startswith("UC") and len(handle) == 24:
        r = call("channels", part="contentDetails,snippet", id=handle)
    else:
        r = call("channels", part="contentDetails,snippet",
                 forHandle=handle if handle.startswith("@") else "@" + handle)
    items = r.get("items") or []
    if not items:
        sys.exit(f"Channel not found for '{handle}'. Try the raw UC... channel id.")
    it = items[0]
    return it["contentDetails"]["relatedPlaylists"]["uploads"], it["snippet"]["title"]


def list_uploads(playlist_id: str) -> list[dict]:
    """Every video in the uploads playlist. 1 unit per page of 50."""
    videos, token = [], None
    while True:
        params = dict(part="snippet,contentDetails", playlistId=playlist_id, maxResults=50)
        if token:
            params["pageToken"] = token
        page = call("playlistItems", **params)
        for it in page.get("items", []):
            videos.append({
                "video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "published_at": it["contentDetails"].get("videoPublishedAt"),
                "description": (it["snippet"].get("description") or "")[:500],
            })
        token = page.get("nextPageToken")
        print(f"  ...{len(videos)} videos", file=sys.stderr)
        if not token:
            return videos


def hydrate(videos: list[dict]) -> list[dict]:
    """Attach view/like/comment counts and duration. 1 unit per batch of 50."""
    by_id = {v["video_id"]: v for v in videos}
    ids = list(by_id)
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        r = call("videos", part="statistics,contentDetails", id=",".join(batch))
        for it in r.get("items", []):
            v = by_id[it["id"]]
            stats = it.get("statistics", {})
            v["views"] = int(stats.get("viewCount", 0) or 0)
            v["likes"] = int(stats.get("likeCount", 0) or 0)
            v["comments"] = int(stats.get("commentCount", 0) or 0)
            v["duration_iso"] = it["contentDetails"].get("duration", "")
            v["duration_s"] = iso_seconds(v["duration_iso"])
            v["is_short"] = 0 < v["duration_s"] <= 180
        print(f"  ...hydrated {min(i + 50, len(ids))}/{len(ids)}", file=sys.stderr)
    return videos


def iso_seconds(iso: str) -> int:
    """PT1M32S -> 92. Good enough for durations under a day."""
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


def main() -> None:
    handle = sys.argv[1] if len(sys.argv) > 1 else "@doctorsango"
    print(f"Resolving {handle}...", file=sys.stderr)
    playlist, name = resolve_uploads_playlist(handle)
    print(f"Channel: {name}  (uploads playlist {playlist})", file=sys.stderr)

    videos = hydrate(list_uploads(playlist))
    videos.sort(key=lambda v: v.get("views", 0), reverse=True)

    out = ROOT / "data" / "catalogue.json"
    out.write_text(json.dumps(
        {"channel": name, "handle": handle, "count": len(videos), "videos": videos},
        indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {len(videos)} videos to {out}", file=sys.stderr)
    print(f"Quota used: {_quota} units of 10,000/day", file=sys.stderr)


if __name__ == "__main__":
    main()
