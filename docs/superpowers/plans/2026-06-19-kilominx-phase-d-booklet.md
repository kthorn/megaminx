# Kilominx Phase D — Booklet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A kid-friendly picture-based kilominx solving booklet (`out/guide_kilo.pdf`), every diagram rendered from a `KILOMINX` simulator state, built on a booklet framework shared with the megaminx guide.

**Architecture:** Extract the puzzle-agnostic booklet framework from the 891-line `build/make_guide.py` into a new `build/guide_common.py` that both booklets import; add a small circle-center cosmetic to the already-puzzle-agnostic `minx/render.py`; write `build/guide_kilo.py` as a parallel, shorter booklet (corners-only, two taught algorithms). The megaminx booklet's page content is untouched — only its helper definitions move out.

**Tech Stack:** Python 3.13+, `weasyprint` (HTML→PDF, manual step only). SVG rendered by `minx/render.py`. Tests are plain `main()` modules run with `python3 -m tests.<module>`; booklet builders live in `build/` and are run directly (`python3 build/guide_kilo.py`).

## Global Constraints

- Run everything from the repo root; `minx.*`/`tests.*` import as packages. Booklet builders in `build/` bootstrap with `sys.path.insert(0, str(ROOT))` where `ROOT = pathlib.Path(__file__).resolve().parent.parent` — the established convention in `make_guide.py` and `build/diag_*.py`.
- The framework extraction must be a **pure relocation**: `make_guide.py`'s megaminx HTML output must be **byte-identical** before and after (verified in Task 1). Helper definitions move to `guide_common.py`; `make_guide.py`'s `PAGES`, `page()`, megaminx content helpers, and all page functions stay and are unchanged.
- `holding(text, puzzle_name='Megaminx')` defaults to `'Megaminx'` so existing `make_guide.py` calls are unchanged; `guide_kilo.py` passes `'Kilominx'`.
- The kilominx booklet teaches exactly two algorithms, the proven `KiloSolver` constants imported from `minx.solver`: `RIGHTY = "Ri DRi R DR"` and `CORNER_CYCLE = "Ri BRi R BR Ri Fi R BRi Ri BR F R"`. Do not hardcode these strings in the booklet — import them.
- Every booklet picture is rendered from a real `KILOMINX` simulator state (built by applying a setup/alg to `K.minx()`), never hand-drawn — diagrams are correct by construction.
- `minx/render.py` stays puzzle-agnostic; the megaminx (`center_shape == 'pentagon'`) render path must be unchanged (no `<circle>` introduced for the megaminx).
- Outputs: kilominx → `out/guide_kilo.html` + `out/guide_kilo.pdf`; megaminx stays `out/guide.html` + `out/guide.pdf`.
- Full regression gate (all must stay green): `python3 -m tests.test_puzzle`, `tests.test_core`, `tests.test_kilo`, `tests.test_solver_opt`, `tests.test_guides`. PDF generation (weasyprint) is a manual step, not in the suite. A manual visual review of BOTH rebuilt PDFs is the final acceptance gate.
- The kilominx hold: `WHITE = max(range(12), key=lambda fi: K.normals[fi][2])`, `FRONT = min(K.adj[WHITE], key=lambda fi: K.normals[fi][1])`, `GRAY = K.opp[WHITE]` — the same canonical convention the megaminx guide/tests share.

---

### Task 1: Extract `build/guide_common.py`; repoint `make_guide.py`

**Files:**
- Create: `build/guide_common.py`
- Modify: `build/make_guide.py` (delete relocated helper defs at ~`55-150`; add import; refactor `build()` at ~`864-890`)

**Interfaces:**
- Produces (in `guide_common`): `svg_img(svg, cls='pic', w=None)`, `expand_alg(alg)`, `display_letter(token, click)`, `goal_box(inner, caption='Your Goal')`, `banner(stage, title)`, `holding(text, puzzle_name='Megaminx')`, `tips(items)`, `congrats(text)`, `F(letter)`, `colorword(word, color)`, `FACE_LETTER_COLORS` (dict), `build_html(pages, root)` (returns the full HTML string, no weasyprint), `render_booklet(pages, out_dir, stem, root)` (writes `<stem>.html`, runs weasyprint to `<stem>.pdf`, returns html).
- Consumes: `minx.puzzle.parse_alg` (via `expand_alg`).

- [ ] **Step 1: Snapshot the current megaminx HTML (baseline for byte-identity)**

Run (from repo root, BEFORE any edit):

```bash
python3 -c "import sys,pathlib; sys.path.insert(0,'.'); import importlib.util as u; \
spec=u.spec_from_file_location('mg','build/make_guide.py'); m=u.module_from_spec(spec); spec.loader.exec_module(m); \
[f() for f in [m.cover,m.stage1,m.notation,m.stage2,m.stage3,m.stage4,m.stage5_edges,m.stage5_pairs,m.stage6_corners,m.stage6_edges,m.stage7,m.stage8,m.stage9,m.stage10,m.backpage]]; \
css=open('build/guide.css').read(); html='<!DOCTYPE html><html><head><meta charset=\"utf-8\">\n<style>'+css+'</style></head><body>'+''.join(m.PAGES)+'</body></html>'; \
open('/tmp/mega_before.html','w').write(html); print('baseline pages', len(m.PAGES))"
```
Expected: `baseline pages 15`. This writes `/tmp/mega_before.html` — the exact current output, used in Step 6 to prove the extraction changed nothing.

- [ ] **Step 2: Create `build/guide_common.py`**

```python
"""Puzzle-agnostic booklet framework, shared by the megaminx and kilominx
guides. Pure presentation helpers (SVG embedding, banners, page chrome) plus
the HTML/PDF build driver. No puzzle-specific content lives here."""
import pathlib
from minx import puzzle as P

FACE_LETTER_COLORS = {
    'U': '#1565d8', 'F': '#0fa84e', 'R': '#e02020', 'L': '#ff8a00',
    'D': '#7b2fbe', 'BR': '#1565d8', 'BL': '#1565d8',
}


def svg_img(svg, cls='pic', w=None):
    import base64
    b64 = base64.b64encode(svg.encode()).decode()
    style = f' style="width:{w}"' if w else ''
    return f'<img class="{cls}" src="data:image/svg+xml;base64,{b64}"{style}/>'


def expand_alg(alg):
    """'R U2i Ri' -> [('R',1),('U',-1),('U',-1),('R',-1)] as (token,click)."""
    out = []
    for name, times in P.parse_alg(alg):
        step = 1 if times > 0 else -1
        for _ in range(abs(times)):
            out.append((name, step))
    return out


def display_letter(token, click):
    t = 'D' if token == 'DR' else token
    return t + ('i' if click < 0 else '')


def goal_box(inner, caption='Your Goal'):
    return (f'<div class="goal">{inner}'
            f'<div class="goalstar">{caption}</div></div>')


def banner(stage, title):
    return (f'<div class="topbar"><div class="stagebadge">STAGE {stage}:</div>'
            f'<div class="banner">{title}</div></div>')


def holding(text, puzzle_name='Megaminx'):
    return (f'<div class="holding"><span class="holdhead">Holding Your '
            f'{puzzle_name}:</span> {text}</div>')


def tips(items):
    lis = ''.join(f'<li>{i}</li>' for i in items)
    return f'<div class="tips"><span class="tiphead">Tips:</span><ul>{lis}</ul></div>'


def congrats(text):
    return (f'<div class="congrats"><div class="congratsbanner">'
            f'Congratulations!</div><div class="congratsbody">{text}</div></div>')


def F(letter):
    col = FACE_LETTER_COLORS.get(letter.rstrip('i'), '#1565d8')
    return f'<span class="facelet" style="color:{col}">({letter})</span>'


def colorword(word, color):
    return f'<span style="color:{color};font-weight:800">{word}</span>'


def build_html(pages, root):
    """Assemble the full HTML document string (no weasyprint). The `\\n` after
    the <meta> tag reproduces make_guide.py's original wrapper exactly, so the
    extracted megaminx HTML stays byte-identical."""
    css = (pathlib.Path(root) / 'build' / 'guide.css').read_text()
    return ('<!DOCTYPE html><html><head><meta charset="utf-8">\n'
            f'<style>{css}</style></head><body>{"".join(pages)}</body></html>')


def render_booklet(pages, out_dir, stem, root):
    """Write <stem>.html and (via weasyprint) <stem>.pdf into out_dir."""
    html = build_html(pages, root)
    (out_dir / f'{stem}.html').write_text(html)
    import weasyprint
    weasyprint.HTML(string=html, base_url=str(root)).write_pdf(
        out_dir / f'{stem}.pdf')
    print(f"wrote {out_dir / f'{stem}.pdf'} ({len(pages)} pages)")
    return html
```

- [ ] **Step 3: Delete the relocated helpers from `make_guide.py`**

In `build/make_guide.py`, DELETE these now-duplicated definitions (they live in `guide_common` now): `FACE_LETTER_COLORS` (the dict at ~`23-26`), `svg_img` (~`55-59`), `expand_alg` (~`62-70`), `display_letter` (~`73-75`), `goal_box` (~`104-106`), `banner` (~`124-126`), `holding` (~`129-131`), `tips` (~`134-136`), `congrats` (~`139-141`), `F` (~`144-146`), `colorword` (~`149-150`).

Keep everything else: `PAGES`, `page()`, `piece_ids`, `bright_for`, `white_layer_ids`, `layer_ids`, `tiles_html`, `picture`, `WHITEW`/`GRAYW`, and ALL page functions (`cover`, `stage1`–`stage10`, `notation`, `backpage`).

- [ ] **Step 4: Add the import to `make_guide.py`**

In `build/make_guide.py`, just after the existing `from minx import puzzle as P, method_mega as M, render as R` line (~`11`), add:

```python
from guide_common import (svg_img, expand_alg, display_letter, goal_box,
                          banner, holding, tips, congrats, F, colorword,
                          FACE_LETTER_COLORS, render_booklet)
```

(`sys.path.insert(0, str(ROOT))` already runs above this line, and `build/` is the script dir, so `import guide_common` resolves when run as `python3 build/make_guide.py`. For `-m`/import use, Task 3's test inserts `build/` on the path — see Task 3.)

- [ ] **Step 5: Refactor `build()` to use `render_booklet`**

In `build/make_guide.py`, replace the entire `build(pages_only=None)` function (~`864-890`) with:

```python
def assemble():
    """Run all page functions, returning the PAGES list."""
    PAGES.clear()
    cover()
    stage1()
    notation()
    stage2()
    stage3()
    stage4()
    stage5_edges()
    stage5_pairs()
    stage6_corners()
    stage6_edges()
    stage7()
    stage8()
    stage9()
    stage10()
    backpage()
    return PAGES


def build():
    render_booklet(assemble(), OUT, 'guide', ROOT)


if __name__ == '__main__':
    build()
```

- [ ] **Step 6: Verify byte-identical megaminx HTML (the regression gate)**

Run (from repo root):

```bash
python3 -c "import sys; sys.path.insert(0,'.'); sys.path.insert(0,'build'); \
import make_guide as m, guide_common as gc; \
html=gc.build_html(m.assemble(), m.ROOT); open('/tmp/mega_after.html','w').write(html); \
print('pages', len(m.PAGES))" && diff -q /tmp/mega_before.html /tmp/mega_after.html && echo "BYTE-IDENTICAL OK"
```
Expected: `pages 15`, then `BYTE-IDENTICAL OK` (the `diff` reports no differences). If `diff` finds a difference, the extraction altered output — fix it (the relocation must be pure) before committing; do not accept a non-identical result in this task.

- [ ] **Step 7: Commit**

```bash
git add build/guide_common.py build/make_guide.py
git commit -m "refactor: extract booklet framework into build/guide_common.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Circle-center cosmetic in `minx/render.py`

**Files:**
- Modify: `minx/render.py` (the sticker loop and draw loop inside `render()`, ~`95-140`)
- Test: `tests/test_guides.py` (create; add `test_center_circle_cosmetic` + `main()`)

**Interfaces:**
- Consumes: `puzzle.spec.center_shape` (`'circle'` for kilominx, `'pentagon'` for megaminx), `sticker.kind`.
- Produces: kilominx renders emit `<circle .../>` for center stickers; megaminx renders are unchanged (no `<circle>`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_guides.py`:

```python
"""Booklet renderer + build smoke tests. Run: python3 -m tests.test_guides"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'build'))   # so build/*.py import as modules

from minx import puzzle as P
from minx import render as R


def test_center_circle_cosmetic():
    K = P.KILOMINX
    white = max(range(12), key=lambda fi: K.normals[fi][2])
    front = min(K.adj[white], key=lambda fi: K.normals[fi][1])
    cmap = R.color_map(white, front, puzzle=K)
    ksvg = R.render_top(K.minx(), white, front, cmap, size=120, puzzle=K)
    assert '<circle' in ksvg, "kilominx center should render as a circle"

    # megaminx (center_shape == 'pentagon') must NOT gain a circle
    mw = max(range(12), key=lambda fi: P.MEGAMINX.normals[fi][2])
    mf = min(P.MEGAMINX.adj[mw], key=lambda fi: P.MEGAMINX.normals[fi][1])
    mcmap = R.color_map(mw, mf)
    msvg = R.render_top(P.MEGAMINX.minx(), mw, mf, mcmap, size=120)
    assert '<circle' not in msvg, "megaminx render must be unchanged"


def main():
    test_center_circle_cosmetic()
    print("test_guides: OK")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_guides`
Expected: FAIL — `AssertionError: kilominx center should render as a circle` (render currently draws the center as a rounded pentagon path, no `<circle>`).

- [ ] **Step 3: Implement the circle cosmetic**

In `minx/render.py`, in `render()`, change the sticker-collection loop so center stickers on a circle-center puzzle are tagged. Replace the body of the `for i, s in enumerate(pz.stickers):` loop's tail (the part from `poly2 = [cam.project(p) for p in inset]` through `polys.append((poly2, fill))`, ~`101-112`) with:

```python
            poly2 = [cam.project(p) for p in inset]
            pts.extend(cam.project(p) for p in s.polygon)
            color_face = m.state[idx]
            if bright_ids is not None and idx not in bright_ids:
                fill = '#b9bdc2'
            elif dim_faces and color_face in dim_faces:
                fill = '#b9bdc2'
            elif color_face not in cmap:
                fill = '#b9bdc2'   # sentinel "unknown" sticker
            else:
                fill = PALETTE[cmap[color_face]]
            if s.kind == 'center' and pz.spec.center_shape == 'circle':
                cx = sum(p[0] for p in poly2) / len(poly2)
                cy = sum(p[1] for p in poly2) / len(poly2)
                r = min(math.dist((cx, cy),
                                  ((poly2[k][0] + poly2[(k + 1) % len(poly2)][0]) / 2,
                                   (poly2[k][1] + poly2[(k + 1) % len(poly2)][1]) / 2))
                        for k in range(len(poly2)))
                polys.append(('circle', (cx, cy, r), fill))
            else:
                polys.append(('poly', poly2, fill))
```

Then change the draw loop (the `for poly2, fill in polys:` block, ~`138-140`) to:

```python
    for kind_, geom, fill in polys:
        if kind_ == 'circle':
            cx, cy, r = geom
            sx, sy = T((cx, cy))
            out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" '
                       f'r="{r * scale:.1f}" fill="{fill}"/>')
        else:
            p2 = [T(p) for p in geom]
            out.append(f'<path d="{_rounded_path(p2)}" fill="{fill}"/>')
```

(`math` is already imported at the top of `render.py`.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m tests.test_guides`
Expected: PASS — prints `test_guides: OK`.

- [ ] **Step 5: Confirm the renderer regression gate**

Run: `python3 -m tests.test_core && python3 -m tests.test_puzzle`
Expected: both print their OK lines (`test_core` exercises `render_smoke` on the megaminx; the megaminx path is unchanged).

- [ ] **Step 6: Commit**

```bash
git add minx/render.py tests/test_guides.py
git commit -m "feat: render kilominx center as a circle (center_shape cosmetic)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `build/guide_kilo.py` scaffold + non-stage pages + build-smoke test

**Files:**
- Create: `build/guide_kilo.py`
- Modify: `tests/test_guides.py` (add `test_kilo_booklet_builds` + call in `main()`)

**Interfaces:**
- Consumes: `guide_common` helpers (Task 1); `minx.render`; `minx.method_kilo.corner_key`; `minx.solver.RIGHTY`/`CORNER_CYCLE`; `puzzle.KILOMINX`.
- Produces: `guide_kilo.assemble()` → list of page HTML strings; `guide_kilo.PAGES`; `guide_kilo.build()`; module globals `K`, `WHITE`, `FRONT`, `GRAY`, `NAMES`, `LNAMES`, `CMAP`; helpers `page`, `picture`, `tiles_html`, `corner_ids`, `center_id`. After this task `assemble()` returns 4 pages (cover, pieces, notation, backpage); Task 4 inserts the 5 stage pages.

- [ ] **Step 1: Write the failing test**

In `tests/test_guides.py`, add (and call it in `main()` after `test_center_circle_cosmetic()`):

```python
def test_kilo_booklet_builds():
    import guide_kilo
    import guide_common as gc
    pages = guide_kilo.assemble()
    assert len(pages) == 4, len(pages)        # cover, pieces, notation, back
    html = gc.build_html(pages, guide_kilo.ROOT)
    assert html.startswith('<!DOCTYPE html>') and html.rstrip().endswith('</html>')
    assert 'data:image/svg+xml' in html       # at least one rendered picture
    assert 'KILOMINX' in html
```

Update `main()`:

```python
def main():
    test_center_circle_cosmetic()
    test_kilo_booklet_builds()
    print("test_guides: OK")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_guides`
Expected: FAIL — `ModuleNotFoundError: No module named 'guide_kilo'`.

- [ ] **Step 3: Create `build/guide_kilo.py` with the scaffold and non-stage pages**

```python
#!/usr/bin/env python3
"""Generate the Kilominx Solution Guide booklet (HTML -> PDF).

Corners-only sibling of make_guide.py. Every picture is rendered from a
KILOMINX simulator state, and the two taught algorithms are the proven
KiloSolver constants, so the booklet is correct by construction.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'build'))

from minx import puzzle as P, render as R
from minx.method_kilo import corner_key
from minx.solver import RIGHTY, CORNER_CYCLE
from guide_common import (svg_img, expand_alg, display_letter, goal_box,
                          banner, holding, tips, congrats, F, colorword,
                          FACE_LETTER_COLORS, render_booklet)

OUT = ROOT / 'out'
OUT.mkdir(exist_ok=True)

K = P.KILOMINX
WHITE = max(range(12), key=lambda fi: K.normals[fi][2])
FRONT = min(K.adj[WHITE], key=lambda fi: K.normals[fi][1])
NAMES = K.name_faces(WHITE, FRONT)
GRAY = K.opp[WHITE]
CMAP = R.color_map(WHITE, FRONT, puzzle=K)
LNAMES = K.name_faces(GRAY, K.adj[GRAY][0])   # gray-up grip for LL pages
WHITEW = colorword('WHITE', '#5a6470')
GRAYW = colorword('GRAY', '#6f7a85')

PAGES = []


def page(body, number=None, cls=''):
    num = ''
    if number is not None:
        side = 'left' if number % 2 else 'right'
        num = f'<div class="pagenum {side}">{number}</div>'
    PAGES.append(f'<div class="page {cls}">{body}{num}</div>')


def corner_ids(faces):
    return K.corner_slots[corner_key(faces)]


def center_id(face):
    return K.id_to_idx[(face, 'center', 0)]


def picture(state, bright=None, size=110, arrow=None, tilt=0.42, yaw=0.18,
            cam_u=None, cam_f=None):
    cu = WHITE if cam_u is None else cam_u
    cf = FRONT if cam_f is None else cam_f
    svg = R.render(state, cu, cf, CMAP, size=size,
                   cam=R.Camera(cu, cf, tilt=tilt, yaw=yaw, puzzle=K),
                   arrow=arrow, bright_ids=bright, puzzle=K)
    return svg_img(svg)


def tiles_html(state, names, alg, cam_u, cam_f, bright=None, size=86):
    m = state.copy()
    cells = []
    for token, click in expand_alg(alg):
        face = names[token]
        svg = R.render(m, cam_u, cam_f, CMAP, size=size,
                       cam=R.Camera(cam_u, cam_f, puzzle=K),
                       arrow=(face, click), bright_ids=bright, puzzle=K)
        letter = display_letter(token, click)
        cells.append(
            f'<div class="tile">{svg_img(svg)}'
            f'<div class="movebox">{letter.replace("i", "<i>i</i>")}</div></div>')
        m.turn(face, click)
    return '<div class="tiles">' + ''.join(cells) + '</div>', m


# --- cover ------------------------------------------------------------------

def cover():
    hero = picture(K.minx(), size=320)
    body = f'''
      <div class="cover">
        <div class="coverlogo">
          <div class="coverdiamond"></div>
          <div class="covertitle">KILOMINX</div>
          <div class="coverribbon">12 SIDES &middot; 20 CORNERS &middot; ONE SECRET</div>
        </div>
        <div class="coversub">SOLUTION GUIDE</div>
        <div class="coverhero">{hero}</div>
        <div class="coverunlock">Unlock the Secret!</div>
      </div>'''
    page(body, None, cls='coverpage')


# --- get to know your kilominx ----------------------------------------------

def pieces_page():
    m = K.minx()
    c_ids = corner_ids((WHITE, NAMES['F'], NAMES['R']))
    ctr_ids = [center_id(NAMES['F'])]
    corner_pic = picture(m, bright=set(c_ids), size=104)
    center_pic = picture(m, bright=set(ctr_ids), size=104)
    body = f'''
      {banner(1, 'GET TO KNOW YOUR<br/>KILOMINX')}
      <div class="defs">DEFINITIONS OF KILOMINX PIECES</div>
      <div class="parts">THE PARTS:</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#0fa84e">CORNER PIECES</div>
        PIECES WITH THREE (3) COLORS. THERE ARE TWENTY (20) CORNER PIECES &mdash;
        these are the ONLY pieces you move. The whole puzzle is corners!
      </div>{corner_pic}</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#1565d8">CENTER PIECES</div>
        PIECES WITH ONE (1) COLOR. THERE ARE TWELVE (12), ONE ON EACH FACE.
        THEY <b>DO NOT MOVE</b> and show the color of their face.
      </div>{center_pic}</div>
      <div class="note">A kilominx is a megaminx with <b>no edge pieces</b> &mdash;
      just corners and centers. It has <b>12 faces</b> and <b>12 colors</b>; each
      color is on exactly one face. {WHITEW} and {GRAYW} are on opposite faces
      &mdash; you start with the white face on top and finish with the gray one
      on the bottom. <i>(Use the face colors of YOUR puzzle; the steps are the
      same.)</i></div>
    '''
    page(body, 1)


# --- notation ---------------------------------------------------------------

def notation():
    m = K.minx()
    rows = []
    letters = [
        ('U', 'Up Face', 'the top face'),
        ('F', 'Front Face', 'the face facing you, below the top'),
        ('R', 'Right Face', 'the face just right of the front'),
        ('L', 'Left Face', 'the face just left of the front'),
        ('DR', 'Down Face', 'the face below and between F and R'),
    ]
    tile_cells = []
    for tok, namestr, desc in letters:
        face = NAMES[tok]
        for click, suffix in ((1, ''), (-1, 'i')):
            svg = R.render(m, WHITE, FRONT, CMAP, size=80,
                           cam=R.Camera(WHITE, FRONT, puzzle=K),
                           arrow=(face, click), puzzle=K)
            disp = display_letter(tok, click)
            tile_cells.append(
                f'<div class="tile">{svg_img(svg)}'
                f'<div class="movebox">{disp.replace("i","<i>i</i>")}</div></div>')
        letter = 'D' if tok == 'DR' else tok
        rows.append(f'<div class="notrow"><span class="bigletter" '
                    f'style="color:{FACE_LETTER_COLORS[letter]}">{letter}</span>'
                    f'<span class="noteq">=</span> <b>{namestr}</b> '
                    f'<span class="notdesc">&mdash; {desc}</span></div>')
    body = f'''
      <div class="topbar"><div class="banner wide">EACH FACE OF THE KILOMINX
      IS REPRESENTED BY A LETTER</div></div>
      {''.join(rows)}
      <div class="note"><b>A letter with an <i>"i"</i> after it</b> means an
      <b>inverted</b> (counter-clockwise) turn of that face. A letter alone
      means a clockwise turn (as you look at that face). Every turn is
      <b>one click</b> &mdash; one fifth of the way around.</div>
      <div class="veryimportant">VERY IMPORTANT</div>
      <div class="note">The pictures show exactly which face moves and which
      way. Hold your kilominx to match the picture before each sequence.
      Dark gray on a picture means <b>the color there does not matter</b>.</div>
      <div class="tiles wrap">{''.join(tile_cells)}</div>
    '''
    page(body, 2)


# --- back page --------------------------------------------------------------

def backpage():
    hero = picture(K.minx(), size=110)
    body = f'''
      <div class="topbar"><div class="banner wide">NOW YOU KNOW THE
      SECRET&hellip;</div></div>
      <div class="funhead">Fun Facts!</div>
      <div class="note">A kilominx is sometimes called a <b>"corners-only
      megaminx."</b> Take a megaminx, throw away every edge piece, and this is
      what is left.</div>
      <div class="note">It still has <b>twenty corner pieces</b> in a dozen
      colors &mdash; plenty of ways to scramble, but always the same secret to
      solve.</div>
      <div class="note">Every solve in this booklet was checked, move by move,
      on a computer model of the puzzle &mdash; so if you follow the pictures
      exactly, it always works.</div>
      <div class="note">The method you just learned is the same idea as the
      megaminx and your cube: build the white layer, drop in the middle corners
      with the Righty move, then finish the last layer in two small steps.
      Different puzzle &mdash; same secret.</div>
      <div style="text-align:center;margin-top:14pt">{hero}</div>
      <div class="backcredit">Made for a young puzzler who already unlocked the
      cube. Happy twisting!</div>
    '''
    page(body, None, cls='backpage')


# --- assembly ---------------------------------------------------------------

def assemble():
    PAGES.clear()
    cover()
    pieces_page()
    notation()
    backpage()
    return PAGES


def build():
    render_booklet(assemble(), OUT, 'guide_kilo', ROOT)


if __name__ == '__main__':
    build()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m tests.test_guides`
Expected: PASS — prints `test_guides: OK` (the kilominx HTML assembles 4 pages with embedded SVG and the word KILOMINX).

- [ ] **Step 5: Commit**

```bash
git add build/guide_kilo.py tests/test_guides.py
git commit -m "feat: guide_kilo scaffold — cover, pieces, notation, back page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: The five solving-stage pages

**Files:**
- Modify: `build/guide_kilo.py` (add 5 stage functions; insert them into `assemble()`)
- Modify: `tests/test_guides.py` (update the page-count assertion 4 → 9)

**Interfaces:**
- Consumes: everything from Task 3 (`picture`, `tiles_html`, `corner_ids`, `center_id`, `NAMES`, `LNAMES`, `RIGHTY`, `CORNER_CYCLE`, `holding`, `banner`, `goal_box`, `tips`, `F`, `WHITEW`, `GRAYW`).
- Produces: `white_corners_page`, `upper_ring_page`, `lower_ring_page`, `ll_permute_page`, `ll_orient_page`; `assemble()` returns 9 pages.

- [ ] **Step 1: Update the page-count assertion (failing test)**

In `tests/test_guides.py`, change the assertion in `test_kilo_booklet_builds`:

```python
    assert len(pages) == 9, len(pages)        # cover, pieces, notation, 5 stages, back
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_guides`
Expected: FAIL — `AssertionError: 4` (the five stage pages are not added yet).

- [ ] **Step 3: Add the five stage functions to `build/guide_kilo.py`**

Insert these functions after `notation()` and before `backpage()`:

```python
# --- stage 2: white corners -------------------------------------------------

def white_corners_page():
    # demo: solved cube with one white corner popped out by inverse-righty, so
    # replaying RIGHTY at this grip drops it home.
    bright = set(corner_ids((WHITE, NAMES['F'], NAMES['R'])))
    bright |= {center_id(WHITE)}
    goalp = picture(K.minx(), bright=bright, size=104)
    demo = K.minx()
    P.apply_alg(demo, "DRi Ri DR R", NAMES)   # inverse of RIGHTY = Ri DRi R DR
    tiles, _ = tiles_html(demo, NAMES, RIGHTY, WHITE, NAMES['F'], bright=bright)
    body = f'''
      {banner(2, 'SOLVE THE WHITE CORNERS')}
      {holding(f'Hold your kilominx with the {WHITEW} center on top {F("U")}. '
               'You will fill the five corners around the white face, each '
               'with white on top and its two side colors matching the side '
               'centers.', 'Kilominx')}
      {goal_box(goalp)}
      {tips([
        'Find a white corner in the bottom of the puzzle. Park it directly '
        '<b>below the slot it belongs in</b> by turning the bottom faces.',
        'Then repeat the <b>Righty</b> move below &mdash; '
        f'{F("R")}<i>i</i> {F("D")}<i>i</i> {F("R")} {F("D")} &mdash; until the '
        'corner pops up into place with white on top. Repeat 1, 2, or 3 times.',
        'Turning the bottom faces never disturbs corners already finished on '
        'top, so work one corner at a time.',
      ])}
      {tiles}
    '''
    page(body, 3)


# --- stage 3: upper-middle ring ---------------------------------------------

def upper_ring_page():
    a, b = NAMES['F'], NAMES['R']
    x = NAMES['DR']
    bright = set(corner_ids((a, b, x)))
    goalp = picture(K.minx(), bright=bright, size=104)
    demo = K.minx()
    P.apply_alg(demo, "DRi Ri DR R", NAMES)
    tiles, _ = tiles_html(demo, NAMES, RIGHTY, WHITE, NAMES['F'], bright=bright)
    body = f'''
      {banner(3, 'SOLVE THE UPPER MIDDLE CORNERS')}
      {holding('Keep white on top. Now fill the ring of five corners just '
               'below the white ones &mdash; each has two side colors and no '
               'white and no gray.', 'Kilominx')}
      {goal_box(goalp)}
      {tips([
        'These corners are already in the middle &mdash; find one that is in '
        'the wrong place (or twisted), and use the same <b>Righty</b> move to '
        'kick it out and bring the right one in.',
        'Park the corner you want directly below its slot, then repeat '
        '<b>Righty</b> until it seats. Same move as the white corners, one row '
        'lower.',
      ])}
      {tiles}
    '''
    page(body, 4)


# --- stage 4: lower-middle ring ---------------------------------------------

def lower_ring_page():
    a = NAMES['F']
    x, y = NAMES['DR'], NAMES['DL']
    bright = set(corner_ids((a, x, y)))
    goalp = picture(K.minx(), bright=bright, size=104)
    demo = K.minx()
    P.apply_alg(demo, "DRi Ri DR R", NAMES)
    tiles, _ = tiles_html(demo, NAMES, RIGHTY, WHITE, NAMES['F'], bright=bright)
    body = f'''
      {banner(4, 'SOLVE THE LOWER MIDDLE CORNERS')}
      {holding('Still white on top. Fill the next ring down &mdash; the five '
               'corners that sit just above the gray face. None of these has '
               'white; none has gray yet on top.', 'Kilominx')}
      {goal_box(goalp)}
      {tips([
        'Exactly like before: park the corner below its slot and repeat '
        '<b>Righty</b> until it drops in.',
        'After this stage only the five {GRAYW} corners on the bottom are '
        'left. Turn the whole puzzle over so gray is on top for the last two '
        'pages.'.replace('{GRAYW}', GRAYW),
      ])}
      {tiles}
    '''
    page(body, 5)


# --- stage 5: last layer, permute -------------------------------------------

def ll_permute_page():
    # all five gray corners + the gray center (adj[GRAY] is index-ordered, not
    # ring-ordered, so collect gray corners straight from corner_slots).
    bright = {center_id(GRAY)}
    for key, ids in K.corner_slots.items():
        if GRAY in key:
            bright |= set(ids)
    goalp = picture(K.minx(), bright=bright, size=104,
                    cam_u=GRAY, cam_f=K.adj[GRAY][0], tilt=0.0, yaw=0.0)
    demo = K.minx()
    P.apply_alg(demo, CORNER_CYCLE + ' ' + CORNER_CYCLE, LNAMES)
    tiles, _ = tiles_html(demo, LNAMES, CORNER_CYCLE, GRAY, LNAMES['F'])
    body = f'''
      {banner(5, 'LAST LAYER: MOVE THE CORNERS HOME')}
      {holding(f'Turn the puzzle over so the {GRAYW} center is on top {F("U")}. '
               'First get every gray corner into the right CORNER (ignore which '
               'way it is twisted for now).', 'Kilominx')}
      {goal_box(goalp, caption='Corners in place')}
      {tips([
        'Hold the puzzle so one corner that is already in the right place is '
        'at the back-right. Then do the <b>Corner Cycle</b> below; it spins the '
        'other three corners around.',
        'Turn the gray top to look at the result, and repeat the Corner Cycle '
        'until all five corners are home. They may still be twisted &mdash; '
        'that is the next page.',
      ])}
      {tiles}
    '''
    page(body, 6)


# --- stage 6: last layer, orient --------------------------------------------

def ll_orient_page():
    slot = corner_ids((GRAY, LNAMES['F'], LNAMES['R']))
    bright = set(slot)
    goalp = picture(K.minx(), size=104,
                    cam_u=GRAY, cam_f=K.adj[GRAY][0], tilt=0.0, yaw=0.0)
    demo = K.minx()
    P.apply_alg(demo, "DRi Ri DR R", LNAMES)
    tiles, _ = tiles_html(demo, LNAMES, RIGHTY, GRAY, LNAMES['F'], bright=bright)
    body = f'''
      {banner(6, 'LAST LAYER: TWIST THE CORNERS')}
      {holding(f'Still {GRAYW} on top. Every corner is in the right place &mdash; '
               'now twist each one so gray faces up. This uses the <b>Righty</b> '
               'move you already know.', 'Kilominx')}
      {goal_box(goalp, caption='Solved!')}
      {tips([
        'Look at the front-right corner. Repeat <b>Righty</b> until its gray '
        'sticker faces up. The lower part will look scrambled &mdash; that is '
        'normal, it fixes itself.',
        'Now turn ONLY the gray top face to bring the next un-twisted corner to '
        'the front-right, and repeat. Do not turn anything else.',
        'When the last corner twists up, a final turn of the gray face snaps '
        'the whole puzzle solved. You did it!',
      ])}
      {tiles}
    '''
    page(body, 7)
```

- [ ] **Step 4: Wire the stage pages into `assemble()`**

In `build/guide_kilo.py`, change `assemble()` to:

```python
def assemble():
    PAGES.clear()
    cover()
    pieces_page()
    notation()
    white_corners_page()
    upper_ring_page()
    lower_ring_page()
    ll_permute_page()
    ll_orient_page()
    backpage()
    return PAGES
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m tests.test_guides`
Expected: PASS — prints `test_guides: OK` (9 pages now).

- [ ] **Step 6: Run the full regression gate and build the PDF**

Run: `python3 -m tests.test_puzzle && python3 -m tests.test_core && python3 -m tests.test_kilo && python3 -m tests.test_solver_opt && python3 -m tests.test_guides`
Expected: all five print their OK lines.

Then build the actual PDF (needs weasyprint):
Run: `python3 build/guide_kilo.py`
Expected: prints `wrote .../out/guide_kilo.pdf (9 pages)`. If weasyprint is not installed, report that — the HTML build and smoke test still prove the booklet assembles; the PDF is a manual artifact.

- [ ] **Step 7: Commit**

```bash
git add build/guide_kilo.py tests/test_guides.py
git commit -m "feat: guide_kilo solving-stage pages (white/upper/lower/LL permute/LL orient)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage** (against `2026-06-19-kilominx-phase-d-booklet-design.md`):
- Extract `guide_common.py`; `make_guide` imports framework, content unchanged → Task 1 (byte-identical gate). ✓
- `holding(text, puzzle_name='Megaminx')` → Task 1 (guide_common), used with `'Kilominx'` in Tasks 3–4. ✓
- Renderer circle for `center_shape == 'circle'`, megaminx unchanged → Task 2. ✓
- `guide_kilo.py` 9 pages (cover, pieces, notation, 5 stages, back), diagrams from sim states → Tasks 3–4. ✓
- Two taught algs imported from `minx.solver` (`RIGHTY`, `CORNER_CYCLE`), not hardcoded → Tasks 3–4 import them. ✓
- Outputs `out/guide_kilo.{html,pdf}`; megaminx keeps `out/guide.*` → Task 1 `render_booklet(stem)`, Task 3/4 `build()`. ✓
- Build-smoke test in `tests/test_guides.py` (pages + embedded SVG, no weasyprint) → Tasks 2–4. ✓
- Full regression gate (5 suites) + manual dual-PDF review → Task 4 Step 6 + Global Constraints. ✓
- Out of scope (coach site, Ortega, dead-end hardening) → correctly absent. ✓

**Placeholder scan:** No TBD/TODO/"handle edge cases". Task 1 relocations name exact source functions + current line ranges (a pure move, not a vague reference). Every new function is written in full. The "inverse of RIGHTY" demo uses the concrete string `"DRi Ri DR R"` (the reverse-and-invert of `Ri DRi R DR`). The byte-identity check is a concrete `diff` command.

**Type/name consistency:** `assemble()`/`build()`/`page()`/`picture()`/`tiles_html()`/`corner_ids()`/`center_id()` and globals `K`/`WHITE`/`FRONT`/`GRAY`/`NAMES`/`LNAMES`/`CMAP` are defined in Task 3 and used identically in Task 4. `guide_common` exports (Task 1) match the imports in `make_guide` (Task 1) and `guide_kilo` (Task 3). `render()`'s new tagged-`polys` tuple `('circle'|'poly', geom, fill)` is produced and consumed in the same Task 2 edit. `R.Camera(..., puzzle=K)` and `R.render(..., puzzle=K)` match the real signatures in `minx/render.py`. The last-layer bright sets collect gray corners directly from `corner_slots` rather than assuming `adj[GRAY]` is ring-ordered (it is index-ordered).
