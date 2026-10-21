# Revisão de conformidade: LGPD, acessibilidade, transparência e segurança

Revisão feita em 21/10/2026 sobre o sistema de cobrança (painel interno + páginas públicas de documentos).

**Legenda:** ✅ resolvido no sistema · 🟡 resolvido no sistema, mas depende de ação da academia · 📋 só a academia pode fazer

> Este documento e os textos legais do sistema são um ponto de partida técnico, não um parecer jurídico.
> Peça a um advogado que revise os documentos antes de divulgá-los aos alunos.

## 1. Documentação e termos

| Item | Status | O que foi feito / o que falta |
|---|---|---|
| Política de privacidade | 🟡 | Página pública `/privacidade`, sem login. Descreve exatamente o que o sistema coleta, as bases legais (art. 7º, II, V e VI), com quem compartilha (provedores de e-mail/WhatsApp), retenção, direitos do art. 18, encarregado, menores, cookies e incidentes. **Falta:** preencher os dados legais em Configurações e pedir revisão jurídica. |
| Termos de serviço | 🟡 | Página `/termos`: planos, renovação (mesma regra do sistema), avisos de vencimento (datas reais de `DIAS_AVISO`), atraso, cancelamento e foro do consumidor (CDC art. 101). As regras de uso das instalações ficam no regulamento interno da academia. |
| Política de reembolso | 🟡 | Página `/reembolso`: arrependimento de 7 dias (CDC art. 49), cancelamento proporcional, prazo e forma do reembolso e cobrança indevida. A multa e o prazo são configuráveis (padrão: sem multa, 30 dias). **Confirmar com advogado** se for usar multa. |

## 2. Privacidade e dados (LGPD)

| Item | Status | O que foi feito / o que falta |
|---|---|---|
| Consentimento de cookies | ✅ | Não há cookies de rastreamento, e as páginas públicas não criam nenhum cookie. O painel usa só um cookie de sessão **estritamente necessário** (login + proteção CSRF), com `HttpOnly`, `SameSite=Lax`, `Secure` (com `COOKIE_SEGURO=1`) e validade de 8 h. Cookie estritamente necessário dispensa banner de consentimento; a política de privacidade e a tela de login informam isso. Se um dia for incluído analytics, será preciso um banner de consentimento **antes** de carregá-lo. |
| Formulários adequados à LGPD | ✅ | Cadastro com autorização separada de avisos por e-mail e por WhatsApp (respeitada no envio automático, no manual e no "Avisar todos"), registro de data e hora do aceite dos termos e da política, menção ao responsável legal no caso de menores e aviso para não registrar dados de saúde (dado sensível) nas observações. Todos os campos têm rótulo acessível. |
| Coletar só o necessário | ✅ | **Data de nascimento removida** do cadastro (não é usada na cobrança). CPF marcado como opcional ("só se precisar emitir recibo ou nota"). O histórico de avisos é apagado automaticamente após `RETENCAO_AVISOS_DIAS` (365). |
| Direitos do titular (art. 18) | ✅ | Na ficha do aluno: **Exportar dados** (arquivo JSON com cadastro, pagamentos e avisos, para acesso e portabilidade) e **Apagar dados pessoais (anonimizar)**, que mantém só os valores pagos exigidos pela lei fiscal. Toda mensagem informa como deixar de receber avisos. |
| Conformidade geral | 🟡 | Ver os itens 📋 em "O que a academia precisa fazer". |

## 3. Rastreamento e analytics

| Item | Status | Resultado |
|---|---|---|
| Google Analytics e scripts de tracking | ✅ | Varredura do código: **nenhum** Google Analytics, Tag Manager, pixel ou script de terceiros. O único recurso externo era a fonte do Google Fonts, que enviava o IP de cada usuário ao Google. Ela agora é **servida pelo próprio sistema** (`static/fonts`). A política de segurança de conteúdo (CSP) bloqueia qualquer script, fonte ou conexão externa. |

## 4. Acessibilidade (WCAG 2.1 AA)

Auditoria automática com **axe-core 4.10** em 14 páginas, nos modos **claro e escuro** e nos tamanhos **computador (1280 px) e celular (390 px)**, mais teste manual de teclado.

| Item | Antes | Depois |
|---|---|---|
| Auditoria (total de ocorrências) | **477** | **0** |
| Contraste de cores | 446 ocorrências (cinza `#94a3b8` = 2,6:1; verde, laranja e amarelo abaixo de 4,5:1) | Cores ajustadas: todos os textos ≥ 4,5:1 sobre branco e sobre os fundos coloridos |
| Campos sem rótulo | 23 (19 campos e 4 seleções) | 0: os rótulos envolvem os campos; buscas, testes e botões de ícone têm `aria-label` |
| Texto alternativo em imagens | O sistema **não tem imagens** `<img>`. Os ícones SVG são decorativos (`aria-hidden`), e o significado está no texto ao lado ou no `aria-label` do botão. As barras de progresso têm descrição em texto para leitor de tela. | ✅ |
| Navegação por teclado | Sem foco visível | Link "Pular para o conteúdo", contorno de foco em todos os elementos, `aria-current` no menu e nos filtros, seleção de provedor de WhatsApp pelas setas. Login e navegação pelo painel testados só com teclado. |
| Outros | Páginas sem região principal, link só por cor, cabeçalho de tabela vazio | `<main>` em todas as páginas, links sublinhados no texto, mensagens com `role="status"`/`alert`, `prefers-reduced-motion` respeitado |

A auditoria automática encontra em torno de metade dos problemas reais. Antes de publicar, recomenda-se um teste
com leitor de tela (NVDA no Windows ou VoiceOver no Mac/iPhone).

## 5. Transparência e direitos autorais

| Item | Status | Resultado |
|---|---|---|
| Avaliações falsas | ✅ | Nenhuma avaliação, depoimento ou nota no sistema. Os 30 alunos do `seed.py` são **fictícios e só para demonstração**; o script avisa para não usar em produção. |
| Promessas sem comprovação | ✅ | Revisados todos os textos (telas, e-mails, documentos, README). Nada de "garantido", "100%" ou "o melhor". Dois textos imprecisos corrigidos: "a Evolution API é gratuita" (o software é; o servidor é pago) e "roda em qualquer computador". |
| Licenças de imagens | ✅ | Não há fotos nem imagens de banco de imagens. Ícones **Lucide** (ISC) e fontes **Inter** e **Kaushan Script** (OFL 1.1), ambos de uso comercial livre, com licenças em `LICENCAS_TERCEIROS.md` e `static/fonts/OFL.txt`. A escrita da logo foi redesenhada em vetor a partir da logo enviada pela academia. |
| Dados legais da empresa | 🟡 | Novos campos em **Configurações → Dados legais**: razão social, CNPJ, endereço, e-mail, encarregado (DPO). Aparecem no rodapé do painel, nas páginas públicas e em todo e-mail de cobrança. Enquanto faltarem, o painel mostra um alerta e os documentos destacam o trecho em amarelo, sem inventar dados. |

## 6. Segurança e riscos jurídicos

| Risco | Status | Mitigação |
|---|---|---|
| Senha padrão `admin123` | 🟡 | Alerta fixo no painel enquanto a senha for a padrão. **Trocar `ADMIN_SENHA` no `.env`.** |
| Chave de sessão fraca | ✅ | Se `SECRET_KEY` não for definida, é gerada uma chave aleatória de 256 bits, guardada em `.secret_key` (fora do Git). |
| Força bruta no login | ✅ | Bloqueio por 15 min após 5 tentativas erradas. |
| Cabeçalhos de segurança | ✅ | CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS (com HTTPS) e `Cache-Control: no-store` nas páginas com dados pessoais. Painel marcado como `noindex`. |
| Cobrança abusiva (CDC art. 42) | ✅ | Mensagens sem ameaça nem exposição a terceiros, só em horário comercial (`HORA_COBRANCA` limitada a 8h–20h) e com no máximo `MAX_LEMBRETES_SEMANAIS` (4) lembretes semanais depois do último aviso. |
| Banimento de WhatsApp por spam | 🟡 | Respeito ao opt-out, volume baixo e espaçado. Em provedores não oficiais (Z-API, Evolution, Green API) o risco existe: use um chip exclusivo da academia. Risco zero só com a API oficial da Meta. |
| Senhas de integração no banco | 🟡 | Tokens nunca voltam para a tela, mas ficam no `academia.db`. Proteja o arquivo (permissão de leitura só do usuário do sistema) e faça backup criptografado. |
| Exclusão de pagamentos | ✅ | "Excluir tudo" avisa que a lei fiscal pode exigir guardar os pagamentos e recomenda anonimizar. |

## O que a academia precisa fazer 📋

1. **Preencher Configurações → Dados legais** (razão social, CNPJ, endereço, e-mail, encarregado) e o endereço público do sistema.
2. **Trocar a senha** (`ADMIN_SENHA`) e publicar com **HTTPS** (`COOKIE_SEGURO=1`).
3. **Revisão jurídica** dos três documentos, principalmente multa de cancelamento, prazos e foro.
4. **Indicar o encarregado** (DPO). Pequenas empresas podem ter dispensa (Resolução CD/ANPD nº 2/2022), mas precisam manter um canal de atendimento ao titular.
5. **Contratos com operadores:** verificar os termos de privacidade do provedor de e-mail e do provedor de WhatsApp, que podem transferir dados para fora do Brasil (art. 33).
6. **Registro das operações de tratamento** (art. 37) e **plano de resposta a incidentes** (art. 48): quem avisa, em quanto tempo, como.
7. **Apresentar os termos ao aluno** na matrícula e marcar o aceite no cadastro. Menores: matrícula feita pelo responsável.
8. **Teste com leitor de tela** antes de publicar as páginas públicas.
9. **Backup** do `academia.db` em local seguro e criptografado.
