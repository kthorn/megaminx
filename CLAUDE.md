# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A picture-based megaminx solving booklet (in the style of the official Rubik's
2010 *Solution Guide*) **plus** the geometric simulator that proves every
algorithm and diagram in it. The whole point: each sequence, case rule, and
diagram is executed on a computer model and verified to leave previously-solved
pieces intact, so the booklet is correct by construction (many online megaminx
guides contain algorithms that simply don't work).

## Commands

```sh
python3 -m tests.test_puzzle     # simulator invariants (the test suite); prints "all simulator invariants: OK"
python3 build/make_guide.py      # build the booklet: out/guide.html + out/guide.pdf
```

- Run everything from the repo root (modules are imported as `minx.*` and
  `tests.*`; there is no installed package).
- `build/make_guide.py` needs **Python 3.13+** with `weasyprint`.
- There is no pytest config despite the `.pytest_cache/` dir — tests are a plain
  `main()`. The diagnostic harnesses under `build/diag_*.py` take CLI args
  (e.g. `python3 build/diag_stage6.py 300` runs 300 white-face seeds).

## Architecture

Everything derives from one real 3D dodecahedron model — adjacency and move
permutations are never hand-coded. Read the layers bottom-up:

1. **`minx/geometry.py`** — builds the dodecahedron: 12 face normals, and each
   face clipped (Sutherland–Hodgman) into 11 sticker polygons (1 center, 5 edge,
   5 corner) at `CUT_FRACTION` depth. `build()` returns `(normals, faces,
   stickers)`. Stickers carry a 3D `centroid`, which is the key to everything above.

2. **`minx/puzzle.py`** — state + move engine. A `Minx` is a flat list of 132
   sticker colors. A face turn is a 72° rotation about the face normal; the
   permutation is found by **nearest-centroid matching** of rotated stickers
   (`CW_PERMS`), so moves are correct by construction. Also derives face
   adjacency (`ADJ`), opposites (`OPP`), and `name_faces(u, f)` which maps a
   physical hold (U on top, F in front) to human names `U F R L BR BL D DR DL`.
   `parse_alg`/`apply_alg` run move strings like `"R U Ri U R U2i Ri"` (`i` =
   inverse, digit = repeat count, fifth-turns).

3. **`minx/pieces.py`** — groups the 132 stickers into the 20 corner + 30 edge
   physical pieces (by shared vertex / edge-midpoint). `describe_effect(alg,
   names)` reports which pieces an algorithm moves/twists — the tool used to
   validate that an insertion doesn't disturb solved pieces.

4. **`minx/method.py`** — the booklet's solving method, executed in the sim. The
   `Solver` class runs stages (white star → corners → edge bands → last layer)
   via `solve()`. Each insertion picks a **grip** (local face naming) and
   verifies in-sim that no piece in `self.solved` is net-disturbed
   (`assert_solved_intact`); `solve()` raises `MethodError` if no safe insertion
   exists, so **a passing run is a proof the method works on that scramble**.
   `scramble(m, n, seed)` makes test positions.

5. **`minx/render.py`** — orthographic SVG views drawn straight from a `Minx`
   state, in the booklet's visual style. `color_map(white, front)` assigns the
   standard color scheme.

6. **`build/make_guide.py`** — assembles the booklet HTML (one `stageN()`
   function per page group), rendering every diagram from a simulator state, then
   `weasyprint` → `out/guide.pdf`. `build/guide.css` is the print stylesheet.
   `build/diag_*.py` are throwaway analysis harnesses that simulate a reader
   following the printed text literally, used to find gaps in the wording
   (`diag_stage6_fast.py` generates legal stage-6 start states directly instead
   of solving stages 1–5).

### The canonical invariant

`tests/test_puzzle.py:canonical_hold()` defines the fixed hold used everywhere
(U = face most +z, F = its neighbor most −y). The sim (`name_faces`), renderer
(`color_map`), and booklet (`make_guide.py`) all share this naming, which is why
a diagram, an algorithm, and the solver agree.

## Conventions

- Vector math is bare tuples with `_dot`/`_cross`/`_norm` helpers in
  `geometry.py`; there is no numpy dependency.
- Float comparisons use explicit epsilons (e.g. `< 1e-6`) and `assert`s guard
  geometric assumptions — keep those when refactoring; they are how "correct by
  construction" is enforced.
- After changing anything in `minx/`, run `python3 -m tests.test_puzzle` and
  rebuild the guide; the booklet only stays correct because it re-renders from
  the sim on every build.

## Licensing

Code (`minx/`, `build/`, `tests/`) is MIT; the booklet output is CC BY 4.0 —
keep new code vs. rendered-content separation in mind.
