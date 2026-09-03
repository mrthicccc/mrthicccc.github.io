# Deploying a shareable version

The published artifact demo cannot search live — browser sandboxes block all
outbound network calls, so no amount of key-pasting makes it work there. A live
version has to be a deployed server. This is that.

## The security model

`REQUIRE_USER_KEY=1` makes the app ignore any key in `.env` and demand one from
each visitor. That means:

- **Nobody spends your quota.** Each visitor uses their own YouTube key
  (~200 units of their own 10,000/day per new search) and their own Anthropic
  key for the judge.
- **Keys live in the visitor's browser** (`localStorage`), sent as request
  headers, used for that one request, and never written to disk or logs.
- **Keys never appear in a URL.** They travel as `X-Youtube-Key` /
  `X-Anthropic-Key` headers, because query strings end up in browser history,
  referrer headers and access logs.
- **The venue scorer stays free.** It needs no key at all, so someone can judge
  whether a venue is worth doing without setting anything up.

One thing this does NOT do, which you should be aware of:

**Keys transit your server.** A visitor is trusting your deployment not to log
their key. The code doesn't (`log_message` is disabled and nothing writes the
key anywhere), but that is a trust claim you're making on their behalf. If your
partner would rather not, they can run it locally from the same repo.

## The passphrase gate

Set `APP_PASSPHRASE` and the whole site — pages and API alike — sits behind a
sign-in screen. Leave it unset (the local default) and the app is open.

How it works:

- **Stateless signed cookie.** On success the server issues
  `expiry.HMAC-SHA256(secret, expiry)`. There is no session store to run or
  clean up, and the passphrase is never re-sent after login.
- **`hmac.compare_digest`, not `==`.** A wrong guess can't be narrowed down by
  timing the comparison.
- **Cookie is `HttpOnly`, `SameSite=Lax`**, and gains `Secure` automatically
  when the request arrives over HTTPS (`X-Forwarded-Proto`).
- **Rate limited**: 8 failed attempts per IP per 15 minutes, then a lockout.
  Behind a proxy it reads `X-Forwarded-For`, so the limit follows the real
  client rather than the load balancer.
- **30-day sessions.** `/logout` clears the cookie.

Set `SESSION_SECRET` in production. Without it the secret is regenerated at
boot, so every restart signs everyone out.

### What it is not

A shared passphrase is one secret held by several people. It doesn't identify
who signed in, can't be revoked per person, and is only as strong as the phrase
itself and wherever you sent it. It's the right weight for keeping a link
private between you and a partner; it is not an access-control system. To
rotate it, change `APP_PASSPHRASE` and redeploy — everyone signs in again.

## Deploy to Render

1. Push this folder to a GitHub repo. Confirm `.env` is not in it —
   `.gitignore` already excludes it, but check with `git status` before pushing.
2. On render.com: **New → Web Service**, point it at the repo.
3. It picks up `render.yaml` and `Dockerfile` automatically. `REQUIRE_USER_KEY`
   is already `1`, and `SESSION_SECRET` is generated for you.
4. Render will prompt for **`APP_PASSPHRASE`** (it's marked `sync: false`, so it
   is never stored in the repo). Enter the phrase you'll share.
5. Deploy. Render supplies `PORT`; the app binds `0.0.0.0` when it sees one.

Send your partner two things: the URL and the passphrase — ideally not in the
same message.

Fly.io, Railway and any other Docker host work the same way. The only required
environment variable is `REQUIRE_USER_KEY=1`.

## Running it locally

Locally you don't want to paste keys every time, so leave `REQUIRE_USER_KEY`
unset and put them in `.env`:

    YOUTUBE_API_KEY=...
    ANTHROPIC_API_KEY=...

The key panel still appears, collapsed, so you can override the server key with
your own at any time.

## What your partner needs

A YouTube Data API key takes about two minutes and needs no billing details:

1. console.cloud.google.com → new project
2. APIs & Services → Library → "YouTube Data API v3" → Enable
3. APIs & Services → Credentials → Create credentials → API key
4. Recommended: restrict it to YouTube Data API v3

The Anthropic key is optional — without it the app ranks on heuristics and says
so. With it, Claude looks at four frames from each clip.
