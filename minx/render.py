"""SVG renderer: orthographic views of the megaminx drawn straight from a
simulator state, in the visual style of the Rubik's booklet diagrams."""
import math
from . import puzzle as P

G = P.geometry

# Standard megaminx colour scheme, assigned around the canonical hold.
PALETTE = {
    'white':  '#f4f4f4',
    'gray':   '#9aa0a6',
    'red':    '#e02020',
    'blue':   '#1565d8',
    'yellow': '#ffd500',
    'purple': '#7b2fbe',
    'green':  '#0fa84e',
    'orange': '#ff8a00',
    'ltblue': '#6ec6ff',
    'cream':  '#fff2b0',
    'pink':   '#ff7bac',
    'lime':   '#9bd927',
}
OPPOSITE_NAME = {
    'white': 'gray', 'red': 'orange', 'blue': 'ltblue',
    'yellow': 'cream', 'purple': 'pink', 'green': 'lime',
}


def color_map(white_face, front_face):
    """face index -> palette key, standard scheme."""
    names = P.name_faces(white_face, front_face)
    cmap = {white_face: 'white'}
    ring = ['red', 'blue', 'yellow', 'purple', 'green']
    for key, col in zip(['F', 'R', 'BR', 'BL', 'L'], ring):
        cmap[names[key]] = col
    for f, col in list(cmap.items()):
        cmap[P.OPP[f]] = OPPOSITE_NAME[col]
    return cmap


def _matvec(M_, v):
    return tuple(sum(M_[i][j] * v[j] for j in range(3)) for i in range(3))


def look_matrix(view_dir, up_hint):
    """Rows: right, up, toward-viewer (z)."""
    z = G._norm(view_dir)                      # points from puzzle to viewer
    x = G._norm(G._cross(up_hint, z))
    y = G._cross(z, x)
    return (x, y, z)


class Camera:
    def __init__(self, u_face, f_face, tilt=0.42, yaw=0.18):
        """Looks at the puzzle so face u is up-toward viewer, f in front.
        tilt: how much of the top face you see; yaw: rotation toward R."""
        nu = P.NORMALS[u_face]
        nf = P.NORMALS[f_face]
        view = G._norm(tuple(nu[i] + tilt * nf[i] for i in range(3)))
        nr = G._cross(G._vmul(nf, -1), nu)
        view = G._norm(tuple(view[i] + yaw * nr[i] for i in range(3)))
        self.M = look_matrix(view, G._vmul(nf, -1))
        self.view = view

    def project(self, p):
        q = _matvec(self.M, p)
        return (q[0], -q[1])   # SVG y goes down


def visible_faces(cam):
    return [fi for fi in range(12)
            if G._dot(P.NORMALS[fi], cam.view) > 0.06]


def render(m, u_face, f_face, cmap, size=120, cam=None, arrow=None,
           dim_faces=None, bright_ids=None, outline_ids=None,
           only_layer=None, pad=4):
    """SVG of state m.  arrow: (face, +1/-1 clicks) draws a turn arrow.
    dim_faces: set of faces to render grayed out (booklet 'color doesn't
    matter' convention).  bright_ids: if given, only these sticker indices
    keep their colour; everything else is grayed."""
    cam = cam or Camera(u_face, f_face)
    vis = visible_faces(cam)
    pts = []
    polys = []   # (depth, points2d, fill, stroke_w)
    for fi in vis:
        for i, s in enumerate(P.STICKERS):
            if s.face != fi:
                continue
            idx = P.ID_TO_IDX[s.id]
            inset = _inset3d(s.polygon, P.NORMALS[fi], 0.028)
            poly2 = [cam.project(p) for p in inset]
            pts.extend(cam.project(p) for p in s.polygon)
            color_face = m.state[idx]
            if bright_ids is not None and idx not in bright_ids:
                fill = '#b9bdc2'
            elif dim_faces and color_face in dim_faces:
                fill = '#b9bdc2'
            elif color_face not in cmap:
                fill = '#b9bdc2'   # sentinel "unknown" sticker
            else:
                fill = PALETTE[cmap[color_face]]
            polys.append((poly2, fill))

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx_, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    w = maxx - minx_
    h = maxy - miny
    scale = (size - 2 * pad) / max(w, h)

    def T(p):
        return ((p[0] - minx_) * scale + pad + (size - 2*pad - w*scale)/2,
                (p[1] - miny) * scale + pad + (size - 2*pad - h*scale)/2)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
           f'height="{size}" viewBox="0 0 {size} {size}">']
    # black body behind everything (slight expand): draw hull of visible faces
    for fi in vis:
        face_poly = [T(cam.project(p)) for p in
                     _expand(P.FACES[fi]['vertices'], 1.03)]
        d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in face_poly) + ' Z'
        out.append(f'<path d="{d}" fill="#111" stroke="#111" '
                   f'stroke-width="{scale*0.06:.2f}" '
                   'stroke-linejoin="round"/>')
    # stickers: inset in 3D within the face plane (uniform real-world gap,
    # correctly foreshortened) and drawn with rounded corners
    for poly2, fill in polys:
        p2 = [T(p) for p in poly2]
        out.append(f'<path d="{_rounded_path(p2)}" fill="{fill}"/>')
    if outline_ids:
        for fi in vis:
            for s in P.STICKERS:
                if s.face != fi or P.ID_TO_IDX[s.id] not in outline_ids:
                    continue
                proj = [cam.project(p) for p in s.polygon]
                c = (sum(p[0] for p in proj) / len(proj),
                     sum(p[1] for p in proj) / len(proj))
                p2 = [T((c[0] + 0.97 * (p[0] - c[0]),
                         c[1] + 0.97 * (p[1] - c[1]))) for p in proj]
                d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in p2) + ' Z'
                out.append(f'<path d="{d}" fill="none" stroke="#e02020" '
                           f'stroke-width="{scale*0.10:.2f}" '
                           'stroke-linejoin="round"/>')
    if arrow:
        out.append(_arrow_svg(cam, arrow, T, scale))
    out.append('</svg>')
    return ''.join(out)


def _inset3d(poly, normal, m):
    """Inset a convex planar polygon by margin m within its plane."""
    c = [sum(p[i] for p in poly) / len(poly) for i in range(3)]
    out = list(poly)
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        edge = G._vsub(b, a)
        ni = G._norm(G._cross(normal, edge))
        # make sure ni points inward (toward centroid)
        if G._dot(G._vsub(c, a), ni) < 0:
            ni = G._vmul(ni, -1)
        pt = G._vadd(a, G._vmul(ni, m))
        out = G._clip(out, pt, ni)
        if len(out) < 3:
            return poly  # degenerate; fall back to original
    return out


def _rounded_path(p2, r=0.22):
    """SVG path for polygon p2 with corners rounded by quadratic beziers."""
    n = len(p2)
    if n < 3:
        return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in p2) + ' Z'
    parts = []
    for i in range(n):
        prev = p2[(i - 1) % n]
        v = p2[i]
        nxt = p2[(i + 1) % n]
        p1 = (v[0] + (prev[0] - v[0]) * r, v[1] + (prev[1] - v[1]) * r)
        q1 = (v[0] + (nxt[0] - v[0]) * r, v[1] + (nxt[1] - v[1]) * r)
        if i == 0:
            parts.append(f'M{p1[0]:.1f},{p1[1]:.1f}')
        else:
            parts.append(f'L{p1[0]:.1f},{p1[1]:.1f}')
        parts.append(f'Q{v[0]:.1f},{v[1]:.1f} {q1[0]:.1f},{q1[1]:.1f}')
    parts.append('Z')
    return ' '.join(parts)


def _expand(verts, factor):
    c = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    return [tuple(c[i] + factor * (v[i] - c[i]) for i in range(3))
            for v in verts]


def _arrow_svg(cam, arrow, T, scale):
    """Curved red arrow showing a face turn, drawn in the face plane."""
    face, clicks = arrow
    n = P.NORMALS[face]
    c = P.FACES[face]['centroid']
    verts = P.FACES[face]['vertices']
    r = 0.62 * math.dist(verts[0], c)
    # build in-plane circle points; direction of sweep = sign of clicks as
    # seen from outside the face
    u = G._norm(G._vsub(verts[0], c))
    w = G._cross(n, u)
    # CW viewed from outside = negative angle direction (right-hand rule)
    sweep = -1 if clicks > 0 else 1
    a0, a1 = 0.45, 0.45 + 1.45 * sweep
    pts = []
    steps = 18
    for s in range(steps + 1):
        a = a0 + (a1 - a0) * s / steps
        p = tuple(c[i] + r * (math.cos(a) * u[i] + math.sin(a) * w[i]) +
                  0.12 * n[i] for i in range(3))
        pts.append(T(cam.project(p)))
    d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    # arrowhead at the end
    (x1, y1), (x0, y0) = pts[-1], pts[-2]
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    dx, dy = dx / L, dy / L
    px, py = -dy, dx
    ah = scale * 0.28
    head = (f'M{x1 + dx*ah:.1f},{y1 + dy*ah:.1f} '
            f'L{x1 - dx*ah*0.6 + px*ah*0.8:.1f},{y1 - dy*ah*0.6 + py*ah*0.8:.1f} '
            f'L{x1 - dx*ah*0.6 - px*ah*0.8:.1f},{y1 - dy*ah*0.6 - py*ah*0.8:.1f} Z')
    return (f'<path d="{d}" fill="none" stroke="#fff" '
            f'stroke-width="{scale*0.16:.2f}" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="#e02020" '
            f'stroke-width="{scale*0.10:.2f}" stroke-linecap="round"/>'
            f'<path d="{head}" fill="#e02020" stroke="#fff" '
            f'stroke-width="{scale*0.03:.2f}"/>')


def render_top(m, u_face, f_face, cmap, size=120, arrow=None,
               dim_faces=None):
    """Bird's-eye view of the U face plus the tops of the 5 ring faces -
    the classic last-layer diagram."""
    cam = Camera(u_face, f_face, tilt=0.0, yaw=0.0)
    return render(m, u_face, f_face, cmap, size=size, cam=cam, arrow=arrow,
                  dim_faces=dim_faces)
