# Graph Report - academia-systemfinance  (2026-10-21)

## Corpus Check
- 27 files · ~45,785 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .css 2, .example 1)

## Summary
- 433 nodes · 1034 edges · 19 communities (11 shown, 8 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 33 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `29c5e290`
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
- integracoes.py
- Licenças de terceiros
- tema.js
- vercel.json
- CLAUDE.md
- graphify-guard.sh
- session-start.sh
- interface.js
- _md_simples
- sw.js

## God Nodes (most connected - your core abstractions)
1. `conectar()` - 47 edges
2. `login_obrigatorio()` - 38 edges
3. `hoje()` - 28 edges
4. `obter()` - 25 edges
5. `reajustes()` - 18 edges
6. `notificar()` - 18 edges
7. `buscar_alunos()` - 16 edges
8. `alunos_lote()` - 15 edges
9. `data_br()` - 15 edges
10. `montar_mensagem()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Convenções` --references--> `csrf()`  [INFERRED]
  CLAUDE.md → tests/conftest.py
- `Versões e releases` --references--> `test_versao_e_saude_publicas()`  [INFERRED]
  CLAUDE.md → tests/test_app.py
- `Regras de negócio` --references--> `provedor_email()`  [INFERRED]
  CLAUDE.md → ajustes.py
- `Mapa dos arquivos` --references--> `planos()`  [INFERRED]
  CLAUDE.md → app.py
- `Mapa dos arquivos` --references--> `reajustes()`  [INFERRED]
  CLAUDE.md → app.py

## Import Cycles
- None detected.

## Communities (19 total, 8 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.07
Nodes (52): agenda_ics(), agenda_novo_link(), alternar_ativo(), aluno_anonimizar(), aluno_detalhe(), aluno_editar(), aluno_excluir(), _aluno_exemplo() (+44 more)

### Community 1 - "db.py"
Cohesion: 0.06
Nodes (48): _bloqueado(), contexto_global(), dashboard(), login(), reajustes(), Regras de negócio, executar_cobranca(), iniciar_agendador() (+40 more)

### Community 2 - "notificacoes.py"
Cohesion: 0.06
Nodes (45): empresa(), obter(), provedor_email(), resend(), salvar(), smtp(), whatsapp(), alunos() (+37 more)

### Community 3 - "test_app.py"
Cohesion: 0.08
Nodes (19): _alunos_do_plano(), _opcoes_padrao(), _tela_lote(), buscar_alunos(), listar_planos(), link_envio(), csrf(), test_aviso_respeita_quem_nao_autorizou() (+11 more)

### Community 4 - "config.py"
Cohesion: 0.10
Nodes (9): _carregar_env(), _chave_secreta(), _env(), _int(), cliente(), logado(), historico(), notas() (+1 more)

### Community 5 - "README.md"
Cohesion: 0.06
Nodes (33): [1.0.0] - 2026-10-20 · Primeira versão, [1.1.0] - 2026-10-21 · Novo visual e envio configurável, [1.2.0] - 2026-10-21 · LGPD, acessibilidade e segurança, [1.3.0] - 2026-10-21 · Publicação na Vercel com Postgres, [1.4.0] - 2026-10-21 · Logo da Corpu's, visual Apple e modo escuro, [1.5.0] - 2026-10-21 · Testes automatizados e memória do projeto, [1.6.0] - 2026-10-21 · Barra de abas flutuante no celular, [1.7.0] - 2026-10-21 · Design shadcn/ui e animações (+25 more)

### Community 6 - "importacao.py"
Cohesion: 0.09
Nodes (22): alunos_lote(), _opcoes_lote(), _achar_plano(), _de_tabela(), formatar_telefone(), ler_arquivo(), ler_data(), ler_texto() (+14 more)

### Community 7 - "Corpu's Academia — cobrança de mensalidades"
Cohesion: 0.09
Nodes (14): Armadilhas conhecidas, Comandos, Convenções, Corpu's Academia — cobrança de mensalidades, Deploy (Vercel + Neon), graphify, O que o sistema faz, Stack (+6 more)

### Community 9 - "integracoes.py"
Cohesion: 0.16
Nodes (10): agenda_token(), backup(), buscar_cep(), buscar_cnpj(), _dobrar(), gerar_ics(), evento(), _get_json() (+2 more)

### Community 10 - "Licenças de terceiros"
Cohesion: 0.50
Nodes (3): Licenças de terceiros, Lucide, shadcn/ui

### Community 11 - "tema.js"
Cohesion: 0.83
Nodes (3): aplicar(), atualizarBotoes(), estaEscuro()

## Knowledge Gaps
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Corpu's Academia — cobrança de mensalidades` to `db.py`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0650103519668737 - nodes in this community are weakly interconnected._
- **Why does `Versões e releases` connect `Corpu's Academia — cobrança de mensalidades` to `README.md`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05821917808219178 - nodes in this community are weakly interconnected._
- **Why does `conectar()` connect `db.py` to `app.py`, `notificacoes.py`, `test_app.py`, `importacao.py`, `Corpu's Academia — cobrança de mensalidades`, `integracoes.py`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Should `notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06142410015649452 - nodes in this community are weakly interconnected._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0773109243697479 - nodes in this community are weakly interconnected._