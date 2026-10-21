# Graph Report - academia-systemfinance  (2026-10-21)

## Corpus Check
- 22 files · ~38,405 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 2, .example 1)

## Summary
- 340 nodes · 801 edges · 17 communities (10 shown, 7 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 24 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `81d1c9b6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- app.py
- db.py
- notificacoes.py
- test_app.py
- config.py
- README.md
- importacao.py
- Corpu's Academia — cobrança de mensalidades
- Linha
- icones.py
- Licenças de terceiros
- tema.js
- vercel.json
- CLAUDE.md
- graphify-guard.sh
- session-start.sh
- interface.js

## God Nodes (most connected - your core abstractions)
1. `conectar()` - 44 edges
2. `login_obrigatorio()` - 31 edges
3. `hoje()` - 24 edges
4. `reajustes()` - 18 edges
5. `notificar()` - 18 edges
6. `obter()` - 17 edges
7. `alunos_lote()` - 15 edges
8. `buscar_alunos()` - 15 edges
9. `obter_aluno()` - 14 edges
10. `listar_planos()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Convenções` --references--> `csrf()`  [INFERRED]
  CLAUDE.md → tests/conftest.py
- `Mapa dos arquivos` --references--> `alunos()`  [INFERRED]
  CLAUDE.md → app.py
- `Mapa dos arquivos` --references--> `planos()`  [INFERRED]
  CLAUDE.md → app.py
- `Mapa dos arquivos` --references--> `reajustes()`  [INFERRED]
  CLAUDE.md → app.py
- `Regras de negócio` --references--> `reajustes()`  [INFERRED]
  CLAUDE.md → app.py

## Import Cycles
- None detected.

## Communities (17 total, 7 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.08
Nodes (40): alternar_ativo(), aluno_anonimizar(), aluno_detalhe(), aluno_editar(), aluno_excluir(), _aluno_exemplo(), aluno_exportar(), alunos() (+32 more)

### Community 1 - "db.py"
Cohesion: 0.06
Nodes (45): aluno_novo(), avisos(), contexto_global(), dashboard(), _form_aluno(), reajustes(), executar_cobranca(), iniciar_agendador() (+37 more)

### Community 2 - "notificacoes.py"
Cohesion: 0.07
Nodes (37): empresa(), obter(), provedor_email(), resend(), salvar(), smtp(), whatsapp(), configuracoes() (+29 more)

### Community 3 - "test_app.py"
Cohesion: 0.11
Nodes (19): _alunos_do_plano(), buscar_alunos(), fila_envio(), limpar_falhas_login(), listar_planos(), csrf(), test_aviso_respeita_quem_nao_autorizou(), test_bloqueio_apos_cinco_senhas_erradas() (+11 more)

### Community 4 - "config.py"
Cohesion: 0.13
Nodes (6): _carregar_env(), _chave_secreta(), _env(), _int(), cliente(), logado()

### Community 5 - "README.md"
Cohesion: 0.09
Nodes (21): 1. Documentação e termos, 2. Privacidade e dados (LGPD), 3. Rastreamento e analytics, 4. Acessibilidade (WCAG 2.1 AA), 5. Transparência e direitos autorais, 6. Segurança e riscos jurídicos, O que a academia precisa fazer 📋, Revisão de conformidade: LGPD, acessibilidade, transparência e segurança (+13 more)

### Community 6 - "importacao.py"
Cohesion: 0.14
Nodes (15): alunos_lote(), _opcoes_lote(), _opcoes_padrao(), _tela_lote(), _achar_plano(), _de_tabela(), formatar_telefone(), ler_arquivo() (+7 more)

### Community 7 - "Corpu's Academia — cobrança de mensalidades"
Cohesion: 0.12
Nodes (10): Armadilhas conhecidas, Comandos, Convenções, Corpu's Academia — cobrança de mensalidades, Deploy (Vercel + Neon), graphify, O que o sistema faz, Stack (+2 more)

### Community 10 - "Licenças de terceiros"
Cohesion: 0.50
Nodes (3): Licenças de terceiros, Lucide, shadcn/ui

### Community 11 - "tema.js"
Cohesion: 0.83
Nodes (3): aplicar(), atualizarBotoes(), estaEscuro()

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `conectar()` connect `db.py` to `app.py`, `notificacoes.py`, `test_app.py`, `importacao.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `reajustes()` (e.g. with `Mapa dos arquivos` and `Regras de negócio`) actually correct?**
  _`reajustes()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08282828282828283 - nodes in this community are weakly interconnected._
- **Why does `Corpu's Academia — cobrança de mensalidades` connect `Corpu's Academia — cobrança de mensalidades` to `db.py`, `notificacoes.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05868544600938967 - nodes in this community are weakly interconnected._
- **Why does `hoje()` connect `db.py` to `app.py`, `notificacoes.py`, `test_app.py`, `importacao.py`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Should `notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07033315705975675 - nodes in this community are weakly interconnected._