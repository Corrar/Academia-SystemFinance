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
}


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
