"""Sistema de cobrança de mensalidades para academia (Flask + SQLite)."""
import os
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

import cobranca
import config
import db
import notificacoes
from notificacoes import data_br, moeda

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.jinja_env.filters["moeda"] = moeda
app.jinja_env.filters["data_br"] = data_br
app.jinja_env.filters["moeda_inteira"] = lambda v: moeda(round(v or 0))[:-3]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
app.jinja_env.filters["mes_curto"] = lambda ym: f"{MESES[int(ym[5:7]) - 1]}/{ym[2:4]}"

STATUS_ROTULO = {
    "em_dia": "Em dia",
    "a_vencer": "Vence em breve",
    "vencido": "Vencido",
    "inadimplente": "Inadimplente",
    "inativo": "Inativo",
}
FORMAS_PAGAMENTO = ["PIX", "Dinheiro", "Cartão de débito", "Cartão de crédito", "Boleto", "Transferência"]


@app.context_processor
def contexto_global():
    return {
        "academia": config.ACADEMIA_NOME,
        "STATUS_ROTULO": STATUS_ROTULO,
        "DIAS_INADIMPLENCIA": config.DIAS_INADIMPLENCIA,
        "csrf_token": session.get("csrf"),
        "hoje": db.hoje(),
    }


# ---------------------------------------------------------------- segurança

def login_obrigatorio(view):
    @wraps(view)
    def interno(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login", proximo=request.path))
        return view(*args, **kwargs)
    return interno


@app.before_request
def proteger_csrf():
    session.setdefault("csrf", secrets.token_hex(16))
    if request.method == "POST" and request.form.get("csrf") != session["csrf"]:
        abort(400, "Token de segurança inválido. Recarregue a página.")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario_ok = secrets.compare_digest(request.form.get("usuario", ""), config.ADMIN_USUARIO)
        senha_ok = secrets.compare_digest(request.form.get("senha", ""), config.ADMIN_SENHA)
        if usuario_ok and senha_ok:
            session["logado"] = True
            proximo = request.args.get("proximo", "")
            return redirect(proximo if proximo.startswith("/") and not proximo.startswith("//") else url_for("dashboard"))
        flash("Usuário ou senha inválidos.", "erro")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- dashboard

@app.route("/")
@login_obrigatorio
def dashboard():
    resumo = db.resumo_dashboard()
    maior = max([m["total"] for m in resumo["historico"]] + [1])
    return render_template(
        "dashboard.html",
        r=resumo,
        maior=maior,
        proximos=db.proximos_vencimentos(7),
        proxima_cobranca=cobranca.proxima_execucao(),
    )


# ---------------------------------------------------------------- alunos

@app.route("/alunos")
@login_obrigatorio
def alunos():
    termo = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    lista = db.buscar_alunos(termo, status)
    return render_template("alunos.html", alunos=lista, termo=termo, status=status)


def _form_aluno() -> dict:
    f = request.form
    return {
        "nome": f.get("nome", "").strip(),
        "cpf": f.get("cpf", "").strip() or None,
        "email": f.get("email", "").strip() or None,
        "telefone": f.get("telefone", "").strip() or None,
        "data_nascimento": f.get("data_nascimento") or None,
        "plano_id": int(f["plano_id"]) if f.get("plano_id") else None,
        "data_inscricao": f.get("data_inscricao") or db.hoje().isoformat(),
        "data_vencimento": f.get("data_vencimento") or db.hoje().isoformat(),
        "observacoes": f.get("observacoes", "").strip() or None,
    }


@app.route("/alunos/novo", methods=["GET", "POST"])
@login_obrigatorio
def aluno_novo():
    planos = db.listar_planos(somente_ativos=True)
    if request.method == "POST":
        dados = _form_aluno()
        if not dados["nome"]:
            flash("Informe o nome do aluno.", "erro")
            return render_template("aluno_form.html", aluno=dados, planos=planos, novo=True, formas=FORMAS_PAGAMENTO)
        try:
            with db.conectar() as con:
                cur = con.execute(
                    "INSERT INTO alunos (nome, cpf, email, telefone, data_nascimento, plano_id, "
                    "data_inscricao, data_vencimento, observacoes) VALUES "
                    "(:nome,:cpf,:email,:telefone,:data_nascimento,:plano_id,:data_inscricao,:data_vencimento,:observacoes)",
                    dados,
                )
                aluno_id = cur.lastrowid
                if request.form.get("pago_agora") and dados["plano_id"]:
                    valor = con.execute("SELECT valor FROM planos WHERE id = ?", (dados["plano_id"],)).fetchone()[0]
                    con.execute(
                        "INSERT INTO pagamentos (aluno_id, valor, data_pagamento, validade_anterior, nova_validade, forma) "
                        "VALUES (?,?,?,?,?,?)",
                        (aluno_id, valor, db.hoje().isoformat(), None, dados["data_vencimento"],
                         request.form.get("forma") or "PIX"),
                    )
        except sqlite3.IntegrityError:
            flash("Já existe um aluno com este CPF.", "erro")
            return render_template("aluno_form.html", aluno=dados, planos=planos, novo=True, formas=FORMAS_PAGAMENTO)
        flash(f"Aluno {dados['nome']} cadastrado!", "ok")
        return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))

    padrao = {"data_inscricao": db.hoje().isoformat(),
              "data_vencimento": (db.hoje() + timedelta(days=30)).isoformat(),
              "plano_id": planos[0]["id"] if planos else None}
    return render_template("aluno_form.html", aluno=padrao, planos=planos, novo=True, formas=FORMAS_PAGAMENTO)


@app.route("/alunos/<int:aluno_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def aluno_editar(aluno_id):
    aluno = db.obter_aluno(aluno_id) or abort(404)
    planos = db.listar_planos()
    if request.method == "POST":
        dados = _form_aluno()
        dados["id"] = aluno_id
        if not dados["nome"]:
            flash("Informe o nome do aluno.", "erro")
            return render_template("aluno_form.html", aluno=dados, planos=planos, novo=False)
        try:
            with db.conectar() as con:
                con.execute(
                    "UPDATE alunos SET nome=:nome, cpf=:cpf, email=:email, telefone=:telefone, "
                    "data_nascimento=:data_nascimento, plano_id=:plano_id, data_inscricao=:data_inscricao, "
                    "data_vencimento=:data_vencimento, observacoes=:observacoes WHERE id=:id",
                    dados,
                )
        except sqlite3.IntegrityError:
            flash("Já existe um aluno com este CPF.", "erro")
            return render_template("aluno_form.html", aluno=dados, planos=planos, novo=False)
        flash("Cadastro atualizado.", "ok")
        return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))
    return render_template("aluno_form.html", aluno=aluno, planos=planos, novo=False)


def _valor(texto: str) -> float:
    """Aceita '120', '120.50', '120,50' e '1.200,50'."""
    texto = texto.strip().replace("R$", "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


def _validade_sugerida(aluno: dict) -> str:
    """Renova a partir do vencimento atual (mantém o dia fixo). Se ficar no
    passado (aluno sumiu por muito tempo), renova a partir de hoje."""
    duracao = aluno.get("plano_duracao") or 30
    nova = date.fromisoformat(aluno["data_vencimento"]) + timedelta(days=duracao)
    if nova < db.hoje():
        nova = db.hoje() + timedelta(days=duracao)
    return nova.isoformat()


@app.route("/alunos/<int:aluno_id>")
@login_obrigatorio
def aluno_detalhe(aluno_id):
    aluno = db.obter_aluno(aluno_id) or abort(404)
    return render_template(
        "aluno_detalhe.html",
        aluno=aluno,
        pagamentos=db.pagamentos_aluno(aluno_id),
        avisos=db.notificacoes_recentes(20, aluno_id),
        validade_sugerida=_validade_sugerida(aluno),
        link_wa=notificacoes.link_whatsapp(aluno),
        preview=notificacoes.montar_mensagem(aluno)[1],
        formas=FORMAS_PAGAMENTO,
    )


@app.post("/alunos/<int:aluno_id>/pagamento")
@login_obrigatorio
def registrar_pagamento(aluno_id):
    aluno = db.obter_aluno(aluno_id) or abort(404)
    try:
        valor = _valor(request.form.get("valor", ""))
        data_pag = date.fromisoformat(request.form["data_pagamento"]).isoformat()
        nova_validade = date.fromisoformat(request.form["nova_validade"]).isoformat()
    except (ValueError, KeyError):
        flash("Dados de pagamento inválidos.", "erro")
        return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))
    if valor <= 0:
        flash("Informe um valor maior que zero.", "erro")
        return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))

    with db.conectar() as con:
        con.execute(
            "INSERT INTO pagamentos (aluno_id, valor, data_pagamento, validade_anterior, nova_validade, forma) "
            "VALUES (?,?,?,?,?,?)",
            (aluno_id, valor, data_pag, aluno["data_vencimento"], nova_validade, request.form.get("forma")),
        )
        con.execute("UPDATE alunos SET data_vencimento = ?, ativo = 1 WHERE id = ?", (nova_validade, aluno_id))
    flash(f"Pagamento de {moeda(valor)} registrado. Nova validade: {data_br(nova_validade)}.", "ok")
    return redirect(request.form.get("voltar") or url_for("aluno_detalhe", aluno_id=aluno_id))


@app.post("/pagamentos/<int:pagamento_id>/estornar")
@login_obrigatorio
def estornar_pagamento(pagamento_id):
    with db.conectar() as con:
        pg = con.execute("SELECT * FROM pagamentos WHERE id = ?", (pagamento_id,)).fetchone() or abort(404)
        con.execute("DELETE FROM pagamentos WHERE id = ?", (pagamento_id,))
        # Se era o último pagamento, devolve a validade anterior
        atual = con.execute("SELECT data_vencimento FROM alunos WHERE id = ?", (pg["aluno_id"],)).fetchone()[0]
        if pg["validade_anterior"] and atual == pg["nova_validade"]:
            con.execute("UPDATE alunos SET data_vencimento = ? WHERE id = ?", (pg["validade_anterior"], pg["aluno_id"]))
    flash("Pagamento estornado.", "ok")
    return redirect(url_for("aluno_detalhe", aluno_id=pg["aluno_id"]))


@app.post("/alunos/<int:aluno_id>/ativo")
@login_obrigatorio
def alternar_ativo(aluno_id):
    aluno = db.obter_aluno(aluno_id) or abort(404)
    with db.conectar() as con:
        con.execute("UPDATE alunos SET ativo = ? WHERE id = ?", (0 if aluno["ativo"] else 1, aluno_id))
    flash("Matrícula cancelada." if aluno["ativo"] else "Matrícula reativada.", "ok")
    return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))


@app.post("/alunos/<int:aluno_id>/excluir")
@login_obrigatorio
def aluno_excluir(aluno_id):
    with db.conectar() as con:
        con.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    flash("Aluno excluído.", "ok")
    return redirect(url_for("alunos"))


# ---------------------------------------------------------------- avisos

ROTULO_RESULTADO = {"enviado": "enviado", "simulado": "registrado (modo simulado)",
                    "erro": "ERRO", "sem contato": "sem contato cadastrado", "já enviado": "já enviado"}


def _resumo_envio(nome: str, res: dict) -> str:
    partes = [f"{'E-mail' if c == 'email' else 'WhatsApp'}: {ROTULO_RESULTADO.get(s, s)}" for c, s in res.items()]
    return f"{nome} – " + " · ".join(partes)


@app.post("/alunos/<int:aluno_id>/avisar")
@login_obrigatorio
def avisar_aluno(aluno_id):
    aluno = db.obter_aluno(aluno_id) or abort(404)
    canal = request.form.get("canal", "ambos")
    canais = ("email", "whatsapp") if canal == "ambos" else (canal,)
    res = notificacoes.notificar(aluno, canais=canais, tipo="manual")
    flash(_resumo_envio(aluno["nome"], res), "erro" if "erro" in res.values() else "ok")
    return redirect(request.form.get("voltar") or url_for("aluno_detalhe", aluno_id=aluno_id))


@app.post("/inadimplentes/avisar-todos")
@login_obrigatorio
def avisar_inadimplentes():
    enviados = erros = 0
    for aluno in db.inadimplentes():
        res = notificacoes.notificar(aluno, tipo="manual")
        enviados += any(s in ("enviado", "simulado") for s in res.values())
        erros += "erro" in res.values()
    flash(f"Avisos disparados para {enviados} inadimplente(s)" + (f" · {erros} com erro" if erros else "") + ".",
          "erro" if erros else "ok")
    return redirect(url_for("dashboard"))


@app.route("/avisos")
@login_obrigatorio
def avisos():
    return render_template(
        "avisos.html",
        avisos=db.notificacoes_recentes(200),
        cfg={
            "email": f"SMTP {config.SMTP_HOST}:{config.SMTP_PORTA}" if config.SMTP_HOST else None,
            "whatsapp": config.WHATSAPP_PROVEDOR if config.WHATSAPP_PROVEDOR != "simulado" else None,
            "dias": config.DIAS_AVISO,
            "hora": config.HORA_COBRANCA,
        },
        ultima=db.get_sistema("ultima_cobranca"),
        proxima=cobranca.proxima_execucao(),
    )


@app.post("/cobranca/executar")
@login_obrigatorio
def executar_cobranca():
    r = cobranca.executar_cobranca()
    flash(f"Cobrança executada: {r['avaliados']} aluno(s) avaliados, {r['avisados']} avisado(s), "
          f"{r['erros']} erro(s).", "erro" if r["erros"] else "ok")
    return redirect(url_for("avisos"))


# ---------------------------------------------------------------- validade

@app.route("/validade")
@login_obrigatorio
def validade():
    termo = request.args.get("q", "").strip()
    resultados = db.buscar_alunos(termo) if termo else []
    return render_template("validade.html", termo=termo, resultados=resultados,
                           proximos=db.proximos_vencimentos(15))


# ---------------------------------------------------------------- financeiro

@app.route("/financeiro")
@login_obrigatorio
def financeiro():
    mes = request.args.get("mes") or db.hoje().strftime("%Y-%m")
    try:
        inicio = date.fromisoformat(mes + "-01")
    except ValueError:
        inicio = db.hoje().replace(day=1)
    fim = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    pagamentos = db.pagamentos_periodo(inicio.isoformat(), fim.isoformat())
    por_forma: dict[str, float] = {}
    for p in pagamentos:
        por_forma[p["forma"] or "Não informado"] = por_forma.get(p["forma"] or "Não informado", 0) + p["valor"]
    return render_template(
        "financeiro.html",
        mes=inicio.strftime("%Y-%m"),
        pagamentos=pagamentos,
        total=sum(p["valor"] for p in pagamentos),
        por_forma=sorted(por_forma.items(), key=lambda x: -x[1]),
    )


# ---------------------------------------------------------------- planos

@app.route("/planos", methods=["GET", "POST"])
@login_obrigatorio
def planos():
    if request.method == "POST":
        try:
            nome = request.form["nome"].strip()
            valor = _valor(request.form["valor"])
            duracao = int(request.form["duracao_dias"])
            assert nome and valor > 0 and duracao > 0
        except (KeyError, ValueError, AssertionError):
            flash("Preencha nome, valor e duração corretamente.", "erro")
            return redirect(url_for("planos"))
        with db.conectar() as con:
            if request.form.get("id"):
                con.execute("UPDATE planos SET nome=?, valor=?, duracao_dias=?, ativo=? WHERE id=?",
                            (nome, valor, duracao, 1 if request.form.get("ativo") else 0, int(request.form["id"])))
            else:
                con.execute("INSERT INTO planos (nome, valor, duracao_dias) VALUES (?,?,?)", (nome, valor, duracao))
        flash("Plano salvo.", "ok")
        return redirect(url_for("planos"))
    with db.conectar() as con:
        contagem = dict(con.execute(
            "SELECT plano_id, COUNT(*) FROM alunos WHERE ativo = 1 GROUP BY plano_id").fetchall())
    return render_template("planos.html", planos=db.listar_planos(), contagem=contagem)


# ---------------------------------------------------------------- inicialização

db.iniciar_banco()

# Evita dois agendadores quando o modo debug recarrega o processo
if os.environ.get("DEBUG") != "1" or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    cobranca.iniciar_agendador()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORTA", 5000)), debug=os.environ.get("DEBUG") == "1")
