"""Contrast: how often is a second-row edge (stage 4) already stuck in a
second-row slot when its turn comes, vs the stage-6 ridge edges?"""
import sys
from collections import Counter
sys.path.insert(0, '/home/kurtt/megaminx')
from minx import puzzle as P
from minx import method as M

loc = Counter()
n_runs = 0
for seed in range(150):
    m = P.Minx()
    M.scramble(m, seed=seed)
    s = M.Solver(m, 0)
    try:
        s.white_star(); s.white_corners()
    except M.MethodError:
        continue
    n_runs += 1
    row2 = [k for k in M.EDGE_SLOTS if set(k) <= set(s.band1)]
    for key in row2:
        slot = M.EDGE_SLOTS[M.edge_key(key)]
        cur = tuple(M.find_edge(s.m, key))
        if cur == tuple(slot):
            if all(s.m.state[i] == P.STICKERS[i].face for i in slot):
                loc['already solved'] += 1
            else:
                loc['FLIPPED in own slot'] += 1
        elif tuple(cur) in {tuple(M.EDGE_SLOTS[M.edge_key(k)])
                            for k in row2}:
            loc['stuck in another row2 slot'] += 1
        else:
            loc['free (reachable below)'] += 1
        # use full solver to place it and move on
    try:
        s.row1_edges()
    except M.MethodError:
        pass

print(f"runs: {n_runs}", flush=True)
for k, v in loc.most_common():
    print(f"  {k}: {v}")
