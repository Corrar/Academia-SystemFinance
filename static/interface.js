// Interações da interface (padrões do shadcn/ui com movimento no estilo Apple):
// menu em tela cheia (Drawer com arrastar para fechar), busca do menu,
// confirmações (AlertDialog), mensagens (Sonner) e números que contam até o valor.
(function () {
  var menosMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // fecha um <dialog> com a animação de saída (classe .fechando no CSS)
  function fecharComAnimacao(dialogo, depois) {
    if (!dialogo.open || dialogo.classList.contains("fechando")) return;
    function fim() {
      dialogo.classList.remove("fechando");
      dialogo.style.transform = "";
      dialogo.style.removeProperty("--arrasto");
      dialogo.close();
      if (depois) depois();
    }
    if (menosMovimento) return fim();
    dialogo.classList.add("fechando");
    dialogo.addEventListener("animationend", function aoTerminar(e) {
      if (e.target !== dialogo) return;
      dialogo.removeEventListener("animationend", aoTerminar);
      fim();
    });
  }

  // ---------------- menu em tela cheia ----------------
  var folha = document.getElementById("mais");
  if (folha && folha.showModal) {
    var campo = folha.querySelector("[data-buscar-menu]");
    document.querySelectorAll("[data-abrir-mais]").forEach(function (b) {
      b.addEventListener("click", function () { folha.showModal(); folha.scrollTop = 0; });
    });
    folha.addEventListener("click", function (e) {
      if (e.target === folha || e.target.closest("[data-fechar]")) fecharComAnimacao(folha);
    });
    folha.addEventListener("cancel", function (e) { e.preventDefault(); fecharComAnimacao(folha); });
    folha.addEventListener("close", function () {
      if (campo && campo.value) { campo.value = ""; filtrar(""); }
    });

    // arrastar a alça (topo da folha) para baixo fecha o menu, como no iOS
    var topo = folha.querySelector(".folha-topo");
    var inicioY = null, inicioT = 0, deslocamento = 0;
    topo.addEventListener("pointerdown", function (e) {
      if (e.target.closest("button")) return;
      inicioY = e.clientY; inicioT = e.timeStamp; deslocamento = 0;
      topo.setPointerCapture(e.pointerId);
      folha.classList.add("arrastando");
    });
    topo.addEventListener("pointermove", function (e) {
      if (inicioY === null) return;
      deslocamento = Math.max(0, e.clientY - inicioY);
      folha.style.transform = "translateY(" + deslocamento + "px)";
    });
    function soltar(e) {
      if (inicioY === null) return;
      var velocidade = deslocamento / Math.max(1, e.timeStamp - inicioT);
      inicioY = null;
      folha.classList.remove("arrastando");
      if (deslocamento > 110 || velocidade > .6) {
        folha.style.setProperty("--arrasto", deslocamento + "px");
        fecharComAnimacao(folha);
      } else if (deslocamento > 0) {
        folha.classList.add("voltando");
        folha.style.transform = "";
        folha.addEventListener("transitionend", function () { folha.classList.remove("voltando"); }, { once: true });
      }
    }
    topo.addEventListener("pointerup", soltar);
    topo.addEventListener("pointercancel", soltar);

    // busca: filtra os itens do menu e oferece procurar o termo nos inscritos
    var semAcento = function (t) { return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); };
    var buscaAluno = folha.querySelector("[data-busca-aluno]");
    var vazio = folha.querySelector("[data-menu-vazio]");
    var filtrar = function (termo) {
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
    };
    if (campo) campo.addEventListener("input", function () { filtrar(campo.value); });
  }

  // ---------------- sidebar lateral (desktop) ----------------
  var raiz = document.documentElement;
  var lateral = document.querySelector(".lateral");
  if (lateral) {
    var botaoLateral = lateral.querySelector("[data-recolher-lateral]");
    var busca = document.getElementById("busca-rapida");
    var recolhida = function () { return raiz.dataset.lateral === "recolhida"; };
    var rotular = function () {
      var r = recolhida();
      botaoLateral.setAttribute("aria-label", r ? "Abrir menu lateral" : "Recolher menu lateral");
      botaoLateral.setAttribute("title", (r ? "Abrir" : "Recolher") + " menu lateral (Ctrl+B)");
      botaoLateral.setAttribute("aria-expanded", r ? "false" : "true");
    };
    var alternar = function (abrir) {
      raiz.dataset.lateral = (abrir === undefined ? recolhida() : abrir) ? "aberta" : "recolhida";
      try { localStorage.setItem("lateral", raiz.dataset.lateral); } catch (e) {}
      rotular();
    };
    rotular();
    botaoLateral.addEventListener("click", function () { alternar(); });
    // na versão recolhida, tocar na lupa abre a sidebar e já foca a busca
    lateral.querySelector(".lateral-busca label").addEventListener("click", function (e) {
      if (recolhida()) { e.preventDefault(); alternar(true); setTimeout(function () { busca.focus(); }, 60); }
    });
    document.addEventListener("keydown", function (e) {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
      var tecla = e.key.toLowerCase();
      if ((tecla !== "k" && tecla !== "b") || getComputedStyle(lateral).display === "none") return;
      e.preventDefault();
      if (tecla === "b") return alternar();
      if (recolhida()) alternar(true);
      setTimeout(function () { busca.focus(); busca.select(); }, 60);
    });
    // o menu do usuário fecha ao clicar fora ou com Esc
    var usuario = lateral.querySelector(".lateral-usuario");
    document.addEventListener("click", function (e) { if (usuario.open && !usuario.contains(e.target)) usuario.open = false; });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && usuario.open) { usuario.open = false; usuario.querySelector("summary").focus(); } });
  }

  // ---------------- fila de envio: abrir o WhatsApp/e-mail marca como enviado ----------------
  document.querySelectorAll("[data-enviar-fila]").forEach(function (link) {
    link.addEventListener("click", function () {
      var cartao = link.closest("[data-item-fila]");
      var dados = new FormData();
      dados.append("csrf", link.dataset.csrf);
      fetch(link.dataset.enviarFila, { method: "POST", body: dados, headers: { "X-Requested-With": "fetch" }, credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (r) {
          if (!r || !cartao) return;
          cartao.classList.add("enviado");
          cartao.querySelector("[data-estado]").textContent = "Enviado ✓";
          document.querySelectorAll("[data-contador-fila]").forEach(function (c) { c.textContent = r.restantes; });
        });
    });
  });

  // ---------------- cadastro rápido: Enter pula de campo, telefone formatado, contador ----------------
  var lote = document.getElementById("lote");
  if (lote) {
    var campos = function () { return Array.prototype.slice.call(lote.querySelectorAll(".fichas input, .fichas select")); };
    lote.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" || !e.target.closest(".fichas")) return;
      e.preventDefault();
      var lista = campos(), i = lista.indexOf(e.target) + (e.shiftKey ? -1 : 1);
      if (lista[i]) lista[i].focus();
    });
    var formatar = function (campo) {
      var d = campo.value.replace(/\D/g, "");
      if (d.length === 13 && d.indexOf("55") === 0) d = d.slice(2);
      if (d.length === 11) campo.value = "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7);
      else if (d.length === 10) campo.value = "(" + d.slice(0, 2) + ") " + d.slice(2, 6) + "-" + d.slice(6);
    };
    var resumo = lote.querySelector("[data-resumo-lote]");
    var contar = function () {
      var n = lote.querySelectorAll(".fichas input[name=nome]");
      var cheias = Array.prototype.filter.call(n, function (c) { return c.value.trim(); }).length;
      if (resumo) resumo.textContent = cheias + " ficha(s) preenchida(s)";
    };
    lote.addEventListener("focusout", function (e) { if (e.target.matches("[data-telefone]")) formatar(e.target); });
    lote.addEventListener("input", function (e) { if (e.target.name === "nome") contar(); });
  }
  document.querySelectorAll(".arquivo-zona input[type=file]").forEach(function (entrada) {
    entrada.addEventListener("change", function () {
      var zona = entrada.closest(".arquivo-zona");
      if (entrada.files[0]) { zona.classList.add("com-arquivo"); zona.querySelector("strong").textContent = entrada.files[0].name; }
    });
  });

  // ---------------- confirmações (AlertDialog) ----------------
  // <form data-confirmar="texto" data-titulo="..." data-ok="Rótulo" data-perigo>
  var alerta = document.getElementById("confirmar");
  var pendente = null;
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.matches("[data-confirmar]")) return;
    if (form.dataset.confirmado) { delete form.dataset.confirmado; return; }
    e.preventDefault();
    var botao = e.submitter || null;
    if (!alerta || !alerta.showModal) {
      if (window.confirm(form.dataset.confirmar)) { form.dataset.confirmado = "1"; form.requestSubmit(botao); }
      return;
    }
    pendente = { form: form, botao: botao };
    alerta.querySelector("#confirmar-titulo").textContent = form.dataset.titulo || "Tem certeza?";
    alerta.querySelector("#confirmar-texto").textContent = form.dataset.confirmar;
    var ok = alerta.querySelector("[data-confirmar-ok]");
    ok.textContent = form.dataset.ok || "Confirmar";
    ok.classList.toggle("destrutivo", "perigo" in form.dataset);
    ok.classList.toggle("primario", !("perigo" in form.dataset));
    alerta.showModal();
  });
  if (alerta && alerta.showModal) {
    alerta.querySelector("[data-cancelar]").addEventListener("click", function () { pendente = null; fecharComAnimacao(alerta); });
    alerta.addEventListener("cancel", function (e) { e.preventDefault(); pendente = null; fecharComAnimacao(alerta); });
    alerta.addEventListener("click", function (e) { if (e.target === alerta) { pendente = null; fecharComAnimacao(alerta); } });
    alerta.querySelector("[data-confirmar-ok]").addEventListener("click", function () {
      var p = pendente; pendente = null;
      fecharComAnimacao(alerta, function () {
        if (!p) return;
        p.form.dataset.confirmado = "1";
        p.form.requestSubmit(p.botao);
      });
    });
  }

  // ---------------- mensagens (Sonner) ----------------
  function dispensar(toast) {
    if (toast.classList.contains("saindo")) return;
    if (menosMovimento) return toast.remove();
    toast.classList.add("saindo");
    toast.addEventListener("animationend", function () { toast.remove(); }, { once: true });
  }
  document.querySelectorAll(".toast").forEach(function (toast) {
    var botao = toast.querySelector("[data-fechar-toast]");
    if (botao) botao.addEventListener("click", function () { dispensar(toast); });
    if (toast.hasAttribute("data-sumir")) {
      var espera = setTimeout(function () { dispensar(toast); }, 5000);
      toast.addEventListener("mouseenter", function () { clearTimeout(espera); });
      toast.addEventListener("focusin", function () { clearTimeout(espera); });
    }
  });

  // ---------------- números que contam até o valor (indicadores) ----------------
  if (!menosMovimento) {
    var moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
    document.querySelectorAll("[data-contar]").forEach(function (el) {
      var final = el.textContent.trim();
      var ehMoeda = final.indexOf("R$") !== -1;
      var alvo = parseFloat(final.replace(/[^\d,-]/g, "").replace(",", "."));
      if (!isFinite(alvo) || alvo === 0) return;
      el.textContent = "";
      var visivel = document.createElement("span");
      visivel.setAttribute("aria-hidden", "true");
      var leitor = document.createElement("span");
      leitor.className = "sr-only";
      leitor.textContent = final;
      el.append(visivel, leitor);
      var inicio = null, duracao = 1100;
      function passo(t) {
        if (inicio === null) inicio = t;
        var p = Math.min(1, (t - inicio) / duracao);
        var suave = 1 - Math.pow(1 - p, 4); // desacelera no fim, como os contadores do iOS
        var v = alvo * suave;
        visivel.textContent = ehMoeda ? moeda.format(v) : Math.round(v).toLocaleString("pt-BR");
        if (p < 1) requestAnimationFrame(passo); else el.textContent = final;
      }
      requestAnimationFrame(passo);
    });
  }
})();
