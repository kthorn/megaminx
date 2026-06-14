# Kilominx Phase A — Instance-Based Shared Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the megaminx-only `minx/` package into an instance-based shared core (`Puzzle` built from a `PuzzleSpec`) that can host a second puzzle, while keeping the shipped megaminx simulator, solver, and booklet behaving exactly as before.

**Architecture:** Today `minx/puzzle.py` builds module-level globals at import — fine for one puzzle, impossible for two. We promote that into a `Puzzle` instance carrying all derived data and methods, build `MEGAMINX = Puzzle(MEGAMINX_SPEC)`, and re-export its attributes as backward-compatible module globals so existing megaminx consumers change minimally. We also add turn recording to `Minx`, a `BaseSolver` + `Solution` contract shared by future solvers, and split the booklet builder into a reusable framework plus megaminx content. No kilominx code is built in this phase; we only make the core able to host it.

**Tech Stack:** Python 3.13+ (stdlib only for the engine; `weasyprint` for the booklet). Tests are plain `python3 -m` scripts asserting invariants — there is no pytest config in this repo.

**Spec:** `docs/superpowers/specs/2026-06-13-kilominx-design.md`

---

## Scope of this plan

This plan implements **Phase A only**. Phases B–D (kilominx geometry, solver, booklet) are scoped in the roadmap at the end and will each become their own plan once Phase A fixes the interface. The Phase A gate: **all existing megaminx invariants pass unchanged**, and the megaminx booklet rebuilds and is **diff-reviewed** (incidental rendering changes accepted deliberately, not required to be byte-identical).

## File structure (Phase A)

| File | Action | Responsibility |
|---|---|---|
| `minx/spec.py` | Create | `PuzzleSpec` dataclass + `MEGAMINX_SPEC`, `KILOMINX_SPEC` constants |
| `minx/geometry.py` | Modify | `build(spec)` parameterized; megaminx (edge-parallel) subdivision implemented; kilominx subdivision deferred to Phase B |
| `minx/pieces.py` | Modify | Pure `build_pieces(stickers, faces, has_edges)`; `piece_at`/`solved_piece`/`describe_effect` take explicit puzzle/stickers (no module globals) |
| `minx/puzzle.py` | Rewrite | `Puzzle` class (all derived data + `name_faces` + piece slots + `minx()` factory); `Minx` class with turn history; `MEGAMINX` instance + backward-compat module globals; `parse_alg`/`apply_alg` free functions |
| `minx/render.py` | Modify | All functions take an optional `puzzle` defaulting to `MEGAMINX`; replace internal `P.<global>` with `puzzle.<attr>` |
| `minx/solver.py` | Create | `Step`/`Solution` records + `BaseSolver` (puzzle-parameterized generics: bands, `assert_solved_intact`, `mark`, `free_faces`, `bfs_to`, `ferry`, `try_insert`, `find_corner`/`find_edge`, per-step recording) |
| `minx/method.py` → `minx/method_mega.py` | Rename + modify | `Solver(BaseSolver)` keeping all megaminx stages; emits a `Solution` |
| `build/diag_stage4.py`, `diag_stage6.py`, `diag_stage6_fast.py` | Modify | Update `method`→`method_mega` import (one line each) |
| `build/make_guide.py` | Modify | Update `method`→`method_mega` import; rebuild + diff-review. (The `guide_common`/`guide_mega` framework split is deferred to **Phase D**, where `guide_kilo` actually needs the shared framework; Phase A only requires the megaminx booklet to keep building.) |
| `tests/test_puzzle.py` | Unchanged | Megaminx invariants — the regression proof. Must keep passing as-is. |
| `tests/test_core.py` | Create | New-surface tests: `Puzzle` instance attrs, `Minx` history, `build_pieces`, `Solution` recording |

**Import-cycle rule:** `pieces.build_pieces` must stay pure (params only; no `import puzzle` at module top) because `puzzle.py` imports `pieces`. `solver.py` imports `puzzle` (for the `Minx` factory type) but `method_mega.py` imports both; no cycle since `puzzle.py` does not import `solver`/`method_mega`.

---

## Task 1: PuzzleSpec and the two specs

**Files:**
- Create: `minx/spec.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_core.py`:

```python
"""Tests for the instance-based shared core. Run: python3 -m tests.test_core"""
from minx import spec


def test_specs():
    mm = spec.MEGAMINX_SPEC
    assert mm.name == "megaminx"
    assert mm.has_edges is True
    assert mm.has_centers is True
    assert mm.layer_size == 26
    assert mm.subdivision == "edge_parallel"
    assert abs(mm.cut_fraction - 0.42) < 1e-9
    assert mm.center_shape == "pentagon"

    ki = spec.KILOMINX_SPEC
    assert ki.name == "kilominx"
    assert ki.has_edges is False
    assert ki.has_centers is True          # colored centers, like a 3x3
    assert ki.layer_size == 16             # 6 own + 10 strip
    assert ki.subdivision == "kite_circular"
    assert ki.center_shape == "circle"
    assert mm.color_ring == ki.color_ring  # same 5-color ring


def main():
    test_specs()
    print("test_core.test_specs: OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m tests.test_core`
Expected: FAIL with `ModuleNotFoundError: No module named 'minx.spec'`

- [ ] **Step 3: Write the implementation**

Create `minx/spec.py`:

```python
"""Per-puzzle configuration. A PuzzleSpec captures the small set of values
that differ between the megaminx and the kilominx; everything else in the
core is derived identically for both."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PuzzleSpec:
    name: str
    has_edges: bool
    has_centers: bool
    subdivision: str          # 'edge_parallel' | 'kite_circular'
    layer_size: int           # stickers in one face's turning layer
    center_shape: str         # 'pentagon' | 'circle' (render only)
    cut_fraction: float = 0.42
    color_ring: tuple = ('red', 'blue', 'yellow', 'purple', 'green')


MEGAMINX_SPEC = PuzzleSpec(
    name="megaminx",
    has_edges=True,
    has_centers=True,
    subdivision="edge_parallel",
    layer_size=26,
    center_shape="pentagon",
    cut_fraction=0.42,
)

KILOMINX_SPEC = PuzzleSpec(
    name="kilominx",
    has_edges=False,
    has_centers=True,
    subdivision="kite_circular",
    layer_size=16,
    center_shape="circle",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m tests.test_core`
Expected: `test_core.test_specs: OK`

- [ ] **Step 5: Commit**

```bash
git add minx/spec.py tests/test_core.py
git commit -m "feat: add PuzzleSpec with megaminx and kilominx configs"
```

---

## Task 2: Parameterize geometry.build(spec)

`geometry.build()` currently takes no args and uses the module constant `CUT_FRACTION`. Make it take a spec and dispatch the per-face subdivision. Only the megaminx (`edge_parallel`) path is implemented here; the kilominx (`kite_circular`) path raises a clear error and is filled in Phase B.

**Files:**
- Modify: `minx/geometry.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_core.py` (and call it in `main()`):

```python
from minx import geometry
from minx import spec as _spec


def test_build_megaminx():
    normals, faces, stickers = geometry.build(_spec.MEGAMINX_SPEC)
    assert len(normals) == 12 and len(faces) == 12
    assert len(stickers) == 132
    from collections import Counter
    kinds = Counter(s.kind for s in stickers)
    assert kinds == {"center": 12, "edge": 60, "corner": 60}


def test_build_kilominx_not_yet():
    try:
        geometry.build(_spec.KILOMINX_SPEC)
    except NotImplementedError:
        return
    raise AssertionError("kilominx subdivision should be unimplemented in Phase A")
```

Update `main()`:

```python
def main():
    test_specs()
    test_build_megaminx()
    test_build_kilominx_not_yet()
    print("test_core: OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m tests.test_core`
Expected: FAIL — `build() takes 0 positional arguments but 1 was given`

- [ ] **Step 3: Modify `build` to accept a spec**

In `minx/geometry.py`, change the signature and the cut fraction source, and dispatch on `spec.subdivision`. Replace the current `def build():` definition with:

```python
def build(spec):
    """Returns (normals, faces, stickers) for the given PuzzleSpec.
    Shared: dodecahedron vertices/normals, face vertices, Sticker class.
    Per-puzzle: the face subdivision into stickers."""
    verts = dodecahedron_vertices()
    normals = face_normals()
    faces = []
    stickers = []
    for fi, n in enumerate(normals):
        fverts, centroid = _face_vertices(n, verts)
        faces.append({'vertices': fverts, 'centroid': centroid, 'normal': n})
        if spec.subdivision == 'edge_parallel':
            _subdivide_edge_parallel(spec, fi, fverts, centroid, stickers)
        elif spec.subdivision == 'kite_circular':
            raise NotImplementedError(
                "kite_circular subdivision is implemented in Phase B")
        else:
            raise ValueError(f"unknown subdivision {spec.subdivision!r}")
    return normals, faces, stickers
```

Then add a new function holding the existing megaminx subdivision body (moved verbatim out of the old `build`, with `CUT_FRACTION` replaced by `spec.cut_fraction`):

```python
def _subdivide_edge_parallel(spec, fi, fverts, centroid, stickers):
    """Megaminx face: 1 center + 5 edges + 5 corners via edge-parallel cuts."""
    cuts = []  # (point_on_line, inward_normal_in_plane)
    for ei in range(5):
        a, b = fverts[ei], fverts[(ei + 1) % 5]
        mid = _vmul(_vadd(a, b), 0.5)
        inward = _norm(_vsub(centroid, mid))
        cutpt = _vadd(mid, _vmul(_vsub(centroid, mid), spec.cut_fraction))
        cuts.append((cutpt, inward))

    pent = list(fverts)
    poly = pent
    for cutpt, inward in cuts:
        poly = _clip(poly, cutpt, inward)
    stickers.append(Sticker(fi, 'center', 0, poly))

    for ei in range(5):
        poly = pent
        cutpt, inward = cuts[ei]
        poly = _clip(poly, cutpt, _vmul(inward, -1))
        for other in ((ei - 1) % 5, (ei + 1) % 5):
            ocut, oin = cuts[other]
            poly = _clip(poly, ocut, oin)
        stickers.append(Sticker(fi, 'edge', ei, poly))

    for ci in range(5):
        poly = pent
        for other in ((ci - 1) % 5, ci):
            ocut, oin = cuts[other]
            poly = _clip(poly, ocut, _vmul(oin, -1))
        stickers.append(Sticker(fi, 'corner', ci, poly))
```

Leave the module-level `CUT_FRACTION = 0.42` constant in place (now unused by `build`, but harmless and documents the default); the spec carries the value.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m tests.test_core`
Expected: `test_core: OK`

- [ ] **Step 5: Commit**

```bash
git add minx/geometry.py tests/test_core.py
git commit -m "refactor: geometry.build takes a PuzzleSpec, dispatch subdivision"
```

---

## Task 3: Pure build_pieces()

Extract the piece grouping from `pieces.py`'s import-time `_build()` into a pure function taking stickers/faces, so the `Puzzle` instance can call it for either puzzle. Make `solved_piece`/`describe_effect` take explicit context instead of reaching for module globals.

**Files:**
- Modify: `minx/pieces.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_core.py` (and call in `main()`):

```python
from minx import pieces


def test_build_pieces():
    _, faces, stickers = geometry.build(_spec.MEGAMINX_SPEC)
    corners, edges = pieces.build_pieces(stickers, faces, has_edges=True)
    assert len(corners) == 20 and all(len(v) == 3 for v in corners.values())
    assert len(edges) == 30 and all(len(v) == 2 for v in edges.values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m tests.test_core`
Expected: FAIL — `module 'minx.pieces' has no attribute 'build_pieces'`

- [ ] **Step 3: Rewrite `minx/pieces.py`**

Replace the whole file with a pure-function version (no top-level `puzzle` import, no import-time globals):

```python
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
    of the named faces. Returns (moved, twisted, minx, summary_string)."""
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
```

> Note: `describe_effect` now takes `puzzle` as its first argument (was a module global). It currently has **no callers** in the repo (verified by grep), so this is a forward-compatible signature change with nothing else to update.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m tests.test_core`
Expected: `test_core: OK`

- [ ] **Step 5: Commit**

```bash
git add minx/pieces.py tests/test_core.py
git commit -m "refactor: pieces.build_pieces() is pure, takes stickers/faces"
```

---

## Task 4: Puzzle class, Minx with history, MEGAMINX + compat globals

This is the core of Phase A. Rewrite `minx/puzzle.py` so all derived data and methods live on a `Puzzle` instance; `Minx` carries a turn history; build `MEGAMINX`; and re-export its attributes as backward-compatible module globals so `method.py`/`make_guide.py`/`render.py`/`tests/test_puzzle.py` keep working unchanged.

**Files:**
- Rewrite: `minx/puzzle.py`
- Test: `tests/test_core.py`, plus the unchanged `tests/test_puzzle.py` must still pass.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_core.py` (and call in `main()`):

```python
from minx import puzzle as P


def test_puzzle_instance_and_history():
    pz = P.MEGAMINX
    assert pz.n_stickers == 132
    assert len(pz.layers) == 12 and len(pz.cw_perms) == 12
    assert len(pz.corners) == 20 and len(pz.edges) == 30
    # backward-compat module globals point at the megaminx instance
    assert P.N_STICKERS == 132
    assert P.STICKERS is pz.stickers
    assert P.NORMALS is pz.normals
    # Minx records turns it actually performs
    m = pz.minx()
    m.turn(0, 2)
    m.turn(3, -1)
    assert m.history == [(0, 2), (3, 4)]   # -1 normalizes to 4 fifth-turns
    # full 5-turn returns to solved and records nothing (times %% 5 == 0)
    m2 = pz.minx()
    m2.turn(1, 5)
    assert m2.is_solved() and m2.history == []
    # compat factory
    assert P.Minx().is_solved()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m tests.test_core`
Expected: FAIL — `module 'minx.puzzle' has no attribute 'MEGAMINX'`

- [ ] **Step 3: Rewrite `minx/puzzle.py`**

Replace the whole file:

```python
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


class Minx:
    def __init__(self, puzzle, colors=None):
        self.puzzle = puzzle
        self.state = list(colors) if colors is not None else \
            [s.face for s in puzzle.stickers]
        self.history = []   # list of (fi, times) actually-applied turns

    def copy(self):
        # Exploratory copies start with a fresh history; only the solver's
        # working cube accumulates the move record.
        return Minx(self.puzzle, self.state)

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
        return Minx(self, colors)

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
    """Backward-compatible factory: a megaminx Minx. New code should prefer
    `puzzle.minx()` on an explicit Puzzle instance."""
    return MEGAMINX.minx(colors)
```

> Behavior notes preserved from the original: `turn` normalizes `times %= 5`; `name_faces`, `_adjacent`, `_opposites`, `parse_alg`, `apply_alg` bodies are unchanged except for `self.`/`math.` qualification. The compat `Minx` is now a factory function, not a class — every existing call site uses it as `Minx(...)`/`Minx()` so this is transparent.

- [ ] **Step 4: Run the new and the regression tests**

Run: `python3 -m tests.test_core`
Expected: `test_core: OK`

Run: `python3 -m tests.test_puzzle`
Expected: `all simulator invariants: OK` (unchanged — this is the regression proof for the engine refactor)

- [ ] **Step 5: Commit**

```bash
git add minx/puzzle.py tests/test_core.py
git commit -m "refactor: Puzzle instance + Minx history; MEGAMINX compat globals"
```

---

## Task 5: render.py takes an optional puzzle

Make every public renderer function accept `puzzle=None` (defaulting to `MEGAMINX`) and use `puzzle.<attr>` internally instead of `P.<global>`. Megaminx callers are unchanged because the default is the megaminx instance.

**Files:**
- Modify: `minx/render.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_core.py` (and call in `main()`):

```python
from minx import render as R
from tests.test_puzzle import canonical_hold


def test_render_smoke():
    names = canonical_hold()
    cmap = R.color_map(names['U'], names['F'])
    svg = R.render(P.MEGAMINX.minx(), names['U'], names['F'], cmap, size=120)
    assert svg.startswith('<svg') and svg.endswith('</svg>')
    assert 'path' in svg
```

- [ ] **Step 2: Run test to verify it fails or errors**

Run: `python3 -m tests.test_core`
Expected: FAIL — `render()` currently has no compatible signature path / uses module globals only (and `color_map` already works, but `render` must accept the instance state). If it happens to pass, still proceed to Step 3 to remove the module-global coupling so kilominx can render later.

- [ ] **Step 3: Thread `puzzle` through render.py**

At the top of `minx/render.py`, after `G = P.geometry`, add:

```python
def _pz(puzzle):
    return puzzle if puzzle is not None else P.MEGAMINX
```

Then in each function that reads puzzle data, add a `puzzle=None` parameter and bind `pz = _pz(puzzle)` as the first line, replacing internal references:
- `color_map(white_face, front_face, puzzle=None)`: use `pz.name_faces(...)` and `pz.opp`.
- `Camera.__init__(self, u_face, f_face, tilt=0.42, yaw=0.18, puzzle=None)`: use `pz.normals`.
- `visible_faces(cam, puzzle=None)`: use `pz.normals`.
- `render(m, u_face, f_face, cmap, size=120, cam=None, ..., puzzle=None)`: use `pz.stickers`, `pz.id_to_idx`, `pz.normals`, `pz.faces`. Default `cam = cam or Camera(u_face, f_face, puzzle=pz)`.
- `_arrow_svg`, `render_top`: thread `puzzle=None` and use `pz`.

Where `render` currently iterates `for i, s in enumerate(P.STICKERS)` and uses `P.ID_TO_IDX[s.id]`, `P.NORMALS[fi]`, `P.FACES[fi]`, replace `P.` with `pz.` (`pz.stickers`, `pz.id_to_idx`, `pz.normals`, `pz.faces`). Keep `G.` (geometry) calls as-is.

> Keep `m.state` indexed exactly as today; `m` already carries its own puzzle, but render uses the passed `puzzle`/default for geometry. For megaminx both are the same instance.

- [ ] **Step 4: Run tests**

Run: `python3 -m tests.test_core`
Expected: `test_core: OK`

Run: `python3 -m tests.test_puzzle`
Expected: `all simulator invariants: OK`

- [ ] **Step 5: Commit**

```bash
git add minx/render.py tests/test_core.py
git commit -m "refactor: render.py threads an optional puzzle (defaults to MEGAMINX)"
```

---

## Task 6: solver.py — Solution records + BaseSolver

Extract the puzzle-agnostic solver scaffolding from `method.py` into `minx/solver.py`: the `Step`/`Solution` records and a `BaseSolver` that owns bands bookkeeping, `assert_solved_intact`, `mark`, `free_faces`, `bfs_to`, `ferry`, `try_insert`, `find_corner`, `find_edge`, and per-step move recording. The megaminx-specific stages stay in `method_mega.py` (Task 7).

**Files:**
- Create: `minx/solver.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_core.py` (and call in `main()`):

```python
from minx import solver


def test_base_solver_records_steps():
    pz = P.MEGAMINX
    s = solver.BaseSolver(pz.minx(), white=0)
    assert s.gray == pz.opp[0]
    # begin/end a step and confirm the raw turns are captured
    s.begin_step("demo", hold_text="white up")
    s.m.turn(0, 1)
    s.m.turn(3, 2)
    step = s.end_step()
    assert step.stage == "demo"
    assert step.hold_text == "white up"
    assert step.moves == [(0, 1), (3, 2)]
    assert s.solution[-1] is step
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m tests.test_core`
Expected: FAIL — `No module named 'minx.solver'`

- [ ] **Step 3: Write `minx/solver.py`**

```python
"""Puzzle-agnostic solver scaffolding shared by all puzzle methods.

Holds bookkeeping (which pieces must stay solved), generic search helpers
(BFS / ferry to bring a piece to a slot over free faces), and per-step move
recording producing a structured Solution that a UI/API can replay."""
from collections import deque
from dataclasses import dataclass, field
from . import puzzle as P


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

    def bfs_to(self, piece_colors, target_ids, ok=None, depth=4,
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
```

> This is the existing `Solver` machinery from `method.py` lines 69–244, re-parameterized on `self.puzzle` instead of module globals, with `find_corner`/`find_edge` promoted to methods reading `self.puzzle.corner_slots`/`edge_slots`, plus the new `Step`/`Solution`/`begin_step`/`end_step` recording. `try_insert`'s backup/restore of `self.m` does not rewind `self.m.history`; callers wrap whole insertions in begin/end_step so a discarded grip's turns are not recorded (Task 7 covers usage).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m tests.test_core`
Expected: `test_core: OK`

- [ ] **Step 5: Commit**

```bash
git add minx/solver.py tests/test_core.py
git commit -m "feat: BaseSolver + Solution/Step recording in minx/solver.py"
```

---

## Task 7: method.py → method_mega.py rebased on BaseSolver

Rename `minx/method.py` to `minx/method_mega.py` and rebase its `Solver` on `BaseSolver`, deleting the now-shared scaffolding and re-pointing module-global lookups to the megaminx instance. The megaminx stage logic (white star, righty corners, edge inserts, last layer) is unchanged.

**Files:**
- Rename: `minx/method.py` → `minx/method_mega.py`
- Modify: the renamed file
- Test: `tests/test_puzzle.py` (unchanged), `tests/test_core.py`

- [ ] **Step 1: Rename with git**

```bash
git mv minx/method.py minx/method_mega.py
```

- [ ] **Step 2: Write the failing test**

Add to `tests/test_core.py` (and call in `main()`):

```python
from minx import method_mega


def test_megaminx_solver_records_solution():
    pz = P.MEGAMINX
    m = pz.minx()
    method_mega.scramble(m, seed=7)
    s = method_mega.Solver(m, white=0)
    s.solve()
    assert s.m.is_solved()
    assert len(s.solution) > 0
    # every recorded step replays to its snapshot from the prior state
    replay = pz.minx()
    method_mega.scramble(replay, seed=7)
    for step in s.solution.steps:
        for fi, t in step.moves:
            replay.turn(fi, t)
        assert replay.state == step.state_after
```

- [ ] **Step 3: Edit `minx/method_mega.py`**

Make these specific changes:

1. **Imports** — replace the top imports:

```python
import random
from . import puzzle as P
from . import pieces
from .solver import BaseSolver, MethodError, Step, Solution

G = P.geometry
```

2. **Module-level slot maps and lookups** — the file currently builds `CORNER_SLOTS`/`EDGE_SLOTS` from `pieces.CORNERS`/`EDGES` (lines ~41–44). Re-point them to the megaminx instance and **keep** the module-level `corner_key`/`edge_key`/`find_corner`/`find_edge`/`solved_ids` functions (so the diag scripts and the unchanged megaminx stage bodies keep calling them):

```python
CORNER_SLOTS = P.MEGAMINX.corner_slots
EDGE_SLOTS = P.MEGAMINX.edge_slots


def corner_key(faces):
    return tuple(sorted(faces))


def edge_key(faces):
    return tuple(sorted(faces))


def find_corner(m, colors):
    want = sorted(colors)
    for ids in CORNER_SLOTS.values():
        if sorted(m.state[i] for i in ids) == want:
            return ids
    raise AssertionError(colors)


def find_edge(m, colors):
    want = sorted(colors)
    for ids in EDGE_SLOTS.values():
        if sorted(m.state[i] for i in ids) == want:
            return ids
    raise AssertionError(colors)


def solved_ids(m, tracked):
    st = P.STICKERS
    return [ids for ids in tracked
            if all(m.state[i] == st[i].face for i in ids)]
```

> `BaseSolver` also exposes `find_corner`/`find_edge` as methods (for the generic/kilominx path). These module-level twins are the megaminx-compat surface; the stage bodies call the unqualified module functions and need no edit.

3. **Delete `class MethodError`** from this file — it now lives in `solver.py` and is imported (re-exported via the `from .solver import` line so `method_mega.MethodError` still resolves).

4. **Solver base + `__init__`** — change `class Solver:` to `class Solver(BaseSolver):` and delete its `__init__` plus the methods now provided by the base: `assert_solved_intact`, `mark`, `free_faces`, `bfs_to`, `ferry`, `try_insert` (lines ~74–244). Keep all stage methods (`white_star`, `righty_corner`, `_eject_corner`, `insert_edge`, ... through `ll_corners_orient`, `solve`) **unchanged** — they call the module-level `find_corner`/`find_edge` and the compat globals `P.apply_alg`/`P.name_faces`/`P.Minx`/`P.ADJ`/`P.OPP`/`P.STICKERS`/`P.LAYERS`, all of which still resolve.

5. **Record steps in `solve()`** — wrap each stage call so its turns are captured. Replace the body of `solve` with:

```python
    def solve(self):
        for stage, fn in [
            ("white-star", self.white_star),
            ("white-corners", self.white_corners),
            ("row1-edges", self.row1_edges),
            ("row2-band", self.row2_band),
            ("row3-corners", self.row3_corners),
            ("ridge-edges", self.ridge_edges),
            ("ll-star", self.ll_star),
            ("ll-edges", self.ll_edges),
            ("ll-corner-pos", self.ll_corners_position),
            ("ll-corner-orient", self.ll_corners_orient),
        ]:
            self.begin_step(stage)
            fn()
            self.end_step()
            self.assert_solved_intact(stage)
        if not self.m.is_solved():
            raise MethodError("end state not solved")
```

> This preserves the original stage order and the `assert_solved_intact` checkpoints (previously after the LL stages) and now records one `Step` per stage. Finer-grained per-insertion steps are a later enhancement; one step per stage satisfies the `Solution` contract and the replay test.

6. Keep `scramble(m, n=60, seed=None)` at the bottom unchanged.

7. **Update the diag-script importers** so the rename doesn't break them. In each of `build/diag_stage4.py`, `build/diag_stage6.py`, `build/diag_stage6_fast.py`, change `from minx import method as M` to `from minx import method_mega as M`. Nothing else in them changes: `M.scramble`, `M.Solver`, `M.MethodError` (re-exported via the `from .solver import` line), `M.CORNER_SLOTS`, `M.EDGE_SLOTS`, `M.corner_key`, `M.edge_key`, and the module-level `M.find_corner`/`M.find_edge` (kept in item 2) all still resolve. `s._eject_corner(...)` is a kept stage method on `Solver`, so it resolves too.

- [ ] **Step 4: Run the regression and new tests**

Run: `python3 -m tests.test_puzzle`
Expected: `all simulator invariants: OK`

Run: `python3 -m tests.test_core`
Expected: `test_core: OK`

Run a broader solver fuzz to confirm no behavior regression:

```bash
python3 -c "
from minx import puzzle as P, method_mega as M
ok = 0
for seed in range(200):
    m = P.MEGAMINX.minx(); M.scramble(m, seed=seed)
    s = M.Solver(m, 0)
    try:
        s.solve(); ok += s.m.is_solved()
    except M.MethodError:
        pass
print('solved', ok, '/ 200')
"
```
Expected: a high count (matches pre-refactor behavior; the diag scripts already note some scrambles raise `MethodError`). Record the number; it must not drop versus a run of the pre-refactor code.

- [ ] **Step 5: Commit**

```bash
git add minx/method_mega.py build/diag_stage4.py build/diag_stage6.py build/diag_stage6_fast.py tests/test_core.py
git commit -m "refactor: Solver rebased on BaseSolver; emits a Solution per stage"
```

---

## Task 8: Keep the megaminx booklet building

Phase A only requires the megaminx booklet to keep building (the gate is tests-green + booklet diff-reviewed). The only break is the `method` → `method_mega` rename. We make the minimal change here and **defer** the `guide_common`/`guide_mega` framework extraction to Phase D, where `guide_kilo` actually needs a shared framework — extracting it now would be a large, behavior-neutral move with no Phase A consumer.

**Files:**
- Modify: `build/make_guide.py` (one import line)
- Test: booklet build + diff review

- [ ] **Step 1: Update the method import in `build/make_guide.py`**

Change line 11 from:

```python
from minx import puzzle as P, method as M, render as R
```

to:

```python
from minx import puzzle as P, method_mega as M, render as R
```

No other change is needed: `make_guide.py` uses `M.RIGHTY`, `M.INSERT_RIGHT`, `M.INSERT_LEFT`, `M.STAR_EO`, `M.EDGE_CYCLE`, `M.CORNER_CYCLE`, `M.FLIP_FIX`, `M.CORNER_SLOTS`, `M.EDGE_SLOTS`, `M.corner_key`, `M.edge_key` — all still defined in `method_mega.py`. The `P.<global>`/`R.<fn>` references resolve via the compat globals and the `puzzle`-defaulted render functions.

- [ ] **Step 2: Build the booklet**

Run: `python3 build/make_guide.py`
Expected: `wrote .../out/guide.pdf (16 pages)` (same page count as before).

- [ ] **Step 3: Diff-review the rendered output**

```bash
git --no-pager diff --stat -- out/guide.html out/guide.pdf
```

Open `out/guide.html` in a browser (or the PDF) and confirm pages and diagrams match the prior booklet. Per the Phase A gate, incidental whitespace/encoding changes are acceptable; the visible content and diagrams must match. If `out/guide.html`/`out/guide.pdf` show no meaningful diff, all the better — the refactor was behavior-neutral.

- [ ] **Step 4: Commit**

```bash
git add build/make_guide.py out/guide.html out/guide.pdf
git commit -m "refactor: point booklet build at method_mega; rebuild + diff-review"
```

---

## Task 9: Phase A regression gate

Confirm the whole Phase A gate before declaring it done.

**Files:** none (verification only)

- [ ] **Step 1: Run all tests**

```bash
python3 -m tests.test_puzzle
python3 -m tests.test_core
```
Expected: `all simulator invariants: OK` and `test_core: OK`.

- [ ] **Step 2: Confirm the solver fuzz count did not regress**

Run the 200-seed fuzz from Task 7 Step 4 and confirm the solved count matches the pre-refactor baseline (check out the parent commit in a scratch worktree if a baseline number was not recorded).

- [ ] **Step 3: Confirm the booklet built and was diff-reviewed**

Confirm `out/guide.pdf` exists, has the expected page count, and the HTML diff was reviewed and accepted.

- [ ] **Step 4: Confirm the kilominx seam exists but is dormant**

```bash
python3 -c "from minx import spec; print(spec.KILOMINX_SPEC.name, spec.KILOMINX_SPEC.layer_size)"
python3 -c "from minx import geometry, spec; geometry.build(spec.KILOMINX_SPEC)" 2>&1 | tail -1
```
Expected: prints `kilominx 16`, and the second command ends with `NotImplementedError: kite_circular subdivision is implemented in Phase B` — proving the core is ready to host the kilominx without it being half-built.

- [ ] **Step 5: Tag the phase**

```bash
git commit --allow-empty -m "chore: Phase A complete — instance-based shared core, megaminx green"
```

---

## Roadmap: Phases B–D (separate plans)

These are scoped here but will each get their own detailed plan once Phase A fixes the interface. They are **not** executable tasks in this plan.

### Phase B — Kilominx geometry
- Implement `_subdivide_kite_circular(spec, fi, fverts, centroid, stickers)` in `geometry.py`: 5 corner kites `[Vᵢ, Mᵢ, C, Mᵢ₋₁]` + a center sticker at C (small polygon, rendered as a circle). Wire it into `build()`'s dispatch.
- Construct `KILOMINX = Puzzle(KILOMINX_SPEC)` (add alongside `MEGAMINX`).
- `render.py`: draw the center as a circle when `puzzle.spec.center_shape == 'circle'`.
- `tests/test_kilo.py`: 72 stickers; 20 corners + 12 centers; no edges; per-face 5× turn = identity; layer counts 6 own / 10 strip; sexy-move order.
- Gate: kilominx simulator invariants pass; megaminx tests still green.

### Phase C — Kilominx solver
- `minx/method_kilo.py`: `KiloSolver(BaseSolver)` with stages — white corners → upper-mid ring → lower-mid ring → last-layer orient (CO) → last-layer permute (CP). Reuses `BaseSolver` primitives; emits a `Solution`.
- The specific move sequences (ring-insert commutators, CO/CP algorithms) are discovered empirically against the simulator (as the megaminx ones were); the plan's test is the proof harness: `KiloSolver.solve()` over N scrambles all end solved with solved-piece-intact checks.
- `tests/test_kilo.py`: add the solver fuzz.
- Gate: solver proven over many seeds.

### Phase D — Kilominx booklet
- **First, extract the booklet framework** (deferred from Phase A): split `build/make_guide.py` into `build/guide_common.py` (a puzzle-agnostic `Guide`: `svg_img`/`tiles_html`/`picture`/`page`/`banner`/`holding`/`tips`/`congrats`/`F`/`colorword` + weasyprint `render_pdf`, parameterized on `puzzle`/`cmap`/holding-names) and `build/guide_mega.py` (megaminx content), with `make_guide.py` reduced to a shim. Re-run the megaminx booklet diff-review to confirm behavior-neutral.
- Then `build/guide_kilo.py` on the `Guide` framework: cover → hold/notation → one page per stage, diagrams rendered from `KILOMINX` states.
- Gate: megaminx booklet still diff-clean after the split; kilominx PDF builds and is reviewed.

### Future / out of scope (tracked in the spec)
- 2×2-style (Ortega) last-layer method for the kilominx.
- Coach-site integration (the `Solution` contract is built to be consumed by it).
- No-dead-end solver hardening (bounded-BFS recovery) for both puzzles.
```
