#!/usr/bin/env python3
"""What integrating an IMU does to its errors: data for the two drift figures.

A deliberately minimal model, in the spirit of the tag-limit plots. Each run
draws a residual bias (what is left after a quick static calibration) and white
noise with the stated densities, integrates once (gyro -> angle) or twice
(accelerometer -> position), and the median and quartiles of the absolute error
over 500 runs are written to CSV for tikz/imu-drift-gyro.tex and
tikz/imu-drift-accel.tex. The numbers are stated assumptions of the order found
in consumer MEMS parts, not a datasheet; swap in the lab IMU's figures when known.
    python3 make_imu_drift.py      (writes imu-drift-gyro.csv, imu-drift-accel.csv here)
"""
import csv, pathlib
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
FS = 100.0                      # sample rate, Hz
REPEATS = 500
rng = np.random.default_rng(3)

# gyro: residual bias ~ N(0, 0.05 deg/s), noise density 0.01 deg/s/sqrt(Hz), 60 s
GYRO_BIAS_SD = 0.05             # deg/s
GYRO_NOISE_DENSITY = 0.01       # deg/s per sqrt(Hz)
T_GYRO = 60.0

# accelerometer: residual bias ~ N(0, 10 mg), noise density 150 ug/sqrt(Hz), 10 s
G = 9.81
ACC_BIAS_SD = 0.010 * G         # m/s^2
ACC_NOISE_DENSITY = 150e-6 * G  # m/s^2 per sqrt(Hz)
T_ACC = 10.0

def integrate_runs(T, bias_sd, noise_density, order):
    n = int(T * FS)
    t = np.arange(1, n + 1) / FS
    sigma = noise_density * np.sqrt(FS)                  # per-sample standard deviation
    err = np.empty((REPEATS, n))
    for k in range(REPEATS):
        x = rng.normal(0, bias_sd) + rng.normal(0, sigma, n)   # the sensor's error signal
        for _ in range(order):
            x = np.cumsum(x) / FS                               # rectangle-rule integration
        err[k] = np.abs(x)
    return t, np.median(err, axis=0), np.percentile(err, 25, axis=0), np.percentile(err, 75, axis=0)

def write(name, t, med, q25, q75, step, unit_scale=1.0):
    with open(HERE / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "err_med", "err_q25", "err_q75"])
        for i in range(step - 1, len(t), step):
            w.writerow(["%.2f" % t[i]] + ["%.4f" % (v[i] * unit_scale) for v in (med, q25, q75)])
    print("wrote", name)

t, med, q25, q75 = integrate_runs(T_GYRO, GYRO_BIAS_SD, GYRO_NOISE_DENSITY, order=1)
write("imu-drift-gyro.csv", t, med, q25, q75, step=100)             # one row per second, degrees
print("gyro: median angle error %.2f deg at 10 s, %.2f deg at 60 s" % (med[int(10 * FS) - 1], med[-1]))

t, med, q25, q75 = integrate_runs(T_ACC, ACC_BIAS_SD, ACC_NOISE_DENSITY, order=2)
write("imu-drift-accel.csv", t, med, q25, q75, step=25)             # one row per 0.25 s, metres
print("accel: median position error %.3f m at 1 s, %.2f m at 10 s" % (med[int(1 * FS) - 1], med[-1]))
