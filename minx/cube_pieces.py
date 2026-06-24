"""Piece-level view of the cube: group stickers into physical cubies.

Like ``minx/pieces.py`` for the dodecahedron, but cubies are found by 3D
position: every sticker's owning cubie centre is its centroid pushed one
half-cubie inward along the face normal. Stickers that share a cubie centre are
the same physical piece. For N=4 this yields 8 corners (3 stickers), 24 edge
wings (2 stickers, two per cube edge) and 24 centres (1 sticker); for N=3, the
usual 8 corners, 12 edges, 6 centres.
"""


def _key(pt):
    return tuple(round(x, 5) for x in pt)


def _cubie_center(centroid, n):
    """Push a surface sticker centroid inward along its face normal by one
    half-cubie, giving the centre of the cubie it belongs to."""
    axis = max(range(3), key=lambda i: abs(centroid[i]))   # the +/-1 coordinate
    sign = 1 if centroid[axis] > 0 else -1
    out = list(centroid)
    out[axis] = centroid[axis] - sign * (1.0 / n)
    return tuple(out)


def build_pieces(stickers, n):
    """Group sticker indices into cubies. Returns (corners, edges, centers),
    each a list of tuples of sticker indices, sorted for determinism."""
    groups = {}
    for i, s in enumerate(stickers):
        groups.setdefault(_key(_cubie_center(s.centroid, n)), []).append(i)
    corners, edges, centers = [], [], []
    for key in sorted(groups):
        ids = tuple(groups[key])
        if len(ids) == 3:
            corners.append(ids)
        elif len(ids) == 2:
            edges.append(ids)
        elif len(ids) == 1:
            centers.append(ids)
        else:
            raise AssertionError(f"cubie with {len(ids)} stickers at {key}")
    assert len(corners) == 8, len(corners)
    return corners, edges, centers


def piece_colors(state, ids):
    return tuple(state[i] for i in ids)


def solved_colors(stickers, ids):
    return tuple(stickers[i].face for i in ids)
