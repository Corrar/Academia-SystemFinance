"""Configuração dos testes: banco SQLite temporário com os alunos de demonstração."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Precisa vir antes de importar o app: config.py lê o ambiente na importação
_pasta = tempfile.mkdtemp(prefix="academia-testes-")
os.environ["DB_PATH"] = os.path.join(_pasta, "teste.db")
os.environ["ADMIN_USUARIO"] = "admin"
os.environ["ADMIN_SENHA"] = "senha-de-teste"
os.environ["CRON_SECRET"] = "segredo-cron-teste"
for var in ("DATABASE_URL", "POSTGRES_URL", "VERCEL", "SMTP_HOST", "URL_PUBLICA"):
    os.environ.pop(var, None)
os.environ["DEBUG"] = "1"  # sem agendador em segundo plano durante os testes

import seed  # noqa: E402
import app as aplicacao  # noqa: E402

seed.main()


@pytest.fixture
def cliente():
    c = aplicacao.app.test_client()
    yield c


def csrf(c):
    with c.session_transaction() as s:
        return s.get("csrf")


@pytest.fixture
def logado(cliente):
    import db
    db.limpar_falhas_login("127.0.0.1")
    cliente.get("/login")
    r = cliente.post("/login", data={"usuario": "admin", "senha": "senha-de-teste", "csrf": csrf(cliente)})
    assert r.status_code == 302
    return cliente
