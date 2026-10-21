"""Ajustes editáveis pela tela de Configurações.

O valor salvo no banco tem prioridade; se não houver, vale o do .env.
"""
import config
import db

# chave do ajuste -> atributo correspondente em config.py (.env)
CAMPOS = {
    "academia_nome": "ACADEMIA_NOME",
    "academia_telefone": "ACADEMIA_TELEFONE",
    "chave_pix": "CHAVE_PIX",
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

# Senhas e tokens: nunca voltam para a tela; campo em branco = manter o atual
SECRETOS = {"smtp_senha", "zapi_token", "zapi_client_token", "evolution_apikey", "meta_token", "twilio_token"}

PROVEDORES_WHATSAPP = ("simulado", "zapi", "evolution", "meta", "twilio")


def obter(chave: str) -> str:
    valor = db.get_sistema("cfg_" + chave)
    if valor is None:
        valor = getattr(config, CAMPOS[chave])
    return str(valor or "")


def salvar(valores: dict) -> None:
    for chave, valor in valores.items():
        if chave in CAMPOS:
            db.set_sistema("cfg_" + chave, (valor or "").strip())


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
    cfg["provedor"] = provedor if provedor in PROVEDORES_WHATSAPP else "simulado"
    cfg["evolution_url"] = cfg["evolution_url"].rstrip("/")
    cfg["meta_template_idioma"] = cfg["meta_template_idioma"] or "pt_BR"
    return cfg
