#!/usr/bin/env python3
"""Build dlt-notes.html: camera calibration by the Direct Linear Transform, derived in full.

The worked example in the notes is dlt_calibration.py in this folder. It is run
when the notes are built and both its source and its output are pasted in, so
the numbers on the page are the numbers the code produced.
Re-run after editing either file:   python3 build-dlt-notes.py
"""
import html, re, pathlib, sys, subprocess, shutil
import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.resolve().parents[1] / "lectures"))
import notes_common as nc

DECK = "../../lectures/01-kinematics-kinetics/kinematics-kinetics.html"
THIS = "01-kinematics-kinetics/dlt-notes.html"
SCRIPT = HERE / "dlt_calibration.py"
CODE = SCRIPT.read_text()
OUT = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=True).stdout

def code(s, caption):
    return ('<figure class="code"><figcaption>%s</figcaption><pre><code>%s</code></pre></figure>'
            % (caption, html.escape(s)))

def excerpt(first, last):
    """Source lines of dlt_calibration.py from the one containing `first` to the one containing `last`."""
    a = CODE.index(first); a = CODE.rfind("\n", 0, a) + 1
    b = CODE.index(last, a); b = CODE.index("\n", b)
    return CODE[a:b]

HEAD = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Camera calibration by the Direct Linear Transform</title>
<script>
  window.MathJax = {
    tex: { inlineMath: [['\\(', '\\)']], displayMath: [['\\[', '\\]']],
           tags: 'ams',
           macros: { v: ['{\\mathbf{#1}}', 1], m: ['{\\begin{bmatrix}#1\\end{bmatrix}}', 1],
                     R: '{\\mathbf{R}}', T: '{\\top}', P: '{\\mathbf{\\Pi}}',
                     kt: ['{\\tilde{\\mathbf{k}}_{#1}^{\\top}}', 1],
                     pr: ['{\\tilde{\\mathbf{p}}_{#1}^{\\top}}', 1],
                     mr: ['{\\tilde{\\mathbf{m}}_{#1}^{\\top}}', 1] } },
    svg: { fontCache: 'global' },
    startup: { typeset: false }
  };
</script>
<script id="MathJax-script" defer src="../../lectures/01-kinematics-kinetics/interactive/vendor/tex-svg.js"></script>
<style>@@STYLE@@</style>
</head>
<body>
@@BANNER@@<div class="wrap">
<nav>
  <div class="t">Contents</div>
  <ol>
@@TOC@@
  </ol>
</nav>
<main>
<header>
  <h1>Camera calibration by the Direct Linear Transform</h1>
  <p class="sub">From the pixel positions of measured points to the eleven numbers of a camera, every step written out</p>
  <div class="meta">Transducers &amp; Instrumentation &middot; Module 2, Kinematics and Kinetics &middot; companion notes to the slides on camera calibration. The worked example is <code>dlt_calibration.py</code>, run when this page is built; the code and its output appear in §8 exactly as they are.</div>
</header>
"""

FOOT = r"""
@@PREVNEXT@@</main>
</div>
@@FOOTER@@<script>
  (function () {
    function run() {
      var main = document.querySelector("main"), chunks = [], cur = [];
      Array.prototype.forEach.call(main.childNodes, function (n) {
        if (n.nodeType === 1 && n.tagName === "H2") { if (cur.length) chunks.push(cur); cur = []; }
        cur.push(n);
      });
      if (cur.length) chunks.push(cur);
      var groups = chunks.map(function (ch) {
        var d = document.createElement("div"); main.insertBefore(d, ch[0]);
        ch.forEach(function (n) { d.appendChild(n); }); return d;
      });
      groups.unshift(document.querySelector("header"));
      var i = 0;
      (function next() {
        if (i >= groups.length) return;
        MathJax.typesetPromise([groups[i++]]).then(next, next);
      })();
    }
    var s = document.getElementById("MathJax-script");
    function ready() { if (window.MathJax && MathJax.startup) MathJax.startup.promise.then(run); }
    s.addEventListener("load", ready); ready();
  })();
</script>
</body>
</html>
"""

TOC = [("problem", "The problem"), ("camera", "The camera model, with the scale written out"),
       ("point", "What one point gives"), ("system", "Many points: the system and its solution"),
       ("apart", "Taking Π apart: K, R and o"), ("noise", "What noise does"),
       ("refine", "Refining the fit"), ("example", "The worked example"),
       ("lessons", "What this says about calibrating a camera"), ("refs", "Sources and further reading"),
       ("appA", "Appendix A: why the split is unique")]
APP = {"appA": "A"}

def build():
    def tocnum(i, a):
        if a in APP: return APP[a]
        return str(i + 1 - sum(1 for k, (b, _) in enumerate(TOC) if k < i and b in APP))
    toc_html = "\n".join('    <li><a href="#%s">%s&ensp;%s</a></li>' % (a, tocnum(i, a), b) for i, (a, b) in enumerate(TOC))
    s = (HEAD.replace("@@STYLE@@", nc.CSS).replace("@@TOC@@", toc_html)
             .replace("@@BANNER@@", nc.banner([("Module 2: Kinematics and kinetics", DECK), ("Notes: camera calibration", "")],
                                               nav=nc.topnav(THIS))))
    H2 = lambda n, a, t: '<h2 id="%s"><span class="n">%s</span>%s</h2>\n' % (a, n, t)

    # ------------------------------------------------------------ 1 problem
    s += H2(1, "problem", "The problem")
    s += r"""
<p class="lead">A rigid object carrying points whose positions have been measured, a calibration jig, is placed in front of a camera. Someone finds each point in the photograph and records its pixel position. From the measured positions and the pixel positions, find the camera: its focal length, principal point and pixel geometry, and where it stands relative to the jig.</p>
<figure class="fig"><img src="dlt-jig.svg" alt="A calibration jig and its image">
<figcaption><b>The jig and its image.</b> Left: an L of two perpendicular faces with points every 0.15 m, nine on the floor and six on the wall, with the jig's own frame \(W\) at the inner corner. Right: the fifteen points as the camera of the worked example sees them, 1.5 m away and turned 30°. The map \(\P\) between the two is what these notes find, and then take apart.</figcaption></figure>
<p>Two frames are involved, with the deck's convention that a superscript names the frame a vector is expressed in:</p>
<table>
<tr><th>frame</th><th>what it is</th><th>vectors in it</th></tr>
<tr><td>\(W\)</td><td>the jig's own frame, the "world": origin at the inner corner, axes along the edges of the two faces.</td><td>\(\v{r}_{P}^{W}\), the points, known from measuring the jig</td></tr>
<tr><td>\(C\)</td><td>the camera frame: origin at the pinhole, \(z_C\) along the optical axis, out through the lens.</td><td>\(\v{r}_{P}^{C}\), unknown</td></tr>
<tr><td>\(S\)</td><td>the sensor frame, in pixels.</td><td>\(\v{r}_{p}^{S}\), the points found in the image, measured</td></tr>
</table>
<div class="cols">
<div>
<h3>Unknowns</h3>
<ul>
<li>\(\v{K}_f\), the intrinsic matrix: \(f_x, f_y, s, o_{xs}, o_{ys}\), 5 numbers.</li>
<li>\(\R_W^C\), the orientation of the jig frame in the camera frame: 3 numbers.</li>
<li>\(\v{o}_W^C\), the position of the jig's origin in the camera frame: 3 numbers.</li>
</ul>
<p>Eleven in all: 5 intrinsic, 6 extrinsic.</p>
</div>
<div>
<h3>Knowns</h3>
<ul>
<li>\(\v{r}_{P,i}^{W}\), the positions of \(n\) points on the jig, from measuring it: \(3n\) numbers.</li>
<li>\(\v{r}_{p,i}^{S}\), the pixel positions of the same \(n\) points, in the same order: \(2n\) numbers.</li>
</ul>
<p>Nothing about the camera is assumed. In particular the pixels are not assumed square, nor the skew zero; the method finds out.</p>
</div>
</div>
<p>The correspondence, which jig point is which image point, is taken as given. On a real jig the points are numbered or coloured so that a person or a program can match them; with fewer than a dozen it is often done by hand.</p>
<div class="note"><b>Why this is worth deriving.</b> The slides say the method returns \(\P\), "from which the intrinsics and extrinsics can be separated". That sentence hides most of the method: how a photograph of known points turns into a linear system, why that system has a unique answer only for a jig that is not flat, how a \(3\times4\) matrix is split into a triangular factor and a rotation, and what the noise in the pixel positions does to each of the eleven numbers. The worked example also shows something the slides do not: which pairs of camera parameters the data cannot tell apart, and what that implies for how a jig should be built.</div>
"""

    # ------------------------------------------------------------- 2 camera
    s += H2(2, "camera", "The camera model, with the scale written out")
    s += r"""
<p>Take one point \(P\) at \(\v{r}_P^{W}\) on the jig. Its position in the camera frame is the rigid transformation</p>
\[\v{r}_P^{C} = \R_W^C\,\v{r}_P^{W} + \v{o}_W^C, \qquad \v{r}_P^{C} = \m{x_P^C \\ y_P^C \\ z_P^C}, \tag{2.1}\]
<p>and the pinhole puts it on the sensor at</p>
\[x_p^S = f_x\,\frac{x_P^C}{z_P^C} + s\,\frac{y_P^C}{z_P^C} + o_{xs}, \qquad y_p^S = f_y\,\frac{y_P^C}{z_P^C} + o_{ys}. \tag{2.2}\]
<p>This is the content of the pinhole slides: similar triangles give \(x^I = f\,x^C/z^C\), and the pixel conversion adds the scale factors and the offset to the principal point. Hold on to the division by \(z_P^C\). A point twice as far away lands half as far from the principal point; that division is where all the depth information lives, and it is what makes (2.2) nonlinear in the unknowns.</p>
<p>The slides package (2.2) by multiplying through by \(z_P^C\). Give the multiplier a name, because it is different for every point and has to be eliminated by hand:</p>
\[\lambda\,\v{r}_p^{S} = \v{K}_f\,\v{r}_P^{C}, \qquad \lambda = z_P^C, \qquad \v{r}_p^{S} = \m{x_p^S \\ y_p^S \\ 1}, \qquad \v{K}_f = \m{f_x & s & o_{xs} \\ 0 & f_y & o_{ys} \\ 0 & 0 & 1}. \tag{2.3}\]
<p>The third row of (2.3) reads \(\lambda\cdot1 = z_P^C\), which is where \(\lambda\) gets its meaning: the last row of \(\v{K}_f\) being \((0, 0, 1)\) makes the third component of \(\v{K}_f\v{r}_P^C\) the depth. Now put (2.1) in, writing \(\v{r}_P^W\) with a fourth coordinate equal to 1 so that the shift \(\v{o}_W^C\) rides along in the matrix product:</p>
\[\boxed{\ \lambda\,\v{r}_p^{S} = \underbrace{\v{K}_f\m{\R_W^C & \v{o}_W^C}}_{\P}\ \m{x_P^W \\ y_P^W \\ z_P^W \\ 1}\ } \tag{2.4}\]
<p>\(\P\) is \(3\times4\), twelve entries, and it is the whole camera: every unknown in the problem is inside it, and nothing else is. Writing its rows as \(\pr{1}, \pr{2}, \pr{3}\) and \(\v{X} = (x_P^W, y_P^W, z_P^W, 1)^\T\), the two pixel coordinates are ratios:</p>
\[x_p^S = \frac{\pr{1}\v{X}}{\pr{3}\v{X}}, \qquad y_p^S = \frac{\pr{2}\v{X}}{\pr{3}\v{X}}, \qquad \lambda = \pr{3}\v{X}. \tag{2.5}\]
<p>Two things about \(\P\) are worth noticing now, because the method is built on them.</p>
<ul>
<li><b>Its scale means nothing.</b> Multiply \(\P\) by any nonzero \(c\) and every \(\lambda\) absorbs it: the same pixels come out of (2.5). So the pixels can determine \(\P\) only up to a factor, and \(\P\) has \(12 - 1 = 11\) meaningful numbers. That is the count on the slides, met from the other side: 5 intrinsic plus 6 extrinsic equals the 11 degrees of freedom of a \(3\times4\) matrix taken up to scale. There is no slack, and that is what makes the split of §5 unique.</li>
<li><b>Its last row is \(c\) times the third row of the rotation.</b> Since the bottom row of \(\v{K}_f\) is \((0, 0, 1)\), the bottom row of \(\v{K}_f\R\) is the bottom row of \(\R\), a unit vector. So the length of the first three entries of \(\pr{3}\) is the unknown factor \(c\). §5 starts from this.</li>
</ul>
"""

    # ------------------------------------------------------------- 3 point
    s += H2(3, "point", "What one point gives")
    s += r"""
<p>For point \(i\), with \((x_i, y_i)\) short for its measured pixel position and \(\v{X}_i\) its known jig position with the 1 appended, (2.5) says</p>
\[x_i\,(\pr{3}\v{X}_i) = \pr{1}\v{X}_i, \qquad y_i\,(\pr{3}\v{X}_i) = \pr{2}\v{X}_i. \tag{3.1}\]
<p>Two equations, and the depth is gone: it was \(\pr{3}\v{X}_i\), and multiplying through has put it on the left as a product of known numbers and unknown ones. Each equation is a measured pixel coordinate times a row of \(\P\) on one side and a row of \(\P\) on the other: linear in the twelve entries of \(\P\). To make that visible, stack the rows of \(\P\) into one vector of twelve unknowns,</p>
\[\v{p} = \m{\tilde{\v{p}}_1 \\ \tilde{\v{p}}_2 \\ \tilde{\v{p}}_3} \in \mathbb{R}^{12}, \tag{3.2}\]
<p>and move everything in (3.1) to one side:</p>
\[\m{\v{X}_i^\T & \v{0}^\T & -x_i\,\v{X}_i^\T \\ \v{0}^\T & \v{X}_i^\T & -y_i\,\v{X}_i^\T}\v{p} = \v{0}. \tag{3.3}\]
<p>This \(2\times12\) block is one point's contribution. Its entries are the point's jig coordinates and its pixel coordinates, all measured. Written out, the first row is</p>
\[x_i^W p_{11} + y_i^W p_{12} + z_i^W p_{13} + p_{14} - x_i\,x_i^W p_{31} - x_i\,y_i^W p_{32} - x_i\,z_i^W p_{33} - x_i\,p_{34} = 0. \tag{3.4}\]
<div class="note warn"><b>The slip to avoid.</b> It is tempting to write a point's equations as \(x_i = \pr{1}\v{X}_i\) and \(y_i = \pr{2}\v{X}_i\): eight unknowns, linear, and wrong. Those are the numerators of (2.5) with the denominators left off, and they describe a camera that does not divide by depth, which draws parallel lines as parallel at any distance. The real camera draws the jig's far edge shorter than its near one, and that is the only information about depth the image has. The factor \(\pr{3}\v{X}_i\) in (3.1) is what keeps it.</div>
<p>"Each point gives two equations", as the slide says: one for its row in the image, one for its column.</p>
"""

    # ------------------------------------------------------------ 4 system
    s += H2(4, "system", "Many points: the system and its solution")
    s += r"""
<p>Stack the blocks (3.3) for all \(n\) points:</p>
\[\v{A}\,\v{p} = \v{0}, \qquad \v{A} = \m{\v{X}_1^\T & \v{0}^\T & -x_1\,\v{X}_1^\T \\ \v{0}^\T & \v{X}_1^\T & -y_1\,\v{X}_1^\T \\ & \vdots & \\ \v{X}_n^\T & \v{0}^\T & -x_n\,\v{X}_n^\T \\ \v{0}^\T & \v{X}_n^\T & -y_n\,\v{X}_n^\T} \in \mathbb{R}^{2n\times12}. \tag{4.1}\]
<p>\(2n\) equations, twelve unknowns, right-hand side zero. The scale of \(\v{p}\) is free, as it must be from §2: if \(\v{p}\) solves (4.1) so does \(c\,\v{p}\). What is being determined is a direction in \(\mathbb{R}^{12}\), which has eleven degrees of freedom, and so eleven independent equations are needed.</p>
<h3>Six points</h3>
<p>Six points give twelve equations, one more than needed. For points in general position \(\v{A}\) has rank 11 and its null space is one line: \(\v{p}\) is unique up to scale, and twelve equations for eleven unknowns means the null vector fits every pixel exactly, noise or no noise. The slide's "at least 6 points" is this count. Five points give ten equations and a two-dimensional null space: a whole family of cameras could have taken the picture.</p>
<h3>More points</h3>
<p>With \(n &gt; 6\) and noisy pixels there is no \(\v{p}\) with \(\v{A}\v{p} = \v{0}\) exactly, and the question becomes</p>
\[\min_{\v{p}}\ \Vert\v{A}\v{p}\Vert^2 \quad\text{subject to}\quad \Vert\v{p}\Vert = 1, \tag{4.2}\]
<p>whose answer is the right singular vector of \(\v{A}\) for its smallest singular value: with \(\v{A} = \v{U}\mathbf{\Sigma}\v{V}^\T\) and \(\v{p} = \v{V}\v{a}\), \(\Vert\v{A}\v{p}\Vert^2 = \sum_j\sigma_j^2a_j^2\), smallest when all of the unit vector \(\v{a}\) sits on the smallest \(\sigma_j\). For six exact points the smallest singular value is zero and (4.2) returns the exact null vector, so one recipe, "take the last right singular vector of \(\v{A}\)", covers every case. That is what the code in §8 does.</p>
<h3>The jig must not be flat</h3>
<p>Suppose every point has \(z_i^W = 0\). Then in every row of \(\v{A}\) the entries multiplying \(p_{13}\), \(p_{23}\) and \(p_{33}\) are zero: three columns of \(\v{A}\) vanish, its rank is at most 9, and its null space has dimension at least 3. In fact it is exactly 4: the three entries of \(\P\)'s third column, which the data never touch, plus the one direction that is always free. The floor-only run in §8 shows the four zero singular values. The reason is the one the fiducial notes use in the other direction: for coplanar points (2.4) collapses to \(\lambda\v{r}_p^S = \v{K}_f\m{\v{r}_1 & \v{r}_2 & \v{o}}\v{q}\), a \(3\times3\) matrix with 8 degrees of freedom, and 8 is less than 11. A flat target fixes the homography; it cannot fix the camera.</p>
<p>A jig that is almost flat is almost as bad. Three singular values that are small rather than zero mean three directions in \(\v{p}\) that the data barely constrain, and noise fills them. This is the first half of the slide's "non-coplanar points that fill the capture volume": the depth of the jig must be a good fraction of its distance from the camera. §6 says why, and the example measures it.</p>
<div class="note"><b>Two remarks on the solve.</b> (i) \(\pr{3}\v{X}_i\) is the depth of point \(i\), never zero for a visible point, so one may set \(p_{34} = 1\) and solve an ordinary least-squares problem in eleven unknowns instead of (4.2). The singular-vector route is standard because it treats all twelve entries alike. (ii) \(\v{A}\) mixes jig coordinates in metres with pixels in the hundreds, so its singular values span five orders of magnitude; the example prints them. The usual remedy is to rescale both sets of coordinates to order one before building \(\v{A}\) and undo the scaling afterwards. The example does not, and at double precision it does not matter for fifteen points.</div>
"""

    # ------------------------------------------------------------- 5 apart
    s += H2(5, "apart", "Taking Π apart: K, R and o")
    s += r"""
<p>We have \(\P\) up to a factor \(c\), and we know from (2.4) what it is made of:</p>
\[\P = c\,\v{K}_f\m{\R & \v{o}} = \m{\v{M} & \v{p}_4}, \qquad \v{M} = c\,\v{K}_f\R \ \ (3\times3), \qquad \v{p}_4 = c\,\v{K}_f\v{o}. \tag{5.1}\]
<p>The task is to split \(\v{M}\) into an upper-triangular matrix and a rotation. Write \(\v{M}\) by its rows, \(\mr{1}, \mr{2}, \mr{3}\), and \(\R\) by its rows \(\v{r}_1^\T, \v{r}_2^\T, \v{r}_3^\T\), which are orthonormal. Then, row by row, \(\v{M} = c\,\v{K}_f\R\) says</p>
\[\mr{3} = c\,\v{r}_3^\T, \qquad \mr{2} = c\,(f_y\,\v{r}_2^\T + o_{ys}\,\v{r}_3^\T), \qquad \mr{1} = c\,(f_x\,\v{r}_1^\T + s\,\v{r}_2^\T + o_{xs}\,\v{r}_3^\T). \tag{5.2}\]
<p>The bottom row involves only \(\v{r}_3\); the middle row brings in \(\v{r}_2\); the top row brings in \(\v{r}_1\). So work from the bottom up, peeling off one row of \(\R\) at a time with the orthonormality doing the work. Five steps.</p>
<ol class="steps">
<li><b>The sign.</b> From (2.5), \(\pr{3}\v{X}_i = c\,z_i^C\): the third row of \(\P\) applied to any jig point is \(c\) times that point's depth. Every point is in front of the camera, so if \(\pr{3}\v{X}_i\) comes out negative, \(c\) is negative, and the fix is to replace \(\P\) by \(-\P\). After this \(c &gt; 0\).</li>
<li><b>The scale.</b> \(\Vert\v{r}_3\Vert = 1\), so from the first of (5.2)
\[c = \Vert\tilde{\v{m}}_3\Vert, \qquad \v{r}_3 = \tilde{\v{m}}_3 / c. \tag{5.3}\]
Divide all of \(\P\) by \(c\). From here on \(\v{M} = \v{K}_f\R\) and \(\v{p}_4 = \v{K}_f\v{o}\) with no factor.</li>
<li><b>The middle row.</b> \(\tilde{\v{m}}_2 = f_y\,\v{r}_2 + o_{ys}\,\v{r}_3\), and \(\v{r}_2\perp\v{r}_3\). Dot with \(\v{r}_3\) to isolate \(o_{ys}\); what is left is \(f_y\v{r}_2\), whose length is \(f_y\) because \(\v{r}_2\) is a unit vector:
\[o_{ys} = \tilde{\v{m}}_2\cdot\v{r}_3, \qquad \v{v} = \tilde{\v{m}}_2 - o_{ys}\,\v{r}_3, \qquad f_y = \Vert\v{v}\Vert, \qquad \v{r}_2 = \v{v}/f_y. \tag{5.4}\]</li>
<li><b>The top row.</b> \(\tilde{\v{m}}_1 = f_x\,\v{r}_1 + s\,\v{r}_2 + o_{xs}\,\v{r}_3\), with \(\v{r}_1\) perpendicular to both of the rows already found. Dot with \(\v{r}_3\) and with \(\v{r}_2\), then take the length of what remains:
\[o_{xs} = \tilde{\v{m}}_1\cdot\v{r}_3, \qquad s = \tilde{\v{m}}_1\cdot\v{r}_2, \qquad \v{u} = \tilde{\v{m}}_1 - o_{xs}\,\v{r}_3 - s\,\v{r}_2, \qquad f_x = \Vert\v{u}\Vert, \qquad \v{r}_1 = \v{u}/f_x. \tag{5.5}\]</li>
<li><b>The position.</b> With \(\v{K}_f\) assembled from (5.4) and (5.5), the last column gives
\[\v{o}_W^C = \v{K}_f^{-1}\,\v{p}_4, \tag{5.6}\]
a triangular solve.</li>
</ol>
<p>This is Gram–Schmidt orthogonalisation run on the rows of \(\v{M}\) from the bottom up, and the coefficients it discards along the way are exactly the entries of \(\v{K}_f\). Counting what came out: \(c\) (1), \(f_x, f_y, s, o_{xs}, o_{ys}\) (5), the rotation (3), the position (3), twelve numbers from the twelve entries of \(\P\), with the one that means nothing, \(c\), set aside. Nothing was left over and nothing was short. That is the 5 + 6 = 11 of the slides doing its work.</p>
<p>Two conventions were made along the way: \(f_x\) and \(f_y\) were taken positive, as the lengths in (5.4) and (5.5), and the rows of \(\R\) came out orthonormal by construction. For a real camera and a right-handed jig frame this gives \(\det\R = +1\). If it came out \(-1\) the picture would be a mirror image of what the model can produce, which means the pixel axes or the jig axes were labelled with the wrong handedness. Appendix A shows that with these conventions the split is the only one possible: an upper-triangular matrix with positive diagonal times a rotation can be written that way in just one way.</p>
<div class="note"><b>Against the fiducial notes.</b> The pose-from-a-tag problem ends with a snap to the nearest rotation, because its \(\v{K}_f^{-1}\v{H}\) has to be forced into the shape \(c\m{\v{r}_1 & \v{r}_2 & \v{o}}\) and noise has spoilt that shape. Here nothing is forced. Any invertible \(\v{M}\) splits as triangular times orthogonal, exactly, so the \(\R\) that comes out is always a true rotation and \(\v{K}_f\R\) reproduces \(\v{M}\) to machine precision. The noise has not been removed; it has gone somewhere else, and §6 says where.</div>
"""

    # ------------------------------------------------------------- 6 noise
    s += H2(6, "noise", "What noise does")
    s += r"""
<p>Pixel positions are found to a fraction of a pixel at best, and the jig itself was measured with a tape or a machine of finite accuracy. Both enter \(\v{A}\), and through (4.2) they move \(\v{p}\). What does a moved \(\v{p}\) look like after §5?</p>
<h3>All eleven numbers move, and the rotation hides it</h3>
<p>The split of §5 is exact for any \(\v{M}\), so it never complains. \(\R\) comes out a perfect rotation whether or not it is the right one; its error is invisible from the inside, and in practice it shows up only as a mismatch when the camera is later used. \(\v{K}_f\) is where the symptoms appear, because \(\v{K}_f\) has structure we know about and \(\R\) does not: on a modern sensor the skew is zero and the pixels are square, so a skew of a few pixels or an \(f_x\) that differs from \(f_y\) is a direct reading of how much noise went into the fit. The noisy run in §8 gets \(s = 2.7\) px and \(f_x - f_y = 0.2\) px from half a pixel of noise; both should be zero. They are the visible part of an error that is also in the principal point, the focal length, the rotation and the position, where there is no "should be" to compare against.</p>
<h3>Errors come in pairs</h3>
<p>The eleven numbers are not disturbed independently. Some pairs change the picture in nearly the same way, so the data cannot tell them apart, and noise moves them together. Two pairs matter most, and both can be read off (2.2).</p>
<ul>
<li><b>Focal length and distance.</b> For a point at depth \(z\), \(x_p^S - o_{xs} = f_x\,x^C/z\). Increase \(f_x\) by a factor \((1+\epsilon)\) and push the jig back so that every depth grows by the same factor: the ratio is unchanged and so is every pixel. The only thing that breaks the tie is that the jig's points are not all at the same depth, so pushing it back scales the near and far depths by different amounts relative to their spread. A jig whose depth range is a small fraction of its distance leaves this pair almost free, and the pixel noise then drives \(f_x\) and \(o_z\) together: in the 500 repeats of §8 the correlation of their errors is \(+1.00\), the focal length is off by \(18\) px, about \(2.2\%\), and the jig's recovered distance is off by the same \(2.2\%\) of 1.5 m, \(33\) mm. Making the jig three times larger, so that its depth spans 1.4 to 2.3 m, cuts the focal-length error to \(2.4\) px, more than the factor of three that the larger image alone would give. This is the second half of the slide's "fill the capture volume": the jig must have depth, and its depth is what fixes \(f\).</li>
<li><b>Principal point and rotation.</b> Turn the camera by a small angle \(\alpha\) about its \(y_C\) axis and every image point moves sideways by about \(f\alpha\) pixels, the same for all points near the optical axis. Shift the principal point by \(f\alpha\) and the same thing happens. The two differ only in the second order, by the perspective terms that grow with the field of view, so for a jig that covers a small part of the image the data cannot separate them; in the example the correlation between the error in \(o_{xs}\) and the rotation error about \(y_C\) is \(-0.98\). A principal point that is "off by 13 px" is, as far as the fit is concerned, a camera that is turned by \(13/800\) rad, about a degree, and the two cancel when the camera is used on the same jig. They do not cancel on another object.</li>
</ul>
<p>Both pairs have the same remedy, and it is the slide's: the jig must be large in the image and deep along the optical axis. A small jig in the middle of the frame constrains the ratios that matter, and the pairs above are left to the noise.</p>
<h3>Algebraic error is not pixel error</h3>
<p>What (4.2) minimises is not the quantity one cares about. Each row of \(\v{A}\v{p}\) is a pixel equation (3.1) multiplied through by the depth \(\pr{3}\v{X}_i\), so a point twice as far away counts twice as much in \(\Vert\v{A}\v{p}\Vert\), and points near the camera are under-weighted. The quantity one cares about is the distance in pixels between where a point was seen and where the fitted camera puts it, the <em class="term">reprojection error</em>, and (4.2) looks at it only through this depth-dependent weighting. For a jig whose depths differ by twenty per cent, as in the example, the two are nearly proportional and the distinction is academic. For a scene with points from half a metre to five metres it is not, and §7 is the remedy.</p>
"""

    # ------------------------------------------------------------ 7 refine
    s += H2(7, "refine", "Refining the fit")
    s += r"""
<p>Write the error that matters and minimise it directly, starting from the answer of §5:</p>
\[E(\v{K}_f, \R, \v{o}) = \sum_{i=1}^{n}\left\Vert\mathbf{\pi}\!\left(\v{K}_f,\ \R\,\v{r}_i^{W} + \v{o}\right) - \m{x_i \\ y_i}\right\Vert^2, \tag{7.1}\]
<p>where \(\mathbf{\pi}\) is the pinhole map (2.2), depth division included. Gauss–Newton does it: linearise the \(2n\) residuals in the parameters, solve the small least-squares problem for a step, apply it, repeat. The rotation is handled as a small rotation vector applied on the left of the current estimate, so it stays a rotation without any snapping. The example takes the Jacobian by finite differences, one parameter at a time, so that the code shows nothing but "nudge a parameter, see how the pixels move".</p>
<p>Two versions are run. One keeps all eleven parameters. The other imposes what we know about the sensor, square pixels and zero skew, leaving nine: \(f\), the principal point, and the pose. The example's result is sobering: neither version changes the answer by much. The reprojection error is already at the noise level after §5, the eleven-parameter refinement leaves the numbers essentially where they were, and imposing the structure moves \(f\) from \(18.0\) to \(18.4\) px of error, which is no improvement at all.</p>
<p>Both results follow from §6. The closed form threw nothing away, so there is little for a reprojection fit to recover, unlike the tag problem where the snap to a rotation discarded the fit and refinement won a factor of five. And the error in \(f\) is not in the spare degrees of freedom \(s\) and \(f_x - f_y\), which are small; it is in the focal-length-against-depth pair, which square pixels say nothing about. The slide's third "issue", that the free parameters absorb noise, is true of the symptoms and not of the disease. What the refinement framework does buy is the ability to add to (7.1) what the linear method cannot hold: the distortion terms of the lens, which the slides list as the method's second issue, and the data of many photographs at once. That is the shape of every calibration tool in use, and the method of these notes is how it finds its starting point.</p>
"""

    # ----------------------------------------------------------- 8 example
    s += H2(8, "example", "The worked example")
    s += r"""
<p>A camera with focal length 800 px, square pixels, no skew and principal point \((640, 360)\): the camera of the fiducial notes. The jig of §1, 0.3 m across, placed 1.5 m in front of the camera and turned 30° so that both faces are seen. The script projects the fifteen points with (2.1) and (2.2), forgets the camera and recovers it by §4 and §5, refines by §7, then repeats everything with half a pixel of noise on every pixel coordinate, tries the nine floor points alone, and runs the noisy calibration 500 times for two sizes of jig.</p>
"""
    s += code(excerpt("import numpy as np", "pix, lam = project(K_true, R_true, o_true, X_W)"), "<b>dlt_calibration.py</b> — the set-up: camera, jig, true pose, and the projection with the depth division written out (§2)")
    s += code(excerpt("def build_A(X_W, pix):", "    return Vt[-1].reshape(3, 4), S"), "<b>dlt_calibration.py</b> — the \\(2n\\times12\\) system (4.1) and its solution (4.2), the last right singular vector")
    s += code(excerpt("def decompose(P, X_W):", "    return K, R, o"), "<b>dlt_calibration.py</b> — taking \\(\\P\\) apart: the five steps of §5")
    s += code(excerpt("def refine(K, R, o, X_W, pix, iters=10, square=False):", "    return unpack(k), R, o"), "<b>dlt_calibration.py</b> — Gauss–Newton on the reprojection error (7.1), with or without square pixels")
    s += code(excerpt("def run(pix, label):", "focal length f_x  and  depth of the jig o_z, closed form"), "<b>dlt_calibration.py</b> — running it: exact pixels, one noisy draw, the flat jig, and 500 repeats for two sizes of jig")
    s += code(OUT, "<b>Output</b> of <code>python3 dlt_calibration.py</code>, as produced when this page was built")
    s += r"""
<p>Reading the output against the derivation, with the labels used above:</p>
<ul>
<li><b>The set-up.</b> Fifteen points, depths from 1.46 to 1.76 m, filling about 200 by 170 px of a 1280 by 720 image: a small jig in the middle of the frame, which is how calibration jigs are usually photographed and, §6 says, why they should not be.</li>
<li><b>Exact pixels.</b> \(\v{A}\) has eleven nonzero singular values and a twelfth that is zero: the null vector of §4 exists and is unique. §5 returns the camera to machine precision, \(\R^\T\R - \v{I}\) is at \(10^{-16}\), and the refinement has nothing to do.</li>
<li><b>Half a pixel of noise.</b> The smallest singular value is now \(0.002\), not zero: fifteen points over-determine \(\v{p}\) and the fit is a compromise, with a reprojection error of \(0.35\) px, below the \(0.5\) px of the noise as a least-squares fit must be. The recovered \(\v{K}_f\) has a skew of \(2.7\) px and \(f_x \ne f_y\), the symptoms of §6; \(\R\) is still a rotation to \(10^{-16}\), the hidden error. The focal length is \(9\) px high and the jig has moved \(22\) mm back: the pair of §6, in one draw. Refinement changes almost nothing; square pixels change almost nothing.</li>
<li><b>The floor alone.</b> Four zero singular values, as §4 predicted: three for the columns of \(\v{A}\) that \(z^W = 0\) wiped out and one that is always there. The script does not try to decompose this \(\P\), because there is no single \(\P\) to decompose.</li>
<li><b>Five hundred repeats.</b> A typical draw has \(f\) off by \(18\) px, the principal point by \(13\) px, the orientation by \(1.5^\circ\) and the position by \(6\) cm. Their errors move in lockstep, \(f\) with depth at \(+1.00\) and principal point with rotation at \(-0.98\). The same jig three times larger, 0.9 m across and reaching from 1.4 to 2.3 m, brings \(f\) to within \(2.4\) px and the orientation to \(0.2^\circ\), and loosens the \(f\)–depth tie to \(+0.96\). Half a pixel of noise did not change; the jig did.</li>
</ul>
"""

    # ----------------------------------------------------------- 9 lessons
    s += H2(9, "lessons", "What this says about calibrating a camera")
    s += r"""
<p>The slide lists three issues with the method and a later slide lists five things to check. Both lists are in the algebra above.</p>
<ul>
<li><b>Fill the volume.</b> §6 and the 500 repeats of §8. The focal length is fixed by how differently near and far points are scaled, and the principal point by how differently points on either side of the axis move under rotation. A jig that is small in the image or shallow in depth gives the fit almost nothing to hold these with, and half a pixel of noise becomes a two per cent error in \(f\). The remedy is not a better solver; it is a bigger, deeper jig, or many photographs of a smaller one at different places and depths.</li>
<li><b>Not flat.</b> §4. A planar jig leaves three directions in \(\v{p}\) unconstrained. A nearly planar one leaves them nearly so, and the near-zero singular values are a diagnostic worth printing.</li>
<li><b>Distortion is not in the model.</b> Nothing in (2.2) bends a straight line, so a lens that does will bias every one of the eleven numbers, most of all when the jig reaches the edges of the frame where distortion is largest. This is the slide's second issue, and it is why the linear method is a starting point for a refinement that includes distortion rather than an end in itself.</li>
<li><b>The symptoms and the disease.</b> §6 and §7. Non-zero skew and unequal focal lengths are how noise announces itself, and it is reasonable to check them. Forcing them to their known values does not remove the error that produced them, which lives in the pairs of §6.</li>
<li><b>A small residual is necessary, not sufficient.</b> In the noisy run of §8 the fit reproduces the noisy pixels to \(0.35\) px while the focal length is \(9\) px wrong and the jig \(22\) mm out of place. The reprojection error measures the fit to these points; it does not measure the camera. The slide's lesson from Module 1 is this example in one line.</li>
</ul>
<p>A count that follows from §4 points at how the slides' other method gets by without a jig. One photograph of a flat target fixes a homography, 8 numbers, of which 6 are the target's pose; the other 2 say something about \(\v{K}_f\). Three photographs at different tilts give 6 such numbers for 5 unknowns, and a flat target has done what the jig does, provided the photographs are tilted differently, which is the first thing on the "what to check" slide. The method built on this count is the one the slides name after Zhang; it is in the further reading, not derived here.</p>
"""

    # -------------------------------------------------------------- 10 refs
    s += H2(10, "refs", "Sources and further reading")
    s += r"""
<p>Nothing in these notes is taken from a source: every claim rests on the derivations and the worked example above. The list below is <b>further reading</b>, pointers to where the topic is treated in depth, offered without any claim about what they conclude.</p>
<h3>Further reading</h3>
<ol class="refs">
<li>Abdel-Aziz, Y. I. &amp; Karara, H. M. (1971). Direct linear transformation from comparator coordinates into object space coordinates in close-range photogrammetry. <i>Proc. Symposium on Close-Range Photogrammetry</i>, 1–18. — the paper the method is named after.</li>
<li>Hartley, R. &amp; Zisserman, A. (2004). <i>Multiple View Geometry in Computer Vision</i>, 2nd ed. Cambridge University Press. — on estimating \(\P\) from point correspondences, the normalisation of §4, the decomposition of §5, and algebraic versus reprojection error (§6, §7).</li>
<li>Zhang, Z. (2000). A flexible new technique for camera calibration. <i>IEEE Transactions on Pattern Analysis and Machine Intelligence</i>, 22, 1330–1334. — calibration from several photographs of a flat target (§9).</li>
</ol>
"""

    # --------------------------------------------------------- Appendix A
    s += H2("A", "appA", "Appendix A: why the split is unique")
    s += r"""
<p>§5 writes \(\v{M} = \v{K}\R\) with \(\v{K}\) upper triangular with positive diagonal and \(\R\) a rotation, and reads the eleven numbers off the factors. If there were two such splits the numbers would be ambiguous. There are not.</p>
<p>Suppose \(\v{M} = \v{K}\R = \v{K}'\R'\), both of the stated form. Then</p>
\[\v{K}'^{-1}\v{K} = \R'\R^\T. \tag{A.1}\]
<p>The left side is a product of upper-triangular matrices, hence upper triangular, with positive diagonal. The right side is a product of rotations, hence orthogonal. An orthogonal upper-triangular matrix is diagonal: its first column is a unit vector with only a first entry, so that entry is \(\pm1\) and the rest of the first row must vanish for the columns to be orthogonal to it; repeat down the diagonal. With positive diagonal the only possibility is the identity. So \(\v{K}' = \v{K}\) and \(\R' = \R\).</p>
<p>This is the uniqueness of the QR factorisation, with the factors in the other order. It is also why §5 must work from the bottom row up: the bottom row of \(\v{K}\) has one nonzero entry, so it ties \(\mr{3}\) to a single row of \(\R\), and each row above adds one more unknown row of \(\R\) and one more set of coefficients of \(\v{K}\). Gram–Schmidt in that order is the RQ factorisation, computed by hand.</p>
<p>The conventions matter. Allow negative diagonal entries and (A.1) admits diagonal matrices of \(\pm1\): each sign flip on \(f_x\) or \(f_y\) is paid for by negating a row of \(\R\), and the split is unique only up to those. §5 fixes them by taking \(f_x, f_y &gt; 0\) and the depths positive; a decomposition that respects a different pixel-axis convention, such as the image \(y\) axis pointing up, would fix them differently and get a negative \(f_y\).</p>
"""
    s += FOOT.replace("@@FOOTER@@", nc.footer()).replace("@@PREVNEXT@@", nc.prevnext(THIS))

    # every section reference becomes a link to its heading; a range links to its first section
    ids = {}
    n = 0
    for a, _ in TOC:
        if a in APP: continue
        n += 1; ids[n] = a
    def link(m):
        n = int(m.group(1))
        return '<a class="sec" href="#%s">%s</a>' % (ids[n], m.group(0)) if n in ids else m.group(0)
    parts = re.split(r"(<pre>.*?</pre>)", s, flags=re.S)
    s = "".join(p if p.startswith("<pre>") else re.sub(r"§(\d+)(?:–§?\d+)?", link, p) for p in parts)
    return s

def figures():
    """Section 1 shows the jig figure drawn for the module: copy it from the figures/ folder."""
    figs = HERE.parents[1] / "lectures" / "01-kinematics-kinetics" / "figures"
    shutil.copy(figs / "dlt-jig.svg", HERE / "dlt-jig.svg")

nc.install_fonts(HERE)
figures()
(HERE / "dlt-notes.html").write_text(build())
print("wrote dlt-notes.html")
