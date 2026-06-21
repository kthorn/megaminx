# LLM Harness Framework — TS / Serverless Design (Option B)

**Date:** 2026-06-21
**Sibling to:** `2026-06-21-llm-harness-framework-design.md` (the **Python** option:
LiteLLM + Pydantic AI + SQLite). This is the **TypeScript, serverless** alternative.
The two are **mutually exclusive choices for the agent core** — pick one to
implement; this doc exists so the decision is made against a concrete second
option, not in the abstract.

**Goal:** The same general-purpose, reusable LLM agent harness — provider seam +
agent loop + local-function tools + persistence — but built in **TypeScript** so
it runs **serverless** (edge function / Lambda) and shares one engine with a
static SPA. Default model **glm-5.2 via OpenRouter**. Megaminx coach is consumer #1.

## How this relates to the other specs

- It is the TS counterpart to the Python harness spec (same product, same
  reusability boundary, different language/runtime).
- It is **architecturally aligned with the static-site coach spec**
  (`2026-06-14-megaminx-coach-static-site-design.md`): static SPA + one tiny
  auth-gated function. The only change is that the function's downstream is
  **OpenRouter** instead of the native Anthropic Messages API, and the agent
  loop is the **Vercel AI SDK** instead of hand-rolled tool-use. If Option B
  wins, this spec effectively updates the agent layer of the static-site spec.

## The serverless reality check (read first)

"Serverless" here means **no server you manage**, not **no server at all**:

- The **OpenRouter API key cannot live in the browser** — a static bundle is
  readable by anyone, and a leaked key lets strangers spend your credits. So
  even a purely static site needs **one thin key-holding hop** (Cloudflare
  Worker / Vercel Edge Function / Lambda Function URL) that holds the key and
  forwards to OpenRouter. This is exactly the "one small lambda" the static-site
  spec already accepted; OpenRouter doesn't remove it.
- Everything else (turn/solve/render/validate, plus the agent loop and tools)
  **can** run in that same function or in the browser. The function is small and
  auth-gated; it is the entire server-side footprint.

## Auth & key delivery (and the one way to delete the server)

Worth recording because it's a natural "can Cognito do something clever here?"
question. Cognito and the proxy function solve **different halves** — Cognito
can replace the *auth*, but on this stack it cannot remove the *key-holding
proxy*:

- **Cognito replaces the auth half only.** A Cognito **User Pool** gives real
  per-user accounts + JWTs in place of the static-site spec's shared-password →
  HMAC token. That's a fine upgrade *if* you want accounts (and a stable user id
  to attach per-user budgets/usage to). For a single shared family password it's
  heavier than the ~20-line HMAC the static-site spec chose — which is exactly
  why that spec listed Cognito as a "later upgrade that doesn't touch the static
  compute." That call still holds.
- **Cognito can't safely deliver the OpenRouter key to the browser.** A Cognito
  **Identity Pool** vends temporary **AWS IAM** credentials — useful only for
  services that accept IAM auth. The OpenRouter key is a **third-party secret**;
  STS creds grant nothing at OpenRouter. You *could* IAM-allow the browser to
  read the key from Secrets Manager, but that hands a long-lived,
  credit-spending key to client JS — the exfiltration risk we're avoiding.
- **The agent loop also forces server-side compute.** The coach is a multi-step
  tool loop (model → run tool against the engine → feed result back → continue),
  not a passthrough request, so it must run where both the tools and the key
  live. API Gateway + a Cognito authorizer can gate the entrance but can't run
  the loop, and streams SSE poorly; a Lambda Function URL in response-streaming
  mode is the right home. So with OpenRouter the proxy survives regardless.

**The one way to delete the server entirely (Cognito + Bedrock).** If the model
endpoint is an **AWS-native** one — **Amazon Bedrock** — the whole proxy
collapses: a Cognito **Identity Pool** vends IAM creds, the browser calls
`bedrock:InvokeModelWithResponseStream` **directly**, and because the engine is
already TS in the browser, the **AI SDK tool loop runs client-side too** (tools
execute in-browser against `packages/engine`). No key, no proxy, no server —
truly static. **Trade-off:** that's Bedrock's model menu (Claude, Llama,
Mistral, Nova…), **not GLM/OpenRouter** — the price of deleting the lambda is
giving up glm-5.2. This is a genuine fork to weigh against the default
OpenRouter-via-proxy path, not a strict improvement.

## Decisions (proposed 2026-06-21)

- **Provider seam = OpenRouter itself.** OpenRouter is OpenAI-compatible *and*
  already aggregates 100+ models behind one key, so it **is** the seam — there
  is no TS LiteLLM layer to add. Swapping glm-5.2 → Claude → Llama is a model-id
  string change. (If a non-OpenRouter backend is ever needed, the Vercel AI SDK
  has per-provider packages; the seam stays a one-file concern.)
- **Agent loop = Vercel AI SDK (`ai`).** `streamText`/`generateText` own the
  tool-call loop (`stopWhen`/step limit), tool dispatch, streaming, and
  structured output (`experimental_output` / `generateObject` with a zod
  schema). This is the TS analog of Pydantic AI.
- **Tools = local TS functions.** AI SDK `tool({ inputSchema: z…, execute })`
  handlers calling the shared engine **in-process** — no MCP, no extra hop
  (matches the static-site spec's "no MCP" decision).
- **Persistence = libSQL/Turso (SQLite, serverless).** Keeps the Python spec's
  SQLite story but serverless-native: same schema, edge-reachable. v1 may ship
  with **no persistence** (client holds puzzle state, no chat history kept — as
  the coach specs already chose) and add Turso only when resumable sessions are
  wanted. Cloudflare D1 is an equivalent if hosting on Workers.
- **Runtime = edge or node function.** The ported engine is **pure TS, zero
  native deps**, so it runs in constrained edge runtimes (Cloudflare Workers /
  Vercel Edge) as well as Node Lambda. Choose by host.
- **Default model = `glm-5.2` via OpenRouter** (`z-ai/glm-5.2`), key in the
  function's env (`OPENROUTER_API_KEY`), never in the browser.

## What is generic (the harness) vs project (the coach)

Same reusability contract as the Python spec, expressed in TS:

**Generic — `packages/harness` (TS), zero megaminx knowledge:**

- **Model factory** — builds an AI SDK model from config (the OpenRouter seam:
  `createOpenRouter({ apiKey }).chat(modelId)` or the OpenAI-compatible provider
  pointed at `https://openrouter.ai/api/v1`).
- **Runner** — `runTurn(sessionId, input, attachments?) -> Reply`: load prior
  messages, run `streamText` with the registered tools + step cap, persist new
  messages + usage. Streaming and non-streaming variants.
- **Tool registry** — a project exports a `tools(ctx)` map of AI SDK tools; the
  harness wires them in and enforces the max-step cap.
- **Persistence adapter** — an interface (`load/saveMessages`, `recordUsage`)
  with a libSQL/Turso impl and a no-op impl; same logical schema as the Python
  spec (sessions, messages, tool_calls, usage, attachments).
- **Config** — env-driven (`OPENROUTER_API_KEY`, model id, max steps, budget
  cap, db url, log level).
- **Observability + cost** — per-turn structured logging; OpenRouter returns
  usage/cost in the response, recorded per session.

**Project — supplied by the coach (consumer #1):**

- **Context/deps** — the TS `packages/engine` handle, current 132-sticker state,
  stage.
- **Tools module** — `apply_alg`, `find_piece`, `render_state`, `validate_state`,
  `describe_effect`, each calling `packages/engine` in-process.
- **System prompt** — built from `coach_kb.json` (the booklet content extraction
  from the static-site spec).
- **Output schema** — a zod schema for the kid-voiced diagnosis + hold +
  sequence + rep count.

## Architecture

```
   Browser (static SPA on S3+CloudFront / Cloudflare Pages)
     - turn/solve/render/validate in-browser (packages/engine)
     - posts photos + question to /api/coach
                    │  (key NEVER in browser)
                    ▼
   /api/coach  — edge function / Lambda Function URL  (the only server)
     1. verify auth token
     2. packages/harness.runTurn(...)
          ├─ Vercel AI SDK streamText loop
          │    └─ tools = local TS fns → packages/engine (in-process)
          └─ persist (libSQL/Turso, optional)
     3. stream reply back
                    │ model calls
                    ▼
          OpenRouter  →  z-ai/glm-5.2   (model swappable by config)
```

The coach itself is small: define the context, write the five engine-backed
tools, point the prompt at `coach_kb`, declare the zod output schema, call
`runTurn`. Everything about driving the model is inherited from `packages/harness`.

## Repo layout

Aligns with the static-site spec's monorepo (`packages/engine`, `web/`):

```
packages/
  engine/      # shared TS engine (turn/solve/render/validate) — from static-site spec
  harness/     # NEW generic TS harness: model factory, runTurn, tool registry,
               #   persistence adapter, config  (its own package, reusable)
coach/         # NEW megaminx consumer: context, tools, prompt, output schema
web/           # Vite TS SPA (static)
functions/     # /api/login + /api/coach (edge/Lambda; import packages/harness + engine)
minx/          # Python oracle — UNCHANGED (generates engine test vectors)
```

`minx/` stays pure-stdlib and remains the correctness oracle that generates test
vectors for `packages/engine` (per the static-site spec). Code stays MIT;
booklet-derived prompt content stays CC BY 4.0.

## Testing strategy

- **Harness, no network:** the Vercel AI SDK ships `MockLanguageModelV2` — drive
  the loop deterministically, assert tool dispatch, the step cap, structured
  output validation, and persistence round-trips. Offline, in CI.
- **Coach tools, no model:** call each tool against `packages/engine` and assert
  simulator truths (a suggested sequence solves the case and leaves marked
  pieces intact) — the "the coach can't suggest a broken alg" guarantee. These
  run under the same CI gate that already checks the TS engine against the
  Python vectors.
- **Live smoke (opt-in, env-gated):** one real glm-5.2 turn through OpenRouter
  to confirm tool calling + structured output bind end to end.

## Build phases

1. **Harness core (offline).** `packages/harness`: model factory (OpenRouter
   seam), `runTurn`, tool registry, persistence adapter (no-op + Turso), config.
   Driven by `MockLanguageModelV2` — lands with no provider needed.
2. **Provider bring-up.** Wire default OpenRouter/glm-5.2; env-gated live smoke;
   confirm tool calling + structured output. (Depends on `packages/engine`
   existing — i.e. static-site spec phase 1.)
3. **Coach consumer.** Context, the five engine-backed tools, zod output schema,
   prompt from `coach_kb`. Tool-level correctness tests vs the engine.
4. **Wire + deploy.** `/api/coach` edge function holding the key; auth token
   reused from the static-site spec's `/api/login`; deploy on the existing
   static stack (CloudFront + Function URL, or Cloudflare Pages + Worker).

## Option A vs Option B (decision aid)

| | A — Python (sibling spec) | B — TS serverless (this) |
|---|---|---|
| Loop | Pydantic AI | Vercel AI SDK |
| Seam | LiteLLM → OpenRouter | OpenRouter directly |
| Engine | Python `minx/` reused directly | ported `packages/engine` (TS) |
| Reusable artifact | `pip`-installable Python package | TS package |
| Deploy | Python Lambda/edge | static SPA + tiny edge fn (matches static-site spec) |
| Persistence | SQLite (`sqlite3`) | libSQL/Turso (or none v1) |
| Best when | reuse across Python projects / CLI; richest agent tooling | one engine across browser+server; truly static-first coach |

**Tie-breaker:** Option B shares a single engine with the SPA and slots into the
already-designed static stack with the least new infrastructure; Option A gives
the more mature agent framework and a Python-reusable artifact, at the cost of a
second runtime alongside the TS SPA.

## Decisions needed (before implementing B)

1. **Model + topology:** OpenRouter/glm-5.2 behind a streaming proxy
   (default; keeps GLM, needs the one function) **vs** Bedrock + Cognito
   Identity Pool with a client-side loop (no server, but Bedrock's model menu,
   no GLM). See "Auth & key delivery."
2. **Host:** Cloudflare (Pages + Workers + D1) vs AWS (S3+CloudFront + Lambda
   Function URL + Turso). Picks the runtime and the persistence impl.
3. **Persistence in v1?** None (client state, no history — coach-spec default)
   vs Turso/D1 from the start (resumable sessions, cost audit).
4. **OpenRouter provider package:** `@openrouter/ai-sdk-provider` vs the AI SDK's
   OpenAI-compatible provider pointed at OpenRouter's base URL. Minor; confirm at
   build time.
5. **`glm-5.2` on OpenRouter with tool calling?** Same live check as Option A;
   name a fallback model if not. (Moot if the Bedrock topology is chosen.)

## Out of scope

The SPA/auth/deploy mechanics (owned by the static-site spec), MCP (avoided —
tools in-process), multi-user accounts, and any change to `minx/` or the booklet
pipeline.
