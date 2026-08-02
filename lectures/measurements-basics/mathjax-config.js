window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    processEscapes: true,
    processRefs: true,
    processEnvironments: true
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
