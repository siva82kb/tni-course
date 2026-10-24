#!/usr/bin/env python3
"""Pose of a square fiducial from one image, step by step.

Everything the companion notes derive, in the order they derive it:
  1. make up a camera K and a true pose (R, o) of the tag, and project its corners
  2. build the 8 x 9 system A h = 0 from the four pixel corners
  3. solve it (smallest singular vector), giving H up to scale
  4. undo K, fix the scale, the sign and the missing column, snap to a rotation
  5. compare with the truth -- first without noise, then with 0.5 px of noise
Only numpy is used, so every step is visible.   python3 fiducial_pose.py
"""
import numpy as np
np.set_printoptions(precision=4, suppress=True)

# ---- 1. the set-up -----------------------------------------------------------
K = np.array([[800.0,   0.0, 640.0],      # f_x, skew, principal point (pixels)
              [  0.0, 800.0, 360.0],      # f_y
              [  0.0,   0.0,   1.0]])
d = 0.10                                  # tag side, metres

def rotation(axis, deg):
    """Rotation matrix for an angle about a unit axis (Rodrigues' formula)."""
    k = np.asarray(axis, float); k /= np.linalg.norm(k)
    a = np.radians(deg)
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(a) * Kx + (1 - np.cos(a)) * Kx @ Kx

R_true = rotation([1.0, 0.6, 0.2], 35.0)  # tag tilted 35 degrees about a skew axis
o_true = np.array([0.10, -0.05, 0.80])    # tag centre 0.8 m in front, a little right and up

# the four corners in the tag's own frame: (+-d/2, +-d/2, 0), in the detector's order
corners_W = (d / 2) * np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]], float)

def project(K, R, o, X_W):
    """Pixel coordinates of world points X_W (rows), with the depth division done explicitly."""
    X_C = X_W @ R.T + o                   # r^C = R r^W + o, one row per point
    uvw = X_C @ K.T                       # K r^C: (f_x X + s Y + c_x Z,  f_y Y + c_y Z,  Z)
    lam = uvw[:, 2]                       # the third row is Z, the depth -- that is lambda
    return uvw[:, :2] / lam[:, None], lam

pix, lam = project(K, R_true, o_true, corners_W)

# ---- 2. the 8 x 9 system ----------------------------------------------------
def build_A(corners_W, pix):
    """Two rows per corner:  [q^T 0^T -x q^T ; 0^T q^T -y q^T] h = 0,  q = (x_W, y_W, 1)."""
    rows = []
    for (xw, yw, _), (x, y) in zip(corners_W, pix):
        q = np.array([xw, yw, 1.0])
        rows.append(np.concatenate([q, np.zeros(3), -x * q]))
        rows.append(np.concatenate([np.zeros(3), q, -y * q]))
    return np.array(rows)

# ---- 3. solve for H up to scale ---------------------------------------------
def solve_H(A):
    """The h that makes A h as small as possible with |h| = 1: the last right singular vector."""
    _, S, Vt = np.linalg.svd(A)
    return Vt[-1].reshape(3, 3), S

# ---- 4. from H to the pose ---------------------------------------------------
def pose_from_H(K, H):
    M = np.linalg.solve(K, H)             # K^{-1} H = c [r1 r2 o]
    c = (np.linalg.norm(M[:, 0]) + np.linalg.norm(M[:, 1])) / 2   # unit columns fix the scale
    M = M / c
    if M[2, 2] < 0:                       # the tag must be in front of the camera: o_z > 0
        M = -M
    r1, r2, o = M[:, 0], M[:, 1], M[:, 2]
    r3 = np.cross(r1, r2)                 # the column that z_W = 0 removed
    R_approx = np.column_stack([r1, r2, r3])
    U, _, Vt = np.linalg.svd(R_approx)    # nearest rotation (polar decomposition)
    R = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    return R, o, R_approx

def angle_between(R1, R2):
    """Angle, in degrees, of the rotation that takes R1 to R2."""
    cosang = (np.trace(R1.T @ R2) - 1) / 2
    return np.degrees(np.arccos(np.clip(cosang, -1, 1)))

# ---- 5. refine: make the corners reproject where they were seen --------------
def refine(K, R, o, corners_W, pix, iters=10):
    """Gauss-Newton on the reprojection error, starting from the closed-form pose.
    The six unknowns are a small rotation (vector w, applied as R <- R(w) R) and
    a shift of o. The Jacobian is taken by finite differences, so there is no
    hidden algebra: each column is 'how much do the eight pixel coordinates
    move when this one parameter moves a little'."""
    eps = 1e-6
    for _ in range(iters):
        res = (project(K, R, o, corners_W)[0] - pix).ravel()        # 8 residuals, pixels
        J = np.zeros((8, 6))
        for j in range(6):
            w, do = np.zeros(3), np.zeros(3)
            if j < 3: w[j] = eps
            else:     do[j - 3] = eps
            Rj = rotation(w, np.degrees(eps)) @ R if j < 3 else R
            res_j = (project(K, Rj, o + do, corners_W)[0] - pix).ravel()
            J[:, j] = (res_j - res) / eps
        step = np.linalg.lstsq(J, -res, rcond=None)[0]              # least-squares step
        if np.linalg.norm(step[:3]) > 0:
            R = rotation(step[:3], np.degrees(np.linalg.norm(step[:3]))) @ R
        o = o + step[3:]
    return R, o

# ---- 6. run it -----------------------------------------------------------------
def run(pix, label):
    print("==== %s ====" % label)
    A = build_A(corners_W, pix)
    H, S = solve_H(A)
    print("singular values of A:", S)
    R, o, R_approx = pose_from_H(K, H)
    print("recovered o^C_W   :", o, "   true:", o_true)
    print("recovered R^C_W   :\n", R)
    print("before snapping, R'^T R' =\n", R_approx.T @ R_approx)
    print("rotation error    : %.4f deg" % angle_between(R_true, R))
    print("position error    : %.2f mm" % (1000 * np.linalg.norm(o - o_true)))
    pix_hat, _ = project(K, R, o, corners_W)
    print("reprojection error: %.3f px (RMS)" % np.sqrt(np.mean((pix_hat - pix) ** 2)))
    R2, o2 = refine(K, R, o, corners_W, pix)
    pix_hat2, _ = project(K, R2, o2, corners_W)
    print("after refinement  : rotation error %.4f deg, position error %.2f mm, reprojection %.3f px"
          % (angle_between(R_true, R2), 1000 * np.linalg.norm(o2 - o_true),
             np.sqrt(np.mean((pix_hat2 - pix) ** 2))))
    print()

if __name__ == "__main__":
    print("pixel corners (x, y) and their depths lambda:")
    for p, l in zip(pix, lam):
        print("   (%8.2f, %8.2f)   lambda = %.4f m" % (p[0], p[1], l))
    print()

    run(pix, "exact corners")
    rng = np.random.default_rng(1)
    run(pix + rng.normal(0, 0.5, pix.shape), "corners with 0.5 px noise")

    # the same experiment repeated, to see what is typical rather than one draw
    e_closed, e_refined = [], []
    for _ in range(500):
        pn = pix + rng.normal(0, 0.5, pix.shape)
        H, _ = solve_H(build_A(corners_W, pn))
        R, o, _ = pose_from_H(K, H)
        e_closed.append(angle_between(R_true, R))
        e_refined.append(angle_between(R_true, refine(K, R, o, corners_W, pn)[0]))
    print("==== 500 repeats at 0.5 px noise: rotation error ====")
    print("closed form  : median %.2f deg,  90th percentile %.2f deg" % (np.median(e_closed), np.percentile(e_closed, 90)))
    print("refined      : median %.2f deg,  90th percentile %.2f deg" % (np.median(e_refined), np.percentile(e_refined, 90)))
