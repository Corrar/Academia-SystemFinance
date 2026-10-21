// Modo claro/escuro e menu em tela cheia da barra de abas (celular).
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

  // menu em tela cheia
  var folha = document.getElementById("mais");
  if (folha && folha.showModal) {
    var campo = folha.querySelector("[data-buscar-menu]");
    document.querySelectorAll("[data-abrir-mais]").forEach(function (b) {
      b.addEventListener("click", function () { folha.showModal(); folha.scrollTop = 0; });
    });
    folha.addEventListener("click", function (e) {
      if (e.target === folha || e.target.closest("[data-fechar]")) folha.close();
    });
    folha.addEventListener("close", function () {
      if (campo && campo.value) { campo.value = ""; filtrar(""); }
    });

    // busca: filtra os itens do menu e oferece procurar o termo nos inscritos
    var semAcento = function (t) { return t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); };
    var buscaAluno = folha.querySelector("[data-busca-aluno]");
    var vazio = folha.querySelector("[data-menu-vazio]");
    function filtrar(termo) {
      var t = semAcento(termo.trim());
      var achou = 0;
      folha.querySelectorAll(".menu-secao").forEach(function (secao) {
        var visiveis = 0;
        secao.querySelectorAll("[data-item]").forEach(function (item) {
          var mostra = !t || semAcento(item.textContent).indexOf(t) !== -1;
          item.hidden = !mostra;
          if (mostra) visiveis++;
        });
        secao.hidden = visiveis === 0;
        achou += visiveis;
      });
      if (buscaAluno) {
        buscaAluno.hidden = !t;
        buscaAluno.href = buscaAluno.href.split("?")[0] + "?q=" + encodeURIComponent(termo.trim());
        buscaAluno.querySelector("[data-termo]").textContent = termo.trim();
      }
      if (vazio) vazio.hidden = !t || achou > 0;
    }
    if (campo) campo.addEventListener("input", function () { filtrar(campo.value); });
  }
})();
