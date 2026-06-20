"""Booklet renderer + build smoke tests. Run: python3 -m tests.test_guides"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'build'))   # so build/*.py import as modules

from minx import puzzle as P
from minx import render as R


def test_center_circle_cosmetic():
    K = P.KILOMINX
    white = max(range(12), key=lambda fi: K.normals[fi][2])
    front = min(K.adj[white], key=lambda fi: K.normals[fi][1])
    cmap = R.color_map(white, front, puzzle=K)
    ksvg = R.render_top(K.minx(), white, front, cmap, size=120, puzzle=K)
    assert '<circle' in ksvg, "kilominx center should render as a circle"

    # megaminx (center_shape == 'pentagon') must NOT gain a circle
    mw = max(range(12), key=lambda fi: P.MEGAMINX.normals[fi][2])
    mf = min(P.MEGAMINX.adj[mw], key=lambda fi: P.MEGAMINX.normals[fi][1])
    mcmap = R.color_map(mw, mf)
    msvg = R.render_top(P.MEGAMINX.minx(), mw, mf, mcmap, size=120)
    assert '<circle' not in msvg, "megaminx render must be unchanged"


def main():
    test_center_circle_cosmetic()
    print("test_guides: OK")


if __name__ == '__main__':
    main()
