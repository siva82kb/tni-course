#!/usr/bin/env python3
"""Build fiducial-notes.html: the pose of a square fiducial from one image, derived in full.

The worked example in the notes is fiducial_pose.py in this folder. It is run
when the notes are built and both its source and its output are pasted in, so
the numbers on the page are the numbers the code produced.
Re-run after editing either file:   python3 build-fiducial-notes.py
"""
import html, re, pathlib, sys, subprocess
import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.resolve().parents[1] / "lectures"))
import notes_common as nc

DECK = "../../lectures/01-kinematics-kinetics/kinematics-kinetics.html"
SCRIPT = HERE / "fiducial_pose.py"
CODE = SCRIPT.read_text()
OUT = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=True).stdout

def code(s, caption):
    return ('<figure class="code"><figcaption>%s</figcaption><pre><code>%s</code></pre></figure>'
            % (caption, html.escape(s)))

def excerpt(first, last):
    """Source lines of fiducial_pose.py from the one containing `first` to the one containing `last`."""
    a = CODE.index(first); a = CODE.rfind("\n", 0, a) + 1
    b = CODE.index(last, a); b = CODE.index("\n", b)
    return CODE[a:b]

HEAD = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pose of a fiducial marker from one image</title>
<script>
  window.MathJax = {
    tex: { inlineMath: [['\\(', '\\)']], displayMath: [['\\[', '\\]']],
           tags: 'ams',
           macros: { v: ['{\\mathbf{#1}}', 1], m: ['{\\begin{bmatrix}#1\\end{bmatrix}}', 1],
                     R: '{\\mathbf{R}}', T: '{\\top}', kt: ['{\\tilde{\\mathbf{k}}_{#1}^{\\top}}', 1],
                     ht: ['{\\tilde{\\mathbf{h}}_{#1}^{\\top}}', 1] } },
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
  <h1>Pose of a fiducial marker from one image</h1>
  <p class="sub">From four pixel corners to the position and orientation of a printed tag, every step written out</p>
  <div class="meta">Transducers &amp; Instrumentation &middot; Module 2, Kinematics and Kinetics &middot; companion notes to the slides on tracking with fiducial markers. The worked example is <code>fiducial_pose.py</code>, run when this page is built; the code and its output appear in §8 exactly as they are.</div>
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

SOURCES = [
    'Olson, E. (2011). AprilTag: A robust and flexible visual fiducial system. <i>Proc. IEEE International Conference on Robotics and Automation</i>, 3400–3407. — the tag design, the code book and its accuracy (§1, §9).',
    'Wang, J. &amp; Olson, E. (2016). AprilTag 2: Efficient and robust fiducial detection. <i>Proc. IEEE/RSJ International Conference on Intelligent Robots and Systems</i>. — the detector that delivers the four ordered corners these notes start from (§1).',
]

TOC = [("problem", "The problem"), ("camera", "The camera model, with the scale written out"),
       ("flat", "A flat tag: the third column drops out"), ("corner", "What one corner gives"),
       ("system", "Four corners: the system and its solution"), ("pose", "From H to the pose"),
       ("refine", "Refining the pose"), ("example", "The worked example"),
       ("lessons", "What this says about using tags"), ("refs", "Sources and further reading"),
       ("appA", "Appendix A: the nearest rotation")]
APP = {"appA": "A"}

def build():
    def tocnum(i, a):
        if a in APP: return APP[a]
        return str(i + 1 - sum(1 for k, (b, _) in enumerate(TOC) if k < i and b in APP))
    toc_html = "\n".join('    <li><a href="#%s">%s&ensp;%s</a></li>' % (a, tocnum(i, a), b) for i, (a, b) in enumerate(TOC))
    s = (HEAD.replace("@@STYLE@@", nc.CSS).replace("@@TOC@@", toc_html).replace("@@DECK@@", DECK)
             .replace("@@BANNER@@", nc.banner([("Module 2: Kinematics and kinetics", DECK), ("Notes: fiducial pose", "")],
                                               nav=nc.topnav("01-kinematics-kinetics/fiducial-notes.html"))))
    H2 = lambda n, a, t: '<h2 id="%s"><span class="n">%s</span>%s</h2>\n' % (a, n, t)

    # ------------------------------------------------------------ 1 problem
    s += H2(1, "problem", "The problem")
    s += r"""
<p class="lead">A square tag of known size is stuck to a body segment. One calibrated camera photographs it. The detector returns the pixel positions of the tag's four corners, in a known order. From those eight numbers, find where the tag is and which way it faces: its position and orientation in the camera frame.</p>
<figure class="fig"><img src="apriltag.svg" alt="A tag36h11 fiducial and its image">
<figcaption><b>The tag and its image.</b> Left: the tag in its own frame \(W\), origin at the centre, \(x_W\) and \(y_W\) in the plane of the paper, corners at \((\pm1, \pm1)\) in units of half the side \(d\). Right: what the camera sees, a quadrilateral whose four corners \(\v{r}_p^{S}\) are the measurement. The map \(\v{H}\) between the two is what these notes construct, and then take apart.</figcaption></figure>
<p>Three frames are involved, with the deck's convention that a superscript names the frame a vector is expressed in:</p>
<table>
<tr><th>frame</th><th>what it is</th><th>vectors in it</th></tr>
<tr><td>\(W\)</td><td>the tag's own frame: origin at the tag centre, \(x_W, y_W\) along the edges, \(z_W\) out of the paper. For a tag the "world" frame of the camera slides is the tag itself.</td><td>\(\v{r}_P^{W}\), the corners, known: \((\pm d/2, \pm d/2, 0)\)</td></tr>
<tr><td>\(C\)</td><td>the camera frame: origin at the pinhole, \(z_C\) along the optical axis, out through the lens.</td><td>\(\v{r}_P^{C}\), unknown</td></tr>
<tr><td>\(S\)</td><td>the sensor frame, in pixels.</td><td>\(\v{r}_p^{S}\), the four detected corners, measured</td></tr>
</table>
<div class="cols">
<div>
<h3>Unknowns</h3>
<ul>
<li>\(\R_W^C\), the orientation of the tag frame in the camera frame: 3 numbers.</li>
<li>\(\v{o}_W^C\), the position of the tag centre in the camera frame: 3 numbers.</li>
</ul>
<p>Six in all: the pose.</p>
</div>
<div>
<h3>Knowns</h3>
<ul>
<li>\(\v{K}_f\), the intrinsic matrix, from calibration.</li>
<li>\(d\), the side of the tag, from its data sheet.</li>
<li>\(\v{r}_{p,i}^{S}\), the four pixel corners, from the detector, in a known order: 8 numbers.</li>
</ul>
</div>
</div>
<p>The order of the corners matters, and it is the code inside the tag that supplies it: a bare square looks the same turned through \(90^\circ\), the bit pattern does not, so the detector can say which image corner is the \((-1,-1)\) corner of the tag.</p>
<div class="note"><b>Why this is worth deriving.</b> The slides state the result in four lines: the tag is flat, so a \(3\times3\) matrix \(\v{H}\) maps tag coordinates to pixels; four corners determine \(\v{H}\); undoing \(\v{K}_f\) and using the unit length of a rotation's columns gives the pose. Each of those lines hides a step that is easy to get wrong, and the most common slip is to forget that a camera divides by depth. These notes take the steps one at a time.</div>
"""

    # ------------------------------------------------------------- 2 camera
    s += H2(2, "camera", "The camera model, with the scale written out")
    s += r"""
<p>Take one point \(P\) at \(\v{r}_P^{W}\) in the tag frame. Its position in the camera frame is the rigid transformation</p>
\[\v{r}_P^{C} = \R_W^C\,\v{r}_P^{W} + \v{o}_W^C, \qquad \v{r}_P^{C} = \m{x_P^C \\ y_P^C \\ z_P^C}, \tag{2.1}\]
<p>and the pinhole puts it on the sensor at</p>
\[x_p^S = f_x\,\frac{x_P^C}{z_P^C} + s\,\frac{y_P^C}{z_P^C} + o_{xs}, \qquad y_p^S = f_y\,\frac{y_P^C}{z_P^C} + o_{ys}. \tag{2.2}\]
<p>This is the content of the pinhole slides: similar triangles give \(x^I = f\,x^C/z^C\), and the pixel conversion adds the scale factors and the offset to the principal point. The thing to hold on to is the division by \(z_P^C\). A point twice as far away lands half as far from the principal point. That division is where all the depth information lives, and it is what makes the equations nonlinear.</p>
<p>The slides package (2.2) as a matrix product by multiplying through by \(z_P^C\):</p>
\[z_P^C \m{x_p^S \\ y_p^S \\ 1} = \underbrace{\m{f_x & s & o_{xs} \\ 0 & f_y & o_{ys} \\ 0 & 0 & 1}}_{\v{K}_f} \m{x_P^C \\ y_P^C \\ z_P^C}. \tag{2.3}\]
<p>Check the third row: it reads \(z_P^C \cdot 1 = z_P^C\), which is true and says nothing. The last row of \(\v{K}_f\) being \((0, 0, 1)\) is exactly what makes the third component of \(\v{K}_f\,\v{r}_P^C\) equal to the depth. The first two rows, divided by that third row, are (2.2) again.</p>
<div class="note"><b>On the slides' \(\equiv\).</b> The camera slides write \(\v{r}_p^I \equiv (f x_P^C,\ f y_P^C,\ z_P^C)\) and then drop the distinction, treating \(\v{r}_p^S\) as a homogeneous vector that is "the same point up to a scale". That is a convenient way to write the model, but it hides the scale, and in this problem the scale is different for each corner and has to be eliminated by hand. So here it is given a name and carried along:</div>
\[\lambda\,\v{r}_p^{S} = \v{K}_f\,\v{r}_P^{C}, \qquad \lambda = z_P^C, \qquad \v{r}_p^{S} = \m{x_p^S \\ y_p^S \\ 1}. \tag{2.4}\]
<p>Writing the rows of \(\v{K}_f\) as \(\kt{1}, \kt{2}, \kt{3} = (0, 0, 1)\), the two pixel coordinates are ratios:</p>
\[x_p^S = \frac{\kt{1}\,\v{r}_P^{C}}{\kt{3}\,\v{r}_P^{C}} = \frac{\kt{1}\,\v{r}_P^{C}}{z_P^C}, \qquad y_p^S = \frac{\kt{2}\,\v{r}_P^{C}}{\kt{3}\,\v{r}_P^{C}} = \frac{\kt{2}\,\v{r}_P^{C}}{z_P^C}. \tag{2.5}\]
<p>Substituting (2.1) for \(\v{r}_P^C\) makes the unknown pose appear in both numerator and denominator. That is the equation each corner has to satisfy.</p>
"""

    # --------------------------------------------------------------- 3 flat
    s += H2(3, "flat", "A flat tag: the third column drops out")
    s += r"""
<p>Write the rotation by its columns, \(\R_W^C = \m{\v{r}_1 & \v{r}_2 & \v{r}_3}\). Each column is one axis of the tag frame expressed in the camera frame: \(\v{r}_1\) is the direction of \(x_W\), \(\v{r}_2\) of \(y_W\), \(\v{r}_3\) of \(z_W\), the tag's normal. Then (2.1) reads</p>
\[\v{r}_P^{C} = x_P^W\,\v{r}_1 + y_P^W\,\v{r}_2 + z_P^W\,\v{r}_3 + \v{o}_W^C. \tag{3.1}\]
<p>Every point on the tag has \(z_P^W = 0\), because the tag frame was put in the plane of the tag. So for the corners the \(\v{r}_3\) term vanishes:</p>
\[\v{r}_i^{C} = x_i^W\,\v{r}_1 + y_i^W\,\v{r}_2 + \v{o}_W^C = \m{\v{r}_1 & \v{r}_2 & \v{o}_W^C}\m{x_i^W \\ y_i^W \\ 1}, \qquad i = 0, 1, 2, 3. \tag{3.2}\]
<p>Nothing has been approximated. The third column of the rotation is simply never multiplied by anything but zero, so it cannot be recovered from the tag's corners directly; it is recovered in §6 from the other two, because the three columns of a rotation are mutually perpendicular.</p>
<p>Put (3.2) into the camera model (2.4):</p>
\[\lambda_i\,\v{r}_{p,i}^{S} = \v{K}_f \m{\v{r}_1 & \v{r}_2 & \v{o}_W^C} \v{q}_i, \qquad \v{q}_i \equiv \m{x_i^W \\ y_i^W \\ 1}. \tag{3.3}\]
<p>The product of the two matrices is a single \(3\times3\) matrix. Call it \(\v{H}\):</p>
\[\boxed{\ \lambda_i\,\v{r}_{p,i}^{S} = \v{H}\,\v{q}_i, \qquad \v{H} = \v{K}_f \m{\v{r}_1 & \v{r}_2 & \v{o}_W^C}\ } \tag{3.4}\]
<p>\(\v{H}\) is the <em class="term">homography</em> of the tag: the map from a position on the tag to a position in the image. It is the same object that Zhang's calibration builds for each photograph of the checkerboard. There the board's homographies are used to find \(\v{K}_f\); here \(\v{K}_f\) is known and the one homography is used to find the pose. Same algebra, run the other way.</p>
<p>For the corner coordinates themselves, with the tag frame at the centre,</p>
\[\v{q}_0 = \m{-d/2 \\ -d/2 \\ 1}, \quad \v{q}_1 = \m{+d/2 \\ -d/2 \\ 1}, \quad \v{q}_2 = \m{+d/2 \\ +d/2 \\ 1}, \quad \v{q}_3 = \m{-d/2 \\ +d/2 \\ 1}. \tag{3.5}\]
<p>Any other choice of tag frame works, for instance the origin at one corner so that the corners are \(0, d\v{r}_1, d(\v{r}_1 + \v{r}_2), d\v{r}_2\), but the pose you get is the pose of the frame you chose, and the detector's convention is the centre.</p>
"""

    # ------------------------------------------------------------ 4 corner
    s += H2(4, "corner", "What one corner gives")
    s += r"""
<p>Write (3.4) row by row for one corner, with \(\ht{1}, \ht{2}, \ht{3}\) the rows of \(\v{H}\) and \((x_i, y_i)\) short for the measured pixel position \((x_{p,i}^S, y_{p,i}^S)\):</p>
\[\lambda_i\,x_i = \ht{1}\,\v{q}_i, \qquad \lambda_i\,y_i = \ht{2}\,\v{q}_i, \qquad \lambda_i = \ht{3}\,\v{q}_i. \tag{4.1}\]
<p>Three equations, but \(\lambda_i\) is an extra unknown that nobody asked for. The third equation tells us what it is, so substitute it into the first two:</p>
\[x_i\,(\ht{3}\,\v{q}_i) = \ht{1}\,\v{q}_i, \qquad y_i\,(\ht{3}\,\v{q}_i) = \ht{2}\,\v{q}_i. \tag{4.2}\]
<p>Two equations per corner, with the depth gone. Each is a product of a measured pixel coordinate and a row of \(\v{H}\) on the left, a row of \(\v{H}\) on the right: linear in the nine entries of \(\v{H}\). To make that visible, stack the rows of \(\v{H}\) into one vector of nine unknowns,</p>
\[\v{h} = \m{\tilde{\v{h}}_1 \\ \tilde{\v{h}}_2 \\ \tilde{\v{h}}_3} \in \mathbb{R}^9, \tag{4.3}\]
<p>and move everything in (4.2) to one side:</p>
\[\m{\v{q}_i^\T & \v{0}^\T & -x_i\,\v{q}_i^\T \\ \v{0}^\T & \v{q}_i^\T & -y_i\,\v{q}_i^\T}\v{h} = \v{0}. \tag{4.4}\]
<p>This \(2\times9\) block is one corner's contribution. Its entries are the known tag coordinates in \(\v{q}_i\) and the measured pixels \(x_i, y_i\). Written out, the first row is</p>
\[x_i^W h_{11} + y_i^W h_{12} + h_{13} - x_i\,x_i^W h_{31} - x_i\,y_i^W h_{32} - x_i\,h_{33} = 0. \tag{4.5}\]
<div class="note warn"><b>The slip to avoid.</b> It is tempting to write a corner's equations as \(x_i = \kt{1}(x_i^W\v{r}_1 + y_i^W\v{r}_2 + \v{o}_W^C)\) and \(y_i = \kt{2}(\ldots)\), linear in the pose. These are the numerators of (2.5) with the denominators left off, and they describe a camera that does not divide by depth: an affine camera, which draws a square as a parallelogram at any distance. The real camera draws it as a trapezoid, the far edge shorter, and that foreshortening is the only information about tilt and distance the image has. The factor \(\lambda_i = \ht{3}\v{q}_i\) in (4.2) is what keeps it.</div>
"""

    # ------------------------------------------------------------ 5 system
    s += H2(5, "system", "Four corners: the system and its solution")
    s += r"""
<p>Stack the four blocks (4.4):</p>
\[\v{A}\,\v{h} = \v{0}, \qquad \v{A} = \m{\v{q}_0^\T & \v{0}^\T & -x_0\,\v{q}_0^\T \\ \v{0}^\T & \v{q}_0^\T & -y_0\,\v{q}_0^\T \\ & \vdots & \\ \v{q}_3^\T & \v{0}^\T & -x_3\,\v{q}_3^\T \\ \v{0}^\T & \v{q}_3^\T & -y_3\,\v{q}_3^\T} \in \mathbb{R}^{8\times9}. \tag{5.1}\]
<p>Eight equations, nine unknowns, and the right-hand side is zero. Three things follow.</p>
<h3>The scale of \(\v{h}\) is free</h3>
<p>If \(\v{h}\) solves (5.1) so does \(c\,\v{h}\) for any number \(c\). This is not a defect of the method; it is in the model. Multiply \(\v{H}\) by \(c\) in (3.4) and every \(\lambda_i\) absorbs it: the same pixels come out. So the pixels determine \(\v{H}\) only up to an overall factor, which is why "nine entries, eight unknowns": a direction in nine-dimensional space, not a point.</p>
<h3>Eight equations are enough</h3>
<p>A direction in \(\mathbb{R}^9\) has eight degrees of freedom, so eight independent equations pin it down. For four corners with no three in a line, which a square always satisfies, \(\v{A}\) has rank 8 and its null space is one line: the solution \(\v{h}\) is unique up to the factor \(c\). That is the whole reason a single tag suffices. The same system from a checkerboard with forty corners would have eighty rows and still only an eight-dimensional answer, hence its better accuracy.</p>
<h3>Solving it: the null vector</h3>
<p>Eight equations in nine unknowns always have a nonzero solution, noise or no noise: an \(8\times9\) matrix has a null space of dimension at least one. So the solution is simply</p>
\[\v{h} = \text{a nonzero vector with } \v{A}\v{h} = \v{0}, \tag{5.2}\]
<p>reshaped into the three rows of \(\v{H}\). The singular value decomposition \(\v{A} = \v{U}\mathbf{\Sigma}\v{V}^\T\) delivers it: \(\v{A}\) has only eight singular values, and the ninth column of \(\v{V}\), the right singular vector with no singular value at all, is the null vector. That is what the code reads off, (5.3) below.</p>
<h3>What noise does, then</h3>
<p>It is worth pausing on what this means. Four noisy corners are still four points in the image, and <em>some</em> homography maps the tag's four corners onto them exactly, because four points in general position fix a homography and any four can be reached. So the \(\v{H}\) from (5.2) reproduces the measured corners perfectly; its reprojection error is zero by construction. Noise has not gone away. It has gone into \(\v{H}\) itself: the matrix that fits the corners is no longer of the form \(\v{K}_f\m{\v{r}_1 & \v{r}_2 & \v{o}_W^C}\) with perpendicular unit columns, and that is where it will be found in §6, in the Gram matrix before snapping, and paid for in §7.</p>
<p>The same system with more than four points is different. A pentagonal tag gives ten rows, a hexagonal one twelve, several tags printed on one flat sheet or a checkerboard's forty corners give many more, all against the same eight degrees of freedom, and then noise does make \(\v{A}\v{h} = \v{0}\) unsatisfiable. (The points must still lie in one plane; that is what let \(\v{r}_3\) drop out in §3. Tags on different faces of a block need the full \(3\times4\) projection instead.) The question becomes</p>
\[\min_{\v{h}}\ \Vert\v{A}\v{h}\Vert^2 \quad\text{subject to}\quad \Vert\v{h}\Vert = 1, \tag{5.3}\]
<p>and the answer is the smallest singular vector: with \(\v{h} = \v{V}\v{a}\) for a unit \(\v{a}\), \(\Vert\v{A}\v{h}\Vert^2 = \sum_j \sigma_j^2 a_j^2\), smallest when all of \(\v{a}\) sits on the smallest \(\sigma_j\). For four corners the smallest singular value is exactly zero and (5.3) reduces to (5.2), so one recipe, "take the last right singular vector of \(\v{A}\)", covers both cases. That is why the code uses it.</p>
<div class="note"><b>Two remarks on the solve.</b> (i) The third row of \(\v{H}\) is \(\kt{3}\m{\v{r}_1 & \v{r}_2 & \v{o}_W^C} = (r_{1z},\ r_{2z},\ o_z)\), so \(h_{33}\) is the depth of the tag centre, which is never zero for a visible tag. One can therefore set \(h_{33} = 1\) and solve an ordinary \(8\times8\) system instead of (5.2). The singular-vector route is the standard one because it treats all nine entries alike. (ii) \(\v{A}\) mixes tag coordinates in metres (\(\pm0.05\)) with pixels (hundreds), so its singular values are spread over five orders of magnitude; the example in §8 prints them. The usual remedy is to rescale both sets of coordinates to order one before building \(\v{A}\) and undo the scaling afterwards. The example does not bother, and at double precision it does not matter for this problem.</div>
"""

    # -------------------------------------------------------------- 6 pose
    s += H2(6, "pose", "From H to the pose")
    s += r"""
<p>We have \(\v{H}\) up to a factor, and we know from (3.4) what it is made of. Undo the intrinsics:</p>
\[\v{M} \equiv \v{K}_f^{-1}\,\v{H} = c\m{\v{r}_1 & \v{r}_2 & \v{o}_W^C} = \m{\v{m}_1 & \v{m}_2 & \v{m}_3}. \tag{6.1}\]
<p>The three columns of \(\v{M}\) are the two axes and the origin of the tag, each multiplied by the same unknown \(c\). Five steps turn this into a pose.</p>
<ol class="steps">
<li><b>The scale.</b> With exact data \(\v{m}_1 = c\,\v{r}_1\) and \(\v{m}_2 = c\,\v{r}_2\), and \(\v{r}_1, \v{r}_2\) are columns of a rotation matrix, hence unit vectors. So \(\Vert\v{m}_1\Vert = \Vert\v{m}_2\Vert = |c|\), and either norm gives the scale. This equality is not guaranteed by the solve; it is inherited from the structure of \(\v{H}\), and with noisy corners that structure is lost (§5): the null vector still fits the corners, but \(\v{K}_f^{-1}\v{H}\) is then no longer \(c\) times a matrix with orthonormal columns, and the two norms differ. There is no single right choice of \(c\) in that case; the mean is a convention,
\[|c| = \tfrac{1}{2}\left(\Vert\v{m}_1\Vert + \Vert\v{m}_2\Vert\right), \tag{6.2}\]
and whatever is chosen is renormalised in step 4 and discarded by the refinement of §7. The gap between the two norms is a diagnostic: it measures how far the four corners are from what a rigid flat square could have produced.
This is also the step in which the <em>known size</em> of the tag does its work. The tag coordinates in \(\v{q}_i\) were written in metres, so \(\v{H}\) and hence \(\v{M}\) carry metres in their third column. Had the corners been written as \((\pm1, \pm1)\) instead, the same procedure would give \(\v{o}_W^C\) in units of \(d/2\). The camera cannot tell a small tag nearby from a big tag far away; the data sheet can.</li>
<li><b>The sign.</b> Dividing by \(|c|\) leaves \(\pm\m{\v{r}_1 & \v{r}_2 & \v{o}_W^C}\), both of which satisfy (5.1). The tag is in front of the camera, so its centre has positive depth: choose the sign that makes the third component of the third column positive, \(o_z > 0\).</li>
<li><b>The missing column.</b> The columns of a rotation are orthonormal and right-handed, so the third is the cross product of the first two:
\[\v{r}_3 = \v{r}_1 \times \v{r}_2. \tag{6.3}\]
This is the tag's normal, the one direction the flat tag's corners said nothing about.</li>
<li><b>Tidying up.</b> With exact data \(\m{\v{r}_1 & \v{r}_2 & \v{r}_3}\) is a rotation matrix. With noise \(\v{r}_1\) and \(\v{r}_2\) are not quite unit and not quite perpendicular, so the matrix is only nearly a rotation. Replace it by the nearest rotation matrix in the least-squares sense: with the singular value decomposition \(\m{\v{r}_1 & \v{r}_2 & \v{r}_3} = \v{U}\mathbf{\Sigma}\v{V}^\T\),
\[\R_W^C = \v{U}\,\mathrm{diag}(1, 1, \det \v{U}\v{V}^\T)\,\v{V}^\T. \tag{6.4}\]
The derivation is Appendix A; it is the three-dimensional version of the fit in Appendix A of the inverse-kinematics notes. The middle factor guards against the answer coming out as a reflection.</li>
<li><b>The result.</b> \(\R_W^C\) from (6.4) and \(\v{o}_W^C = \v{m}_3 / c\), with the sign from step 2. Six numbers, from eight pixel coordinates and a known side length.</li>
</ol>
<p>Two checks are free. The dot product \(\v{r}_1\cdot\v{r}_2\) should be near zero and the two norms near each other; how far they are from that is a direct reading of how much the four corners disagree with a rigid, planar tag. The example in §8 prints the Gram matrix \(\R'^\T\R'\) before step 4 for exactly this purpose.</p>
"""

    # ------------------------------------------------------------ 7 refine
    s += H2(7, "refine", "Refining the pose")
    s += r"""
<p>The pose from §6 is a closed-form answer, and it is the right answer for exact data. For noisy data it is only a good starting point, for two reasons that are visible in the derivation.</p>
<ul>
<li>The constraint that the first two columns of \(\v{M}\) are perpendicular unit vectors is ignored while solving and imposed afterwards. §5 fits the four noisy corners exactly with an \(\v{H}\) that has the wrong structure, and step 4 of §6 then snaps to the nearest rotation. But "nearest" there means nearest in the entries of a \(3\times3\) matrix, (A.1), which has nothing to do with pixels: the snapped pose no longer reproduces the corners, and nothing has chosen it to miss them as little as possible. The distance in pixels between where a corner was seen and where the model puts it, the <em class="term">reprojection error</em>, is what one actually cares about, and the closed form never looks at it.</li>
<li>With more than four points the same objection applies one step earlier: (5.3) minimises \(\Vert\v{A}\v{h}\Vert\), and each row of \(\v{A}\v{h}\) is a pixel equation multiplied through by \(\lambda_i\), (4.2), so corners at different depths are weighted differently and the quantity minimised is again not the reprojection error.</li>
</ul>
<p>The remedy is the same one the constrained inverse-kinematics notes use in their section 9: write the error that matters and minimise it directly by Gauss–Newton, starting from the closed-form pose.</p>
\[E(\R, \v{o}) = \sum_{i=0}^{3} \left\Vert \mathbf{\pi}\!\left(\v{K}_f,\ \R\,\v{r}_i^{W} + \v{o}\right) - \m{x_i \\ y_i}\right\Vert^2, \tag{7.1}\]
<p>where \(\mathbf{\pi}\) is the pinhole map (2.2), depth division included. The six unknowns are handled as a small rotation vector \(\v{w}\) applied on the left of the current estimate, \(\R \leftarrow \R(\v{w})\,\R\), and a shift of \(\v{o}\); after each step the rotation is exactly a rotation, so nothing has to be tidied. Each iteration linearises the eight residuals in the six parameters, solves the \(8\times6\) least-squares problem for the step, and applies it. In the example the Jacobian is taken by finite differences, one parameter at a time, so that the code shows nothing but "nudge a parameter, see how the pixels move".</p>
<p>The example in §8 runs both: the closed form alone, then the closed form followed by refinement, and repeats the comparison five hundred times with fresh noise. The refinement reduces the orientation error by about a factor of five. Any detector meant for measurement does this, or something equivalent; the closed form is how it finds the neighbourhood of the answer.</p>
"""

    # ----------------------------------------------------------- 8 example
    s += H2(8, "example", "The worked example")
    s += r"""
<p>A camera with focal length 800 px and principal point at \((640, 360)\), a tag of side \(d = 0.1\) m turned \(35^\circ\) about a skew axis and placed 0.8 m in front of the camera. The script projects the four corners with (2.1) and (2.2), then forgets the pose and recovers it by §5–§7. Then it does the same with half a pixel of noise on every corner coordinate.</p>
"""
    s += code(excerpt("import numpy as np", "pix, lam = project(K, R_true, o_true, corners_W)"), "<b>fiducial_pose.py</b> — the set-up: camera, tag, true pose, and the projection with the depth division written out (§2)")
    s += code(excerpt("def build_A(corners_W, pix):", "    return Vt[-1].reshape(3, 3), S"), "<b>fiducial_pose.py</b> — the \\(8\\times9\\) system (5.1) and its null vector (5.2), read off as the last right singular vector")
    s += code(excerpt("def pose_from_H(K, H):", "    return R, o, R_approx"), "<b>fiducial_pose.py</b> — from \\(\\v{H}\\) to the pose: the five steps of §6")
    s += code(excerpt("def refine(K, R, o, corners_W, pix, iters=10):", "    return R, o"), "<b>fiducial_pose.py</b> — Gauss–Newton on the reprojection error (7.1)")
    s += code(excerpt("def run(pix, label):", "refined      : median"), "<b>fiducial_pose.py</b> — running it: exact corners, one noisy draw, and 500 noisy repeats")
    s += code(OUT, "<b>Output</b> of <code>python3 fiducial_pose.py</code>, as produced when this page was built")
    s += r"""
<p>Reading the output against the derivation:</p>
<ul>
<li>The four depths \(\lambda_i\) differ, 0.76 m to 0.84 m, because the tag is tilted; that spread is the foreshortening of §4.</li>
<li>In both runs \(\v{A}\) has eight nonzero singular values and the ninth right singular vector is an exact null vector, as §5 said it must be. With exact corners that null vector is the true \(\v{H}\): the pose comes back to machine precision, the Gram matrix before snapping is the identity, and refinement has nothing to do.</li>
<li>With half a pixel of noise the null vector still fits the four corners exactly, but it is no longer the right kind of matrix. The Gram matrix shows what the corners said: the two axes came out with lengths \(\sqrt{1.04}\) and \(\sqrt{0.96}\) and a dot product of \(-0.02\), far from a rigid square. Snapping to a rotation gives a pose that is off by about \(5^\circ\) in orientation and 3 mm in position, and that pose puts the corners a pixel away from where they were seen. Refinement brings the reprojection down to the noise level and the orientation error to about \(1^\circ\).</li>
<li>Five hundred repeats say the single draw was typical: a median of \(5^\circ\) for the closed form against \(1^\circ\) refined, with 90% of trials under \(9^\circ\) and \(2^\circ\) respectively.</li>
</ul>
<p>Half a pixel is an ordinary corner-detection error, and the tag here spans only about a hundred pixels. The sensitivity is real, and it is why tags are used large, close, and refined.</p>
"""

    # ----------------------------------------------------------- 9 lessons
    s += H2(9, "lessons", "What this says about using tags")
    s += r"""
<p>Everything a tag can and cannot do for movement tracking is in the algebra above.</p>
<ul>
<li><b>Depth comes from apparent size.</b> Step 1 of §6 recovers distance from how large the tag appears against how large it is. The apparent size shrinks as \(1/z\), so a fixed error in pixels becomes a depth error that grows with the square of the distance. Doubling the distance quadruples the depth uncertainty, for the same corner accuracy.</li>
<li><b>Tilt comes from foreshortening.</b> The orientation is read from how the far edge is shorter than the near one, (4.2). For a tag facing the camera squarely the four corners are nearly a square and small tilts change the picture very little, so orientation about the in-plane axes is least certain when the tag looks best. At very oblique angles the opposite happens: one of \(\v{m}_1, \v{m}_2\) becomes short and the corresponding axis is poorly determined, and the detector loses the border altogether beyond roughly \(70^\circ\) off-axis.</li>
<li><b>Four points is the minimum.</b> §5 showed eight equations for eight unknowns with no redundancy; every pixel error goes straight into the pose. More corners would average it out, which is why a checkerboard calibrates well and why, for tracking, several tags on one rigid segment are treated as one target with their relative poses fixed.</li>
<li><b>Refine, always.</b> §7. The closed form is where you start, not where you stop.</li>
<li><b>One camera, no correspondence problem.</b> Against the marker clusters of the earlier sections: no triangulation, no second camera to calibrate against the first, and no question of which image blob is which marker, because the tag's code names it. The price is the sensitivity above and the need for the tag to be seen flat enough to decode.</li>
</ul>
<p>Flat tags on a curved limb also violate the model in a way nothing here corrects: the tag rides on skin, and the soft-tissue artefact of the inverse-kinematics notes applies to it as it does to any other marker.</p>
<h3>The four limits, in figures</h3>
<p>The statements above are made concrete on the slides with four figures, reproduced here. Two come from a deliberately minimal simulation, <code>make_limit_data.py</code> in this folder: the tag's four corners are projected through the camera model of §2, each coordinate is given 0.5 px of Gaussian noise, the pose is recovered with the closed form and refinement of §5–§7, and the median and interquartile range of 500 runs are written to <code>data/limit-distance.csv</code> and <code>data/limit-headon.csv</code> in the module folder, with the fitted constants of the scaling laws in <code>data/limit-fits.tex</code>. The other two are geometry alone. All four are pgfplots or TikZ figures in the module's <code>tikz/</code> folder, drawn from those files; the camera has \(f = 800\) px and the tag \(d = 0.1\) m throughout.</p>
<figure class="fig"><img src="limit-distance.svg" alt="Pose error against distance">
<figcaption><b>Distance</b> (<code>tikz/limit-distance.tex</code>). Tag tilted 30° from face-on, 0.4 m to 2 m. Depth error follows \(z^2\) and orientation error follows \(z\): both are the corner noise \(\sigma\) scaled by the tag's size in the image, \(s = fd/z\), once for orientation and twice for depth. Depth from one camera is the stereo triangle with the tag's side as baseline.</figcaption></figure>
<figure class="fig"><img src="limit-headon.svg" alt="Orientation error against tilt near face-on">
<figcaption><b>Face-on</b> (<code>tikz/limit-headon.tex</code>). Tag at 0.8 m, 100 px wide, tilted 0° to 50°. Tilt is read from the ratio \(h/s = \cos\theta\) of the tag's height to its width in the image; the sensitivity of that ratio to tilt is \(\sin\theta\), zero at face-on, and the error is the noise divided by the sensitivity, \(\sigma/(s\sin\theta)\), the dashed line. This is Module 1's rule for noise referred to the measurand, applied to a tag used as a tilt sensor.</figcaption></figure>
<figure class="fig"><img src="limit-oblique.svg" alt="Row height at the far edge against tilt">
<figcaption><b>Edge-on</b> (<code>tikz/limit-oblique.tex</code>). Geometry only. The tilt estimate keeps improving as the tag turns; what gives out is reading the bits. The rows of cells are foreshortened by \(\cos\theta\), and the far rows are also farther away by \(\tfrac{d}{2}\sin\theta\), so a far-edge row is \(h_{\rm row} = \tfrac{s}{8}\cos\theta \cdot z/(z + \tfrac{d}{2}\sin\theta)\) px high. Below about 2 px, twice a typical lens blur, a sample cannot be placed inside a cell and the code is not read: near 80° for a 100 px tag, 70° for 50 px, 50° for 25 px.</figcaption></figure>
<figure class="fig"><img src="blur-images.svg" alt="The tag's cells under motion blur">
<figcaption><b>Motion blur</b> (<code>tikz/blur-images.tex</code>, pixels from <code>make_blur_pixels.py</code>). A 32 px tag, 4 px per cell, moved sideways during the exposure by \(b = vT_{\rm exp}f/z\) pixels. Every edge becomes a ramp \(b\) px long. A bit is read by sampling the centre of its cell: at half a cell of smear the centre is still clean; at one cell the ramps meet at the centre; at two cells a black cell's centre averages as much white neighbour as black, and the code is gone while the border is still found.</figcaption></figure>
"""

    # -------------------------------------------------------------- 10 refs
    s += H2(10, "refs", "Sources and further reading")
    s += r"""
<p>The claims in these notes rest on the derivations and the worked example above. The list is divided into <b>sources</b>, works read and relied on, and <b>further reading</b>, pointers to where a topic is treated in depth, offered without any claim about what they conclude.</p>
<h3>Sources</h3>
<ol class="refs">
""" + "\n".join("<li>%s</li>" % x for x in SOURCES) + r"""
</ol>
<h3>Further reading</h3>
<ol class="refs">
<li>Zhang, Z. (2000). A flexible new technique for camera calibration. <i>IEEE Transactions on Pattern Analysis and Machine Intelligence</i>, 22, 1330–1334. — on the planar homography and its decomposition (§3, §6), run in the calibration direction.</li>
<li>Hartley, R. &amp; Zisserman, A. (2004). <i>Multiple View Geometry in Computer Vision</i>, 2nd ed. Cambridge University Press. — on estimating a homography from point correspondences, the normalisation of §5, and algebraic versus reprojection error (§5, §7).</li>
<li>Horn, B. K. P. (1987). Closed-form solution of absolute orientation using unit quaternions. <i>Journal of the Optical Society of America A</i>, 4, 629–642. — on the nearest rotation matrix (§6, Appendix A).</li>
<li>Nocedal, J. &amp; Wright, S. J. (2006). <i>Numerical Optimization</i>, 2nd ed. Springer. — on Gauss–Newton and least squares (§7).</li>
</ol>
"""

    # --------------------------------------------------------- Appendix A
    s += H2("A", "appA", "Appendix A: the nearest rotation")
    s += r"""
<p>Step 4 of §6 asks: given a \(3\times3\) matrix \(\R'\) that is almost a rotation, which rotation \(\R\) is closest to it? Closest in the least-squares sense, summing the squares of all nine entry differences:</p>
\[\R = \arg\min_{\R^\T\R = \v{I},\ \det\R = 1}\ \Vert \R - \R' \Vert_F^2. \tag{A.1}\]
<p>Expand the square. \(\Vert\R - \R'\Vert_F^2 = \Vert\R\Vert_F^2 + \Vert\R'\Vert_F^2 - 2\,\mathrm{tr}(\R^\T\R')\). The first term is 3 for any rotation and the second does not involve \(\R\), so minimising (A.1) is the same as</p>
\[\max_{\R}\ \mathrm{tr}(\R^\T\R'). \tag{A.2}\]
<p>Decompose \(\R' = \v{U}\mathbf{\Sigma}\v{V}^\T\) with \(\v{U}, \v{V}\) orthogonal and \(\mathbf{\Sigma} = \mathrm{diag}(\sigma_1, \sigma_2, \sigma_3)\), all \(\sigma_j \ge 0\). The trace is unchanged by cycling its factors:</p>
\[\mathrm{tr}(\R^\T\v{U}\mathbf{\Sigma}\v{V}^\T) = \mathrm{tr}(\mathbf{\Sigma}\,\underbrace{\v{V}^\T\R^\T\v{U}}_{\v{Q}}) = \sum_j \sigma_j\,Q_{jj}. \tag{A.3}\]
<p>\(\v{Q}\) is a product of orthogonal matrices, so it is orthogonal, and every entry of an orthogonal matrix has magnitude at most 1 (each row is a unit vector). Hence \(\sum_j \sigma_j Q_{jj} \le \sum_j \sigma_j\), with equality exactly when every \(Q_{jj} = 1\), which for an orthogonal matrix forces \(\v{Q} = \v{I}\). Then \(\v{V}^\T\R^\T\v{U} = \v{I}\), so</p>
\[\R = \v{U}\v{V}^\T. \tag{A.4}\]
<p>This is orthogonal, but its determinant is \(\det\v{U}\det\v{V} = \pm1\). If it comes out \(-1\) the closest orthogonal matrix is a reflection, which is not a pose. Among proper rotations the best choice flips the sign on the smallest singular direction, since that costs the least in (A.3):</p>
\[\R = \v{U}\,\mathrm{diag}(1, 1, \det\v{U}\v{V}^\T)\,\v{V}^\T, \tag{A.5}\]
<p>which is (6.4). With clean data \(\R'\) is already a rotation, all \(\sigma_j = 1\), and (A.5) returns \(\R'\) unchanged. The planar version of the same argument, with a single angle in place of a matrix, is Appendix A of the inverse-kinematics notes.</p>
"""
    s += FOOT.replace("@@FOOTER@@", nc.footer()).replace("@@PREVNEXT@@", nc.prevnext("01-kinematics-kinetics/fiducial-notes.html"))

    # every section reference becomes a link to its heading; a range links to its first section
    ids = {}
    n = 0
    for a, _ in TOC:
        if a in APP: continue
        n += 1; ids[n] = a
    def link(m):
        n = int(m.group(1))
        return '<a class="sec" href="#%s">%s</a>' % (ids[n], m.group(0)) if n in ids else m.group(0)
    # only outside <pre> blocks (the code and output contain no § anyway, but be safe)
    parts = re.split(r"(<pre>.*?</pre>)", s, flags=re.S)
    s = "".join(p if p.startswith("<pre>") else re.sub(r"§(\d+)(?:–§?\d+)?", link, p) for p in parts)
    return s

def limit_figures():
    """Section 9 shows the same four figures as the slides: copy them from the module's figures/ folder."""
    import shutil
    figs = HERE.parents[1] / "lectures" / "01-kinematics-kinetics" / "figures"
    for name in ("limit-distance.svg", "limit-headon.svg", "limit-oblique.svg", "blur-images.svg"):
        shutil.copy(figs / name, HERE / name)

nc.install_fonts(HERE)
limit_figures()
(HERE / "fiducial-notes.html").write_text(build())
print("wrote fiducial-notes.html")
