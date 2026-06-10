"""Dodecahedron geometry for the megaminx: faces, sticker polygons, layers.

Everything downstream (the move engine and the SVG renderer) is derived from
this real 3D model, so sticker adjacency is never hand-coded.
"""
import math
from itertools import product

PHI = (1 + 5 ** 0.5) / 2

# Fraction of the apothem (face-center -> edge distance) at which the layer
# cuts cross a face.  Real megaminxes cut deep: the center pentagon spans
# only ~55-60% of the face.
CUT_FRACTION = 0.42  # cut line sits 42% of the way from the edge to the center


def _vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _vsub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _vmul(a, s):
    return tuple(x * s for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return _vmul(a, 1 / n)


def rotate(p, axis, angle):
    """Rodrigues rotation of point p about unit axis."""
    k = axis
    c, s = math.cos(angle), math.sin(angle)
    kxp = _cross(k, p)
    kdp = _dot(k, p)
    return tuple(p[i] * c + kxp[i] * s + k[i] * kdp * (1 - c) for i in range(3))


def dodecahedron_vertices():
    verts = []
    for sx, sy, sz in product((1, -1), repeat=3):
        verts.append((sx, sy, sz))
    for s1, s2 in product((1, -1), repeat=2):
        verts.append((0, s1 / PHI, s2 * PHI))
        verts.append((s1 / PHI, s2 * PHI, 0))
        verts.append((s1 * PHI, 0, s2 / PHI))
    return verts


def face_normals():
    normals = []
    for s1, s2 in product((1, -1), repeat=2):
        normals.append(_norm((0, s1 * PHI, s2)))
        normals.append(_norm((s1, 0, s2 * PHI)))
        normals.append(_norm((s1 * PHI, s2, 0)))
    return normals


def _face_vertices(normal, verts):
    """The 5 vertices of the face with this normal, ordered CCW viewed from outside."""
    scored = sorted(verts, key=lambda v: -_dot(v, normal))
    five = scored[:5]
    centroid = _vmul(_vadd(_vadd(five[0], five[1]),
                           _vadd(_vadd(five[2], five[3]), five[4])), 1 / 5)
    # build in-plane basis
    u = _norm(_vsub(five[0], centroid))
    w = _cross(normal, u)
    five.sort(key=lambda v: math.atan2(_dot(_vsub(v, centroid), w),
                                       _dot(_vsub(v, centroid), u)))
    return five, centroid


def _clip(poly, point_on_line, inward_normal):
    """Sutherland-Hodgman clip of 3D polygon (planar) against half-space
    dot(p - point_on_line, inward_normal) >= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da = _dot(_vsub(a, point_on_line), inward_normal)
        db = _dot(_vsub(b, point_on_line), inward_normal)
        if da >= -1e-12:
            out.append(a)
            if db < -1e-12:
                t = da / (da - db)
                out.append(_vadd(a, _vmul(_vsub(b, a), t)))
        elif db >= -1e-12:
            t = da / (da - db)
            out.append(_vadd(a, _vmul(_vsub(b, a), t)))
    return out


class Sticker:
    __slots__ = ('face', 'kind', 'index', 'polygon', 'centroid', 'id')

    def __init__(self, face, kind, index, polygon):
        self.face = face          # face index 0..11
        self.kind = kind          # 'center' | 'edge' | 'corner'
        self.index = index        # 0..4 within the face (0 for center)
        self.polygon = polygon    # list of 3D points
        c = (0.0, 0.0, 0.0)
        for p in polygon:
            c = _vadd(c, p)
        self.centroid = _vmul(c, 1 / len(polygon))
        self.id = (face, kind, index)


def build():
    """Returns (normals, faces, stickers) where faces[i] = dict with
    'vertices', 'centroid', 'normal'; stickers = list of Sticker."""
    verts = dodecahedron_vertices()
    normals = face_normals()
    faces = []
    stickers = []
    for fi, n in enumerate(normals):
        fverts, centroid = _face_vertices(n, verts)
        faces.append({'vertices': fverts, 'centroid': centroid, 'normal': n})

        # cut lines: one parallel to each edge, CUT_FRACTION of the way in
        cuts = []  # (point_on_line, inward_normal_in_plane)
        for ei in range(5):
            a, b = fverts[ei], fverts[(ei + 1) % 5]
            mid = _vmul(_vadd(a, b), 0.5)
            inward = _norm(_vsub(centroid, mid))
            cutpt = _vadd(mid, _vmul(_vsub(centroid, mid), CUT_FRACTION))
            cuts.append((cutpt, inward))

        pent = list(fverts)
        # center: inside all five cuts
        poly = pent
        for cutpt, inward in cuts:
            poly = _clip(poly, cutpt, inward)
        stickers.append(Sticker(fi, 'center', 0, poly))

        # edge sticker ei: outside cut ei, inside cuts ei-1 and ei+1
        for ei in range(5):
            poly = pent
            cutpt, inward = cuts[ei]
            poly = _clip(poly, cutpt, _vmul(inward, -1))
            for other in ((ei - 1) % 5, (ei + 1) % 5):
                ocut, oin = cuts[other]
                poly = _clip(poly, ocut, oin)
            stickers.append(Sticker(fi, 'edge', ei, poly))

        # corner sticker ci sits at vertex (ci): outside cuts ci-1 and ci
        # (vertex ci is shared by edges ci-1 and ci)
        for ci in range(5):
            poly = pent
            for other in ((ci - 1) % 5, ci):
                ocut, oin = cuts[other]
                poly = _clip(poly, ocut, _vmul(oin, -1))
            stickers.append(Sticker(fi, 'corner', ci, poly))

    return normals, faces, stickers
