# Kilominx Phase B — Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `KILOMINX = Puzzle(KILOMINX_SPEC)` build a correct 72-sticker simulator, proven by a new `tests/test_kilo.py`, without touching any module downstream of geometry.

**Architecture:** Implement the one missing per-face subdivision (`geometry._subdivide_kite_circular`) that the `kite_circular` branch of `geometry.build` currently stubs with `NotImplementedError`, then instantiate `KILOMINX` as a module-level `Puzzle`. Everything else — `Puzzle`, `pieces.build_pieces(has_edges=False)`, `_layer_indices`, `_perm_for`, `name_faces` — is already puzzle-agnostic and consumes the new stickers unchanged. Correctness is proven by construction: `Puzzle.__init__`'s build-time asserts (layer depth-gap, permutation closure, 20-corners/0-edges grouping) plus the new invariant test module.

**Tech Stack:** Python 3 (no third-party deps for the simulator), bare-tuple vector math via the `_vadd`/`_vsub`/`_vmul`/`_dot` helpers in `minx/geometry.py`. Tests are a plain `main()` printing an OK line, run with `python3 -m tests.<module>`.

## Global Constraints

- Run everything from the repo root; modules import as `minx.*` and `tests.*` (no installed package).
- Vector math uses the bare-tuple helpers in `geometry.py` (`_vadd`, `_vsub`, `_vmul`, `_dot`) — no numpy.
- Float comparisons use explicit epsilons; the build-time geometric `assert`s in `puzzle.py` (`dk - dk1 > 0.05`, `bestd < 1e-6`, permutation closure) are how "correct by construction" is enforced — they must keep passing, not be loosened.
- Sticker append order per face is a convention every consumer relies on: **center first (index 0), then corners by index 0..4.** Corner `ci` must be located at vertex `fverts[ci]` so `pieces.build_pieces` (which keys corners by `_key(fverts[s.index])`) groups the three tiles at each shared dodecahedron vertex into one corner piece.
- The megaminx `edge_parallel` path in `geometry.py` must not be edited. `python3 -m tests.test_puzzle` must still print `all simulator invariants: OK`.
- Kilominx scope for this phase is **geometry + move engine only**: no renderer changes (center-as-circle is Phase D), no solver (`method_kilo.py` is Phase C), no booklet.

---

### Task 1: Kite face-subdivision geometry

**Files:**
- Modify: `minx/geometry.py` (replace the `kite_circular` `NotImplementedError` branch at ~`geometry.py:135-137`; add `_subdivide_kite_circular`)
- Modify: `minx/puzzle.py` (add module-level `KILOMINX` instance after `MEGAMINX = Puzzle(_spec.MEGAMINX_SPEC)` at ~`puzzle.py:190`)
- Create/Test: `tests/test_kilo.py`

**Interfaces:**
- Consumes: `geometry.build(spec)` (already dispatches on `spec.subdivision`); `geometry.Sticker(face, kind, index, polygon)`; helpers `_vadd`, `_vsub`, `_vmul`; `spec.cut_fraction` (0.42 on `KILOMINX_SPEC`); `Puzzle(spec)`; `minx.spec.KILOMINX_SPEC`.
- Produces: `geometry._subdivide_kite_circular(spec, fi, fverts, centroid, stickers)` appending 6 stickers per face (1 `center` index 0, 5 `corner` indices 0..4); module global `puzzle.KILOMINX`, a `Puzzle` over `KILOMINX_SPEC` with `n_stickers == 72`, `corners` (20 × 3 tiles), `edges == {}`.

- [ ] **Step 1: Write the failing counts test**

Create `tests/test_kilo.py`:

```python
"""Kilominx simulator invariants. Run: python3 -m tests.test_kilo"""
from collections import Counter
from minx import puzzle as P


def main():
    K = P.KILOMINX

    # --- sticker + piece counts ---
    assert K.n_stickers == 72, K.n_stickers
    kinds = Counter(s.kind for s in K.stickers)
    assert kinds == {'center': 12, 'corner': 60}, kinds
    assert len(K.corners) == 20 and all(len(v) == 3 for v in K.corners.values())
    assert K.edges == {}, K.edges

    print("all kilominx invariants: OK")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m tests.test_kilo`
Expected: FAIL — `AttributeError: module 'minx.puzzle' has no attribute 'KILOMINX'` (the module global does not exist yet; once added in Step 4 but before Step 3 it would instead surface the `NotImplementedError` from `geometry.build`).

- [ ] **Step 3: Implement the kite subdivision**

In `minx/geometry.py`, replace the stub branch:

```python
        elif spec.subdivision == 'kite_circular':
            raise NotImplementedError(
                "kite_circular subdivision is implemented in Phase B")
```

with a call:

```python
        elif spec.subdivision == 'kite_circular':
            _subdivide_kite_circular(spec, fi, fverts, centroid, stickers)
```

and add the new function next to `_subdivide_edge_parallel` (after it, end of file):

```python
def _subdivide_kite_circular(spec, fi, fverts, centroid, stickers):
    """Kilominx face: 1 cosmetic center cap + 5 corner kites meeting at C.

    The 5 kites tile the whole pentagon down to the face center C; the center
    sticker is a small pentagon scaled toward C (its centroid is exactly C), so
    it maps onto itself under the face turn and the renderer can draw it as a
    circle (Phase D). The cap is cosmetic: the kites still extend to C beneath
    it. Corner ci is keyed at vertex fverts[ci], matching the megaminx so
    pieces.build_pieces groups the three tiles meeting at each shared dodeca-
    hedron vertex into one corner piece."""
    c = centroid
    # midpoint of each face edge; edge ei joins fverts[ei] and fverts[ei+1]
    mids = [_vmul(_vadd(fverts[ei], fverts[(ei + 1) % 5]), 0.5)
            for ei in range(5)]

    # center cap: face pentagon scaled toward C by cut_fraction (centroid == C)
    cap = [_vadd(c, _vmul(_vsub(fverts[k], c), spec.cut_fraction))
           for k in range(5)]
    stickers.append(Sticker(fi, 'center', 0, cap))

    # 5 corner kites: [V_ci, M_ci, C, M_(ci-1)]
    for ci in range(5):
        poly = [fverts[ci], mids[ci], c, mids[(ci - 1) % 5]]
        stickers.append(Sticker(fi, 'corner', ci, poly))
```

- [ ] **Step 4: Instantiate the KILOMINX puzzle**

In `minx/puzzle.py`, just below the existing megaminx instance line (`MEGAMINX = Puzzle(_spec.MEGAMINX_SPEC)`, ~line 190), add:

```python
KILOMINX = Puzzle(_spec.KILOMINX_SPEC)
```

(Place it on the line immediately after `MEGAMINX = Puzzle(_spec.MEGAMINX_SPEC)`, before the `NORMALS = MEGAMINX.normals` aliases. Building it at import runs the kite geometry through all of `Puzzle.__init__`'s asserts — layer depth-gap (`dk - dk1 > 0.05`), permutation closure (`bestd < 1e-6`, `sorted(perm) == range`), and `pieces.build_pieces` 20-corners/0-edges grouping — so a broken subdivision fails loudly at import.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m tests.test_kilo`
Expected: PASS — prints `all kilominx invariants: OK`.

- [ ] **Step 6: Confirm the megaminx regression gate**

Run: `python3 -m tests.test_puzzle`
Expected: PASS — prints `all simulator invariants: OK` (the `edge_parallel` path was not touched).

- [ ] **Step 7: Commit**

```bash
git add minx/geometry.py minx/puzzle.py tests/test_kilo.py
git commit -m "feat: kilominx kite geometry; KILOMINX builds (72 stickers, 20 corners)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Move-engine and layer invariants

**Files:**
- Modify: `tests/test_kilo.py` (extend `main()` with the engine/layer invariant blocks)

**Interfaces:**
- Consumes: `P.KILOMINX` with attributes `stickers`, `layers`, `normals`, `adj`, `id_to_idx`, methods `minx()`, `name_faces(u, f)`; `_Minx.turn(fi, times)`, `.state`, `.is_solved()`; `P.apply_alg(minx, alg, names)`.
- Produces: nothing consumed downstream — this task hardens the invariant net that proves the move engine composes correctly on the kilominx.

- [ ] **Step 1: Add the order-5 / center-fixity / layer-shape / composition invariants**

Edit `tests/test_kilo.py`. Insert the following blocks into `main()` after the `assert K.edges == {}` line and before the `print(...)`:

```python
    # --- order-5 face turns; the center sticker is fixed by its own turn ---
    for fi in range(12):
        cidx = K.id_to_idx[(fi, 'center', 0)]
        m = K.minx()
        for _ in range(5):
            m.turn(fi)
            assert m.state[cidx] == fi, (fi, 'center moved')
        assert m.is_solved(), fi

    # --- layer shape: 16 = 6 own (center + 5 corners) + 10 strip (corners) ---
    for fi in range(12):
        own = [i for i in K.layers[fi] if K.stickers[i].face == fi]
        strip = [i for i in K.layers[fi] if K.stickers[i].face != fi]
        assert len(own) == 6 and len(strip) == 10, (fi, len(own), len(strip))
        assert Counter(K.stickers[i].kind for i in own) == \
            {'center': 1, 'corner': 5}, fi
        assert Counter(K.stickers[i].kind for i in strip) == {'corner': 10}, fi

    # --- move engine composes & inverts ---
    m = K.minx()
    m.turn(0)
    m.turn(0, -1)
    assert m.is_solved()                      # a turn and its inverse cancel
    a = K.minx(); a.turn(3, 2)
    b = K.minx(); b.turn(3); b.turn(3)
    assert a.state == b.state                 # double turn == two singles

    # sexy move R U Ri Ui returns to solved in a finite, nontrivial number of
    # repeats (proves named turns compose and invert correctly on the kilominx)
    u = max(range(12), key=lambda fi: K.normals[fi][2])
    f = min(K.adj[u], key=lambda fi: K.normals[fi][1])
    names = K.name_faces(u, f)
    m = K.minx()
    order = None
    for k in range(1, 200):
        P.apply_alg(m, "R U Ri Ui", names)
        if m.is_solved():
            order = k
            break
    assert order is not None and order > 1, order
```

(`Counter` is already imported at the top of the file from Task 1.)

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m tests.test_kilo`
Expected: PASS — prints `all kilominx invariants: OK`. If the layer-shape assert fails (e.g. a foreign center in the strip, or own ≠ 6), the kite geometry is wrong — fix the subdivision in Task 1, do not loosen the assert.

- [ ] **Step 3: Confirm the megaminx regression gate still holds**

Run: `python3 -m tests.test_puzzle`
Expected: PASS — prints `all simulator invariants: OK`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_kilo.py
git commit -m "test: kilominx move-engine & layer invariants (order-5, 6/10 layer, sexy)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage** (against `2026-06-16-kilominx-phase-b-geometry-design.md`):
- Kite subdivision, center cap scaled by `cut_fraction`, corner `ci` at `fverts[ci]`, append order center-then-corners → Task 1, Step 3. ✓
- `Puzzle(KILOMINX_SPEC)` builds / `KILOMINX` importable → Task 1, Step 4. ✓
- 72 stickers; 12 centers + 60 corners; 20 corner pieces (3 tiles); 0 edges → Task 1, Step 1. ✓
- Center fixity; order-5 turns → Task 2 (order-5 + per-step center check). ✓
- Layer shape 6 own / 10 strip with kind composition → Task 2. ✓
- Move-engine composition (compose/invert/double + sexy) → Task 2. ✓
- Regression gate `test_puzzle` green → Task 1 Step 6 and Task 2 Step 3. ✓
- Out-of-scope (render circle, solver, booklet) — correctly absent from all tasks. ✓
- Build-time depth-gap / permutation-closure asserts as the correctness proof → relied on in Task 1 Step 4 note. ✓

**Placeholder scan:** No TBD/TODO/"add error handling"/"similar to". Every code step shows complete code; every run step states the exact command and expected output. The sexy-move order is discovered (asserted finite and `> 1`) rather than hardcoded, because the kilominx order is not pre-verified — this is a deliberate, fully-specified assertion, not a placeholder.

**Type/name consistency:** `K = P.KILOMINX` throughout; attributes used (`n_stickers`, `stickers`, `corners`, `edges`, `layers`, `normals`, `adj`, `id_to_idx`) and methods (`minx()`, `name_faces`, `turn`, `is_solved`, `state`) all match `Puzzle`/`_Minx` in `puzzle.py`. `_subdivide_kite_circular(spec, fi, fverts, centroid, stickers)` matches the call site and the existing `_subdivide_edge_parallel` signature. `Sticker(fi, kind, index, polygon)` matches `geometry.Sticker.__init__`. Helper names (`_vadd`, `_vsub`, `_vmul`) match `geometry.py`.
