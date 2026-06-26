"""Cube geometry for the N x N Rubik's cube: faces, sticker grid, slabs.

Parallel to ``minx/geometry.py`` (which builds a dodecahedron) but for a cube.
Everything downstream (the move engine and the SVG renderer) is derived from
this real 3D model, so sticker adjacency and move permutations are never
hand-coded -- exactly the discipline the megaminx engine uses.

The cube is centred at the origin with half-side 1, so every face plane sits at
a coordinate of +/-1. Each face is subdivided into an N x N grid of square
sticker polygons; a sticker carries a 3D ``centroid`` which is the key to the
move engine (nearest-centroid matching) and the renderer (projection).
"""
from .geometry import (_vadd, _vsub, _vmul, _dot, _cross, _norm, rotate,
                        Sticker)

# Faces in a fixed order: U D R L F B. Each entry is (axis, sign) where axis is
# 0/1/2 for x/y/z. Outward normal = sign along that axis.
#   U=+y  D=-y  R=+x  L=-x  F=+z  B=-z
FACE_DEFS = [
    (1, +1),   # 0 U
    (1, -1),   # 1 D
    (0, +1),   # 2 R
    (0, -1),   # 3 L
    (2, +1),   # 4 F
    (2, -1),   # 5 B
]
FACE_NAMES = ['U', 'D', 'R', 'L', 'F', 'B']


def _basis(axis, sign):
    """Return (normal, u, v) for a face: an in-plane right-handed frame with
    u x v == outward normal, so grid orientation is consistent across faces."""
    n = tuple(sign if i == axis else 0 for i in range(3))
    a1, a2 = (axis + 1) % 3, (axis + 2) % 3
    u = tuple(1 if i == a1 else 0 for i in range(3))
    v = tuple(1 if i == a2 else 0 for i in range(3))
    if _dot(_cross(u, v), n) < 0:
        v = _vmul(v, -1)
    return n, u, v


def build(spec):
    """Returns (normals, faces, stickers) for an N x N cube (N = spec.n).

    - normals: 6 outward unit face normals, in FACE_DEFS order.
    - faces: list of {'vertices' (4 corners CCW), 'centroid', 'normal'}.
    - stickers: 6 * N*N Sticker objects. kind is 'corner' (grid corner),
      'edge' (grid border, non-corner) or 'center' (interior), matching how a
      real cubie's stickers are classified.
    """
    n = spec.n
    normals, faces, stickers = [], [], []
    for fi, (axis, sign) in enumerate(FACE_DEFS):
        nrm, u, v = _basis(axis, sign)
        normals.append(nrm)
        c = nrm   # face centre sits on the unit cube face plane
        corners = [_vadd(c, _vadd(_vmul(u, su), _vmul(v, sv)))
                   for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        faces.append({'vertices': corners, 'centroid': c, 'normal': nrm})
        for row in range(n):
            for col in range(n):
                poly = []
                for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    pu = -1 + (2 * col + 1 + du) / n
                    pv = -1 + (2 * row + 1 + dv) / n
                    poly.append(_vadd(c, _vadd(_vmul(u, pu), _vmul(v, pv))))
                on_r = row in (0, n - 1)
                on_c = col in (0, n - 1)
                kind = ('corner' if on_r and on_c else
                        'edge' if on_r or on_c else 'center')
                stickers.append(Sticker(fi, kind, row * n + col, poly))
    return normals, faces, stickers
