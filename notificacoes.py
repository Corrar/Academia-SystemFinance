"""Envio de avisos de vencimento por e-mail (SMTP) e WhatsApp."""
import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from urllib.parse import quote

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

import ajustes
import config
import db

_jinja = Environment(loader=FileSystemLoader(str(config.BASE_DIR / "templates")),
                     autoescape=select_autoescape(["html"]))


# ---------------------------------------------------------------- formatação

def moeda(valor) -> str:
    valor = float(valor or 0)
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(iso: str | None) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "-"


def normalizar_telefone(telefone: str | None) -> str:
    """Retorna só dígitos no formato internacional (ex.: 5511999990000)."""
    digitos = "".join(c for c in (telefone or "") if c.isdigit())
    if not digitos:
        return ""
    if digitos.startswith("0"):
        digitos = digitos.lstrip("0")
    if len(digitos) in (10, 11):  # DDD + número, sem código do país
        digitos = "55" + digitos
    return digitos


def tipo_aviso(dias: int) -> str:
    if dias > 0:
        return "lembrete"
    if dias == 0:
        return "vencimento"
    return "atraso"


def montar_mensagem(aluno: dict) -> tuple[str, str]:
    """Retorna (assunto, corpo) conforme a situação do aluno."""
    dias = db.dias_para_vencer(aluno["data_vencimento"])
    primeiro_nome = aluno["nome"].split()[0]
    venc = data_br(aluno["data_vencimento"])
    valor = moeda(aluno.get("plano_valor"))
    academia = ajustes.obter("academia_nome")

    if dias > 0:
        assunto = f"{academia}: sua mensalidade vence em {dias} dia(s)"
        texto = (
            f"Olá, {primeiro_nome}! 💪\n\n"
            f"Passando para lembrar que sua mensalidade na {academia} vence em "
            f"*{venc}* (daqui a {dias} dia(s)).\nValor: *{valor}*."
        )
    elif dias == 0:
        assunto = f"{academia}: sua mensalidade vence hoje"
        texto = (
            f"Olá, {primeiro_nome}!\n\n"
            f"Sua mensalidade na {academia} vence *hoje ({venc})*.\nValor: *{valor}*."
        )
    else:
        atraso = -dias
        assunto = f"{academia}: mensalidade em atraso há {atraso} dia(s)"
        texto = (
            f"Olá, {primeiro_nome}.\n\n"
            f"Identificamos que sua mensalidade na {academia} venceu em *{venc}* "
            f"e está em aberto há {atraso} dia(s).\nValor: *{valor}*.\n\n"
            "Regularize para continuar treinando sem interrupções."
        )

    pix, telefone = ajustes.obter("chave_pix"), ajustes.obter("academia_telefone")
    if pix:
        texto += f"\n\nPague via PIX: {pix}"
    texto += "\n\nSe já pagou, por favor desconsidere esta mensagem."
    if telefone:
        texto += f"\nDúvidas: {telefone}"
    return assunto, texto


def montar_email_html(aluno: dict) -> str:
    """Versão em HTML do aviso, no mesmo visual do painel."""
    dias = db.dias_para_vencer(aluno["data_vencimento"])
    if dias > 0:
        tom, rotulo, detalhe = "azul", "Vence em breve", f"Faltam {dias} dia(s) para o vencimento"
    elif dias == 0:
        tom, rotulo, detalhe = "amarelo", "Vence hoje", "Último dia para pagar sem atraso"
    else:
        tom, rotulo, detalhe = "vermelho", "Mensalidade em atraso", f"Em aberto há {-dias} dia(s)"
    return _jinja.get_template("email_aviso.html").render(
        aluno=aluno,
        primeiro_nome=aluno["nome"].split()[0],
        academia=ajustes.obter("academia_nome"),
        telefone=ajustes.obter("academia_telefone"),
        pix=ajustes.obter("chave_pix"),
        vencimento=data_br(aluno["data_vencimento"]),
        valor=moeda(aluno.get("plano_valor")),
        plano=aluno.get("plano_nome") or "Mensalidade",
        tom=tom, rotulo=rotulo, detalhe=detalhe, dias=dias,
    )


def link_whatsapp(aluno: dict) -> str | None:
    """Link wa.me com a mensagem pronta (envio manual pelo celular/WhatsApp Web)."""
    numero = normalizar_telefone(aluno.get("telefone"))
    if not numero:
        return None
    _, texto = montar_mensagem(aluno)
    return f"https://wa.me/{numero}?text={quote(texto)}"


# ---------------------------------------------------------------- e-mail

def enviar_email(destino: str, assunto: str, texto: str, html: str | None = None) -> str:
    """Retorna 'enviado' ou 'simulado' (SMTP não configurado). Lança exceção em caso de erro."""
    cfg = ajustes.smtp()
    if not cfg["host"]:
        return "simulado"
    msg = EmailMessage()
    msg["From"] = f"{ajustes.obter('academia_nome')} <{cfg['remetente']}>"
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.set_content(texto.replace("*", ""))
    if html:
        msg.add_alternative(html, subtype="html")
    contexto = ssl.create_default_context()
    if cfg["seguranca"] == "ssl":
        servidor = smtplib.SMTP_SSL(cfg["host"], cfg["porta"], context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(cfg["host"], cfg["porta"], timeout=30)
    with servidor as s:
        if cfg["seguranca"] == "tls":
            s.starttls(context=contexto)
        if cfg["usuario"]:
            s.login(cfg["usuario"], cfg["senha"])
        s.send_message(msg)
    return "enviado"


# ---------------------------------------------------------------- WhatsApp

def _verificar(r: requests.Response) -> None:
    """Erro HTTP com a resposta do provedor, para aparecer no histórico de avisos."""
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        corpo = r.json()
    except ValueError:
        return
    if isinstance(corpo, dict) and corpo.get("error"):  # Z-API responde 200 com {"error": ...}
        raise RuntimeError(str(corpo.get("message") or corpo["error"])[:300])


def _zapi(cfg: dict, numero: str, texto: str) -> None:
    url = f"https://api.z-api.io/instances/{cfg['zapi_instancia']}/token/{cfg['zapi_token']}/send-text"
    headers = {"Client-Token": cfg["zapi_client_token"]} if cfg["zapi_client_token"] else {}
    _verificar(requests.post(url, json={"phone": numero, "message": texto}, headers=headers, timeout=30))


def _evolution(cfg: dict, numero: str, texto: str) -> None:
    url = f"{cfg['evolution_url']}/message/sendText/{cfg['evolution_instancia']}"
    _verificar(requests.post(url, json={"number": numero, "text": texto},
                             headers={"apikey": cfg["evolution_apikey"]}, timeout=30))


def _meta(cfg: dict, numero: str, texto: str, aluno: dict) -> None:
    url = f"https://graph.facebook.com/v21.0/{cfg['meta_phone_id']}/messages"
    if cfg["meta_template"]:
        # Template aprovado com 3 variáveis: {{1}} nome, {{2}} vencimento, {{3}} valor
        corpo = {
            "messaging_product": "whatsapp", "to": numero, "type": "template",
            "template": {
                "name": cfg["meta_template"],
                "language": {"code": cfg["meta_template_idioma"]},
                "components": [{"type": "body", "parameters": [
                    {"type": "text", "text": aluno["nome"].split()[0]},
                    {"type": "text", "text": data_br(aluno["data_vencimento"])},
                    {"type": "text", "text": moeda(aluno.get("plano_valor"))},
                ]}],
            },
        }
    else:
        corpo = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto}}
    _verificar(requests.post(url, json=corpo, headers={"Authorization": f"Bearer {cfg['meta_token']}"}, timeout=30))


def _twilio(cfg: dict, numero: str, texto: str) -> None:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['twilio_sid']}/Messages.json"
    remetente = "+" + "".join(c for c in cfg["twilio_numero"] if c.isdigit())
    dados = {"From": f"whatsapp:{remetente}", "To": f"whatsapp:+{numero}", "Body": texto}
    _verificar(requests.post(url, data=dados, auth=(cfg["twilio_sid"], cfg["twilio_token"]), timeout=30))


def enviar_whatsapp(numero: str, texto: str, aluno: dict) -> str:
    """Retorna 'enviado' ou 'simulado'. Lança exceção em caso de erro."""
    cfg = ajustes.whatsapp()
    provedor = cfg["provedor"]
    if provedor == "zapi":
        _zapi(cfg, numero, texto)
    elif provedor == "evolution":
        _evolution(cfg, numero, texto)
    elif provedor == "meta":
        _meta(cfg, numero, texto, aluno)
    elif provedor == "twilio":
        _twilio(cfg, numero, texto)
    else:
        return "simulado"
    return "enviado"


# ---------------------------------------------------------------- orquestração

def registrar(aluno_id, canal, tipo, chave, destino, status, mensagem, erro=None) -> None:
    with db.conectar() as con:
        con.execute(
            "INSERT INTO notificacoes (aluno_id, canal, tipo, chave, destino, status, mensagem, erro) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (aluno_id, canal, tipo, chave, destino, status, mensagem, erro),
        )


def ja_enviado(aluno_id: int, chave: str, canal: str) -> bool:
    with db.conectar() as con:
        return con.execute(
            "SELECT 1 FROM notificacoes WHERE aluno_id = ? AND chave = ? AND canal = ? "
            "AND status IN ('enviado','simulado') LIMIT 1",
            (aluno_id, chave, canal),
        ).fetchone() is not None


def notificar(aluno: dict, canais=("email", "whatsapp"), chave: str | None = None,
              tipo: str | None = None) -> dict:
    """Envia o aviso nos canais pedidos. Retorna {canal: status} (status ou 'sem contato')."""
    assunto, texto = montar_mensagem(aluno)
    tipo = tipo or tipo_aviso(db.dias_para_vencer(aluno["data_vencimento"]))
    resultado = {}

    for canal in canais:
        if chave and ja_enviado(aluno["id"], chave, canal):
            resultado[canal] = "já enviado"
            continue
        if canal == "email":
            destino = (aluno.get("email") or "").strip()
            enviar = lambda: enviar_email(destino, assunto, texto, montar_email_html(aluno))
        else:
            destino = normalizar_telefone(aluno.get("telefone"))
            enviar = lambda: enviar_whatsapp(destino, texto, aluno)
        if not destino:
            resultado[canal] = "sem contato"
            continue
        try:
            status = enviar()
            registrar(aluno["id"], canal, tipo, chave, destino, status, texto)
        except Exception as e:  # noqa: BLE001 - registra qualquer falha de envio
            status = "erro"
            registrar(aluno["id"], canal, tipo, chave, destino, status, texto, str(e)[:500])
        resultado[canal] = status
    return resultado
