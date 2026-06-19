"""Kilominx simulator invariants. Run: python3 -m tests.test_kilo"""
from collections import Counter
from minx import puzzle as P
from minx.method_kilo import KiloSolver, corner_key


def main():
    K = P.KILOMINX

    # --- sticker + piece counts ---
    assert K.n_stickers == 72, K.n_stickers
    kinds = Counter(s.kind for s in K.stickers)
    assert kinds == {'center': 12, 'corner': 60}, kinds
    assert len(K.corners) == 20 and all(len(v) == 3 for v in K.corners.values())
    assert K.edges == {}, K.edges

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

    # sexy move R U Ri Ui has order 6 on the kilominx (proves named turns
    # compose and invert correctly); 200 >> any plausible order, so failing to
    # converge is a real bug, not an arbitrary cap.
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
    assert order == 6, order

    _solver_stages_123()
    print("all kilominx invariants: OK")


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


if __name__ == '__main__':
    main()
