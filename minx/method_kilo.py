"""Verified layer-by-layer kilominx solver, executed in the simulator.

The kilominx is corners-only: 20 corners in four rings of five. With white on
top the stages are
  1. white corners      (white + 2 band1 faces)
  2. upper-middle ring  (2 band1 + 1 band2 face)
  3. lower-middle ring  (1 band1 + 2 band2 faces)
  4. last layer (gray):  permute the 5 corners, then orient them   (Task 3)

Insertion is the same 'righty' the megaminx booklet teaches. Every insertion
verifies in-sim that no already-solved corner is net-disturbed, so a passing
fuzz run is a proof the method works on those scrambles. This is an independent
parallel solver: it reuses the shared BaseSolver primitives but does NOT touch
method_mega's corner logic.
"""
import random
from . import puzzle as P
from .solver import BaseSolver, MethodError, RIGHTY, CORNER_CYCLE


def corner_key(faces):
    return tuple(sorted(faces))


class KiloSolver(BaseSolver):

    # -- corner insertion via righty ----------------------------------------

    def righty_corner(self, slot_faces):
        """Insert the corner into slot (u, f, r) where u is the local-top face;
        stage it at the vertex below, then repeat righty until seated."""
        u, f, r = slot_faces
        pz = self.puzzle
        st = pz.stickers
        slot = pz.corner_slots[corner_key(slot_faces)]
        colors = slot_faces
        if f not in pz.adj[u] or r not in pz.adj[u] or r not in pz.adj[f]:
            raise MethodError("slot faces not mutually adjacent")
        names = pz.name_faces(u, f)
        if names['R'] != r:
            names = pz.name_faces(u, r)
            if names['R'] != f:
                raise MethodError("slot not addressable as U-F-R")
            f, r = r, f
        stage_slot = pz.corner_slots[corner_key((f, r, names['DR']))]
        cur = self.find_corner(self.m, colors)
        if tuple(cur) != tuple(slot):
            if not self.ferry(colors, stage_slot):
                self._eject_corner(self.find_corner(self.m, colors))
                if not self.ferry(colors, stage_slot):
                    raise MethodError(f"cannot stage corner {colors}")
        for rep in range(15):
            if all(self.m.state[i] == st[i].face for i in slot):
                self.assert_solved_intact("righty")
                self.mark(slot)
                return rep
            P.apply_alg(self.m, RIGHTY, names)
        raise MethodError("righty never solved the corner")

    def _eject_corner(self, cur_ids):
        """Corner sits in a solved-region slot; pop it out with one righty at
        that slot, verifying solved corners survive."""
        pz = self.puzzle
        faces = [pz.stickers[i].face for i in cur_ids]
        for u in faces:
            others = [x for x in faces if x != u]
            f, r = others
            if f not in pz.adj[u] or r not in pz.adj[u]:
                continue
            for ff, rr in ((f, r), (r, f)):
                try:
                    names = pz.name_faces(u, ff)
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

    # -- stage drivers ------------------------------------------------------

    def white_corners(self):
        for a in self.band1:
            for b in self.band1:
                if b in self.puzzle.adj[a] and a < b:
                    self.righty_corner((self.white, a, b))

    def upper_ring(self):
        """2 band1 + 1 band2 corners."""
        pz = self.puzzle
        for key, slot in pz.corner_slots.items():
            fs = set(key)
            if len(fs & set(self.band1)) == 2 and \
               len(fs & set(self.band2)) == 1:
                (x,) = fs & set(self.band2)
                a, b = sorted(fs & set(self.band1))
                done = False
                for u, f, r in ((a, b, x), (a, x, b), (b, a, x), (b, x, a)):
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
                    raise MethodError(f"upper ring corner {key} failed")

    def lower_ring(self):
        """1 band1 + 2 band2 corners."""
        pz = self.puzzle
        for key, slot in pz.corner_slots.items():
            fs = set(key)
            if len(fs & set(self.band1)) == 1 and \
               len(fs & set(self.band2)) == 2:
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
                    raise MethodError(f"lower ring corner {key} failed")
