#!/usr/bin/env python3
"""Render the tag's pixels under motion blur, for the blur figure on the slides.

The tag36h11 (id 0) pattern is projected through the pinhole model of
fiducial_pose.py at a tilt of 30 degrees about its horizontal axis, 0.10 m across
at z = 2.5 m with f = 800 px, so 32 px wide and 4 px per cell. The image is
rendered at 8 x 8 sub-samples per pixel, smeared along x by a box of length b
pixels (the motion during the exposure), and averaged to pixels. Each pixel's
grey level is written as a TikZ fill into

    ../../lectures/01-kinematics-kinetics/data/blur-pixels.tex

as macros \\blurimgZERO, \\blurimgTWO, \\blurimgFOUR, \\blurimgEIGHT (b = 0, 2, 4, 8 px),
each a list of  \\fill[black!G] (x, y) rectangle ++(1, 1);  in pixel units with the
tag centre at the origin. tikz/blur-images.tex draws them.
    python3 make_blur_pixels.py
"""
import pathlib, io, contextlib, importlib.util
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parents[1] / "lectures" / "01-kinematics-kinetics" / "data" / "blur-pixels.tex"
spec = importlib.util.spec_from_file_location("fp", HERE / "fiducial_pose.py")
fp = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(fp)

F, D, Z, TILT = 800.0, 0.10, 2.5, 30.0
HALF, SS = 32, 8                                  # rendered half-size in px (the figure shows +-20; the margin keeps the blur off the array edge), sub-samples per pixel
BLURS = {"ZERO": 0.0, "TWO": 2.0, "FOUR": 4.0, "EIGHT": 8.0}

BLACK = {(0,7),(1,7),(2,7),(3,7),(4,7),(5,7),(6,7),(7,7),(0,6),(1,6),(2,6),(4,6),(5,6),(6,6),(7,6),
         (0,5),(1,5),(4,5),(6,5),(7,5),(0,4),(1,4),(2,4),(3,4),(5,4),(7,4),(0,3),(1,3),(2,3),(3,3),
         (6,3),(7,3),(0,2),(2,2),(6,2),(7,2),(0,1),(2,1),(4,1),(7,1),(0,0),(1,0),(2,0),(3,0),(4,0),
         (5,0),(6,0),(7,0)}
CELLS = np.ones((8, 8))                            # 1 = white
for c, r in BLACK: CELLS[r, c] = 0

# the tag's pose: facing the camera, tilted about its horizontal axis, top edge away
R = fp.rotation([1, 0, 0], TILT) @ np.diag([1.0, -1.0, -1.0])
o = np.array([0.0, 0.0, Z])
H = np.array([[F, 0, 0], [0, F, 0], [0, 0, 1]]) @ np.column_stack([R[:, 0], R[:, 1], o])
Hi = np.linalg.inv(H)

# the sharp image on the sub-sample grid (pixel centres at i + 0.5, y down in the image)
n = 2 * HALF * SS
coords = (np.arange(n) + 0.5) / SS - HALF
U, V = np.meshgrid(coords, coords)
P = Hi @ np.stack([U.ravel(), V.ravel(), np.ones(U.size)])
a, b = P[0] / P[2] / (D / 2), P[1] / P[2] / (D / 2)
img = np.ones(a.shape)                             # white quiet zone everywhere
inside = (np.abs(a) < 1) & (np.abs(b) < 1)
col = np.clip(((a[inside] + 1) * 4).astype(int), 0, 7)
row = np.clip(((b[inside] + 1) * 4).astype(int), 0, 7)
img[inside] = CELLS[row, col]
img = img.reshape(n, n)

def blur(img, bpx):
    """Box blur of bpx pixels along x, on the sub-sample grid, symmetric."""
    if bpx <= 0: return img
    k = int(round(bpx * SS)); k += (k + 1) % 2
    ker = np.ones(k) / k
    return np.apply_along_axis(lambda r: np.convolve(r, ker, mode="same"), 1, img)

lines = ["% written by notes/01-kinematics-kinetics/make_blur_pixels.py; do not edit"]
for name, bpx in BLURS.items():
    pix = blur(img, bpx).reshape(2 * HALF, SS, 2 * HALF, SS).mean(axis=(1, 3))
    cmds = []
    for j in range(2 * HALF):
        for i in range(2 * HALF):
            g = int(round(100 * (1 - pix[j, i])))   # 0 = white, 100 = black
            if g > 0:
                # TikZ y goes up, the image's v goes down: flip
                cmds.append("\\fill[black!%d] (%d,%d) rectangle ++(1,1);" % (g, i - HALF, HALF - 1 - j))
    lines.append("\\def\\blurimg%s{%s}" % (name, " ".join(cmds)))
OUT.write_text("\n".join(lines) + "\n")
print("wrote", OUT, "with", sum(len(l) for l in lines), "characters")
