# Graph Report - academia-systemfinance  (2026-10-21)

## Corpus Check
- 20 files · ~24,649 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 2, .example 1)

## Summary
- 257 nodes · 543 edges · 15 communities (9 shown, 6 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `afd72cd4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- conectar
- db.py
- notificacoes.py
- test_app.py
- config.py
- README.md
- ajustes.py
- Corpu's Academia — cobrança de mensalidades
- app.py
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
- `Mapa dos arquivos` --references--> `alunos()`  [INFERRED]
  CLAUDE.md → app.py
- `Mapa dos arquivos` --references--> `planos()`  [INFERRED]
  CLAUDE.md → app.py
- `Corpu's Academia — cobrança de mensalidades` --references--> `main()`  [INFERRED]
  CLAUDE.md → seed.py
- `Convenções` --references--> `_traduzir()`  [INFERRED]
  CLAUDE.md → db.py

## Import Cycles
- None detected.

## Communities (15 total, 6 thin omitted)

### Community 0 - "conectar"
Cohesion: 0.11
Nodes (30): alternar_ativo(), aluno_anonimizar(), aluno_detalhe(), aluno_editar(), aluno_excluir(), aluno_novo(), avisar_aluno(), avisar_inadimplentes() (+22 more)

### Community 1 - "db.py"
Cohesion: 0.08
Nodes (15): _bloqueado(), login(), iniciar_agendador(), _loop_agendador(), agora(), _conexao_pg(), _ConexaoSQLite, _fabrica_linhas() (+7 more)

### Community 2 - "notificacoes.py"
Cohesion: 0.09
Nodes (26): _aluno_exemplo(), email_preview(), teste_email(), teste_whatsapp(), Mapa dos arquivos, dias_para_vencer(), _enriquecer(), status_aluno() (+18 more)

### Community 3 - "test_app.py"
Cohesion: 0.12
Nodes (9): limpar_falhas_login(), cliente(), csrf(), logado(), test_aviso_respeita_quem_nao_autorizou(), test_bloqueio_apos_cinco_senhas_erradas(), test_documentos_publicos_sem_login_e_sem_cookie(), test_exportar_e_anonimizar() (+1 more)

### Community 4 - "config.py"
Cohesion: 0.22
Nodes (4): _carregar_env(), _chave_secreta(), _env(), _int()

### Community 5 - "README.md"
Cohesion: 0.09
Nodes (20): 1. Documentação e termos, 2. Privacidade e dados (LGPD), 3. Rastreamento e analytics, 4. Acessibilidade (WCAG 2.1 AA), 5. Transparência e direitos autorais, 6. Segurança e riscos jurídicos, O que a academia precisa fazer 📋, Revisão de conformidade: LGPD, acessibilidade, transparência e segurança (+12 more)

### Community 6 - "ajustes.py"
Cohesion: 0.23
Nodes (11): empresa(), obter(), salvar(), smtp(), whatsapp(), avisos(), configuracoes(), contexto_global() (+3 more)

### Community 7 - "Corpu's Academia — cobrança de mensalidades"
Cohesion: 0.12
Nodes (11): Armadilhas conhecidas, Comandos, Convenções, Corpu's Academia — cobrança de mensalidades, Deploy (Vercel + Neon), graphify, O que o sistema faz, Regras de negócio (+3 more)

### Community 9 - "app.py"
Cohesion: 0.09
Nodes (17): aluno_exportar(), alunos(), cabecalhos_seguranca(), cron_cobranca(), _documento(), executar_cobranca(), logout(), privacidade() (+9 more)

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Corpu's Academia — cobrança de mensalidades` connect `Corpu's Academia — cobrança de mensalidades` to `db.py`, `notificacoes.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Should `conectar` be split into smaller, more focused modules?**
  _Cohesion score 0.10953058321479374 - nodes in this community are weakly interconnected._
- **Why does `conectar()` connect `conectar` to `db.py`, `notificacoes.py`, `test_app.py`, `ajustes.py`, `app.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07657657657657657 - nodes in this community are weakly interconnected._
- **Should `notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08985200845665962 - nodes in this community are weakly interconnected._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1225296442687747 - nodes in this community are weakly interconnected._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._