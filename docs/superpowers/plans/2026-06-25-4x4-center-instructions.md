# 4×4 Center Instructions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the vague text-only centers page in the 4×4 booklet with concrete, simulator-verified move diagrams (two pages): a bar method overview plus a dedicated "last two centers" finale.

**Architecture:** The teachable algorithms are discovered/verified against the sim, exposed as named constants in `minx/method_cube.py`, proven by a new `test_center_algs` in `tests/test_cube.py`, then rendered as `demo` tile rows by `build/guide_cube.py`. A small enhancement to `tiles()` makes inner-slice moves render as cube pictures (no arrow) instead of text-only boxes. Booklet pages re-render from the same verified sequences, so the booklet stays "correct by construction."

**Tech Stack:** Python 3.13+, the existing `minx.cube` / `minx.cube_render` / `build.guide_common` modules, weasyprint for PDF.

## Global Constraints

- Run everything from the repo root (`python3 -m tests.test_cube`, `python3 build/guide_cube.py`).
- Keep the "correct by construction" discipline: every algorithm rendered in the booklet must be verified in `tests/test_cube.py` (per `CLAUDE.md`).
- Don't change `minx/cube.py` move semantics; only add named string constants to `minx/method_cube.py`.
- Code (`minx/`, `build/`, `tests/`) is MIT; keep code vs. rendered-content separation.
- The four verified algorithms (use these exact strings everywhere):
  - `CENTER_BAR_LIFT = "2R"`
  - `CENTER_LAST_TWO_COLUMN = "2U2 2B2 2U2"`
  - `CENTER_LAST_TWO_ROW = "2U2 2L2 2U2"`
  - `CENTER_LAST_TWO_DIAG = "U' 2R2 U' D' 2R2"`
- Canonical center-setup sticker-id swap pairs (ids verified against `CUBE4.stickers`):
  - Bar lift (U has a white bar on top; second white bar in Front's right column): `[(70, 9), (74, 10)]`
  - Column split (U/D last two, swapped in columns): `[(5, 25), (9, 21)]`
  - Row split: `[(5, 25), (6, 26)]`
  - Diagonal split: `[(5, 25), (10, 22)]`
- U/D/R/L/F/B face indices in `guide_cube.py`: `U, D, R, L, Fr, B = 0, 1, 2, 3, 4, 5`.

---

## File Structure

- **Modify** `minx/method_cube.py` — add 4 named string constants for the center algorithms (alongside the existing `EO`, `PLL_PARITY`, etc.).
- **Modify** `tests/test_cube.py` — add `test_center_algs()` proving the 4 algorithms do what the booklet claims.
- **Modify** `build/guide_cube.py` — import the new constants; enhance `tiles()` to render slice/wide moves as pictures; rewrite `centers_page()`; add `last_two_centers_page()`; insert it into `assemble()` and renumber subsequent pages.

No new files.

---

### Task 1: Named center-algorithm constants + verification test

**Files:**

- Modify: `minx/method_cube.py` (near the existing last-layer/parity constant block, around lines 28–33 and 196–199)
- Test: `tests/test_cube.py`

**Interfaces:**

- Produces: module-level constants `CENTER_BAR_LIFT`, `CENTER_LAST_TWO_COLUMN`, `CENTER_LAST_TWO_ROW`, `CENTER_LAST_TWO_DIAG` (all `str`), importable from `minx.method_cube`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cube.py` (after `test_parity_algs_preserve_reduction`, before `test_solve_3x3`):

```python
def test_center_algs():
    """The center algorithms the booklet renders, verified in-sim."""
    from minx.method_cube import (CENTER_BAR_LIFT, CENTER_LAST_TWO_COLUMN,
                                  CENTER_LAST_TWO_ROW, CENTER_LAST_TWO_DIAG)
    from minx import cube as _C
    P = _C.CUBE4
    st = P.stickers
    cenids = {f: [ids[0] for ids in P.centers if st[ids[0]].face == f]
              for f in range(6)}

    def fc(s, f):
        return [s[i] for i in cenids[f]]

    def solved_all(s):
        return all(fc(s, f) == [f] * 4 for f in range(6))

    def corners_home(s):
        return all(s[i] == st[i].face for ids in P.corners for i in ids)

    def build(pairs):
        cols = list(P.state().state)
        for a, b in pairs:
            cols[a], cols[b] = cols[b], cols[a]
        return P.state(colors=cols)

    # Bar lift: U has a white bar on top; a second white bar in Front's right
    # column. 2R slides it up and completes the U center; corners stay home.
    m = build([(70, 9), (74, 10)])
    m.do(CENTER_BAR_LIFT)
    assert fc(m.state, 0) == [0, 0, 0, 0]      # U center completed
    assert corners_home(m.state)

    # Last two centers, column split -> all six solved, corners home.
    m = build([(5, 25), (9, 21)])
    m.do(CENTER_LAST_TWO_COLUMN)
    assert solved_all(m.state)
    assert corners_home(m.state)

    # Last two centers, row split -> all six solved, corners home.
    m = build([(5, 25), (6, 26)])
    m.do(CENTER_LAST_TWO_ROW)
    assert solved_all(m.state)
    assert corners_home(m.state)

    # Last two centers, diagonal split -> all six solved, four side centers
    # intact. (Corners are NOT home: the alg uses outer U/D turns -- OK.)
    m = build([(5, 25), (10, 22)])
    m.do(CENTER_LAST_TWO_DIAG)
    assert solved_all(m.state)
    assert all(fc(m.state, f) == [f] * 4 for f in (2, 3, 4, 5))
```

Add `test_center_algs` to the `main()` call list:

```python
def main():
    test_geometry()
    test_moves()
    test_last_layer_algs()
    test_parity_algs_preserve_reduction()
    test_center_algs()
    test_solve_3x3()
    test_solve_4x4()
    print("test_cube: OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m tests.test_cube`
Expected: ImportError / `cannot import name 'CENTER_BAR_LIFT'` (the constants don't exist yet).

- [ ] **Step 3: Add the constants to `minx/method_cube.py`**

Add this block immediately after the `PLL_PARITY` / `OLL_PARITY` lines (after line 199, before the `_PAIR_INNER` block):

```python
# Center-building algorithms for the 4x4 booklet, verified in-sim (see
# tests/test_cube.py:test_center_algs). Each is rendered as a move diagram in
# build/guide_cube.py. Inner-slice-only algs leave the corners home; the
# diagonal alg uses outer U/D turns so corners move (fine -- centres stage does
# not depend on corners).
CENTER_BAR_LIFT = "2R"                       # slide a 2x1 bar up to complete a center
CENTER_LAST_TWO_COLUMN = "2U2 2B2 2U2"       # last two faces, column split
CENTER_LAST_TWO_ROW = "2U2 2L2 2U2"          # last two faces, row split (mirror)
CENTER_LAST_TWO_DIAG = "U' 2R2 U' D' 2R2"    # last two faces, diagonal split
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m tests.test_cube`
Expected: `test_cube: OK`

- [ ] **Step 5: Commit**

```bash
git add minx/method_cube.py tests/test_cube.py
git commit -m "Verify 4x4 center algorithms for booklet diagrams"
```

---

### Task 2: Render slice/wide moves as cube pictures in `tiles()`

**Files:**

- Modify: `build/guide_cube.py:expand_cube` and `build/guide_cube.py:tiles`

**Interfaces:**

- Consumes: existing `CR.render`, `CR.camera`, `svg_img`, `P4`, `CMAP`.
- Produces: `tiles()` now renders a cube picture (no arrow) for slice (`2R`, `2U2`, …) and wide (`Rw`, …) tokens, instead of a text-only movebox. Arrow rendering for outer moves is unchanged.

- [ ] **Step 1: Edit `tiles()` to render the state for slice/wide tokens**

In `build/guide_cube.py`, find the slice/wide branch inside the `tiles` function:

```python
    for tok, mv in expand_cube(alg):
        if mv is None:
            m.move(tok)
            cells.append(f'<div class="tile"><div class="movebox">{tok}</div>'
                         '</div>')
            continue
```

Replace it with a version that renders the cube (no arrow) **before** applying the move, matching the arrow path's "show state then move" order:

```python
    for tok, mv in expand_cube(alg):
        if mv is None:
            svg = CR.render(m, cam_u, cam_f, CMAP, size=size,
                            cam=CR.camera(P4, cam_u, cam_f), puzzle=P4)
            cells.append(f'<div class="tile">{svg_img(svg)}'
                         f'<div class="movebox">{tok}</div></div>')
            m.move(tok)
            continue
```

(`expand_cube` itself is unchanged — it already tags slice/wide tokens with `mv is None`.)

- [ ] **Step 2: Smoke-check the render path**

Run:

```bash
python3 -c "
import sys, pathlib
ROOT = pathlib.Path('/home/kurtt/megaminx').resolve()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'build'))
from minx import cube as C
from build import guide_cube as g
cells, m = g.tiles(C.CUBE4.state(), '2R 2U2')
print('tiles ok, cells:', len(cells))
"
```

Expected: `tiles ok, cells: 2` (no exception; each cell now contains an `<svg`).

- [ ] **Step 3: Commit**

```bash
git add build/guide_cube.py
git commit -m "Render slice/wide moves as cube pictures in booklet tiles"
```

---

### Task 3: Rewrite `centers_page()` with the bar method + verified demo

**Files:**

- Modify: `build/guide_cube.py:centers_page` and the import line at the top.

**Interfaces:**

- Consumes: `CENTER_BAR_LIFT` from `minx.method_cube`; existing `banner`, `holding`, `goal_box`, `tips`, `pic`, `tiles`, `stage_state`.
- Produces: a rewritten `centers_page()` returning a richer page body with a verified `demo` of `CENTER_BAR_LIFT` from a canonical setup state.

- [ ] **Step 1: Import the center constants**

In `build/guide_cube.py`, extend the existing `from minx.method_cube import (...)` block to include the four new constants. The current import is:

```python
from minx.method_cube import (Cube4Solver, scramble, EO, NIKLAS, UPERM,
                              PLL_PARITY, OLL_PARITY)
```

Change it to:

```python
from minx.method_cube import (Cube4Solver, scramble, EO, NIKLAS, UPERM,
                              PLL_PARITY, OLL_PARITY, CENTER_BAR_LIFT,
                              CENTER_LAST_TWO_COLUMN, CENTER_LAST_TWO_ROW,
                              CENTER_LAST_TWO_DIAG)
```

- [ ] **Step 2: Add a center-setup helper**

Add this helper near the other piece-finding helpers (after `center_ids`):

```python
def center_setup(swap_pairs):
    """A canonical 4x4 state with chosen center stickers swapped (used to
    demonstrate a center algorithm from a recognisable starting position).
    Pairs are sticker ids; everything else stays solved."""
    cols = list(P4.state().state)
    for a, b in swap_pairs:
        cols[a], cols[b] = cols[b], cols[a]
    return P4.state(colors=cols)
```

- [ ] **Step 3: Rewrite `centers_page()`**

Replace the entire current `centers_page()` function with:

```python
def centers_page():
    goal = pic(stage_state('centers'), size=120)
    # Demo: U already has a white bar on top; a second white bar sits in the
    # Front face's right column. 2R slides it up to complete the white center.
    demo, _ = tiles(center_setup([(70, 9), (74, 10)]), CENTER_BAR_LIFT,
                    cam_u=U, cam_f=Fr)
    body = f'''
      {banner(2, 'BUILD THE 6 CENTERS')}
      {holding('Pick a color to start (we use white). Build its four center '
               'pieces into one 2&times;2 block on a face. Then do the same for '
               'every color &mdash; opposite colors go on opposite faces.',
               '4&times;4')}
      {goal_box(goal, 'Goal: six solid centers')}
      <div class="note">THE BAR METHOD: find two center pieces of your color
      that sit next to each other on a side face &mdash; that is a 2&times;1
      <b>bar</b>. Turn an inner slice (the middle layer) to slide the bar up
      onto the face you are building. Make a second bar the same way and slide
      it up next to the first to finish the 2&times;2 block.</div>
      {demo}
      <div class="note">Here the top face already has one white bar; a second
      white bar waits in the front face&rsquo;s right column.
      {F("2R")} (the inner slice next to the right face) slides it up to
      complete the white center.</div>
      {tips([
        'Build one face, then hold it on top or bottom so the inner slices '
        'you use for the next face do not break it.',
        'The last two colors are the tricky ones &mdash; that needs its own '
        'page (next).',
        'When all six centers are solid blocks, the centers are done &mdash; '
        'their colors now tell you where every other piece belongs.',
      ])}
    '''
    page(body, 3)
```

- [ ] **Step 4: Smoke-check the page builds**

Run:

```bash
python3 -c "
import sys, pathlib
ROOT = pathlib.Path('/home/kurtt/megaminx').resolve()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'build'))
from build import guide_cube as g
g.PAGES.clear(); g.centers_page()
print('centers_page ok, pages:', len(g.PAGES))
"
```

Expected: `centers_page ok, pages: 1` (no exception).

- [ ] **Step 5: Commit**

```bash
git add build/guide_cube.py
git commit -m "Rewrite 4x4 centers page with verified bar-method demo"
```

---

### Task 4: Add the "last two centers" page and renumber

**Files:**

- Modify: `build/guide_cube.py` (new `last_two_centers_page()`; update `assemble()` and the page-number arguments of all later `page()` calls).

**Interfaces:**

- Consumes: `CENTER_LAST_TWO_COLUMN`, `CENTER_LAST_TWO_ROW`, `CENTER_LAST_TWO_DIAG`; `center_setup`, `tiles`, `pic`, `banner`, `holding`, `tips`, `F`.
- Produces: a new booklet page inserted as page 4; every subsequent page number increments by 1.

- [ ] **Step 1: Add `last_two_centers_page()`**

Add this new function immediately after `centers_page()`:

```python
def last_two_centers_page():
    # Column case demo (the row case is the mirror, shown as a note).
    col_demo, _ = tiles(center_setup([(5, 25), (9, 21)]),
                        CENTER_LAST_TWO_COLUMN, cam_u=U, cam_f=Fr)
    # Diagonal case demo.
    diag_demo, _ = tiles(center_setup([(5, 25), (10, 22)]),
                         CENTER_LAST_TWO_DIAG, cam_u=U, cam_f=Fr)
    # After-shots from top and bottom, to show both faces end solved.
    after = center_setup([(5, 25), (9, 21)])
    for t in CENTER_LAST_TWO_COLUMN.split():
        after.move(t)
    after_top = pic(after, cam_u=U, cam_f=Fr, size=120)
    after_bot = pic(after, cam_u=D, cam_f=Fr, size=120)
    body = f'''
      {banner(3, 'THE LAST TWO CENTERS')}
      {holding('When only two colors are left, they share the two opposite '
               'faces. Look at how their pieces are split, then use the '
               'matching fix below.', '4&times;4')}
      <div class="note">Hold the two unsolved faces on top and bottom. The
      four side centers are already solid &mdash; keep them that way. Only
      inner slices (and, for the diagonal case, a top/bottom turn) are
      used.</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#0fa84e">TWO COLUMNS SPLIT</div>
        If the swapped pairs line up as two columns, do:<br/>
        <b>{CENTER_LAST_TWO_COLUMN}</b><br/>
        <i>(Row split? Use the mirror: {CENTER_LAST_TWO_ROW})</i>
      </div></div>
      {col_demo}
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#7b2fbe">DIAGONAL SPLIT</div>
        If the swapped pairs sit diagonal to each other, do:<br/>
        <b>{CENTER_LAST_TWO_DIAG}</b>
      </div></div>
      {diag_demo}
      <div class="note">Both unsolved faces finish at the same time:</div>
      <div class="tiles">{after_top}{after_bot}</div>
      {tips([
        'Turn only the inner slices for the column and row cases &mdash; the '
        'side centers stay solid.',
        'The diagonal fix uses one top and one bottom turn; that is fine, the '
        'side centers still come back solved.',
        'Done! All six centers are solid blocks &mdash; move on to pairing '
        'the edges.',
      ])}
    '''
    page(body, 4)
```

- [ ] **Step 2: Insert the new page into `assemble()`**

In `assemble()`, add `last_two_centers_page()` right after `centers_page()`:

```python
def assemble():
    PAGES.clear()
    cover()
    pieces_page()
    notation()
    centers_page()
    last_two_centers_page()
    edges_page()
    white_cross_page()
    white_corners_page()
    middle_page()
    yellow_cross_page()
    last_layer_page()
    parity_page()
    back_page()
    return list(PAGES)
```

- [ ] **Step 3: Renumber the subsequent pages**

Each `page()` call takes an explicit page number as its second argument. Increment by 1 every page after the new page 4. Update these calls in `build/guide_cube.py`:

| Function | Old number | New number |
|---|---|---|
| `edges_page()` | `page(body, 4)` | `page(body, 5)` |
| `white_cross_page()` | `page(body, 5)` | `page(body, 6)` |
| `white_corners_page()` | `page(body, 6)` | `page(body, 7)` |
| `middle_page()` | `page(body, 7)` | `page(body, 8)` |
| `yellow_cross_page()` | `page(body, 8)` | `page(body, 9)` |
| `last_layer_page()` | `page(body, 9)` | `page(body, 10)` |
| `parity_page()` | `page(body, 10)` | `page(body, 11)` |

(`cover()`, `pieces_page()` (1), `notation()` (2), `centers_page()` (3), and `back_page()` (no number) are unchanged.)

- [ ] **Step 4: Smoke-check the full assembly**

Run:

```bash
python3 -c "
import sys, pathlib
ROOT = pathlib.Path('/home/kurtt/megaminx').resolve()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'build'))
from build import guide_cube as g
pages = g.assemble()
print('assembled pages:', len(pages))
"
```

Expected: `assembled pages: 13` (was 12; the new page added one).

- [ ] **Step 5: Commit**

```bash
git add build/guide_cube.py
git commit -m "Add 4x4 'last two centers' page and renumber booklet"
```

---

### Task 5: Rebuild the booklet and verify end-to-end

**Files:**

- None modified (build + verification only).

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m tests.test_cube`
Expected: `test_cube: OK` (confirms the four center algorithms are still verified).

- [ ] **Step 2: Rebuild the 4×4 booklet**

Run: `python3 build/guide_cube.py`
Expected: completes without error and writes `out/guide_cube.html` and `out/guide_cube.pdf`.

- [ ] **Step 3: Confirm the outputs exist and grew**

Run:

```bash
ls -la out/guide_cube.html out/guide_cube.pdf
```

Expected: both files present; HTML page count increased by one (13 pages).

- [ ] **Step 4: Sanity-check page numbering in the HTML**

Run:

```bash
grep -c 'class="page' out/guide_cube.html
grep -o 'STAGE [0-9]' out/guide_cube.html | head
```

Expected: 13 page divs (cover + back have no number); STAGE labels run 1 through 9 plus the parity stage.

- [ ] **Step 5: Commit (if any rebuild artifacts are tracked)**

```bash
git status --short
```

If `out/` is tracked and changed:

```bash
git add out/guide_cube.html out/guide_cube.pdf
git commit -m "Rebuild 4x4 guide with detailed center pages"
```

Otherwise no commit needed (rebuilt artifacts are generated).

---

## Self-Review

**Spec coverage:**

- Verified algorithms rendered as diagrams → Task 1 (proves them) + Tasks 3 & 4 (render them). ✓
- Rewrite `centers_page()` with bar method prose + verified demo → Task 3. ✓
- New "last two centers" page with column/row/diagonal demos, two camera views → Task 4 (`after_top`/`after_bot`). ✓
- Enhance `tiles()` for slice moves → Task 2. ✓
- `test_center_algs` in `tests/test_cube.py` → Task 1. ✓
- Renumber subsequent pages → Task 4 Step 3. ✓
- Out of scope (edges page) respected — no task touches `edges_page()` content. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code; sticker ids and algorithm strings are the verified values.

**Type consistency:** Constants `CENTER_*` named identically in Task 1 (definition + test) and Tasks 3/4 (import + use). `center_setup` defined in Task 3, used in Task 4. Page numbers form a consecutive 1–11 sequence after renumber.
