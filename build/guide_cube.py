#!/usr/bin/env python3
"""Generate the 4x4 Rubik's Cube Solution Guide booklet (HTML -> PDF).

A kid-friendly, picture-based guide in the style of the official Rubik's
booklet, built for the 4x4 by *reduction*: solve the centres, pair the edges,
then solve it exactly like a 3x3 (with two extra "parity" fixes the 3x3 never
needs). Every diagram is rendered straight from a verified Cube simulator state
(see minx/method_cube.py and tests/test_cube.py), so the booklet is correct by
construction. Reuses the shared booklet framework (guide_common, guide.css) and
the shared SVG renderer (minx/render.py via minx/cube_render.py).
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'build'))

from minx import cube as C
from minx import cube_render as CR
from minx.method_cube import (Cube4Solver, scramble, EO, NIKLAS, PLL_PARITY,
                              OLL_PARITY, CENTER_BAR_LIFT,
                              CENTER_LAST_TWO_COLUMN, CENTER_LAST_TWO_ROW,
                              CENTER_LAST_TWO_DIAG)
from guide_common import (svg_img, goal_box, banner, holding, tips, congrats,
                          F, colorword, render_booklet)

OUT = ROOT / 'out'
OUT.mkdir(exist_ok=True)

P4 = C.CUBE4
ST = P4.stickers
U, D, R, L, Fr, B = 0, 1, 2, 3, 4, 5          # face indices
CMAP = CR.color_map(U, Fr, P4)                # fixed colour identity (yellow up)
WHITEW = colorword('WHITE', '#5a6470')
YELLOWW = colorword('YELLOW', '#caa800')
PR = "<i>'</i>"           # the counter-clockwise (prime) mark, e.g. R'

PAGES = []


def page(body, number=None, cls=''):
    num = ''
    if number is not None:
        side = 'left' if number % 2 else 'right'
        num = f'<div class="pagenum {side}">{number}</div>'
    PAGES.append(f'<div class="page {cls}">{body}{num}</div>')


def pic(state, cam_u=U, cam_f=Fr, size=120, bright=None, arrow=None,
        tilt=0.5, yaw=0.4):
    svg = CR.render(state, cam_u, cam_f, CMAP, size=size,
                    cam=CR.camera(P4, cam_u, cam_f, tilt=tilt, yaw=yaw),
                    arrow=arrow, bright_ids=bright, puzzle=P4)
    return svg_img(svg)


# --- a solved example solve, used to render real stage states ---------------
SOLVE = Cube4Solver(scramble(P4.state(), n=40, seed=7))
SOLVE.solve()
STEPS = {s.stage: s for s in SOLVE.solution.steps}


def stage_state(stage):
    """The cube state right after the named stage of the example solve."""
    return P4.state(STEPS[stage].state_after)


# Cube notation -> per-quarter (face_index, click) for drawing arrow tiles.
_LET = {'U': U, 'D': D, 'R': R, 'L': L, 'F': Fr, 'B': B}


def expand_cube(alg):
    out = []
    for tok in alg.split():
        if tok[0] in '0123456789' or 'w' in tok:   # slice/wide: not tiled
            out.append((tok, None))
            continue
        f = _LET[tok[0]]
        times = 2 if tok.endswith('2') else 1
        click = -1 if "'" in tok else 1
        for _ in range(times):
            out.append((tok, (f, click)))
    return out


def tiles(state, alg, cam_u=U, cam_f=Fr, size=78):
    m = state.copy()
    cells = []
    for tok, mv in expand_cube(alg):
        if mv is None:
            svg = CR.render(m, cam_u, cam_f, CMAP, size=size,
                            cam=CR.camera(P4, cam_u, cam_f), puzzle=P4)
            cells.append(f'<div class="tile">{svg_img(svg)}'
                         f'<div class="movebox">{tok}</div></div>')
            m.move(tok)
            continue
        f, click = mv
        svg = CR.render(m, cam_u, cam_f, CMAP, size=size,
                        cam=CR.camera(P4, cam_u, cam_f), arrow=(f, click),
                        puzzle=P4)
        disp = tok
        cells.append(f'<div class="tile">{svg_img(svg)}'
                     f'<div class="movebox">{disp}</div></div>')
        m.move(tok)
    return '<div class="tiles wrap">' + ''.join(cells) + '</div>', m


# --- piece-finding helpers --------------------------------------------------
def corner_ids(faces):
    fs = set(faces)
    for ids in P4.corners:
        if set(ST[i].face for i in ids) == fs:
            return list(ids)


def edge_ids(faces):
    fs = frozenset(faces)
    out = []
    for ids in P4.edges:
        if frozenset(ST[i].face for i in ids) == fs:
            out += list(ids)
    return out


def center_ids(face):
    return [ids[0] for ids in P4.centers if ST[ids[0]].face == face]


def center_setup(swap_pairs):
    """A canonical 4x4 state with chosen center stickers swapped (used to
    demonstrate a center algorithm from a recognisable starting position).
    Pairs are sticker ids; everything else stays solved."""
    cols = list(P4.state().state)
    for a, b in swap_pairs:
        cols[a], cols[b] = cols[b], cols[a]
    return P4.state(colors=cols)


# ===========================================================================
# Pages
# ===========================================================================

def cover():
    hero = pic(P4.state(), size=320, tilt=0.55, yaw=0.45)
    body = f'''
      <div class="cover">
        <div class="coverlogo">
          <div class="coverdiamond"></div>
          <div class="covertitle">4&times;4 CUBE</div>
          <div class="coverribbon">6 SIDES &middot; 24 CENTERS &middot;
            24 EDGES &middot; 8 CORNERS</div>
        </div>
        <div class="coversub">SOLUTION GUIDE</div>
        <div class="coverhero">{hero}</div>
        <div class="coverunlock">Solve it like a 3&times;3!</div>
      </div>'''
    page(body, None, cls='coverpage')


def pieces_page():
    m = P4.state()
    corner = pic(m, bright=set(corner_ids((U, Fr, R))), size=104)
    edge = pic(m, bright=set(edge_ids((U, Fr))), size=104)
    center = pic(m, bright=set(center_ids(Fr)), size=104)
    body = f'''
      {banner(1, 'GET TO KNOW YOUR<br/>4&times;4 CUBE')}
      <div class="defs">THE BIG IDEA</div>
      <div class="note">A 4&times;4 has no fixed centers and its edges are split
      into <b>two halves</b>. The trick is <b>reduction</b>: first build the
      center blocks and join the edge halves, and then the whole puzzle behaves
      <b>exactly like a 3&times;3</b> &mdash; so you finish it with the same
      moves you already know.</div>
      <div class="parts">THE PARTS:</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#e02020">CORNER PIECES</div>
        Three (3) colors. There are <b>eight (8)</b>, one at each corner of the
        cube &mdash; just like a 3&times;3.
      </div>{corner}</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#0fa84e">EDGE PIECES (WINGS)</div>
        Two (2) colors. There are <b>24</b>, in matching pairs. Two wings of
        the same two colors make one 3&times;3 edge once you pair them.
      </div>{edge}</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#1565d8">CENTER PIECES</div>
        One (1) color, four to a face (<b>24</b> total). They are <b>not</b>
        fixed &mdash; you build each face's 2&times;2 center block yourself.
      </div>{center}</div>
      <div class="note">{WHITEW} and {YELLOWW} are on opposite faces. We build
      the white side first and finish on the yellow side. <i>(Use YOUR cube's
      colors; the steps are the same.)</i></div>
    '''
    page(body, 1)


def notation():
    m = P4.state()
    cells = []
    for tok in ('U', "U'", 'D', "D'", 'R', "R'", 'L', "L'", 'F', "F'",
                'B', "B'"):
        f = _LET[tok[0]]
        click = -1 if "'" in tok else 1
        svg = CR.render(m, U, Fr, CMAP, size=80, cam=CR.camera(P4, U, Fr),
                        arrow=(f, click), puzzle=P4)
        cells.append(f'<div class="tile">{svg_img(svg)}'
                     f'<div class="movebox">{tok}</div></div>')
    body = f'''
      <div class="topbar"><div class="banner wide">EACH FACE TURN HAS A
      LETTER</div></div>
      <div class="note">A letter alone (like {F("R")}) means turn that face a
      quarter turn <b>clockwise</b> as you look straight at it. A letter with an
      <i>apostrophe</i> ({F("R")}<i>'</i>) means <b>counter-clockwise</b>. A
      letter with a <b>2</b> (R2) means a half turn. <b>U</b>p, <b>D</b>own,
      <b>R</b>ight, <b>L</b>eft, <b>F</b>ront, <b>B</b>ack.</div>
      <div class="note">For the very last "parity" page you will also use
      <b>wide</b> turns, written like <b>Rw</b> &mdash; turn the face <b>and</b>
      the slice next to it together (two layers at once).</div>
      <div class="veryimportant">VERY IMPORTANT</div>
      <div class="note">Hold your cube to match each picture before you start a
      sequence. Dark gray in a picture means <b>that color does not
      matter</b>.</div>
      <div class="tiles wrap">{''.join(cells)}</div>
    '''
    page(body, 2)


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


def edges_page():
    goal = pic(stage_state('edge-pairing'), size=120)
    body = f'''
      {banner(4, 'PAIR THE EDGES')}
      {holding('Find two edge wings that share the same two colors and join '
               'them so they sit side by side as one edge. Repeat until all '
               '12 edges are paired.', '4&times;4')}
      {goal_box(goal, 'Goal: 12 joined edges')}
      {tips([
        'Bring one wing to the top-front and its matching wing next to it, '
        'then turn a wide layer to lock them together &mdash; and turn it back '
        'so the centers stay solid.',
        'Keep finished pairs out of the way (in the top or bottom) while you '
        'join the next pair.',
        'Once all 12 edges are joined, STOP using slice and wide turns. From '
        'here, only turn whole faces &mdash; your 4&times;4 is now a '
        '3&times;3!',
      ])}
    '''
    page(body, 5)


def white_cross_page():
    goal = pic(stage_state('3x3:cross'), cam_u=D, cam_f=Fr, size=120)
    body = f'''
      {banner(5, 'MAKE THE WHITE CROSS')}
      {holding(f'Turn the cube so {WHITEW} is on the bottom. Make a white plus '
               'on the bottom, and make each edge&rsquo;s side color match its '
               'center.', '4&times;4')}
      {goal_box(goal, 'Goal: a white cross')}
      {tips([
        'Find a white edge, line it up under the matching side center, then '
        'turn that face twice to drop it into the cross.',
        'If a white edge is flipped, take it to the top first, then bring it '
        'down the right way.',
        'This is exactly the 3&times;3 white cross &mdash; only whole-face '
        'turns from now on.',
      ])}
    '''
    page(body, 6)


def white_corners_page():
    goal = pic(stage_state('3x3:first-layer-corners'), cam_u=D, size=120)
    demo, _ = tiles(P4.state(), "R U R'", cam_u=U)
    body = f'''
      {banner(6, 'FINISH THE WHITE LAYER')}
      {holding('Put the four white corners in place to complete the bottom '
               'layer, white on the bottom and side colors matching.',
               '4&times;4')}
      {goal_box(goal, 'Goal: full white layer')}
      {tips([
        'Find a white corner in the top layer, hold it above the empty corner '
        'where it belongs.',
        f'Use {F("R")} {F("U")} {F("R")}{PR} (and a top turn between '
        'tries) to drop it in with white on the bottom.',
      ])}
      {demo}
    '''
    page(body, 7)


def middle_page():
    goal = pic(stage_state('3x3:middle-layer'), cam_u=D, size=120)
    demo, _ = tiles(P4.state(), "U R U' R' U' F' U F", cam_u=U)
    body = f'''
      {banner(7, 'SOLVE THE MIDDLE EDGES')}
      {holding('Flip the cube so white is on the bottom and yellow on top. '
               'Place the four middle-layer edges (the ones with no yellow).',
               '4&times;4')}
      {goal_box(goal, 'Goal: two layers done')}
      {tips([
        'Find a top edge with no yellow. Turn the top so its front color '
        'matches a side center, making a sideways T.',
        f'If it belongs to the right, do {F("U")} {F("R")} {F("U")}{PR} '
        f'{F("R")}{PR} {F("U")}{PR} {F("F")}{PR} {F("U")} '
        f'{F("F")}. Mirror it for the left.',
      ])}
      {demo}
    '''
    page(body, 8)


def yellow_cross_page():
    goal = pic(stage_state('3x3:last-layer-orient'), size=120)
    demo, _ = tiles(P4.state(), EO)
    body = f'''
      {banner(8, 'YELLOW CROSS &amp; TOP')}
      {holding('With yellow on top, make a yellow cross, then make the whole '
               'top face yellow.', '4&times;4')}
      {goal_box(goal, 'Goal: yellow top')}
      {tips([
        f'For the cross, repeat {F("F")} {F("R")} {F("U")} {F("R")}{PR} '
        f'{F("U")}{PR} {F("F")}{PR} until the yellow plus appears.',
        'Then orient the yellow corners (turn the top so an unsolved corner is '
        'front-right and repeat a corner move) until the whole top is yellow.',
      ])}
      {demo}
    '''
    page(body, 9)


def last_layer_page():
    goal = pic(P4.state(), size=120)
    demo, _ = tiles(P4.state(), NIKLAS)
    body = f'''
      {banner(9, 'FINISH THE LAST LAYER')}
      {holding('Move the last pieces into place: first the corners, then the '
               'edges, until the cube is solved.', '4&times;4')}
      {goal_box(goal, 'Goal: solved!')}
      {tips([
        'Position the yellow corners using a corner 3-cycle, turning the top '
        'between tries so the solved corners stay put.',
        'Then cycle the last edges into place. These are the same last-layer '
        'moves as the 3&times;3.',
      ])}
      {demo}
    '''
    page(body, 10)


def parity_page():
    pll, _ = tiles(P4.state(), PLL_PARITY)
    body = f'''
      {banner(10, 'PARITY (4&times;4 ONLY)')}
      <div class="note">Because a 4&times;4 has split edges, you can reach two
      cases a 3&times;3 never shows. They are not mistakes &mdash; just do the
      matching fix and keep going.</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#0fa84e">ONE FLIPPED EDGE (OLL)</div>
        If a single last-layer edge looks flipped while making the yellow cross,
        do:<br/><b>{OLL_PARITY}</b>
      </div></div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#7b2fbe">TWO SWAPPED EDGES (PLL)</div>
        If only two last-layer edges need to swap at the very end, do:<br/>
        <b>{PLL_PARITY}</b>
      </div></div>
      {pll}
    '''
    page(body, 11)


def back_page():
    body = f'''
      {congrats('You reduced a 4&times;4 to a 3&times;3 and solved it! '
                'Centers, then edges, then the same moves you know. '
                'Now mix it up and do it again.')}
      <div class="note" style="text-align:center;margin-top:24px">
        Every picture in this booklet was drawn by a computer model of the cube
        that checks every move really works.
      </div>
    '''
    page(body, None, cls='backpage')


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


def main():
    pages = assemble()
    render_booklet(pages, OUT, 'guide_cube', ROOT)


if __name__ == '__main__':
    main()
