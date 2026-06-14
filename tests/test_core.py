"""Tests for the instance-based shared core. Run: python3 -m tests.test_core"""
from minx import spec
from minx import geometry
from minx import spec as _spec


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


def main():
    test_specs()
    test_build_megaminx()
    test_build_kilominx_not_yet()
    print("test_core: OK")


if __name__ == "__main__":
    main()
