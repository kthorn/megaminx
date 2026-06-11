# Megaminx Coach — Interactive Website Design

**Date:** 2026-06-11
**Goal:** A password-protected website where Freddie can twist a simulated
megaminx, enter his real puzzle's state, get an exact booklet-style solution
played back step by step, and — when he's stuck — upload a photo and ask a
Claude-powered coach what to do, in the booklet's kid-facing voice.

## Decisions (agreed 2026-06-11)

- **Hosting:** Fly.io, one small app, mirroring the deploy pattern of the
  existing `weapons-gen` repo (same account). Single shared password gates
  everything; the Anthropic API key lives in Fly secrets, never client-side.
- **v1 input modes:** photo coach mode + tap-to-enter full state.
  Guided multi-photo full-state capture is explicitly v2.
- **Visuals:** reuse the booklet's orthographic rounded-tile SVG renderer
  (`minx/render.py`) so the site looks like the printed guide Freddie knows.
  No Three.js.

## What the repo already provides

- `minx/puzzle.py` — sticker-level engine; a turn is one of 12 precomputed
  permutations (`CW_PERMS`) over a 132-entry state array. Pure stdlib.
- `minx/method.py` — the booklet's method as a stage-by-stage solver that
  works from any valid state and self-verifies (raises `MethodError` instead
  of producing a wrong solution). Has a high-level stage log but does **not**
  yet record the raw turn list.
- `minx/render.py` — SVG renderer for any state/view, same art as the guide.
- `build/make_guide.py` — all stage text and recovery notes: the coach's
  knowledge base, and `tiles_html`-style move-tile rendering to reuse for
  solution playback.

## Architecture

One Fly.io app: FastAPI backend + a single-page vanilla-JS frontend.
The client holds the current 132-sticker state array; the server is
stateless (no DB). Endpoints (all behind the password cookie):

| Endpoint | Purpose |
|---|---|
| `POST /api/render` | state (+ view faces) → booklet-style SVG |
| `POST /api/turn` | state + face + direction → new state |
| `POST /api/validate` | is this entered state physically possible? kid-friendly errors |
| `POST /api/solve` | state → staged solution: per-step hold ("gray bottom-right, pink front"), move tiles, SVG frames |
| `POST /api/coach` | photos + stage + question (+ optional entered state) → streamed Claude reply |

`/api/turn` could later move client-side by exporting `CW_PERMS` as JSON
(~20 lines of JS) if round-trips feel laggy, but we start server-side for
simplicity.

## Feature 1: interactive puzzle + tap-to-enter state

- Booklet-style SVG with two or three fixed views (front vertex + back);
  click a face arrow to turn it; scramble button.
- **Entry mode:** tap a sticker, pick from the puzzle's 12-color palette.
  Default palette = Freddie's puzzle's colors (from the photos we have);
  palette is editable since the booklet already says "use YOUR colors."
- **Stage-aware entry** (big usability win): pick your stage first, and only
  the stickers that stage cares about need entering — e.g. stage 6 needs
  only the low corners, ridge edges, and gray layer. Everything earlier is
  assumed solved and filled in automatically.
- Validation: piece multiset, corner-twist sum, edge-flip sum, permutation
  parity. Errors point at the suspect stickers ("two corners can't both be
  red+pink+cream — check these two again"), since a mis-tap is the common
  failure.

## Feature 2: exact solution playback

- Harden the solver (see below), record the concrete turn list per stage
  step, and play it back as booklet-style move-tile rows with Next/Back.
- Each step states the hold explicitly before its tiles, reusing the
  guide's language ("hold it so the empty slot is at the top front-right;
  gray is at the bottom-right").
- "I messed up" button: re-enter the affected region (or jump to photo
  coach) rather than trying to detect divergence, which we can't.

## Feature 3: photo coach mode

What it is — and honestly is not: one photo shows ~3 of 12 faces, so the
coach **diagnoses local situations**; it never claims to reconstruct full
state. (This is exactly the stage-6 red-corner/gray-squatter feedback loop
that motivated the site, made self-serve.)

- Input: 1–3 photos, a stage picker, optional free-text question.
- The Claude call gets: the booklet's full stage text + recovery notes in
  the system prompt, the photos, and **tools backed by the simulator** —
  `apply_alg`, `find_piece`, `render_state` — so it can verify a suggested
  sequence actually works on a canonical reconstruction of the described
  case before answering, and attach a rendered picture of the hold.
- Output: kid-voiced diagnosis + exact hold + sequence + rep count, with
  SVG move tiles. When colors are ambiguous (this puzzle's pink/hot-pink/
  red/salmon palette is genuinely hard), the coach asks for another angle
  instead of guessing.
- Model: default to the latest generally available Claude model
  (vision + tool use); cost at family scale is pennies per question.

## Prerequisite engineering: solver hardening

1. Record raw turns: wrap `Minx.turn` with a history, map back to per-stage
   segments with their grips.
2. Fuzz: run `Solver.solve()` over ~10k scrambles; today some raise
   `MethodError` (the diag scripts skip them). Fix the gaps or add a
   bounded-BFS recovery fallback so `/api/solve` never dead-ends.
3. State validation module (shared by entry UI and coach).

## Auth, safety, cost

- One shared password → signed cookie; rate-limit `/api/coach`.
- Coach system prompt is locked to megaminx coaching; no chat history kept
  beyond the session.
- Fly shared-cpu-1x ≈ $5/mo; Claude usage at family scale ≈ $0.01–0.10 per
  coach question.

## Build phases

1. **Interactive toy:** engine API, render, turn, scramble, tap-to-enter,
   validate. (~1 session)
2. **Solution playback:** solver hardening + move recording + playback UI.
   (~1–2 sessions)
3. **Photo coach:** Claude endpoint with simulator tools + photo upload UI.
   (~1 session)
4. **Deploy:** Fly app per weapons-gen pattern, password gate, polish,
   Freddie field-test. (~0.5 session)

## Out of scope (v1)

Full-state photo reconstruction (v2 candidate as a guided multi-photo
flow), accounts/multi-user, speedsolving methods, move-by-move camera
tracking.
