# Graph Report - academia-systemfinance  (2026-10-21)

## Corpus Check
- 20 files · ~24,098 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 2, .example 1)

## Summary
- 256 nodes · 542 edges · 16 communities (9 shown, 7 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c7eb6b62`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- app.py
- db.py
- notificacoes.py
- test_app.py
- config.py
- README.md
- ajustes.py
- Corpu's Academia — cobrança de mensalidades
- hoje
- icones.py
- Licenças de terceiros
- tema.js
- vercel.json
- CLAUDE.md
- graphify-guard.sh
- session-start.sh

## God Nodes (most connected - your core abstractions)
1. `conectar()` - 32 edges
2. `login_obrigatorio()` - 24 edges
3. `hoje()` - 16 edges
4. `notificar()` - 15 edges
5. `obter_aluno()` - 14 edges
6. `montar_mensagem()` - 12 edges
7. `Corpu's Academia — cobrança de mensalidades` - 11 edges
8. `obter()` - 10 edges
9. `executar_cobranca()` - 10 edges
10. `montar_email_html()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Convenções` --references--> `csrf()`  [INFERRED]
  CLAUDE.md → tests/conftest.py
- `Mapa dos arquivos` --references--> `_enriquecer()`  [INFERRED]
  CLAUDE.md → db.py
- `Mapa dos arquivos` --references--> `moeda()`  [INFERRED]
  CLAUDE.md → notificacoes.py
- `Mapa dos arquivos` --references--> `data_br()`  [INFERRED]
  CLAUDE.md → notificacoes.py
- `Corpu's Academia — cobrança de mensalidades` --references--> `main()`  [INFERRED]
  CLAUDE.md → seed.py

## Import Cycles
- None detected.

## Communities (16 total, 7 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.09
Nodes (40): alternar_ativo(), aluno_anonimizar(), aluno_editar(), aluno_excluir(), _aluno_exemplo(), aluno_exportar(), aluno_novo(), alunos() (+32 more)

### Community 1 - "db.py"
Cohesion: 0.08
Nodes (15): _bloqueado(), login(), executar_cobranca(), iniciar_agendador(), _loop_agendador(), agora(), anonimizar_aluno(), _conexao_pg() (+7 more)

### Community 2 - "notificacoes.py"
Cohesion: 0.12
Nodes (16): data_br(), enviar_whatsapp(), _evolution(), ja_enviado(), link_whatsapp(), _meta(), moeda(), montar_mensagem() (+8 more)

### Community 3 - "test_app.py"
Cohesion: 0.09
Nodes (12): buscar_alunos(), iniciar_banco(), limpar_falhas_login(), main(), cliente(), csrf(), logado(), test_aviso_respeita_quem_nao_autorizou() (+4 more)

### Community 4 - "config.py"
Cohesion: 0.22
Nodes (4): _carregar_env(), _chave_secreta(), _env(), _int()

### Community 5 - "README.md"
Cohesion: 0.09
Nodes (20): 1. Documentação e termos, 2. Privacidade e dados (LGPD), 3. Rastreamento e analytics, 4. Acessibilidade (WCAG 2.1 AA), 5. Transparência e direitos autorais, 6. Segurança e riscos jurídicos, O que a academia precisa fazer 📋, Revisão de conformidade: LGPD, acessibilidade, transparência e segurança (+12 more)

### Community 6 - "ajustes.py"
Cohesion: 0.16
Nodes (13): empresa(), obter(), salvar(), smtp(), whatsapp(), avisos(), configuracoes(), contexto_global() (+5 more)

### Community 7 - "Corpu's Academia — cobrança de mensalidades"
Cohesion: 0.12
Nodes (11): Armadilhas conhecidas, Comandos, Convenções, Corpu's Academia — cobrança de mensalidades, Deploy (Vercel + Neon), graphify, O que o sistema faz, Regras de negócio (+3 more)

### Community 8 - "hoje"
Cohesion: 0.18
Nodes (11): aluno_detalhe(), _validade_sugerida(), dias_para_vencer(), _enriquecer(), hoje(), inadimplentes(), notificacoes_recentes(), pagamentos_aluno() (+3 more)

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Corpu's Academia — cobrança de mensalidades` connect `Corpu's Academia — cobrança de mensalidades` to `app.py`, `test_app.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08552188552188553 - nodes in this community are weakly interconnected._
- **Why does `conectar()` connect `app.py` to `db.py`, `notificacoes.py`, `test_app.py`, `ajustes.py`, `hoje`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08067226890756303 - nodes in this community are weakly interconnected._
- **Should `notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12413793103448276 - nodes in this community are weakly interconnected._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09195402298850575 - nodes in this community are weakly interconnected._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._