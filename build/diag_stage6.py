"""Diagnose Stage 6 of the booklet: simulate what a reader following the
page LITERALLY would encounter, over many scrambles.

Step 1 (low corners): booklet says park the corner below its slot and repeat
the Stage-3 righty "exactly like before" (stage 3 says 2, 4, up to 6 times).
Reader can only park by turning the gray face.

Step 2 (ridge edges): booklet says turn the gray top until the edge lines up
with the front center, then drop right or left.  No other instruction.

We count, per scramble: where the pieces actually are when their turn comes,
how many righty reps each corner needs, and how often the reader hits a case
the page never explains (piece stuck in a slot, flipped in slot, etc.).
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/kurtt/megaminx')
from minx import puzzle as P
from minx import method as M

WHITE_SEEDS = range(int(sys.argv[1]) if len(sys.argv) > 1 else 300)

corner_loc = Counter()      # where the low corner is when its turn comes
corner_reps = Counter()     # righty reps needed once staged
corner_fail = Counter()
edge_loc = Counter()        # where the ridge edge is when its turn comes
edge_simple_ok = 0          # align-and-drop solved it
edge_simple_fail = Counter()
ej_then_ok = 0

def gray_park(s, colors, stage_slot):
    """Try to bring the corner to stage_slot using only gray turns."""
    for t in (0, 1, 2, -1, -2):
        backup = s.m.copy()
        if t:
            s.m.turn(s.gray, t)
        if tuple(M.find_corner(s.m, colors)) == tuple(stage_slot):
            return True
        s.m = backup
    return False


def booklet_corner(s, slot_faces):
    """Stage-6 step 1 as written: grip with the slot at top-front-right,
    park below by turning gray, repeat righty until in."""
    u, f, r = slot_faces
    slot = M.CORNER_SLOTS[M.corner_key(slot_faces)]
    colors = slot_faces
    names = P.name_faces(u, f)
    if names['R'] != r:
        names = P.name_faces(u, r)
        assert names['R'] == f
        f, r = r, f
    assert names['DR'] == s.gray, "staging vertex is NOT next to gray!"
    stage_slot = M.CORNER_SLOTS[M.corner_key((f, r, names['DR']))]

    cur = tuple(M.find_corner(s.m, colors))
    if cur == tuple(slot) and all(s.m.state[i] == P.STICKERS[i].face
                                  for i in slot):
        corner_loc['already solved'] += 1
        s.mark(slot)
        return
    cur_faces = {P.STICKERS[i].face for i in cur}
    if s.gray in cur_faces:
        corner_loc['in gray layer (parkable)'] += 1
    elif cur == tuple(slot):
        corner_loc['in own slot, twisted'] += 1
    else:
        corner_loc['stuck in another low slot'] += 1

    if not gray_park(s, colors, stage_slot):
        # stuck in a low slot: stage-3 note says hold it top-front-right and
        # do the sequence once to pop it out
        s._eject_corner(M.find_corner(s.m, colors))
        if not gray_park(s, colors, stage_slot):
            corner_fail['cannot park even after eject'] += 1
            raise M.MethodError('park failed')
    for rep in range(1, 31):
        P.apply_alg(s.m, M.RIGHTY, names)
        if all(s.m.state[i] == P.STICKERS[i].face for i in slot):
            s.assert_solved_intact('booklet righty')
            s.mark(slot)
            corner_reps[rep] += 1
            return
    corner_fail['righty never inserted (30 reps)'] += 1
    raise M.MethodError('righty failed')


def booklet_ridge_edge(s, key):
    """Stage-6 step 2 as written: gray on top; turn gray until the edge's
    side sticker matches the front center, drop right or left.  Returns a
    category string."""
    global edge_simple_ok
    x, y = key
    slot = M.EDGE_SLOTS[M.edge_key(key)]
    colors = key
    cur = tuple(M.find_edge(s.m, colors))
    if cur == tuple(slot):
        if all(s.m.state[i] == P.STICKERS[i].face for i in slot):
            edge_loc['already solved'] += 1
            s.mark(slot)
            return 'solved'
        edge_loc['FLIPPED in own slot'] += 1
        return 'flipped-in-slot'
    cur_faces = {P.STICKERS[i].face for i in cur}
    if s.gray in cur_faces:
        edge_loc['in gray layer (alignable)'] += 1
    else:
        edge_loc['stuck in another ridge slot'] += 1
        return 'stuck-other-slot'

    # align: turn gray until side sticker color == the face it sits over
    for t in range(5):
        cur = M.find_edge(s.m, colors)
        side_id = next(i for i in cur if P.STICKERS[i].face != s.gray)
        side_color = s.m.state[side_id]
        front = P.STICKERS[side_id].face
        if side_color == front:
            break
        s.m.turn(s.gray, 1)
    else:
        edge_simple_fail['never aligns'] += 1
        return 'align-failed'
    cur = M.find_edge(s.m, colors)
    top_id = next(i for i in cur if P.STICKERS[i].face == s.gray)
    top_color = s.m.state[top_id]
    names = P.name_faces(s.gray, front)
    if names['R'] == top_color:
        P.apply_alg(s.m, M.INSERT_RIGHT, names)
    elif names['L'] == top_color:
        P.apply_alg(s.m, M.INSERT_LEFT, names)
    else:
        edge_simple_fail['top color is not a neighbor'] += 1
        return 'no-neighbor'
    if all(s.m.state[i] == P.STICKERS[i].face for i in slot):
        s.assert_solved_intact('booklet edge')
        s.mark(slot)
        edge_simple_ok += 1
        return 'ok'
    edge_simple_fail['insert did not solve'] += 1
    return 'insert-failed'


def report():
    print(f"runs reaching stage 6: {n_runs}", flush=True)
    print("--- STEP 1 corner locations:", dict(corner_loc), flush=True)
    print("--- STEP 1 righty reps:", dict(corner_reps), flush=True)
    if corner_fail:
        print("--- STEP 1 FAILURES:", dict(corner_fail), flush=True)
    print("--- STEP 2 edge locations:", dict(edge_loc), flush=True)
    print(f"--- STEP 2 simple align-and-drop ok: {edge_simple_ok}",
          flush=True)
    if edge_simple_fail:
        print("--- STEP 2 simple-rule failures:", dict(edge_simple_fail),
              flush=True)
    if hard_failures:
        print("--- hard failures:", hard_failures[:10], flush=True)


n_runs = 0
hard_failures = []
for seed in WHITE_SEEDS:
    if seed and seed % 25 == 0:
        print(f"[seed {seed}]", flush=True)
        report()
    m = P.Minx()
    M.scramble(m, seed=seed)
    s = M.Solver(m, 0)
    try:
        s.white_star(); s.white_corners(); s.row1_edges(); s.row2_band()
    except M.MethodError as e:
        continue
    n_runs += 1

    # --- step 1: low corners, booklet-literal
    low = [k for k in M.CORNER_SLOTS
           if len(set(k) & set(s.band1)) == 1
           and len(set(k) & set(s.band2)) == 2]
    ok = True
    for key in low:
        (a,) = set(key) & set(s.band1)
        x, yv = sorted(set(key) & set(s.band2))
        try:
            booklet_corner(s, (a, x, yv))
        except M.MethodError as e:
            hard_failures.append((seed, 'corner', key, str(e)))
            ok = False
            break
    if not ok:
        continue

    # --- step 2: ridge edges, booklet-literal (with retry loop: a reader
    # who hits a stuck/flipped edge has NO instruction; count those, then
    # use the solver to get unstuck so we can keep measuring later edges)
    ridge = [k for k in M.EDGE_SLOTS if set(k) <= set(s.band2)]
    for key in ridge:
        res = booklet_ridge_edge(s, key)
        if res in ('flipped-in-slot', 'stuck-other-slot', 'align-failed',
                   'no-neighbor', 'insert-failed'):
            # fall back to full solver so the run can continue
            s.insert_edge(key, s.gray)

print("=== FINAL ===", flush=True)
report()
