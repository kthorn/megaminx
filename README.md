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

## Layout

- `minx/` — megaminx simulator: dodecahedron-derived move engine
  (`puzzle.py`, `geometry.py`), SVG renderer (`render.py`), and `method.py`,
  a scripted solver that executes the booklet's exact method stage by stage.
- `build/make_guide.py` + `build/guide.css` — generates the booklet
  (HTML → weasyprint → `out/guide.pdf`); `build/diag_stage6_fast.py` is the
  harness that simulates a reader following the printed instructions
  literally, used to find and fix gaps in the text.
- `tests/test_puzzle.py` — simulator invariants
  (`python3 -m tests.test_puzzle`).

## Building

Requires Python 3.13+ with `weasyprint`:

```sh
python3 build/make_guide.py   # writes out/guide.pdf
```

## License

- **Code** (`minx/`, `build/`, `tests/`): [MIT](LICENSE)
- **Booklet** (`Megaminx_Solution_Guide.pdf`, `out/guide.pdf`, and the
  rendered booklet content): [CC BY 4.0](LICENSE-BOOKLET)
