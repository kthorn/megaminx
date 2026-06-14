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
plus the coach. But all of `minx/` (engine, solver, renderer, validation,
~1500 lines) is **pure-stdlib Python with zero external deps** — so that compute
can run client-side. The *only* thing that fundamentally needs a secret is the
coach's Claude call. That collapses the architecture to "static site + one tiny
lambda," which is cheaper, simpler to operate, and scales for free.

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
- A generator, `tools/gen_vectors.py`, exports Python-derived **data** (not
  logic):
  - `perms.json` — the 12 turn permutations. The **TS turn engine is
    data-driven by this** (apply a permutation ≈ 20 lines), so it cannot
    diverge from the geometry — it consumes it.
  - `geometry.json` — per-view projected sticker polygons + adjacency + naming,
    so the **TS renderer draws identical SVG** from the same geometry rather
    than re-deriving it.
  - `vectors.json` — N scrambles → exact solution turn lists + per-step grips,
    plus valid/invalid state cases with expected error codes.
  - `coach_kb.json` — the booklet's stage text + recovery notes, exported from
    `make_guide.py`, so the coach's kid-facing voice stays in sync with the
    printed guide.
- **Only the solver and the validator are genuinely ported logic.** Engine and
  renderer are thin data consumers.
- **CI gate:** run the TS solver over `vectors.json`; for every scramble its
  turn list must **exactly match Python's** (deterministic method → exact match
  proves agreement). The validator must match expected error codes. A red gate
  means the port drifted. This carries "correct by construction" into TS.

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
minx/                 # unchanged Python: oracle + guide pipeline
build/                # unchanged guide build; + exports coach_kb.json
tools/gen_vectors.py  # Python → perms.json, geometry.json, vectors.json, coach_kb.json
packages/engine/      # shared TS: data-driven turn engine, renderer, validator, ported solver
web/                  # Vite TS SPA (imports packages/engine)
lambda/               # login + coach (Node, imports packages/engine)
infra/                # CloudFront + S3 + Lambda Function URL config (CDK or plain)
tests/                # Python suite (unchanged) + TS port-vs-vectors CI gate
```

Generated `*.json` are build artifacts; commit-vs-gitignore decided at
implementation time. Code (`minx/`, `build/`, `tests/`, `packages/`, `web/`,
`lambda/`) stays MIT; rendered booklet content stays CC BY 4.0 — preserve the
code-vs-content separation.

## Build phases

1. **Generator + shared engine.** `tools/gen_vectors.py`; port turn-engine +
   renderer (data-driven) + validator to TS; CI exact-match gate green. *(The
   static interactive toy is functional.)*
2. **Solver: harden (Python) → port (TS).** Fuzz 10k + fix gaps / BFS fallback
   in the oracle, then port; solver test-vector gate green; wire up playback UI.
   *(Exact solution playback works, fully static.)*
3. **SPA polish:** tap-to-enter, stage-aware entry, validation UI (errors point
   at suspect stickers).
4. **Auth + coach lambda:** login/HMAC, coach proxy with native tool-use over
   the TS engine, photo-upload UI.
5. **Deploy:** CloudFront + S3 + two Lambda Function URLs, password gate,
   Freddie field-test.

## Out of scope (v1)

Unchanged from the original spec: full-state photo reconstruction (v2 candidate
as a guided multi-photo flow), multi-user accounts, speedsolving methods,
move-by-move camera tracking. Cognito-based per-user auth is a possible later
upgrade that does not affect the static compute.
