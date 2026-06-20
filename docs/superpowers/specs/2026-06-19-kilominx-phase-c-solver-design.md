# Kilominx Phase C — Solver

**Date:** 2026-06-19
**Parent design:** `docs/superpowers/specs/2026-06-13-kilominx-design.md`
(Phases A and B are complete: the instance-based `Puzzle(spec)` core +
`BaseSolver`/`Solution`, and the kilominx kite geometry. `KILOMINX` builds and
its simulator invariants pass.)

## Goal

A verified layer-by-layer kilominx solver: `minx/method_kilo.py` with a
`KiloSolver(BaseSolver)` that `solve()`s any scramble, recording a structured
`Solution`, and raising `MethodError` if any stage cannot find a safe
insertion — so a fuzz run over many seeds is a proof the method works.

## Key decision: two parallel solvers (not a shared corner abstraction)

Agreed 2026-06-19. `method_kilo.py` is written fresh alongside
`method_mega.py`, **not** by extracting the megaminx's corner machinery into a
shared base. Rationale:

- **The reusable substrate is already shared.** `BaseSolver` already provides
  both puzzles the move-perm hot path (`_apply`), `bfs_to`, `ferry`,
  `try_insert`, `mark`, `assert_solved_intact`, `free_faces`, and per-step
  `Solution` recording (`begin_step`/`end_step`). `KiloSolver` uses all of these.
- **The megaminx's corner choreography is complex *because of edges*.**
  `righty_corner`/`_eject_corner` do an elaborate stage-and-eject dance to avoid
  disturbing solved *edges* — pieces the kilominx does not have. Forcing the
  kilominx through that machinery would import complexity it does not owe; the
  kilominx's corner insertion is materially simpler.
- **Weak regression net for the megaminx solver.** The megaminx full-solve is
  proven only by the slow manual `build/diag_*.py` harnesses; nothing in the
  fast suite would catch a regression from refactoring `method_mega`. Leaving it
  untouched is the safe choice.

**What is shared:** the algorithm *constants* `RIGHTY` and `CORNER_CYCLE` move
to `minx/solver.py` as module constants, imported by both `method_mega` and
`method_kilo`, guaranteeing the two booklets teach identical moves. This is the
**only** change to `method_mega.py`: it imports the two constants instead of
defining them locally. The string *values* are unchanged, so megaminx behavior
is identical; `tests/test_core` and `tests/test_solver_opt` (which import and
exercise `method_mega`) plus a manual `diag` spot-check cover this trivial edit.

## What changes

| File | Change |
|---|---|
| `minx/solver.py` | Add module constants `RIGHTY = "Ri DRi R DR"` and `CORNER_CYCLE = "Ri BRi R BR Ri Fi R BRi Ri BR F R"`. No logic change. |
| `minx/method_mega.py` | Replace the local `RIGHTY`/`CORNER_CYCLE` definitions with `from .solver import RIGHTY, CORNER_CYCLE`. Behavior-preserving. |
| `minx/method_kilo.py` | **New.** `KiloSolver(BaseSolver)` + `scramble()` helper. |
| `tests/test_kilo.py` | Extend with a `KiloSolver.solve()` fuzz over N seeds. |
| `build/diag_kilo.py` | **New.** CLI harness for heavier manual sweeps (`python3 build/diag_kilo.py 500`), mirroring `build/diag_*.py`. |

## KiloSolver structure

The 20 corners form four rings of 5. With white on top:

1. **`white_corners`** — top ring (white + 2 band1 faces).
2. **`upper_ring`** — 2 band1 + 1 band2 face.
3. **`lower_ring`** — 1 band1 + 2 band2 faces.
4. **last layer** (gray up) — `ll_permute` then `ll_orient`.

### Stages 1–3: righty insertion

Each of the 15 non-last-layer corners is inserted by the booklet's pedagogy:
bring the corner to the staging vertex directly below its slot (using the shared
`ferry`/`bfs_to` over `free_faces`), then repeat `RIGHTY` (grip from
`puzzle.name_faces` at the slot) until it is seated. `try_insert` selects a safe
grip; `assert_solved_intact` guards already-placed corners after every
insertion. If a corner is stuck in a solved-region slot it is ejected with one
`RIGHTY` at its current location (a small kilominx-local eject, far simpler than
the megaminx's because there are no edges to preserve). A stage raises
`MethodError` if no safe insertion exists.

Slot classification per ring uses the same band membership the megaminx uses
(`self.band1` = `puzzle.adj[white]`, `self.band2` = the middle faces), via
`puzzle.corner_slots` keyed by sorted color tuple.

### Stage 4: last layer — permute then orient

Confirmed pedagogy (2026-06-19): **permute first, then orient**, matching the
megaminx booklet and reusing `RIGHTY` for orientation (no new algorithm for the
reader).

- **`ll_permute`** — greedily apply `CORNER_CYCLE` from the best last-layer grip
  (and best gray pre-spin) until all 5 gray corners sit in their correct slots
  (orientation ignored). Mirrors `method_mega.ll_corners_position`.
- **`ll_orient`** — hold one mis-oriented corner in the front-right slot, repeat
  `RIGHTY` until its gray sticker faces correctly, then turn **only** the gray
  face to bring the next bad corner into position; repeat. A final gray turn
  realigns. Mirrors `method_mega.ll_corners_orient`. Raises `MethodError` if the
  end state is not solved.

### `solve()` and the `Solution` contract

`solve()` runs the four stages, wrapping each in `begin_step(stage)` /
`end_step()` so the returned `Solution` carries `(stage, hold_text, moves,
state_after)` per step — the same coach-API contract `method_mega` produces. It
asserts `assert_solved_intact` after each stage and raises if the final state is
not solved. Stage names: `white-corners`, `upper-ring`, `lower-ring`,
`ll-permute`, `ll-orient`.

A module-level `scramble(m, n=40, seed=None)` mirrors `method_mega.scramble`.

## Testing & proof

- **Fuzz proof in `tests/test_kilo.py`:** solve N scrambled seeds end-to-end;
  each must finish with `m.is_solved()` and never raise `MethodError`. The
  kilominx is small (72 stickers, no edges, 4 corner stages), so this runs in
  the fast suite — unlike the megaminx full-solve. Target **N ≥ 50** in the
  suite (tuned so the suite stays fast); `build/diag_kilo.py` runs larger sweeps
  (e.g. 500+) manually.
- **Replayability:** at least one solved seed's `Solution` is replayed from a
  fresh scrambled cube — applying each step's `moves` reproduces that step's
  `state_after`, and the final replay equals the solved state (parallel to
  `tests/test_core.py:test_solver_records_replayable_steps`).
- **Regression gate — all four suites must stay green:** `test_puzzle`,
  `test_core`, `test_kilo`, `test_solver_opt`. (The full suite is four modules,
  not the single one CLAUDE.md names; the Phase B `test_core` breakage came from
  running too few.) A manual `python3 build/diag_kilo.py` and a megaminx
  `diag_*.py` spot-check confirm the shared-constant move did not disturb either
  solver.

## Out of scope (later phases)

- **Kilominx booklet** (`guide_kilo.py`) — Phase D.
- **Renderer circle-center cosmetic** — Phase D.
- **2×2-style (Ortega) last layer** and **no-dead-end BFS recovery** — future,
  per the umbrella design.

## Done when

- `python3 -m tests.test_kilo` passes including the solver fuzz (N ≥ 50 seeds).
- All four test suites green; `KiloSolver().solve()` returns a `Solution` and
  the megaminx solver is unchanged in behavior.
