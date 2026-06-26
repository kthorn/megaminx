# 4×4 Rubik's Cube — Solver + Booklet — Design

**Date:** 2026-06-24
**Goal:** A 4×4 Rubik's cube solver and a kid-friendly, picture-based solution
booklet in the same spirit as the megaminx/kilominx guides — every algorithm
and diagram executed and verified on a geometric simulator, so the booklet is
correct by construction. The 4×4 reduces to a 3×3 and is then solved with the
same beginner method as the official 3×3 guide (`Rubiks.pdf`).

## Decisions (agreed with user)

- **Scope:** full stack end-to-end now — cube engine, 3×3 solver, 4×4 reduction
  solver, renderer, and the **4×4 booklet** (the 3×3 method is built as its
  final stages; no separate standalone 3×3 PDF).
- **Code organization:** new modules inside the existing `minx/` package. A cube
  is a different solid from the dodecahedron, so it gets its **own** geometry +
  move engine; it does *not* subclass the minx `Puzzle`. It exposes the same
  duck-typed attributes the renderer reads, so `minx/render.py` is reused
  unchanged. `Solution`/`Step` records and the booklet framework
  (`guide_common.py`, `guide.css`) are also reused.

## Engine

`minx/cube_geometry.py` + `minx/cube.py` build an N×N cube (N=3 and N=4 share
the code): 6 faces, each an N×N grid of square sticker polygons with 3D
centroids. A face/slab turn is a 90° rotation found by **nearest-centroid
matching** — the exact technique `minx/puzzle.py` uses for 72° minx turns — so
move permutations are never hand-coded. Notation supports outer turns
(`R R' R2`), wide turns (`Rw`), and inner slices (`2R`). `minx/cube_pieces.py`
groups stickers into cubies by 3D cubie position (8 corners, 24 wings, 24
centres for N=4).

## Method (`minx/method_cube.py`)

- **`Cube3Solver`** — beginner layer-by-layer: white cross → first-layer
  corners → middle edges → two-look last layer. First two layers use
  **verified, case-indexed insertion tables** (discovered + checked in-sim; a
  buried piece is first ejected to the top by a short bounded search that may
  not disturb solved pieces — the minx pattern). The last layer is finished by a
  two-look BFS over verified macro-algorithms (`F R U R' U' F'`, Sune, a pure
  corner 3-cycle, a pure edge 3-cycle, T-perm).
- **`Cube4Solver`** — reduction:
  1. **Centres** — a greedy progress search builds each face's 2×2 centre block
     while keeping finished faces intact.
  2. **Edge pairing** — a greedy search over **centre-preserving macros** (outer
     turns for setup + wide-move pairing primitives that leave every centre
     solved). The bulk "flip" primitives reach the last-two-edges case.
  3. **3×3 phase** — map the reduced cube onto a `CUBE3`, solve with
     `Cube3Solver`, and replay the outer-face moves on the 4×4.
  4. **Parity** — detect PLL parity (odd permutation) and OLL parity (an
     impossible 3×3 orientation) and apply the verified center- and
     pairing-preserving fixes.

Every solve asserts the cube ends solved, so a passing fuzz run **is** the proof
(`tests/test_cube.py`). The centre stage is the slow part (~10 s/solve); the
rest is sub-second.

## Renderer & booklet

`minx/render.py` is reused as-is (it only reads `normals`/`faces`/`stickers`).
`minx/cube_render.py` adds the standard colour scheme (white = first layer = D,
yellow = last layer = U) and camera helpers. `build/guide_cube.py` produces the
12-page 4×4 booklet (cover → parts → notation → centres → edge pairing → 3×3
stages → parity → back), every diagram rendered from a simulator state, output
`out/guide_cube.{html,pdf}`.

## Testing

`tests/test_cube.py`: geometry/piece counts, every face turn⁴ = identity,
last-layer/parity algorithm effects, and `Cube3Solver`/`Cube4Solver` fuzz runs
asserted solved. `tests/test_guides.py` gains a 4×4 booklet smoke test. The
megaminx/kilominx suites stay green (only additive changes).

## Future / out of scope

- Faster centres (commutator macros instead of greedy search).
- A standalone 3×3 booklet (the method is built; only the page wrapper is
  missing).
- CFOP/advanced methods.
