"""Megaminx/kilominx state + move engine, built from a PuzzleSpec.

A move is a 72-degree rotation about a face normal applied to every sticker
in that face's layer; the permutation is found by nearest-centroid matching,
so it is correct by construction. All derived data lives on a Puzzle
instance; module-level names at the bottom alias the megaminx instance for
backward compatibility."""
import math
from . import geometry
from . import pieces
from . import spec as _spec


class _Minx:
    # Private class. The public surface is `puzzle.minx()` and the
    # backward-compat module-level `Minx(...)` factory defined at the bottom.
    # The class is NOT named `Minx` because the compat factory takes that name
    # at module scope and would otherwise shadow this class inside the methods
    # below (which look up names against module globals at call time).
    def __init__(self, puzzle, colors=None):
        self.puzzle = puzzle
        self.state = list(colors) if colors is not None else \
            [s.face for s in puzzle.stickers]
        self.history = []   # list of (fi, times) actually-applied turns

    def copy(self):
        c = _Minx(self.puzzle, self.state)
        c.history = list(self.history)   # snapshot, so backup/restore via
        return c                         # `self.m = backup` preserves the record

    def turn(self, fi, times=1):
        """times>0 = clockwise fifth-turns viewed facing that face."""
        times %= 5
        if times:
            self.history.append((fi, times))
        perm = self.puzzle.cw_perms[fi]
        n = self.puzzle.n_stickers
        for _ in range(times):
            new = list(self.state)
            for i in range(n):
                new[perm[i]] = self.state[i]
            self.state = new
        return self

    def is_solved(self):
        st = self.puzzle.stickers
        return all(self.state[i] == st[i].face for i in range(len(st)))

    def sticker(self, face, kind, index):
        return self.state[self.puzzle.id_to_idx[(face, kind, index)]]

    def changed_vs(self, other):
        return [i for i in range(self.puzzle.n_stickers)
                if self.state[i] != other.state[i]]


class Puzzle:
    def __init__(self, spec):
        self.spec = spec
        self.normals, self.faces, self.stickers = geometry.build(spec)
        self.n_stickers = len(self.stickers)
        self.id_to_idx = {s.id: i for i, s in enumerate(self.stickers)}
        self.layers = [self._layer_indices(fi) for fi in range(12)]
        self.cw_perms = [self._perm_for(fi, -2 * math.pi / 5)
                         for fi in range(12)]
        self.adj = [self._adjacent(fi) for fi in range(12)]
        self.opp = self._opposites()
        self.corners, self.edges = pieces.build_pieces(
            self.stickers, self.faces, has_edges=spec.has_edges)
        self.all_pieces = list(self.corners.values()) + \
            list(self.edges.values())
        self.corner_slots = {self._piece_key(ids): tuple(ids)
                             for ids in self.corners.values()}
        self.edge_slots = {self._piece_key(ids): tuple(ids)
                           for ids in self.edges.values()}

    def minx(self, colors=None):
        return _Minx(self, colors)

    def _piece_key(self, ids):
        return tuple(sorted(self.stickers[i].face for i in ids))

    def _layer_indices(self, fi):
        n = self.normals[fi]
        scored = sorted(range(self.n_stickers),
                        key=lambda i: -geometry._dot(self.stickers[i].centroid, n))
        k = self.spec.layer_size
        chosen = scored[:k]
        dk = geometry._dot(self.stickers[chosen[-1]].centroid, n)
        dk1 = geometry._dot(self.stickers[scored[k]].centroid, n)
        assert dk - dk1 > 0.05, (fi, dk, dk1)
        return chosen

    def _perm_for(self, fi, angle):
        n = self.normals[fi]
        perm = list(range(self.n_stickers))
        for i in self.layers[fi]:
            p = geometry.rotate(self.stickers[i].centroid, n, angle)
            best, bestd = None, 1e9
            for j in self.layers[fi]:
                q = self.stickers[j].centroid
                d = sum((p[k] - q[k]) ** 2 for k in range(3))
                if d < bestd:
                    best, bestd = j, d
            assert bestd < 1e-6, (fi, i, bestd)
            perm[i] = best
        assert sorted(perm) == list(range(self.n_stickers))
        return perm

    def _adjacent(self, fi):
        out = []
        for fj in range(12):
            if fj == fi:
                continue
            shared = sum(1 for v in self.faces[fi]['vertices'] if any(
                sum((v[k] - w[k]) ** 2 for k in range(3)) < 1e-9
                for w in self.faces[fj]['vertices']))
            if shared == 2:
                out.append(fj)
        return out

    def _opposites(self):
        opp = []
        for fi in range(12):
            others = [fj for fj in range(12) if geometry._dot(
                self.normals[fi], self.normals[fj]) < -0.99]
            opp.append(others[0])
        return opp

    def name_faces(self, u, f):
        """Given face indices for U (top) and F (front, adjacent to U), return
        a dict of names U F R BR BL L D DR DL."""
        assert f in self.adj[u]
        nu = self.normals[u]
        ring = [fj for fj in self.adj[u]]
        cf = self.faces[f]['centroid']
        base = geometry._vsub(cf, geometry._vmul(nu, geometry._dot(cf, nu)))
        bu = geometry._norm(base)
        bw = geometry._cross(nu, bu)

        def ang(fj):
            c = self.faces[fj]['centroid']
            proj = geometry._vsub(c, geometry._vmul(nu, geometry._dot(c, nu)))
            a = math.atan2(geometry._dot(proj, bw), geometry._dot(proj, bu))
            return -a % (2 * math.pi)

        ring.sort(key=ang)
        ring = ring[ring.index(f):] + ring[:ring.index(f)]
        nf = self.normals[f]
        right = geometry._cross(geometry._vmul(nf, -1), nu)
        if geometry._dot(self.faces[ring[1]]['centroid'], right) < \
           geometry._dot(self.faces[ring[4]]['centroid'], right):
            ring = [ring[0]] + ring[1:][::-1]
        names = {'U': u, 'F': ring[0], 'R': ring[1], 'BR': ring[2],
                 'BL': ring[3], 'L': ring[4], 'D': self.opp[u]}
        both = [fj for fj in self.adj[names['F']]
                if fj in self.adj[names['R']] and fj != u]
        assert len(both) == 1
        names['DR'] = both[0]
        both = [fj for fj in self.adj[names['F']]
                if fj in self.adj[names['L']] and fj != u]
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


# ---------------------------------------------------------------------------
# The shipped megaminx instance, plus backward-compatible module-level aliases
# so existing megaminx-only consumers keep working unchanged.
# ---------------------------------------------------------------------------
MEGAMINX = Puzzle(_spec.MEGAMINX_SPEC)
KILOMINX = Puzzle(_spec.KILOMINX_SPEC)

NORMALS = MEGAMINX.normals
FACES = MEGAMINX.faces
STICKERS = MEGAMINX.stickers
N_STICKERS = MEGAMINX.n_stickers
ID_TO_IDX = MEGAMINX.id_to_idx
LAYERS = MEGAMINX.layers
CW_PERMS = MEGAMINX.cw_perms
ADJ = MEGAMINX.adj
OPP = MEGAMINX.opp
name_faces = MEGAMINX.name_faces


def Minx(colors=None):          # noqa: N802 - compat factory, was a class
    """Backward-compatible factory: a megaminx Minx (an `_Minx` bound to the
    megaminx instance). New code should prefer `puzzle.minx()` on an explicit
    Puzzle instance. This name intentionally shadows nothing problematic: the
    class is `_Minx`, so `Puzzle.minx`/`_Minx.copy` resolve correctly."""
    return MEGAMINX.minx(colors)


# Backward-compat piece groupings ON the pieces module: previously computed in
# pieces.py, now sourced from the megaminx instance so pieces.py needn't import
# puzzle (which would form a puzzle<->pieces import cycle). Consumers that read
# pieces.CORNERS/EDGES/ALL_PIECES (tests/test_puzzle.py, method.py) import
# puzzle first, so these are populated by the time they're read.
pieces.CORNERS = MEGAMINX.corners
pieces.EDGES = MEGAMINX.edges
pieces.ALL_PIECES = MEGAMINX.all_pieces
