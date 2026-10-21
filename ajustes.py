"""Ajustes editáveis pela tela de Configurações.

O valor salvo no banco tem prioridade; se não houver, vale o do .env.
"""
import config
import db

# chave do ajuste -> atributo correspondente em config.py (.env)
CAMPOS = {
    "academia_nome": "ACADEMIA_NOME",
    "razao_social": None,
    "cnpj": None,
    "endereco": None,
    "email_contato": None,
    "url_publica": "URL_PUBLICA",
    "encarregado_nome": None,
    "encarregado_email": None,
    "cidade_foro": None,
    "retencao_cancelamento_pct": None,
    "prazo_reembolso_dias": None,
    "academia_telefone": "ACADEMIA_TELEFONE",
    "chave_pix": "CHAVE_PIX",
    "email_provedor": "EMAIL_PROVEDOR",
    "resend_api_key": "RESEND_API_KEY",
    "resend_remetente": "RESEND_REMETENTE",
    "smtp_host": "SMTP_HOST",
    "smtp_porta": "SMTP_PORTA",
    "smtp_usuario": "SMTP_USUARIO",
    "smtp_senha": "SMTP_SENHA",
    "smtp_remetente": "SMTP_REMETENTE",
    "smtp_seguranca": "SMTP_SEGURANCA",
    "wa_provedor": "WHATSAPP_PROVEDOR",
    "zapi_instancia": "ZAPI_INSTANCIA",
    "zapi_token": "ZAPI_TOKEN",
    "zapi_client_token": "ZAPI_CLIENT_TOKEN",
    "evolution_url": "EVOLUTION_URL",
    "evolution_instancia": "EVOLUTION_INSTANCIA",
    "evolution_apikey": "EVOLUTION_APIKEY",
    "meta_token": "META_TOKEN",
    "meta_phone_id": "META_PHONE_ID",
    "meta_template": "META_TEMPLATE",
    "meta_template_idioma": "META_TEMPLATE_IDIOMA",
    "twilio_sid": "TWILIO_SID",
    "twilio_token": "TWILIO_TOKEN",
    "twilio_numero": "TWILIO_NUMERO",
}

PADROES = {"prazo_reembolso_dias": "30", "retencao_cancelamento_pct": "0"}

# Dados obrigatórios para identificar a empresa nos documentos e e-mails
DADOS_LEGAIS = ("razao_social", "cnpj", "endereco", "email_contato", "encarregado_nome", "encarregado_email")

# Senhas e tokens: nunca voltam para a tela; campo em branco = manter o atual
SECRETOS = {"smtp_senha", "resend_api_key", "zapi_token", "zapi_client_token", "evolution_apikey", "meta_token",
            "twilio_token"}

# "manual": o sistema monta a mensagem e coloca na fila de envio; você envia com um toque
# pelo seu WhatsApp ou e-mail (funciona sem contratar nada). "simulado": só registra.
PROVEDORES_EMAIL = ("manual", "smtp", "resend", "simulado")
PROVEDORES_WHATSAPP = ("manual", "zapi", "evolution", "meta", "twilio", "simulado")


def obter(chave: str) -> str:
    valor = db.get_sistema("cfg_" + chave)
    if valor is None:
        valor = getattr(config, CAMPOS[chave]) if CAMPOS[chave] else PADROES.get(chave, "")
    return str(valor or "")


def salvar(valores: dict) -> None:
    for chave, valor in valores.items():
        if chave in CAMPOS:
            db.set_sistema("cfg_" + chave, (valor or "").strip())


def provedor_email() -> str:
    escolhido = obter("email_provedor").lower()
    if escolhido in PROVEDORES_EMAIL:
        return escolhido
    return "smtp" if obter("smtp_host") else "manual"


def resend() -> dict:
    return {"api_key": obter("resend_api_key"), "remetente": obter("resend_remetente")}


def smtp() -> dict:
    porta = obter("smtp_porta")
    usuario = obter("smtp_usuario")
    return {
        "host": obter("smtp_host"),
        "porta": int(porta) if porta.isdigit() else 587,
        "usuario": usuario,
        "senha": obter("smtp_senha"),
        "remetente": obter("smtp_remetente") or usuario,
        "seguranca": (obter("smtp_seguranca") or "tls").lower(),
    }


def whatsapp() -> dict:
    provedor = obter("wa_provedor").lower()
    cfg = {k: obter(k) for k in CAMPOS if k.split("_")[0] in ("zapi", "evolution", "meta", "twilio")}
    cfg["provedor"] = provedor if provedor in PROVEDORES_WHATSAPP else "manual"
    cfg["evolution_url"] = cfg["evolution_url"].rstrip("/")
    cfg["meta_template_idioma"] = cfg["meta_template_idioma"] or "pt_BR"
    return cfg


def empresa() -> dict:
    """Dados da empresa usados nos documentos legais, rodapés e e-mails."""
    dados = {k: obter(k) for k in ("academia_nome", "academia_telefone", "chave_pix") + DADOS_LEGAIS
             + ("url_publica", "cidade_foro", "retencao_cancelamento_pct", "prazo_reembolso_dias")}
    dados["url_publica"] = dados["url_publica"].rstrip("/")
    dados["faltando"] = [k for k in DADOS_LEGAIS if not dados[k]]
    return dados
