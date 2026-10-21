"""Testes de ponta a ponta do painel (rodam com SQLite)."""
import json

import pytest

import db
import notificacoes
from conftest import csrf

PAGINAS = ["/", "/alunos", "/alunos?status=inadimplente", "/alunos/3", "/alunos/3/editar", "/alunos/novo",
           "/validade?q=a", "/financeiro", "/avisos", "/planos", "/configuracoes", "/configuracoes/email-preview?aluno=3",
           "/alunos?plano=1&contato=whatsapp&ordem=vencimento&de=2026-01-01", "/alunos/cadastro-rapido",
           "/alunos/cadastro-rapido?aba=colar", "/alunos/cadastro-rapido?aba=arquivo", "/avisos/fila",
           "/avisos?canal=whatsapp&status=pendente&tipo=atraso", "/reajustes", "/novidades", "/integracoes"]


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
    assert resultado["email"] == "pendente"  # modo manual (padrão): vai para a fila de envio


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


# ---------------------------------------------------------------- cadastro rápido (fichas em papel)

def test_ler_planilha_colada_reconhece_colunas_datas_e_planos():
    import importacao
    planos = db.listar_planos()
    texto = "Nome\tWhatsApp\tVencimento\tPlano\nAna Paula\t11 98765-4321\t05/12/2026\tmensal\nBeto\t\t2026-11-30\t330"
    linhas = importacao.ler_texto(texto, planos)
    assert [l["nome"] for l in linhas] == ["Ana Paula", "Beto"]
    assert linhas[0]["telefone"] == "(11) 98765-4321"
    assert linhas[0]["data_vencimento"] == "2026-12-05" and linhas[1]["data_vencimento"] == "2026-11-30"
    assert linhas[0]["plano_id"] == str(next(p["id"] for p in planos if p["nome"] == "Mensal"))
    assert linhas[1]["plano_id"] == str(next(p["id"] for p in planos if p["valor"] == 330))


def test_ler_planilha_xlsx_e_data_do_excel():
    import io
    from datetime import date
    from openpyxl import Workbook
    import importacao
    livro = Workbook()
    aba = livro.active
    aba.append(["Nome completo", "Celular", "E-mail", "Válido até"])
    aba.append(["Carla Dias", 11912345678, "CARLA@EXEMPLO.COM", date(2026, 12, 20)])
    aba.append(["Davi Rocha", "(21) 3333-4444", "", 46300])  # número de série do Excel
    arquivo = io.BytesIO()
    livro.save(arquivo)
    linhas = importacao.ler_arquivo("fichas.xlsx", arquivo.getvalue(), db.listar_planos())
    assert linhas[0]["telefone"] == "(11) 91234-5678" and linhas[0]["email"] == "carla@exemplo.com"
    assert linhas[0]["data_vencimento"] == "2026-12-20"
    assert linhas[1]["data_vencimento"] == "2026-10-05"


def test_cadastro_rapido_valida_e_salva_varias_fichas(logado):
    antes = len(db.buscar_alunos())
    base = {"csrf": csrf(logado), "acao": "salvar", "plano_padrao": "1", "aceita_whatsapp": "1"}
    # ficha sem vencimento e telefone repetido: volta para revisão sem gravar nada
    r = logado.post("/alunos/cadastro-rapido", data={**base,
        "nome": ["Fulano Papel", "Ciclano Papel"], "telefone": ["(11) 97000-0001", "11970000001"],
        "email": ["", ""], "cpf": ["", ""], "plano_id": ["", ""], "data_vencimento": ["2026-12-01", ""],
        "data_inscricao": ["", ""]})
    assert r.status_code == 200 and "repetido" in r.get_data(as_text=True)
    assert len(db.buscar_alunos()) == antes
    r = logado.post("/alunos/cadastro-rapido", data={**base,
        "nome": ["Fulano Papel", "Ciclano Papel", ""], "telefone": ["(11) 97000-0001", "(11) 97000-0002", ""],
        "email": ["fulano@exemplo.com", "", ""], "cpf": ["", "", ""], "plano_id": ["", "2", ""],
        "data_vencimento": ["2026-12-01", "2026-12-15", ""], "data_inscricao": ["", "2025-03-10", ""]})
    assert r.status_code == 302
    novos = {a["nome"]: a for a in db.buscar_alunos("Papel")}
    assert set(novos) == {"Fulano Papel", "Ciclano Papel"}
    assert novos["Fulano Papel"]["plano_id"] == 1 and novos["Ciclano Papel"]["plano_id"] == 2
    assert novos["Fulano Papel"]["aceita_whatsapp"] == 1 and novos["Fulano Papel"]["aceita_email"] == 0
    assert "ficha em papel" in novos["Fulano Papel"]["observacoes"]
    # a mesma ficha de novo é recusada como duplicada
    r = logado.post("/alunos/cadastro-rapido", data={**base, "nome": ["Fulano Outra Vez"], "telefone": ["11970000001"],
        "email": [""], "cpf": [""], "plano_id": [""], "data_vencimento": ["2026-12-01"], "data_inscricao": [""]})
    assert "já cadastrado" in r.get_data(as_text=True)


def test_colar_do_excel_mostra_revisao_sem_gravar(logado):
    antes = len(db.buscar_alunos())
    r = logado.post("/alunos/cadastro-rapido", data={"csrf": csrf(logado), "acao": "colar", "plano_padrao": "1",
                                                      "texto": "Joana Revisão\t(11) 96000-1111\t\tMensal\t01/02/2027"})
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "Joana Revisão" in html and "Lemos" in html
    assert len(db.buscar_alunos()) == antes


# ---------------------------------------------------------------- filtros

def test_filtros_de_busca(logado):
    todos = db.buscar_alunos()
    so_mensal = db.buscar_alunos(plano_id=1)
    assert so_mensal and all(a["plano_id"] == 1 for a in so_mensal) and len(so_mensal) <= len(todos)
    ordenados = db.buscar_alunos(ordem="vencimento")
    assert [a["data_vencimento"] for a in ordenados] == sorted(a["data_vencimento"] for a in ordenados)
    corte = ordenados[len(ordenados) // 2]["data_vencimento"]
    assert all(a["data_vencimento"] >= corte for a in db.buscar_alunos(venc_de=corte))
    assert all(a["telefone"] and a["aceita_whatsapp"] for a in db.buscar_alunos(contato="whatsapp"))
    r = logado.get("/alunos/exportar.csv?plano=1")
    assert r.status_code == 200 and r.mimetype == "text/csv" and "Nome;WhatsApp" in r.get_data(as_text=True)


# ---------------------------------------------------------------- fila de envio (modo manual)

def test_modo_manual_coloca_na_fila_e_abrir_marca_enviado(logado):
    aluno = next(a for a in db.inadimplentes() if a["telefone"] and a["aceita_whatsapp"])
    res = notificacoes.notificar(aluno, canais=("whatsapp",), tipo="manual")
    assert res["whatsapp"] == "pendente"
    item = [n for n in db.fila_envio() if n["aluno_id"] == aluno["id"]][-1]
    link = notificacoes.link_envio(item)
    assert link.startswith("https://wa.me/55") and "text=" in link
    assert item["id"] in [n["id"] for n in db.fila_envio()]
    r = logado.post(f"/avisos/{item['id']}/marcar", data={"csrf": csrf(logado)}, headers={"X-Requested-With": "fetch"})
    assert r.get_json()["ok"] is True
    assert item["id"] not in [n["id"] for n in db.fila_envio()]
    email = {"canal": "email", "destino": "a@b.com", "assunto": "Olá & tchau", "mensagem": "Linha *1*"}
    assert notificacoes.link_envio(email) == "mailto:a@b.com?subject=Ol%C3%A1%20%26%20tchau&body=Linha%201"


def test_comprovante_de_pagamento_vai_para_a_fila(logado):
    aluno = next(a for a in db.inadimplentes() if a["telefone"] and a["aceita_whatsapp"])
    logado.post(f"/alunos/{aluno['id']}/pagamento", data={"csrf": csrf(logado), "valor": "120,00", "forma": "PIX",
                "data_pagamento": db.hoje().isoformat(), "nova_validade": "2099-03-01", "comprovante": "1"})
    fila = db.fila_envio(aluno["id"])
    assert any(n["tipo"] == "comprovante" and "01/03/2099" in n["mensagem"] for n in fila)


# ---------------------------------------------------------------- reajuste

def test_reajuste_avisa_mensalistas_e_aplica_na_vigencia(logado):
    from datetime import timedelta
    import cobranca
    plano = next(p for p in db.listar_planos() if p["nome"] == "Trimestral")
    alunos = [a for a in db.buscar_alunos(plano_id=plano["id"]) if a["ativo"]]
    vigencia = (db.hoje() + timedelta(days=40)).isoformat()
    r = logado.post("/reajustes", data={"csrf": csrf(logado), f"plano_{plano['id']}": "1", f"valor_{plano['id']}": "360,00",
                                        "vigencia": vigencia, "canal_whatsapp": "1", "canal_email": "1",
                                        "observacao": "Aparelhos novos & manutenção"})
    assert r.status_code == 302
    reajuste = next(x for x in db.reajustes_agendados() if x["plano_id"] == plano["id"])
    assert reajuste["valor_novo"] == 360 and reajuste["avisados"] >= 1
    avisos = db.notificacoes_recentes(500, tipo="reajuste")
    assert avisos and all("R$ 360,00" in n["mensagem"] for n in avisos)
    assert {n["aluno_id"] for n in avisos} <= {a["id"] for a in alunos}
    # vencimento depois da vigência já cobra o valor novo; antes, o atual
    assert db.valor_do_plano(plano["id"], vigencia) == 360
    assert db.valor_do_plano(plano["id"], db.hoje().isoformat()) == plano["valor"]
    # segundo reajuste para o mesmo plano é recusado enquanto o primeiro estiver agendado
    logado.post("/reajustes", data={"csrf": csrf(logado), f"plano_{plano['id']}": "1", f"valor_{plano['id']}": "400",
                                    "vigencia": vigencia, "canal_whatsapp": "1"})
    assert len([x for x in db.reajustes_agendados() if x["plano_id"] == plano["id"]]) == 1
    # na vigência, a cobrança diária aplica o valor novo
    with db.conectar() as con:
        con.execute("UPDATE reajustes SET vigencia = ? WHERE id = ?", (db.hoje().isoformat(), reajuste["id"]))
    assert cobranca.executar_cobranca()["reajustes_aplicados"] == 1
    assert next(p for p in db.listar_planos() if p["id"] == plano["id"])["valor"] == 360
    assert not [x for x in db.reajustes_agendados() if x["plano_id"] == plano["id"]]


def test_reajuste_exige_vigencia_futura(logado):
    plano = db.listar_planos()[0]
    logado.post("/reajustes", data={"csrf": csrf(logado), f"plano_{plano['id']}": "1", f"valor_{plano['id']}": "999",
                                    "vigencia": db.hoje().isoformat(), "canal_email": "1"})
    assert not [x for x in db.reajustes_agendados() if x["valor_novo"] == 999]


# ---------------------------------------------------------------- versão, saúde e app

def test_versao_e_saude_publicas(cliente):
    import versao
    r = cliente.get("/api/versao")
    assert r.status_code == 200 and r.get_json()["versao"] == versao.VERSAO
    r = cliente.get("/api/saude")
    assert r.get_json() == {"ok": True, "banco": "ok", "versao": versao.VERSAO}
    assert "Set-Cookie" not in r.headers
    assert versao.secao(versao.VERSAO), "a versão do arquivo VERSION precisa de uma seção no CHANGELOG.md"
    assert versao.historico()[0]["versao"] == versao.VERSAO


def test_versao_aparece_no_painel_e_novidades(logado):
    import versao
    assert f"v{versao.VERSAO}" in logado.get("/").get_data(as_text=True)
    html = logado.get("/novidades").get_data(as_text=True)
    assert "Versão atual" in html and "<strong>PIX copia e cola" in html


def test_app_instalavel(cliente):
    m = cliente.get("/manifest.webmanifest")
    assert m.status_code == 200 and m.get_json()["display"] == "standalone"
    sw = cliente.get("/sw.js")
    assert sw.status_code == 200 and "__VERSAO__" not in sw.get_data(as_text=True)
    assert cliente.get("/offline").status_code == 200


# ---------------------------------------------------------------- PIX

def test_pix_copia_e_cola_valido():
    import pix
    assert pix.crc16("123456789") == "29B1"  # valor de referência do CRC-16/CCITT-FALSE
    assert pix.normalizar_chave("(11) 98888-7777") == "+5511988887777"
    assert pix.normalizar_chave("529.982.247-25") == "52998224725"
    assert pix.normalizar_chave("12.345.678/0001-95") == "12345678000195"
    codigo = pix.codigo(135.5, "MENSALIDADE", chave="Pix@Academia.com")
    assert codigo.startswith("000201") and "br.gov.bcb.pix" in codigo and "pix@academia.com" in codigo
    assert "5406135.50" in codigo and "5802BR" in codigo
    assert pix.crc16(codigo[:-4]) == codigo[-4:]
    assert pix.qr_png(codigo)[:4] == b"\x89PNG"


def test_pix_nos_avisos_e_na_ficha(logado):
    import ajustes
    ajustes.salvar({"chave_pix": "pix@academia.com", "pix_cidade": "São Paulo"})
    aluno = db.inadimplentes()[0]
    _, texto = notificacoes.montar_mensagem(aluno)
    assert "PIX copia e cola" in texto and "br.gov.bcb.pix" in texto
    html = logado.get(f"/alunos/{aluno['id']}").get_data(as_text=True)
    assert "Receber por PIX" in html and "<svg" in html
    r = logado.get("/pix/qr/12000.png")
    assert r.status_code == 200 and r.mimetype == "image/png"
    assert logado.get("/pix/qr/0.png").status_code == 404


# ---------------------------------------------------------------- agenda, backup, CNPJ e resumo

def test_agenda_ical_com_token(logado, cliente):
    import integracoes
    token = integracoes.agenda_token()
    assert cliente.get("/agenda/errado.ics").status_code == 404
    r = cliente.get(f"/agenda/{token}.ics")
    texto = r.get_data(as_text=True)
    assert r.mimetype == "text/calendar" and texto.startswith("BEGIN:VCALENDAR") and "Vence:" in texto
    assert all(len(l.encode()) <= 75 for l in texto.split("\r\n"))
    novo = integracoes.agenda_token(novo=True)
    assert cliente.get(f"/agenda/{token}.ics").status_code == 404 and cliente.get(f"/agenda/{novo}.ics").status_code == 200


def test_backup_sem_segredos(logado):
    import ajustes
    ajustes.salvar({"smtp_senha": "segredo-que-nao-pode-sair"})
    r = logado.get("/integracoes/backup.json")
    texto = r.get_data(as_text=True)
    dados = json.loads(texto)
    assert {"alunos", "pagamentos", "planos", "notificacoes", "reajustes"} <= set(dados["tabelas"])
    assert "segredo-que-nao-pode-sair" not in texto and "secret_key" not in dados["tabelas"]["ajustes"]


def test_cnpj_pela_brasilapi(logado, monkeypatch):
    import integracoes

    class Resposta:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"razao_social": "ACADEMIA CORPUS LTDA", "descricao_tipo_de_logradouro": "RUA", "logradouro": "DAS FLORES",
                    "numero": "120", "complemento": "", "bairro": "CENTRO", "municipio": "SAO PAULO", "uf": "SP",
                    "cep": "01001000", "ddd_telefone_1": "1140000000", "descricao_situacao_cadastral": "ATIVA"}
    monkeypatch.setattr(integracoes.requests, "get", lambda *a, **k: Resposta())
    d = logado.get("/api/cnpj/12345678000195").get_json()
    assert d["razao_social"] == "Academia Corpus Ltda." and d["cidade_foro"] == "Sao Paulo/SP"
    assert d["endereco"].startswith("Rua das Flores, 120 – Centro") and d["academia_telefone"] == "(11) 4000-0000"
    assert logado.get("/api/cnpj/123").status_code == 400


def test_resumo_diario_so_com_email_automatico(monkeypatch):
    import ajustes
    import integracoes
    ajustes.salvar({"resumo_ativo": "1", "resumo_email": "dono@academia.com", "email_provedor": "manual"})
    assert integracoes.enviar_resumo() == "precisa de envio automático de e-mail"
    enviados = []
    monkeypatch.setattr(notificacoes, "enviar_email", lambda *a, **k: enviados.append(a) or "enviado")
    ajustes.salvar({"email_provedor": "smtp", "smtp_host": "smtp.exemplo.com"})
    db.set_sistema("resumo_enviado_em", "")
    assert integracoes.enviar_resumo() == "enviado"
    assert enviados[0][0] == "dono@academia.com" and "Inadimplentes" in enviados[0][2]
    assert integracoes.enviar_resumo() == "já enviado hoje"
    ajustes.salvar({"email_provedor": "manual", "smtp_host": "", "resumo_ativo": "0"})
