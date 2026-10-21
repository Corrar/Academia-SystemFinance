// Modo claro/escuro. A troca usa View Transitions: o tema novo se espalha
// em círculo a partir do botão (sem animação se o aparelho pede menos movimento).
(function () {
  var raiz = document.documentElement;
  var escuroNoSistema = window.matchMedia("(prefers-color-scheme: dark)");
  var menosMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");

  function estaEscuro() {
    return raiz.dataset.tema ? raiz.dataset.tema === "escuro" : escuroNoSistema.matches;
  }
  function atualizarBotoes() {
    var escuro = estaEscuro();
    document.querySelectorAll("[data-alternar-tema]").forEach(function (b) {
      var rotulo = escuro ? "Usar modo claro" : "Usar modo escuro";
      b.setAttribute("aria-label", rotulo);
      b.setAttribute("title", rotulo);
      var texto = b.querySelector("[data-rotulo-tema]");
      if (texto) texto.textContent = rotulo;
    });
    var cor = document.querySelector('meta[name="theme-color"]:not([media])');
    if (cor) cor.setAttribute("content", escuro ? "#09090b" : "#ffffff");
  }
  function aplicar(novo) {
    raiz.dataset.tema = novo;
    try { localStorage.setItem("tema", novo); } catch (e) {}
    atualizarBotoes();
  }

  document.querySelectorAll("[data-alternar-tema]").forEach(function (b) {
    b.addEventListener("click", function (ev) {
      var novo = estaEscuro() ? "claro" : "escuro";
      if (!document.startViewTransition || menosMovimento.matches) return aplicar(novo);

      var caixa = b.getBoundingClientRect();
      var x = ev.clientX || caixa.left + caixa.width / 2;
      var y = ev.clientY || caixa.top + caixa.height / 2;
      var raio = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      raiz.classList.add("trocando-tema");
      var transicao = document.startViewTransition(function () { aplicar(novo); });
      transicao.ready.then(function () {
        raiz.animate(
          { clipPath: ["circle(0px at " + x + "px " + y + "px)", "circle(" + raio + "px at " + x + "px " + y + "px)"] },
          { duration: 520, easing: "cubic-bezier(.32, .72, 0, 1)", pseudoElement: "::view-transition-new(root)" }
        );
      });
      transicao.finished.finally(function () { raiz.classList.remove("trocando-tema"); });
    });
  });
  escuroNoSistema.addEventListener("change", atualizarBotoes);
  atualizarBotoes();
})();
