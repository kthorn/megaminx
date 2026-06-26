"""Verified cube solver: a beginner-method 3x3 solve plus a 4x4 reduction that
hands off to it. Every step is executed in the simulator and the result is
asserted solved, so a passing fuzz run is a proof the method works -- the same
discipline the megaminx/kilominx solvers use.

Structure:
  * ``Cube3Solver`` solves a 3x3 (CUBE3). First two layers use verified,
    case-indexed insertion algorithms (a buried piece is first ejected to the
    top by a short bounded search that may not disturb solved pieces -- the
    minx pattern -- then a table lookup inserts it); the last layer is finished
    by a two-look search over verified macro-algorithms (the booklet's algs).
  * ``solve_4x4`` reduces a 4x4 (centres, then edge pairing) until it behaves
    like a 3x3, maps the reduced state onto a CUBE3, solves that, and replays
    the outer-face moves on the 4x4 -- plus the two parity fixes.
"""
from collections import deque
from . import cube as C
from .solver import Solution, Step, MethodError

# Macro algorithms for the last layer (grip-relative: U on top, F in front).
# Each is verified in-sim (see tests/test_cube.py) so the booklet is correct.
EO = "F R U R' U' F'"                       # orient last-layer edges
SUNE = "R U R' U R U2 R'"                   # orient corners (3-cycle of twists)
ANTISUNE = "R U2 R' U' R U' R'"
NIKLAS = "U R U' L' U R' U' L"             # pure corner 3-cycle
UPERM = "R U' R U R U R U' R' U' R2"       # pure edge 3-cycle
TPERM = "R U R' U' R' F R2 U' R' U' R U R' F'"  # swap 2 corners + 2 edges

# First-two-layers insertion tables, discovered + verified in-sim (each entry
# is proven to place the piece while preserving the relevant solved pieces).
# Keys are grip-relative: a sorted tuple of (position-letter, colour-letter)
# for the piece's stickers, with U on top, the target slot at front-right.
# A bottom corner inserts into D-F-R; values are grip-relative algorithms.
CORNER_TABLE = {
    (('B', 'D'), ('L', 'R'), ('U', 'F')): "R U2 R'",
    (('B', 'D'), ('R', 'F'), ('U', 'R')): "F' U F",
    (('B', 'F'), ('L', 'D'), ('U', 'R')): "F' U2 F",
    (('B', 'F'), ('R', 'R'), ('U', 'D')): "F' U2 F R U R'",
    (('B', 'R'), ('L', 'F'), ('U', 'D')): "F' U' F R U R'",
    (('B', 'R'), ('R', 'D'), ('U', 'F')): "U2 R U' R'",
    (('F', 'D'), ('L', 'F'), ('U', 'R')): "U' R U R'",
    (('F', 'D'), ('R', 'R'), ('U', 'F')): "F' U' F",
    (('F', 'F'), ('L', 'R'), ('U', 'D')): "R F R F' U R'",
    (('F', 'F'), ('R', 'D'), ('U', 'R')): "R U R'",
    (('F', 'R'), ('L', 'D'), ('U', 'F')): "R U' R'",
    (('F', 'R'), ('R', 'F'), ('U', 'D')): "R F R2 F' R'",
}
# A bottom cross edge inserts into D-F.
CROSS_TABLE = {
    (('B', 'D'), ('U', 'F')): "U R' F R",
    (('B', 'F'), ('U', 'D')): "U2 F2",
    (('F', 'D'), ('U', 'F')): "U' R' F R",
    (('F', 'F'), ('U', 'D')): "F2",
    (('L', 'D'), ('U', 'F')): "L F' L'",
    (('L', 'F'), ('U', 'D')): "U' F2",
    (('R', 'D'), ('U', 'F')): "R' F R",
    (('R', 'F'), ('U', 'D')): "U F2",
}
# Middle-layer edge inserts (grip-relative, front = the matched centre).
MID_RIGHT = "U R U' R' U' F' U F"
MID_LEFT = "U' L' U L U F U' F'"


def _pulls(puzzle, tokens):
    """Pull-index array per token: applying tok to state == tuple(state[p[j]])."""
    n = puzzle.n_stickers
    out = {}
    for tok in tokens:
        cs = puzzle.state(colors=list(range(n)))
        cs.move(tok)
        out[tok] = tuple(cs.state)
    return out


class Cube3Solver:
    FACES = ['U', 'D', 'R', 'L', 'F', 'B']

    def __init__(self, state):
        self.s = state
        self.P = state.puzzle
        assert self.P.n == 3
        self.st = self.P.stickers
        self.solved = []          # list of sticker-id tuples that must stay home
        self.solution = Solution()
        self._mark = 0
        toks = [f + suf for f in self.FACES for suf in ('', "'", '2')]
        self.move_tokens = toks
        self.pull = _pulls(self.P, toks)

    # -- recording ----------------------------------------------------------
    def begin(self, stage, hold=""):
        self._stage, self._hold, self._mark = stage, hold, len(self.s.history)

    def end(self):
        moves = self.s.history[self._mark:]
        self.solution.append(Step(self._stage, self._hold, list(moves),
                                  list(self.s.state)))

    # -- piece lookup -------------------------------------------------------
    def _slot_home(self, ids):
        return all(self.s.state[i] == self.st[i].face for i in ids)

    def home_colorset(self, ids):
        return tuple(sorted(self.st[i].face for i in ids))

    def _find_colorset(self, state, colors, size):
        """The cubie slot (sticker-id tuple) currently holding exactly these
        colours, among corners (size 3) or edges (size 2)."""
        want = set(colors)
        groups = self.P.corners if size == 3 else self.P.edges
        for ids in groups:
            if set(state[i] for i in ids) == want:
                return ids
        raise MethodError(f"no slot holds colours {colors}")

    def _intact(self, state):
        return all(state[i] == self.st[i].face
                   for grp in self.solved for i in grp)

    def _apply_tuple(self, state, tok):
        p = self.pull[tok]
        return tuple(state[p[j]] for j in range(len(p)))

    def _free_faces(self):
        """Faces whose outer layer holds no already-solved sticker (safe to
        turn freely), as letters. The minx solver uses the same idea."""
        solved_idx = set(i for grp in self.solved for i in grp)
        out = []
        for f in self.FACES:
            axis, sign = C._FACE_AXIS[f]
            lk = self.P.n - 1 if sign > 0 else 0
            ids = [i for i in range(self.P.n_stickers)
                   if self.P._layer_index(self.st[i].centroid[axis]) == lk]
            if not solved_idx.intersection(ids):
                out.append(f)
        return out

    # -- constrained search for one piece -----------------------------------
    def _bfs_path(self, start, faces, goal, max_depth):
        """Shortest move sequence (list of tokens) over `faces` reaching a
        state where goal() holds, or None. BFS with a visited set; never turns
        the same face twice in a row."""
        toks = [f + suf for f in faces for suf in ('', "'", '2')]
        if goal(start):
            return []
        seen = {start}
        q = deque([(start, [], None)])
        while q:
            state, path, lastf = q.popleft()
            if len(path) >= max_depth:
                continue
            for tok in toks:
                if tok[0] == lastf:
                    continue
                ns = self._apply_tuple(state, tok)
                if ns in seen:
                    continue
                seen.add(ns)
                np = path + [tok]
                if goal(ns):
                    return np
                q.append((ns, np, tok[0]))
        return None

    # -- FTL placement: eject to top (search), then a verified insertion -----
    def _eject_to_top(self, colors, k):
        """Bring a buried piece up to the U layer, keeping solved pieces intact
        (a short BFS over the piece's current faces + U)."""
        st = self.st

        def in_top(state):
            cur = self._find_colorset(state, colors, k)
            return any(st[i].face == 0 for i in cur) and self._intact(state)

        start = tuple(self.s.state)
        if in_top(start):
            return
        cur = self._find_colorset(start, colors, k)
        cur_faces = set('UDRLFB'[st[i].face] for i in cur)
        p = self._bfs_path(start, sorted(cur_faces | {'U'}), in_top, 6)
        if p is None:
            raise MethodError(f"eject: colours {colors}")
        for t in p:
            self.s.move(t)

    def _grip_front(self, colors):
        """Choose a front face so the target slot sits at the canonical
        position (corner -> D-F-R, edge -> F-R / D-F)."""
        sides = [c for c in colors if c not in (0, 1)]
        if len(sides) == 1:                 # cross edge {D, side}
            return sides[0]
        a, b = sides                        # corner or middle edge
        return a if self.P.name_faces(0, a)['R'] == b else b

    def _grip_key(self, colors, k, front):
        names = self.P.name_faces(0, front)
        inv = {v: kk for kk, v in names.items()}
        cur = self._find_colorset(tuple(self.s.state), colors, k)
        key = tuple(sorted((inv[self.st[i].face], inv[self.s.state[i]])
                           for i in cur))
        return key, names

    def place_corner(self, slot_ids):
        if self._slot_home(slot_ids):
            return
        colors = [self.st[i].face for i in slot_ids]
        self._eject_to_top(colors, 3)
        key, names = self._grip_key(colors, 3, self._grip_front(colors))
        C.apply_alg(self.s, CORNER_TABLE[key], names)
        if not self._slot_home(slot_ids):
            raise MethodError(f"corner {slot_ids}: key {key}")

    def place_cross_edge(self, slot_ids):
        if self._slot_home(slot_ids):
            return
        colors = [self.st[i].face for i in slot_ids]
        self._eject_to_top(colors, 2)
        key, names = self._grip_key(colors, 2, self._grip_front(colors))
        C.apply_alg(self.s, CROSS_TABLE[key], names)
        if not self._slot_home(slot_ids):
            raise MethodError(f"cross {slot_ids}: key {key}")

    def place_middle_edge(self, slot_ids):
        if self._slot_home(slot_ids):
            return
        st = self.st
        colors = [st[i].face for i in slot_ids]
        # If the edge is stuck in a middle slot (possibly its own, flipped),
        # kick it up to the top with a clean middle-insert (which preserves the
        # other already-paired middle edges); then it inserts from the top.
        cur = self._find_colorset(tuple(self.s.state), colors, 2)
        if not any(st[i].face == 0 for i in cur):
            sf = [st[i].face for i in cur]      # the two side faces it occupies
            front = sf[0] if self.P.name_faces(0, sf[0])['R'] == sf[1] else sf[1]
            C.apply_alg(self.s, MID_RIGHT, self.P.name_faces(0, front))
        # AUF until the top edge's side sticker matches the centre it sits on;
        # then insert toward the face the top colour belongs to.
        for _ in range(5):
            cur = self._find_colorset(tuple(self.s.state), colors, 2)
            top_i = next(i for i in cur if st[i].face == 0)
            side_i = next(i for i in cur if st[i].face != 0)
            S = st[side_i].face
            if self.s.state[side_i] == S:
                break
            self.s.move('U')
        top_color = self.s.state[top_i]
        names = self.P.name_faces(0, S)
        if names['R'] == top_color:
            C.apply_alg(self.s, MID_RIGHT, names)
        elif names['L'] == top_color:
            C.apply_alg(self.s, MID_LEFT, names)
        else:
            raise MethodError(f"middle {slot_ids}: no insert direction")
        if not self._slot_home(slot_ids):
            raise MethodError(f"middle {slot_ids}: not placed")

    # -- last layer: two-look macro search ----------------------------------
    def _bfs_macros(self, macros, goal, max_macros=8):
        start = tuple(self.s.state)
        if goal(start):
            return []
        seen = {start}
        q = deque([(start, [])])
        # Precompute each macro as a pull array (compose its tokens).
        macro_pull = {}
        for name, alg in macros:
            cur = tuple(range(self.P.n_stickers))
            for tok in alg.split():
                cur = self._apply_tuple(cur, tok)
            macro_pull[name] = cur
        while q:
            state, path = q.popleft()
            if len(path) >= max_macros:
                continue
            for name, alg in macros:
                p = macro_pull[name]
                ns = tuple(state[p[j]] for j in range(len(p)))
                if ns in seen:
                    continue
                seen.add(ns)
                np = path + [(name, alg)]
                if goal(ns):
                    for _, a in np:
                        self.s.do(a)
                    return np
                q.append((ns, np))
        raise MethodError("last layer: macro search exhausted")

    def last_layer(self):
        st = self.st
        U = 0
        # Look 1: orient (all U-face stickers show colour U).
        u_face_ids = [i for i in range(self.P.n_stickers) if st[i].face == U]

        def oriented(state):
            return all(state[i] == U for i in u_face_ids)
        orient_macros = [("U", "U"), ("U'", "U'"), ("U2", "U2"),
                         ("EO", EO), ("Sune", SUNE), ("Antisune", ANTISUNE)]
        self.begin("last-layer-orient")
        self._bfs_macros(orient_macros, oriented, max_macros=10)
        self.end()
        # Look 2: permute (fully solved).

        def solved(state):
            return all(state[i] == st[i].face for i in range(len(state)))
        perm_macros = [("U", "U"), ("U'", "U'"), ("U2", "U2"),
                       ("Niklas", NIKLAS), ("Uperm", UPERM), ("Tperm", TPERM)]
        self.begin("last-layer-permute")
        self._bfs_macros(perm_macros, solved, max_macros=10)
        self.end()

    # -- stages -------------------------------------------------------------
    def _slots_with_faces(self, want_faces, kind):
        """Cubie slots (corner or edge) whose home faces are exactly want_faces
        for any one face fixed, used to drive FTL stage ordering."""
        groups = self.P.corners if kind == 'corner' else self.P.edges
        out = []
        for ids in groups:
            faces = set(self.st[i].face for i in ids)
            if want_faces <= faces:
                out.append(ids)
        return out

    def solve(self):
        D, U = 1, 0
        # Stage 1: bottom cross (4 D-edges).
        self.begin("cross")
        for ids in self._slots_with_faces({D}, 'edge'):
            self.place_cross_edge(ids)
            self.solved.append(tuple(ids))
        self.end()
        # Stage 2: bottom corners.
        self.begin("first-layer-corners")
        for ids in self._slots_with_faces({D}, 'corner'):
            self.place_corner(ids)
            self.solved.append(tuple(ids))
        self.end()
        # Stage 3: middle-layer edges (those touching neither U nor D).
        self.begin("middle-layer")
        for ids in self.P.edges:
            faces = set(self.st[i].face for i in ids)
            if U in faces or D in faces:
                continue
            self.place_middle_edge(ids)
            self.solved.append(tuple(ids))
        self.end()
        # Stage 4: last layer.
        self.last_layer()
        assert self.s.is_solved(), "cube not solved after method"
        return self.solution


# 4x4 parity fixes, verified in-sim to preserve solved centres and all edge
# pairings while changing only the last-layer parity (see tests/test_cube.py).
PLL_PARITY = "2R2 U2 2R2 Uw2 2R2 Uw2"          # swap two opposite last-layer edges
OLL_PARITY = "Rw2 B2 U2 Lw U2 Rw' U2 Rw U2 F2 Rw F2 Lw' B2 Rw2"  # flip one edge

# Edge-pairing primitives: each is a wide turn, a 3x3-style edge insert, then
# the wide turn back. Because the inner part uses only outer turns, the whole
# sequence leaves every centre solved while merging wings -- so edge pairing
# never disturbs the centres built in the previous stage. The solver greedily
# applies whichever primitive (after a short outer setup) pairs another edge.
_PAIR_INNER = ["R U R' U'", "R U' R'", "L' U' L U", "L' U L",
               "R U2 R'", "L' U2 L"]
_PAIR_WIDES = ['Dw', 'Uw', 'Rw', 'Lw', 'Fw', 'Bw']
EDGE_PRIMS = [f"{x} {s} {x}'" for x in _PAIR_WIDES for s in _PAIR_INNER] + \
             [f"{x}' {s} {x}" for x in _PAIR_WIDES for s in _PAIR_INNER] + [
    # Bulk "flip" primitives that re-pair several dedges at once -- these reach
    # the last-two-edges case the simple primitives can't.
    "Dw R F' U R' F Dw'", "Dw' R F' U R' F Dw",
    "Uw' R U R' F R' F' R Uw", "Uw R U R' F R' F' R Uw'",
    "Dw L' F U' L F' Dw'", "Dw' L' F U' L F' Dw",
]


class Cube4Solver:
    """Solve a 4x4 by reduction: build the six centres, pair the 24 wings into
    12 edges, fix any 4x4-only parity, then solve the result as a 3x3 with the
    Cube3Solver and replay those outer-face moves on the 4x4. Centres and edge
    pairing are each driven by a greedy progress-search that increases the count
    of solved pieces while keeping finished pieces intact (the same eject/insert
    discipline as the 3x3 and the minx solvers)."""

    CENTER_ORDER = [0, 1, 4, 2, 5, 3]          # U D F R B L
    CENTER_GENS = [g + s for g in ('U', 'D', 'R', 'L', 'F', 'B',
                                   '2U', '2D', '2R', '2L', '2F', '2B')
                   for s in ('', "'", '2')]
    EDGE_GENS = [g + s for g in ('U', 'D', 'R', 'L', 'F', 'B',
                                 'Uw', 'Dw', 'Rw', 'Lw', 'Fw', 'Bw')
                 for s in ('', "'", '2')]

    def __init__(self, state):
        self.m = state
        self.P = state.puzzle
        assert self.P.n == 4
        self.st = self.P.stickers
        self.n = self.P.n_stickers
        self.solution = Solution()
        self._mark = 0
        self.cen_by_face = {f: [ids[0] for ids in self.P.centers
                                if self.st[ids[0]].face == f] for f in range(6)}
        slots = {}
        for ids in self.P.edges:
            slots.setdefault(frozenset(self.st[i].face for i in ids),
                             []).append(ids)
        self.edge_slots = list(slots.values())
        self.cen_pull = _pulls(self.P, self.CENTER_GENS)
        # Edge-pairing macros: outer turns (setup) + centre-preserving pairing
        # primitives. Each macro carries its token list and a composed pull, so
        # the greedy search treats it as one move. All preserve the centres.
        outer = [g + s for g in 'UDRLFB' for s in ('', "'", '2')]
        self.edge_macros = []
        cen_idx = [i for f in range(6) for i in self.cen_by_face[f]]
        for alg in outer + EDGE_PRIMS:
            toks = alg.split()
            cur = tuple(range(self.n))
            for t in toks:
                cur = self._compose(cur, t)
            # Keep only macros that leave every centre's colour in place.
            if all(self.st[cur[i]].face == self.st[i].face for i in cen_idx):
                self.edge_macros.append((toks, cur))

    def _compose(self, pull, tok):
        cs = self.P.state(colors=list(pull))
        cs.move(tok)
        return tuple(cs.state)

    # -- recording ----------------------------------------------------------
    def begin(self, stage, hold=""):
        self._stage, self._hold, self._mark = stage, hold, len(self.m.history)

    def end(self):
        self.solution.append(Step(self._stage, self._hold,
                                  list(self.m.history[self._mark:]),
                                  list(self.m.state)))

    # -- helpers ------------------------------------------------------------
    def _apply(self, state, tok, pull):
        p = pull[tok]
        return tuple(state[p[j]] for j in range(self.n))

    def _correct_centers(self, state, f):
        return sum(1 for i in self.cen_by_face[f] if state[i] == f)

    def _paired(self, state, slot):
        a, b = slot
        return ({self.st[i].face: state[i] for i in a} ==
                {self.st[i].face: state[i] for i in b})

    def _n_paired(self, state):
        return sum(1 for s in self.edge_slots if self._paired(state, s))

    @staticmethod
    def _layer_id(tok):
        """The turning layer a token acts on (e.g. 'U','2U','Uw'), ignoring the
        amount/direction -- used to avoid two consecutive turns of one layer."""
        i = 0
        while i < len(tok) and tok[i].isdigit():
            i += 1
        i += 1                          # the face letter
        if i < len(tok) and tok[i] == 'w':
            i += 1
        return tok[:i]

    def _one_step(self, gens, pull, progress, intact, max_depth):
        """Shortest move sequence (tokens) that strictly increases progress()
        while keeping intact() true, or None. BFS with a visited set; never
        turns the same layer on two consecutive moves."""
        start = tuple(self.m.state)
        base = progress(start)
        seen = {start}
        q = deque([(start, [], None)])
        while q:
            cur, path, lastl = q.popleft()
            if len(path) >= max_depth:
                continue
            for t in gens:
                lid = self._layer_id(t)
                if lid == lastl:
                    continue
                ns = self._apply(cur, t, pull)
                if ns in seen:
                    continue
                seen.add(ns)
                np = path + [t]
                if progress(ns) > base and intact(ns):
                    return np
                q.append((ns, np, lid))
        return None

    def _greedy(self, gens, pull, progress, intact, max_depth, goal):
        """Apply progress-increasing steps until progress reaches `goal`.
        Returns the final progress value. The goal check happens BEFORE each
        search so we never run a futile (and very slow) search for an
        impossible further increase."""
        while progress(tuple(self.m.state)) < goal:
            step = self._one_step(gens, pull, progress, intact, max_depth)
            if step is None:
                break
            for t in step:
                self.m.move(t)
        return progress(tuple(self.m.state))

    # -- stages -------------------------------------------------------------
    def centers(self):
        self.begin("centers")
        done = []
        for f in self.CENTER_ORDER:
            got = self._greedy(
                self.CENTER_GENS, self.cen_pull,
                progress=lambda s, f=f: self._correct_centers(s, f),
                intact=lambda s, d=tuple(done): all(
                    self._correct_centers(s, x) == 4 for x in d),
                max_depth=8, goal=4)
            if self._correct_centers(tuple(self.m.state), f) < 4:
                raise MethodError(f"centers: face {f} stuck at {got}")
            done.append(f)
        self.end()

    def _centers_intact(self, s):
        return all(s[i] == self.st[i].face for f in range(6)
                   for i in self.cen_by_face[f])

    def _macro_step(self, max_depth):
        """Shortest sequence of edge macros (each a token list) that increases
        the paired-edge count, or None. All macros preserve the centres, so the
        only goal is more pairs. BFS over macros with a visited set."""
        start = tuple(self.m.state)
        base = self._n_paired(start)
        seen = {start}
        q = deque([(start, [])])
        while q:
            cur, path = q.popleft()
            if len(path) >= max_depth:
                continue
            for toks, pull in self.edge_macros:
                ns = tuple(cur[pull[j]] for j in range(self.n))
                if ns in seen:
                    continue
                seen.add(ns)
                np = path + [toks]
                if self._n_paired(ns) > base:
                    return np
                q.append((ns, np))
        return None

    def edges(self):
        self.begin("edge-pairing")
        while self._n_paired(tuple(self.m.state)) < 12:
            step = self._macro_step(max_depth=2)
            if step is None:               # last hard edges: search deeper
                step = self._macro_step(max_depth=4)
            if step is None:
                raise MethodError(
                    f"edge-pairing stuck at "
                    f"{self._n_paired(tuple(self.m.state))}")
            for toks in step:
                for t in toks:
                    self.m.move(t)
        self.end()

    # -- reduction to 3x3 ---------------------------------------------------
    def _to_cube3(self):
        def reg(x):
            return [0] if x == 0 else ([3] if x == 2 else [1, 2])
        colors = [0] * C.CUBE3.n_stickers
        for i, s in enumerate(C.CUBE3.stickers):
            r, c = divmod(s.index, 3)
            R, Cc = reg(r)[0], reg(c)[0]
            colors[i] = self.m.state[s.face * 16 + R * 4 + Cc]
        return C.CUBE3.state(colors)

    @staticmethod
    def _perm_sign(c3):
        sign = 1
        st = C.CUBE3.stickers
        for grp in (C.CUBE3.corners, C.CUBE3.edges):
            home = {tuple(sorted(st[i].face for i in ids)): k
                    for k, ids in enumerate(grp)}
            perm = [home[tuple(sorted(c3.state[i] for i in ids))]
                    for ids in grp]
            seen = [False] * len(perm)
            for i in range(len(perm)):
                if seen[i]:
                    continue
                j, ln = i, 0
                while not seen[j]:
                    seen[j] = True
                    j = perm[j]
                    ln += 1
                if ln % 2 == 0:
                    sign = -sign
        return sign

    def finish_3x3(self):
        # Fix PLL parity (odd permutation), then solve as a 3x3; if last-layer
        # orientation is impossible, that is OLL parity -- fix it and resolve.
        if self._perm_sign(self._to_cube3()) == -1:
            self.begin("parity")
            self.m.do(PLL_PARITY)
            self.end()
        for fix in (None, OLL_PARITY):
            if fix is not None:
                self.begin("parity")
                self.m.do(fix)
                self.end()
            c3 = self._to_cube3()
            try:
                sub = Cube3Solver(c3)
                sub.solve()
            except MethodError:
                continue
            # Replay the 3x3 solution stage by stage on the 4x4.
            for step in sub.solution.steps:
                self.begin("3x3:" + step.stage)
                for tok in step.moves:
                    self.m.move(tok)
                self.end()
            return
        raise MethodError("3x3 phase: parity unresolved")

    def solve(self):
        self.centers()
        self.edges()
        self.finish_3x3()
        assert self.m.is_solved(), "4x4 not solved after reduction"
        return self.solution


def scramble(state, n=25, seed=0):
    """Apply n pseudo-random moves (deterministic from seed). On a 4x4 the pool
    includes wide turns so centres and wings get fully mixed."""
    rng = (seed * 1103515245 + 12345) & 0x7fffffff

    def nxt():
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7fffffff
        return rng >> 16
    base = ['U', 'D', 'R', 'L', 'F', 'B']
    moves = list(base)
    if state.puzzle.n >= 4:
        moves += [b + 'w' for b in base]
    sufs = ['', "'", '2']
    last = None
    for _ in range(n):
        mv = moves[nxt() % len(moves)]
        while mv[0] == last:
            mv = moves[nxt() % len(moves)]
        last = mv[0]
        state.move(mv + sufs[nxt() % 3])
    return state
