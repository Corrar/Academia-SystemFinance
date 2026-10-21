// Service worker do app instalável (PWA). Guarda só arquivos estáticos (visual, ícones e scripts)
// e a página "sem internet". As telas com dados dos alunos nunca ficam guardadas no aparelho.
const CACHE = "academia-__VERSAO__";
const ESTATICOS = [
  "/offline",
  "/static/style.css",
  "/static/fontes.css",
  "/static/tema.js",
  "/static/interface.js",
  "/static/logo-horizontal.svg",
  "/static/favicon.svg",
  "/static/icone-192.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ESTATICOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  // versão nova do sistema: apaga o cache antigo
  e.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const pedido = e.request;
  if (pedido.method !== "GET") return;
  const url = new URL(pedido.url);
  if (url.origin !== location.origin) return;

  if (pedido.mode === "navigate") {
    // páginas: sempre da internet; sem conexão, mostra o aviso
    e.respondWith(fetch(pedido).catch(() => caches.match("/offline")));
    return;
  }
  if (url.pathname.startsWith("/static/")) {
    // visual e scripts: responde do cache e atualiza em segundo plano
    e.respondWith(
      caches.open(CACHE).then((c) =>
        c.match(pedido).then((guardado) => {
          const rede = fetch(pedido).then((r) => { if (r.ok) c.put(pedido, r.clone()); return r; }).catch(() => guardado);
          return guardado || rede;
        })
      )
    );
  }
});
