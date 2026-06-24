"""N x N Rubik's cube state + move engine, built from a CubeSpec.

Parallel to ``minx/puzzle.py`` (the dodecahedron engine) but for a cube. A move
is a 90-degree rotation of a layer "slab" about a face axis; the permutation is
found by nearest-centroid matching of the rotated stickers, so it is correct by
construction -- the same technique ``minx/puzzle.py`` uses for 72-degree minx
turns. The engine is parameterised by cube size N, so N=3 builds the 3x3 used
internally by the reduction solver and N=4 builds the 4x4.
"""
import math
from dataclasses import dataclass
from . import cube_geometry as G
from . import cube_pieces


@dataclass(frozen=True)
class CubeSpec:
    name: str
    n: int                       # cube size (3 or 4)
    center_shape: str = 'square'  # for the shared renderer (vs minx 'circle')


CUBE3_SPEC = CubeSpec(name="3x3", n=3)
CUBE4_SPEC = CubeSpec(name="4x4", n=4)

_AXIS_UNIT = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
# Face letter -> (axis, sign). U=+y D=-y R=+x L=-x F=+z B=-z
_FACE_AXIS = {'U': (1, 1), 'D': (1, -1), 'R': (0, 1),
              'L': (0, -1), 'F': (2, 1), 'B': (2, -1)}


class CubeState:
    """A flat list of sticker colours plus a move history (for recording)."""

    def __init__(self, puzzle, colors=None):
        self.puzzle = puzzle
        self.state = list(colors) if colors is not None else \
            [s.face for s in puzzle.stickers]
        self.history = []     # list of move tokens actually applied

    def copy(self):
        c = CubeState(self.puzzle, self.state)
        c.history = list(self.history)
        return c

    def _apply_perm(self, perm):
        new = list(self.state)
        for i in range(len(perm)):
            new[perm[i]] = self.state[i]
        self.state = new

    def move(self, token):
        """Apply one move token (e.g. 'R', "U'", 'R2', 'Rw', "2R'")."""
        ops, norm_token = self.puzzle.resolve(token)
        if not ops:
            return self
        self.history.append(norm_token)
        for axis, layer, q in ops:
            p = self.puzzle.layer_q[(axis, layer)]
            for _ in range(q % 4):
                self._apply_perm(p)
        return self

    def do(self, alg):
        for tok in alg.split():
            self.move(tok)
        return self

    def is_solved(self):
        st = self.puzzle.stickers
        return all(self.state[i] == st[i].face for i in range(len(st)))

    def changed_vs(self, other):
        return [i for i in range(self.puzzle.n_stickers)
                if self.state[i] != other.state[i]]


class CubePuzzle:
    def __init__(self, spec):
        self.spec = spec
        self.n = spec.n
        self.normals, self.faces, self.stickers = G.build(spec)
        self.n_stickers = len(self.stickers)
        self.id_to_idx = {s.id: i for i, s in enumerate(self.stickers)}
        self.opp = self._opposites()
        self.adj = [[fj for fj in range(6) if fj != fi and fj != self.opp[fi]]
                    for fi in range(6)]
        self.layer_q = self._build_layer_perms()
        self.corners, self.edges, self.centers = cube_pieces.build_pieces(
            self.stickers, self.n)

    def state(self, colors=None):
        return CubeState(self, colors)

    # -- geometry helpers ---------------------------------------------------

    def _opposites(self):
        opp = []
        for fi in range(6):
            o = [fj for fj in range(6)
                 if G._dot(self.normals[fi], self.normals[fj]) < -0.99][0]
            opp.append(o)
        return opp

    def _layer_index(self, coord):
        """Which slab (0..n-1, along +axis) a centroid coordinate falls in."""
        k = int((coord + 1) / 2 * self.n - 1e-9)
        return max(0, min(self.n - 1, k))

    def _build_layer_perms(self):
        """For each (axis, layer) precompute the +90deg (CCW about +axis)
        permutation of the whole sticker set, by nearest-centroid matching."""
        perms = {}
        for axis in range(3):
            unit = _AXIS_UNIT[axis]
            members = {k: [] for k in range(self.n)}
            for i, s in enumerate(self.stickers):
                members[self._layer_index(s.centroid[axis])].append(i)
            for k in range(self.n):
                idxs = members[k]
                perm = list(range(self.n_stickers))
                for i in idxs:
                    p = G.rotate(self.stickers[i].centroid, unit, math.pi / 2)
                    best, bestd = None, 1e9
                    for j in idxs:
                        q = self.stickers[j].centroid
                        d = sum((p[t] - q[t]) ** 2 for t in range(3))
                        if d < bestd:
                            best, bestd = j, d
                    assert bestd < 1e-6, (axis, k, i, bestd)
                    perm[i] = best
                assert sorted(perm) == list(range(self.n_stickers))
                perms[(axis, k)] = perm
        return perms

    # -- move notation ------------------------------------------------------

    def resolve(self, token):
        """Token -> (list of (axis, layer_index, quarter_turns), norm_token).

        quarter_turns count CCW rotations about the +axis. CW-from-the-face
        (the standard meaning of e.g. R) is negative about a +sign axis and
        positive about a -sign axis. Supports outer (R, U'...), doubles (R2),
        wide (Rw / lowercase r), and inner-slice (2R = 2nd layer from R).
        """
        import re
        m = re.match(r"^(\d*)([URFDLBurfdlb])(w?)('?)(\d*)$", token)
        if not m:
            raise ValueError(f"bad cube move {token!r}")
        lead, letter, w, prime, cnt = m.groups()
        face = letter.upper()
        wide = (w == 'w') or letter.islower()
        depth = int(lead) if lead else None
        count = int(cnt) if cnt else 1
        turns = -count if prime else count       # CW quarter-turns
        axis, sign = _FACE_AXIS[face]
        cw_to_axis = -1 if sign > 0 else 1        # CW about the face -> +axis q
        q = (turns * cw_to_axis) % 4

        if depth is not None:
            depths = [depth]
        elif wide:
            depths = [1, 2]
        else:
            depths = [1]
        ops = []
        for d in depths:
            layer = self.n - d if sign > 0 else d - 1
            ops.append((axis, layer, q))
        return ops, token

    def name_faces(self, u, f):
        """Given face indices for U (top) and F (front, adjacent), return a
        dict U D L R F B."""
        assert f in self.adj[u]
        nu, nf = self.normals[u], self.normals[f]
        r = G._cross(nu, nf)            # right direction
        names = {'U': u, 'F': f, 'D': self.opp[u], 'B': self.opp[f]}
        names['R'] = self._face_with_normal(r)
        names['L'] = self.opp[names['R']]
        return names

    def _face_with_normal(self, vec):
        best, bestd = None, 1e9
        for fi in range(6):
            d = sum((self.normals[fi][t] - vec[t]) ** 2 for t in range(3))
            if d < bestd:
                best, bestd = fi, d
        return best


# Module-level instances + convenience.
CUBE3 = CubePuzzle(CUBE3_SPEC)
CUBE4 = CubePuzzle(CUBE4_SPEC)


def parse_alg(alg):
    return alg.split()


def apply_alg(state, alg, names=None):
    """Apply an algorithm string. If `names` (a name_faces dict) is given, the
    move letters are taken as grip-relative and remapped to the held faces;
    otherwise they are absolute U/D/L/R/F/B moves."""
    if names is None:
        return state.do(alg)
    inv = names  # names maps letter -> face index; tokens already use letters
    for tok in alg.split():
        state.move(_remap_token(tok, inv, state.puzzle))
    return state


def _remap_token(tok, names, puzzle):
    """Rewrite a grip-relative token so its face letter points at the held
    face. Used when an algorithm is taught from a particular hold."""
    import re
    m = re.match(r"^(\d*)([URFDLBurfdlb])(w?)('?)(\d*)$", tok)
    lead, letter, w, prime, cnt = m.groups()
    face_letter = letter.upper()
    target = names[face_letter]
    # map the absolute face index back to an absolute letter for state.move
    abs_letter = G.FACE_NAMES[target]
    out = lead + (abs_letter.lower() if letter.islower() else abs_letter)
    out += w + prime + cnt
    return out
