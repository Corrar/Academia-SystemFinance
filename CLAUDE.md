# Corpu's Academia — cobrança de mensalidades

Memória do projeto para o Claude Code. Leia isto antes de abrir arquivos: aqui está o mapa do
sistema, os comandos e as armadilhas já conhecidas. Para detalhes de código, use o grafo do
Graphify (seção no fim) em vez de reler os arquivos inteiros.

- O usuário escreve em português: responda sempre em português.
- Produção: https://academia-systemfinance.vercel.app (deploy automático a cada push na `main`).
- Repositório: github.com/Corrar/Academia-SystemFinance

## O que o sistema faz

Painel administrativo (um único usuário admin) para controlar os mensalistas de uma academia:

- cadastro de inscritos e consulta da validade do plano;
- dashboard com quem venceu há `DIAS_INADIMPLENCIA` (10) dias ou mais e não pagou;
- cadastro rápido das fichas em papel (várias de uma vez, colar do Excel, importar .xlsx/.csv) e filtros de busca;
- fila de envio (modo manual por wa.me/mailto, padrão), aviso de reajuste da mensalidade e comprovante de pagamento;
- avisos de vencimento por e-mail (SMTP) e WhatsApp (Z-API, Evolution, Meta Cloud ou Twilio);
- quantidade de mensalistas e faturamento do mês.

## Stack

Python 3.12, Flask 3, Jinja2, sem framework de front (CSS e JS puros). Banco SQLite no
desenvolvimento e Postgres (Neon, via psycopg 3) em produção. Sem ORM: SQL escrito à mão.

## Mapa dos arquivos

| Arquivo | Papel |
| --- | --- |
| `config.py` | Lê o ambiente (tem um carregador de `.env` próprio). Fuso `America/Sao_Paulo` via `time.tzset()`. Todas as constantes de regra de negócio. |
| `db.py` | Esquema, migrações, camada de compatibilidade SQLite/Postgres e todas as consultas. `_enriquecer()` calcula `dias`, `status` e `ciclo_pct` de cada aluno. |
| `app.py` | Rotas Flask, login, CSRF, cabeçalhos de segurança, filtros Jinja (`moeda`, `data_br`, `mes_curto`). |
| `cobranca.py` | `executar_cobranca()`: decide quem recebe aviso hoje. Agendador em thread só fora da Vercel. |
| `notificacoes.py` | Monta mensagens (texto e HTML) e envia por e-mail ou WhatsApp. Registra tudo em `notificacoes`. |
| `ajustes.py` | Configurações editáveis na tela (tabela `sistema`), com fallback para variáveis de ambiente. Segredos nunca voltam para o formulário. |
| `icones.py` | Ícones Lucide em SVG inline (`icone('nome', tamanho)`). |
| `importacao.py` | Cadastro rápido: lê texto colado do Excel, CSV e XLSX (`openpyxl`), reconhece cabeçalhos, datas BR/ISO/série do Excel e planos (nome ou valor); `validar()` aponta erros por ficha e duplicados (telefone/e-mail/CPF). |
| `pix.py` | PIX copia e cola (BR Code EMV, CRC16) e QR em SVG/PNG (`segno`); `normalizar_chave` (CPF válido, CNPJ, +55 telefone, e-mail, EVP). |
| `integracoes.py` | Agenda iCal (`gerar_ics`, token em `sistema.agenda_token`), CNPJ/CEP pela BrasilAPI, resumo diário (`enviar_resumo`, 1x por dia) e `backup()` sem segredos. |
| `versao.py` | `VERSAO` (arquivo `VERSION`), `COMMIT` (`VERCEL_GIT_COMMIT_SHA`), `historico()` do `CHANGELOG.md`; CLI `python versao.py notas X` usada no workflow. |
| `seed.py` | Popula 30 alunos fictícios para demonstração. |
| `templates/` | `base.html` (sidebar do desktop, cabeçalho e barra de abas do celular, menu em tela cheia `#mais`, AlertDialog), `alunos_lote.html` (cadastro rápido), `fila.html`, `reajustes.html`, `email_mensagem.html` (e-mail genérico), `_head.html`, `_componentes.html` e `legal/`. |
| `static/style.css` | Todo o visual: tokens e receitas do shadcn/ui em CSS puro, animações e View Transitions. |
| `static/tema.js` | Alterna claro/escuro (localStorage), com transição em círculo a partir do botão. |
| `static/interface.js` | Menu em tela cheia (Drawer com arrastar para fechar), busca do menu, sidebar (recolher, Ctrl+K/Ctrl+B), fila de envio (marcar ao abrir), cadastro rápido (Enter pula campo, telefone), confirmações (`data-confirmar` → AlertDialog), mensagens (Sonner) e contadores (`data-contar`). |
| `vercel.json` | Cron diário `0 12 * * *` (9h em Brasília) → `/api/cron/cobranca`. |
| `docs/CONFORMIDADE.md` | O que foi feito para LGPD, acessibilidade e riscos jurídicos. |

Tabelas: `planos`, `alunos`, `pagamentos`, `notificacoes` (com `assunto`), `reajustes`, `sistema` (chave/valor) e `tentativas_login`.

## Regras de negócio

- Um pagamento grava `validade_anterior` e `nova_validade` e move a `data_vencimento` do aluno.
  Para estornar, apaga o pagamento e, se era o último, devolve a validade anterior.
- Os avisos saem nos dias de `DIAS_AVISO` (padrão `-3,0,3,10`, relativos ao vencimento). Depois
  do último dia, o inadimplente recebe um lembrete a cada 7 dias, no máximo
  `MAX_LEMBRETES_SEMANAIS` (4) vezes.
- A chave `vencimento:+dia` impede aviso duplicado no mesmo ciclo. Reajuste usa `reajuste:<id>` e comprovante
  `comprovante:<data>:<validade>`.
- Envio: cada canal tem provedor (`ajustes.provedor_email()`, `ajustes.whatsapp()["provedor"]`). Padrão **manual**:
  o aviso é gravado com status `pendente` e aparece na Fila de envio (`/avisos/fila`); o link `notificacoes.link_envio()`
  abre `wa.me`/`mailto` e um `fetch` em `/avisos/<id>/marcar` marca como `enviado`. `ENTREGUES` = enviado, simulado,
  pendente (não gera de novo). E-mail: manual | smtp | resend | simulado. WhatsApp: manual | zapi | evolution | meta | twilio | simulado.
  A CSP tem `form-action 'self'`: nunca redirecione um POST para wa.me (o Chrome bloqueia); use link + fetch.
- Reajuste: tabela `reajustes` (agendado | aplicado | cancelado), um agendado por plano. `db.valor_do_plano(plano, data)`
  devolve o valor novo para vencimentos a partir da vigência (mensagens e valor sugerido do pagamento usam isso);
  `cobranca.executar_cobranca()` chama `db.aplicar_reajustes()` antes dos avisos. Antecedência recomendada: 30 dias.
- LGPD:
  - consentimento por canal (`aceita_email`, `aceita_whatsapp`): quem não autorizou recebe o
    status `"não autorizado"` e nada é enviado;
  - o aceite dos termos fica gravado em `termos_aceitos_em`;
  - a ficha do aluno permite exportar (JSON) e anonimizar;
  - avisos com mais de `RETENCAO_AVISOS_DIAS` (365) são apagados.
- Rotas públicas (sem login, em `PUBLICAS`): documentos, `/api/saude`, `/api/versao`, `/agenda/<token>.ics`,
  `/pix/qr/<centavos>.png` (só gera QR da chave da própria academia), `/manifest.webmanifest`, `/sw.js`, `/offline`.
  O service worker guarda só `/static` e `/offline`; páginas com dados nunca vão para o cache.
- Único cookie: o de sessão (essencial), por isso não há banner de cookies. Não adicionar Google
  Analytics nem scripts de terceiros sem atualizar a política de privacidade.

## Versões e releases

- Toda entrega para o usuário sobe a versão: edite `VERSION` e adicione no topo do `CHANGELOG.md` a seção
  `## [X.Y.Z] - AAAA-MM-DD · Título` com itens `- **destaque**: texto`. O teste `test_versao_e_saude_publicas`
  falha se a versão não tiver seção. Ao chegar na `main`, `.github/workflows/release.yml` cria a tag e a release.
- A API de Actions não é acessível desta sessão (proxy); releases e tags podem ser lidas/criadas por
  `gh api repos/Corrar/Academia-SystemFinance/releases` (só REST; GraphQL é bloqueado).
- Workflows: `testes.yml` (pyflakes + pytest), `release.yml`, `monitor.yml` (de hora em hora em `/api/saude`;
  abre/fecha issue `fora-do-ar`) e `dependabot.yml`.

## Comandos

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # o hook de sessão já faz isso
python seed.py                 # cria academia.db com dados de demonstração
python app.py                  # http://127.0.0.1:5000 (usuário/senha do .env; padrão admin/admin123)
python -m pytest -q tests      # testes (SQLite temporário; não tocam no academia.db)
python -m pyflakes *.py tests  # linter
```

Teste visual: o Chromium fica em `/opt/pw-browsers/chromium` (Playwright com `executable_path`).
Não rode `playwright install`.

## Convenções

- Nomes, comentários, mensagens e textos da interface em português.
- SQL com `?` ou `:nome`. `db._traduzir` converte para `%s`/`%(nome)s` no Postgres. Inserções que
  precisam do id usam `RETURNING id` (funciona nos dois bancos). Para comparar texto sem
  diferenciar maiúsculas, use `lower(...)`, porque o Postgres não tem `COLLATE NOCASE`.
- Abra conexões sempre com `with db.conectar() as con:`. O bloco grava ou desfaz e fecha a conexão
  no fim, nos dois bancos.
- Todo POST precisa do campo `csrf` (`{{ csrf_token }}`). Endpoints públicos ficam em `PUBLICAS`
  no `app.py`.
- Design (shadcn/ui em CSS puro, sem React nem Tailwind):
  - tokens do shadcn no `:root` (`--background`, `--card`, `--primary`, `--muted`, `--border`, `--input`,
    `--ring`, `--radius`); os nomes antigos (`--superficie`, `--texto`, `--suave`…) apontam para eles;
  - componentes: `.btn` = Button outline, `.btn.primario` = default, `.btn.perigo`, `.btn.destrutivo`,
    `.btn.fantasma`; `.card`/`.kpi`/`.tcard` = Card; `.pill` = Badge; `.filtros` = Tabs; `.toast` = Sonner;
    `#confirmar` = AlertDialog; `#mais` = Drawer;
  - fonte do sistema (SF Pro), com Inter local como alternativa; switches no estilo iOS;
  - confirmação de ação: `<form data-confirmar="texto" data-titulo="..." data-ok="Rótulo" data-perigo>`
    (nunca `onsubmit="return confirm()"`);
  - no celular, tabelas têm uma versão `.lista-cel.so-celular` e a tabela fica em `.so-desktop`;
    `.tcard.tocavel` deixa o cartão inteiro clicável; `.acoes-contato` são as ações rápidas;
  - movimento: curvas `--curva` (folhas do iOS) e `--mola`; entrada em cascata com
    `animation-fill-mode: backwards` (com `both` o `transform` final trava o hover); View Transitions
    entre páginas (`topo`, `abas` e `aba-ativa` têm nome próprio); tudo some com `prefers-reduced-motion`;
  - acima de 760px, **sidebar lateral** (`.lateral` em `base.html`, variante floating do shadcn): busca rápida
    (Ctrl+K), Fila de envio com contador, Avisos, grupo "Menu", cartão de status do envio, Configurações/tema/ajuda
    e usuário (`<details>`). Recolhe para só ícones com `html[data-lateral="recolhida"]` (Ctrl+B, salvo em
    localStorage; telas de 761–1100px começam recolhidas pelo script do `_head.html`). No desktop o `.topbar` some;
  - abaixo de 760px, barra de abas flutuante (cantos de 34px) com Início, Inscritos, Validade,
    Financeiro e Menu; a aba atual vira um círculo azul de 60px só com o ícone (ícones `aba-*`);
  - ícones: Lucide 0.469 (biblioteca do shadcn) em `icones.py`, gerados do pacote `lucide-static`; para incluir
    um novo, copie o miolo do SVG oficial (sem o `<svg>`), nunca desenhe à mão;
  - "Menu" abre um `<dialog>` em tela cheia: botão fechar redondo, busca em pílula (filtra o menu
    e oferece buscar nos inscritos), "Acesso rápido" em cartões 2×3 e listas com o ícone à direita;
  - a logo é só a escrita "Corpu's" (`static/logo-horizontal.svg`).
- Cores novas viram tokens no `:root` e precisam ser redefinidas nos dois blocos do modo escuro
  (`[data-tema="escuro"]` e `prefers-color-scheme`). Contraste mínimo: WCAG AA. A auditoria com
  axe-core deu 0 problemas nos dois modos, em 1280px e 390px; mantenha assim.
- Sem CDN: a CSP é `default-src 'self'`. Fontes e imagens ficam em `static/`.

## Deploy (Vercel + Neon)

- Flask detectado sem configuração, Python 3.12 (`.python-version`). O `.vercelignore` tira testes,
  docs, `.claude` e `graphify-out` do pacote.
- Variáveis de ambiente na Vercel:
  - sensíveis: `DATABASE_URL` (Neon, pooler), `SECRET_KEY`, `CRON_SECRET`, `ADMIN_SENHA`;
  - comuns: `ADMIN_USUARIO`, `ACADEMIA_NOME`, `FUSO`, `URL_PUBLICA`.
- Sem `DATABASE_URL`, o app usa `/tmp/academia.db` (temporário) e mostra um alerta vermelho.
- O sistema de arquivos é só leitura: nada pode depender de gravar arquivo fora de `/tmp`.
- O container desta sessão não acessa `*.vercel.app` nem o host do Neon. Use os conectores
  (MCP da Vercel: `web_fetch_vercel_url`, `get_runtime_logs`; MCP do Neon: `run_sql`).
- Nunca imprimir segredos (`DATABASE_URL`, tokens) na conversa nem em commits.

## Armadilhas conhecidas

- `pkill -f "python app.py"` mata o próprio shell, porque o padrão aparece na linha de comando.
  Use `pkill -f "[b]in/python app[.]py"` numa chamada separada.
- O servidor Flask local guarda templates em cache: reinicie depois de editar HTML.
- `<form>` não pode ficar dentro de `<tr>`: use o atributo `form="id"` nos botões.
- Itens de grid com texto `nowrap` estouram a largura no celular: `.grade-2 > *` e afins usam `min-width: 0`.
- Auditoria axe e capturas: use `reduced_motion="reduce"` no Playwright, senão pega elementos no meio da animação.
- `<legend>` não participa do grid do `<fieldset>`: no cadastro rápido a legenda é `sr-only` e o número da ficha é um `<span>`.
- Campos `type=date` têm largura mínima: em grids, ponha `min-width: 0` nos filhos para não estourar no celular.
- Macros de um template base não ficam visíveis nos filhos: ficam em `legal/_macros.html` e são
  importadas.
- O login limpa a sessão (contra fixação de sessão) e gera um token CSRF novo.
- Bloqueio de login: 5 erros em 15 minutos retornam 429. A contagem fica no banco, porque na
  Vercel cada instância tem a sua memória.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

No Claude Code na web, o hook `.claude/hooks/session-start.sh` instala o Graphify
(`graphifyy==0.9.93`, fora do projeto) e roda `GRAPHIFY_BACKEND=none graphify update .` no início
de cada sessão. Assim o grafo nunca fica defasado, mesmo que alguém esqueça de atualizá-lo.
