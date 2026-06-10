"""The booklet's solving method, executed in the simulator.

Stages (white on top until the last layer):
  2. White star
  3. White corners            (righty alg below each slot)
  4. Second row of corners    (same righty alg, one row lower)
  5. First band of edges      (the two cube-style edge inserts)
  6. Slanted edges            (same inserts, helper face chosen per slot)
  7. Third row of corners     (righty again, staged toward gray)
  8. Ridge edges              (inserts with gray as the helper layer)
  9. Last layer: star EO -> edge cycle -> corner cycle (CP1) -> righty CO

Every insertion picks a grip (local face naming) and verifies in the sim
that no previously-solved piece is net-disturbed.  solve() raises if any
stage cannot find a safe insertion, so a passing run is a proof that the
method as specified works on that scramble.
"""
import random
from . import puzzle as P
from . import pieces

G = P.geometry

RIGHTY = "Ri DRi R DR"
INSERT_RIGHT = "U R Ui Ri Ui Fi U F"     # U-F edge -> F-R slot
INSERT_LEFT = "Ui Li U L U F Ui Fi"      # U-F edge -> F-L slot
STAR_EO = "F U R Ui Ri Fi"
EDGE_CYCLE = "R U Ri U R U2i Ri"          # cycles U-R -> U-BR -> U-BL -> U-R
CORNER_CYCLE = "Ri BRi R BR Ri Fi R BRi Ri BR F R"   # CP1
FLIP_FIX = "Fi U Li Ui"                   # flips the U-F edge in place


def corner_key(faces):
    return tuple(sorted(faces))


def edge_key(faces):
    return tuple(sorted(faces))


CORNER_SLOTS = {corner_key(P.STICKERS[i].face for i in ids): tuple(ids)
                for ids in pieces.CORNERS.values()}
EDGE_SLOTS = {edge_key(P.STICKERS[i].face for i in ids): tuple(ids)
              for ids in pieces.EDGES.values()}


def find_corner(m, colors):
    """Where the corner piece with these 3 colors currently sits."""
    want = sorted(colors)
    for key, ids in CORNER_SLOTS.items():
        if sorted(m.state[i] for i in ids) == want:
            return ids
    raise AssertionError(colors)


def find_edge(m, colors):
    want = sorted(colors)
    for key, ids in EDGE_SLOTS.items():
        if sorted(m.state[i] for i in ids) == want:
            return ids
    raise AssertionError(colors)


def solved_ids(m, tracked):
    return [ids for ids in tracked
            if all(m.state[i] == P.STICKERS[i].face for i in ids)]


class MethodError(Exception):
    pass


class Solver:
    def __init__(self, m, white):
        self.m = m
        self.white = white
        self.gray = P.OPP[white]
        # bands
        self.band1 = P.ADJ[white]                      # faces around white
        self.band2 = [f for f in range(12)
                      if f not in self.band1 and f not in (white, self.gray)]
        self.solved = []     # list of sticker-id tuples that must stay solved
        self.log = []

    # -- bookkeeping --------------------------------------------------------

    def assert_solved_intact(self, context):
        for ids in self.solved:
            for i in ids:
                if self.m.state[i] != P.STICKERS[i].face:
                    raise MethodError(f"{context}: disturbed {ids}")

    def mark(self, ids):
        assert all(self.m.state[i] == P.STICKERS[i].face for i in ids), ids
        self.solved.append(tuple(ids))

    def free_faces(self):
        """Faces whose layers contain no solved pieces."""
        solved_stickers = set(i for ids in self.solved for i in ids)
        out = []
        for f in range(12):
            if not solved_stickers.intersection(P.LAYERS[f]):
                out.append(f)
        return out

    # -- generic helpers ----------------------------------------------------

    def bfs_to(self, piece_colors, target_ids, ok=None, depth=4,
               faces=None, orient=None, extra=None):
        """BFS over free-face turns to bring piece to target slot.
        orient: optional dict {face: color} the piece must satisfy at target.
        Returns True if achieved (and applies the moves)."""
        faces = faces if faces is not None else self.free_faces()
        from collections import deque
        start = tuple(self.m.state)

        solved_flat = [(i, P.STICKERS[i].face)
                       for ids in self.solved for i in ids]

        def done(state):
            mm = P.Minx(list(state))
            ids = find_corner(mm, piece_colors) if len(piece_colors) == 3 \
                else find_edge(mm, piece_colors)
            if tuple(ids) != tuple(target_ids):
                return False
            if orient:
                for i in ids:
                    f = P.STICKERS[i].face
                    if orient.get(f) is not None and mm.state[i] != orient[f]:
                        return False
            for i, c in solved_flat:
                if state[i] != c:
                    return False
            if extra and not extra(state):
                return False
            return True

        if done(start):
            return True
        seen = {start}
        q = deque([(start, [])])
        while q:
            state, path = q.popleft()
            if len(path) >= depth:
                continue
            for f in faces:
                for t in (1, -1, 2, -2):
                    mm = P.Minx(list(state)).turn(f, t)
                    s2 = tuple(mm.state)
                    if s2 in seen:
                        continue
                    seen.add(s2)
                    p2 = path + [(f, t)]
                    if done(s2):
                        for ff, tt in p2:
                            self.m.turn(ff, tt)
                        return True
                    q.append((s2, p2))
        return False

    def try_insert(self, slot_ids, stage_fn, grips):
        """Try each grip via stage_fn until one solves the slot without
        disturbing solved pieces. stage_fn(grip) must attempt the insert on a
        copy and return the move list or None."""
        for grip in grips:
            backup = self.m.copy()
            try:
                if stage_fn(grip):
                    self.assert_solved_intact("insert")
                    if all(self.m.state[i] == P.STICKERS[i].face
                           for i in slot_ids):
                        return grip
            except MethodError:
                pass
            self.m = backup
        raise MethodError(f"no safe grip for slot {slot_ids}")

    # -- stage 2: white star -------------------------------------------------

    def white_star(self):
        for fa in self.band1:
            slot = EDGE_SLOTS[edge_key((self.white, fa))]
            colors = (self.white, fa)
            # try to bring it straight to the slot, correctly oriented
            ok = self.bfs_to(colors, slot, depth=4,
                             orient={self.white: self.white, fa: fa})
            if not ok:
                # maybe it is in place but flipped, or unreachable without
                # breaking placed edges: stage it below and flip-fix.
                names = P.name_faces(self.white, fa)
                ok = self.bfs_to(colors, slot, depth=4,
                                 orient={self.white: fa, fa: self.white})
                if ok:
                    P.apply_alg(self.m, FLIP_FIX, names)
                    ids = find_edge(self.m, colors)
                    if tuple(ids) != tuple(slot) or \
                       self.m.state[slot[0]] != P.STICKERS[slot[0]].face:
                        # flip fix should have fixed it; if alg flipped it the
                        # other way apply again from scratch
                        raise MethodError("flip fix failed")
            if not ok:
                raise MethodError(f"star edge {colors} unreachable")
            self.assert_solved_intact("star")
            self.mark(slot)
            self.log.append(("star", fa))

    # -- corner insertion via righty -----------------------------------------

    def righty_corner(self, slot_faces):
        """Insert the corner into slot (u, f, r) where u is the local-top
        face of the slot; stages it at the vertex below, then repeats righty."""
        u, f, r = slot_faces
        slot = CORNER_SLOTS[corner_key(slot_faces)]
        colors = slot_faces
        if f not in P.ADJ[u] or r not in P.ADJ[u] or r not in P.ADJ[f]:
            raise MethodError("slot faces not mutually adjacent")
        names = P.name_faces(u, f)
        if names['R'] != r:
            names = P.name_faces(u, r)
            if names['R'] != f:
                raise MethodError("slot not addressable as U-F-R")
            f, r = r, f
        # staging vertex: F, R, DR
        stage_slot = CORNER_SLOTS[corner_key((f, r, names['DR']))]
        cur = find_corner(self.m, colors)
        if tuple(cur) != tuple(slot):
            if not self.bfs_to(colors, stage_slot, depth=4):
                # stuck in a non-free slot: eject it with one righty there,
                # then try staging again
                self._eject_corner(find_corner(self.m, colors))
                if not self.bfs_to(colors, stage_slot, depth=4):
                    raise MethodError(f"cannot stage corner {colors}")
        for rep in range(15):
            if all(self.m.state[i] == P.STICKERS[i].face for i in slot):
                self.assert_solved_intact("righty")
                self.mark(slot)
                return rep
            P.apply_alg(self.m, RIGHTY, names)
        raise MethodError("righty never solved the corner")

    def _eject_corner(self, cur_ids):
        """Corner sits in some solved-region slot; pop it down with one
        righty at that slot, verifying solved pieces survive."""
        faces = [P.STICKERS[i].face for i in cur_ids]
        for u in faces:
            others = [x for x in faces if x != u]
            f, r = others
            if f not in P.ADJ[u] or r not in P.ADJ[u]:
                continue
            for ff, rr in ((f, r), (r, f)):
                try:
                    names = P.name_faces(u, ff)
                except AssertionError:
                    continue
                if names['R'] != rr:
                    continue
                backup = self.m.copy()
                P.apply_alg(self.m, RIGHTY, names)
                try:
                    self.assert_solved_intact("eject")
                    return
                except MethodError:
                    self.m = backup
        raise MethodError("cannot eject corner")

    # -- edge insertion -------------------------------------------------------

    def insert_edge(self, slot_faces, helper):
        """Insert edge (a, b) using helper as the local U face.
        Tries both mirrors x all 5 U-conjugations; verifies safety."""
        a, b = slot_faces
        slot = EDGE_SLOTS[edge_key(slot_faces)]
        colors = slot_faces
        attempts = []
        for mirror in ('R', 'L'):
            for k in range(5):
                attempts.append((mirror, k))

        for round_ in range(5):
            if round_:
                cur = find_edge(self.m, colors)
                if tuple(cur) == tuple(slot):
                    pass  # in-slot case is handled inside _edge_attempt
                elif not self._eject_edge(cur):
                    break
            for mirror, k in attempts:
                backup = self.m.copy()
                try:
                    if self._edge_attempt(slot, colors, helper, mirror, k):
                        self.assert_solved_intact("edge insert")
                        self.mark(slot)
                        return (mirror, k)
                except MethodError:
                    pass
                self.m = backup
        raise MethodError(f"no safe edge insert for {slot_faces}")

    def _eject_edge(self, cur_ids):
        """Edge sits in a slot unreachable by free faces; kick it out with one
        insert alg at that slot, keeping solved pieces intact."""
        fa, fb = (P.STICKERS[i].face for i in cur_ids)
        helpers = [h for h in P.ADJ[fa] if h in P.ADJ[fb]]
        for h in helpers:
            for mirror in ('R', 'L'):
                for ff, ss in ((fa, fb), (fb, fa)):
                    try:
                        names = P.name_faces(h, ff)
                    except AssertionError:
                        continue
                    if names['R' if mirror == 'R' else 'L'] != ss:
                        continue
                    for k in range(5):
                        backup = self.m.copy()
                        if k:
                            self.m.turn(h, k)
                        P.apply_alg(self.m,
                                    INSERT_RIGHT if mirror == 'R'
                                    else INSERT_LEFT, names)
                        if k:
                            self.m.turn(h, -k)
                        try:
                            self.assert_solved_intact("edge eject")
                            return True
                        except MethodError:
                            self.m = backup
        return False

    def _edge_attempt(self, slot, colors, helper, mirror, k):
        a, b = colors
        # local naming: slot must be F-R (mirror 'R') or F-L (mirror 'L')
        if mirror == 'R':
            for ff, rr in ((a, b), (b, a)):
                try:
                    names = P.name_faces(helper, ff)
                except AssertionError:
                    continue
                if names['R'] == rr:
                    break
            else:
                return False
            front, side = ff, rr
        else:
            for ff, ll in ((a, b), (b, a)):
                try:
                    names = P.name_faces(helper, ff)
                except AssertionError:
                    continue
                if names['L'] == ll:
                    break
            else:
                return False
            front, side = ff, ll

        # the piece must reach the local U-F position rotated k steps onward,
        # oriented with `front`'s color facing out on the ring face.
        # staging position after pre-rotation U^k will be U-F; so stage at the
        # position that U^k maps to U-F, i.e. U^-k of U-F.
        ring = [names['F'], names['R'], names['BR'], names['BL'], names['L']]
        # U^1 (CW from above) sends content of ring[i+1] to ring[i]?? -- we
        # verified: after U CW, F's slot receives R's strip, i.e. content moves
        # ring[i] <- ring[i+1].  So U^k maps content at ring[(0 + k) % 5] to
        # ring[0] (=F).  Stage at ring[k].
        stage_face = ring[k % 5]
        stage_slot = EDGE_SLOTS[edge_key((helper, stage_face))]
        cur = find_edge(self.m, colors)
        if tuple(cur) == tuple(slot):
            # already in slot: solved (caller checked not) or flipped; pop it
            # out first with the insert alg using a junk... simplest: run the
            # alg once to eject it into the helper layer, then restage.
            alg = INSERT_RIGHT if mirror == 'R' else INSERT_LEFT
            seq = ('U ' if k else '') * 0  # placeholder, ejection without conj
            P.apply_alg(self.m, alg, names)
        # stage with BFS over free faces plus the helper; done() requires all
        # solved pieces back intact, so helper excursions must self-cancel.
        free = set(self.free_faces())
        free.add(helper)
        if not self.bfs_to(colors, stage_slot, depth=4, faces=sorted(free),
                           orient={stage_face: front, helper: side}):
            return False
        alg = INSERT_RIGHT if mirror == 'R' else INSERT_LEFT
        moves = []
        if k:
            self.m.turn(helper, k)
        P.apply_alg(self.m, alg, names)
        if k:
            self.m.turn(helper, -k)
        return all(self.m.state[i] == P.STICKERS[i].face for i in slot)

    # -- stage drivers --------------------------------------------------------

    def white_corners(self):
        for a in self.band1:
            for b in self.band1:
                if b in P.ADJ[a] and a < b:
                    self.righty_corner((self.white, a, b))
                    self.log.append(("white corner", a, b))

    def row2_corners(self):
        # corners (A, B, X): A,B adjacent band1 faces, X band2 below them
        for key, slot in CORNER_SLOTS.items():
            fs = set(key)
            if len(fs & set(self.band1)) == 2 and len(fs & set(self.band2)) == 1:
                (x,) = fs & set(self.band2)
                a, b = sorted(fs & set(self.band1))
                # local top of slot must be a or b such that the other two are
                # F and R; the slot's "U" is whichever band1 face works with
                # righty staging below toward gray. Try both.
                done = False
                for u, f, r in ((a, b, x), (a, x, b), (b, a, x), (b, x, a)):
                    backup = self.m.copy()
                    try:
                        self.righty_corner((u, f, r))
                        done = True
                        break
                    except MethodError:
                        self.m = backup
                        # remove the mark if partially added
                        self.solved = [s for s in self.solved
                                       if s != tuple(slot)]
                if not done:
                    raise MethodError(f"row2 corner {key} failed")
                self.log.append(("row2 corner", key))

    def row1_edges(self):
        for key, slot in EDGE_SLOTS.items():
            fs = set(key)
            if fs <= set(self.band1):
                a, b = key
                # helper = the band2 face adjacent to both (below the slot)
                helpers = [x for x in self.band2
                           if a in P.ADJ[x] and b in P.ADJ[x]]
                grip = self.insert_edge((a, b), helpers[0])
                self.log.append(("row1 edge", key, grip))

    def _petals(self):
        """For each band2 face X: (grip names, corner key, lone slant key,
        pair-flank slant key).  The righty grip at X's corner slot kicks the
        local R-F edge = the pair flank; the other slant is the lone one."""
        petals = []
        for x in self.band2:
            a_b = [f for f in P.ADJ[x] if f in self.band1]
            assert len(a_b) == 2
            a, b = a_b
            names = None
            for u, f in ((a, b), (b, a)):
                nm = P.name_faces(u, f)
                if nm['R'] == x:
                    names = nm
                    break
            assert names, (x, a, b)
            flank = edge_key((names['F'], x))   # local F-R edge, kicked
            lone = edge_key((names['U'], x))    # local U-R edge, safe
            corner = corner_key((names['U'], names['F'], x))
            petals.append((names, corner, lone, flank))
        return petals

    def row2_band(self):
        """Lone slants first (one per petal, plain inserts), then each corner
        goes in together with its flank edge via repeated righty (a 'pair')."""
        petals = self._petals()
        for names, corner, lone, flank in petals:
            a = next(f for f in lone if f in self.band1)
            x = next(f for f in lone if f in self.band2)
            helpers = [h for h in P.ADJ[a]
                       if h in P.ADJ[x] and h in self.band2]
            grip = self.insert_edge((a, x), helpers[0])
            self.log.append(("lone slant", lone, grip, helpers[0]))
        for names, corner, lone, flank in petals:
            self.pair_righty(names, corner, flank)
            self.log.append(("righty pair", corner, flank))

    def pair_righty(self, names, corner_colors, flank_colors):
        """Insert corner and its flank edge together by repeating righty.
        The corner's phase in the righty cycle is shifted by pre-applying
        righty 0-5 times before staging the edge, so any reachable edge
        staging can be phase-matched."""
        cslot = CORNER_SLOTS[corner_key(corner_colors)]
        eslot = EDGE_SLOTS[edge_key(flank_colors)]
        stage_c = CORNER_SLOTS[corner_key(
            (names['F'], names['R'], names['DR']))]
        probe = P.Minx()
        P.apply_alg(probe, RIGHTY, names)
        feed = []
        for key, ids in EDGE_SLOTS.items():
            if tuple(ids) == tuple(eslot):
                continue
            if any(probe.state[i] != P.STICKERS[i].face for i in ids):
                feed.append(ids)
        assert len(feed) == 2, feed
        feed_faces = sorted({P.STICKERS[i].face for ids in feed for i in ids})
        stage_faces = sorted({P.STICKERS[i].face for i in stage_c})

        def cfaces():
            return sorted(set(self.free_faces()) | set(feed_faces)
                          | set(stage_faces))

        def finish(backup, nsolved):
            for rep in range(7):
                if all(self.m.state[i] == P.STICKERS[i].face
                       for i in cslot) and \
                   all(self.m.state[i] == P.STICKERS[i].face for i in eslot):
                    self.assert_solved_intact("pair")
                    self.mark(cslot)
                    self.mark(eslot)
                    return True
                P.apply_alg(self.m, RIGHTY, names)
            self.m = backup
            self.solved = self.solved[:nsolved]
            return False

        for round_ in range(6):
            # make sure the corner is in the righty cycle (slot or staging)
            cur = find_corner(self.m, corner_colors)
            if tuple(cur) != tuple(cslot) and tuple(cur) != tuple(stage_c):
                if not self.bfs_to(corner_colors, stage_c, depth=4,
                                   faces=cfaces()):
                    self._eject_corner(find_corner(self.m, corner_colors))
                    if not self.bfs_to(corner_colors, stage_c, depth=4,
                                       faces=cfaces()):
                        raise MethodError("pair: cannot stage corner")

            for phase in range(6):
                base = self.m.copy()
                nsolved0 = len(self.solved)
                for _ in range(phase):
                    P.apply_alg(self.m, RIGHTY, names)

                cur = find_corner(self.m, corner_colors)
                cur_pin = tuple(cur)
                cur_ori = {P.STICKERS[i].face: self.m.state[i] for i in cur}

                def corner_pinned(state):
                    mm = P.Minx(list(state))
                    try:
                        ids = find_corner(mm, corner_colors)
                    except AssertionError:
                        return False
                    if tuple(ids) != cur_pin:
                        return False
                    return all(mm.state[i] == cur_ori[P.STICKERS[i].face]
                               for i in ids)

                hit = False
                for fslot in feed:
                    fa, fb = (P.STICKERS[i].face for i in fslot)
                    for ca, cb in ((flank_colors[0], flank_colors[1]),
                                   (flank_colors[1], flank_colors[0])):
                        backup = self.m.copy()
                        nsolved = len(self.solved)
                        if self.bfs_to(flank_colors, fslot, depth=4,
                                       faces=cfaces(),
                                       orient={fa: ca, fb: cb},
                                       extra=corner_pinned):
                            if finish(backup, nsolved):
                                return
                        else:
                            self.m = backup
                        hit = hit or False
                self.m = base
                self.solved = self.solved[:nsolved0]
            # vary the edge's flip by ejecting it, then try again
            cur = find_edge(self.m, flank_colors)
            if tuple(cur) != tuple(eslot):
                if not self._eject_edge(cur):
                    P.apply_alg(self.m, RIGHTY, names)
            else:
                P.apply_alg(self.m, RIGHTY, names)
        raise MethodError(f"pair failed for {corner_colors}+{flank_colors}")

    def row3_corners(self):
        for key, slot in CORNER_SLOTS.items():
            fs = set(key)
            if len(fs & set(self.band1)) == 1 and len(fs & set(self.band2)) == 2:
                (a,) = fs & set(self.band1)
                x, y = sorted(fs & set(self.band2))
                done = False
                for u, f, r in ((a, x, y), (a, y, x)):
                    backup = self.m.copy()
                    try:
                        self.righty_corner((u, f, r))
                        done = True
                        break
                    except MethodError:
                        self.m = backup
                        self.solved = [s for s in self.solved
                                       if s != tuple(slot)]
                if not done:
                    raise MethodError(f"row3 corner {key} failed")
                self.log.append(("row3 corner", key))

    def ridge_edges(self):
        for key, slot in EDGE_SLOTS.items():
            fs = set(key)
            if fs <= set(self.band2):
                x, y = key
                grip = self.insert_edge((x, y), self.gray)
                self.log.append(("ridge edge", key, grip))

    # -- last layer -----------------------------------------------------------

    def ll_names(self):
        """All 5 grips with gray up."""
        return [P.name_faces(self.gray, f) for f in P.ADJ[self.gray]]

    def ll_star(self):
        self._ll_star_bfs()

    def _gedge(self, f):
        """edge index on the gray face bordering face f."""
        ids = EDGE_SLOTS[edge_key((self.gray, f))]
        for i in ids:
            if P.STICKERS[i].face == self.gray:
                return P.STICKERS[i].index
        raise AssertionError

    def _ll_star_bfs(self):
        from collections import deque
        gray = self.gray

        def oriented(state):
            mm = P.Minx(list(state))
            return all(mm.sticker(gray, 'edge', self._gedge(f)) == gray
                       for f in P.ADJ[gray])

        start = tuple(self.m.state)
        if oriented(start):
            return
        seen = {start}
        q = deque([(start, [])])
        grips = self.ll_names()
        while q:
            state, path = q.popleft()
            if len(path) >= 6:
                continue
            for gi, names in enumerate(grips):
                for pre in range(5):
                    mm = P.Minx(list(state))
                    if pre:
                        mm.turn(gray, pre)
                    P.apply_alg(mm, STAR_EO, names)
                    s2 = tuple(mm.state)
                    if s2 in seen:
                        continue
                    seen.add(s2)
                    p2 = path + [(gi, pre)]
                    if oriented(s2):
                        for gg, pp in p2:
                            if pp:
                                self.m.turn(gray, pp)
                            P.apply_alg(self.m, STAR_EO, grips[gg])
                        return
                    q.append((s2, p2))
        raise MethodError("LL star unreachable")

    def ll_edges(self):
        gray = self.gray
        from collections import deque

        def solved_edges(state):
            mm = P.Minx(list(state))
            n = 0
            for f in P.ADJ[gray]:
                ids = EDGE_SLOTS[edge_key((gray, f))]
                if all(mm.state[i] == P.STICKERS[i].face for i in ids):
                    n += 1
            return n

        # spin gray to maximize matches, then apply cycle alg until solved
        def best_spin():
            best, bestn = 0, -1
            for k in range(5):
                mm = self.m.copy().turn(gray, k)
                n = solved_edges(tuple(mm.state))
                if n > bestn:
                    best, bestn = k, n
            self.m.turn(gray, best)
            return bestn

        for _ in range(20):
            n = best_spin()
            if n == 5:
                return
            # apply edge cycle from some grip; choose the grip that increases
            # solved count most after a re-spin
            cands = []
            for names in self.ll_names():
                mm = self.m.copy()
                P.apply_alg(mm, EDGE_CYCLE, names)
                bn = max(solved_edges(tuple(mm.copy().turn(gray, k).state))
                         for k in range(5))
                cands.append((bn, names))
            cands.sort(key=lambda c: -c[0])
            P.apply_alg(self.m, EDGE_CYCLE, cands[0][1])
        raise MethodError("LL edges unsolved")

    def ll_corners_position(self):
        gray = self.gray

        def placed(state=None):
            mm = P.Minx(list(state)) if state else self.m
            n = 0
            for key, ids in CORNER_SLOTS.items():
                if gray in key:
                    if sorted(mm.state[i] for i in ids) == sorted(key):
                        n += 1
            return n

        for _ in range(20):
            if placed() == 5:
                return
            cands = []
            for names in self.ll_names():
                mm = self.m.copy()
                P.apply_alg(mm, CORNER_CYCLE, names)
                cands.append((placed(tuple(mm.state)), names))
            cands.sort(key=lambda c: -c[0])
            P.apply_alg(self.m, CORNER_CYCLE, cands[0][1])
        raise MethodError("LL corner positions unsolved")

    def ll_corners_orient(self):
        gray = self.gray
        # cube-guide style: pick ONE grip; repeat righty until the U-F-R
        # corner is solved; then turn ONLY the gray face to bring the next
        # unsolved corner into U-F-R; at the end the gray face realigns.
        names = self.ll_names()[0]
        slot = CORNER_SLOTS[corner_key((gray, names['F'], names['R']))]
        up_sticker = next(i for i in slot if P.STICKERS[i].face == gray)
        for outer in range(12):
            if self.m.is_solved():
                return
            if self.m.state[up_sticker] != gray:
                # gray sticker not facing up: righty until it is (the lower
                # layers look scrambled meanwhile - that is OK and fixes
                # itself once every corner is done)
                for rep in range(7):
                    if self.m.state[up_sticker] == gray:
                        break
                    P.apply_alg(self.m, RIGHTY, names)
                else:
                    raise MethodError("righty did not orient the corner")
            else:
                self.m.turn(gray, 1)
        if not self.m.is_solved():
            raise MethodError("LL corner orientation failed")

    # -- main -----------------------------------------------------------------

    def solve(self):
        self.white_star()
        self.white_corners()
        self.row1_edges()
        self.row2_band()
        self.row3_corners()
        self.ridge_edges()
        self.ll_star()
        self.assert_solved_intact("LL star")
        self.ll_edges()
        self.assert_solved_intact("LL edges")
        self.ll_corners_position()
        self.assert_solved_intact("LL corner pos")
        self.ll_corners_orient()
        if not self.m.is_solved():
            raise MethodError("end state not solved")


def scramble(m, n=60, seed=None):
    rng = random.Random(seed)
    for _ in range(n):
        m.turn(rng.randrange(12), rng.choice((1, 2, -1, -2)))
    return m
