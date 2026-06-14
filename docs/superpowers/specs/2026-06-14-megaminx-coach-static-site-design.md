# Megaminx Coach — Static-Site Architecture (revision)

**Date:** 2026-06-14
**Supersedes the hosting/compute decisions in:** `2026-06-11-megaminx-coach-site.md`
(the product goal, feature set, and UX in that spec are unchanged — this revises
*where the compute runs*).

**Goal:** Deliver the same coach site — interactive megaminx, tap-to-enter state,
exact booklet-style solution playback, and a Claude-powered photo coach — as a
**purely static site** with **no managed server**. All puzzle compute runs in
the browser; the only server-side code is one small auth-gated lambda for the
coach, which exists solely to keep the Anthropic API key secret.

## Why this revision

The original spec put a FastAPI app on Fly.io doing render/turn/solve/validate
plus the coach. But all of `minx/` (engine, solver, renderer; ~1500 lines) is
**pure-stdlib Python with zero external deps** — so that compute can run
client-side. The *only* thing that fundamentally needs a secret is the coach's
Claude call. That collapses the architecture to "static site + one tiny lambda,"
which is cheaper, simpler to operate, and scales for free.

**Dependency caveat:** the stdlib-only claim applies to `minx/` *only*. The guide
build (`build/make_guide.py`) imports `weasyprint`; the booklet pipeline is
unaffected by this revision and keeps that dependency. The new `coach_kb`
extraction (below) must read the booklet's stage text **without** importing
`weasyprint`, so the content must be split from the rendering code.

**Codebase note (the original spec is stale here):** there is no `minx/method.py`.
The solver now lives in `minx/solver.py` (`BaseSolver`, `Step`, `Solution`,
`MethodError`) and `minx/method_mega.py` (the megaminx method); `minx/spec.py`
holds the `PuzzleSpec`. There is **no validator module today** — state validation
is new work. `Step.moves` are raw `(face_index, times)` tuples and `hold_text`
is left empty by `method_mega.solve()`; booklet notation, grip names, and camera
angles live only in `build/make_guide.py` (`tiles_html`). These gaps are
addressed in the build phases.

## Decisions (agreed 2026-06-14)

- **Static SPA** built with **Vite + TypeScript**, hosted on **S3 + CloudFront**
  (Cloudflare Pages is an acceptable alternative). All turn / solve / render /
  validate runs in the browser.
- **Two Lambda Function URLs**, fronted by the **same CloudFront distribution**
  as additional origins (single domain → cookie auth with no CORS):
  - `POST /api/login` — verifies the shared family password, returns an
    **HMAC-signed token** as a cookie.
  - `POST /api/coach` — verifies the token, then **proxies to Claude with the
    API key held server-side**. The key never reaches the browser.
- **Auth:** single shared password → signed token (chosen over Cognito for
  minimal cost/complexity; can graduate to Cognito later without touching the
  static compute).
- **Cost minimization:** the lambdas run **outside any VPC** (public egress to
  `api.anthropic.com` is free) → **no NAT gateway, no VPC endpoints**. Key lives
  in the lambda **env var** (encrypted at rest); Secrets Manager is a trivial
  later upgrade. Expected bill ≈ pennies/month + actual Claude usage.
- **Client compute:** port the engine/renderer/validator/solver to TypeScript,
  **verified against Python-generated test vectors in CI** (see Correctness).
- **Coach tool access:** native Messages API **tool use** (function calling) with
  in-process handlers calling the shared TS engine — **no MCP** (no separate
  server, no extra hop).

## Architecture

```
                         ┌──────────────── CloudFront (one domain) ───────────────┐
   Browser (SPA) ───────▶│  /            → S3 (static Vite build)                  │
   - turn/solve/render    │  /api/login  → Lambda Function URL (HMAC issuer)       │
   - validate             │  /api/coach  → Lambda Function URL (Claude proxy)      │
   - solution playback    └────────────────────────────────────────────────────────┘
                                              │ (coach only)
                                              ▼
                              Claude Messages API (vision + tool use)
                              key in lambda env var; lambda outside any VPC
```

- The client holds the 132-sticker state array and does **all** megaminx work.
- The server touches the puzzle **only** inside the coach lambda, and only to
  *verify* Claude's suggested sequences via the shared engine.

### Endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/login` | password in body | verify shared password → set HMAC-signed cookie |
| `POST /api/coach` | signed cookie | photos + stage + question → streamed Claude reply |

All render/turn/validate/solve endpoints from the original spec are **gone** —
that work now happens in the browser.

## Correctness strategy (the heart of this design)

Porting to a second language risks divergence from the verified Python sim. We
structure the port so **only one component is genuinely reimplemented**:

- **Python `minx/` remains the single source of truth.** It still derives
  geometry → `CW_PERMS`, runs the solver, renders, and builds the guide
  (`build/make_guide.py`) — unchanged. The booklet pipeline is untouched.
- A generator, `tools/gen_vectors.py`, exports Python-derived **data**:
  - `perms.json` — the 12 turn permutations (`CW_PERMS`). The **TS turn engine
    is data-driven by this** (apply a permutation ≈ 20 lines), so it cannot
    diverge from the geometry — it consumes it.
  - `geometry.json` — the **static 3D geometry**: per-sticker 3D polygons and
    face normals, plus the derived `adj`/`opp`, the canonical face order, the
    per-face `name_faces` mapping, and the solver's slot ordering and grip
    names. This is raw geometry/convention data, **not** pre-projected per-view
    polygons.
  - `vectors.json` — N scrambles → exact solution turn lists (raw
    `(face, times)`) **and** the enriched per-step playback fields (display
    notation, grip names, hold text, camera faces — see build phase 2), plus
    valid/invalid state cases with expected error codes.
  - `coach_kb.json` — the booklet's stage text + recovery notes, produced by a
    **dedicated extraction pass** (see build phase 4), so the coach's kid-facing
    voice stays in sync with the printed guide.
- **Genuinely ported logic: the solver, the validator, and the renderer.** The
  turn engine is the only true data consumer. The renderer is **not** a thin
  consumer — `minx/render.py` computes cameras (`Camera.project`,
  `visible_faces`), insets sticker polygons in 3D (`_inset3d`), and draws turn
  arrows/outlines dynamically. The TS renderer ports that camera/projection/SVG
  math (small, pure tuple arithmetic) and consumes `geometry.json` for the
  static 3D inputs. SVG must match Python *visually*, not byte-for-byte.
- **CI gate (two tiers):**
  1. **Robust, language-independent (primary):** for every scramble in
     `vectors.json`, the TS solver must produce a solution that (a) actually
     solves the puzzle and (b) leaves earlier-solved pieces intact when applied
     by the TS engine. This mirrors the solver's own `assert_solved_intact`
     self-verification and does not depend on traversal-order parity.
  2. **Exact-match (stricter, where feasible):** the TS solver's raw turn list
     should equal Python's. This is achievable **only** if the TS port faithfully
     replicates Python's traversal/search order (BFS face & turn order, ferry
     face-set sorting, slot dict order, mirror/`k` attempt order, last-layer
     candidate tie-breaking). The exported ordering/grip conventions in
     `geometry.json` make this possible; where a case proves too order-sensitive
     to match exactly, it falls back to tier 1 (logged, not silently skipped).

  A red gate means the port drifted. This carries "correct by construction" into
  TS without making the whole suite hostage to byte/order parity.

**Python-first prerequisite (from the original spec, unchanged):** harden the
solver — fuzz ~10k scrambles, fix the `MethodError` gaps or add a bounded-BFS
fallback so `/solve` never dead-ends — **before** porting, so the oracle never
dead-ends.

## Coach lambda

- **Node** lambda (so it can import the shared TS engine — keeping a single
  engine across browser and server rather than reintroducing Python's `minx/`).
- Flow: verify HMAC token → build system prompt from `coach_kb.json` → call the
  latest Claude vision model with photos + a `tools` array
  (`apply_alg`, `find_piece`, `render_state`) → run a **native tool-use loop**
  whose handlers call `packages/engine` in-process → stream the reply back.
- **No MCP.** Tools are in-process function calls; MCP would add a server and a
  network hop for no benefit at this scale.
- Output: kid-voiced diagnosis + exact hold + sequence + rep count + an SVG of
  the hold. The coach **diagnoses local situations** (one photo ≈ 3 of 12
  faces); it never claims full-state reconstruction. When colors are ambiguous,
  it asks for another angle rather than guessing.
- Rate-limit per token; no chat history kept beyond the session.

## Auth

- `POST /api/login` checks the shared password against a value in the lambda env
  var, and on success sets a cookie containing an **HMAC-signed token** (e.g.
  `payload.HMAC_SHA256(payload, secret)` with an expiry).
- `POST /api/coach` recomputes the HMAC and rejects invalid/expired tokens
  before doing any Claude work.
- The signing secret and the Anthropic key live only in lambda env vars. The
  key is **never** sent to the browser — the lambda proxies the Claude call.

## Repo layout

```
minx/                 # Python oracle: geometry, puzzle, solver.py, method_mega.py,
                      #   spec.py, render.py + NEW validate.py (state validation)
build/                # guide pipeline (weasyprint); booklet content split into a
                      #   weasyprint-free module for coach_kb extraction
tools/gen_vectors.py  # Python → perms.json, geometry.json, vectors.json
tools/gen_coach_kb.py # Python → coach_kb.json (no weasyprint import)
packages/engine/      # shared TS: data-driven turn engine + ported solver,
                      #   renderer (camera/projection/SVG), validator; stable public API
web/                  # Vite TS SPA (imports packages/engine)
lambda/               # login + coach (Node, imports packages/engine)
infra/                # CloudFront + S3 + Lambda Function URL config (CDK or plain)
tests/                # Python suite + TS port-vs-vectors CI gate
```

**Engine API contract (define before wiring browser + lambda).** `packages/engine`
exposes a stable public API used identically by the SPA and the coach lambda:
the state shape (132-entry color array) and color encoding, move notation
(parse/apply, matching `parse_alg`/`apply_alg`), the solver entry point and the
enriched `Solution`/`Step` shape, render options, the validator result/error-code
schema, and `find_piece`. Lock this contract in phase 1 so later phases build
against a fixed surface.

Generated `*.json` are build artifacts; commit-vs-gitignore decided at
implementation time. Code (`minx/`, `build/`, `tests/`, `packages/`, `web/`,
`lambda/`) stays MIT; rendered booklet content stays CC BY 4.0 — preserve the
code-vs-content separation.

## Build phases

1. **Generator + shared engine + API contract.** Lock the engine API contract;
   write `tools/gen_vectors.py` (export `perms.json` + `geometry.json` including
   adj/opp/face-order/slot-order/grip names); port the turn engine (data-driven)
   and renderer (camera/projection/SVG math) to TS; tier-1 CI gate green for
   render/turn round-trips. *(The static interactive toy is functional.)*
2. **Solver: enrich → harden → port.** First enrich the Python solver so each
   `Step` carries display notation, grip `names`, populated `hold_text`, and
   camera faces (today `method_mega.solve()` leaves these empty and `Step.moves`
   are raw `(face, times)`); these feed both `vectors.json` and playback. Then
   fuzz ~10k + fix `MethodError` gaps / add bounded-BFS fallback in the oracle so
   `/solve` never dead-ends. Then port the solver to TS; bring up the two-tier
   solver gate (tier-1 validity+intact for all, tier-2 exact-match where order
   permits). Wire up booklet-style playback UI. *(Exact solution playback works,
   fully static.)*
3. **State validator (Python first, then port) + SPA entry UI.** Build the new
   `minx/validate.py` as the oracle — sticker multiset, fixed-center checks,
   corner-twist / edge-flip sums, permutation parity — with a defined error-code
   schema; add valid/invalid cases to `vectors.json`; port to TS; build
   tap-to-enter, stage-aware entry, and validation UI (errors point at suspect
   stickers).
4. **Coach knowledge + lambda.** Split the booklet's stage text + recovery notes
   out of `build/make_guide.py` into a weasyprint-free content module; write
   `tools/gen_coach_kb.py` → `coach_kb.json`. Build login/HMAC and the coach
   proxy lambda with native tool-use over the TS engine; photo-upload UI.
5. **Deploy:** CloudFront + S3 + two Lambda Function URLs, password gate,
   Freddie field-test.

## Out of scope (v1)

Unchanged from the original spec: full-state photo reconstruction (v2 candidate
as a guided multi-photo flow), multi-user accounts, speedsolving methods,
move-by-move camera tracking. Cognito-based per-user auth is a possible later
upgrade that does not affect the static compute.
