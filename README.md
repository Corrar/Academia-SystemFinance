# 🏋️ Sistema de Cobrança para Academia

Sistema simples para controlar mensalistas: cadastro de inscritos, validade dos planos,
pagamentos, faturamento do mês e **avisos automáticos de vencimento por e-mail e WhatsApp**.

Feito em **Python + Flask + SQLite**: não precisa instalar banco de dados, roda em qualquer
computador (Windows, Mac ou Linux) ou servidor.

## Funcionalidades

| Tela | O que faz |
|---|---|
| **Dashboard** | Nº de mensalistas ativos, faturado no mês, receita mensal prevista, gráfico dos últimos 6 meses e a lista de quem **venceu há 10 dias ou mais e não pagou**, com botões de e-mail, WhatsApp e "Receber" |
| **Inscritos** | Busca por nome, CPF, telefone ou e-mail, com filtro por situação (em dia, vence em breve, vencido, inadimplente, inativo) |
| **Consulta de validade** | Digite nome/CPF/telefone e veja até quando o plano vale, e os vencimentos dos próximos 15 dias |
| **Ficha do aluno** | Dados, validade, registro de pagamento (renova a validade sozinho), histórico, estorno, envio de aviso manual e link "Abrir no WhatsApp" |
| **Financeiro** | Pagamentos de qualquer mês, total recebido, ticket médio e total por forma de pagamento |
| **Avisos e cobrança** | Histórico de todos os avisos enviados, status do e-mail e WhatsApp, e botão "Executar cobrança agora" |
| **Planos** | Mensal, trimestral, semestral… (valor e duração em dias) |
| **Configurações** | Nome da academia, telefone, chave PIX e **servidor de e-mail** (com atalhos para Gmail, Outlook, Hostinger, Locaweb, Zoho), botão de **e-mail de teste** e pré-visualização do e-mail |

### Como funciona a cobrança automática

Todo dia, a partir de `HORA_COBRANCA` (padrão 9h), o sistema envia avisos para os alunos ativos em
dias definidos em `DIAS_AVISO` (padrão `-3,0,3,10`):

- **3 dias antes**: lembrete
- **No dia do vencimento**
- **3 e 10 dias depois**: aviso de atraso
- Depois disso, **um novo lembrete a cada 7 dias** até o aluno pagar ou ter a matrícula cancelada

Cada aviso é enviado **uma única vez** por vencimento, mesmo que a rotina rode várias vezes.
Quando o pagamento é registrado, a validade é renovada e os avisos param.

## Instalação

Precisa do Python 3.10 ou mais novo.

```bash
cd academia
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # no Windows: copy .env.example .env
# edite o .env: nome da academia, senha do painel, chave PIX, e-mail e WhatsApp

python seed.py              # (opcional) cria 30 alunos de exemplo para testar
python app.py
```

Acesse **http://localhost:5000**. Usuário e senha padrão: `admin` / `admin123` (troque no `.env`).

> Para começar do zero depois de testar, apague o arquivo `academia.db`.

## Configurando o envio

Enquanto e-mail e WhatsApp não estiverem configurados, o sistema funciona em **modo simulado**:
as mensagens aparecem no histórico de avisos, mas nada é enviado. Dá para testar tudo com segurança.

### E-mail

Pelo próprio sistema: menu **Configurações → Envio por e-mail (SMTP)**.

1. Clique no seu provedor (Gmail, Outlook, Hostinger…) para preencher servidor, porta e segurança.
2. Informe o e-mail de login e a senha.
   - **Gmail**: ative a verificação em duas etapas e gere uma **senha de app** em
     https://myaccount.google.com/apppasswords. Use essa senha de 16 letras, não a senha normal.
   - **Outlook/Hotmail**: contas pessoais podem exigir senha de app.
3. Salve e use **Enviar e-mail de teste** para confirmar.

Os avisos saem em HTML no mesmo visual do painel (com valor, vencimento e chave PIX) e também em
texto simples. Use **Ver modelo do e-mail** para conferir antes.

> Também dá para configurar pelo `.env` (`SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`,
> `SMTP_SEGURANCA`). O que for salvo na tela de Configurações tem prioridade.
> A senha fica guardada no arquivo `academia.db`: mantenha esse arquivo protegido.

### WhatsApp

Escolha **um** provedor em `WHATSAPP_PROVEDOR`:

| Provedor | Quando usar | Variáveis |
|---|---|---|
| `zapi` | Mais simples no Brasil: conecta o seu número lendo um QR Code. Serviço pago | `ZAPI_INSTANCIA`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN` |
| `evolution` | Gratuito/open-source, você hospeda a Evolution API | `EVOLUTION_URL`, `EVOLUTION_INSTANCIA`, `EVOLUTION_APIKEY` |
| `meta` | API oficial do WhatsApp Business (Cloud API). Exige um template aprovado para mandar mensagem a quem não falou com você nas últimas 24h | `META_TOKEN`, `META_PHONE_ID`, `META_TEMPLATE` |
| `twilio` | API oficial via Twilio | `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_NUMERO` |

**Template da Meta**: crie um template de categoria *Utilidade* com 3 variáveis, por exemplo:
> Olá {{1}}! Sua mensalidade vence em {{2}}, no valor de {{3}}. Qualquer dúvida, estamos à disposição.

**Sem API nenhuma?** Na ficha do aluno existe o botão **"Abrir no WhatsApp (envio manual)"**, que abre o
WhatsApp Web/celular com a mensagem já escrita. É só apertar enviar.

Os telefones podem ser cadastrados como `(11) 99999-0000`. O sistema coloca o `55` automaticamente.

## Deixando rodando

A cobrança automática roda **enquanto o sistema estiver aberto** (`python app.py`). Para deixar
sempre ligado, use um computador da recepção que fique ligado, ou um servidor/VPS.

Se preferir agendar pelo sistema operacional (cron no Linux ou Agendador de Tarefas no Windows),
dá para rodar só a cobrança:

```bash
# todo dia às 9h (crontab -e)
0 9 * * * cd /caminho/academia && .venv/bin/python cobranca.py
```

Para produção, rode com um servidor WSGI, por exemplo: `pip install waitress` e
`waitress-serve --port=5000 app:app`.

## Estrutura

```
academia/
├── app.py            # rotas e telas (Flask)
├── db.py             # banco SQLite, consultas e indicadores
├── notificacoes.py   # mensagens, envio por e-mail e WhatsApp
├── ajustes.py        # configurações editáveis pela tela (sobrepõem o .env)
├── icones.py         # ícones SVG das telas
├── cobranca.py       # rotina diária de cobrança automática
├── config.py         # leitura do .env
├── seed.py           # dados de exemplo
├── templates/        # páginas HTML (+ email_aviso.html, modelo do e-mail)
└── static/style.css
```

## Regras usadas

- **Inadimplente**: aluno ativo com `DIAS_INADIMPLENCIA` (padrão 10) dias ou mais após o vencimento.
- **Renovação**: ao registrar pagamento, a nova validade sugerida é *vencimento atual + duração do plano*
  (mantém o dia fixo de vencimento). Se essa data ainda ficar no passado (aluno sumiu por meses),
  conta a partir de hoje. A data pode ser alterada antes de confirmar.
- **Faturado no mês**: soma dos pagamentos registrados no mês atual.
- **Receita mensal prevista**: soma do valor dos planos dos alunos ativos, convertida para 30 dias
  (ex.: trimestral de R$ 330 conta como R$ 110/mês).
- **Cancelar matrícula** deixa o aluno inativo: ele sai das contagens e não recebe cobranças, mas o histórico é mantido.
