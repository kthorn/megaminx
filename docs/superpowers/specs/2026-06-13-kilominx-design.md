# Kilominx — Design

**Date:** 2026-06-13
**Goal:** A parallel set of tools and algorithms for the **kilominx** (the
corners-only megaminx — the dodecahedral analog of the 2×2 pocket cube),
matching what the megaminx already has: a geometry-derived simulator, a
verified layer-by-layer solver, an SVG renderer, and a kid-friendly printed
booklet — all rendered/proved from the simulator so they are correct by
construction.

## Decisions (agreed 2026-06-13)

- **Scope:** full parallel stack **including** a printed booklet PDF.
- **Code organization:** an instance-based **shared core**, not a duplicated
  package. Everything puzzle-agnostic is shared; only the solver, the booklet
  content, and a small per-puzzle spec differ. (Pressure-tested "generalize"
  vs. "extract primitives" — they collapse to the same boundary: the shared
  part includes the entire move engine, piece model, renderer, and booklet
  framework; the only genuinely per-puzzle code is the solver and booklet
  pages.)
- **Solving method:** layer-by-layer, parallel to the megaminx booklet's
  pedagogy (same "righty" commutator feel). The 2×2-style (Ortega) last-layer
  method is recorded as a **future** alternative, not built now.
- **Solver interface:** both solvers sit on a shared `BaseSolver` and return a
  structured `Solution` record, so the planned Megaminx Coach site
  (`docs/superpowers/specs/2026-06-11-megaminx-coach-site.md`) can consume
  either puzzle's solver uniformly. This also delivers the coach site's
  "record the concrete turn list per step" hardening item for the megaminx
  for free.

## What changes vs. today

Today `minx/puzzle.py` builds **module-level globals** (`NORMALS`, `FACES`,
`STICKERS`, `LAYERS`, `CW_PERMS`) at import — fine for one puzzle, impossible
for two simultaneously. The core refactor promotes that into a `Puzzle`
**instance** built from a `PuzzleSpec`. Every consumer (`pieces`, `render`,
the solvers, the booklet builders) takes/holds a `Puzzle` instead of reaching
for module globals.

**Regression safety:** the existing `tests/test_puzzle.py` megaminx invariants
must still pass unchanged after the refactor. That is the proof the shipped
megaminx behavior is preserved.

## Target layout

```
minx/
  geometry.py    # shared primitives; build(spec) dispatches face-subdivision
  spec.py        # PuzzleSpec + MEGAMINX, KILOMINX configs
  puzzle.py      # Puzzle(spec) instance: NORMALS/FACES/STICKERS/LAYERS/CW_PERMS;
                 #   Minx state (+ turn history); name_faces/ADJ/OPP; parse_alg/apply_alg
  pieces.py      # corner grouping always; edge grouping only when spec.has_edges
  render.py      # unchanged logic; takes a Puzzle instance
  solver.py      # BaseSolver + Solution/Step records + shared corner primitives
  method_mega.py # megaminx Solver (refactored onto BaseSolver)
  method_kilo.py # kilominx Solver (new)
build/
  guide_common.py   # svg_img, page assembly, weasyprint driver (extracted)
  guide_mega.py     # megaminx booklet content (refactored from make_guide.py)
  guide_kilo.py     # kilominx booklet content (new)
tests/
  test_puzzle.py    # megaminx invariants (unchanged)
  test_kilo.py      # kilominx invariants (new)
```

> Naming note: existing `build/make_guide.py` is split into `guide_common.py`
> (framework) + `guide_mega.py` (content). If keeping the old entry-point name
> matters, `make_guide.py` can stay as a thin shim that calls `guide_mega.py`.

## PuzzleSpec

A ~10-line config per puzzle. Fields:

| Field | Megaminx | Kilominx | Used by |
|---|---|---|---|
| `name` | `"megaminx"` | `"kilominx"` | labels, output paths |
| `has_edges` | `True` | `False` | `geometry.build`, `pieces` |
| `subdivision` | edge-parallel cut, `fraction=0.42` | kite/center-pentagon, `center_scale` (tuned so corners meet at edge midpoints) | `geometry.build` |
| `layer_size` | `26` | `16` | `_layer_indices` (replaces the hardcoded `26`) |
| `color_ring` | `['red','blue','yellow','purple','green']` | same | `render.color_map` |

`MEGAMINX = Puzzle(MEGAMINX_SPEC)` and `KILOMINX = Puzzle(KILOMINX_SPEC)`.

## Kilominx geometry (the one genuinely new piece)

- **72 stickers:** each face = 1 central pentagon + 5 corner "kites" (no edge
  stickers). Total pieces: 20 corners (3 stickers each) + 12 single-sticker
  centers.
- **Face subdivision differs from the megaminx's edge-parallel cuts.** On a
  kilominx the corners meet at the **edge midpoints**; each corner kite is
  bounded by two half-edges and two segments running inward to a scaled
  central pentagon whose vertices point toward the edge midpoints; its single
  parameter is `center_scale` (how far those vertices sit from the face center,
  tuned so adjacent corners meet exactly at the edge midpoints). `build()`
  shares the dodecahedron construction, the `Sticker` class, and centroid
  computation, and branches **only** on this per-face subdivision step
  (selected by `spec.subdivision` / `spec.has_edges`).
- **Layer membership:** face F's layer = its 6 own stickers (center + 5
  corners) + 2 corner stickers on each of the 5 neighbors = **16**
  (`6 own + 10 strip`). `_layer_indices` uses `spec.layer_size`; the
  own/strip sanity assert becomes `6`/`10` (corners only).
- **Move engine unchanged:** the nearest-centroid permutation works as-is. A
  face turn rotates the center onto itself (5-fold symmetric) and cycles the
  corners.

## Solver core: `BaseSolver` + `Solution` contract

Shared in `minx/solver.py`, used by both puzzles:

- **Turn recording.** `Minx.turn` records to an optional history; `BaseSolver`
  captures the concrete move list per step. (Directly satisfies the coach
  site's hardening item #1 for the megaminx.)
- **`Solution` record** (puzzle-agnostic), the shape `POST /api/solve` wants:
  ```
  Solution = list[Step]
  Step = {
    stage:      str,            # e.g. "white-corners", "upper-ring"
    hold_text:  str,            # human grip, e.g. "gray bottom-right, pink front"
    moves:      list[(name, times)],   # raw turns in named-face notation
    state_after: list[int],     # sticker state for SVG frame rendering
  }
  ```
- **Shared corner primitives:** `assert_solved_intact`, righty insertion,
  eject, ferry, and bounded-BFS staging — these are corners-only today and
  reused by both solvers.
- **Hold/grip describer:** small helper on top of `name_faces` that turns a
  grip into `hold_text`.

`method_mega.py` refactors its `Solver` onto `BaseSolver` (gaining turn
recording + structured `Solution`); `method_kilo.py` is built on it from the
start, so both are coach-API-ready.

## Kilominx method (layer-by-layer, white on top)

The 20 corners sit in four rings of 5 (top face, upper-mid, lower-mid, bottom
face). Four stages:

1. **White corners** (top 5) — placed & oriented. No star stage (no edges).
2. **Upper-middle ring** (5) — inserted from the top via a righty-style
   commutator.
3. **Lower-middle ring** (5).
4. **Last layer** (gray bottom): **orient** the 5 corners (CO), then
   **permute** them (CP).

Same proof discipline as the megaminx: every insertion verifies that
previously-solved pieces survive; `solve()` raises `MethodError` if no safe
insertion exists. A passing run over many scrambles is a proof the method
works on those scrambles.

## Renderer & booklet

- **Renderer:** `render.py` is already puzzle-agnostic (it iterates whatever
  stickers exist and never distinguishes edge from corner). It only needs to
  take a `Puzzle` instance. Kilominx diagrams come for free.
- **Booklet:** `guide_kilo.py` produces a parallel kid-friendly PDF — cover →
  hold/notation → one page per stage (white corners, upper ring, lower ring,
  last-layer orient, last-layer permute) — every diagram rendered from a
  simulator state. Reuses `guide_common.py`, `guide.css`, and `render.py`.

## Testing & sequencing

- **`tests/test_kilo.py`** invariants: 72 stickers; 20 corners; each face's
  5× turn = identity; layer counts 6 own / 10 strip; sexy-move order; and a
  fuzz run of `KiloSolver.solve()` over N seeds (proof of the method).
- **`tests/test_puzzle.py`** (megaminx) must stay green throughout — the
  regression proof for the instance-based refactor.

**Phases:**

- **A — Instance-based refactor.** Promote module globals to `Puzzle(spec)`;
  add the `PuzzleSpec`; add turn recording + `BaseSolver`/`Solution`; refactor
  `method_mega.py` onto it. Gate: all megaminx tests green; the megaminx
  booklet rebuilds byte-comparable (or intentionally diff-reviewed).
- **B — Kilominx geometry.** Kilominx spec + the kite face-subdivision;
  `test_kilo.py` simulator invariants pass.
- **C — Kilominx solver.** `method_kilo.py` on `BaseSolver`, proven over
  scrambles; returns a `Solution`.
- **D — Kilominx booklet.** `guide_kilo.py` → kilominx PDF.

## Future / out of scope

- **2×2-style (Ortega) method** for the kilominx last layer — a documented
  alternative pedagogy to add later.
- **Coach-site integration** — building the website is out of scope here; this
  design only keeps the solver interface compatible with it.
- **No-dead-end hardening** (bounded-BFS recovery fallback so `solve()` never
  raises) — the coach site wants it for both puzzles; tackled with that work,
  not here.
```
