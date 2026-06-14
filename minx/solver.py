"""Puzzle-agnostic solver scaffolding shared by all puzzle methods.

Holds bookkeeping (which pieces must stay solved), generic search helpers
(BFS / ferry to bring a piece to a slot over free faces), and per-step move
recording producing a structured Solution that a UI/API can replay."""
from collections import deque
from dataclasses import dataclass, field

class MethodError(Exception):
    pass


@dataclass
class Step:
    stage: str
    hold_text: str
    moves: list          # list of (face_index, times)
    state_after: list    # sticker-state snapshot for rendering


@dataclass
class Solution:
    steps: list = field(default_factory=list)

    def append(self, step):
        self.steps.append(step)

    def __getitem__(self, i):
        return self.steps[i]

    def __len__(self):
        return len(self.steps)


class BaseSolver:
    def __init__(self, m, white):
        self.m = m
        self.puzzle = m.puzzle
        self.white = white
        self.gray = self.puzzle.opp[white]
        self.band1 = self.puzzle.adj[white]
        self.band2 = [f for f in range(12)
                      if f not in self.band1 and f not in (white, self.gray)]
        self.solved = []        # list of sticker-id tuples that must stay solved
        self.log = []
        self.solution = Solution()
        self._step_mark = None  # history length at begin_step

    # -- per-step recording -------------------------------------------------

    def begin_step(self, stage, hold_text=""):
        self._step_stage = stage
        self._step_hold = hold_text
        self._step_mark = len(self.m.history)

    def end_step(self):
        moves = self.m.history[self._step_mark:]
        step = Step(self._step_stage, self._step_hold,
                    list(moves), list(self.m.state))
        self.solution.append(step)
        return step

    # -- piece lookup -------------------------------------------------------

    def find_corner(self, m, colors):
        want = sorted(colors)
        for ids in self.puzzle.corner_slots.values():
            if sorted(m.state[i] for i in ids) == want:
                return ids
        raise AssertionError(colors)

    def find_edge(self, m, colors):
        want = sorted(colors)
        for ids in self.puzzle.edge_slots.values():
            if sorted(m.state[i] for i in ids) == want:
                return ids
        raise AssertionError(colors)

    def _find(self, colors):
        return self.find_corner if len(colors) == 3 else self.find_edge

    # -- bookkeeping --------------------------------------------------------

    def assert_solved_intact(self, context):
        st = self.puzzle.stickers
        for ids in self.solved:
            for i in ids:
                if self.m.state[i] != st[i].face:
                    raise MethodError(f"{context}: disturbed {ids}")

    def mark(self, ids):
        st = self.puzzle.stickers
        assert all(self.m.state[i] == st[i].face for i in ids), ids
        self.solved.append(tuple(ids))

    def free_faces(self):
        solved_stickers = set(i for ids in self.solved for i in ids)
        return [f for f in range(12)
                if not solved_stickers.intersection(self.puzzle.layers[f])]

    # -- generic search -----------------------------------------------------

    def bfs_to(self, piece_colors, target_ids, depth=4,
               faces=None, orient=None, extra=None):
        st = self.puzzle.stickers
        faces = faces if faces is not None else self.free_faces()
        find = self._find(piece_colors)
        start = tuple(self.m.state)
        solved_flat = [(i, st[i].face) for ids in self.solved for i in ids]

        def done(state):
            mm = self.puzzle.minx(list(state))
            ids = find(mm, piece_colors)
            if tuple(ids) != tuple(target_ids):
                return False
            if orient:
                for i in ids:
                    f = st[i].face
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
                    mm = self.puzzle.minx(list(state)).turn(f, t)
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

    def ferry(self, piece_colors, target_ids, orient=None, extra=None,
              extra_faces=()):
        st = self.puzzle.stickers
        find = self._find(piece_colors)

        def local_faces():
            cur = find(self.m, piece_colors)
            return {st[i].face for i in cur}

        base_faces = set(self.free_faces()) | set(extra_faces)
        tgt_faces = {st[i].face for i in target_ids}
        if self.bfs_to(piece_colors, target_ids, depth=4,
                       faces=sorted(base_faces | tgt_faces | local_faces()),
                       orient=orient, extra=extra):
            return True
        gray = self.gray
        cur = find(self.m, piece_colors)
        if gray not in {st[i].face for i in cur}:
            def to_gray(state):
                mm = self.puzzle.minx(list(state))
                ids = find(mm, piece_colors)
                return gray in {st[i].face for i in ids}

            solved_flat = [(i, st[i].face) for ids in self.solved for i in ids]
            faces = sorted(base_faces | local_faces())
            start = tuple(self.m.state)
            seen = {start}
            q = deque([(start, [])])
            okpath = None
            while q and okpath is None:
                state, path = q.popleft()
                if len(path) >= 3:
                    continue
                for f in faces:
                    for t in (1, -1, 2, -2):
                        mm = self.puzzle.minx(list(state)).turn(f, t)
                        s2 = tuple(mm.state)
                        if s2 in seen:
                            continue
                        seen.add(s2)
                        p2 = path + [(f, t)]
                        if to_gray(s2) and \
                           all(s2[i] == c for i, c in solved_flat) and \
                           (extra is None or extra(s2)):
                            okpath = p2
                            break
                        q.append((s2, p2))
                    if okpath:
                        break
            if okpath:
                for f, t in okpath:
                    self.m.turn(f, t)
        return self.bfs_to(piece_colors, target_ids, depth=4,
                           faces=sorted(base_faces | tgt_faces
                                        | local_faces() | {gray}),
                           orient=orient, extra=extra)

    def try_insert(self, slot_ids, stage_fn, grips):
        st = self.puzzle.stickers
        for grip in grips:
            backup = self.m.copy()
            try:
                if stage_fn(grip):
                    self.assert_solved_intact("insert")
                    if all(self.m.state[i] == st[i].face for i in slot_ids):
                        return grip
            except MethodError:
                pass
            self.m = backup
        raise MethodError(f"no safe grip for slot {slot_ids}")
