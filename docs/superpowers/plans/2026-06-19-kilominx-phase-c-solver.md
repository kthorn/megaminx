# Kilominx Phase C — Solver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A verified layer-by-layer kilominx solver (`minx/method_kilo.py`, `KiloSolver(BaseSolver)`) that solves any scramble, records a structured `Solution`, and is proven by a fast-suite fuzz over ≥50 seeds.

**Architecture:** A second, parallel solver alongside `method_mega.Solver`, built on the already-shared `BaseSolver` primitives (`bfs_to`, `ferry`, `try_insert`/`find_corner`, `mark`, `assert_solved_intact`, `free_faces`, `begin_step`/`end_step`). Corners-only: four rings of five solved white-up via the booklet's `RIGHTY` insertion, then a gray-up last layer that permutes (`CORNER_CYCLE`) then orients (`RIGHTY`). `method_mega` is touched only to import the two now-shared algorithm constants.

**Tech Stack:** Python 3, no third-party deps. Tests are plain `main()` modules run with `python3 -m tests.<module>`; diagnostic harnesses live in `build/` and take CLI args.

## Global Constraints

- Run everything from the repo root; modules import as `minx.*` and `tests.*` (no installed package).
- `method_kilo.py` must NOT extract or refactor `method_mega`'s corner logic — it is an independent parallel solver. The ONLY change to `method_mega.py` is importing `RIGHTY` and `CORNER_CYCLE` from `solver.py` instead of defining them locally; their string values are unchanged.
- Shared algorithm constants live in `minx/solver.py` as the single source of truth: `RIGHTY = "Ri DRi R DR"` and `CORNER_CYCLE = "Ri BRi R BR Ri Fi R BRi Ri BR F R"`.
- Every corner insertion must verify in-sim that no already-solved corner is net-disturbed (`assert_solved_intact`); a stage raises `solver.MethodError` if no safe insertion exists. A passing fuzz run is therefore a proof the method works on those scrambles.
- Stage names (for the `Solution` record), in order: `white-corners`, `upper-ring`, `lower-ring`, `ll-permute`, `ll-orient`.
- The full regression gate is FOUR suites — all must stay green: `python3 -m tests.test_puzzle`, `python3 -m tests.test_core`, `python3 -m tests.test_kilo`, `python3 -m tests.test_solver_opt`. (CLAUDE.md names only `test_puzzle`; running too few is what left `test_core` red after Phase B.)
- The kilominx solver uses `white=0` as its reference top face (any face works; the solved target is the full identity regardless). `gray` is `puzzle.opp[0]`.
- Use the bare `_Minx`/`Puzzle` API: `puzzle.minx(state=None)`, `m.turn(fi, times)`, `m.copy()`, `m.state`, `m.is_solved()`, `puzzle.corner_slots` (key = sorted color tuple → sticker-id tuple), `puzzle.name_faces(u, f)`, `puzzle.adj`, `puzzle.opp`, `puzzle.stickers`. Move strings run via `puzzle_module.apply_alg(m, alg, names)`.

---

### Task 1: Hoist shared algorithm constants into solver.py

**Files:**
- Modify: `minx/solver.py` (add two module constants near the top)
- Modify: `minx/method_mega.py:24,29` (import the constants instead of defining them)
- Test: `tests/test_core.py` (add `test_shared_alg_constants` + call it in `main()`)

**Interfaces:**
- Produces: `solver.RIGHTY` (str `"Ri DRi R DR"`) and `solver.CORNER_CYCLE` (str `"Ri BRi R BR Ri Fi R BRi Ri BR F R"`), imported by both `method_mega` and (in Task 2/3) `method_kilo`.

- [ ] **Step 1: Write the failing test**

In `tests/test_core.py`, add this function (anywhere among the other `test_*` functions):

```python
def test_shared_alg_constants():
    from minx import solver, method_mega
    assert solver.RIGHTY == "Ri DRi R DR"
    assert solver.CORNER_CYCLE == "Ri BRi R BR Ri Fi R BRi Ri BR F R"
    # method_mega must reuse the shared objects, not redefine them
    assert method_mega.RIGHTY is solver.RIGHTY
    assert method_mega.CORNER_CYCLE is solver.CORNER_CYCLE
```

And add a call to it inside `main()` (alongside the other calls, e.g. right after `test_specs()`):

```python
    test_shared_alg_constants()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_core`
Expected: FAIL — `AttributeError: module 'minx.solver' has no attribute 'RIGHTY'`.

- [ ] **Step 3: Add the constants to solver.py**

In `minx/solver.py`, immediately after the existing imports (the `from collections import deque` / `from dataclasses import ...` block at the top) and before `class MethodError`, insert:

```python
# Shared corner algorithms (grip-relative; correct on any puzzle via
# name_faces). Single source of truth so the megaminx and kilominx booklets
# teach identical moves; method_mega and method_kilo both import these.
RIGHTY = "Ri DRi R DR"
CORNER_CYCLE = "Ri BRi R BR Ri Fi R BRi Ri BR F R"
```

- [ ] **Step 4: Make method_mega import them**

In `minx/method_mega.py`, change the solver import (currently `from .solver import BaseSolver, MethodError`) to:

```python
from .solver import BaseSolver, MethodError, RIGHTY, CORNER_CYCLE
```

Then DELETE the two local definitions so there is a single source of truth:
- the line `RIGHTY = "Ri DRi R DR"`
- the line `CORNER_CYCLE = "Ri BRi R BR Ri Fi R BRi Ri BR F R"   # CP1`

Leave the other algorithm constants (`INSERT_RIGHT`, `INSERT_LEFT`, `STAR_EO`, `EDGE_CYCLE`, `FLIP_FIX`) exactly as they are — they are megaminx-only and stay local.

- [ ] **Step 5: Run the full regression gate**

Run: `python3 -m tests.test_core && python3 -m tests.test_puzzle && python3 -m tests.test_kilo && python3 -m tests.test_solver_opt`
Expected: each prints its OK line (`test_core: OK`, `all simulator invariants: OK`, `all kilominx invariants: OK`, `test_solver_opt: OK`). The constant values are unchanged, so megaminx behavior is identical.

- [ ] **Step 6: Commit**

```bash
git add minx/solver.py minx/method_mega.py tests/test_core.py
git commit -m "refactor: hoist RIGHTY/CORNER_CYCLE to solver.py (shared by both solvers)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: KiloSolver insertion + stages 1–3 (white / upper / lower rings)

**Files:**
- Create: `minx/method_kilo.py`
- Test: `tests/test_kilo.py` (add `_solver_stages_123` check + call in `main()`)

**Interfaces:**
- Consumes: `solver.BaseSolver`, `solver.MethodError`, `solver.RIGHTY` (Task 1); `BaseSolver` methods `find_corner(m, colors)`, `ferry(colors, target_ids)`, `mark(ids)`, `assert_solved_intact(ctx)`, `self.white`, `self.gray`, `self.band1`, `self.band2`, `self.m`, `self.puzzle`; `puzzle.apply_alg(m, alg, names)`.
- Produces: `method_kilo.corner_key(faces) -> tuple`; `method_kilo.KiloSolver(BaseSolver)` with `righty_corner(slot_faces)`, `_eject_corner(cur_ids)`, `white_corners()`, `upper_ring()`, `lower_ring()`. (Last layer + `solve()` + `scramble` are added in Task 3.)

- [ ] **Step 1: Write the failing test**

In `tests/test_kilo.py`, add at the top (with the other imports):

```python
from minx.method_kilo import KiloSolver
from minx.method_kilo import scramble as _kilo_scramble  # provided in Task 3
```

Wait — `scramble` does not exist until Task 3. For THIS task, scramble locally instead. Add this import only:

```python
from minx.method_kilo import KiloSolver, corner_key
```

and add this function, plus a call to it in `main()` (after the existing invariant blocks, before `print(...)`):

```python
def _solver_stages_123():
    import random
    K = P.KILOMINX
    gray = K.opp[0]
    for seed in range(15):
        m = K.minx()
        rng = random.Random(seed)
        for _ in range(40):
            m.turn(rng.randrange(12), rng.choice((1, 2, -1, -2)))
        s = KiloSolver(m, white=0)
        s.white_corners()
        s.upper_ring()
        s.lower_ring()
        # every corner not on the gray (last) layer must now be home
        for key, ids in K.corner_slots.items():
            if gray in key:
                continue
            assert all(s.m.state[i] == K.stickers[i].face for i in ids), \
                (seed, key)
```

Call site inside `main()`:

```python
    _solver_stages_123()
```

(Leave the existing `print("all kilominx invariants: OK")` as the last line.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_kilo`
Expected: FAIL — `ModuleNotFoundError: No module named 'minx.method_kilo'`.

- [ ] **Step 3: Create method_kilo.py with insertion + stages 1–3**

Create `minx/method_kilo.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m tests.test_kilo`
Expected: PASS — prints `all kilominx invariants: OK`. (The 15 non-gray corners are placed on all 15 seeds. If a `MethodError` escapes, the insertion/staging logic is wrong — do not silence it; report BLOCKED with the failing seed/key.)

- [ ] **Step 5: Commit**

```bash
git add minx/method_kilo.py tests/test_kilo.py
git commit -m "feat: KiloSolver righty insertion + stages 1-3 (15 corners placed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Last layer, solve(), scramble, and the fuzz proof

**Files:**
- Modify: `minx/method_kilo.py` (add `ll_names`, `ll_permute`, `ll_orient`, `solve`, module-level `scramble`)
- Test: `tests/test_kilo.py` (replace the `_solver_stages_123` call with a full-solve fuzz + a replay check)

**Interfaces:**
- Consumes: everything from Task 2 plus `solver.CORNER_CYCLE`; `self.ll_names()`; `begin_step(stage)`/`end_step()` and `self.solution` from `BaseSolver`; `m.is_solved()`.
- Produces: `KiloSolver.solve()` (runs the 5 stages, records a `Solution`, raises `MethodError` if the end state is unsolved); `method_kilo.scramble(m, n=40, seed=None) -> m`.

- [ ] **Step 1: Write the failing test**

In `tests/test_kilo.py`, update the import line from Task 2 to also import `scramble`:

```python
from minx.method_kilo import KiloSolver, corner_key, scramble
```

KEEP the `_solver_stages_123` function from Task 2 (it is a finer-grained guard). ADD these two new functions below it:

```python
def _solver_full_solve():
    K = P.KILOMINX
    # solve N scrambles end to end; each must finish solved and never raise
    for seed in range(50):
        m = K.minx()
        scramble(m, n=40, seed=seed)
        s = KiloSolver(m, white=0)
        s.solve()
        assert s.m.is_solved(), seed


def _solver_solution_replays():
    K = P.KILOMINX
    m = K.minx()
    scramble(m, n=40, seed=0)
    start = list(m.state)                 # snapshot the scrambled state
    s = KiloSolver(m, white=0)
    s.solve()
    assert len(s.solution) == 5           # five recorded stages
    replay = K.minx(start)                # replay from the same scramble
    for step in s.solution.steps:
        for fi, t in step.moves:
            replay.turn(fi, t)
        assert replay.state == step.state_after, step.stage
    assert replay.is_solved()
```

Update `main()` so the single `_solver_stages_123()` call becomes three calls (keep the existing one, add the two new ones immediately after it):

```python
    _solver_stages_123()
    _solver_full_solve()
    _solver_solution_replays()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_kilo`
Expected: FAIL — `AttributeError: ... has no attribute 'scramble'` (or, once import is fixed, `KiloSolver` has no attribute `solve`). The last layer and `solve()` do not exist yet.

- [ ] **Step 3: Add the last layer, solve(), and scramble**

Append these methods to `class KiloSolver` in `minx/method_kilo.py` (after `lower_ring`):

```python
    # -- last layer (gray up): permute then orient --------------------------

    def ll_names(self):
        """All 5 grips with gray up (one per gray-adjacent front face)."""
        return [self.puzzle.name_faces(self.gray, f)
                for f in self.puzzle.adj[self.gray]]

    def ll_permute(self):
        """Greedily cycle the 5 gray corners into their slots (orientation
        ignored) with CORNER_CYCLE."""
        pz = self.puzzle
        gray = self.gray

        def placed(state):
            n = 0
            for key, ids in pz.corner_slots.items():
                if gray in key and sorted(state[i] for i in ids) == sorted(key):
                    n += 1
            return n

        for _ in range(20):
            if placed(self.m.state) == 5:
                return
            cands = []
            for names in self.ll_names():
                mm = self.m.copy()
                P.apply_alg(mm, CORNER_CYCLE, names)
                cands.append((placed(mm.state), names))
            cands.sort(key=lambda c: -c[0])
            P.apply_alg(self.m, CORNER_CYCLE, cands[0][1])
        raise MethodError("LL corner positions unsolved")

    def ll_orient(self):
        """Orient the 5 gray corners in place: hold one corner in the front-
        right slot, repeat righty until its gray sticker faces up, then turn
        ONLY the gray face to the next corner. A final gray turn realigns."""
        pz = self.puzzle
        gray = self.gray
        names = self.ll_names()[0]
        slot = pz.corner_slots[corner_key((gray, names['F'], names['R']))]
        up_sticker = next(i for i in slot if pz.stickers[i].face == gray)
        for outer in range(12):
            if self.m.is_solved():
                return
            if self.m.state[up_sticker] != gray:
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

    # -- main ---------------------------------------------------------------

    def solve(self):
        for stage, fn in [
            ("white-corners", self.white_corners),
            ("upper-ring", self.upper_ring),
            ("lower-ring", self.lower_ring),
            ("ll-permute", self.ll_permute),
            ("ll-orient", self.ll_orient),
        ]:
            self.begin_step(stage)
            fn()
            self.end_step()
            self.assert_solved_intact(stage)
        if not self.m.is_solved():
            raise MethodError("end state not solved")
```

And add this module-level function at the end of `minx/method_kilo.py` (outside the class, mirroring `method_mega.scramble`):

```python
def scramble(m, n=40, seed=None):
    rng = random.Random(seed)
    for _ in range(n):
        m.turn(rng.randrange(12), rng.choice((1, 2, -1, -2)))
    return m
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m tests.test_kilo`
Expected: PASS — prints `all kilominx invariants: OK` (50 full solves + the replay check). If any seed raises `MethodError` or finishes unsolved, the method has a gap on that scramble — report the seed; do not weaken the assertion or shrink the loop to make it pass.

- [ ] **Step 5: Confirm suite speed and the full regression gate**

Run: `time python3 -m tests.test_kilo`
Expected: PASS, and the wall-clock should be modest (the kilominx is small; corner-only solving is fast). If it exceeds ~15s, note it in your report (the controller may tune the seed count), but do NOT reduce coverage on your own.

Then run all four suites:
Run: `python3 -m tests.test_puzzle && python3 -m tests.test_core && python3 -m tests.test_kilo && python3 -m tests.test_solver_opt`
Expected: all four print their OK lines.

- [ ] **Step 6: Commit**

```bash
git add minx/method_kilo.py tests/test_kilo.py
git commit -m "feat: KiloSolver last layer + solve(); fuzz proof over 50 seeds

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Manual sweep harness `build/diag_kilo.py`

**Files:**
- Create: `build/diag_kilo.py`

**Interfaces:**
- Consumes: `puzzle.KILOMINX`, `method_kilo.KiloSolver`, `method_kilo.scramble`, `solver.MethodError`.
- Produces: a CLI harness `python3 build/diag_kilo.py [N] [start_seed]` that solves N seeds and prints `<solved>/<N> solved`, exiting non-zero on any failure.

- [ ] **Step 1: Create the harness**

Create `build/diag_kilo.py`:

```python
"""Manual kilominx solver sweep (heavier than the fast-suite fuzz).

Run: python3 build/diag_kilo.py [N] [start_seed]
Prints "<solved>/<N> solved" and exits non-zero if any seed fails.
"""
import sys
from minx import puzzle as P
from minx.method_kilo import KiloSolver, scramble
from minx.solver import MethodError


def main(n=200, start=0):
    fails = 0
    for seed in range(start, start + n):
        m = P.KILOMINX.minx()
        scramble(m, n=40, seed=seed)
        try:
            s = KiloSolver(m, white=0)
            s.solve()
            if not s.m.is_solved():
                print(f"seed {seed}: finished unsolved")
                fails += 1
        except MethodError as e:
            print(f"seed {seed}: {e}")
            fails += 1
    print(f"{n - fails}/{n} solved")
    return fails


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    sys.exit(1 if main(n, start) else 0)
```

- [ ] **Step 2: Run a heavier sweep to verify the method**

Run: `python3 build/diag_kilo.py 200`
Expected: prints `200/200 solved` and exits 0. (This is the heavier proof beyond the 50-seed fast-suite fuzz. If any seed fails, the printed `seed N: <reason>` lines name reproducible failures — report them; do not edit the harness to hide them.)

- [ ] **Step 3: Commit**

```bash
git add build/diag_kilo.py
git commit -m "feat: build/diag_kilo.py manual solver sweep harness

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage** (against `2026-06-19-kilominx-phase-c-solver-design.md`):
- Two parallel solvers, no method_mega refactor → Task 2/3 create `method_kilo` independently; Task 1's only method_mega touch is the import. ✓
- Shared constants in `solver.py`, imported by both → Task 1. ✓
- Stages `white_corners` / `upper_ring` / `lower_ring` via righty insertion → Task 2. ✓
- LL permute-then-orient (`CORNER_CYCLE` then `RIGHTY`) → Task 3. ✓
- `solve()` records a 5-step `Solution`, raises if unsolved → Task 3. ✓
- `scramble()` helper → Task 3. ✓
- Fuzz proof ≥50 seeds in the fast suite → Task 3 (`_solver_full_solve`, 50 seeds). ✓
- `Solution` replay check → Task 3 (`_solver_solution_replays`). ✓
- `build/diag_kilo.py` heavier sweep → Task 4. ✓
- Four-suite regression gate → Task 1 Step 5 and Task 3 Step 5. ✓
- Out of scope (booklet, renderer circle, Ortega, BFS recovery) → correctly absent. ✓

**Placeholder scan:** No TBD/TODO/"handle edge cases"/"similar to". Every code step shows complete code; every run step gives the exact command and expected output. Task 2's test note about `scramble` not yet existing is resolved inline (import only `KiloSolver, corner_key` in Task 2; add `scramble` to the import in Task 3). The 50/200 seed counts are concrete, with explicit instruction not to silently reduce coverage.

**Type/name consistency:** `KiloSolver`, `corner_key`, `scramble`, `righty_corner`, `_eject_corner`, `white_corners`, `upper_ring`, `lower_ring`, `ll_names`, `ll_permute`, `ll_orient`, `solve` are used identically across tasks. `solver.RIGHTY`/`solver.CORNER_CYCLE` are defined in Task 1 and consumed in Tasks 2–3. `puzzle.corner_slots`, `name_faces`, `adj`, `opp`, `stickers`, `minx`, and `P.apply_alg` match the real `Puzzle`/`puzzle` API (verified against `minx/puzzle.py` and `minx/solver.py`). Stage names match the spec's list exactly. `placed(state)` takes a state list in both its definition and call sites in Task 3.
