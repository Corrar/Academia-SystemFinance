# Novidades

Todas as mudanças do sistema, da mais nova para a mais antiga. A versão segue o
[versionamento semântico](https://semver.org/lang/pt-BR/): `MAIOR.MENOR.CORREÇÃO`.
Para publicar uma versão nova, mude o arquivo `VERSION` e adicione a seção aqui:
a release no GitHub é criada sozinha.

## [1.10.0] - 2026-10-24 · Celular mais simples, em cartões

- **Cartões compactos no celular**: em Inscritos e no painel, cada aluno vira um cartão com só o essencial (nome, situação e quantos dias faltam ou de atraso). O resto fica na ficha, a um toque.
- **Inadimplentes com ações rápidas**: no painel do celular, cada atrasado mostra os dias e o valor, com os botões redondos de avisar no WhatsApp e de receber.
- **Seções que abrem com um toque**: no celular, a ficha do aluno (registrar pagamento, aviso, pagamentos, avisos enviados, contato e dados, matrícula) e as Configurações começam fechadas; os atalhos "Receber" e "Avisar" abrem direto a seção certa.
- **Menos texto na tela**: descrições longas, subtítulos e números secundários ficam só no computador; no painel do celular entra "Vencem em 7 dias" no lugar da receita prevista.
- **Planos em uma coluna** no celular, sem cortar o valor, e o aviso do topo sem quebrar o texto.
- **Correção**: o cadastro rápido não estoura mais a largura da tela no computador.

## [1.9.0] - 2026-10-21 · Integrações gratuitas e versão no sistema

- **PIX copia e cola e QR Code** (padrão do Banco Central) com o valor certo de cada aluno: vai nos avisos de WhatsApp e e-mail, aparece na ficha do aluno para pagar na recepção e na fila de envio.
- **Agenda no celular**: link de calendário (Google Agenda, Apple Calendário, Outlook) com os vencimentos e os reajustes, que se atualiza sozinho.
- **Preenchimento automático**: dados da empresa pelo CNPJ e endereço pelo CEP (BrasilAPI, gratuita).
- **Instalar como app** no celular e no computador (PWA), com ícone na tela inicial e aviso quando estiver sem internet.
- **Resumo diário por e-mail** para o administrador: quem vence hoje, inadimplentes, recebido no dia anterior e a fila de envio.
- **Backup completo** em um arquivo, a qualquer momento.
- **Versão no sistema**: número da versão na sidebar, no login e no rodapé, e a página **Novidades** com este histórico.
- **Automações no GitHub**: testes a cada envio de código, release automática a cada versão nova, monitor que abre um alerta se o sistema sair do ar e atualização das dependências (Dependabot).

## [1.8.0] - 2026-10-21 · Cadastro rápido, filtros, fila de envio e reajuste

- **Cadastro rápido** das fichas em papel: várias de uma vez, colar do Excel/Google Planilhas ou importar .xlsx/.csv, com revisão e bloqueio de duplicados.
- **Filtros** em Inscritos (plano, contato, vencimento, ordem) e no histórico de avisos; exportação da lista.
- **Fila de envio**: modo manual pelo seu WhatsApp ou e-mail com um toque, pronto para usar sem configurar nada; Resend como provedor de e-mail; comprovante de pagamento.
- **Aviso de reajuste** da mensalidade com antecedência, aplicado sozinho na data de vigência.
- **Sidebar lateral** no computador (padrão shadcn/ui) e ícones Lucide.

## [1.7.0] - 2026-10-21 · Design shadcn/ui e animações

- Sistema de design do **shadcn/ui** em CSS puro (botões, cartões, campos, abas, confirmações e mensagens).
- **Animações no estilo Apple**: transição entre páginas, entrada em cascata, molas, contadores e troca de tema em círculo.
- Celular com cartões tocáveis, ações rápidas e listas no lugar das tabelas.

## [1.6.0] - 2026-10-21 · Barra de abas flutuante no celular

- Barra de abas inferior flutuante, com a aba atual em destaque.
- Menu em tela cheia com busca, acesso rápido e listas por assunto.

## [1.5.0] - 2026-10-21 · Testes automatizados e memória do projeto

- Testes automatizados (pytest) e verificação de código (pyflakes).
- Memória do projeto para o Claude Code (CLAUDE.md e grafo do Graphify).

## [1.4.0] - 2026-10-21 · Logo da Corpu's, visual Apple e modo escuro

- Escrita da logo da Corpu's Academia no cabeçalho, login, documentos e e-mails.
- Visual no estilo Apple, **modo escuro** completo e barra de abas no celular.

## [1.3.0] - 2026-10-21 · Publicação na Vercel com Postgres

- Suporte a Postgres (Neon), cobrança diária pelo Cron da Vercel e README com capturas.

## [1.2.0] - 2026-10-21 · LGPD, acessibilidade e segurança

- Política de privacidade, termos de uso e política de reembolso públicos.
- Consentimento por canal, exportação e anonimização de dados, auditoria de acessibilidade e bloqueio de login.

## [1.1.0] - 2026-10-21 · Novo visual e envio configurável

- Novo visual e configuração do e-mail (SMTP) e do WhatsApp (Z-API, Evolution, Meta, Twilio) pela tela.

## [1.0.0] - 2026-10-20 · Primeira versão

- Cadastro de inscritos, consulta de validade, dashboard de inadimplentes, faturamento do mês e avisos de vencimento por e-mail e WhatsApp.
