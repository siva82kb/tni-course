window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    processEscapes: true,
    processRefs: true,
    processEnvironments: true,
    macros: {
      // \v{r}      -> bold vector            \mathbf{r}
      v: ['{\\mathbf{#1}}', 1],
      // \m{3.2}    -> column matrix          [3.2]
      m: ['{\\begin{bmatrix}#1\\end{bmatrix}}', 1],
      // \norm{a}   -> 2-norm                 ||a||
      norm: ['{\\lVert \\mathbf{#1} \\rVert}', 1],
      // \ip{a}{b}  -> inner product          a^T b
      ip: ['{\\mathbf{#1}^{\\top}\\mathbf{#2}}', 2]
    }
  },
  chtml: {
    font: 'mathjax-newcm'
  },
  startup: {
    ready: () => {
      console.log('MathJax is loaded and ready with font: mathjax-newcm (New Computer Modern — LaTeX look)');
      MathJax.startup.defaultReady();
    }
  }
};
