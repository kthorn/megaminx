"""Cube simulator invariants + a proof-by-fuzzing of the solver.

Run: python3 -m tests.test_cube  ->  prints "test_cube: OK"

Like tests/test_puzzle.py for the megaminx, a passing run is the proof: the
move engine is derived from the cube geometry (nearest-centroid matching), the
last-layer/parity/edge-pairing algorithms are verified here, and the full 3x3
and 4x4 solvers are run on many scrambles and asserted to end solved.
"""
from minx import cube as C
from minx.method_cube import (Cube3Solver, Cube4Solver, scramble,
                              NIKLAS, UPERM, PLL_PARITY, OLL_PARITY)


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
    test_center_algs()
    test_solve_3x3()
    test_solve_4x4()
    print("test_cube: OK")


if __name__ == '__main__':
    main()
