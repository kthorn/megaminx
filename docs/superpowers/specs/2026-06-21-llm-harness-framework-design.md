# LLM Harness Framework — Design

**Date:** 2026-06-21
**Goal:** A small, **general-purpose, project-agnostic** LLM agent harness —
provider seam + agent loop + local-function tools + persistence — that other
projects can adopt unchanged, with the **megaminx coach as its first consumer**.
Default model: **glm-5.2 via OpenRouter**.
The harness owns "how to drive a model with tools and remember the
conversation"; each project supplies only its tools, its system prompt, and its
output schema.

**Relationship to the coach specs.** The two coach designs
(`2026-06-11-megaminx-coach-site.md`, `2026-06-14-megaminx-coach-static-site-design.md`)
chose a TypeScript engine + the **native Anthropic Messages API** tool-use loop
in a Node lambda, **no MCP**. This spec is a deliberate fork of that compute
decision: a **Python** harness, **provider-agnostic** via LiteLLM, driven by
**Pydantic AI**, default model **glm-5.2 via OpenRouter**. It keeps the same
product (a simulator-backed coach) but makes the agent layer reusable and the
model swappable. The static-site/auth/deploy parts of those specs are
orthogonal and unchanged; this spec only replaces the agent core.

## Decisions (proposed 2026-06-21)

- **Provider seam = LiteLLM.** All model traffic goes through LiteLLM so the
  model is a config value, not a code dependency. Swapping glm-5.2 → Claude →
  a local vLLM is an env/config change, never a code change.
- **Agent loop = Pydantic AI.** Pydantic AI owns the tool-call loop, typed
  dependency injection (`RunContext[Deps]`), structured/validated output, and
  per-tool retries. It composes *on top of* LiteLLM via its first-party
  `LiteLLMProvider`, so there is **no overlap** between the two — LiteLLM is the
  transport, Pydantic AI is the orchestration.
- **Tools = local Python functions.** Plain functions registered with the
  agent; no MCP, no separate tool server, no extra network hop. A project drops
  in a tools module; the harness wires it up.
- **Persistence = SQLite.** One file DB stores sessions, the full Pydantic AI
  message history (for resume/replay), tool calls + results, token usage/cost,
  and attachments. Pure-stdlib `sqlite3`; no ORM required.
- **Default model = `glm-5.2` via OpenRouter.** OpenRouter is an
  OpenAI-compatible model gateway that LiteLLM supports natively (the
  `openrouter/` prefix); one key, one endpoint, GLM exposed as `z-ai/glm-5.2`.
  (See "Model routing" for the direct-to-Z.ai alternative.)
- **Reusability boundary is explicit** (see "What is generic vs project").
  The harness ships as its own installable package with its own optional
  dependencies, so the existing **`minx` package stays pure-stdlib** and the
  booklet pipeline is untouched.

## Why this layering (LiteLLM *and* Pydantic AI)

These two look like they overlap — both can "talk to many providers" — but they
sit at different layers, and Pydantic AI ships the adapter to stack them:

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider

model = OpenAIChatModel(
    "openrouter/z-ai/glm-5.2",                    # LiteLLM's native OpenRouter route
    provider=LiteLLMProvider(api_key=settings.openrouter_api_key),
)
agent = Agent(model, deps_type=Deps, output_type=CoachReply, ...)
```

- **LiteLLM** = the *provider seam*: one call shape over 100+ providers, plus
  retries/fallbacks, cost accounting, and pluggable callbacks (logging, budget
  caps). It is what makes the model swappable.
- **Pydantic AI** = the *agent loop*: the tool-call iteration, typed deps,
  validated structured output, streaming, and message history. It is what makes
  the loop typed and testable.

**Honest caveat to record now:** because OpenRouter is *already*
OpenAI-compatible, Pydantic AI could talk to it directly via `OpenAIProvider`
(`base_url=https://openrouter.ai/api/v1`) with no LiteLLM at all. LiteLLM earns
its place only if we want (a) genuine multi-provider swap across
*non*-OpenAI-shaped backends, (b) centralized cost/budget callbacks, or (c) a
shared LiteLLM **proxy** across projects. If none of those land, LiteLLM is
removable without touching the loop — which is itself a point in favor of the
seam (it's isolated to the model factory).

## Model routing

The harness routes by config; the default and the fallback:

1. **OpenRouter (default, recommended).** Model `openrouter/z-ai/glm-5.2`, key =
   `OPENROUTER_API_KEY`. LiteLLM has native OpenRouter support, so no `api_base`
   is needed — the `openrouter/` prefix selects the route. One key, one gateway,
   and the same path swaps to any other OpenRouter-hosted model by changing the
   model string.
2. **Direct to Z.ai (Zhipu).** LiteLLM `zai/glm-5.2` (or `api_base =
   https://api.z.ai/api/coding/paas/v4` for the coding plan). Use this to hold a
   Zhipu key directly and skip the gateway.

**Verification item before build:** confirm OpenRouter exposes `z-ai/glm-5.2`
and that it advertises **tool/function calling** (the GLM-4.x line does; confirm
for 5.2), since the whole loop depends on tool calls.

## What is generic (the harness) vs project (the coach)

This separation *is* the reusability claim, so it is stated as a contract.

**Generic — lives in the harness package, zero megaminx knowledge:**

- **Model factory** — builds a Pydantic AI model from config (the LiteLLM seam).
- **Runner** — `run_turn(session_id, user_input, attachments=…) -> Reply`;
  loads prior message history from SQLite, runs the agent, persists the new
  messages, usage, and tool calls. Sync + async variants.
- **Tool registry / protocol** — a project exposes a `tools(registry)` hook;
  tools are functions taking `RunContext[Deps]`. The harness registers them and
  enforces a per-run tool-iteration cap.
- **Persistence layer** — SQLite schema + a thin repository (no ORM): sessions,
  messages (Pydantic AI `ModelMessage` JSON via its `ModelMessagesTypeAdapter`),
  tool_calls, usage/cost, attachments (blobs or paths). Enables resume, replay,
  and audit.
- **Config** — `pydantic-settings`: model id, api_base, api-key env var,
  temperature, max tool iterations, budget cap, db path, log level.
- **Observability + cost** — structured per-turn logging; LiteLLM cost callback
  writes spend per session; optional Pydantic Logfire toggle.
- **CLI** — `python -m harness chat --session …` for quick driving of any
  project's agent; a thin REPL that calls `run_turn`.

**Project — supplied by each consumer (the megaminx coach is consumer #1):**

- **`Deps`** dataclass — what tools need (for the coach: the `Puzzle`/`Minx`
  engine handle, current 132-sticker state, stage).
- **Tools module** — the local functions (for the coach, backed by `minx/`):
  `apply_alg`, `find_piece`, `render_state` (SVG of a hold), `validate_state`,
  `describe_effect`. These mirror the tool set the coach specs already named.
- **System prompt provider** — for the coach, built from the booklet's stage
  text + recovery notes (the `coach_kb` extraction from the static-site spec is
  the content source; the harness just consumes a prompt string/builder).
- **Output model** — a Pydantic model the agent must return (for the coach:
  kid-voiced diagnosis + exact hold + sequence + rep count + optional SVG ref).

## Architecture

```
        project supplies ─┐                        ┌─ harness owns
                          ▼                        ▼
  ┌─────────────┐   ┌──────────────────────────────────────────┐
  │ Deps        │   │  Runner.run_turn(session, input, attach)  │
  │ Tools(fns)  │──▶│   1. load history  ◀───────┐              │
  │ SystemPrompt│   │   2. Pydantic AI Agent loop │  SQLite      │
  │ OutputModel │   │        ├─ tool calls (local fns)  (sessions,
  └─────────────┘   │        └─ structured output │   messages,  │
                    │   3. persist messages+usage─┘   tool_calls,│
                    │                                  usage)     │
                    └───────────────┬──────────────────────────┘
                                    │ model calls
                                    ▼
                       LiteLLM (provider seam)
                                    │
                                    ▼
                OpenRouter  →  z-ai/glm-5.2   (swappable by config)
```

The coach is then ~a few hundred lines: define `Deps`, write the five
simulator-backed tools, point the system prompt at `coach_kb`, declare the
`CoachReply` output model, and call the harness. Everything about *driving the
model* is inherited.

## Repo layout

Keep `minx` stdlib-only; the harness is a separate package with its own extras.

```
harness/                     # NEW generic package (its own optional deps)
  __init__.py
  config.py                  # pydantic-settings: model, api_base, keys, caps
  model.py                   # LiteLLM seam -> Pydantic AI model factory
  runner.py                  # run_turn: history -> agent -> persist
  tools.py                   # registry/protocol for project tool modules
  store.py                   # SQLite schema + repository (stdlib sqlite3)
  cli.py                     # python -m harness chat
coach/                       # NEW megaminx consumer of the harness
  deps.py                    # Deps: Puzzle/Minx state + stage
  tools.py                   # apply_alg, find_piece, render_state, validate, describe_effect
  prompt.py                  # system prompt from coach_kb
  reply.py                   # CoachReply output model
minx/                        # UNCHANGED, still pure-stdlib oracle
build/  tests/  docs/        # unchanged
```

`pyproject.toml`: add a `[project.optional-dependencies]` `harness` extra
(`pydantic-ai`, `litellm`, `pydantic-settings`) — analogous to today's
`booklet = ["weasyprint"]`. The `minx` core keeps `dependencies = []`. Code
stays MIT; booklet-derived prompt content stays CC BY 4.0 (the prompt builder
*reads* content, it doesn't relicense it).

## SQLite schema (sketch)

```
sessions(id, project, created_at, model, system_prompt_hash, meta_json)
messages(id, session_id, idx, role, content_json, created_at)   -- Pydantic AI ModelMessage JSON
tool_calls(id, session_id, message_id, tool_name, args_json, result_json, ok, ms)
usage(id, session_id, message_id, prompt_tokens, completion_tokens, cost_usd, model)
attachments(id, session_id, kind, path_or_blob, mime, created_at)
```

Message history round-trips through Pydantic AI's `ModelMessagesTypeAdapter`
(dump on persist, validate on load), so resume/replay are exact.

## Testing strategy

- **Harness, no network:** a fake/stub Pydantic AI model (Pydantic AI's
  `TestModel`/`FunctionModel`) drives the loop deterministically — assert tool
  dispatch, the iteration cap, structured-output validation, and that
  persistence round-trips message history and usage. Fast, offline, in CI.
- **Coach tools, no model:** call each tool directly against `minx/` and assert
  simulator truths (e.g. a suggested sequence really solves the described case
  and leaves marked pieces intact — reusing the solver's `assert_solved_intact`
  spirit). This is the "the coach can't hallucinate a broken alg" guarantee.
- **Live smoke (manual/opt-in, gated by a key env var):** one real glm-5.2 turn
  through OpenRouter to confirm tool-calling and the output schema bind end to
  end. Kept out of the default `python3 -m tests.test_puzzle` run.

## Build phases

1. **Harness core (offline).** `config`, `model` factory (LiteLLM →
   Pydantic AI), `store` (SQLite + repo), `runner.run_turn`, tool registry, CLI.
   Driven entirely by `TestModel` in tests — no provider needed to land it.
2. **Provider bring-up.** Wire the default OpenRouter/glm-5.2 config; live
   smoke test behind an env-gated flag; confirm tool calling + structured output
   over the OpenAI-compatible surface. Document the Z.ai-direct alternative.
3. **Coach consumer.** `Deps`, the five `minx`-backed tools, `CoachReply`,
   system prompt from `coach_kb` (depends on the booklet-content split from the
   static-site spec — coordinate or stub the prompt until that lands). Tool-level
   correctness tests against the simulator.
4. **Integration + cost.** Persisted sessions, usage/cost accounting, replay;
   wire the coach into whatever surface ships (the static site's `/api/coach`
   path, or the CLI for a first field test with Freddie).

## Decisions needed from you (before phase 1)

1. **Packaging:** in-repo `harness/` package now (recommended; fastest, can be
   extracted to its own repo later) vs. a separate repo from day one.
2. **Keep LiteLLM given it's partly redundant with OpenRouter's
   OpenAI-compat?** Recommended **yes**, isolated to `model.py`, for the
   multi-provider swap + cost callbacks; it's cheap to drop later if unused.
3. **Async or sync runner first?** Recommended sync for the CLI/first field
   test; add async when a web surface needs it.
4. **`glm-5.2` confirmed on OpenRouter with tool calling?** Needs a quick live
   check (phase 2); name the fallback model (e.g. a GLM-4.x or Claude) if not.

## Out of scope

Streaming UI specifics, the static site / auth / deploy (covered by the coach
specs), multi-user accounts, MCP (explicitly avoided — tools are in-process),
and any change to the `minx` simulator, the solver, or the booklet pipeline.
