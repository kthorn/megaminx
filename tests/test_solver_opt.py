"""Equivalence tests for the solver hot-path optimization.

These prove the fast primitives (`_apply`, `_find_corner_state`,
`_find_edge_state`) produce identical results to the original object-based
path, so the optimized BFS explores the same states in the same order and
therefore yields byte-identical solutions.

Run: python3 -m tests.test_solver_opt
"""
import random as _r
from minx import puzzle as P
from minx import solver as S
from minx import method_mega as M


def _scrambled_state(seed, n=24):
    m = P.MEGAMINX.minx()
    rng = _r.Random(seed)
    for _ in range(n):
        m.turn(rng.randrange(12), rng.choice((1, 2, -1, -2)))
    return tuple(m.state)


def test_apply_matches_turn():
    s = S.BaseSolver(P.MEGAMINX.minx(), 0)
    for seed in range(25):
        state = _scrambled_state(seed)
        for f in range(12):
            for t in (1, -1, 2, -2):
                expected = tuple(P.MEGAMINX.minx(list(state)).turn(f, t).state)
                assert s._apply(state, f, t) == expected, (seed, f, t)


def test_find_state_matches():
    s = S.BaseSolver(P.MEGAMINX.minx(), 0)
    for seed in range(12):
        state = _scrambled_state(seed)
        mm = P.MEGAMINX.minx(list(state))
        for key in P.MEGAMINX.corner_slots:        # key = sorted color tuple
            assert s._find_corner_state(state, key) == s.find_corner(mm, key)
        for key in P.MEGAMINX.edge_slots:
            assert s._find_edge_state(state, key) == s.find_edge(mm, key)


def test_solved_cube_solves_instantly():
    # early-skip: a solved cube needs no search and produces no moves, but
    # solve() still runs all stages end-to-end and ends solved.
    s = M.Solver(P.MEGAMINX.minx(), 0)
    s.solve()
    assert s.m.is_solved()
    assert len(s.solution) == 10        # one Step per stage
    assert sum(len(st.moves) for st in s.solution.steps) == 0


def main():
    test_apply_matches_turn()
    test_find_state_matches()
    test_solved_cube_solves_instantly()
    print("test_solver_opt: OK")


if __name__ == "__main__":
    main()
