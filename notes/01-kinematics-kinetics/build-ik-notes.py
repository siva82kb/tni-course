#!/usr/bin/env python3
"""Build ik-notes-thigh.html and ik-notes-leg.html from ../../lectures/01-kinematics-kinetics/interactive/ik.html.

Every code excerpt in the notes is cut out of ik.html at build time (by
function name), so the notes show exactly the code the simulation runs.
Re-run this after editing ik.html:   python3 build-ik-notes.py
"""
import html, re, pathlib, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.resolve().parents[1] / "lectures"))
import notes_common as nc
MODULE = HERE.resolve().parents[1] / "lectures" / "01-kinematics-kinetics"
SRC = (MODULE / "interactive" / "ik.html").read_text()

# ---------------------------------------------------------------- excerpts
def func(name):
    """The whole `function name(...) { ... }` block, dedented."""
    m = re.search(r"^( *)function %s\(" % re.escape(name), SRC, re.M)
    if not m: raise SystemExit("no function " + name)
    i = m.start(); depth = 0; j = i
    while True:
        c = SRC[j]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: j += 1; break
        j += 1
    return dedent(SRC[i:j])

def lines(first, last):
    """Source lines from the one containing `first` to the one containing `last`."""
    a = SRC.index(first); a = SRC.rfind("\n", 0, a) + 1
    b = SRC.index(last, a); b = SRC.index("\n", b)
    return dedent(SRC[a:b])

def dedent(s):
    ls = s.split("\n")
    ind = min(len(l) - len(l.lstrip()) for l in ls if l.strip())
    return "\n".join(l[ind:] if l.strip() else "" for l in ls)

def code(s, caption):
    return ('<figure class="code"><figcaption>%s</figcaption><pre><code>%s</code></pre></figure>'
            % (caption, html.escape(s)))

X = {
    "geom":   lines("var L1 = 0.42", "var SL = ["),
    "slope":  lines("var TA = [0.15", "var SA = ["),
    "truth":  func("truth"),
    "poses":  func("poses") + "\n" + func("rot"),
    "bone":   func("bonePoint"),
    "rest":   func("restPoint"),
    "init":   func("initMarkers"),
    "step":   lines("var ka = Math.pow", "m.p[0] += m.v[0]*dt; m.p[1] += m.v[1]*dt;"),
    "stepfn": func("stepMarkers"),
    "gauss":  func("gauss") + "\n" + func("measure"),
    "link":   func("linkPose"),
    "wrap":   func("wrap") + "\n" + func("uik"),
    "model":  func("modelMarkers"),
    "cik":    func("cik"),
    "loop":   lines("var t = 0, paused = false, SUB = 10", "requestAnimationFrame(tick);\n  }"),
}

# ------------------------------------------------------------------- style
STYLE = nc.CSS

HEAD = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<script>
  window.MathJax = {
    tex: { inlineMath: [['\\(', '\\)']], displayMath: [['\\[', '\\]']],
           tags: 'ams',
           macros: { v: ['{\\mathbf{#1}}', 1], m: ['{\\begin{bmatrix}#1\\end{bmatrix}}', 1],
                     R: '{\\mathbf{R}}', T: '{\\top}' } },
    svg: { fontCache: 'global' },
    startup: { typeset: false }
  };
</script>
<script id="MathJax-script" defer src="../../lectures/01-kinematics-kinetics/interactive/vendor/tex-svg.js"></script>
<style>%(style)s</style>
</head>
<body>
%(banner)s<div class="wrap">
<nav>
  <div class="t">Contents</div>
  <ol>
%(toc)s
  </ol>
</nav>
<main>
<header>
  <h1>%(title)s</h1>
  <p class="sub">%(subtitle)s</p>
  <div class="meta">Transducers &amp; Instrumentation &middot; Module 2, Kinematics and Kinetics &middot; companion notes to <code>ik.html</code>. Every code block below is cut from that file when these notes are built, so what you read is what runs.</div>
</header>
"""

FOOT = r"""
%(prevnext)s</main>
</div>
%(footer)s<script>
  // Typeset section by section once MathJax is ready. One pass over the whole
  // page is not reliable for a document this long; section passes are.
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

# ---- works that have been read and are relied on. To promote a further-reading
#      item, move its entry here (and restore the in-text claim it supports).
SOURCES = [
    'Uchida, T. K. &amp; Delp, S. L. (2021). <i>Biomechanics of Movement: The Science of Sports, Robotics, and Rehabilitation</i>. MIT Press. — marker-based kinematics, anatomical and tracking frames, and the two estimators (§8–9).',
]
SOURCES_HTML = ('<h3>Sources</h3>\n<ol class="refs">\n' + '\n'.join('<li>%s</li>' % x for x in SOURCES) + '\n</ol>') if SOURCES else ''

# ------------------------------------------------------------- the content
def page(mode):
    leg = mode == "leg"
    name = "two-link leg" if leg else "thigh"
    J = "knee" if leg else "hip"
    sym_q = r"\theta_2" if leg else r"\theta_1"
    toc = [("model", "The model"), ("fk", "Forward kinematics"), ("motion", "The true motion"),
           ("slide", "Skin artefact I: stretch with joint angle"), ("wobble", "Skin artefact II: wobbling mass"),
           ("noise", "Measurement noise"), ("loop", "One frame of the simulation"),
           ("uik", "Unconstrained inverse kinematics"), ("cik", "Constrained inverse kinematics"),
           ("compare", "What to expect"), ("appA", "Appendix A: the pose-fit derivation"), ("appB", "Appendix B: the Jacobian derivation"), ("refs", "References")]
    APP = {"appA": "A", "appB": "B"}
    def tocnum(i, a):
        if a in APP: return APP[a]
        return str(i + 1 - sum(1 for k, (b, _) in enumerate(toc) if k < i and b in APP))
    toc_html = "\n".join('    <li><a href="#%s">%s&ensp;%s</a></li>' % (a, tocnum(i, a), b) for i, (a, b) in enumerate(toc))
    s = HEAD % dict(
        title=("Inverse kinematics of a two-link leg" if leg else "Inverse kinematics of a single link"),
        subtitle=("Model, artefacts and the two estimators, as implemented in the simulation: thigh and shank, hip pinned, knee angle"
                  if leg else "Model, artefacts and the two estimators, as implemented in the simulation: one thigh on a pinned hip, hip angle"),
        style=STYLE, toc=toc_html, mode=mode,
        banner=nc.banner([("Module 2: Kinematics and kinetics", "../../lectures/01-kinematics-kinetics/kinematics-kinetics.html"),
                          (("Notes: two-link leg" if leg else "Notes: single link"), "")],
                         nav=nc.topnav("01-kinematics-kinetics/ik-notes-%s.html" % mode)),
        other=("ik-notes-thigh.html" if leg else "ik-notes-leg.html"),
        othername=("thigh-only" if leg else "two-link"))

    H2 = lambda n, a, t: '<h2 id="%s"><span class="n">%d</span>%s</h2>\n' % (a, n, t)

    # ---------------------------------------------------------------- 1 model
    s += H2(1, "model", "The model")
    fig = dict(mode=mode,
               a=("the" if not leg else "the two"), b=("" if not leg else "s"), c=("" if not leg else "s"),
               d=("" if not leg else "s"), e=(r"\(\theta_1\)" if not leg else r"\(\theta_1\), \(\theta_2\)"),
               f=("the" if not leg else "each"))
    FIG = r"""<figure class="fig"><img src="ik-model-%(mode)s.svg" alt="The model, annotated">
<figcaption><b>The model, drawn as the simulation draws it.</b> Lab frame \(A\) at the pinned hip; %(a)s link frame%(b)s at the proximal joint%(c)s with \(x\) along the link; the direction angle \(\varphi_1\) from \(+x_A\) and the joint angle%(d)s %(e)s; the three template markers on %(f)s link. Inset: a marker is a mass on the skin, tied to its rest point on the bone by a spring and damper (§4–5), and what the cameras report is that position plus noise (§6).</figcaption></figure>
"""
    s += r"""
<p class="lead">%s</p>
<p>Everything is planar and in SI units (metres, seconds, radians inside the code; degrees on the sliders and charts). The <em class="term">lab frame</em> \(A\) has its origin at the hip, \(x\) pointing to the right of the screen and \(y\) up (a right leg seen from the person's right: they face \(+x\), so the thigh swings towards \(+x\) in flexion and the shank folds back towards \(-x\)). The hip is a pin: it cannot translate. %s</p>
@@FIG@@
<h3>Reference frames and angles</h3>
<p>Each link carries its own frame with the origin at the link's proximal joint and the \(x\)-axis running along the link towards its distal end. A link's orientation in \(A\) is its <em class="term">direction angle</em> \(\varphi\), measured from the lab \(x\)-axis. Rotation matrices carry the slides' frame labels, \(\R^{A}_{T}\) being "the thigh frame \(T\) expressed in \(A\)", and in the plane each one is a rotation by a single angle:</p>
\[\R^{A}_{T} = \R(\varphi_1), \qquad \R(\varphi) \equiv \m{\cos\varphi & -\sin\varphi \\ \sin\varphi & \cos\varphi}, \qquad \R(\varphi)^{-1} = \R(\varphi)^\T = \R(-\varphi). \tag{1.1}\]
<p>The joint angles are what a clinician would quote: <em class="term">hip flexion</em> \(\theta_1\) is the angle of the thigh from vertical-down, positive towards \(+x\)%s. In terms of direction angles,</p>
\[\varphi_1 = -\tfrac{\pi}{2} + \theta_1%s \tag{1.2}\]
%s
<h3>The marker template</h3>
<div class="note"><b>On notation.</b> A superscript on a vector names the <em>reference frame it is expressed in</em>, as on the slides: \(\v{r}^{A}_{m_i}\) is in the lab frame \(A\), \(\v{l}^{T}_i\) is in the thigh frame \(T\)%s. It is <em>not</em> a transpose. The skin and camera quantities \(\v{\rho}^{A}_i, \v{p}^{A}_i, \v{m}^{A}_i\) all live in the lab frame and are written with \(A\) throughout. All vectors here are columns, and the transpose, when it appears, is written \(\top\): \(\R^{\top}\), \(\v{J}_i^{\top}\).</div>
<p>Three markers sit on each link at fixed positions in the link's own frame, the <em class="term">template</em> \(\v{l}_i\). They are deliberately not symmetric and not on the link's axis: the frame built from them is attached to the body but is not the body's own symmetry frame. These positions are what a calibration would supply; the simulation assumes that calibration is perfect.</p>
%s
<table>
<tr><th>symbol</th><th>meaning</th><th>in the code</th></tr>
<tr><td>\(\v{r}^{A}\), \(\v{l}^{T}\), \(\v{l}^{S}\)</td><td>a <b>superscript names the frame</b> a vector is expressed in (lab \(A\), thigh \(T\), shank \(S\)) --- the deck's convention. All vectors are columns; the transpose is \(\top\).</td><td></td></tr>
<tr><td>\(L_1\)%s</td><td>link length%s, m</td><td><code>L1</code>%s</td></tr>
<tr><td>\(\theta_1\)%s</td><td>hip flexion%s</td><td><code>q[0]</code>%s</td></tr>
<tr><td>\(\varphi_1\)%s</td><td>direction angle of the thigh%s</td><td><code>ps.p1</code>%s</td></tr>
<tr><td>\(\R^{A}_{T}\)%s</td><td>rotation of the thigh frame%s, as on the slides; \(= \R(\varphi_1)\)%s</td><td><code>rot(ps.p1, &middot;)</code>%s</td></tr>
<tr><td>\(\v{l}^{T}_i\)%s</td><td>marker \(i\) of the thigh%s, in its link frame</td><td><code>TL[i]</code>%s</td></tr>
<tr><td>\(\v{r}^{A}_{m_i}\)</td><td>true, bone-fixed position of marker \(i\) in the lab</td><td><code>bonePoint(k, i, q)</code></td></tr>
<tr><td>\(\v{\rho}^{A}_i\)</td><td>rest point of marker \(i\): bone-fixed position plus the skin stretch</td><td><code>restPoint(k, i, q)</code>, kept in <code>m.r</code></td></tr>
<tr><td>\(\v{p}^{A}_i\)</td><td>actual position of marker \(i\) on the skin</td><td><code>m.p</code></td></tr>
<tr><td>\(\v{m}^{A}_i\)</td><td>measured position of marker \(i\): \(\v{p}^{A}_i\) plus camera noise</td><td><code>meas[i]</code></td></tr>
<tr><td>\(\hat{\cdot}\)</td><td>an estimate</td><td>returned by <code>uik()</code>, <code>cik()</code></td></tr>
</table>
""" % (
        ("Two rigid links, thigh and shank, hinged at the hip and at the knee. Six markers. We want the knee angle." if leg
         else "One rigid link, the thigh, pinned at the hip. Three markers. We want the hip angle."),
        ("The knee is a hinge: the shank's proximal end is always at the thigh's distal end." if leg else ""),
        ("; <em class=\"term\">knee flexion</em> \\(\\theta_2\\) is the angle by which the shank is folded back from the thigh's line, zero when the leg is straight" if leg else ""),
        (r", \qquad \varphi_2 = \varphi_1 - \theta_2." if leg else "."),
        (r"<p>With the shank, the knee's rotation is the shank frame expressed in the thigh frame, \(\R^{T}_{S} = \R(-\theta_2)\), and the shank in the lab composes the two: \(\R^{A}_{S} = \R^{A}_{T}\,\R^{T}_{S} = \R(\varphi_2)\).</p>" if leg else ""),
        (", \\(\\v{l}^{S}_i\\) in the shank frame \\(S\\)" if leg else ""),
        code(X["geom"], "<b>ik.html</b> &middot; geometry and marker templates (the shank's are unused in thigh-only mode)"),
        (", \\(L_2\\)" if leg else ""), ("s" if leg else ""), (", <code>L2</code>" if leg else ""),
        (", \\(\\theta_2\\)" if leg else ""), (", knee flexion" if leg else ""), (", <code>q[1]</code>" if leg else ""),
        (", \\(\\varphi_2\\)" if leg else ""), (", shank" if leg else ""), (", <code>ps.p2</code>" if leg else ""),
        (", \\(\\R^{A}_{S}\\)" if leg else ""), (", shank" if leg else ""), (", \\(\\R(\\varphi_2)\\)" if leg else ""), (", <code>rot(ps.p2, &middot;)</code>" if leg else ""),
        (", \\(\\v{l}^{S}_i\\)" if leg else ""), (", shank" if leg else ""), (", <code>SL[i]</code>" if leg else ""),
    )

    s = s.replace("@@FIG@@", FIG % fig)

    # ------------------------------------------------------------------ 2 FK
    s += H2(2, "fk", "Forward kinematics")
    s += r"""
<p>Forward kinematics maps joint angles to marker positions. For the thigh, whose frame sits on the pinned hip,</p>
\[\v{r}^{A}_{m_i} = \R^{A}_{T}\,\v{l}^{T}_i = \R(\varphi_1)\,\v{l}^{T}_i, \qquad i = 1,2,3. \tag{2.1}\]
<p>Read it as the slides' rule for changing frames, \(\v{r}^{A} = \R^{A}_{T}\,\v{r}^{T} + \v{o}^{A}_{T}\), with the thigh's origin \(\v{o}^{A}_{T} = \v{0}\) because the hip is pinned at the lab origin.</p>
"""
    if leg:
        s += r"""
<p>The knee is the thigh's distal end, and the shank's markers are placed from there:</p>
\[\begin{aligned}
  \v{o}^{A}_{S} &= \R^{A}_{T}\m{L_1 \\ 0} = L_1\m{\cos\varphi_1 \\ \sin\varphi_1}, \\
  \v{r}^{A}_{m_i} &= \v{o}^{A}_{S} + \R^{A}_{S}\,\v{l}^{S}_i, \qquad \R^{A}_{S} = \R^{A}_{T}\,\R^{T}_{S} = \R(\varphi_2), \qquad i = 4,5,6.
\end{aligned} \tag{2.2}\]
<p>The knee is where the shank's frame sits in the thigh's: \(\v{o}^{T}_{S} = [L_1, 0]^{\top}\), carried into \(A\) by \(\R^{A}_{T}\). And the shank's orientation composes, exactly as on the slides: the thigh's rotation, then the knee's.</p>
<p>Equations (2.1)–(2.2) are the whole forward model: given \((\theta_1, \theta_2)\), every marker position follows. Note what is baked in — fixed lengths, a hinge knee, a pinned hip. These are exactly the constraints the constrained estimator will exploit, and the assumptions it will be wrong by if the real leg violates them.</p>
"""
    else:
        s += r"""
<p>That is the whole forward model: given \(\theta_1\), every marker position follows. Two things are baked in — the link is rigid, and the hip is pinned. These are exactly the constraints the constrained estimator will exploit.</p>
"""
    s += code(X["poses"], "<b>ik.html</b> &middot; direction angles from joint angles, and the 2-D rotation")
    s += r"""
<p><code>poses</code> implements (1.2) and the knee position of (2.2); <code>rot(a, v)</code> is \(\R(a)\,\v{v}\). Put together, they give the forward kinematics of a marker, \(\v{r}^{A}_{m_i}\):</p>
"""
    s += code(X["bone"], "<b>ik.html</b> &middot; equations (2.1)%s: where marker <i>i</i> of link <i>k</i> is on the bone" % ("&ndash;(2.2)" if leg else ""))
    s += r"""
<p>This is the point the markers would sit at if skin did not move. You will meet the same calculation a second time in <code>modelMarkers</code> (§9): the constrained estimator needs these positions <em>and</em> their derivatives with respect to the joint angles, so that function repeats the rotate-and-add of <code>bonePoint</code> inline and builds the derivatives from the same rotations as it goes, rather than calling <code>bonePoint</code>.</p>
"""

    # -------------------------------------------------------------- 3 motion
    s += H2(3, "motion", "The true motion")
    s += r"""
<p>The joint angles are driven, not simulated dynamically: the simulation prescribes smooth trajectories and the question is only how well they can be recovered from the markers. Each angle is a sum of two sinusoids whose frequencies are not simple multiples of one another, so the motion never exactly repeats, with amplitudes and a cadence (0.9 Hz) in the range of walking:</p>
%s
<p>%sThe <em>speed</em> slider scales how fast \(t\) advances per displayed frame (§7), so it changes velocities and accelerations without changing the path.</p>
""" % (
        (r"""\[\begin{aligned}
\theta_1(t) &= 22^\circ \sin(2\pi\,0.9\,t) + 7^\circ \sin(2\pi\,0.37\,t + 1),\\
\theta_2(t) &= \max\!\big(0,\; 28^\circ + 26^\circ \sin(2\pi\,0.9\,t - 0.7) + 7^\circ \sin(2\pi\,0.53\,t)\big).
\end{aligned} \tag{3.1}\]""" if leg else
         r"""\[\theta_1(t) = 22^\circ \sin(2\pi\,0.9\,t) + 7^\circ \sin(2\pi\,0.37\,t + 1). \tag{3.1}\]"""),
        ("" if leg else r"The code below also returns <code>th2</code>, the knee angle \(\theta_2\): the same function serves the two-link leg model, where \(\theta_2\) sets the shank. With the thigh on its own there is no shank, so it drives nothing and can be ignored here. "))
    s += code(X["truth"], "<b>ik.html</b> &middot; the prescribed joint angles")

    # --------------------------------------------------------------- 6 slide
    s += H2(4, "slide", "Skin artefact I: stretch with the joint angle")
    s += r"""
<p>The larger part of soft-tissue artefact in walking is not inertial at all. It is deterministic: as a joint flexes, the skin and muscle over the neighbouring segments slide and stretch, and the markers go with them. The simplest model of this, and the one the simulation uses, is that the displacement is <em>linear</em> in the joint angle, and nothing more: a marker's rest point is displaced <em>along its link</em> by an amount proportional to the flexion of the joint under study%s:</p>
\[\v{\rho}^{A}_i = \v{r}^{A}_{m_i} + g\,a_i\,%s\m{\cos\varphi \\ \sin\varphi}, \tag{4.1}\]
<p>where \(\v{r}^{A}_{m_i}\) is the bone point of §2, \((\cos\varphi, \sin\varphi)\) is the link's direction, \(%s\) is in degrees, \(a_i\) is a per-marker slope in mm per degree, and \(g\) is the <em>gain</em> slider (0 switches the effect off, so \(\v{\rho}^{A}_i = \v{r}^{A}_{m_i}\); 1 gives the slopes below). The slopes grow towards the knee, where the skin moves most:</p>
""" % (("" if leg else " (the hip, in this mode)"), sym_q, sym_q)
    s += code(X["slope"], "<b>ik.html</b> &middot; the per-marker slopes")
    s += code(X["rest"], "<b>ik.html</b> &middot; the rest point, equation (4.1)")
    s += r"""
<div class="note warn"><b>Two honest caveats.</b> (1) The slopes are illustrative values, chosen so that the effect is clearly visible at gain 1; they are not fitted to any data, and the real magnitudes vary with marker site, subject and task. (2) The <em>sign</em> (thigh skin bunching distally towards the knee, shank skin proximally) is likewise an assumption. Neither caveat changes the lesson of §10, which depends only on the artefact being systematic rather than random.</div>
"""

    # -------------------------------------------------------------- 5 wobble
    s += H2(5, "wobble", "Skin artefact II: the wobbling mass")
    s += r"""
<p>Markers are stuck to skin, and skin is not bone. When the segment accelerates, the soft tissue (and the marker on it) lags and overshoots. A simple model of this, and a common one, is the <em class="term">wobbling mass</em>: the marker is a point mass tied to its rest point \(\v{\rho}^{A}_i\) of §4 by a spring and a damper. The stiffness and damping are set by the sliders.</p>
<p>The stiffness and damping matrices are <em>diagonal in the link frame</em>, because skin is held differently along a limb than across it. With unit mass, the equation of motion of marker \(i\) on a link of direction angle \(\varphi\) is</p>
\[\ddot{\v{p}}^{A}_i = -\R(\varphi)\,\v{K}\,\R(\varphi)^\T (\v{p}^{A}_i - \v{\rho}^{A}_i)
                  -\R(\varphi)\,\v{C}\,\R(\varphi)^\T (\dot{\v{p}}^{A}_i - \dot{\v{\rho}}^{A}_i), \tag{5.1}\]
\[\begin{aligned}
  \v{K} &= \m{k_a & 0 \\ 0 & k_x}, & k_a &= (2\pi f_{along})^2, & k_x &= (2\pi f_{across})^2; \\
  \v{C} &= \m{c_a & 0 \\ 0 & c_x}, & c_a &= 2\zeta\,(2\pi f_{along}), & c_x &= 2\zeta\,(2\pi f_{across}).
\end{aligned} \tag{5.2}\]

<p>The sliders set the two undamped natural frequencies and one damping ratio \(\zeta\); (5.2) converts them to stiffness and damping per unit mass. The rotation by \(\R(\varphi)^\T\) takes the offset and the relative velocity into the link frame, the diagonal matrices act there, and \(\R(\varphi)\) brings the force back to the lab. The damper acts on the velocity <em>relative to the rest point</em>, so a marker on a link moving at constant velocity feels no drag.</p>
<h3>Integration</h3>
<p>(5.1) is a second-order differential equation for each marker, and the simulation has to step it forward in time. It does so in the simplest possible way. Writing \(\v{v}^{A}_i\) for the marker's velocity, (5.1) says what the acceleration \(\ddot{\v{p}}^{A}_i\) is right now; over a short interval \(\delta t\) we take the velocity to change by acceleration \(\times\, \delta t\), and the position to change by velocity \(\times\, \delta t\). That is Euler's method, the first thing anyone tries for a differential equation.</p>
<p>One detail matters. Plain Euler updates position with the <em>old</em> velocity, and for a spring that is a bad choice: the energy of the oscillation creeps up a little every step and the marker ends up swinging more and more. Updating the velocity first and then moving the position with the <em>new</em> velocity costs nothing extra and does not have that defect — the oscillation keeps its amplitude. This variant is called the <em class="term">semi-implicit Euler</em> method (the name only records that one half of the update uses the updated value). The step is taken ten times per displayed frame so that even the stiffest spring on the slider (25 Hz, a period of 40 ms) is sampled some 24 times per cycle. The rest-point velocity \(\dot{\v{\rho}}^{A}_i\) is taken as the change in \(\v{\rho}^{A}_i\) over the last sub-step divided by \(\delta t\). At \(t=0\) every marker starts on its rest point, at rest.</p>
\[\v{v}^{A}_i \leftarrow \v{v}^{A}_i + \ddot{\v{p}}^{A}_i\,\delta t, \qquad \v{p}^{A}_i \leftarrow \v{p}^{A}_i + \v{v}^{A}_i\,\delta t, \qquad \delta t = \tfrac{1}{10}\cdot\tfrac{\text{speed}}{60}\ \text{s}. \tag{5.3}\]
"""
    s += r"""
<p>Euler's method and its limitations are the opening of any treatment of ordinary differential equations; see the further reading at the end, or the <a href="https://en.wikipedia.org/wiki/Semi-implicit_Euler_method">Wikipedia entry for the semi-implicit Euler method</a>.</p>
"""
    s += code(X["init"] + "\n" + X["stepfn"], "<b>ik.html</b> &middot; marker state, and one sub-step of (5.1)–(5.3)")
    s += r"""
<div class="note"><b>What this artefact looks like to an estimator.</b> Because (5.1) is linear, the marker is a <em>filtered</em> copy of its rest point. In the link frame, axis by axis, the transfer function from rest point to marker is
\[\frac{P(s)}{R(s)} = \frac{cs + k}{s^2 + cs + k},\]
a causal second-order low-pass filter (module 1's LTI systems again): unity gain for slow movement, a resonance near \(f_{along}\) or \(f_{across}\) when \(\zeta\) is small, and attenuation with a phase lag above — the marker always arrives late. All three markers on a link are filtered the same way and lag the bone <em>together</em>. The cluster moves almost as a rigid unit, so to any method it looks as if the bone itself moved. Only the small differences between markers — from their different offsets and the different stiffness along and across — can be averaged out. This is the "rigid component" of soft-tissue artefact in the literature, and it is why neither estimator removes it (§10).</div>
"""

    # --------------------------------------------------------------- 4 noise
    s += H2(6, "noise", "Measurement noise")
    s += r"""
<p>A camera system reports each marker with a random error that is, to a good approximation, independent between markers, between frames and between axes, with zero mean. The simulation adds exactly that:</p>
\[\v{m}^{A}_i = \v{p}^{A}_i + \sigma\,\v{\varepsilon}_i, \qquad \v{\varepsilon}_i \sim \mathcal{N}(\v{0}, \v{I}_2), \tag{6.1}\]
<p>Note that it is \(\v{p}^{A}_i\), the marker where it actually is on the skin (§4–5), that is measured — not the bone point \(\v{r}^{A}_{m_i}\) of §2. The two coincide only when both artefact sliders are at zero; otherwise the cameras faithfully report a marker that is itself in the wrong place. Here \(\sigma\) is the <em>noise</em> slider in millimetres, drawn afresh for every marker on every frame. A computer's random-number generator gives uniform numbers; to turn two of them into a Gaussian one, the code uses the Box–Muller transform: for \(u, v\) uniform on \((0,1)\), \(\sqrt{-2\ln u}\,\cos 2\pi v\) is a standard normal sample.</p>
"""
    s += code(X["gauss"], "<b>ik.html</b> &middot; the sampler, and the measurement")
    s += r"""
<div class="note"><b>Order of magnitude.</b> A calibrated optical system in a lab achieves sub-millimetre residuals; the slider's default of 2 mm is deliberately pessimistic so that the noise is visible. The point of the comparison in §10 is that noise is the <em>least</em> important error in practice — which is why it comes last here, after the two artefacts that move the marker before any camera sees it.</div>
"""

    # ---------------------------------------------------------------- 7 loop
    s += H2(7, "loop", "One frame of the simulation")
    s += r"""
<p>The browser calls <code>tick()</code> once per displayed frame, 60 times a second. Each call advances the simulation by \(\Delta t = \text{speed}/60\) s and does the following, in this order:</p>
<ol class="steps">
<li><b>Advance the world, in ten sub-steps.</b> For each sub-step of \(\delta t = \Delta t / 10\): evaluate the true joint angle%s at the current time from (3.1); from %s compute every marker's bone point (§2) and rest point (§4); move every marker on the skin by one step of the wobbling-mass equation (5.1)–(5.3); advance the clock by \(\delta t\). After ten sub-steps the clock has moved by \(\Delta t\) and the markers have followed the bone with whatever lag the springs impose. (If the simulation is paused, or the speed is zero, this step is skipped and nothing moves.)</li>
<li><b>Measure.</b> Call <code>measure()</code> once: for each of the %d markers, take its current position on the skin \(\v{p}^{A}_i\) and add fresh Gaussian noise of standard deviation \(\sigma\) to each coordinate (§6). The result, <code>meas</code>, is the only thing the estimators are ever shown.</li>
<li><b>Record the truth</b> for this instant: the joint angle%s <code>q = truth(t)</code>. This is what the estimates will be compared with. The estimators do not see it.</li>
<li><b>Unconstrained estimate.</b> <code>uik(meas)</code>: build %s from %s own three markers (§8, Step A), %s</li>
<li><b>Constrained estimate.</b> <code>cik(meas)</code>: starting from the previous frame's answer, run Gauss–Newton on all %d markers at once (§9) to get \(\hat{\v{q}}\).</li>
<li><b>Store and draw.</b> Append \(\{t,\ \text{truth},\ \text{unconstrained},\ \text{constrained},\ \text{gap}\}\) to the history, drop anything older than the 8 s window, redraw the leg and the charts, and ask the browser for the next frame.</li>
</ol>
<p>Two consequences of this ordering are worth noticing. The artefact is applied <em>before</em> the noise, as in §4–6, so the measurement is noise on top of a marker that may already be in the wrong place. And both estimators see the <em>same</em> measurement each frame, so the comparison between them is never confounded by different noise draws.</p>
""" % (
        ("s" if leg else ""), ("them" if leg else "it"), 6 if leg else 3, ("s" if leg else ""),
        ("each link's frame" if leg else "the thigh's frame"), ("its" if leg else "its"),
        ("then take the knee angle as the difference of the two orientations and record the knee gap (Steps B–C)." if leg
         else "then read off the hip angle and record how far the estimated hip is from its pin (Step B)."),
        6 if leg else 3)
    s += code(X["loop"], "<b>ik.html</b> &middot; the frame loop")
    s += r"""
<p>The estimators see only <code>meas</code>. They are also given the marker templates \(\v{l}_i\)%s — that is, the simulation assumes a perfect calibration. The error you see is therefore entirely due to noise and artefact, never to a wrong model of the subject.</p>
""" % (" and, for the constrained estimator, the link lengths and the pinned hip" if leg else " and, for the constrained estimator, the pinned hip")

    # ----------------------------------------------------------------- 8 UIK
    s += H2(8, "uik", "Unconstrained inverse kinematics")
    stepA = r"""
<p>The unconstrained estimator treats each link as an independent rigid body: from the link's three measured markers alone, find the link's pose in the lab — its rotation \(\hat{\R}^{A}_{B} = \R(\hat\varphi)\) and origin \(\hat{\v{o}}^{A}_{B}\), \(B\) being \(T\) or \(S\) — with no reference to any other link or joint. %s</p>
<h3>Step A — the pose of one link from its markers</h3>
<p>Two ways to do it are provided; the radio button chooses.%s</p>
<p>First, what is being looked for. The template \(\v{l}_i\) says where each marker sits <em>relative to the link's own origin</em>, in the link's own frame. If the link were turned by \(\varphi\) and its origin were at \(\v{o}\) in the lab, marker \(i\) would be at \(\R(\varphi)\,\v{l}_i + \v{o}\) — the slides' rule for changing frames. The unknowns are therefore the link's angle \(\varphi\) and the lab position \(\v{o}\) of its origin%s; the data are the three measured \(\v{m}^{A}_i\). Nothing tells the estimator where the origin is beforehand — it must work that out from the markers too.</p>
<p><b>A1, the lecture's construction.</b> Use the first two markers only. The measured direction from \(\v{m}^{A}_1\) to \(\v{m}^{A}_2\), compared with the same direction in the template, gives the rotation. The origin then follows from marker 1 alone: it must be wherever the rotated template puts \(\v{l}_1\) onto the measured \(\v{m}^{A}_1\):</p>
\[\hat{\varphi} = \operatorname{atan2}(\v{m}^{A}_2 - \v{m}^{A}_1) - \operatorname{atan2}(\v{l}_2 - \v{l}_1), \qquad
  \hat{\v{o}} = \v{m}^{A}_1 - \R(\hat{\varphi})\,\v{l}_1. \tag{8.1}\]
<p>This is exactly the three-marker frame of the slides collapsed to the plane: \(\v{x}_B\) along \(m_1 \to m_2\), origin at \(m_1\). The third marker is not used at all, which is why this variant is noisier than it needs to be.</p>
<p><b>A2, least-squares rigid fit.</b> Use all three. For any candidate \((\varphi, \v{o})\), each marker has a mismatch \(\v{m}^{A}_i - \R(\varphi)\,\v{l}_i - \v{o}\) between where it was measured and where the candidate pose would put it. We want the pose that makes the three mismatches as small as possible together — the smallest sum of squared lengths%s:</p>
\[\min_{\varphi,\,\v{o}} \sum_{i=1}^{3} \big\| \v{m}^{A}_i - \R(\varphi)\,\v{l}_i - \v{o} \big\|^2. \tag{8.2}\]
<p>Setting the derivative with respect to \(\v{o}\) to zero shows that the optimal translation maps the template centroid onto the measured centroid, \(\hat{\v{o}} = \bar{\v{m}}^{A} - \R(\hat\varphi)\,\bar{\v{l}}\). Substituting back, with centred coordinates \(\v{a}_i = \v{l}_i - \bar{\v{l}}\) and \(\v{b}_i = \v{m}^{A}_i - \bar{\v{m}}^{A}\), the problem reduces to maximising \(\sum_i \v{b}_i^\T \R(\varphi)\,\v{a}_i = S_c \cos\varphi + S_s \sin\varphi\), where</p>
\[S_c = \sum_i \v{a}_i \cdot \v{b}_i = \sum_i (a_{ix} b_{ix} + a_{iy} b_{iy}), \qquad
  S_s = \sum_i \v{a}_i \times \v{b}_i = \sum_i (a_{ix} b_{iy} - a_{iy} b_{ix}), \tag{8.3}\]
<p>whose maximum over \(\varphi\) is at</p>
\[\hat{\varphi} = \operatorname{atan2}(S_s,\, S_c), \qquad \hat{\v{o}} = \bar{\v{m}}^{A} - \R(\hat{\varphi})\,\bar{\v{l}}. \tag{8.4}\]
<p>The three steps from (8.2) to (8.4) — eliminating \(\v{o}\), reducing to a maximisation over \(\varphi\), and solving it — are worked through line by line in <a class="sec" href="#appA">Appendix A</a>. Closed form, no iteration: in two dimensions the best-fit rotation is a single <code>atan2</code>.</p>
<p>This task — lay one set of points over another as well as possible using only a rotation and a translation — is a standard problem with a name, the <a href="https://en.wikipedia.org/wiki/Orthogonal_Procrustes_problem"><em class="term">Procrustes problem</em></a>. In two dimensions a rotation has a single angle, which is why the answer collapses to one <code>atan2</code>. In three dimensions a rotation has three, so that last step cannot be done with an <code>atan2</code>; instead the \(3\times3\) matrix \(\sum_i \v{b}_i\v{a}_i^\top\) is factorised (its singular-value decomposition) and the rotation is read off the factors. That three-dimensional version is usually called the Kabsch algorithm, and it is what motion-capture software runs. Everything up to that last step is the same.</p>
""" % (("Here there is one link, so the whole method is Step A followed by reading off the hip angle." if not leg
        else "The joint angle then comes from the two poses."),
       ("" if not leg else r" <b>Whichever is chosen, Step A is carried out twice, once per link, and the two runs are completely independent:</b> the thigh's pose is found from the thigh's three markers \(\v{m}^{A}_{1,2,3}\) with the thigh template \(\v{l}^{T}_i\), and the shank's from \(\v{m}^{A}_{4,5,6}\) with \(\v{l}^{S}_i\). Neither run knows the other exists; nothing ties the shank's origin to the thigh's far end. Below, \(\v{l}_i\), \(\hat\varphi\) and \(\hat{\v{o}}\) refer to whichever link is in hand, and <code>linkPose</code> is simply called twice."),
       (" — for the thigh, that origin is the hip" if not leg else " — the hip for the thigh, the knee for the shank"),
       ("" if not leg else r" (the sum runs over one link's three markers only; it is solved once for the thigh and once, separately, for the shank)"))
    if not leg:
        # one link only: say thigh everywhere instead of a generic link
        for a, b in [
            ("treats each link as an independent rigid body: from the link's three measured markers alone, find the link's pose in the lab — its rotation \\(\\hat{\\R}^{A}_{B} = \\R(\\hat\\varphi)\\) and origin \\(\\hat{\\v{o}}^{A}_{B}\\), \\(B\\) being \\(T\\) or \\(S\\) — with no reference to any other link or joint.",
             "treats the thigh as a rigid body on its own: from its three measured markers alone, find its pose in the lab — its rotation \\(\\hat{\\R}^{A}_{T} = \\R(\\hat\\varphi)\\) and origin \\(\\hat{\\v{o}}\\) — with no reference to anything else."),
            ("Step A — the pose of one link from its markers", "Step A — the pose of the thigh from its markers"),
            ("\\hat{\\varphi}", "\\hat{\\varphi}_1"), ("\\hat\\varphi)", "\\hat\\varphi_1)"),
            ("\\hat{\\v{o}}", "\\hat{\\v{o}}^{A}_{T}"),
            ("\\v{l}_i", "\\v{l}^{T}_i"), ("\\v{l}_1", "\\v{l}^{T}_1"), ("\\v{l}_2", "\\v{l}^{T}_2"), ("\\bar{\\v{l}}", "\\bar{\\v{l}}^{T}"),
            ("\\v{x}_B\\) along", "\\v{x}_T\\) along"),
        ]:
            stepA = stepA.replace(a, b)
    s += stepA
    s += code(X["link"], "<b>ik.html</b> &middot; Step A, both variants: (8.1) and (8.3)–(8.4)")
    if leg:
        s += r"""
<h3>Step B — joint angles from the two poses</h3>
<p>With the thigh pose \((\hat{\R}^{A}_{T}, \hat{\v{o}}^{A}_{T})\), i.e. \(\hat\varphi_1\) and \(\hat{\v{o}}_T\), and the shank pose \((\hat{\R}^{A}_{S}, \hat{\v{o}}^{A}_{S})\) likewise, the knee's rotation is \(\hat{\R}^{T}_{S} = \hat{\R}^{A\top}_{T}\hat{\R}^{A}_{S} = \R(\hat\varphi_2 - \hat\varphi_1)\) — the slides' \(\R^{B_p}_{B_d} = \R^{A\top}_{B_p}\R^{A}_{B_d}\) — so, inverting (1.2):</p>
\[\hat\theta_1 = \hat\varphi_1 + \tfrac{\pi}{2}, \qquad \hat\theta_2 = \hat\varphi_1 - \hat\varphi_2. \tag{8.5}\]
<p>Both differences must be <em>wrapped</em> into \((-\pi, \pi]\). At deep flexion the shank's direction angle sits near \(-180^\circ\), and <code>atan2</code> jumps from \(-180^\circ\) to \(+180^\circ\) there, so a little noise can flip its answer by \(360^\circ\) for a frame; without wrapping, that lands in the knee angle. The wrap is \(\operatorname{atan2}(\sin a, \cos a)\).</p>
<h3>Step C — the knee gap</h3>
<p>Nothing in Steps A–B says the two links meet. The thigh's reconstruction puts the knee at \(\hat{\v{o}}_T + \R(\hat\varphi_1)\,[L_1, 0]^\T\); the shank's puts it at \(\hat{\v{o}}_S\). The distance between them,</p>
\[\text{gap} = \big\| \hat{\v{o}}_T + \R(\hat\varphi_1)\m{L_1\\0} - \hat{\v{o}}_S \big\|, \tag{8.6}\]
<p>is reported and charted. It is a direct, physical measure of how much the unconstrained reconstruction violates the anatomy — a real leg's gap is zero.</p>
"""
    else:
        s += r"""
<h3>Step B — the hip angle, and where the hip went</h3>
<p>With the thigh pose \((\hat{\R}^{A}_{T}, \hat{\v{o}}^{A}_{T})\), i.e. \(\hat\varphi_1\) and \(\hat{\v{o}}_T\), invert (1.2):</p>
\[\hat\theta_1 = \hat\varphi_1 + \tfrac{\pi}{2}, \tag{8.5}\]
<p>wrapped into \((-\pi, \pi]\) by \(\operatorname{atan2}(\sin a, \cos a)\) so that noise near \(\pm180^\circ\), where <code>atan2</code> jumps from one sign to the other, cannot produce a \(360^\circ\) jump.</p>
<p>Nothing in Step A knows the hip is pinned. The estimated origin \(\hat{\v{o}}_T\) is where the thigh's markers say the hip is; its distance from the true pin,</p>
\[\text{hip position error} = \| \hat{\v{o}}_T \|, \tag{8.6}\]
<p>is reported and charted. It is the one-link version of the "knee gap" in the two-link notes: a physical quantity that the unconstrained reconstruction gets wrong and the constrained one cannot, by construction.</p>
"""
    s += code(X["wrap"], "<b>ik.html</b> &middot; Steps B–C")

    # ----------------------------------------------------------------- 9 CIK
    s += H2(9, "cik", "Constrained inverse kinematics")
    nq = 2 if leg else 1
    s += r"""
<div class="note"><b>Same cost, fewer freedoms.</b> This is the same kind of problem as the least-squares fit of §8 (A2): choose the pose that puts the model's markers closest to the measured ones. What changes is <em>which poses are allowed</em>.</p>
<p>In §8 each link was fitted on its own and could take any rigid pose: its angle and its origin were both unknowns%s, and nothing kept the links together. Here the origins are not unknowns at all — %s. The only unknown%s left %s the joint angle%s, all %d markers enter one fit, and the pose that comes out is always one the model can reach. That is what "constrained" means.</p>
<p>So "unconstrained" in §8 never meant that no least squares was involved. It meant that each link was free to sit wherever its own three markers put it.</div>
<p>The constrained estimator starts from the forward model of §2 — which already contains the pinned hip%s — and asks for the joint angle%s that best explain <em>all</em> the measured markers at once. It is a nonlinear least-squares problem in \(%s\):</p>
\[\hat{\v{q}} = \arg\min_{\v{q}} E(\v{q}), \qquad E(\v{q}) = \sum_{i=1}^{%d} \big\| \v{m}^{A}_i - \hat{\v{r}}^{A}_i(\v{q}) \big\|^2, \tag{9.1}\]
<p>where \(\hat{\v{r}}^{A}_i(\v{q})\) is the forward model (2.1)%s evaluated at \(\v{q}\): where marker \(i\) <em>would</em> be if the joint angles were \(\v{q}\). The constraints are never written down as constraints; they are satisfied automatically because the only thing the estimator can vary is \(\v{q}\).</p>
<h3>Step A — the model markers and their Jacobian</h3>
<p>(9.1) cannot be solved in one shot, because the model markers depend on the angles through sines and cosines. The standard way to minimise a sum of squares like this is the <em class="term">Gauss–Newton method</em>: guess \(\v{q}\), pretend the model is linear near that guess, solve the resulting linear least-squares problem for a correction, apply it, and repeat until the correction is negligible. It needs \(\hat{\v{r}}^{A}_i(\v{q})\) and its derivative with respect to each joint angle. The one derivative rule required is that of a rotated vector with respect to its angle,</p>
\[\frac{\partial}{\partial \varphi}\,\R(\varphi)\,\v{l} = \R\!\left(\varphi + \tfrac{\pi}{2}\right)\v{l}, \tag{9.2}\]
<p>i.e. the same vector turned a quarter turn — which is why the code rotates by <code>ps.p1 + Math.PI/2</code>. With \(\partial\varphi_1/\partial\theta_1 = 1\)%s, the Jacobian rows are:</p>
""" % (
        (" (three per link, six in all)" if leg else " (three of them)"),
        ("the thigh's is pinned at the hip, and the shank's is wherever the thigh's far end is, \\(L_1\\) along it" if leg else "the thigh's is pinned at the hip"),
        ("s" if leg else ""), ("are" if leg else "is"), ("s \\(\\theta_1\\) and \\(\\theta_2\\)" if leg else " \\(\\theta_1\\)"), (6 if leg else 3),
        (", the fixed link lengths and the hinge knee" if leg else " and the rigid link"),
        ("s \\(\\v{q} = (\\theta_1, \\theta_2)\\)" if leg else " \\(q = \\theta_1\\)"),
        ("\\v{q}" if leg else "\\theta_1"), 6 if leg else 3,
        ("–(2.2)" if leg else ""),
        (", \\(\\partial\\varphi_2/\\partial\\theta_1 = 1\\) and \\(\\partial\\varphi_2/\\partial\\theta_2 = -1\\) from (1.2)" if leg else ""),
    )
    if leg:
        s += r"""
\[\text{thigh marker: } \quad \frac{\partial \hat{\v{r}}^{A}_i}{\partial \theta_1} = \R\!\left(\varphi_1 + \tfrac{\pi}{2}\right)\v{l}^T_i, \qquad \frac{\partial \hat{\v{r}}^{A}_i}{\partial \theta_2} = \v{0}; \tag{9.3}\]
\[\begin{aligned}
  \text{shank marker: } \quad \frac{\partial \hat{\v{r}}^{A}_i}{\partial \theta_1} &= \R\!\left(\varphi_1 + \tfrac{\pi}{2}\right)\m{L_1\\0} + \R\!\left(\varphi_2 + \tfrac{\pi}{2}\right)\v{l}^S_i, \\
  \frac{\partial \hat{\v{r}}^{A}_i}{\partial \theta_2} &= -\R\!\left(\varphi_2 + \tfrac{\pi}{2}\right)\v{l}^S_i.
\end{aligned} \tag{9.4}\]
<p>The first term of (9.4) is the knee moving with the thigh; the second is the shank marker swinging about the knee. Each \(\v{J}_i\) is a \(2\times 2\) matrix (two coordinates, two angles). Where (9.2) comes from, and how (9.3)–(9.4) follow from it by the chain rule, is worked out in <a class="sec" href="#appB">Appendix B</a>.</p>
"""
    else:
        s += r"""
\[\frac{\partial \hat{\v{r}}^{A}_i}{\partial \theta_1} = \R\!\left(\varphi_1 + \tfrac{\pi}{2}\right)\v{l}^T_i, \tag{9.3}\]
<p>a \(2\times1\) column for each marker. (The code also carries the shank rows of the two-link model; in thigh-only mode they are simply never read.) Where (9.2) comes from, and how (9.3) follows from it, is worked out in <a class="sec" href="#appB">Appendix B</a>.</p>
"""
    s += code(X["model"], "<b>ik.html</b> &middot; Step A: model markers (2.1)–(2.2) and their Jacobians (9.3)–(9.4)")
    s += r"""
<h3>Step B — one Gauss–Newton iteration</h3>
<p>Linearise the model about the current guess \(\v{q}\): \(\hat{\v{r}}^{A}_i(\v{q} + \v{\delta}) \approx \hat{\v{r}}^{A}_i(\v{q}) + \v{J}_i\,\v{\delta}\). With the residuals \(\v{e}_i = \v{m}^{A}_i - \hat{\v{r}}^{A}_i(\v{q})\), the cost (9.1) becomes an ordinary linear least-squares problem in \(\v{\delta}\). Setting its derivative with respect to \(\v{\delta}\) to zero gives a small linear system — the <em class="term">normal equations</em> of least squares — and its solution is the correction:</p>
\[\Big(\sum_i \v{J}_i^\T \v{J}_i\Big)\v{\delta} = \sum_i \v{J}_i^\T \v{e}_i, \qquad \v{q} \leftarrow \v{q} + \v{\delta}. \tag{9.5}\]
"""
    if leg:
        s += r"""
<p>Here \(\sum \v{J}_i^\T\v{J}_i\) is \(2\times2\) and symmetric, so (9.5) is two equations in two unknowns and is solved directly with the usual determinant formula — that is what the <code>det</code>, <code>d1</code>, <code>d2</code> lines do. The loop accumulates the four entries of the matrix and the two of the right-hand side over the six markers, solves, updates, and repeats.</p>
"""
    else:
        s += r"""
<p>With a single unknown, (9.5) is a scalar equation: \(\delta = \big(\sum_i \v{J}_i^\T \v{e}_i\big) / \big(\sum_i \v{J}_i^\T \v{J}_i\big)\) — the variables <code>g</code> and <code>a</code> in the code. The loop accumulates both over the three markers, divides, updates, and repeats.</p>
"""
    s += r"""
<h3>Step C — starting point and stopping</h3>
<p>The iteration starts from the previous frame's answer rather than from scratch (the motion is continuous, so the previous answer is already close — a "warm start"), runs at most six times, and stops early when the update falls below \(10^{-7}\) rad. In practice one or two iterations suffice. The estimated angle%s read directly from \(\hat{\v{q}}\): no wrapping is needed, because \(\v{q}\) is a continuous variable that is nudged, never recomputed from an <code>atan2</code>.</p>
""" % ("s are" if leg else " is")
    s += code(X["cik"], "<b>ik.html</b> &middot; Steps B–C, equation (9.5)")
    s += r"""
<div class="note"><b>What is, and is not, in the fit.</b> Weighted least squares in general carries a weight \(w_i\) per marker (trusted markers count more); the simulation uses \(w_i = 1\). Production tools (OpenSim's inverse kinematics is the common example) solve the same problem with more joints, three dimensions and safeguards on the step size, but the structure is this one. Gauss–Newton and its safeguarded relatives are treated in the texts listed under further reading.</div>
"""

    # ------------------------------------------------------------- 10 compare
    s += H2(10, "compare", "What to expect, and why")
    s += r"""
<p>Set one error source at a time and read the RMS error%s in the readout. The behaviour follows from the models above, not from anything hidden:</p>
<table>
<tr><th>error source</th><th>unconstrained</th><th>constrained</th><th>why</th></tr>
<tr><td>Gaussian noise only</td><td>larger; A1 worse than A2</td><td><b>smallest</b></td><td>Noise is independent and zero-mean. The constrained fit averages it over all %d markers; A2 averages over 3; A1 uses 2 and ignores the third.</td></tr>
<tr><td>wobbling mass only</td><td>about equal</td><td>about equal</td><td>The cluster lags the bone as a near-rigid unit (§5). It looks like bone motion to both methods; there is nothing to average.</td></tr>
<tr><td>skin stretch only</td><td><b>small</b></td><td>larger</td><td>The stretch is systematic in the joint angle, so it never averages out. The constrained model can only move joint angles, so it absorbs the displaced markers into the angle estimate. The unconstrained frame is barely affected because the markers slide <em>along</em> the link, which hardly rotates the \(m_1 m_2\) line.</td></tr>
</table>
<p>The practical conclusion, which the simulation itself demonstrates: constraints clean up noise, not skin. In a real laboratory the noise is well under a millimetre and the artefact is ten or more, so the regime where the constrained fit shines is the one that matters least. Its real advantages are elsewhere — a chain that cannot come apart, tolerance of a missing marker, and output that feeds a musculoskeletal model directly — and its real cost is that a joint the model gets wrong is forced to behave as the model says.</p>
""" % ((" of the %s angle" % J), 6 if leg else 3)

    # ---------------------------------------------------------------- appendix A
    s += '<h2 id="appA"><span class="n">A</span>Appendix: deriving the least-squares pose, (8.2) to (8.4)</h2>\n'
    s += r"""
<p>The problem is: given the template points \(\v{l}_i\) and the measured points \(\v{m}^{A}_i\), \(i = 1,2,3\), find the angle \(\varphi\) and translation \(\v{o}\) that minimise</p>
\[E(\varphi, \v{o}) = \sum_{i=1}^{3} \big\| \v{m}^{A}_i - \R(\varphi)\,\v{l}_i - \v{o} \big\|^2. \tag{A.1}\]
<h3>Step 1 — the translation, for any angle</h3>
<p>Hold \(\varphi\) fixed and differentiate with respect to \(\v{o}\). The derivative of \(\|\v{u}\|^2 = \v{u}^\top\v{u}\) with respect to \(\v{u}\) is \(2\v{u}\), and \(\v{u}_i = \v{m}^{A}_i - \R\v{l}_i - \v{o}\) depends on \(\v{o}\) with a minus sign, so</p>
\[\frac{\partial E}{\partial \v{o}} = -2 \sum_i \big(\v{m}^{A}_i - \R(\varphi)\,\v{l}_i - \v{o}\big) = \v{0}
  \quad\Longrightarrow\quad 3\,\v{o} = \sum_i \v{m}^{A}_i - \R(\varphi)\sum_i \v{l}_i. \tag{A.2}\]
<p>Dividing by 3 and writing \(\bar{\v{m}}^{A} = \tfrac13\sum_i \v{m}^{A}_i\) and \(\bar{\v{l}} = \tfrac13\sum_i \v{l}_i\) for the two centroids,</p>
\[\v{o}^{*}(\varphi) = \bar{\v{m}}^{A} - \R(\varphi)\,\bar{\v{l}}. \tag{A.3}\]
<p>In words: whatever the angle, the best translation is the one that carries the template's centroid onto the measured centroid. (\(E\) is a sum of squares in \(\v{o}\), so this stationary point is its minimum.)</p>
<h3>Step 2 — eliminate the translation</h3>
<p>Put (A.3) back into (A.1). Each term becomes</p>
\[\v{m}^{A}_i - \R\v{l}_i - \bar{\v{m}}^{A} + \R\bar{\v{l}} = \underbrace{(\v{m}^{A}_i - \bar{\v{m}}^{A})}_{\v{b}_i} - \R\,\underbrace{(\v{l}_i - \bar{\v{l}})}_{\v{a}_i}, \tag{A.4}\]
<p>so the centred coordinates of §8 appear by themselves, and the translation is gone. What is left is not \(E\) itself but \(E\) evaluated along the curve on which the translation is already optimal for each angle — a function of the angle alone, which deserves its own name:</p>
\[E^{*}(\varphi) \equiv E\big(\varphi, \v{o}^{*}(\varphi)\big) = \sum_i \| \v{b}_i - \R(\varphi)\,\v{a}_i \|^2. \tag{A.5}\]
<p>Minimising \(E^{*}\) over \(\varphi\) does give the minimum of \(E\) over both unknowns: for any \(\varphi\), no choice of \(\v{o}\) can beat \(\v{o}^{*}(\varphi)\), so the best pair \((\hat\varphi, \hat{\v{o}})\) must lie on that curve, and along it \(E\) is \(E^{*}\).</p>
<p>Expand the square: \(\|\v{b} - \R\v{a}\|^2 = \|\v{b}\|^2 - 2\,\v{b}^\top\R\v{a} + \|\R\v{a}\|^2\). A rotation does not change a length, so \(\|\R\v{a}_i\|^2 = \|\v{a}_i\|^2\). Therefore</p>
\[E^{*}(\varphi) = \underbrace{\sum_i \|\v{b}_i\|^2 + \sum_i \|\v{a}_i\|^2}_{\text{does not depend on } \varphi} \;-\; 2 \sum_i \v{b}_i^\top \R(\varphi)\,\v{a}_i, \tag{A.6}\]
<p>and minimising \(E^{*}\) over \(\varphi\) is the same as <em>maximising</em> \(F(\varphi) = \sum_i \v{b}_i^\top \R(\varphi)\,\v{a}_i\).</p>
<h3>Step 3 — write the angle out</h3>
<p>With \(\R(\varphi) = \m{\cos\varphi & -\sin\varphi \\ \sin\varphi & \cos\varphi}\) and \(\v{a}_i = (a_{ix}, a_{iy})\),</p>
\[\R(\varphi)\,\v{a}_i = \m{a_{ix}\cos\varphi - a_{iy}\sin\varphi \\ a_{ix}\sin\varphi + a_{iy}\cos\varphi},\]
\[\begin{aligned}
  \v{b}_i^\top \R(\varphi)\,\v{a}_i &= b_{ix}(a_{ix}\cos\varphi - a_{iy}\sin\varphi) + b_{iy}(a_{ix}\sin\varphi + a_{iy}\cos\varphi) \\
  &= (a_{ix}b_{ix} + a_{iy}b_{iy})\cos\varphi + (a_{ix}b_{iy} - a_{iy}b_{ix})\sin\varphi.
\end{aligned} \tag{A.7}\]
<p>The first bracket is the dot product \(\v{a}_i\cdot\v{b}_i\); the second is the two-dimensional cross product \(\v{a}_i\times\v{b}_i\) (a scalar in the plane). Summing over the three markers gives exactly (8.3):</p>
\[F(\varphi) = S_c\cos\varphi + S_s\sin\varphi, \qquad S_c = \sum_i \v{a}_i\cdot\v{b}_i, \quad S_s = \sum_i \v{a}_i\times\v{b}_i. \tag{A.8}\]
<h3>Step 4 — maximise over the angle</h3>
<p>Write the pair \((S_c, S_s)\) in polar form, \(S_c = \rho\cos\psi\), \(S_s = \rho\sin\psi\) with \(\rho = \sqrt{S_c^2 + S_s^2}\) and \(\psi = \operatorname{atan2}(S_s, S_c)\). Then by the cosine addition formula</p>
\[F(\varphi) = \rho\,(\cos\psi\cos\varphi + \sin\psi\sin\varphi) = \rho\cos(\varphi - \psi), \tag{A.9}\]
<p>which is largest, equal to \(\rho\), when \(\varphi = \psi\). (Setting \(F'(\varphi) = -S_c\sin\varphi + S_s\cos\varphi = 0\) gives \(\tan\varphi = S_s/S_c\), which has two solutions \(180^\circ\) apart; the \(\operatorname{atan2}\) picks the one where \(F\) is a maximum rather than a minimum.) So</p>
\[\hat{\varphi} = \operatorname{atan2}(S_s,\, S_c), \qquad \hat{\v{o}} = \bar{\v{m}}^{A} - \R(\hat{\varphi})\,\bar{\v{l}}, \tag{A.10}\]
<p>the second line being (A.3) evaluated at the best angle. This is (8.4). Note what made it closed-form: in two dimensions a rotation has a single parameter, so the maximisation in Step 4 is of one sinusoid. In three dimensions Steps 1 and 2 go through unchanged, but a rotation then has three parameters, and the maximisation is solved by factorising the \(3\times3\) matrix \(\sum_i \v{b}_i\v{a}_i^\top\) (the Kabsch algorithm mentioned in §8).</p>
"""

    # ---------------------------------------------------------------- appendix B
    s += '<h2 id="appB"><span class="n">B</span>Appendix: deriving the Jacobians, (9.2) to (9.%s)</h2>\n' % ("4" if leg else "3")
    s += r"""
<p>Gauss–Newton needs the derivative of each model marker position with respect to each joint angle. Every marker position in §2 is a rotated template vector, plus a rotated offset for the shank, so one derivative does all the work: that of a rotated vector with respect to its angle.</p>
<h3>Step 1 — the derivative of a rotated vector, (9.2)</h3>
<p>Take a fixed vector \(\v{l} = (l_x, l_y)\) and rotate it by \(\varphi\):</p>
\[\R(\varphi)\,\v{l} = \m{\cos\varphi & -\sin\varphi \\ \sin\varphi & \cos\varphi}\m{l_x \\ l_y} = \m{l_x\cos\varphi - l_y\sin\varphi \\ l_x\sin\varphi + l_y\cos\varphi}. \tag{B.1}\]
<p>Only \(\varphi\) varies, so differentiate each component (the derivative of \(\cos\) is \(-\sin\), of \(\sin\) is \(\cos\)):</p>
\[\frac{\partial}{\partial\varphi}\,\R(\varphi)\,\v{l} = \m{-l_x\sin\varphi - l_y\cos\varphi \\ \phantom{-}l_x\cos\varphi - l_y\sin\varphi}. \tag{B.2}\]
<p>Now write out \(\R(\varphi + \tfrac{\pi}{2})\,\v{l}\), using \(\cos(\varphi + \tfrac{\pi}{2}) = -\sin\varphi\) and \(\sin(\varphi + \tfrac{\pi}{2}) = \cos\varphi\):</p>
\[\R\!\left(\varphi + \tfrac{\pi}{2}\right)\v{l} = \m{-\sin\varphi & -\cos\varphi \\ \phantom{-}\cos\varphi & -\sin\varphi}\m{l_x \\ l_y} = \m{-l_x\sin\varphi - l_y\cos\varphi \\ \phantom{-}l_x\cos\varphi - l_y\sin\varphi}. \tag{B.3}\]
<p>(B.2) and (B.3) are the same vector, which is (9.2). The picture behind it: as \(\varphi\) increases, the tip of \(\R(\varphi)\v{l}\) moves round a circle of radius \(\|\v{l}\|\); its velocity is tangent to that circle, i.e. the vector itself turned a quarter-turn, with the same length. Equivalently \(\frac{\partial}{\partial\varphi}\R(\varphi) = \R(\varphi)\,\v{S}\) with \(\v{S} = \m{0 & -1 \\ 1 & 0}\), the quarter-turn matrix, which is why the code can take any derivative by calling <code>rot</code> with the angle shifted by <code>Math.PI/2</code>.</p>
<h3>Step 2 — the thigh markers, (9.3)</h3>
<p>From (2.1), \(\hat{\v{r}}^{A}_i(\v{q}) = \R(\varphi_1)\,\v{l}^{T}_i\) with \(\varphi_1 = -\tfrac{\pi}{2} + \theta_1\) from (1.2). The angle depends on the joint angle through \(\varphi_1\), so by the chain rule and \(\partial\varphi_1/\partial\theta_1 = 1\),</p>
\[\frac{\partial \hat{\v{r}}^{A}_i}{\partial\theta_1} = \frac{\partial}{\partial\varphi_1}\big(\R(\varphi_1)\,\v{l}^{T}_i\big)\cdot\frac{\partial\varphi_1}{\partial\theta_1} = \R\!\left(\varphi_1 + \tfrac{\pi}{2}\right)\v{l}^{T}_i \cdot 1. \tag{B.4}\]
"""
    if leg:
        s += r"""
<p>A thigh marker does not involve \(\theta_2\) at all, so \(\partial\hat{\v{r}}^{A}_i/\partial\theta_2 = \v{0}\). Together these are (9.3).</p>
<h3>Step 3 — the shank markers, (9.4)</h3>
<p>From (2.2), a shank marker is the knee plus a rotated template vector,</p>
\[\hat{\v{r}}^{A}_i(\v{q}) = \underbrace{\R(\varphi_1)\m{L_1 \\ 0}}_{\text{the knee}} + \R(\varphi_2)\,\v{l}^{S}_i, \qquad \varphi_2 = \varphi_1 - \theta_2 = -\tfrac{\pi}{2} + \theta_1 - \theta_2. \tag{B.5}\]
<p>Both angles depend on the joint angles, and the two partial derivatives of \(\varphi_2\) are what carry the signs:</p>
\[\frac{\partial\varphi_1}{\partial\theta_1} = 1, \qquad \frac{\partial\varphi_2}{\partial\theta_1} = 1, \qquad \frac{\partial\varphi_1}{\partial\theta_2} = 0, \qquad \frac{\partial\varphi_2}{\partial\theta_2} = -1. \tag{B.6}\]
<p><em>Derivative with respect to \(\theta_1\).</em> Both terms of (B.5) move, because turning the hip turns the knee's position and the shank's direction together. Apply (9.2) to each, with the chain-rule factors from (B.6):</p>
\[\frac{\partial \hat{\v{r}}^{A}_i}{\partial\theta_1} = \R\!\left(\varphi_1 + \tfrac{\pi}{2}\right)\m{L_1 \\ 0}\cdot 1 + \R\!\left(\varphi_2 + \tfrac{\pi}{2}\right)\v{l}^{S}_i \cdot 1. \tag{B.7}\]
<p><em>Derivative with respect to \(\theta_2\).</em> The knee does not move when only the knee angle changes, so the first term of (B.5) gives nothing; the second gives</p>
\[\frac{\partial \hat{\v{r}}^{A}_i}{\partial\theta_2} = \R\!\left(\varphi_2 + \tfrac{\pi}{2}\right)\v{l}^{S}_i \cdot (-1) = -\R\!\left(\varphi_2 + \tfrac{\pi}{2}\right)\v{l}^{S}_i. \tag{B.8}\]
<p>(B.7) and (B.8) are (9.4). The minus sign is the sign convention of (1.2): increasing knee flexion turns the shank the <em>other</em> way from increasing hip flexion.</p>
<h3>Step 4 — reading the code against the result</h3>
<p>In <code>modelMarkers</code>: <code>dr</code> is (B.4); for the shank, <code>dk</code> is the first term of (B.7), <code>ds</code> is the second term, their sum is the \(\theta_1\) column and <code>[-ds[0], -ds[1]]</code> is the \(\theta_2\) column, (B.8). Every call is <code>rot</code> with the angle shifted by <code>Math.PI/2</code>, which is Step 1 applied three times.</p>
"""
    else:
        s += r"""
<p>That is (9.3): for each marker a single \(2\times1\) column, the template vector turned a quarter-turn. In <code>modelMarkers</code> it is the variable <code>dr</code> — <code>rot</code> called with the angle shifted by <code>Math.PI/2</code>, which is Step 1 applied directly. (The shank rows that the same function builds, with their second column for a knee angle, are the two-link version; see the two-link notes, Appendix B.)</p>
"""

    # ---------------------------------------------------------------- 11 refs
    s += H2(11, "refs", "Sources and further reading")
    s += r"""
<p>The claims in these notes rest on the derivations and the simulation above. The list below is divided into <b>sources</b> — works read and relied on — and <b>further reading</b>, pointers to where a topic is treated in depth, offered without any claim about what they conclude.</p>
%s
<h3>Further reading</h3>
<ol class="refs">
<li>Dumas, R. &amp; Jacquelin, E. (2017). Stiffness of a wobbling mass models analysed by a smooth orthogonal decomposition of the skin movement relative to the underlying bone. <i>Journal of Biomechanics</i>, 62, 47–52. — on wobbling-mass models of soft-tissue artefact (§5).</li>
<li>Leardini, A., Chiari, L., Della Croce, U. &amp; Cappozzo, A. (2005). Human movement analysis using stereophotogrammetry. Part 3: Soft tissue artifact assessment and compensation. <i>Gait &amp; Posture</i>, 21, 212–225. — a review of soft-tissue artefact (§4–5).</li>
<li>Cappello, A., Cappozzo, A., La Palombara, P. F., Lucchetti, L. &amp; Leardini, A. (1997). Multiple anatomical landmark calibration for optimal bone pose estimation. <i>Human Movement Science</i>, 16, 259–274. — on artefact compensation (§4).</li>
<li>Camomilla, V., Cereatti, A., Cheze, L. &amp; Cappozzo, A. (2013). A hip joint kinematics driven model for the generation of realistic thigh soft tissue artefacts. <i>Journal of Biomechanics</i>, 46, 625–630. — on modelling thigh artefact (§4).</li>
<li>Kabsch, W. (1976). A solution for the best rotation to relate two sets of vectors. <i>Acta Crystallographica A</i>, 32, 922–923; and Horn, B. K. P. (1987). Closed-form solution of absolute orientation using unit quaternions. <i>Journal of the Optical Society of America A</i>, 4, 629–642. — on the three-dimensional rigid fit (§8, Appendix A).</li>
<li>Lu, T.-W. &amp; O'Connor, J. J. (1999). Bone position estimation from skin marker co-ordinates using global optimisation with joint constraints. <i>Journal of Biomechanics</i>, 32, 129–134. — on constrained inverse kinematics (§9).</li>
<li>Andersen, M. S., Benoit, D. L., Damsgaard, M., Ramsey, D. K. &amp; Rasmussen, J. (2010). Do kinematic models reduce the effects of soft tissue artefacts in skin marker-based motion analysis? An in vivo study of knee kinematics. <i>Journal of Biomechanics</i>, 43, 268–273. — on joint constraints and soft-tissue artefact (§10).</li>
<li>Press, W. H., Teukolsky, S. A., Vetterling, W. T. &amp; Flannery, B. P. (2007). <i>Numerical Recipes: The Art of Scientific Computing</i>, 3rd ed. Cambridge University Press. — on random numbers, nonlinear least squares and integrating differential equations (§5, §6, §9). The book's site is <a href="https://numerical.recipes">numerical.recipes</a>.</li>
<li>Nocedal, J. &amp; Wright, S. J. (2006). <i>Numerical Optimization</i>, 2nd ed. Springer. — on least-squares methods (§9).</li>
</ol>
""" % SOURCES_HTML
    s += FOOT % dict(footer=nc.footer(), prevnext=nc.prevnext("01-kinematics-kinetics/ik-notes-%s.html" % mode))
    # every section reference becomes a link to its heading; a range links to its first section
    ids = {}
    n = 0
    for a, _ in toc:
        if a in ("appA", "appB"): continue
        n += 1; ids[n] = a
    def link(m):
        n = int(m.group(1))
        return '<a class="sec" href="#%s">%s</a>' % (ids[n], m.group(0)) if n in ids else m.group(0)
    s = re.sub(r"§(\d+)(?:–\d+)?", link, s)
    return s

nc.install_fonts(HERE)
(HERE / "ik-notes-thigh.html").write_text(page("thigh"))
(HERE / "ik-notes-leg.html").write_text(page("leg"))
print("wrote ik-notes-thigh.html, ik-notes-leg.html")
