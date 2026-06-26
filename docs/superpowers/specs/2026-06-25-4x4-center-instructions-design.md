# 4×4 Center Instructions — Design

Date: 2026-06-25
Scope: `build/guide_cube.py` (centers page) + `tests/test_cube.py`

## Problem

`build/guide_cube.py:centers_page()` (booklet page 3) is the only stage page
with **no verified move diagrams** — just three vague text tips. Every other
stage (white cross, corners, middle, yellow cross, last layer, parity) renders
a `demo` tile row from a simulator state. The solver builds centers via a
greedy BFS over inner-slice moves (`minx/method_cube.py:Cube4Solver.centers`),
so there was no fixed human algorithm to render — the booklet punted and only
described the idea, leaving readers without a concrete method.

## Goal

Add concrete, simulator-verified move diagrams for building the six 2×2
centers, matching the rest of the booklet's "correct by construction"
discipline (per `CLAUDE.md`: every diagram/sequence is executed on the sim and
verified).

## Verified algorithms (discovered and checked in-sim)

All four below were verified against `minx.cube.CUBE4`. "Corners home" means
every corner sticker is back at its home face after the sequence (true for the
inner-slice-only algs; the diagonal alg uses outer U/D turns so corners move,
which is fine — the centers stage does not depend on corners).

| Case | Setup (canonical) | Algorithm | Verified result |
|---|---|---|---|
| Join the second bar (complete a center) | U has a white bar on top; a second white bar sits in Front's right column | `2R` | slides the second bar up to complete the U center; corners home |
| Last two, column split | last two colors on U/D, swapped pairs in columns; four side centers solved | `2U2 2B2 2U2` | all six centers solved; corners home |
| Last two, row split | same, pairs in rows | `2U2 2L2 2U2` | mirror of the column case; all six solved; corners home |
| Last two, diagonal split | same, pairs diagonal | `U' 2R2 U' D' 2R2` | all six centers solved, four side centers intact (corners move — OK) |

## Changes

### 1. `build/guide_cube.py`

- **Rewrite `centers_page()`** (page 3): keep the "big idea" framing, add the
  step-by-step bar method in prose (make a 2×1 bar on a side face → slide it up
  with the adjacent inner slice → park the finished face on top/bottom →
  repeat for all but two faces), plus one verified `demo` of the "join the
  second bar" move (`2R`) rendered from a canonical setup state where U already
  has one white bar and Front holds the second.
- **Add `last_two_centers_page()`** (new page): the genuinely non-obvious
  finale. Verified tile demos of the column case (`2U2 2B2 2U2`) and the
  diagonal case (`U' 2R2 U' D' 2R2`); a one-line note that the row case is the
  mirror (`2U2 2L2 2U2`). Two camera views (top and bottom) so both unsolved
  faces are visible.
- **Insert the new page** into `assemble()` between `centers_page()` and
  `edges_page()`; renumber subsequent pages.
- **Enhance `tiles()`** so inner-slice moves (`2R`, `2U2`, …) render the cube
  state as a picture (without an arrow) instead of a text-only movebox. The
  reader sees the centers change under each slice. This also improves the
  parity page. Mirrors the existing arrow-less fallback path; low risk.

### 2. `tests/test_cube.py`

- **Add `test_center_algs()`** asserting all four algorithms above do exactly
  what is claimed:
  - bar lift: after setup + `2R`, the U center holds a 2×1 bar of the bar
    color, with corners at home;
  - column / row: after setup + the algorithm, all six centers are solved,
    the four side faces' centers stay solved, and corners are home (inner-slice
    only).
  - diagonal: after setup + the algorithm, all six centers are solved and the
    four side faces' centers stay solved (corners are NOT asserted — the alg
    uses outer U/D turns).
- A passing `python3 -m tests.test_cube` run is the proof the new pages are
  correct; the booklet re-renders from the same verified sequences.

## Out of scope

- The edges page stays as-is. (Centers were the reported gap; edges can be
  upgraded later on request.)

## Verification

- `python3 -m tests.test_cube` passes (includes the new `test_center_algs`).
- `python3 build/guide_cube.py` rebuilds `out/guide_cube.{html,pdf}` with the
  two new pages and no broken diagrams.
- Page numbers continue consecutively after the inserted page.
