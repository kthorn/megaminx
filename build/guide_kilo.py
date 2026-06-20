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
    white_corners_page()
    upper_ring_page()
    lower_ring_page()
    ll_permute_page()
    ll_orient_page()
    backpage()
    return PAGES


def build():
    render_booklet(assemble(), OUT, 'guide_kilo', ROOT)


if __name__ == '__main__':
    build()
