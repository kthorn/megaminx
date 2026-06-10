"""Fast Stage-6 diagnosis.

Instead of solving stages 1-5 (slow, fragile), generate legal stage-6 start
states directly: random-walk from SOLVED using only operations that provably
preserve stages 1-5:
  - gray face turns
  - the booklet righty at each low-corner grip
  - the two insert sequences at each gray-up grip (with gray pre-rotations)
Each generator is verified once to fix all stage-1..5 stickers, so every
walk state is a reachable position with stages 1-5 exactly solved.

Then run the booklet-LITERAL stage 6 on each sample and tally what a reader
following the page would encounter.
"""
import sys, random
from collections import Counter
sys.path.insert(0, '/home/kurtt/megaminx')
from minx import puzzle as P
from minx import method as M
from tests.test_puzzle import canonical_hold

W = canonical_hold()['U']
GRAY = P.OPP[W]
_s = M.Solver(P.Minx(), W)
BAND1, BAND2 = _s.band1, _s.band2

LOW_CORNERS = [k for k in M.CORNER_SLOTS
               if len(set(k) & set(BAND1)) == 1
               and len(set(k) & set(BAND2)) == 2]
RIDGE = [k for k in M.EDGE_SLOTS if set(k) <= set(BAND2)]
LAST_IDS = set()
for k in LOW_CORNERS:
    LAST_IDS |= set(M.CORNER_SLOTS[M.corner_key(k)])
for k in RIDGE:
    LAST_IDS |= set(M.EDGE_SLOTS[M.edge_key(k)])
LAST_IDS |= {i for i in P.LAYERS[GRAY]}
FIXED_IDS = [i for i in range(P.N_STICKERS)
             if i not in LAST_IDS and P.STICKERS[i].kind != 'center']

def low_grip(key):
    (a,) = set(key) & set(BAND1)
    x, y = sorted(set(key) & set(BAND2))
    n = P.name_faces(a, x)
    if n['R'] != y:
        n = P.name_faces(a, y)
        assert n['R'] == x
    assert n['DR'] == GRAY
    return n

GENS = []
for k in LOW_CORNERS:
    GENS.append((M.RIGHTY, low_grip(k)))
for f in P.ADJ[GRAY]:
    n = P.name_faces(GRAY, f)
    GENS.append((M.INSERT_RIGHT, n))
    GENS.append((M.INSERT_LEFT, n))

# verify every generator preserves stages 1-5
for alg, names in GENS:
    m = P.Minx()
    P.apply_alg(m, alg, names)
    assert all(m.state[i] == P.STICKERS[i].face for i in FIXED_IDS), alg

def sample_state(rng, steps=40):
    m = P.Minx()
    for _ in range(steps):
        alg, names = GENS[rng.randrange(len(GENS))]
        P.apply_alg(m, alg, names)
        m.turn(GRAY, rng.choice((1, 2, -1, -2)))
    return m

def fresh_solver(m):
    s = M.Solver(m, W)
    # mark everything except the last-row/gray pieces as solved
    seen = set()
    for slots in (M.CORNER_SLOTS, M.EDGE_SLOTS):
        for key, ids in slots.items():
            t = tuple(ids)
            if t in seen:
                continue
            seen.add(t)
            if all(i not in LAST_IDS for i in ids):
                s.solved.append(t)
    return s

corner_loc = Counter(); corner_reps = Counter(); corner_fail = Counter()
edge_loc = Counter(); edge_simple_fail = Counter()
edge_simple_ok = 0
runs_with_stuck_edge = 0
runs_with_corner_eject = 0
eject_remedy = Counter()


def pop_stuck_edge(s, key):
    """The remedy the page should describe: run the insert sequence once at
    the slot where the edge is stuck, popping it into the gray layer."""
    colors = key
    cur = M.find_edge(s.m, colors)
    fa, fb = (P.STICKERS[i].face for i in cur)
    names = P.name_faces(GRAY, fa)
    if names['R'] == fb:
        P.apply_alg(s.m, M.INSERT_RIGHT, names)
    elif names['L'] == fb:
        P.apply_alg(s.m, M.INSERT_LEFT, names)
    else:
        return False
    s.assert_solved_intact('edge pop')
    cur = M.find_edge(s.m, colors)
    return GRAY in {P.STICKERS[i].face for i in cur}

def gray_park(s, colors, stage_slot):
    for t in (0, 1, 2, -1, -2):
        backup = s.m.copy()
        if t:
            s.m.turn(GRAY, t)
        if tuple(M.find_corner(s.m, colors)) == tuple(stage_slot):
            return True
        s.m = backup
    return False

def booklet_corner(s, key):
    global runs_corner_eject
    names = low_grip(key)
    slot_faces = (names['U'], names['F'], names['R'])
    slot = M.CORNER_SLOTS[M.corner_key(slot_faces)]
    colors = slot_faces
    stage_slot = M.CORNER_SLOTS[M.corner_key(
        (names['F'], names['R'], GRAY))]
    cur = tuple(M.find_corner(s.m, colors))
    if cur == tuple(slot) and all(s.m.state[i] == P.STICKERS[i].face
                                  for i in slot):
        corner_loc['already solved'] += 1
        s.mark(slot)
        return False
    cf = {P.STICKERS[i].face for i in cur}
    needed_eject = False
    if GRAY in cf:
        corner_loc['in gray layer (parkable by gray turns)'] += 1
    elif cur == tuple(slot):
        corner_loc['in own slot but TWISTED'] += 1
        needed_eject = True
    else:
        corner_loc['stuck in another low slot'] += 1
        needed_eject = True
    if not gray_park(s, colors, stage_slot):
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
            return needed_eject
    corner_fail['righty never inserted'] += 1
    raise M.MethodError('righty failed')

def booklet_ridge_edge(s, key):
    global edge_simple_ok
    slot = M.EDGE_SLOTS[M.edge_key(key)]
    colors = key
    cur = tuple(M.find_edge(s.m, colors))
    if cur == tuple(slot):
        if all(s.m.state[i] == P.STICKERS[i].face for i in slot):
            edge_loc['already solved'] += 1
            s.mark(slot)
            return 'solved'
        edge_loc['FLIPPED in own slot'] += 1
        return 'stuck'
    if GRAY not in {P.STICKERS[i].face for i in cur}:
        edge_loc['stuck in another ridge slot'] += 1
        return 'stuck'
    edge_loc['in gray layer (page rule applies)'] += 1
    for t in range(5):
        cur = M.find_edge(s.m, colors)
        side_id = next(i for i in cur if P.STICKERS[i].face != GRAY)
        if s.m.state[side_id] == P.STICKERS[side_id].face:
            break
        s.m.turn(GRAY, 1)
    cur = M.find_edge(s.m, colors)
    side_id = next(i for i in cur if P.STICKERS[i].face != GRAY)
    top_id = next(i for i in cur if P.STICKERS[i].face == GRAY)
    front = P.STICKERS[side_id].face
    top_color = s.m.state[top_id]
    names = P.name_faces(GRAY, front)
    if names['R'] == top_color:
        P.apply_alg(s.m, M.INSERT_RIGHT, names)
    elif names['L'] == top_color:
        P.apply_alg(s.m, M.INSERT_LEFT, names)
    else:
        edge_simple_fail['top color not a neighbor'] += 1
        return 'fail'
    if all(s.m.state[i] == P.STICKERS[i].face for i in slot):
        s.assert_solved_intact('booklet edge')
        s.mark(slot)
        edge_simple_ok += 1
        return 'ok'
    edge_simple_fail['aligned insert did not solve'] += 1
    return 'fail'

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
rng = random.Random(12345)
for trial in range(N):
    m = sample_state(rng)
    s = fresh_solver(m)
    had_eject = False
    for key in LOW_CORNERS:
        try:
            if booklet_corner(s, key):
                had_eject = True
        except M.MethodError as e:
            print('CORNER HARD FAIL', trial, key, e, flush=True)
            break
    else:
        if had_eject:
            runs_with_corner_eject += 1
        stuck_this_run = False
        for key in RIDGE:
            r = booklet_ridge_edge(s, key)
            if r == 'stuck':
                stuck_this_run = True
                if pop_stuck_edge(s, key):
                    r2 = booklet_ridge_edge(s, key)
                    eject_remedy['pop-then-insert worked'
                                 if r2 == 'ok' else
                                 'pop ok but insert failed'] += 1
                else:
                    eject_remedy['pop did not reach gray layer'] += 1
                    s.insert_edge(key, GRAY)
            elif r == 'fail':
                stuck_this_run = True
                s.insert_edge(key, GRAY)
        if stuck_this_run:
            runs_with_stuck_edge += 1

print(f"\nsamples: {N}")
print("\nSTEP 1 - where the low corner is when its turn comes:")
for k, v in corner_loc.most_common():
    print(f"  {k}: {v}")
print("righty reps once parked:", dict(sorted(corner_reps.items())))
if corner_fail:
    print("STEP 1 FAILURES:", dict(corner_fail))
print(f"solves needing at least one corner eject: "
      f"{runs_with_corner_eject}/{N}")
print("\nSTEP 2 - where the ridge edge is when its turn comes:")
for k, v in edge_loc.most_common():
    print(f"  {k}: {v}")
print(f"page rule (align & drop) succeeded: {edge_simple_ok}")
if edge_simple_fail:
    print("page-rule failures:", dict(edge_simple_fail))
if eject_remedy:
    print("stuck-edge remedy (one insert at the stuck slot):",
          dict(eject_remedy))
print(f"solves hitting at least one case the page never explains: "
      f"{runs_with_stuck_edge}/{N}")
