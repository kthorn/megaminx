"""Piece-level view: group corner/edge stickers into physical pieces."""


def _key(pt):
    return tuple(round(x, 6) for x in pt)


def build_pieces(stickers, faces, has_edges=True):
    """Group stickers into corner pieces (3 stickers, shared vertex) and,
    when has_edges, edge pieces (2 stickers, shared edge-midpoint).
    Returns (corners, edges) as dicts: location-key -> list of sticker idx."""
    corners, edges = {}, {}
    for i, s in enumerate(stickers):
        fverts = faces[s.face]['vertices']
        if s.kind == 'corner':
            corners.setdefault(_key(fverts[s.index]), []).append(i)
        elif s.kind == 'edge' and has_edges:
            a, b = fverts[s.index], fverts[(s.index + 1) % 5]
            mid = tuple((a[k] + b[k]) / 2 for k in range(3))
            edges.setdefault(_key(mid), []).append(i)
    assert len(corners) == 20 and all(len(v) == 3 for v in corners.values())
    if has_edges:
        assert len(edges) == 30 and all(len(v) == 2 for v in edges.values())
    else:
        assert len(edges) == 0
    return corners, edges


def piece_at(minx, sticker_ids):
    """Colors currently sitting at this piece location."""
    return tuple(minx.state[i] for i in sticker_ids)


def solved_piece(stickers, sticker_ids):
    return tuple(stickers[i].face for i in sticker_ids)


def describe_effect(puzzle, alg, names, minx=None):
    """Apply alg to a solved puzzle; report moved and twisted pieces in terms
    of the named faces. Returns (moved, twisted, minx, summary_string).
    Uses a local puzzle import so it survives a later task removing the top-level one."""
    from . import puzzle as P
    inv_names = {v: k for k, v in names.items()}
    stickers = puzzle.stickers

    def loc_name(sticker_ids):
        fs = sorted(stickers[i].face for i in sticker_ids)
        return '-'.join(inv_names.get(f, f'#{f}') for f in fs)

    m = minx.copy() if minx else puzzle.minx()
    before = {tuple(ids): piece_at(m, ids) for ids in puzzle.all_pieces}
    P.apply_alg(m, alg, names)
    moved, twisted = [], []
    for ids in puzzle.all_pieces:
        now = piece_at(m, tuple(ids))
        was = before[tuple(ids)]
        if now == was:
            continue
        if sorted(now) == sorted(was):
            twisted.append(loc_name(ids))
        else:
            moved.append(loc_name(ids))
    summary = f"moved: {moved or 'none'}  twisted-in-place: {twisted or 'none'}"
    return moved, twisted, m, summary
