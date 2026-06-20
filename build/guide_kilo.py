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
