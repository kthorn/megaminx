# Megaminx Solution Guide

A kid-friendly, picture-based solving guide for the megaminx, in the style of
the official Rubik's 2010 *Solution Guide* booklet — plus the geometric
megaminx simulator used to prove every algorithm and diagram in it.

**[Download the booklet PDF](Megaminx_Solution_Guide.pdf)** (15 pages).

## Why this exists

Many online megaminx guides contain algorithms that don't actually work on a
megaminx (the classic Niklas is literally the identity; a plain Sune leaks
into lower layers). Every sequence, case rule, and diagram in this booklet was
executed and verified on a computer model of the puzzle: each insertion is
checked to leave previously-solved pieces intact, and the diagrams are
rendered directly from simulator states, so they are correct by construction.

## Also in this repo

The same idea — a geometric simulator that proves a kid-friendly booklet — now
covers two more puzzles:

- **Kilominx** (the corners-only megaminx): `minx/method_kilo.py`,
  `build/guide_kilo.py`, `tests/test_kilo.py`.
- **4×4 Rubik's cube**, solved by *reduction* (build the centers, pair the
  edges, then solve it exactly like a 3×3, plus the two parity fixes a 3×3 never
  needs): `minx/cube*.py`, `minx/method_cube.py`, `build/guide_cube.py`,
  `tests/test_cube.py`. The cube is a different solid, so it has its own
  cube-derived move engine, but reuses the shared SVG renderer and booklet
  framework.

## Layout

- `minx/` — the simulators: the dodecahedron move engine (`puzzle.py`,
  `geometry.py`) shared by the megaminx/kilominx, the **cube** engine
  (`cube.py`, `cube_geometry.py`, `cube_pieces.py`), the shared SVG renderer
  (`render.py`), and the scripted solvers (`method.py`, `method_kilo.py`,
  `method_cube.py`) that execute each booklet's exact method.
- `build/make_guide.py`, `build/guide_kilo.py`, `build/guide_cube.py` +
  `build/guide.css` — generate the booklets (HTML → weasyprint → `out/*.pdf`).
- `tests/` — simulator invariants and solver proofs
  (`python3 -m tests.test_puzzle` / `test_kilo` / `test_cube`).

## Building

Requires Python 3.13+ with `weasyprint`:

```sh
python3 build/make_guide.py   # megaminx -> out/guide.pdf
python3 build/guide_cube.py   # 4x4 cube -> out/guide_cube.pdf
```

## License

- **Code** (`minx/`, `build/`, `tests/`): [MIT](LICENSE)
- **Booklet** (`Megaminx_Solution_Guide.pdf`, `out/guide.pdf`, and the
  rendered booklet content): [CC BY 4.0](LICENSE-BOOKLET)
