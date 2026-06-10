#!/usr/bin/env python3
"""Generate the Megaminx Solution Guide booklet (HTML -> PDF).

Every puzzle picture is rendered from a simulator state, so diagrams are
correct by construction.  Style mirrors the official Rubik's 2010 booklet.
"""
import sys, pathlib, math
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from minx import puzzle as P, method as M, render as R
from tests.test_puzzle import canonical_hold

OUT = ROOT / 'out'
OUT.mkdir(exist_ok=True)

NAMES = canonical_hold()
WHITE = NAMES['U']
GRAY = P.OPP[WHITE]
CMAP = R.color_map(WHITE, NAMES['F'])
LNAMES = P.name_faces(GRAY, P.ADJ[GRAY][0])   # gray-up grip for LL pages

FACE_LETTER_COLORS = {
    'U': '#1565d8', 'F': '#0fa84e', 'R': '#e02020', 'L': '#ff8a00',
    'D': '#7b2fbe', 'BR': '#1565d8', 'BL': '#1565d8',
}


def piece_ids(kind, faces):
    if kind == 'corner':
        return M.CORNER_SLOTS[M.corner_key(faces)]
    return M.EDGE_SLOTS[M.edge_key(faces)]


def bright_for(*piece_lists):
    out = set()
    for ids in piece_lists:
        out.update(ids)
    return out


def white_layer_ids():
    out = set()
    for i, s in enumerate(P.STICKERS):
        if i in P.LAYERS[WHITE]:
            out.add(i)
    # plus the white-face centre etc. all included via layer
    return out


def layer_ids(face):
    return set(P.LAYERS[face])


def svg_img(svg, cls='pic', w=None):
    import base64
    b64 = base64.b64encode(svg.encode()).decode()
    style = f' style="width:{w}"' if w else ''
    return f'<img class="{cls}" src="data:image/svg+xml;base64,{b64}"{style}/>'


def expand_alg(alg):
    """'R U2i Ri' -> [('R',1), ('U',-1), ('U',-1), ('R',-1)] as (token, click)
    pairs with one tile per click."""
    out = []
    for name, times in P.parse_alg(alg):
        step = 1 if times > 0 else -1
        for _ in range(abs(times)):
            out.append((name, step))
    return out


def display_letter(token, click):
    t = 'D' if token == 'DR' else token
    return t + ('i' if click < 0 else '')


def tiles_html(state, names, alg, cam_u, cam_f, bright=None, size=86):
    """A row of move tiles: puzzle picture (with arrow) above a letter box.
    Mutates a copy of state, returns (html, final_state)."""
    m = state.copy()
    cells = []
    for token, click in expand_alg(alg):
        face = names[token]
        svg = R.render(m, cam_u, cam_f, CMAP, size=size,
                       cam=R.Camera(cam_u, cam_f),
                       arrow=(face, click), bright_ids=bright)
        letter = display_letter(token, click)
        cells.append(
            f'<div class="tile">{svg_img(svg)}'
            f'<div class="movebox">{letter.replace("i", "<i>i</i>")}</div></div>')
        m.turn(face, click)
    return '<div class="tiles">' + ''.join(cells) + '</div>', m


def picture(state, cam_u, cam_f, bright=None, size=110, arrow=None,
            tilt=0.42, yaw=0.18):
    svg = R.render(state, cam_u, cam_f, CMAP, size=size,
                   cam=R.Camera(cam_u, cam_f, tilt=tilt, yaw=yaw),
                   arrow=arrow, bright_ids=bright)
    return svg_img(svg)


def goal_box(inner, caption='Your Goal'):
    return (f'<div class="goal">{inner}'
            f'<div class="goalstar">{caption}</div></div>')


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

PAGES = []


def page(body, number=None, cls=''):
    num = ''
    if number is not None:
        side = 'left' if number % 2 else 'right'
        num = f'<div class="pagenum {side}">{number}</div>'
    PAGES.append(f'<div class="page {cls}">{body}{num}</div>')


def banner(stage, title):
    return (f'<div class="topbar"><div class="stagebadge">STAGE {stage}:</div>'
            f'<div class="banner">{title}</div></div>')


def holding(text):
    return (f'<div class="holding"><span class="holdhead">Holding Your '
            f'Megaminx:</span> {text}</div>')


def tips(items):
    lis = ''.join(f'<li>{i}</li>' for i in items)
    return f'<div class="tips"><span class="tiphead">Tips:</span><ul>{lis}</ul></div>'


def congrats(text):
    return (f'<div class="congrats"><div class="congratsbanner">'
            f'Congratulations!</div><div class="congratsbody">{text}</div></div>')


def F(letter):   # colored face letter like the original's (U) (R)
    col = FACE_LETTER_COLORS.get(letter.rstrip('i'), '#1565d8')
    return f'<span class="facelet" style="color:{col}">({letter})</span>'


def colorword(word, color):
    return f'<span style="color:{color};font-weight:800">{word}</span>'


WHITEW = colorword('WHITE', '#5a6470')
GRAYW = colorword('GRAY', '#6f7a85')


# --- cover ------------------------------------------------------------------

def cover():
    hero = picture(P.Minx(), WHITE, NAMES['F'], size=320)
    body = f'''
      <div class="cover">
        <div class="coverlogo">
          <div class="coverdiamond"></div>
          <div class="covertitle">MEGAMINX</div>
          <div class="coverribbon">12 SIDES &middot; 50 PIECES &middot; ONE SECRET</div>
        </div>
        <div class="coversub">SOLUTION GUIDE</div>
        <div class="coverhero">{hero}</div>
        <div class="coverunlock">Unlock the Secret!</div>
      </div>'''
    page(body, None, cls='coverpage')


# --- stage 1: get to know ----------------------------------------------------

def stage1():
    m = P.Minx()
    # example pieces
    e_ids = piece_ids('edge', (WHITE, NAMES['F']))
    c_ids = piece_ids('corner', (WHITE, NAMES['F'], NAMES['R']))
    ctr_ids = [P.ID_TO_IDX[(NAMES['F'], 'center', 0)]]
    edge_pic = picture(m, WHITE, NAMES['F'], bright=set(e_ids), size=104)
    corner_pic = picture(m, WHITE, NAMES['F'], bright=set(c_ids), size=104)
    center_pic = picture(m, WHITE, NAMES['F'], bright=set(ctr_ids), size=104)
    body = f'''
      {banner(1, 'GET TO KNOW YOUR<br/>MEGAMINX')}
      <div class="defs">DEFINITIONS OF MEGAMINX PIECES</div>
      <div class="parts">THE PARTS:</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#e02020">EDGE PIECES</div>
        PIECES WITH TWO (2) COLORS. THERE ARE THIRTY (30) EDGE PIECES.
        FIVE OF THEM HAVE A WHITE SIDE &mdash; THEY MAKE THE WHITE STAR.
      </div>{edge_pic}</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#0fa84e">CORNER PIECES</div>
        PIECES WITH THREE (3) COLORS. THERE ARE TWENTY (20) CORNER PIECES.
      </div>{corner_pic}</div>
      <div class="partrow"><div class="parttext">
        <div class="parthead" style="color:#1565d8">CENTER PIECES</div>
        PIECES WITH ONE (1) COLOR. THERE ARE TWELVE (12), ONE ON EACH FACE.
        THEY <b>DO NOT MOVE</b> AND REPRESENT THE COLOR OF THEIR FACE.
      </div>{center_pic}</div>
      <div class="note">A megaminx has <b>12 faces</b> and <b>12 colors</b>.
      Each color appears on exactly one face. {WHITEW} and {GRAYW} are on
      opposite faces &mdash; you will start with the white face and finish with
      the gray one. <i>(Some megaminxes use slightly different colors &mdash;
      use the face colors of YOUR puzzle; the steps are the same.)</i></div>
    '''
    page(body, 1)


# --- notation page -----------------------------------------------------------

def notation():
    m = P.Minx()
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
            svg = R.render(m, WHITE, NAMES['F'], CMAP, size=80,
                           cam=R.Camera(WHITE, NAMES['F']),
                           arrow=(face, click))
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
      <div class="topbar"><div class="banner wide">EACH FACE OF THE MEGAMINX
      IS REPRESENTED BY A LETTER</div></div>
      {''.join(rows)}
      <div class="note"><b>A letter with an <i>"i"</i> after it</b> means an
      <b>inverted</b> (counter-clockwise) turn of that face. A letter alone
      means a clockwise turn (as you look at that face). Every turn is
      <b>one click</b> &mdash; one fifth of the way around.</div>
      <div class="veryimportant">VERY IMPORTANT</div>
      <div class="note">The pictures show exactly which face moves and which
      way. Hold your megaminx to match the picture before each sequence.
      Dark gray on a picture means <b>the color there does not matter</b>.</div>
      <div class="tiles wrap">{''.join(tile_cells)}</div>
    '''
    page(body, 2)


# --- stage 2: white star -----------------------------------------------------

def stage2():
    star_ids = bright_for(*[piece_ids('edge', (WHITE, f)) for f in P.ADJ[WHITE]])
    star_ids |= {P.ID_TO_IDX[(WHITE, 'center', 0)]}
    goal_state = P.Minx()
    goalp = picture(goal_state, WHITE, NAMES['F'], bright=star_ids, size=104)

    # flipped-edge demo: invert the fix alg so replaying the fix solves it
    demo = P.Minx()
    P.apply_alg(demo, "U L Ui F", NAMES)   # inverse of Fi U Li Ui
    flip_pic = picture(demo, WHITE, NAMES['F'], bright=star_ids |
                       set(piece_ids('edge', (WHITE, NAMES['F']))), size=92)
    tiles, _ = tiles_html(demo, NAMES, M.FLIP_FIX, WHITE, NAMES['F'],
                          bright=star_ids |
                          set(piece_ids('edge', (WHITE, NAMES['F']))))
    body = f'''
      {banner(2, 'SOLVE THE WHITE STAR')}
      {holding(f'Hold your megaminx with the {WHITEW} center piece on top '
               f'{F("U")}. You will make a white star, and the side color of '
               'each star edge must match its side center piece.')}
      {goal_box(goalp)}
      {tips([
        'Find a white edge in the bottom part of the puzzle. Turning the '
        'bottom faces never disturbs finished star edges on top.',
        'Park it on the <b>bottom-right edge of the matching side face</b>, '
        'white sticker facing <b>down-right</b>; then turn that side face '
        '<b>twice counter-clockwise</b> &mdash; the edge rises into the star.',
        'Parked on the <b>bottom-left</b> with white facing down-left? Turn '
        'the side face <b>twice clockwise</b> instead. This stage is '
        'practice and trial-and-error, just like the white cross on your '
        'cube!',
      ])}
      <div class="note">If an edge is <b>in the star but flipped</b> (white
      facing out, like the picture), hold the puzzle so that edge is at the
      front and do this sequence:</div>
      <div class="demoline">{flip_pic}{tiles}</div>
      {congrats('If the top of your megaminx shows a white star with every '
                'side color matching its center, you can move to <b>Stage 3</b>!')}
    '''
    page(body, 3)


# --- stage 3: white corners --------------------------------------------------

def stage3():
    wl = layer_ids(WHITE)
    cslot = piece_ids('corner', (WHITE, NAMES['F'], NAMES['R']))
    stage_slot = piece_ids('corner', (NAMES['F'], NAMES['R'], NAMES['DR']))
    sfaces = [P.STICKERS[i].face for i in stage_slot]
    cc = [WHITE, NAMES['F'], NAMES['R']]

    goalp = picture(P.Minx(), WHITE, NAMES['F'], bright=wl, size=100)

    # three staging orientations (physical rotations of the corner)
    case_pics = []
    found = set()
    import itertools
    for perm in itertools.permutations(cc):
        o = dict(zip(sfaces, perm))
        showing = next(f for f, c in o.items() if c == WHITE)
        if showing in found:
            continue
        m = P.Minx()
        for i in stage_slot:
            m.state[i] = o[P.STICKERS[i].face]
        for i in cslot:
            m.state[i] = 99   # unknown-yet slot: gets dimmed anyway
        pic = picture(m, WHITE, NAMES['F'],
                      bright=wl | set(stage_slot), size=92,
                      tilt=0.62, yaw=0.42)
        case_pics.append(pic)
        found.add(showing)
        if len(case_pics) == 3:
            break

    demo = P.Minx()
    for _ in range(4):   # righty-inverse x4 == righty x2 staged state
        P.apply_alg(demo, M.RIGHTY, NAMES)
    tiles, _ = tiles_html(demo, NAMES, M.RIGHTY, WHITE, NAMES['F'],
                          bright=wl | set(stage_slot) | set(cslot))
    body = f'''
      {banner(3, 'SOLVE THE WHITE CORNERS')}
      {holding(f'Keep the {WHITEW} star on top {F("U")}. Now you will fill in '
               'the five white corners, one at a time.')}
      {goal_box(goalp)}
      {tips([
        'Find a white corner in the bottom part of the puzzle and turn the '
        'bottom faces until it sits <b>directly below its place</b> (between '
        'the two side colors that match it).',
        'Hold the puzzle so that corner is at the <b>front-right</b>, just '
        'below the top, like the three pictures below. The white sticker can '
        'face three ways &mdash; the sequence works for all of them!',
      ])}
      <div class="cases">{''.join(case_pics)}</div>
      <div class="note">Now do this sequence <b>over and over</b> (2, 4 or up
      to 6 times) <b>UNTIL</b> the corner pops into place with white on top:</div>
      {tiles}
      <div class="note"><b>NOTE!</b> If a white corner is stuck in the top
      layer in the wrong spot or twisted, hold the puzzle so it is at the
      top-front-right and do the sequence <b>once</b> &mdash; it will pop out
      below. Then place it the normal way.</div>
      {congrats('If the whole white face and its side colors are solid, you '
                'are ready for <b>Stage 4</b>!')}
    '''
    page(body, 4)


# --- stage 4: second row of edges ---------------------------------------------

S4 = {'helper': 9, 'F': 5, 'R': 6}


def s4_bright():
    out = layer_ids(WHITE)
    for f in P.ADJ[WHITE]:
        for g in P.ADJ[WHITE]:
            if g in P.ADJ[f] and f < g:
                out |= set(piece_ids('edge', (f, g)))
    return out


def stage4():
    h, ff, rr = S4['helper'], S4['F'], S4['R']
    grip = P.name_faces(h, ff)
    bright = s4_bright()
    slot = piece_ids('edge', (ff, rr))

    goalp = picture(P.Minx(), WHITE, NAMES['F'], bright=bright, size=100)
    holdpic = picture(P.Minx(), h, ff, bright=bright, size=92)

    demoR = P.Minx()
    P.apply_alg(demoR, "Fi Ui F U R U Ri Ui", grip)  # inverse of right insert
    matchpic = picture(demoR, h, ff, bright=bright | set(slot), size=92)
    tilesR, _ = tiles_html(demoR, grip, M.INSERT_RIGHT, h, ff,
                           bright=bright | set(slot))
    gripL = P.name_faces(h, rr)   # mirror demo: slot to the front-left
    slotL = piece_ids('edge', (gripL['F'], gripL['L']))
    demoL = P.Minx()
    P.apply_alg(demoL, "F U Fi Ui Li Ui L U", gripL)  # inverse of left insert
    tilesL, _ = tiles_html(demoL, gripL, M.INSERT_LEFT, h, gripL['F'],
                           bright=bright | set(slotL))
    body = f'''
      {banner(4, 'SOLVE THE SECOND ROW<br/>OF EDGES')}
      {holding('Now <b>tilt the puzzle</b>! Hold it so the empty edge slot is '
               'at the <b>front</b> and the face just <b>below</b> the slot '
               f'points <b>up</b> &mdash; that is your new top {F("U")}:')}
      {goal_box(holdpic, 'Hold It Like This')}
      {tips([
        f'Turn the new top {F("U")} until the edge sits above the front face '
        'with its <b>front color matching</b> the front center &mdash; a '
        'straight line, just like on your cube!',
        f'The edge&rsquo;s top color points where it must go: toward {F("R")} '
        f'&rarr; sequence 1; toward {F("L")} &rarr; sequence 2.',
      ])}
      <div class="seqlabel">1) Edge goes down-and-RIGHT:</div>
      {tilesR}
      <div class="seqlabel">2) Edge goes down-and-LEFT:</div>
      {tilesL}
      {congrats('Do all five edges of the second row, then on to '
                '<b>Stage 5</b>!')}
    '''
    page(body, 5)


# --- stage 5: the petals (lone edges, then corner+edge pairs) -----------------

def stage5_edges():
    s = M.Solver(P.Minx(), WHITE)
    petals = s._petals()
    pn, corner, lone, flank = petals[0]
    bright = s4_bright()
    # highlight the lone slots on a solved puzzle (front petal clearest)
    m = P.Minx()
    outline = set()
    for pn2, c2, lone2, fl2 in petals:
        outline |= set(piece_ids('edge', lone2))
        outline -= set()  # keep all five; front ones read clearly
    lonepic_svg = R.render(m, WHITE, NAMES['F'], CMAP, size=110,
                           cam=R.Camera(WHITE, NAMES['F'], tilt=1.15,
                                        yaw=0.25),
                           outline_ids=outline)
    lonepic = svg_img(lonepic_svg)

    # demo insert for the lone edge of petal 0 (helper = other band2 face)
    a = next(f for f in lone if f in s.band1)
    x = next(f for f in lone if f in s.band2)
    helper = [h for h in P.ADJ[a] if h in P.ADJ[x] and h in s.band2][0]
    for ffc, rrc in ((a, x), (x, a)):
        nm = P.name_faces(helper, ffc)
        if nm['R'] == rrc:
            grip, front = nm, ffc
            alg, inv = M.INSERT_RIGHT, "Fi Ui F U R U Ri Ui"
            break
    else:
        for ffc, llc in ((a, x), (x, a)):
            nm = P.name_faces(helper, ffc)
            if nm['L'] == llc:
                grip, front = nm, ffc
                alg, inv = M.INSERT_LEFT, "F U Fi Ui Li Ui L U"
                break
    demo = P.Minx()
    P.apply_alg(demo, inv, grip)
    slot = piece_ids('edge', lone)
    tiles, _ = tiles_html(demo, grip, alg, helper, front,
                          bright=bright | set(slot))
    holdpic = picture(P.Minx(), helper, front, bright=bright | set(slot),
                      size=92)
    body = f'''
      {banner(5, 'THE MIDDLE BAND')}
      <div class="stephead">1<sup>st</sup> Step: place the five leaning edges</div>
      <div class="note">Around the middle of the puzzle there are slanted
      edge slots. In this step you place <b>one slanted edge above each
      petal</b> &mdash; always the one that <b>leans the same way</b>, shown
      outlined in red:</div>
      <div class="demoline">{lonepic}{holdpic}</div>
      {tips([
        'Tilt the puzzle so the empty slanted slot is at the front (second '
        'picture) and use exactly the same sequences as Stage 4.',
        'Go all the way around the puzzle: five slanted edges, one per petal. '
        '<b>Only these five!</b> The other five slanted slots get filled in '
        'the 2<sup>nd</sup> Step together with the corners.',
      ])}
      {tiles}
      <div class="note">Then continue straight to the 2<sup>nd</sup> Step on
      the next page.</div>
    '''
    page(body, 6)


def stage5_pairs():
    s = M.Solver(P.Minx(), WHITE)
    pn, corner, lone, flank = s._petals()[0]
    bright = s4_bright()
    for pn2, c2, l2, f2 in s._petals():
        bright |= set(piece_ids('edge', l2))
    cslot = piece_ids('corner', corner)
    eslot = piece_ids('edge', flank)
    stage_slot = piece_ids('corner', (pn['F'], pn['R'], pn['DR']))
    sfaces = [P.STICKERS[i].face for i in stage_slot]

    # two staging cases derived in the simulator:
    #   white..er top-color on local F  -> edge at (R,DR) reversed
    #   top-color on local R            -> edge at (DR, D-of-DR...) normal
    probe = P.Minx(); P.apply_alg(probe, M.RIGHTY, pn)
    feed = [ids for key, ids in M.EDGE_SLOTS.items()
            if tuple(ids) != tuple(eslot)
            and any(probe.state[i] != P.STICKERS[i].face for i in ids)]
    cc = list(corner)
    by_orient = {}
    import itertools as it
    for perm in it.permutations(cc):
        o = dict(zip(sfaces, perm))
        okey = tuple(sorted(o.items()))
        for fslot in feed:
            fa, fb = (P.STICKERS[i].face for i in fslot)
            for ca, cb in ((flank[0], flank[1]), (flank[1], flank[0])):
                m = P.Minx()
                for i in stage_slot:
                    m.state[i] = o[P.STICKERS[i].face]
                m.state[[i for i in fslot
                         if P.STICKERS[i].face == fa][0]] = ca
                m.state[[i for i in fslot
                         if P.STICKERS[i].face == fb][0]] = cb
                for i in cslot:
                    m.state[i] = 99
                for i in eslot:
                    m.state[i] = 98
                mm = m.copy()
                for rep in range(1, 8):
                    P.apply_alg(mm, M.RIGHTY, pn)
                    if all(mm.state[i] == P.STICKERS[i].face for i in cslot) \
                       and all(mm.state[i] == P.STICKERS[i].face
                               for i in eslot):
                        prev = by_orient.get(okey)
                        if prev is None or rep < prev[1]:
                            by_orient[okey] = (m, rep, set(fslot))
                        break
    case_pics = []
    for okey, (m, rep, fset) in sorted(by_orient.items(),
                                       key=lambda kv: kv[1][1]):
        pic = picture(m, pn['U'], pn['F'],
                      bright=bright | set(stage_slot) | fset, size=92)
        case_pics.append((pic, rep))

    demo = P.Minx()
    tiles, _ = tiles_html(demo, pn, M.RIGHTY, pn['U'], pn['F'],
                          bright=bright | set(stage_slot) | set(cslot)
                          | set(eslot))
    case_html = ''.join(
        f'<div class="paircase">{pic}<div class="pcap">repeat sequence '
        f'{rep}&times;</div></div>' for pic, rep in case_pics[:2])
    body = f'''
      {banner(5, 'THE MIDDLE BAND')}
      <div class="stephead">2<sup>nd</sup> Step: corner + edge pairs</div>
      {holding('Hold the puzzle so the empty petal pocket (a corner slot plus '
               'its last slanted edge slot) is at the <b>top front-right</b>. '
               'Just like Stage 3 &mdash; but the corner brings its edge '
               'along for the ride!')}
      {tips([
        'Park the corner <b>below its slot</b>, and its edge in one of the '
        'two parking spots shown &mdash; pick by which way the corner&rsquo;s '
        '<b>top color</b> faces:',
      ])}
      <div class="cases">{case_html}</div>
      <div class="note">Then repeat the Stage-3 sequence <b>until corner and
      edge BOTH snap in together</b> (up to 6 times):</div>
      {tiles}
      <div class="note"><b>NOTE!</b> Top color facing <b>down</b>? Do the
      sequence <b>once</b> and look again &mdash; it will match a picture.
      Piece stuck in a wrong slot? Pop it out as in Stage 3.</div>
      {congrats('Five pockets done? The middle band is finished &mdash; '
                'on to <b>Stage 6</b>!')}
    '''
    page(body, 7)


# --- stage 6: third row corners + ridge edges ---------------------------------

S6 = {'corner': (0, 3, 8), 'grip_u': 0, 'grip_f': 3, 'ridge': (3, 4)}


def stage6():
    bright = s4_bright()
    s = M.Solver(P.Minx(), WHITE)
    for pn2, c2, l2, f2 in s._petals():
        bright |= set(piece_ids('edge', l2)) | set(piece_ids('edge', f2))
        bright |= set(piece_ids('corner', c2))

    grip = P.name_faces(S6['grip_u'], S6['grip_f'])
    cslot = piece_ids('corner', S6['corner'])
    stage_slot = piece_ids('corner',
                           (grip['F'], grip['R'], grip['DR']))
    demo = P.Minx()
    for _ in range(4):
        P.apply_alg(demo, M.RIGHTY, grip)
    tiles, _ = tiles_html(demo, grip, M.RIGHTY, grip['U'], grip['F'],
                          bright=bright | set(stage_slot) | set(cslot))
    holdpic = picture(P.Minx(), grip['U'], grip['F'],
                      bright=bright | set(cslot), size=88)

    rgrip = P.name_faces(GRAY, S6['ridge'][0])
    rslot = piece_ids('edge', S6['ridge'])
    rdemo = P.Minx()
    P.apply_alg(rdemo, "Fi Ui F U R U Ri Ui", rgrip)
    rtiles, _ = tiles_html(rdemo, rgrip, M.INSERT_RIGHT, GRAY, rgrip['F'],
                           bright=bright | set(rslot))
    body = f'''
      {banner(6, 'THE LAST ROW OF CORNERS<br/>AND EDGES')}
      <div class="stephead">1<sup>st</sup> Step: the five low corners</div>
      <div class="demoline"><div class="note" style="flex:1">Tilt the puzzle
      even further: hold it so an empty low corner slot is at the top
      front-right (picture). Park the matching corner below it and repeat the
      Stage-3 sequence until it pops in &mdash; <b>exactly like before</b>.
      The staging area is now next to the {GRAYW} face, which is still
      unsolved, so nothing can break.</div>{holdpic}</div>
      {tiles}
      <div class="stephead">2<sup>nd</sup> Step: the five ridge edges</div>
      <div class="note">Now turn the puzzle so {GRAYW} is <b>on top</b> &mdash;
      and keep it there until the very end! The last five non-gray edges sit
      just below the gray face. Use the Stage-4 sequences: turn the gray top
      until the edge makes its straight line with the front center, then drop
      it right or left:</div>
      {rtiles}
      {congrats('Everything except the gray top layer is done &mdash; '
                'you are two thirds of the way! On to <b>Stage 7</b>.')}
    '''
    page(body, 8)


# --- stage 7: gray star --------------------------------------------------------

def ll_bright_edges():
    out = {P.ID_TO_IDX[(GRAY, 'center', 0)]}
    for f in P.ADJ[GRAY]:
        out |= set(piece_ids('edge', (GRAY, f)))
    return out


def stage7():
    ring = [LNAMES[k] for k in ['F', 'R', 'BR', 'BL', 'L']]
    bright = ll_bright_edges()

    def eo_state_pic(flipped_positions):
        m = P.Minx()
        for posname in flipped_positions:
            f = LNAMES[posname]
            ids = piece_ids('edge', (GRAY, f))
            up = next(i for i in ids if P.STICKERS[i].face == GRAY)
            side = next(i for i in ids if P.STICKERS[i].face != GRAY)
            m.state[up], m.state[side] = m.state[side], m.state[up]
        return picture(m, GRAY, LNAMES['F'], bright=bright, size=86,
                       tilt=0.12, yaw=0.0)

    case1 = eo_state_pic(['F', 'R', 'BL', 'L'])     # one gray edge (at BR)
    case2 = eo_state_pic(['F', 'R'])                # adjacent pair in front
    case3 = eo_state_pic(['F', 'BR'])               # skew pair
    demo = P.Minx()
    P.apply_alg(demo, "F R U Ri Ui Fi", LNAMES)   # inverse-ish for tiles
    tiles, _ = tiles_html(P.Minx(), LNAMES, M.STAR_EO, GRAY, LNAMES['F'],
                          bright=None)
    body = f'''
      {banner(7, 'MAKE THE GRAY STAR')}
      {holding(f'{GRAYW} stays on top {F("U")}. Look only at the five '
               f'<b>gray edge stickers</b> on top: how many face up?')}
      {tips([
        'You will always see exactly <b>1, 3 or 5</b> gray stickers facing '
        'up. (5 means the star is done &mdash; skip to Stage 8!)',
        'Match your puzzle to one of the pictures, hold it exactly that way, '
        'and do the sequence below. Re-count and repeat until the star is '
        'complete. The side colors do NOT need to match yet!',
      ])}
      <div class="cases labeled">
        <div class="case">{case1}<div class="pcap">1 gray edge: hold it at
        the <b>back-right</b>; sequence once, then re-match.</div></div>
        <div class="case">{case2}<div class="pcap">3 gray; the 2 odd ones
        <b>side by side</b>: hold them at <b>front&nbsp;+&nbsp;right</b>;
        sequence once &rarr; star!</div></div>
        <div class="case">{case3}<div class="pcap">3 gray; the 2 odd ones
        <b>apart</b>: hold them at <b>front + back-right</b>; sequence
        <b>twice</b> &rarr; star!</div></div>
      </div>
      {tiles}
      {congrats('Gray star on top? Excellent &mdash; <b>Stage 8</b>!')}
    '''
    page(body, 9)


# --- stage 8: position the star edges ------------------------------------------

def stage8():
    bright = ll_bright_edges()
    before = P.Minx()
    P.apply_alg(before, "R U2 Ri Ui R Ui Ri", LNAMES)  # inverse of edge cycle
    beforep = picture(before, GRAY, LNAMES['F'], bright=bright, size=92,
                      tilt=0.12, yaw=0.0)
    tiles, _ = tiles_html(before, LNAMES, M.EDGE_CYCLE, GRAY, LNAMES['F'],
                          bright=bright)
    body = f'''
      {banner(8, 'PUT THE STAR EDGES<br/>IN THEIR PLACES')}
      {holding(f'{GRAYW} on top. Now make every star edge&rsquo;s side color '
               'match its center.')}
      {tips([
        f'Spin the gray top {F("U")} until <b>as many edges as possible</b> '
        'match their side centers. At least two will match.',
        'Hold the puzzle so the two matching edges are at the <b>front</b> '
        'and <b>front-left</b> &mdash; the three wrong ones to the right and '
        'back, like the picture. Then do the sequence; it swaps the three '
        'wrong edges around. You may need it twice.',
        'If you can&rsquo;t find a hold with two matching edges, do the '
        'sequence once from any position and look again.',
      ])}
      <div class="demoline">{beforep}{tiles}</div>
      {congrats('Star perfect all around? <b>Stage 9</b> awaits!')}
    '''
    page(body, 10)


# --- stage 9: position the gray corners -----------------------------------------

def ll_bright_all():
    return set(P.LAYERS[GRAY]) | ll_bright_edges()


def stage9():
    bright = ll_bright_all()
    before = P.Minx()
    P.apply_alg(before, "Ri Fi BRi R BR Ri F R BRi Ri BR R", LNAMES)  # CP1 inv
    beforep = picture(before, GRAY, LNAMES['F'], bright=bright, size=92,
                      tilt=0.12, yaw=0.0)
    tiles, _ = tiles_html(before, LNAMES, M.CORNER_CYCLE, GRAY, LNAMES['F'],
                          bright=bright)
    body = f'''
      {banner(9, 'PUT THE GRAY CORNERS<br/>IN THEIR PLACES')}
      {holding(f'{GRAYW} on top. Now move each gray corner <b>between</b> '
               'the two side colors it matches. Twisted is OK &mdash; '
               'location is all that counts in this stage!')}
      {tips([
        'Find corners that are already <b>between the right colors</b>. '
        'Hold the puzzle so two correct corners are on the <b>left side</b> '
        '(front-left and back-left) &mdash; the three wrong ones at front-right, '
        'right and back.',
        'Do the sequence: it cycles the three wrong corners. Repeat from the '
        'same hold if needed.',
        'Fewer than two correct? Do the sequence once from any position and '
        'look again.',
      ])}
      <div class="demoline">{beforep}</div>
      {tiles}
      {congrats('All five corners between their right colors? One stage '
                'to go!')}
    '''
    page(body, 11)


# --- stage 10: twist the gray corners -------------------------------------------

def stage10():
    bright = ll_bright_all()
    before = P.Minx()
    P.apply_alg(before, M.RIGHTY + ' ' + M.RIGHTY, LNAMES)
    beforep = picture(before, GRAY, LNAMES['F'], bright=bright, size=92)
    tiles, _ = tiles_html(before, LNAMES, M.RIGHTY, GRAY, LNAMES['F'],
                          bright=bright)
    hero = picture(P.Minx(), GRAY, LNAMES['F'], size=140)
    body = f'''
      {banner(10, 'TWIST THE GRAY CORNERS')}
      {holding(f'{GRAYW} on top. Hold the puzzle with a twisted corner at the '
               '<b>top front-right</b> and repeat the good old Stage-3 '
               'sequence until its gray sticker faces up (2 or 4 times):')}
      <div class="demoline">{beforep}{tiles}</div>
      {tips([
        f'Then turn <b>ONLY the gray top</b> {F("U")} to bring the next '
        'twisted corner to the front-right, and repeat.',
        '<b>DON&rsquo;T PANIC!</b> The rest of the puzzle will look scrambled '
        'while you work &mdash; it fixes itself the moment the last corner '
        'is twisted right. Trust the moves, just like on your cube!',
        'When all corners are done, spin the gray top to line everything up.',
      ])}
      {congrats('<b>YOU DID IT!</b> Your megaminx is solved &mdash; all 12 '
                'colors, all 50 pieces. You have unlocked the secret!')}
      <div style="text-align:center">{hero}</div>
    '''
    page(body, 12)


# --- back page -------------------------------------------------------------------

def backpage():
    hero = picture(P.Minx(), WHITE, NAMES['F'], size=110)
    body = f'''
      <div class="topbar"><div class="banner wide">NOW YOU KNOW THE
      SECRET&hellip;</div></div>
      <div class="funhead">Fun Facts!</div>
      <div class="note">The megaminx was invented around 1982, soon after the
      Rubik&rsquo;s Cube craze began. Early versions were sold under names
      like the <b>Hungarian Supernova</b>.</div>
      <div class="note">A megaminx has about
      <b>100,669,616,553,523,347,122,516,032,313,645,505,168,688,116,411,019,
      768,627,200,000,000,000</b> possible positions &mdash; that&rsquo;s a
      1 followed by 68 digits. The Rubik&rsquo;s Cube has &ldquo;only&rdquo;
      43 quintillion!</div>
      <div class="note">The world record for solving a megaminx is under
      <b>25 seconds</b>. Every solve in this booklet was checked, move by
      move, on a computer model of the puzzle &mdash; so if you follow the
      pictures exactly, it always works.</div>
      <div class="note">The method you just learned is the same idea as your
      cube&rsquo;s: solve a star instead of a cross, drop in corners with the
      Righty moves, pair up the middle, then finish the last layer in four
      small steps. Bigger puzzle &mdash; same secret.</div>
      <div style="text-align:center;margin-top:14pt">{hero}</div>
      <div class="backcredit">Made for a young puzzler who already unlocked
      the cube. Happy twisting!</div>
    '''
    page(body, None, cls='backpage')


def build(pages_only=None):
    cover()
    stage1()
    notation()
    stage2()
    stage3()
    stage4()
    stage5_edges()
    stage5_pairs()
    stage6()
    stage7()
    stage8()
    stage9()
    stage10()
    backpage()
    css = (ROOT / 'build' / 'guide.css').read_text()
    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{css}</style></head><body>{''.join(PAGES)}</body></html>'''
    (OUT / 'guide.html').write_text(html)
    import weasyprint
    weasyprint.HTML(string=html, base_url=str(ROOT)).write_pdf(
        OUT / 'guide.pdf')
    print(f"wrote {OUT/'guide.pdf'} ({len(PAGES)} pages)")


if __name__ == '__main__':
    build()
