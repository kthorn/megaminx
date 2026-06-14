"""Tests for the instance-based shared core. Run: python3 -m tests.test_core"""
from minx import spec
from minx import geometry
from minx import spec as _spec
from minx import pieces
from minx import puzzle as P
from minx import render as R
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


def test_build_kilominx_not_yet():
    try:
        geometry.build(_spec.KILOMINX_SPEC)
    except NotImplementedError:
        return
    raise AssertionError("kilominx subdivision should be unimplemented in Phase A")


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


def main():
    test_specs()
    test_build_megaminx()
    test_build_kilominx_not_yet()
    test_build_pieces()
    test_puzzle_instance_and_history()
    test_render_smoke()
    print("test_core: OK")


if __name__ == "__main__":
    main()
