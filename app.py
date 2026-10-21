"""Sistema de cobrança de mensalidades para academia (Flask + SQLite)."""
import json
import os
import secrets
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

import ajustes
import cobranca
import config
import db
import notificacoes
from icones import icone
from notificacoes import data_br, moeda

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
if config.NA_VERCEL:
    # A Vercel fica na frente do app: usa o IP real do visitante e o https original
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=config.COOKIE_SEGURO,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
app.jinja_env.filters["moeda"] = moeda
app.jinja_env.filters["data_br"] = data_br
app.jinja_env.filters["moeda_inteira"] = lambda v: moeda(round(v or 0))[:-3]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
app.jinja_env.globals["icone"] = icone
app.jinja_env.filters["mes_curto"] = lambda ym: f"{MESES[int(ym[5:7]) - 1]}/{ym[2:4]}"

STATUS_ROTULO = {
    "em_dia": "Em dia",
    "a_vencer": "Vence em breve",
    "vencido": "Vencido",
    "inadimplente": "Inadimplente",
    "inativo": "Inativo",
}
# status -> (tom de cor do card, ícone)
TONS = {
    "em_dia": ("verde", "check"),
    "a_vencer": ("azul", "clock"),
    "vencido": ("laranja", "alert"),
    "inadimplente": ("vermelho", "alert"),
    "inativo": ("cinza", "ban"),
}
FORMAS_PAGAMENTO = ["PIX", "Dinheiro", "Cartão de débito", "Cartão de crédito", "Boleto", "Transferência"]


@app.context_processor
def contexto_global():
    return {
        "academia": ajustes.obter("academia_nome"),
        "academia_curto": ajustes.obter("academia_nome").split()[0],
        "empresa": ajustes.empresa(),
        "SENHA_PADRAO": config.SENHA_PADRAO,
        "BANCO_TEMPORARIO": config.BANCO_TEMPORARIO,
        "usuario": config.ADMIN_USUARIO.capitalize(),
        "STATUS_ROTULO": STATUS_ROTULO,
        "TONS": TONS,
        "DIAS_INADIMPLENCIA": config.DIAS_INADIMPLENCIA,
        "DIAS_AVISO": config.DIAS_AVISO,
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
    if request.endpoint in PUBLICAS - {"login"}:
        return  # páginas públicas não criam cookie
    session.setdefault("csrf", secrets.token_hex(16))
    if request.method == "POST" and request.form.get("csrf") != session["csrf"]:
        abort(400, "Token de segurança inválido. Recarregue a página.")


# Páginas abertas ao público (sem login): documentos legais
PUBLICAS = {"login", "static", "privacidade", "termos", "reembolso", "cron_cobranca"}

CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; "
       "form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")


@app.after_request
def cabecalhos_seguranca(resp):
    resp.headers.setdefault("Content-Security-Policy", CSP)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if config.COOKIE_SEGURO:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    if request.endpoint not in PUBLICAS:
        resp.headers["Cache-Control"] = "no-store"  # páginas com dados pessoais não ficam no cache
    return resp


# Bloqueio após tentativas erradas de login (por IP, guardado no banco para valer
# entre processos e instâncias na nuvem)
TENTATIVAS_MAX, JANELA_SEG = 5, 15 * 60


def _bloqueado(ip: str) -> bool:
    return db.falhas_recentes(ip, JANELA_SEG) >= TENTATIVAS_MAX


@app.route("/login", methods=["GET", "POST"])
def login():
    ip = request.remote_addr or "?"
    if request.method == "POST" and _bloqueado(ip):
        flash("Muitas tentativas erradas. Aguarde 15 minutos e tente novamente.", "erro")
        return render_template("login.html"), 429
    if request.method == "POST":
        usuario_ok = secrets.compare_digest(request.form.get("usuario", ""), config.ADMIN_USUARIO)
        senha_ok = secrets.compare_digest(request.form.get("senha", ""), config.ADMIN_SENHA)
        if usuario_ok and senha_ok:
            db.limpar_falhas_login(ip)
            session.clear()
            session.permanent = True
            session["logado"] = True
            proximo = request.args.get("proximo", "")
            return redirect(proximo if proximo.startswith("/") and not proximo.startswith("//") else url_for("dashboard"))
        db.registrar_falha_login(ip)
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
    db.avisos_do_ciclo(resumo["inadimplentes"])
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
    todos = db.buscar_alunos(termo)
    contagem = {k: sum(1 for a in todos if a["status"] == k) for k in STATUS_ROTULO}
    lista = [a for a in todos if a["status"] == status] if status else todos
    return render_template("alunos.html", alunos=lista, termo=termo, status=status,
                           contagem=contagem, total=len(todos))


def _form_aluno() -> dict:
    f = request.form
    return {
        "nome": f.get("nome", "").strip(),
        "cpf": f.get("cpf", "").strip() or None,
        "email": f.get("email", "").strip() or None,
        "telefone": f.get("telefone", "").strip() or None,
        "aceita_email": 1 if f.get("aceita_email") else 0,
        "aceita_whatsapp": 1 if f.get("aceita_whatsapp") else 0,
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
                    "INSERT INTO alunos (nome, cpf, email, telefone, plano_id, data_inscricao, data_vencimento, "
                    "observacoes, aceita_email, aceita_whatsapp, termos_aceitos_em) VALUES "
                    "(:nome,:cpf,:email,:telefone,:plano_id,:data_inscricao,:data_vencimento,:observacoes,"
                    ":aceita_email,:aceita_whatsapp,:termos_aceitos_em) RETURNING id",
                    {**dados, "termos_aceitos_em": datetime.now().isoformat(timespec="seconds")
                     if request.form.get("termos_aceitos") else None},
                )
                aluno_id = cur.fetchone()[0]
                if request.form.get("pago_agora") and dados["plano_id"]:
                    valor = con.execute("SELECT valor FROM planos WHERE id = ?", (dados["plano_id"],)).fetchone()[0]
                    con.execute(
                        "INSERT INTO pagamentos (aluno_id, valor, data_pagamento, validade_anterior, nova_validade, forma) "
                        "VALUES (?,?,?,?,?,?)",
                        (aluno_id, valor, db.hoje().isoformat(), None, dados["data_vencimento"],
                         request.form.get("forma") or "PIX"),
                    )
        except db.ErroIntegridade:
            flash("Já existe um aluno com este CPF.", "erro")
            return render_template("aluno_form.html", aluno=dados, planos=planos, novo=True, formas=FORMAS_PAGAMENTO)
        flash(f"Aluno {dados['nome']} cadastrado!", "ok")
        return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))

    padrao = {"aceita_email": 1, "aceita_whatsapp": 1, "data_inscricao": db.hoje().isoformat(),
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
        dados["termos_aceitos_em"] = (datetime.now().isoformat(timespec="seconds")
                                      if request.form.get("termos_aceitos") else None)
        if not dados["nome"]:
            flash("Informe o nome do aluno.", "erro")
            return render_template("aluno_form.html", aluno=dados, planos=planos, novo=False)
        try:
            with db.conectar() as con:
                con.execute(
                    "UPDATE alunos SET nome=:nome, cpf=:cpf, email=:email, telefone=:telefone, "
                    "plano_id=:plano_id, data_inscricao=:data_inscricao, data_vencimento=:data_vencimento, "
                    "observacoes=:observacoes, aceita_email=:aceita_email, aceita_whatsapp=:aceita_whatsapp, "
                    "termos_aceitos_em=COALESCE(termos_aceitos_em, :termos_aceitos_em) WHERE id=:id",
                    dados,
                )
        except db.ErroIntegridade:
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


@app.route("/alunos/<int:aluno_id>/exportar")
@login_obrigatorio
def aluno_exportar(aluno_id):
    dados = db.exportar_aluno(aluno_id) or abort(404)
    dados["exportado_em"] = datetime.now().isoformat(timespec="seconds")
    dados["controlador"] = {k: v for k, v in ajustes.empresa().items() if k in ("razao_social", "cnpj", "email_contato")}
    return Response(
        json.dumps(dados, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=dados-aluno-{aluno_id}.json"},
    )


@app.post("/alunos/<int:aluno_id>/anonimizar")
@login_obrigatorio
def aluno_anonimizar(aluno_id):
    db.obter_aluno(aluno_id) or abort(404)
    db.anonimizar_aluno(aluno_id)
    flash("Dados pessoais apagados. Ficaram só os valores pagos, exigidos pela legislação fiscal.", "ok")
    return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))


# ---------------------------------------------------------------- documentos públicos

def _documento(nome: str):
    return render_template(f"legal/{nome}.html", e=ajustes.empresa(), DIAS_AVISO=config.DIAS_AVISO,
                           retencao_avisos=config.RETENCAO_AVISOS_DIAS,
                           atualizado=db.get_sistema("documentos_atualizados_em"))


@app.route("/privacidade")
def privacidade():
    return _documento("privacidade")


@app.route("/termos")
def termos():
    return _documento("termos")


@app.route("/reembolso")
def reembolso():
    return _documento("reembolso")


# ---------------------------------------------------------------- avisos

ROTULO_RESULTADO = {"enviado": "enviado", "simulado": "registrado (modo simulado)",
                    "não autorizado": "aluno pediu para não receber",
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
            "email": "{host}:{porta}".format(**ajustes.smtp()) if ajustes.smtp()["host"] else None,
            "whatsapp": NOMES_WHATSAPP[ajustes.whatsapp()["provedor"]] if ajustes.whatsapp()["provedor"] != "simulado" else None,
            "dias": config.DIAS_AVISO,
            "hora": config.HORA_COBRANCA,
        },
        ultima=db.get_sistema("ultima_cobranca"),
        proxima=cobranca.proxima_execucao(),
    )


@app.route("/api/cron/cobranca")
def cron_cobranca():
    """Chamado uma vez por dia pelo Cron da Vercel (ver vercel.json)."""
    esperado = f"Bearer {config.CRON_SECRET}"
    if not config.CRON_SECRET or not secrets.compare_digest(request.headers.get("Authorization", ""), esperado):
        abort(401)
    r = cobranca.executar_cobranca()
    return jsonify({k: r[k] for k in ("avaliados", "avisados", "erros", "avisos_apagados")})


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


# ---------------------------------------------------------------- configurações

PRESETS_SMTP = {
    "Gmail": ("smtp.gmail.com", 587, "tls"),
    "Outlook / Hotmail": ("smtp-mail.outlook.com", 587, "tls"),
    "Microsoft 365": ("smtp.office365.com", 587, "tls"),
    "Hostinger": ("smtp.hostinger.com", 465, "ssl"),
    "Locaweb": ("email-ssl.com.br", 465, "ssl"),
    "Zoho": ("smtp.zoho.com", 465, "ssl"),
}


NOMES_WHATSAPP = {"simulado": "Simulado", "zapi": "Z-API", "evolution": "Evolution API",
                  "meta": "Meta Cloud API", "twilio": "Twilio"}
# (chave, descrição, ícone, gradiente)
PROVEDORES_WHATSAPP_TELA = [
    ("simulado", "Só registra, não envia", "lock", "g-cinza"),
    ("zapi", "Seu número via QR Code", "whatsapp", "g-verde"),
    ("evolution", "Software livre, servidor próprio", "settings", "g-teal"),
    ("meta", "API oficial do WhatsApp", "building", "g-azul"),
    ("twilio", "API oficial via Twilio", "send", "g-vermelho"),
]


def _aluno_exemplo() -> dict:
    return {"id": 0, "nome": "Aluno Exemplo", "plano_nome": "Mensal", "plano_valor": 120.0,
            "data_vencimento": (db.hoje() + timedelta(days=3)).isoformat()}


@app.route("/configuracoes", methods=["GET", "POST"])
@login_obrigatorio
def configuracoes():
    if request.method == "POST":
        valores = {k: request.form.get(k, "") for k in ajustes.CAMPOS if k not in ajustes.SECRETOS}
        # senhas e tokens em branco = manter os atuais
        valores.update({k: request.form[k] for k in ajustes.SECRETOS if request.form.get(k)})
        if valores.get("wa_provedor") not in ajustes.PROVEDORES_WHATSAPP:
            valores["wa_provedor"] = "simulado"
        if valores.get("smtp_porta") and not valores["smtp_porta"].isdigit():
            flash("A porta SMTP deve ser um número.", "erro")
            return redirect(url_for("configuracoes"))
        try:
            assert 0 <= float((valores.get("retencao_cancelamento_pct") or "0").replace(",", ".")) <= 100
            assert (valores.get("prazo_reembolso_dias") or "30").isdigit()
        except (ValueError, AssertionError):
            flash("Multa deve ser um percentual de 0 a 100 e o prazo de reembolso um número de dias.", "erro")
            return redirect(url_for("configuracoes") + "#empresa")
        valores["retencao_cancelamento_pct"] = (valores.get("retencao_cancelamento_pct") or "0").replace(",", ".")
        ajustes.salvar(valores)
        db.set_sistema("documentos_atualizados_em", db.hoje().isoformat())
        flash("Configurações salvas.", "ok")
        return redirect(url_for("configuracoes"))
    valores = {k: ajustes.obter(k) for k in ajustes.CAMPOS}
    salvos = {k for k in ajustes.SECRETOS if valores.pop(k)}
    valores["wa_provedor"] = ajustes.whatsapp()["provedor"]
    return render_template("configuracoes.html", v=valores, salvos=salvos, presets=PRESETS_SMTP,
                           provedores=PROVEDORES_WHATSAPP_TELA)


@app.post("/configuracoes/teste-email")
@login_obrigatorio
def teste_email():
    destino = request.form.get("destino", "").strip()
    if "@" not in destino:
        flash("Informe um e-mail válido para o teste.", "erro")
        return redirect(url_for("configuracoes"))
    exemplo = _aluno_exemplo()
    assunto, texto = notificacoes.montar_mensagem(exemplo)
    try:
        status = notificacoes.enviar_email(destino, "[TESTE] " + assunto, texto, notificacoes.montar_email_html(exemplo))
    except Exception as e:  # noqa: BLE001 - mostra o erro do servidor de e-mail
        flash(f"Falha ao enviar: {e}", "erro")
        return redirect(url_for("configuracoes"))
    if status == "simulado":
        flash("Servidor SMTP não configurado: preencha os dados acima e salve antes de testar.", "erro")
    else:
        flash(f"E-mail de teste enviado para {destino}. Confira a caixa de entrada (e o spam).", "ok")
    return redirect(url_for("configuracoes"))


@app.post("/configuracoes/teste-whatsapp")
@login_obrigatorio
def teste_whatsapp():
    numero = notificacoes.normalizar_telefone(request.form.get("numero"))
    if len(numero) < 12:
        flash("Informe um número de WhatsApp com DDD, ex.: (11) 99999-0000.", "erro")
        return redirect(url_for("configuracoes") + "#whatsapp")
    exemplo = _aluno_exemplo()
    _, texto = notificacoes.montar_mensagem(exemplo)
    try:
        status = notificacoes.enviar_whatsapp(numero, "[TESTE]\n" + texto, exemplo)
    except Exception as e:  # noqa: BLE001 - mostra o erro do provedor
        flash(f"Falha ao enviar WhatsApp: {e}", "erro")
        return redirect(url_for("configuracoes") + "#whatsapp")
    if status == "simulado":
        flash("WhatsApp em modo simulado: escolha um provedor, preencha os dados e salve antes de testar.", "erro")
    else:
        flash(f"Mensagem de teste enviada para +{numero}. Confira o WhatsApp.", "ok")
    return redirect(url_for("configuracoes") + "#whatsapp")


@app.route("/configuracoes/email-preview")
@login_obrigatorio
def email_preview():
    aluno = db.obter_aluno(int(request.args["aluno"])) if request.args.get("aluno") else _aluno_exemplo()
    return notificacoes.montar_email_html(aluno or abort(404))


# ---------------------------------------------------------------- inicialização

db.iniciar_banco()

if not app.secret_key:
    # Disco somente leitura (Vercel) e sem SECRET_KEY: gera uma vez e guarda no banco
    app.secret_key = db.get_sistema("secret_key") or secrets.token_hex(32)
    db.set_sistema("secret_key", app.secret_key)

# Na Vercel não há processo contínuo: a cobrança diária roda pelo Cron (/api/cron/cobranca).
# Fora dela, um agendador interno roda a cobrança (evita dois quando o debug recarrega o processo).
if not config.NA_VERCEL and (os.environ.get("DEBUG") != "1" or os.environ.get("WERKZEUG_RUN_MAIN") == "true"):
    cobranca.iniciar_agendador()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORTA", 5000)), debug=os.environ.get("DEBUG") == "1")
