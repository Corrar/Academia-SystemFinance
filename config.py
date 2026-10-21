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
SENHA_PADRAO = ADMIN_SENHA == "admin123"


def _chave_secreta() -> str:
    """Usa SECRET_KEY do .env; se não houver, gera uma aleatória e guarda em .secret_key."""
    chave = _env("SECRET_KEY")
    if chave and chave not in ("dev-inseguro-troque", "troque-por-uma-chave-longa-e-aleatoria"):
        return chave
    arquivo = BASE_DIR / ".secret_key"
    if not arquivo.exists():
        import secrets
        arquivo.write_text(secrets.token_hex(32), encoding="utf-8")
        try:
            arquivo.chmod(0o600)
        except OSError:
            pass
    return arquivo.read_text(encoding="utf-8").strip()


SECRET_KEY = _chave_secreta()
# Defina COOKIE_SEGURO=1 quando o sistema estiver publicado com HTTPS
COOKIE_SEGURO = _env("COOKIE_SEGURO") == "1"

DIAS_INADIMPLENCIA = _int("DIAS_INADIMPLENCIA", 10)
DIAS_AVISO = sorted({int(d) for d in _env("DIAS_AVISO", "-3,0,3,10").split(",") if d.strip().lstrip("-").isdigit()})
# Avisos só em horário comercial (8h às 20h), para não incomodar o aluno
HORA_COBRANCA = min(max(_int("HORA_COBRANCA", 9), 8), 20)
# Depois do último dia de DIAS_AVISO, no máximo N lembretes semanais (evita cobrança abusiva)
MAX_LEMBRETES_SEMANAIS = _int("MAX_LEMBRETES_SEMANAIS", 4)
# Histórico de avisos é apagado depois de N dias (minimização de dados - LGPD)
RETENCAO_AVISOS_DIAS = _int("RETENCAO_AVISOS_DIAS", 365)

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
