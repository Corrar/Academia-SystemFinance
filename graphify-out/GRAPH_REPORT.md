# Graph Report - Academia-SystemFinance  (2026-10-24)

## Corpus Check
- 27 files · ~46,697 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .css 2, .example 1)

## Summary
- 436 nodes · 1038 edges · 23 communities (15 shown, 8 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 33 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1519574f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- app.py
- db.py
- notificacoes.py
- test_app.py
- Mapa dos arquivos
- README.md
- importacao.py
- _ConexaoPG
- Linha
- integracoes.py
- Licenças de terceiros
- tema.js
- vercel.json
- .claude/CLAUDE.md
- graphify-guard.sh
- session-start.sh
- interface.js
- _md_simples
- sw.js
- hoje
- listar_planos
- aplicar_reajustes
- test_cnpj_pela_brasilapi

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
- `Mapa dos arquivos` --references--> `alunos()`  [INFERRED]
  CLAUDE.md → app.py
- `Mapa dos arquivos` --references--> `planos()`  [INFERRED]
  CLAUDE.md → app.py

## Import Cycles
- None detected.

## Communities (23 total, 8 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.06
Nodes (57): agenda_ics(), agenda_novo_link(), alternar_ativo(), aluno_anonimizar(), aluno_editar(), aluno_excluir(), _aluno_exemplo(), aluno_exportar() (+49 more)

### Community 1 - "db.py"
Cohesion: 0.12
Nodes (18): avisos_do_ciclo(), conectar(), _conexao_pg(), _ConexaoSQLite, contatos_existentes(), exportar_aluno(), _fabrica_linhas(), falhas_recentes() (+10 more)

### Community 2 - "notificacoes.py"
Cohesion: 0.06
Nodes (42): empresa(), obter(), provedor_email(), resend(), salvar(), smtp(), whatsapp(), aluno_detalhe() (+34 more)

### Community 3 - "test_app.py"
Cohesion: 0.10
Nodes (16): buscar_alunos(), fila_envio(), csrf(), test_aviso_respeita_quem_nao_autorizou(), test_bloqueio_apos_cinco_senhas_erradas(), test_cadastro_rapido_valida_e_salva_varias_fichas(), test_colar_do_excel_mostra_revisao_sem_gravar(), test_comprovante_de_pagamento_vai_para_a_fila() (+8 more)

### Community 4 - "Mapa dos arquivos"
Cohesion: 0.06
Nodes (23): Armadilhas conhecidas, Comandos, Corpu's Academia — cobrança de mensalidades, Deploy (Vercel + Neon), graphify, Mapa dos arquivos, O que o sistema faz, Regras de negócio (+15 more)

### Community 5 - "README.md"
Cohesion: 0.05
Nodes (34): [1.0.0] - 2026-10-20 · Primeira versão, [1.10.0] - 2026-10-24 · Celular mais simples, em cartões, [1.1.0] - 2026-10-21 · Novo visual e envio configurável, [1.2.0] - 2026-10-21 · LGPD, acessibilidade e segurança, [1.3.0] - 2026-10-21 · Publicação na Vercel com Postgres, [1.4.0] - 2026-10-21 · Logo da Corpu's, visual Apple e modo escuro, [1.5.0] - 2026-10-21 · Testes automatizados e memória do projeto, [1.6.0] - 2026-10-21 · Barra de abas flutuante no celular (+26 more)

### Community 6 - "importacao.py"
Cohesion: 0.09
Nodes (20): alunos_lote(), _opcoes_lote(), _achar_plano(), _de_tabela(), formatar_telefone(), ler_arquivo(), ler_data(), ler_texto() (+12 more)

### Community 7 - "_ConexaoPG"
Cohesion: 0.25
Nodes (3): Convenções, _ConexaoPG, _traduzir()

### Community 9 - "integracoes.py"
Cohesion: 0.11
Nodes (15): executar_cobranca(), iniciar_agendador(), _loop_agendador(), proxima_execucao(), get_sistema(), agenda_token(), backup(), buscar_cep() (+7 more)

### Community 10 - "Licenças de terceiros"
Cohesion: 0.50
Nodes (3): Licenças de terceiros, Lucide, shadcn/ui

### Community 11 - "tema.js"
Cohesion: 0.83
Nodes (3): aplicar(), atualizarBotoes(), estaEscuro()

### Community 16 - "interface.js"
Cohesion: 0.32
Nodes (4): abrirDobraDoAlvo(), alternarDobra(), fecharComAnimacao(), soltar()

### Community 19 - "hoje"
Cohesion: 0.18
Nodes (13): dashboard(), _validade_sugerida(), contar_fila(), dias_para_vencer(), _enriquecer(), hoje(), inadimplentes(), proximos_vencimentos() (+5 more)

### Community 20 - "listar_planos"
Cohesion: 0.25
Nodes (8): _opcoes_padrao(), _tela_lote(), listar_planos(), notificacoes_recentes(), valor_do_plano(), test_ler_planilha_colada_reconhece_colunas_datas_e_planos(), test_ler_planilha_xlsx_e_data_do_excel(), test_reajuste_avisa_mensalistas_e_aplica_na_vigencia()

### Community 21 - "aplicar_reajustes"
Cohesion: 0.33
Nodes (3): agora(), anonimizar_aluno(), aplicar_reajustes()

## Knowledge Gaps
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Mapa dos arquivos` to `db.py`, `hoje`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.061621621621621624 - nodes in this community are weakly interconnected._
- **Why does `Versões e releases` connect `Mapa dos arquivos` to `README.md`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11822660098522167 - nodes in this community are weakly interconnected._
- **Why does `conectar()` connect `db.py` to `app.py`, `notificacoes.py`, `test_app.py`, `Mapa dos arquivos`, `importacao.py`, `integracoes.py`, `hoje`, `listar_planos`, `aplicar_reajustes`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Should `notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0635814889336016 - nodes in this community are weakly interconnected._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09885057471264368 - nodes in this community are weakly interconnected._