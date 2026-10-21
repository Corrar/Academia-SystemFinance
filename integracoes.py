"""Integrações gratuitas: agenda (iCal), dados por CNPJ e CEP (BrasilAPI), resumo diário e backup.

Nada aqui exige conta paga: a agenda é um link que o Google Agenda, o Apple Calendário e o
Outlook assinam; a BrasilAPI é pública e sem chave; o resumo usa o envio de e-mail já configurado.
"""
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone

import requests

import ajustes
import db
from notificacoes import data_br, moeda

BRASILAPI = "https://brasilapi.com.br/api"


# ---------------------------------------------------------------- agenda (iCal)

def agenda_token(novo: bool = False) -> str:
    """Senha do link da agenda (o link é privado: quem tiver o endereço vê os vencimentos)."""
    token = db.get_sistema("agenda_token")
    if novo or not token:
        token = secrets.token_urlsafe(24)
        db.set_sistema("agenda_token", token)
    return token


def _ical_texto(texto: str) -> str:
    return (texto or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _dobrar(linha: str) -> str:
    """Linhas do iCal têm no máximo 75 bytes; o resto continua na linha seguinte com um espaço."""
    partes, atual = [], ""
    for c in linha:
        if len((atual + c).encode("utf-8")) > 73:
            partes.append(atual)
            atual = " "
        atual += c
    partes.append(atual)
    return "\r\n".join(partes)


def gerar_ics(dias_antes: int = 7, dias_depois: int = 90) -> str:
    """Calendário com os vencimentos dos alunos ativos e os reajustes agendados."""
    hoje = db.hoje()
    base = ajustes.empresa()["url_publica"]
    academia = ajustes.obter("academia_nome")
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Corpus Academia//Cobranca//PT-BR", "CALSCALE:GREGORIAN",
              "METHOD:PUBLISH", f"X-WR-CALNAME:{_ical_texto('Vencimentos · ' + academia)}",
              "X-WR-TIMEZONE:America/Sao_Paulo", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]

    def evento(uid, dia: date, titulo, descricao, url=""):
        linhas.extend(["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{carimbo}", f"DTSTART;VALUE=DATE:{dia:%Y%m%d}",
                       f"DTEND;VALUE=DATE:{dia + timedelta(days=1):%Y%m%d}", f"SUMMARY:{_ical_texto(titulo)}",
                       f"DESCRIPTION:{_ical_texto(descricao)}", "TRANSP:TRANSPARENT"]
                      + ([f"URL:{url}"] if url else []) + ["END:VEVENT"])

    inicio, fim = (hoje - timedelta(days=dias_antes)).isoformat(), (hoje + timedelta(days=dias_depois)).isoformat()
    for a in db.buscar_alunos(venc_de=inicio, venc_ate=fim, ordem="vencimento"):
        if not a["ativo"]:
            continue
        valor = db.valor_do_plano(a["plano_id"], a["data_vencimento"], a["plano_valor"])
        evento(f"venc-{a['id']}-{a['data_vencimento']}@academia",
               date.fromisoformat(a["data_vencimento"]),
               f"💳 Vence: {a['nome']} ({moeda(valor) if valor else 'sem plano'})",
               f"Plano {a['plano_nome'] or '-'} · telefone {a['telefone'] or '-'}",
               f"{base}/alunos/{a['id']}" if base else "")
    for r in db.reajustes_agendados():
        evento(f"reajuste-{r['id']}@academia", date.fromisoformat(r["vigencia"]),
               f"📈 Reajuste do plano {r['plano_nome']}: {moeda(r['valor_anterior'])} → {moeda(r['valor_novo'])}",
               f"{r['avisados']} aluno(s) avisado(s).", f"{base}/reajustes" if base else "")
    linhas.append("END:VCALENDAR")
    return "\r\n".join(_dobrar(l) for l in linhas) + "\r\n"


# ---------------------------------------------------------------- CNPJ e CEP (BrasilAPI)

def _get_json(caminho: str) -> dict:
    r = requests.get(f"{BRASILAPI}/{caminho}", timeout=8, headers={"User-Agent": "academia-systemfinance"})
    if r.status_code == 404:
        raise LookupError("não encontrado")
    r.raise_for_status()
    return r.json()


def _titulo(texto: str) -> str:
    pequenas = {"de", "da", "do", "das", "dos", "e"}
    return " ".join(p if p in pequenas else p.capitalize() for p in (texto or "").lower().split())


def buscar_cnpj(cnpj: str) -> dict:
    """Razão social, endereço, cidade e telefone a partir do CNPJ (Receita Federal, via BrasilAPI)."""
    digitos = re.sub(r"\D", "", cnpj)
    if len(digitos) != 14:
        raise ValueError("CNPJ deve ter 14 números")
    d = _get_json(f"cnpj/v1/{digitos}")
    rua = " ".join(x for x in (_titulo(d.get("descricao_tipo_de_logradouro", "")), _titulo(d.get("logradouro", ""))) if x)
    numero = d.get("numero") or "s/n"
    complemento = f" – {_titulo(d['complemento'])}" if d.get("complemento") else ""
    cidade = _titulo(d.get("municipio", ""))
    cep = re.sub(r"\D", "", str(d.get("cep") or ""))
    endereco = f"{rua}, {numero}{complemento} – {_titulo(d.get('bairro', ''))}, {cidade}/{d.get('uf', '')}"
    if len(cep) == 8:
        endereco += f", CEP {cep[:5]}-{cep[5:]}"
    telefone = re.sub(r"\D", "", d.get("ddd_telefone_1") or "")
    return {
        "razao_social": _titulo(d.get("razao_social", "")).replace(" Ltda", " Ltda."),
        "nome_fantasia": _titulo(d.get("nome_fantasia", "")),
        "cnpj": f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}",
        "endereco": endereco,
        "cidade_foro": f"{cidade}/{d.get('uf', '')}" if cidade else "",
        "pix_cidade": cidade,
        "academia_telefone": (f"({telefone[:2]}) {telefone[2:-4]}-{telefone[-4:]}" if len(telefone) >= 10 else ""),
        "situacao": _titulo(d.get("descricao_situacao_cadastral", "")),
    }


def buscar_cep(cep: str) -> dict:
    digitos = re.sub(r"\D", "", cep)
    if len(digitos) != 8:
        raise ValueError("CEP deve ter 8 números")
    d = _get_json(f"cep/v2/{digitos}")
    return {"rua": d.get("street", ""), "bairro": d.get("neighborhood", ""), "cidade": d.get("city", ""),
            "uf": d.get("state", ""), "cep": f"{digitos[:5]}-{digitos[5:]}"}


# ---------------------------------------------------------------- resumo diário por e-mail

def montar_resumo() -> tuple[str, str]:
    hoje = db.hoje()
    ontem = (hoje - timedelta(days=1)).isoformat()
    vencem = db.proximos_vencimentos(0)
    devedores = db.inadimplentes()
    with db.conectar() as con:
        recebido = con.execute("SELECT COALESCE(SUM(valor),0), COUNT(*) FROM pagamentos WHERE data_pagamento = ?",
                               (ontem,)).fetchone()
    fila = db.contar_fila()
    academia = ajustes.obter("academia_nome")
    base = ajustes.empresa()["url_publica"]
    linhas = [
        f"Resumo de {hoje.strftime('%d/%m/%Y')} · {academia}",
        "",
        f"• Recebido ontem: {moeda(recebido[0])} ({recebido[1]} pagamento(s))",
        f"• Vencem hoje: {len(vencem)}" + (": " + ", ".join(a["nome"] for a in vencem[:10]) if vencem else ""),
        f"• Inadimplentes (10+ dias): {len(devedores)} · em aberto {moeda(sum(a['plano_valor'] or 0 for a in devedores))}",
        f"• Avisos esperando você enviar: {fila}" + (f" ({base}/avisos/fila)" if fila and base else ""),
    ]
    for r in db.reajustes_agendados():
        linhas.append(f"• Reajuste agendado: plano {r['plano_nome']} em {data_br(r['vigencia'])}")
    if base:
        linhas += ["", f"Abrir o painel: {base}"]
    return f"{academia}: resumo do dia", "\n".join(linhas)


def enviar_resumo(forcar: bool = False) -> str:
    """Envia o resumo uma vez por dia. Retorna o status (enviado, desligado, sem destino, já enviado...)."""
    from notificacoes import enviar_email  # evita import circular na carga do módulo

    destino = ajustes.obter("resumo_email") or ajustes.obter("email_contato")
    if not forcar and ajustes.obter("resumo_ativo") != "1":
        return "desligado"
    if not destino:
        return "sem destino"
    if ajustes.provedor_email() not in ("smtp", "resend"):
        return "precisa de envio automático de e-mail"
    hoje = db.hoje().isoformat()
    if not forcar and db.get_sistema("resumo_enviado_em") == hoje:
        return "já enviado hoje"
    assunto, texto = montar_resumo()
    status = enviar_email(destino, assunto, texto)
    if status == "enviado":
        db.set_sistema("resumo_enviado_em", hoje)
    return status


# ---------------------------------------------------------------- backup completo

TABELAS_BACKUP = ("planos", "alunos", "pagamentos", "notificacoes", "reajustes")
# ajustes que nunca saem no backup (senhas, tokens e chaves)
NAO_EXPORTAR = {"secret_key", "agenda_token"} | {"cfg_" + k for k in ajustes.SECRETOS}


def backup() -> str:
    dados = {"gerado_em": datetime.now().isoformat(timespec="seconds"), "tabelas": {}}
    with db.conectar() as con:
        for tabela in TABELAS_BACKUP:
            dados["tabelas"][tabela] = [dict(r) for r in con.execute(f"SELECT * FROM {tabela} ORDER BY id").fetchall()]
        dados["tabelas"]["ajustes"] = {r[0]: r[1] for r in con.execute("SELECT chave, valor FROM sistema").fetchall()
                                       if r[0] not in NAO_EXPORTAR}
    return json.dumps(dados, ensure_ascii=False, indent=1, default=str)
