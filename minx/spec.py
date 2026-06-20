"""Per-puzzle configuration. A PuzzleSpec captures the small set of values
that differ between the megaminx and the kilominx; everything else in the
core is derived identically for both."""
from dataclasses import dataclass


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
