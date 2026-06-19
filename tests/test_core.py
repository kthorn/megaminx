"""Tests for the instance-based shared core. Run: python3 -m tests.test_core"""
from minx import spec
from minx import geometry
from minx import spec as _spec
from minx import pieces
from minx import puzzle as P
from minx import render as R
from minx import solver
from minx import method_mega
from tests.test_puzzle import canonical_hold


def test_specs():
    mm = spec.MEGAMINX_SPEC
    assert mm.name == "megaminx"
    assert mm.has_edges is True
    assert mm.has_centers is True
    assert mm.layer_size == 26
    assert mm.subdivision == "edge_parallel"
    assert abs(mm.cut_fraction - 0.42) < 1e-9
    assert mm.center_shape == "pentagon"

    ki = spec.KILOMINX_SPEC
    assert ki.name == "kilominx"
    assert ki.has_edges is False
    assert ki.has_centers is True          # colored centers, like a 3x3
    assert ki.layer_size == 16             # 6 own + 10 strip
    assert ki.subdivision == "kite_circular"
    assert ki.center_shape == "circle"
    assert mm.color_ring == ki.color_ring  # same 5-color ring


def test_build_megaminx():
    normals, faces, stickers = geometry.build(_spec.MEGAMINX_SPEC)
    assert len(normals) == 12 and len(faces) == 12
    assert len(stickers) == 132
    from collections import Counter
    kinds = Counter(s.kind for s in stickers)
    assert kinds == {"center": 12, "edge": 60, "corner": 60}


def test_build_kilominx():
    normals, faces, stickers = geometry.build(_spec.KILOMINX_SPEC)
    assert len(normals) == 12 and len(faces) == 12
    assert len(stickers) == 72
    from collections import Counter
    kinds = Counter(s.kind for s in stickers)
    assert kinds == {"center": 12, "corner": 60}


def test_build_pieces():
    _, faces, stickers = geometry.build(_spec.MEGAMINX_SPEC)
    corners, edges = pieces.build_pieces(stickers, faces, has_edges=True)
    assert len(corners) == 20 and all(len(v) == 3 for v in corners.values())
    assert len(edges) == 30 and all(len(v) == 2 for v in edges.values())


def test_puzzle_instance_and_history():
    pz = P.MEGAMINX
    assert pz.n_stickers == 132
    assert len(pz.layers) == 12 and len(pz.cw_perms) == 12
    assert len(pz.corners) == 20 and len(pz.edges) == 30
    # backward-compat module globals point at the megaminx instance
    assert P.N_STICKERS == 132
    assert P.STICKERS is pz.stickers
    assert P.NORMALS is pz.normals
    # _Minx records turns it actually performs
    m = pz.minx()
    m.turn(0, 2)
    m.turn(3, -1)
    assert m.history == [(0, 2), (3, 4)]   # -1 normalizes to 4 fifth-turns
    # full 5-turn returns to solved and records nothing (times % 5 == 0)
    m2 = pz.minx()
    m2.turn(1, 5)
    assert m2.is_solved() and m2.history == []
    # compat factory
    assert P.Minx().is_solved()


def test_render_smoke():
    names = canonical_hold()
    cmap = R.color_map(names['U'], names['F'])
    svg = R.render(P.MEGAMINX.minx(), names['U'], names['F'], cmap, size=120)
    assert svg.startswith('<svg') and svg.endswith('</svg>')
    assert 'path' in svg


def test_copy_preserves_history():
    pz = P.MEGAMINX
    m = pz.minx()
    m.turn(0, 1)
    backup = m.copy()
    assert backup.history == [(0, 1)]        # copy carries the history snapshot
    m.turn(2, 1)                             # diverge the working cube
    assert backup.history == [(0, 1)]        # snapshot unaffected (independent list)
    m = backup                               # "restore" to the backup
    assert m.history == [(0, 1)] and m.state == backup.state


def test_base_solver_records_steps():
    pz = P.MEGAMINX
    s = solver.BaseSolver(pz.minx(), white=0)
    assert s.gray == pz.opp[0]
    # begin/end a step and confirm the raw turns are captured
    s.begin_step("demo", hold_text="white up")
    s.m.turn(0, 1)
    s.m.turn(3, 2)
    step = s.end_step()
    assert step.stage == "demo"
    assert step.hold_text == "white up"
    assert step.moves == [(0, 1), (3, 2)]
    assert s.solution[-1] is step


def test_solver_records_replayable_steps():
    # The recorded Solution must replay to each step's snapshot, including across
    # the backup/restore (`self.m = self.m.copy()`) pattern the megaminx stages
    # use. We drive a real Solver through two steps manually rather than calling
    # the full solve(), which is correct but BFS-slow on scrambled cubes (the
    # full-solve replay was verified manually; it is too slow for the fast suite).
    pz = P.MEGAMINX
    names = pz.name_faces(0, pz.adj[0][0])
    s = method_mega.Solver(pz.minx(), white=0)

    # step 1: record a real committed sequence
    s.begin_step("s1")
    P.apply_alg(s.m, "R U Ri Ui R U Ri Ui", names)
    s.end_step()

    # step 2: apply a tentative sequence, restore to the backup (history rolls
    # back via the history-preserving copy), then commit a different sequence
    s.begin_step("s2")
    backup = s.m.copy()
    P.apply_alg(s.m, "L Ui Li U", names)     # tentative; will be discarded
    s.m = backup                             # restore: tentative turns dropped
    P.apply_alg(s.m, "BR U BRi Ui", names)   # committed
    s.end_step()

    assert len(s.solution) == 2
    assert len(s.solution.steps[1].moves) == 4   # only the 4 committed turns
    # replay every recorded step from a fresh solved cube; each must reproduce
    # its snapshot, and the final replay equals the solver's working cube
    replay = pz.minx()
    for step in s.solution.steps:
        for fi, t in step.moves:
            replay.turn(fi, t)
        assert replay.state == step.state_after
    assert replay.state == s.m.state


def test_shared_alg_constants():
    from minx import solver, method_mega
    assert solver.RIGHTY == "Ri DRi R DR"
    assert solver.CORNER_CYCLE == "Ri BRi R BR Ri Fi R BRi Ri BR F R"
    # method_mega must reuse the shared objects, not redefine them
    assert method_mega.RIGHTY is solver.RIGHTY
    assert method_mega.CORNER_CYCLE is solver.CORNER_CYCLE


def main():
    test_specs()
    test_build_megaminx()
    test_build_kilominx()
    test_build_pieces()
    test_puzzle_instance_and_history()
    test_render_smoke()
    test_copy_preserves_history()
    test_base_solver_records_steps()
    test_solver_records_replayable_steps()
    test_shared_alg_constants()
    print("test_core: OK")


if __name__ == "__main__":
    main()
