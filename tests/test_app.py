"""Testes de ponta a ponta do painel (rodam com SQLite)."""
import json

import pytest

import db
import notificacoes
from conftest import csrf

PAGINAS = ["/", "/alunos", "/alunos?status=inadimplente", "/alunos/3", "/alunos/3/editar", "/alunos/novo",
           "/validade?q=a", "/financeiro", "/avisos", "/planos", "/configuracoes", "/configuracoes/email-preview?aluno=3"]


@pytest.mark.parametrize("url", ["/privacidade", "/termos", "/reembolso"])
def test_documentos_publicos_sem_login_e_sem_cookie(cliente, url):
    r = cliente.get(url)
    assert r.status_code == 200
    assert "Set-Cookie" not in r.headers


def test_painel_exige_login(cliente):
    r = cliente.get("/")
    assert r.status_code == 302 and "/login" in r.location


@pytest.mark.parametrize("url", PAGINAS)
def test_paginas_do_painel_abrem(logado, url):
    r = logado.get(url)
    assert r.status_code == 200, url
    assert r.headers["Cache-Control"] == "no-store"


def test_cabecalhos_de_seguranca(logado):
    h = logado.get("/").headers
    for nome in ("Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"):
        assert nome in h


def test_bloqueio_apos_cinco_senhas_erradas(cliente):
    db.limpar_falhas_login("127.0.0.1")
    cliente.get("/login")
    for _ in range(5):
        cliente.post("/login", data={"usuario": "admin", "senha": "errada", "csrf": csrf(cliente)})
    r = cliente.post("/login", data={"usuario": "admin", "senha": "senha-de-teste", "csrf": csrf(cliente)})
    assert r.status_code == 429
    db.limpar_falhas_login("127.0.0.1")


def test_post_sem_csrf_e_recusado(logado):
    assert logado.post("/cobranca/executar").status_code == 400


def test_cron_exige_segredo(cliente):
    assert cliente.get("/api/cron/cobranca").status_code == 401
    r = cliente.get("/api/cron/cobranca", headers={"Authorization": "Bearer segredo-cron-teste"})
    assert r.status_code == 200 and "avaliados" in r.get_json()


def test_pagamento_renova_e_estorno_desfaz(logado):
    aluno = db.inadimplentes()[0]
    antes = aluno["data_vencimento"]
    logado.post(f"/alunos/{aluno['id']}/pagamento", data={"csrf": csrf(logado), "valor": "120,00",
                "data_pagamento": db.hoje().isoformat(), "nova_validade": "2099-01-31", "forma": "PIX"})
    assert db.obter_aluno(aluno["id"])["data_vencimento"] == "2099-01-31"
    ultimo = db.pagamentos_aluno(aluno["id"])[0]
    logado.post(f"/pagamentos/{ultimo['id']}/estornar", data={"csrf": csrf(logado)})
    assert db.obter_aluno(aluno["id"])["data_vencimento"] == antes


def test_aviso_respeita_quem_nao_autorizou(logado):
    r = logado.post("/alunos/novo", data={"csrf": csrf(logado), "nome": "Sem WhatsApp", "telefone": "11911112222",
                    "email": "sem@exemplo.com", "plano_id": "1", "data_inscricao": "2026-01-01",
                    "data_vencimento": "2026-02-01", "aceita_email": "1"})
    aluno = db.obter_aluno(int(r.location.rsplit("/", 1)[1]))
    resultado = notificacoes.notificar(aluno)
    assert resultado["whatsapp"] == "não autorizado"
    assert resultado["email"] == "simulado"


def test_exportar_e_anonimizar(logado):
    aluno_id = db.buscar_alunos()[0]["id"]
    dados = json.loads(logado.get(f"/alunos/{aluno_id}/exportar").data)
    assert {"aluno", "pagamentos", "avisos"} <= set(dados)
    logado.post(f"/alunos/{aluno_id}/anonimizar", data={"csrf": csrf(logado)})
    anon = db.obter_aluno(aluno_id)
    assert anon["nome"].startswith("Aluno removido") and anon["email"] is None and anon["cpf"] is None


def test_mensagem_de_cobranca_tem_valor_e_vencimento():
    aluno = db.obter_aluno(3)
    _, texto = notificacoes.montar_mensagem(aluno)
    assert notificacoes.data_br(aluno["data_vencimento"]) in texto
    assert "R$" in texto
