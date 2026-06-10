# Megaminx Solution Guide — Design

**Date:** 2026-06-09
**Goal:** A printable PDF megaminx solving guide for a kid who already solves the 3x3
with the official Rubik's "Solution Guide" booklet, matching that booklet's style,
detail level, algorithm presentation, and imagery.

## Source material

`Rubiks.pdf` (13 pages, 5.5"×7.5", scanned official 2010 Seven Towns guide).
Style conventions to mirror:

- Blue water-wave page background; yellow rounded "STAGE N:" badge + blue banner title.
- Per stage: green "Holding Your Cube:" intro, orange "Tips:" bullets with color-coded
  words, "Your Goal" starburst callout with a picture of the target state.
- Algorithms as rows of picture tiles: puzzle-state drawing above a blue rounded square
  containing the move letter; red arrows on the drawing show the turn.
- Notation: R L U D F letters, "i" suffix = inverse (counter-clockwise).
- Green "Congratulations!" box ends each stage and gates progression.
- Yellow oval page numbers, alternating corners.

## Structure (≈14 pages, same size)

1. Cover — "MEGAMINX · Solution Guide · Unlock the Secret!"
2. Stage 1: Get to know your Megaminx (12 faces; edge/corner/center pieces)
3. Notation page — face letters on labelled pictures, "i" rule, 1/5 turns
4. Stage 2: White star
5. Stage 3: White corners (Ri Di R D — same righty moves as the cube)
6. Stage 4: Second-layer edges
7. Stage 5: Working down — repeat corners + edges row by row until only gray remains
8. Stage 6: Gray star (last-layer edge orientation)
9. Stage 7: Position the star edges
10. Stage 8: Position the gray corners
11. Stage 9: Orient the gray corners → final Congratulations
12. Fun facts / back page

Color scheme: standard white-start, gray-last-layer megaminx. Kid-facing voice
identical to the original ("If your Megaminx looks like this picture you can move
to Stage 5!").

## Approach (user-approved: option 1, simulator-driven)

- **Simulator:** Python sticker-level megaminx built from real dodecahedron geometry.
  A face turn = 72° rotation about the face normal applied to all sticker points in
  that layer, mapped to nearest sticker positions. Correct by construction; verified
  by permutation-order tests.
- **Algorithm verification:** every algorithm printed in the guide is executed in the
  simulator first; its exact effect (which pieces move/twist) is checked against what
  the guide claims. Case tables (e.g. star-orientation states) are *derived from* the
  simulator, not hand-reasoned.
- **Diagrams:** every state picture is rendered from the simulator state at that point
  in the algorithm — orthographic 3D SVG projection of the dodecahedron with sticker
  polygons, painter's algorithm, arrow overlays. Move tiles mirror the booklet format.
- **Layout:** HTML/CSS replicating the booklet, rendered to PDF (weasyprint or headless
  Chrome). Pages rasterized and visually reviewed before delivery.

## Out of scope

Speedsolving methods, alternate color schemes, video/interactive content.
