#!/usr/bin/env python3
"""Camera calibration by the Direct Linear Transform, step by step.

Everything the companion notes derive, in the order they derive it:
  1. make up a camera K, a pose (R, o) of a calibration jig, and project its points
  2. build the 2n x 12 system A p = 0 from the pixel positions
  3. solve it (smallest singular vector), giving Pi up to scale
  4. take Pi apart: the scale from its bottom row, K and R by Gram-Schmidt from
     the bottom row up, the sign from the points being in front, o from the last column
  5. compare with the truth -- exact pixels, then 0.5 px of noise, then refinement
  6. two things the derivation predicts: a flat jig fails, and errors come in pairs
Only numpy is used, so every step is visible.   python3 dlt_calibration.py
"""
import numpy as np
np.set_printoptions(precision=4, suppress=True)

# ---- 1. the set-up -----------------------------------------------------------
K_true = np.array([[800.0,   0.0, 640.0],   # f_x, skew, principal point (pixels)
                   [  0.0, 800.0, 360.0],   # f_y
                   [  0.0,   0.0,   1.0]])

def rotation(axis, deg):
    """Rotation matrix for an angle about a unit axis (Rodrigues' formula)."""
    k = np.asarray(axis, float); k /= np.linalg.norm(k)
    a = np.radians(deg)
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(a) * Kx + (1 - np.cos(a)) * Kx @ Kx

R_true = rotation([0.3, 1.0, 0.1], -30.0)   # the jig seen from 30 degrees to one side
o_true = np.array([-0.15, -0.10, 1.50])     # its origin 1.5 m in front of the camera

# the jig: an L of two perpendicular faces, points every 0.15 m -- 9 on the floor
# (z_W = 0) and 6 on the wall (x_W = 0). Not all in one plane; that matters (step 6).
def jig(spacing):
    g = spacing * np.arange(3)
    floor = np.array([[x, y, 0.0] for x in g for y in g])
    wall = np.array([[0.0, y, z] for y in g for z in g[1:]])
    return floor, np.vstack([floor, wall])  # 15 points, one per row
floor, X_W = jig(0.15)

def project(K, R, o, X_W):
    """Pixel coordinates of world points X_W (rows), with the depth division done explicitly."""
    X_C = X_W @ R.T + o                     # r^C = R r^W + o, one row per point
    uvw = X_C @ K.T                         # K r^C: (f_x X + s Y + o_xs Z,  f_y Y + o_ys Z,  Z)
    lam = uvw[:, 2]                         # the third row is Z, the depth -- that is lambda
    return uvw[:, :2] / lam[:, None], lam

pix, lam = project(K_true, R_true, o_true, X_W)

# ---- 2. the 2n x 12 system --------------------------------------------------
def build_A(X_W, pix):
    """Two rows per point:  [X^T 0^T -x X^T ; 0^T X^T -y X^T] p = 0,  X = (x_W, y_W, z_W, 1)."""
    rows = []
    for (xw, yw, zw), (x, y) in zip(X_W, pix):
        X = np.array([xw, yw, zw, 1.0])
        rows.append(np.concatenate([X, np.zeros(4), -x * X]))
        rows.append(np.concatenate([np.zeros(4), X, -y * X]))
    return np.array(rows)

# ---- 3. solve for Pi up to scale --------------------------------------------
def solve_P(A):
    """The p that makes A p as small as possible with |p| = 1: the last right singular vector."""
    _, S, Vt = np.linalg.svd(A)
    return Vt[-1].reshape(3, 4), S

# ---- 4. from Pi to K, R, o ---------------------------------------------------
def decompose(P, X_W):
    """Pi = c K [R | o], with K upper triangular (positive diagonal), R a rotation."""
    X_h = np.hstack([X_W, np.ones((len(X_W), 1))])
    if np.mean(X_h @ P[2]) < 0:             # third row of Pi X is c times the depth:
        P = -P                              # the points are in front, so make it positive
    M, p4 = P[:, :3], P[:, 3]
    c = np.linalg.norm(M[2])                # bottom row of M is c r3^T, and |r3| = 1
    M, p4 = M / c, p4 / c                   # now M = K R exactly (if the data were exact)
    r3 = M[2]                               # bottom row of K is (0, 0, 1): M's bottom row is r3
    o_ys = M[1] @ r3                        # middle row: f_y r2 + o_ys r3, and r2 is perpendicular to r3
    v = M[1] - o_ys * r3
    f_y = np.linalg.norm(v); r2 = v / f_y
    o_xs = M[0] @ r3                        # top row: f_x r1 + s r2 + o_xs r3
    s = M[0] @ r2
    u = M[0] - o_xs * r3 - s * r2
    f_x = np.linalg.norm(u); r1 = u / f_x
    R = np.vstack([r1, r2, r3])             # orthonormal rows by construction
    K = np.array([[f_x, s, o_xs], [0.0, f_y, o_ys], [0.0, 0.0, 1.0]])
    o = np.linalg.solve(K, p4)              # last column is K o
    return K, R, o

def angle_between(R1, R2):
    """Angle, in degrees, of the rotation that takes R1 to R2."""
    cosang = (np.trace(R1.T @ R2) - 1) / 2
    return np.degrees(np.arccos(np.clip(cosang, -1, 1)))

def reproj(K, R, o, X_W, pix):
    """Root-mean-square distance, in pixels, between the measured points and where the model puts them."""
    return np.sqrt(np.mean((project(K, R, o, X_W)[0] - pix) ** 2))

# ---- 5. refine: make the points reproject where they were seen ---------------
def refine(K, R, o, X_W, pix, iters=10, square=False):
    """Gauss-Newton on the reprojection error, starting from the closed form.
    The intrinsics are the five entries of K as they stand or, with square=True,
    only three (f, o_xs, o_ys): square pixels and no skew, as every modern sensor
    has. The pose is a small rotation vector w applied as R <- R(w) R and a shift
    of o. The Jacobian is by finite differences: each column is 'how far do the
    2n pixel coordinates move when this parameter moves a little'."""
    if square:
        k = np.array([(K[0, 0] + K[1, 1]) / 2, K[0, 2], K[1, 2]])
        unpack = lambda k: np.array([[k[0], 0, k[1]], [0, k[0], k[2]], [0, 0, 1.0]])
    else:
        k = np.array([K[0, 0], K[0, 1], K[0, 2], K[1, 1], K[1, 2]])
        unpack = lambda k: np.array([[k[0], k[1], k[2]], [0, k[3], k[4]], [0, 0, 1.0]])
    nk = len(k)
    for _ in range(iters):
        res = (project(unpack(k), R, o, X_W)[0] - pix).ravel()
        J = np.zeros((res.size, nk + 6))
        for j in range(nk + 6):
            dk, w, do = np.zeros(nk), np.zeros(3), np.zeros(3)
            eps = 1e-4 if j < nk else 1e-6
            if j < nk:       dk[j] = eps
            elif j < nk + 3: w[j - nk] = eps
            else:            do[j - nk - 3] = eps
            Rj = rotation(w, np.degrees(eps)) @ R if nk <= j < nk + 3 else R
            res_j = (project(unpack(k + dk), Rj, o + do, X_W)[0] - pix).ravel()
            J[:, j] = (res_j - res) / eps
        step = np.linalg.lstsq(J, -res, rcond=None)[0]
        k = k + step[:nk]
        if np.linalg.norm(step[nk:nk + 3]) > 0:
            R = rotation(step[nk:nk + 3], np.degrees(np.linalg.norm(step[nk:nk + 3]))) @ R
        o = o + step[nk + 3:]
    return unpack(k), R, o

# ---- 6. run it -----------------------------------------------------------------
def run(pix, label):
    print("==== %s ====" % label)
    A = build_A(X_W, pix)
    P, S = solve_P(A)
    print("singular values of A:", S)
    K, R, o = decompose(P, X_W)
    print("recovered K:\n", K)
    print("recovered o^C_W   :", o, "   true:", o_true)
    print("R^T R - I, largest entry: %.1e   det R = %.4f" % (np.abs(R.T @ R - np.eye(3)).max(), np.linalg.det(R)))
    print("rotation error    : %.4f deg" % angle_between(R_true, R))
    print("position error    : %.2f mm" % (1000 * np.linalg.norm(o - o_true)))
    print("reprojection error: %.3f px (RMS)" % reproj(K, R, o, X_W, pix))
    for square in (False, True):
        K2, R2, o2 = refine(K, R, o, X_W, pix, square=square)
        print("refined, %s: f_x %.1f  f_y %.1f  s %.2f  pp (%.1f, %.1f)"
              % ("all 11 parameters   " if not square else "square pixels, 9 par", K2[0, 0], K2[1, 1], K2[0, 1], K2[0, 2], K2[1, 2]))
        print("    rotation error %.4f deg, position error %.2f mm, reprojection %.3f px"
              % (angle_between(R_true, R2), 1000 * np.linalg.norm(o2 - o_true), reproj(K2, R2, o2, X_W, pix)))
    print()

def repeats(X_W, pix, rng, n=500):
    """The noisy calibration n times over, to see what is typical and which errors travel together."""
    e = {k: [] for k in ("f_x", "f_y", "s", "o_xs", "z", "theta_y", "rot", "pos", "f_11", "f_9", "rot_9", "pos_9")}
    for _ in range(n):
        pn = pix + rng.normal(0, 0.5, pix.shape)
        K, R, o = decompose(solve_P(build_A(X_W, pn))[0], X_W)
        dR = R @ R_true.T                   # the small rotation left over, as a vector
        w = np.degrees(np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / 2)
        e["f_x"].append(K[0, 0] - 800); e["f_y"].append(K[1, 1] - 800); e["s"].append(K[0, 1])
        e["o_xs"].append(K[0, 2] - 640); e["z"].append(1000 * (o[2] - o_true[2])); e["theta_y"].append(w[1])
        e["rot"].append(angle_between(R_true, R)); e["pos"].append(1000 * np.linalg.norm(o - o_true))
        e["f_11"].append(refine(K, R, o, X_W, pn)[0][0, 0] - 800)
        K9, R9, o9 = refine(K, R, o, X_W, pn, square=True)
        e["f_9"].append(K9[0, 0] - 800); e["rot_9"].append(angle_between(R_true, R9)); e["pos_9"].append(1000 * np.linalg.norm(o9 - o_true))
    return {k: np.array(v) for k, v in e.items()}

if __name__ == "__main__":
    print("%d jig points; depths lambda from %.3f to %.3f m; image spans x %.0f..%.0f, y %.0f..%.0f px\n"
          % (len(X_W), lam.min(), lam.max(), pix[:, 0].min(), pix[:, 0].max(), pix[:, 1].min(), pix[:, 1].max()))

    run(pix, "exact pixels")
    rng = np.random.default_rng(1)
    run(pix + rng.normal(0, 0.5, pix.shape), "pixels with 0.5 px noise")

    # ---- a flat jig: the floor points only ----
    print("==== the 9 floor points alone (all in the plane z_W = 0), exact pixels ====")
    _, S = solve_P(build_A(floor, pix[:9]))
    print("singular values of A:", S)
    print("four are zero, not one: z_W = 0 wipes out three columns of A, so Pi is not determined\n")

    # ---- 500 repeats ----
    e = repeats(X_W, pix, rng)
    print("==== 500 repeats at 0.5 px noise, jig 0.3 m across ====")
    print("closed form   : f_x off by %.1f px (median |error|), f_y by %.1f, skew %.1f, principal point x %.1f px"
          % tuple(np.median(np.abs(e[k])) for k in ("f_x", "f_y", "s", "o_xs")))
    print("                rotation error median %.2f deg, position error median %.0f mm" % (np.median(e["rot"]), np.median(e["pos"])))
    print("refined, 11   : f_x off by %.1f px" % np.median(np.abs(e["f_11"])))
    print("refined, 9    : f off by %.1f px; rotation error median %.2f deg, position error median %.0f mm"
          % (np.median(np.abs(e["f_9"])), np.median(e["rot_9"]), np.median(e["pos_9"])))
    print("errors that travel together (correlation over the 500 runs, closed form):")
    print("   focal length f_x  and  depth of the jig o_z        : %+.2f" % np.corrcoef(e["f_x"], e["z"])[0, 1])
    print("   principal point o_xs  and  rotation about y_C      : %+.2f" % np.corrcoef(e["o_xs"], e["theta_y"])[0, 1])
    print("   f_x  and  f_y                                      : %+.2f" % np.corrcoef(e["f_x"], e["f_y"])[0, 1])
    print()

    # ---- the same jig three times larger, filling the frame ----
    _, X_big = jig(0.45)
    pix_big, lam_big = project(K_true, R_true, o_true, X_big)
    e = repeats(X_big, pix_big, rng)
    print("==== 500 repeats at 0.5 px noise, jig 0.9 m across (depths %.2f to %.2f m, image spans %.0f px) ===="
          % (lam_big.min(), lam_big.max(), np.ptp(pix_big[:, 0])))
    print("closed form   : f_x off by %.1f px, principal point x %.1f px; rotation error median %.2f deg, position error median %.0f mm"
          % (np.median(np.abs(e["f_x"])), np.median(np.abs(e["o_xs"])), np.median(e["rot"]), np.median(e["pos"])))
    print("refined, 9    : f off by %.1f px; rotation error median %.2f deg, position error median %.0f mm"
          % (np.median(np.abs(e["f_9"])), np.median(e["rot_9"]), np.median(e["pos_9"])))
    print("   focal length f_x  and  depth of the jig o_z, closed form: %+.2f" % np.corrcoef(e["f_x"], e["z"])[0, 1])
