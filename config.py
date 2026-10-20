"""Configurações lidas do arquivo .env (ou variáveis de ambiente)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _carregar_env(caminho: Path) -> None:
    """Leitor simples de .env (CHAVE=valor), sem dependências externas."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(BASE_DIR / ".env")


def _env(chave: str, padrao: str = "") -> str:
    return os.environ.get(chave, padrao)


def _int(chave: str, padrao: int) -> int:
    try:
        return int(_env(chave, str(padrao)))
    except ValueError:
        return padrao


DB_PATH = _env("DB_PATH", str(BASE_DIR / "academia.db"))

ACADEMIA_NOME = _env("ACADEMIA_NOME", "Minha Academia")
ACADEMIA_TELEFONE = _env("ACADEMIA_TELEFONE")
CHAVE_PIX = _env("CHAVE_PIX")

ADMIN_USUARIO = _env("ADMIN_USUARIO", "admin")
ADMIN_SENHA = _env("ADMIN_SENHA", "admin123")
SECRET_KEY = _env("SECRET_KEY", "dev-inseguro-troque")

DIAS_INADIMPLENCIA = _int("DIAS_INADIMPLENCIA", 10)
DIAS_AVISO = sorted({int(d) for d in _env("DIAS_AVISO", "-3,0,3,10").split(",") if d.strip().lstrip("-").isdigit()})
HORA_COBRANCA = _int("HORA_COBRANCA", 9)

SMTP_HOST = _env("SMTP_HOST")
SMTP_PORTA = _int("SMTP_PORTA", 587)
SMTP_USUARIO = _env("SMTP_USUARIO")
SMTP_SENHA = _env("SMTP_SENHA")
SMTP_REMETENTE = _env("SMTP_REMETENTE") or SMTP_USUARIO
SMTP_SEGURANCA = _env("SMTP_SEGURANCA", "tls").lower()

WHATSAPP_PROVEDOR = _env("WHATSAPP_PROVEDOR", "simulado").lower()
ZAPI_INSTANCIA = _env("ZAPI_INSTANCIA")
ZAPI_TOKEN = _env("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = _env("ZAPI_CLIENT_TOKEN")
EVOLUTION_URL = _env("EVOLUTION_URL").rstrip("/")
EVOLUTION_INSTANCIA = _env("EVOLUTION_INSTANCIA")
EVOLUTION_APIKEY = _env("EVOLUTION_APIKEY")
META_TOKEN = _env("META_TOKEN")
META_PHONE_ID = _env("META_PHONE_ID")
META_TEMPLATE = _env("META_TEMPLATE")
META_TEMPLATE_IDIOMA = _env("META_TEMPLATE_IDIOMA", "pt_BR")
TWILIO_SID = _env("TWILIO_SID")
TWILIO_TOKEN = _env("TWILIO_TOKEN")
TWILIO_NUMERO = _env("TWILIO_NUMERO")
