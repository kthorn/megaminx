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
