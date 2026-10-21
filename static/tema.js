// Modo claro/escuro e painel "Mais" da barra de abas (celular).
(function () {
  var raiz = document.documentElement;
  var escuroNoSistema = window.matchMedia("(prefers-color-scheme: dark)");

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
    if (cor) cor.setAttribute("content", escuro ? "#000000" : "#f5f5f7");
  }
  document.querySelectorAll("[data-alternar-tema]").forEach(function (b) {
    b.addEventListener("click", function () {
      var novo = estaEscuro() ? "claro" : "escuro";
      raiz.dataset.tema = novo;
      try { localStorage.setItem("tema", novo); } catch (e) {}
      atualizarBotoes();
    });
  });
  escuroNoSistema.addEventListener("change", atualizarBotoes);
  atualizarBotoes();

  // painel "Mais"
  var folha = document.getElementById("mais");
  if (folha && folha.showModal) {
    document.querySelectorAll("[data-abrir-mais]").forEach(function (b) {
      b.addEventListener("click", function () { folha.showModal(); });
    });
    folha.addEventListener("click", function (e) {
      if (e.target === folha || e.target.closest("[data-fechar]")) folha.close();
    });
  }
})();
