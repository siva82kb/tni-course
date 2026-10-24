#!/usr/bin/env python3
"""Generate the 'what limits tag tracking' data: CSV files, no plots.

The model is deliberately minimal. A tag36h11 of side d is placed at a known pose;
its four corners are projected through the pinhole camera of fiducial_pose.py;
Gaussian noise of SIGMA pixels is added to every corner coordinate, standing in
for everything a real detector gets wrong; and the pose is recovered with the
closed form plus refinement of fiducial_pose.py. Each setting is repeated
REPEATS times with fresh noise and the medians are written to

    ../../lectures/01-kinematics-kinetics/data/limit-distance.csv   pose error against distance
    ../../lectures/01-kinematics-kinetics/data/limit-headon.csv     pose error against tilt, near face-on

with columns: the swept variable; rot_err_deg, depth_err_mm (medians) with their
quartiles rot_q25, rot_q75, depth_q25, depth_q75; flip_frac (the fraction of runs
in which the tilt came back with the wrong sign); plus
limit-fits.tex with the constants of the fitted scaling laws, which the pgfplots
figures in lectures/01-kinematics-kinetics/tikz/limit-*.tex draw as dashed lines.

    python3 make_limit_data.py                 (a few seconds)
    python3 make_limit_data.py --fits-only     (refit from the CSVs, no re-run)
"""
import sys, pathlib, io, contextlib, importlib.util, csv
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parents[1] / "lectures" / "01-kinematics-kinetics" / "data"
spec = importlib.util.spec_from_file_location("fp", HERE / "fiducial_pose.py")
fp = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(fp)

K, d, CW = fp.K, fp.d, fp.corners_W          # f = 800 px, side d = 0.10 m, corners at (+-d/2, +-d/2)
F = float(K[0, 0])
SIGMA = 0.5                                  # corner noise, pixels, on every coordinate
REPEATS = 500

def pose(tilt_deg, z):
    """Tag facing the camera (R0 = diag(1,-1,-1)), tilted about the horizontal axis, centre on the optical axis at depth z."""
    R0 = np.diag([1.0, -1.0, -1.0])
    return fp.rotation([1, 0, 0], tilt_deg) @ R0, np.array([0.0, 0.0, z])

def measure(R, o, rng):
    """Project the corners, add the noise, recover the pose, compare with the truth."""
    truth, _ = fp.project(K, R, o, CW)
    pts = truth + rng.normal(0, SIGMA, truth.shape)
    Hh, _ = fp.solve_H(fp.build_A(CW, pts))
    R0, o0, _ = fp.pose_from_H(K, Hh)
    R1, o1 = fp.refine(K, R0, o0, CW, pts)
    return dict(rot=fp.angle_between(R, R1), dz=abs(o1[2] - o[2]) * 1000,
                flipped=float(np.sign(R1[2, 1]) != np.sign(R[2, 1])) if abs(R[2, 1]) > 1e-9 else 0.0)

def sweep(name, varname, values, make):
    rng = np.random.default_rng(7)
    DATA.mkdir(exist_ok=True)
    path = DATA / ("limit-%s.csv" % name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([varname, "rot_err_deg", "rot_q25", "rot_q75", "depth_err_mm", "depth_q25", "depth_q75", "flip_frac"])
        for v in values:
            R, o = make(v)
            rs = [measure(R, o, rng) for _ in range(REPEATS)]
            rot = np.percentile([r["rot"] for r in rs], [50, 25, 75])      # median and quartiles
            dz = np.percentile([r["dz"] for r in rs], [50, 25, 75])
            flip = np.mean([r["flipped"] for r in rs])
            w.writerow(["%g" % v] + ["%.4f" % x for x in rot] + ["%.4f" % x for x in dz] + ["%.4f" % flip])
            print("  %s = %-5s  rot %.3f [%.3f, %.3f] deg  dz %.2f [%.2f, %.2f] mm  flipped %.0f%%" %
                  ((varname, "%.3g" % v) + tuple(rot) + tuple(dz) + (100 * flip,)))
    print("wrote", path)

def fits():
    """Fit the scaling laws to the data and write the constants as TeX macros."""
    def load(k):
        rows = list(csv.DictReader(open(DATA / ("limit-%s.csv" % k))))
        return {c: np.array([float(r[c]) for r in rows]) for c in rows[0].keys()}
    t = load("distance"); z = t["z_m"]
    k_depth = np.exp(np.mean(np.log(t["depth_err_mm"]) - 2 * np.log(z)))     # depth error (mm) = k z^2, all points
    k_rot = np.exp(np.mean(np.log(t["rot_err_deg"]) - np.log(z)))            # orientation error (deg) = k z
    flip = t["z_m"][t["flip_frac"] > 0.1]
    lines = ["%% written by make_limit_data.py: constants of the fitted scaling laws (corner noise %.2f px)" % SIGMA,
             "\\def\\kDepth{%.5f}%% depth error (mm) = kDepth * z^2" % k_depth,
             "\\def\\kRot{%.5f}%% orientation error (deg) = kRot * z" % k_rot,
             "\\def\\zFlip{%s}%% first distance at which more than 10%% of runs flip the tilt sign (m)" % ("%.3g" % flip[0] if len(flip) else "nan"),
             "\\def\\sFlip{%s}%% the tag's size in pixels there" % ("%.0f" % (F * d / flip[0]) if len(flip) else "nan")]
    if (DATA / "limit-headon.csv").exists():
        t = load("headon"); ok = t["tilt_deg"] >= 8
        k_sin = np.exp(np.mean(np.log(t["rot_err_deg"][ok]) + np.log(np.sin(np.radians(t["tilt_deg"][ok])))))
        lines.append("\\def\\kSin{%.5f}%% orientation error (deg) = kSin / sin(theta), fitted for theta >= 8 deg" % k_sin)
    (DATA / "limit-fits.tex").write_text("\n".join(lines) + "\n")
    print("wrote", DATA / "limit-fits.tex")

if __name__ == "__main__":
    if "--fits-only" not in sys.argv:
        print("distance, tilt 30 deg, corner noise %.2f px" % SIGMA)
        sweep("distance", "z_m", [0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0], lambda z: pose(30, z))
        print("head-on, z = 0.8 m")
        sweep("headon", "tilt_deg", [0, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50], lambda t: pose(t, 0.8))
    fits()
