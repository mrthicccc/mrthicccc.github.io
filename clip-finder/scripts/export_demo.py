#!/usr/bin/env python3
"""Bake the cached searches into a self-contained JSON blob for the public demo.

The published page cannot call the YouTube API (browser sandboxes block it) and
must never carry an API key, so the demo ships real results captured locally.
Thumbnails are embedded as data URIs because external images are blocked too.

Writes data/demo.json.
"""
import base64
import importlib.util
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

spec = importlib.util.spec_from_file_location("clipapp", ROOT / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
import recommend_venue as rv

CLIPS_PER_SCENARIO = 10
FRAMES = ("default", "1", "2", "3")     # 120x90 storyboard frames - small


def fetch_frame(video_id, name):
    url = "https://i.ytimg.com/vi/{}/{}.jpg".format(video_id, name)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = r.read()
        if len(data) < 800:              # YouTube's grey placeholder
            return None
        return "data:image/jpeg;base64," + base64.b64encode(data).decode()
    except Exception:
        return None


def main():
    scenarios, total_bytes = [], 0
    for cache in sorted((ROOT / "data" / "cache").glob("*.json")):
        name = cache.stem.replace("-", " ")
        clips = json.loads(cache.read_text(encoding="utf-8"))
        clips = app.decode_entities([c for c in clips if c.get("views")])
        for c in clips:
            app.score_clip(c)
        clips.sort(key=lambda c: c["score"], reverse=True)

        seen, spread = {}, []
        for c in clips:
            n = seen.get(c["channel"], 0)
            if n < 2:
                seen[c["channel"]] = n + 1
                spread.append(c)
        spread = spread[:CLIPS_PER_SCENARIO]

        out = []
        for c in spread:
            frames = [f for f in (fetch_frame(c["video_id"], n) for n in FRAMES) if f]
            total_bytes += sum(len(f) for f in frames)
            out.append({
                "id": c["video_id"], "title": c["title"], "channel": c["channel"],
                "views": c["views"], "duration": c["duration_s"],
                "score": c["score"], "reasons": c["reasons"], "flags": c["flags"],
                "url": c["url"], "frames": frames,
            })
            print("  {:<42} {} frames".format(c["title"][:40], len(frames)))

        scenarios.append({
            "name": name,
            "verdict": rv.assess(name),
            "suggested": out[0]["id"] if out else None,
            "clips": out,
        })
        print("{} -> {} clips".format(name, len(out)))

    payload = {
        "scenarios": scenarios,
        "model": {
            "weights": [round(x, 5) for x in rv.fit_and_validate()[0]],
            "features": rv.FEATURES,
            "rho": round(rv.fit_and_validate()[1], 3),
            "tried": {k: v[1] for k, v in rv.TRIED.items()},
            "tried_features": {k: v[0] for k, v in rv.TRIED.items()},
            "candidates": rv.CANDIDATES,
            "keywords": rv.KEYWORDS,
            "saturated": rv.SATURATED,
            "high_supply": rv.HIGH_SUPPLY,
        },
    }
    out_path = ROOT / "data" / "demo.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    size = out_path.stat().st_size
    print("\nwrote {}  ({:,} bytes, {:.1f} MB)".format(out_path, size, size / 1e6))
    print("image payload: {:.1f} MB of that".format(total_bytes / 1e6))


if __name__ == "__main__":
    main()
