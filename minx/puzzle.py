"""Megaminx state + move engine derived from geometry.

A move is a 72-degree rotation about a face normal applied to every sticker
whose centroid lies in that face's layer; the permutation is found by
nearest-centroid matching, so it is correct by construction.
"""
import math
from . import geometry

NORMALS, FACES, STICKERS = geometry.build()
N_STICKERS = len(STICKERS)
ID_TO_IDX = {s.id: i for i, s in enumerate(STICKERS)}

# ---------------------------------------------------------------------------
# Layer membership: for face f, the layer is the face's own 11 stickers plus
# the 15 strip stickers on the 5 neighbouring faces (2 corners + 1 edge each).
# We find them by the gap in dot(centroid, normal).
# ---------------------------------------------------------------------------


def _layer_indices(fi):
    n = NORMALS[fi]
    scored = sorted(range(N_STICKERS),
                    key=lambda i: -geometry._dot(STICKERS[i].centroid, n))
    chosen = scored[:26]
    # sanity: gap between 26th and 27th must be substantial
    d26 = geometry._dot(STICKERS[chosen[-1]].centroid, n)
    d27 = geometry._dot(STICKERS[scored[26]].centroid, n)
    assert d26 - d27 > 0.05, (fi, d26, d27)
    return chosen


LAYERS = [_layer_indices(fi) for fi in range(12)]

# Permutation tables: PERM[fi][i] = j means a CW (viewed from outside) 72-degree
# turn of face fi sends the colour at sticker i to sticker j.


def _perm_for(fi, angle):
    n = NORMALS[fi]
    perm = list(range(N_STICKERS))
    for i in LAYERS[fi]:
        p = geometry.rotate(STICKERS[i].centroid, n, angle)
        best, bestd = None, 1e9
        for j in LAYERS[fi]:
            q = STICKERS[j].centroid
            d = sum((p[k] - q[k]) ** 2 for k in range(3))
            if d < bestd:
                best, bestd = j, d
        assert bestd < 1e-6, (fi, i, bestd)
        perm[i] = best
    assert sorted(perm) == list(range(N_STICKERS))
    return perm


# Viewed from outside along -normal, a clockwise physical turn corresponds to
# rotation by -72 degrees about the outward normal (right-hand rule).
CW_PERMS = [_perm_for(fi, -2 * math.pi / 5) for fi in range(12)]


class Minx:
    def __init__(self, colors=None):
        # colour of each sticker = its face index when solved
        self.state = list(colors) if colors else [s.face for s in STICKERS]

    def copy(self):
        return Minx(self.state)

    def turn(self, fi, times=1):
        """times>0 = clockwise fifth-turns viewed facing that face."""
        times %= 5
        for _ in range(times):
            new = list(self.state)
            perm = CW_PERMS[fi]
            for i in range(N_STICKERS):
                new[perm[i]] = self.state[i]
            self.state = new
        return self

    def is_solved(self):
        return all(self.state[i] == STICKERS[i].face for i in range(N_STICKERS))

    def sticker(self, face, kind, index):
        return self.state[ID_TO_IDX[(face, kind, index)]]

    def changed_vs(self, other):
        return [i for i in range(N_STICKERS) if self.state[i] != other.state[i]]


# ---------------------------------------------------------------------------
# Human face naming for a given holding orientation.
# We pick a canonical hold: U = face whose normal is closest to +z,
# F = the U-adjacent face whose outward normal is closest to -y (facing viewer).
# The renderer and the algorithm runner share this naming.
# ---------------------------------------------------------------------------


def _adjacent(fi):
    out = []
    for fj in range(12):
        if fj == fi:
            continue
        shared = sum(1 for v in FACES[fi]['vertices'] if any(
            sum((v[k] - w[k]) ** 2 for k in range(3)) < 1e-9
            for w in FACES[fj]['vertices']))
        if shared == 2:
            out.append(fj)
    return out


ADJ = [_adjacent(fi) for fi in range(12)]
OPP = []
for fi in range(12):
    others = [fj for fj in range(12) if geometry._dot(
        NORMALS[fi], NORMALS[fj]) < -0.99]
    OPP.append(others[0])


def name_faces(u, f):
    """Given face indices for U (top) and F (front, adjacent to U), return a
    dict of names.  Around U clockwise (viewed from above/outside U): F, R,
    BR, BL, L.  D2 ('down-right') is the face adjacent to both F-neighbour R
    and F below them; DR names follow standard megaminx conventions loosely
    but the guide only uses U F R L D names plus pictures."""
    assert f in ADJ[u]
    nu = NORMALS[u]
    ring = [fj for fj in ADJ[u]]
    cf = FACES[f]['centroid']
    # order ring clockwise viewed from outside U, starting at F
    import math as _m
    base = geometry._vsub(cf, geometry._vmul(nu, geometry._dot(cf, nu)))
    bu = geometry._norm(base)
    bw = geometry._cross(nu, bu)

    def ang(fj):
        c = FACES[fj]['centroid']
        proj = geometry._vsub(c, geometry._vmul(nu, geometry._dot(c, nu)))
        a = _m.atan2(geometry._dot(proj, bw), geometry._dot(proj, bu))
        return -a % (2 * _m.pi)

    ring.sort(key=ang)
    ring = ring[ring.index(f):] + ring[:ring.index(f)]  # F first (ang(F) may
    # float-round to 2*pi instead of 0, which would sort it last)
    # Orient the ring so ring[1] is on the viewer's right.  Viewer: up = nu,
    # forward = -normal(F); right = forward x up.
    nf = NORMALS[f]
    right = geometry._cross(geometry._vmul(nf, -1), nu)
    if geometry._dot(FACES[ring[1]]['centroid'], right) < \
       geometry._dot(FACES[ring[4]]['centroid'], right):
        ring = [ring[0]] + ring[1:][::-1]
    names = {'U': u, 'F': ring[0], 'R': ring[1], 'BR': ring[2],
             'BL': ring[3], 'L': ring[4], 'D': OPP[u]}
    # D-right: the lower-band face adjacent to both F and R (below the UFR area)
    both = [fj for fj in ADJ[names['F']] if fj in ADJ[names['R']] and fj != u]
    assert len(both) == 1
    names['DR'] = both[0]
    # D-left: lower-band face adjacent to both F and L
    both = [fj for fj in ADJ[names['F']] if fj in ADJ[names['L']] and fj != u]
    assert len(both) == 1
    names['DL'] = both[0]
    return names


def parse_alg(alg):
    """'R U Ri U R U2i Ri' -> list of (name, times). 'i' = inverse,
    digit = repeats (2 = two fifth-turns)."""
    moves = []
    for tok in alg.split():
        name = ''.join(ch for ch in tok if ch.isalpha() and ch != 'i')
        inv = tok.endswith('i')
        digits = ''.join(ch for ch in tok if ch.isdigit())
        times = int(digits) if digits else 1
        moves.append((name, -times if inv else times))
    return moves


def apply_alg(minx, alg, names):
    for name, times in parse_alg(alg):
        minx.turn(names[name], times)
    return minx
