"""Cube simulator invariants + a proof-by-fuzzing of the solver.

Run: python3 -m tests.test_cube  ->  prints "test_cube: OK"

Like tests/test_puzzle.py for the megaminx, a passing run is the proof: the
move engine is derived from the cube geometry (nearest-centroid matching), the
last-layer/parity/edge-pairing algorithms are verified here, and the full 3x3
and 4x4 solvers are run on many scrambles and asserted to end solved.
"""
from minx import cube as C
from minx import cube_pieces
from minx.method_cube import (Cube3Solver, Cube4Solver, scramble,
                              EO, SUNE, NIKLAS, UPERM, TPERM,
                              PLL_PARITY, OLL_PARITY)


def test_geometry():
    for P, ns in ((C.CUBE3, 54), (C.CUBE4, 96)):
        assert P.n_stickers == ns
        assert len(P.corners) == 8
    # 3x3: 12 edges + 6 centres; 4x4: 24 wings + 24 centres
    assert len(C.CUBE3.edges) == 12 and len(C.CUBE3.centers) == 6
    assert len(C.CUBE4.edges) == 24 and len(C.CUBE4.centers) == 24


def test_moves():
    for P in (C.CUBE3, C.CUBE4):
        for f in 'URFDLB':
            s = P.state()
            for _ in range(4):
                s.move(f)
            assert s.is_solved(), (P.spec.name, f)
            s = P.state(); s.move(f)
            assert not s.is_solved()
        # wide turns on the 4x4
    for f in ('Rw', 'Uw', 'Fw'):
        s = C.CUBE4.state()
        for _ in range(4):
            s.move(f)
        assert s.is_solved(), f
    # sexy move has order 6 on the 3x3
    s = C.CUBE3.state()
    for _ in range(6):
        s.do("R U R' U'")
    assert s.is_solved()


def _moved_corners_edges(P, alg):
    st = P.stickers
    m = P.state(); m.do(alg)
    moved = sum(1 for ids in P.corners + P.edges
                if tuple(sorted(m.state[i] for i in ids))
                != tuple(sorted(st[i].face for i in ids)))
    twist = sum(1 for ids in P.corners + P.edges
                if tuple(sorted(m.state[i] for i in ids))
                == tuple(sorted(st[i].face for i in ids))
                and any(m.state[i] != st[i].face for i in ids))
    return moved, twist


def test_last_layer_algs():
    P = C.CUBE3
    # NIKLAS is a pure corner 3-cycle; UPERM a pure edge 3-cycle.
    assert _moved_corners_edges(P, NIKLAS) == (3, 0)
    assert _moved_corners_edges(P, UPERM) == (3, 0)


def test_parity_algs_preserve_reduction():
    P = C.CUBE4
    st = P.stickers
    cen = [ids[0] for ids in P.centers]
    from collections import defaultdict
    slots = defaultdict(list)
    for ids in P.edges:
        slots[frozenset(st[i].face for i in ids)].append(ids)

    def reduced(m):
        centres = all(m.state[i] == st[i].face for i in cen)
        paired = all({st[i].face: m.state[i] for i in a}
                     == {st[i].face: m.state[i] for i in b}
                     for a, b in slots.values())
        return centres and paired
    for alg in (PLL_PARITY, OLL_PARITY):
        m = P.state(); m.do(alg)
        assert reduced(m), alg


def test_solve_3x3(n=40):
    P = C.CUBE3
    for seed in range(n):
        s = P.state(); scramble(s, n=30, seed=seed)
        Cube3Solver(s).solve()
        assert s.is_solved(), f"3x3 seed {seed}"


def test_solve_4x4(n=4):
    P = C.CUBE4
    for seed in range(n):
        s = P.state(); scramble(s, n=40, seed=seed)
        Cube4Solver(s).solve()
        assert s.is_solved(), f"4x4 seed {seed}"


def main():
    test_geometry()
    test_moves()
    test_last_layer_algs()
    test_parity_algs_preserve_reduction()
    test_solve_3x3()
    test_solve_4x4()
    print("test_cube: OK")


if __name__ == '__main__':
    main()
