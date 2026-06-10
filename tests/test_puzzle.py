"""Simulator invariants. Run: python3 -m tests.test_puzzle"""
from collections import Counter
from minx import puzzle as P
from minx import pieces
G = P.geometry


def canonical_hold():
    u = max(range(12), key=lambda fi: P.NORMALS[fi][2])
    f = min(P.ADJ[u], key=lambda fi: P.NORMALS[fi][1])
    return P.name_faces(u, f)


def main():
    assert P.N_STICKERS == 132

    m = P.Minx()
    for fi in range(12):
        mm = m.copy()
        for _ in range(5):
            mm.turn(fi)
        assert mm.is_solved(), fi

    for fi in range(12):
        own = [i for i in P.LAYERS[fi] if P.STICKERS[i].face == fi]
        strip = [i for i in P.LAYERS[fi] if P.STICKERS[i].face != fi]
        assert len(own) == 11 and len(strip) == 15
        assert Counter(P.STICKERS[i].kind for i in strip) == \
            {'corner': 10, 'edge': 5}

    for u2 in range(12):
        for f2 in P.ADJ[u2]:
            nm = P.name_faces(u2, f2)
            assert nm['F'] == f2 and nm['U'] == u2
            nu, nf = P.NORMALS[u2], P.NORMALS[f2]
            right = G._cross(G._vmul(nf, -1), nu)
            assert G._dot(P.FACES[nm['R']]['centroid'], right) > 0.1
            assert G._dot(P.FACES[nm['L']]['centroid'], right) < -0.1

    names = canonical_hold()
    mm = P.Minx().turn(names['U'])
    fe = [i for i in P.LAYERS[names['U']]
          if P.STICKERS[i].face == names['F'] and P.STICKERS[i].kind == 'edge']
    assert mm.state[fe[0]] == names['R']  # CW U sends R strip into F slot

    mm = P.Minx()
    for k in range(1, 500):
        P.apply_alg(mm, "R U Ri Ui", names)
        if mm.is_solved():
            break
    assert k == 6  # sexy move has order 6 on megaminx too

    # piece grouping sanity
    assert len(pieces.CORNERS) == 20 and len(pieces.EDGES) == 30

    print("all simulator invariants: OK")


if __name__ == '__main__':
    main()
