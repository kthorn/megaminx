"""Piece-level view: group stickers into the 20 corner and 30 edge pieces."""
from . import puzzle as P


def _key(pt):
    return tuple(round(x, 6) for x in pt)


def _build():
    from . import geometry as G
    corners = {}
    edges = {}
    for i, s in enumerate(P.STICKERS):
        face = P.FACES[s.face]
        fverts = face['vertices']
        if s.kind == 'corner':
            corners.setdefault(_key(fverts[s.index]), []).append(i)
        elif s.kind == 'edge':
            a, b = fverts[s.index], fverts[(s.index + 1) % 5]
            mid = tuple((a[k] + b[k]) / 2 for k in range(3))
            edges.setdefault(_key(mid), []).append(i)
    assert len(corners) == 20 and all(len(v) == 3 for v in corners.values())
    assert len(edges) == 30 and all(len(v) == 2 for v in edges.values())
    return corners, edges


CORNERS, EDGES = _build()
ALL_PIECES = list(CORNERS.values()) + list(EDGES.values())


def piece_at(minx, sticker_ids):
    """Colors currently sitting at this piece location."""
    return tuple(minx.state[i] for i in sticker_ids)


def solved_piece(sticker_ids):
    return tuple(P.STICKERS[i].face for i in sticker_ids)


def describe_effect(alg, names, minx=None):
    """Apply alg to a solved minx; report moved and twisted pieces in terms of
    the named faces.  Returns (moved, twisted, summary_string)."""
    inv_names = {v: k for k, v in names.items()}

    def loc_name(sticker_ids):
        faces = sorted(P.STICKERS[i].face for i in sticker_ids)
        return '-'.join(inv_names.get(f, f'#{f}') for f in faces)

    m = minx.copy() if minx else P.Minx()
    before = {tuple(ids): piece_at(m, ids) for ids in ALL_PIECES}
    P.apply_alg(m, alg, names)
    moved, twisted = [], []
    for ids in ALL_PIECES:
        now = piece_at(m, tuple(ids))
        was = before[tuple(ids)]
        if now == was:
            continue
        if sorted(now) == sorted(was):
            twisted.append(loc_name(ids))
        else:
            moved.append(loc_name(ids))
    kind = lambda ids: 'corner' if len(ids) == 3 else 'edge'
    summary = (f"moved: {moved or 'none'}  twisted-in-place: {twisted or 'none'}")
    return moved, twisted, m, summary
