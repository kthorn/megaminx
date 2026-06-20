# Kilominx Phase D — Booklet

**Date:** 2026-06-19
**Parent design:** `docs/superpowers/specs/2026-06-13-kilominx-design.md`
(Phases A–C are complete: the shared `Puzzle(spec)` core + `BaseSolver`, the
kite geometry, and the verified `KiloSolver`. This is the final phase.)

## Goal

A kid-friendly, picture-based **kilominx solving booklet** (`out/guide_kilo.pdf`),
parallel to the existing megaminx guide, with every diagram rendered from a
`KILOMINX` simulator state so it is correct by construction. Built by extracting
the booklet framework now tangled inside `make_guide.py` into a shared module
both booklets use.

## Decisions (agreed 2026-06-19)

- **Framework reuse:** extract a shared `build/guide_common.py` (not a standalone
  duplicate). Pressure-tested against the Phase C "two parallel solvers" choice;
  it tilts the other way here because the booklet framework is pure presentation
  scaffolding with a strong DRY case and the project's licensing note already
  wants a code/content split.
- **Last-layer pedagogy:** permute-then-orient, matching Phase C's solver and the
  megaminx guide.
- **Scope:** 9 pages (cover, pieces/hold, notation, one page per the 5 solve
  stages, back page). No worked full-solve walkthrough.

## What changes

| File | Change |
|---|---|
| `build/guide_common.py` | **New.** Puzzle-agnostic booklet framework extracted from `make_guide.py`. |
| `build/make_guide.py` | Import the framework from `guide_common`; keep all megaminx page CONTENT unchanged in behavior. |
| `minx/render.py` | Draw the center sticker as a circle when `puzzle.spec.center_shape == 'circle'` (else unchanged). |
| `build/guide_kilo.py` | **New.** The kilominx booklet content → `out/guide_kilo.html` + `out/guide_kilo.pdf`. |
| `tests/test_guides.py` | **New.** Build-smoke test: the kilominx (and megaminx) HTML build runs and produces the expected pages + embedded SVG images. |

## 1. Framework extraction — `build/guide_common.py`

Move the puzzle-agnostic presentation helpers out of `make_guide.py`:

- **Pure string builders:** `svg_img`, `banner`, `tips`, `congrats`, `goal_box`,
  `F` (colored face letter), `colorword`.
- **`holding(text, puzzle_name)`** — gains a `puzzle_name` argument so it renders
  "Holding Your Kilominx:" / "Holding Your Megaminx:".
- **Page collection** — the current module-global `PAGES` list + `page()` become a
  small `Booklet` holder (`Booklet.page(body, number, cls)` appending to
  `self.pages`), so the two booklets never share page state.
- **Build driver** — the weasyprint HTML→PDF step, parameterized by output stem
  (`out/guide.*` vs `out/guide_kilo.*`) and CSS path; returns/writes the HTML and
  PDF. Reuses `build/guide.css`.

`make_guide.py` imports these and is otherwise behavior-preserving: its
megaminx-specific helpers (`piece_ids`, `tiles_html`, `picture`, `bright_for`,
`layer_ids`, the `CMAP`/`NAMES` setup) and every page function (`cover`,
`stage1`–`stage10`, `notation`, `backpage`) stay in `make_guide.py`.

**Regression gate:** rebuild the megaminx PDF and visually diff-review it. The
extraction may shift output incidentally; review and accept it deliberately
(the gate the umbrella design set for the Phase A refactor), not byte-identity.

## 2. Renderer circle cosmetic — `minx/render.py`

In `render()`, when drawing a sticker whose `kind == 'center'` and the puzzle's
`spec.center_shape == 'circle'`, emit an SVG `<circle>` (centered at the
projected center C, radius = the inset small-pentagon's apothem) instead of the
rounded polygon path. The megaminx (`center_shape == 'pentagon'`) path is
untouched. `render.py` stays puzzle-agnostic; the only new input is reading
`puzzle.spec.center_shape`. This makes kilominx diagrams read as a real kilominx
(round center cap, distinct from the kite corners).

## 3. The booklet — `build/guide_kilo.py`

Mirrors the megaminx guide's structure and visual style (same `guide.css`), but
shorter — the kilominx is corners-only and teaches just two algorithms,
`RIGHTY` ("Ri DRi R DR") and `CORNER_CYCLE`, the exact shared constants the
proven `KiloSolver` uses. Pages:

1. **Cover** — "KILOMINX".
2. **Get to know your kilominx** — the pieces (20 corners + 12 fixed centers, no
   edges) and the hold (white on top, gray on bottom).
3. **Notation** — each face turns a fifth (reuses the megaminx notation style).
4. **Stage 1 — White corners** (top ring) via `RIGHTY`.
5. **Stage 2 — Upper-middle ring** via `RIGHTY`.
6. **Stage 3 — Lower-middle ring** via `RIGHTY`.
7. **Stage 4 — Last layer: permute** the 5 gray corners (`CORNER_CYCLE`).
8. **Stage 5 — Last layer: orient** them (repeat `RIGHTY` + turn the gray top).
9. **Back page** — congratulations.

Each stage page mirrors the megaminx layout: a stage banner, a "Holding Your
Kilominx" line, the algorithm shown as a row of move-tiles (a puzzle picture
with a turn arrow per move), a before/after goal picture, and tips. Every
picture is rendered from a `KILOMINX` simulator state — built by applying a
setup/alg to a solved `KILOMINX.minx()` — so diagrams are correct by
construction. The booklet reads faces by their center color, as the megaminx
guide does.

The kilominx hold uses `white` and `gray` as the canonical top/bottom (the same
`canonical_hold()` convention the megaminx guide and tests share), so the color
scheme and diagrams agree with the simulator.

## 4. Output, testing & gate

- **Output:** `out/guide_kilo.html` + `out/guide_kilo.pdf` (megaminx keeps
  `out/guide.*`).
- **Build-smoke test (`tests/test_guides.py`, fast suite):** running the
  kilominx HTML build (the pre-weasyprint step) returns non-empty HTML
  containing the expected number of pages (9) and at least one embedded
  `<img ... data:image/svg+xml ...>`; likewise a smoke build of the megaminx
  HTML still succeeds (guards the framework extraction). PDF generation
  (weasyprint) stays a manual `python3 build/guide_kilo.py` step, mirroring how
  the megaminx PDF is not tested in the suite.
- **Correct by construction:** the two taught algorithms are the proven
  `KiloSolver` constants (Phase C: 50-seed fuzz + 200-seed sweep), and every
  diagram is a real sim state — so no separate algorithm-verification test is
  needed.
- **Full regression gate:** all suites green (`test_puzzle`, `test_core`,
  `test_kilo`, `test_solver_opt`, `test_guides`), plus a manual rebuild of
  **both** PDFs with visual review — the kilominx for correctness/kid-
  friendliness, the megaminx for no regression from the extraction.

## Out of scope (future, per the umbrella design)

- The interactive **Megaminx Coach** website.
- The **2×2 / Ortega** last-layer variant for the kilominx.
- **No-dead-end** solver hardening (BFS recovery so `solve()` never raises).

## Done when

- `python3 build/guide_kilo.py` writes a non-empty `out/guide_kilo.pdf`.
- `tests/test_guides.py` passes; all other suites stay green.
- The megaminx PDF, rebuilt from the extracted framework, is visually reviewed
  and accepted.
