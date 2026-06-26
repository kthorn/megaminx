"""SVG rendering for the cube, reusing the shared orthographic renderer in
``minx.render``. That module is geometry-agnostic -- it reads only a puzzle's
normals/faces/stickers -- so a CubePuzzle (which exposes the same attributes)
draws with it directly; here we add the cube's standard colour scheme and a
camera helper. Squares are drawn (the circular-centre branch only fires for the
kilominx's ``center_shape == 'circle'``)."""
from . import render as R
from . import cube as C

# Standard Western colour scheme. White is the first layer the solver builds
# (the D face) and yellow the last layer (U), with green/blue and red/orange on
# the remaining opposite pairs -- so "make the white cross" is the first stage.
SCHEME = {'D': 'white', 'U': 'yellow', 'F': 'green', 'B': 'blue',
          'R': 'red', 'L': 'orange'}


def color_map(u_face, f_face, puzzle):
    """face index -> palette key for the cube, given which face is held as U
    (top) and which as F (front). With the standard hold U is yellow and the
    opposite face (D) is white."""
    names = puzzle.name_faces(u_face, f_face)
    return {names[k]: col for k, col in SCHEME.items()}


def camera(puzzle, u_face, f_face, tilt=0.5, yaw=0.4):
    return R.Camera(u_face, f_face, tilt=tilt, yaw=yaw, puzzle=puzzle)


def render(state, u_face, f_face, cmap, size=120, cam=None, arrow=None,
           bright_ids=None, puzzle=None):
    pz = puzzle if puzzle is not None else C.CUBE3
    cam = cam or camera(pz, u_face, f_face)
    return R.render(state, u_face, f_face, cmap, size=size, cam=cam,
                    arrow=arrow, bright_ids=bright_ids, puzzle=pz)


def render_flat(state, face, cmap, size=90, puzzle=None):
    """A straight-on view of a single face (handy for the booklet's small
    case diagrams)."""
    pz = puzzle if puzzle is not None else C.CUBE3
    # look directly down the face normal: use it as both U and pick any front.
    front = pz.adj[face][0]
    cam = R.Camera(face, front, tilt=0.0, yaw=0.0, puzzle=pz)
    return R.render(state, face, front, cmap, size=size, cam=cam, puzzle=pz)
