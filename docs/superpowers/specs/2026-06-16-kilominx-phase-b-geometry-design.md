# Kilominx Phase B — Geometry

**Date:** 2026-06-16
**Parent design:** `docs/superpowers/specs/2026-06-13-kilominx-design.md`
(Phase A — the instance-based shared core, `PuzzleSpec`, `BaseSolver`/`Solution`
— is complete and merged. This document refines that umbrella spec's **Phase B**
into an implementable unit.)

## Goal

Make `KILOMINX = Puzzle(KILOMINX_SPEC)` build a correct 72-sticker simulator,
proven by a new `tests/test_kilo.py`. Phase B is deliberately narrow: it adds
**one geometry function plus a test module**. Everything downstream of geometry
— `Puzzle`, `pieces.build_pieces(has_edges=False)`, `_layer_indices`,
`_perm_for`, `name_faces` — is already puzzle-agnostic and handles the kilominx
without change. `KILOMINX_SPEC` already exists (added in Phase A); the only thing
stopping `Puzzle(KILOMINX_SPEC)` from building today is the `kite_circular`
branch in `geometry.build`, which currently raises `NotImplementedError`.

## What changes

1. Implement `geometry._subdivide_kite_circular`, replacing the
   `NotImplementedError` branch in `geometry.build`.
2. Add `tests/test_kilo.py` with the kilominx geometry + move-engine invariants.

No other module is touched. The megaminx `edge_parallel` path is untouched.

## The kite subdivision

A kilominx is the edges-removed megaminx: 12 fixed colored centers, **no edge
pieces**, and corner pieces enlarged so they meet each other along the
edge-midlines. Each face shows **5 four-sided (kite) corner tiles** meeting at
the face center C, with a small colored center sticker capping the middle.

`_subdivide_kite_circular(spec, fi, fverts, centroid, stickers)` appends stickers
for one face in this exact order, so `id_to_idx` and `pieces` grouping stay
consistent with the megaminx convention (center first, then corners by index):

- **1 center sticker** — `Sticker(fi, 'center', 0, poly)`.
  `poly` = the face pentagon scaled toward C by `spec.cut_fraction` (0.42):
  `[C + (V_k − C) * cut_fraction for k in 0..4]`. Its centroid is exactly C
  (the face centroid lies on the face normal through the origin), so the center
  maps onto itself under that face's 72° turn. The small pentagon is geometry
  only; rendering it as a circle is a Phase D concern. **Modeling decision
  (confirmed 2026-06-16): the cap is cosmetic — the corner kites still extend to
  C beneath it; we do not carve a real central pentagon out of the face.**

- **5 corner kites** — `Sticker(fi, 'corner', ci, poly)` for `ci` in `0..4`.
  Kite `ci` = `[V_ci, M_ci, C, M_(ci−1)]` where
  - `V_ci = fverts[ci]` (a dodecahedron vertex),
  - `M_ci` = midpoint of the face edge `(fverts[ci], fverts[(ci+1) % 5])`,
  - `M_(ci−1)` = midpoint of edge `(fverts[(ci−1) % 5], fverts[ci])`,
  - `C = centroid` (the face center).

  The 5 kites tile the whole pentagon down to C with no gaps and no overlap
  (each is the quadrilateral bounded by vertex `ci`, its two incident edge
  midpoints, and the center). The cosmetic center cap is drawn over their inner
  tips in Phase D.

Keying corner `ci` at vertex `fverts[ci]` is **identical to the megaminx**
(`pieces.build_pieces` groups corners by `_key(fverts[s.index])`), so the three
kite tiles meeting at each shared dodecahedron vertex group into one corner
piece. Result per face: `1 + 5 = 6` stickers → **72 stickers total**; pieces:
**20 corners (3 tiles each) + 12 single-sticker centers, zero edges.**

### Why the move engine is correct by construction

No move code changes. `Puzzle._layer_indices(fi)` selects the
`spec.layer_size = 16` stickers deepest along the face normal: the face's own 6
(center + 5 kites) plus the 2 kite tiles each of the 5 neighbors contributes to
that vertex ring (`6 own + 10 strip`). `_perm_for` then finds the 72° rotation
permutation by nearest-centroid matching within that layer — exactly the
megaminx mechanism, minus the edges. The center's centroid sits at C (maximal
depth, on-axis, fixed by the rotation); the 15 surrounding kite centroids cycle
among themselves. The existing depth-gap assertion in `_layer_indices`
(`dk − dk1 > 0.05`) is the in-build proof that the 16-sticker layer is cleanly
separated from the rest; if the kilominx geometry produced an ambiguous cut the
build would fail loudly rather than silently mis-permute.

## Tests — `tests/test_kilo.py`

Geometry and move-engine invariants only. **The solver and any `solve()` fuzz
are Phase C and are explicitly not in this module yet.** Built as a plain
`main()` that prints an OK line, matching `tests/test_puzzle.py`'s style.

- **Sticker counts:** `KILOMINX.n_stickers == 72`; exactly 12 `center` stickers
  and 60 `corner` stickers; **zero** `edge` stickers.
- **Piece counts:** 20 corner pieces, each grouping 3 tiles; 12 centers;
  `KILOMINX.edges == {}` (no edge pieces).
- **Center fixity:** each face's center sticker is unmoved by that face's turn,
  and unmoved by all 5 repeats.
- **Order-5 turns:** for every face, `turn(fi)` applied 5 times is the identity
  on the full state.
- **Layer shape:** each face's layer has 16 stickers split `6 own + 10 strip`
  (own = stickers whose `.face == fi`); the `_layer_indices` depth-gap assert
  holds for all 12 faces (covered simply by `Puzzle(KILOMINX_SPEC)` building).
- **Move-engine composition:** a commutator / "sexy"-style sequence
  (e.g. `R U Ri Ui` analog in named-face notation) returns to solved after the
  appropriate number of repeats, parallel to the megaminx engine check — a
  smoke test that named turns compose and invert correctly on the kilominx.

## Regression gate

`python3 -m tests.test_puzzle` (megaminx invariants) must still print its OK
line unchanged. The kilominx branch is additive — the `edge_parallel` path is
not edited — so this should hold trivially, but it is the stated gate for the
phase.

## Out of scope (assigned elsewhere by the parent design)

- **Render circle** for `center_shape == 'circle'` — Phase D (booklet).
- **`method_kilo.py`** and any `solve()` proof-over-scrambles fuzz — Phase C.
- **Kilominx booklet** (`guide_kilo.py`) — Phase D.

## Done when

- `Puzzle(KILOMINX_SPEC)` builds; `KILOMINX` is importable.
- `python3 -m tests.test_kilo` prints its OK line.
- `python3 -m tests.test_puzzle` still prints its OK line.
