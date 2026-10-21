"""Sistema de cobrança de mensalidades para academia (Flask + SQLite)."""
import csv
import io
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
import importacao
import notificacoes
from icones import icone
from notificacoes import data_br, moeda

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
if config.NA_VERCEL:
    # A Vercel fica na frente do app: usa o IP real do visitante e o https original
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    MAX_CONTENT_LENGTH=4 * 1024 * 1024,  # planilhas do cadastro rápido
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
app.jinja_env.globals["link_envio"] = notificacoes.link_envio
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
        # contadores da sidebar e do menu (só no painel)
        "fila_total": db.contar_fila() if session.get("logado") else 0,
        "envio_modos": _modos_envio() if session.get("logado") else {},
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
            session["csrf"] = secrets.token_hex(16)  # token novo a cada login
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
        reajustes=db.reajustes_agendados(),
    )


# ---------------------------------------------------------------- alunos

ORDENS_ROTULO = {"nome": "Nome (A–Z)", "vencimento": "Vencimento mais próximo", "vencimento_desc": "Vencimento mais distante",
                 "recentes": "Inscritos mais recentes"}
CONTATOS_ROTULO = {"whatsapp": "Recebe por WhatsApp", "email": "Recebe por e-mail", "sem_contato": "Sem telefone e e-mail",
                   "sem_autorizacao": "Não autorizou avisos"}


def _filtros_alunos() -> dict:
    a = request.args
    plano = a.get("plano", "")
    return {
        "termo": a.get("q", "").strip(),
        "plano_id": int(plano) if plano.isdigit() else None,
        "contato": a.get("contato", "") if a.get("contato") in CONTATOS_ROTULO else "",
        "venc_de": importacao.ler_data(a.get("de", "")),
        "venc_ate": importacao.ler_data(a.get("ate", "")),
        "ordem": a.get("ordem", "nome") if a.get("ordem") in ORDENS_ROTULO else "nome",
    }


@app.route("/alunos")
@login_obrigatorio
def alunos():
    f = _filtros_alunos()
    status = request.args.get("status", "") if request.args.get("status") in STATUS_ROTULO else ""
    todos = db.buscar_alunos(f["termo"], plano_id=f["plano_id"], contato=f["contato"], venc_de=f["venc_de"],
                             venc_ate=f["venc_ate"], ordem=f["ordem"])
    contagem = {k: sum(1 for a in todos if a["status"] == k) for k in STATUS_ROTULO}
    lista = [a for a in todos if a["status"] == status] if status else todos
    planos = db.listar_planos()
    # filtros ativos viram "chips" removíveis (link sem aquele filtro)
    args = {k: v for k, v in request.args.items() if v}
    nomes_plano = {p["id"]: p["nome"] for p in planos}
    chips = []
    for chave, rotulo in (("plano", nomes_plano.get(f["plano_id"])), ("contato", CONTATOS_ROTULO.get(f["contato"])),
                          ("de", f["venc_de"] and "Vence a partir de " + data_br(f["venc_de"])),
                          ("ate", f["venc_ate"] and "Vence até " + data_br(f["venc_ate"])),
                          ("ordem", f["ordem"] != "nome" and ORDENS_ROTULO[f["ordem"]])):
        if rotulo:
            chips.append((rotulo, url_for("alunos", **{k: v for k, v in args.items() if k != chave})))
    return render_template("alunos.html", alunos=lista, termo=f["termo"], status=status, f=f, chips=chips,
                           contagem=contagem, total=len(todos), planos=planos, ordens=ORDENS_ROTULO,
                           contatos=CONTATOS_ROTULO, args=args,
                           total_geral=len(db.buscar_alunos()) if (chips or f["termo"]) else len(todos))


@app.route("/alunos/exportar.csv")
@login_obrigatorio
def alunos_exportar():
    """A lista filtrada em planilha (abre no Excel). Contém dados pessoais: só para uso interno."""
    f = _filtros_alunos()
    status = request.args.get("status", "")
    lista = db.buscar_alunos(f["termo"], status if status in STATUS_ROTULO else "", plano_id=f["plano_id"],
                             contato=f["contato"], venc_de=f["venc_de"], venc_ate=f["venc_ate"], ordem=f["ordem"])
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(["Nome", "WhatsApp", "E-mail", "CPF", "Plano", "Valor", "Vencimento", "Situação",
                       "Inscrição", "Aceita WhatsApp", "Aceita e-mail"])
    for a in lista:
        escritor.writerow([a["nome"], a["telefone"] or "", a["email"] or "", a["cpf"] or "", a["plano_nome"] or "",
                           moeda(a["plano_valor"]) if a["plano_valor"] else "", data_br(a["data_vencimento"]),
                           STATUS_ROTULO[a["status"]], data_br(a["data_inscricao"]),
                           "sim" if a["aceita_whatsapp"] else "não", "sim" if a["aceita_email"] else "não"])
    nome = f"inscritos-{db.hoje().isoformat()}.csv"
    return Response("\ufeff" + saida.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nome}"})


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
        if request.form.get("proximo"):
            # mantém plano e autorizações para agilizar a próxima ficha
            return redirect(url_for("aluno_novo", plano=dados["plano_id"] or "",
                                    email=dados["aceita_email"], whatsapp=dados["aceita_whatsapp"]))
        return redirect(url_for("aluno_detalhe", aluno_id=aluno_id))

    plano_pedido = request.args.get("plano", "")
    padrao = {"aceita_email": request.args.get("email", "1") == "1", "aceita_whatsapp": request.args.get("whatsapp", "1") == "1",
              "data_inscricao": db.hoje().isoformat(),
              "data_vencimento": (db.hoje() + timedelta(days=30)).isoformat(),
              "plano_id": int(plano_pedido) if plano_pedido.isdigit() else (planos[0]["id"] if planos else None)}
    return render_template("aluno_form.html", aluno=padrao, planos=planos, novo=True, formas=FORMAS_PAGAMENTO)


# ---------------------------------------------------------------- cadastro rápido (fichas em papel)

LINHAS_INICIAIS = 6


def _opcoes_padrao(plano_padrao: str = "") -> dict:
    planos = db.listar_planos(somente_ativos=True)
    return {"aceita_whatsapp": True, "aceita_email": True, "termos": False,
            "plano_padrao": plano_padrao or (str(planos[0]["id"]) if planos else "")}


def _tela_lote(linhas, erros=None, opcoes=None, aba="digitar", lidas=None):
    planos = db.listar_planos(somente_ativos=True)
    linhas = list(linhas) + [{} for _ in range(max(0, LINHAS_INICIAIS - len(linhas)))]
    opcoes = opcoes or _opcoes_padrao()
    return render_template("alunos_lote.html", linhas=linhas, erros=erros or {}, opcoes=opcoes, planos=planos,
                           aba=aba, lidas=lidas, total_erros=sum(len(v) for v in (erros or {}).values()))


def _opcoes_lote() -> dict:
    f = request.form
    return {"aceita_whatsapp": bool(f.get("aceita_whatsapp")), "aceita_email": bool(f.get("aceita_email")),
            "termos": bool(f.get("termos")), "plano_padrao": f.get("plano_padrao", "")}


@app.route("/alunos/cadastro-rapido", methods=["GET", "POST"])
@login_obrigatorio
def alunos_lote():
    if request.method == "GET":
        aba = request.args.get("aba", "digitar")
        return _tela_lote([], aba=aba if aba in ("digitar", "colar", "arquivo") else "digitar")
    acao = request.form.get("acao", "salvar")
    planos = db.listar_planos(somente_ativos=True)

    if acao in ("colar", "arquivo"):
        opcoes = _opcoes_padrao(request.form.get("plano_padrao", ""))
        if acao == "colar":
            linhas = importacao.ler_texto(request.form.get("texto", ""), planos)
        else:
            arquivo = request.files.get("arquivo")
            if not arquivo or not arquivo.filename:
                flash("Escolha um arquivo .csv ou .xlsx.", "erro")
                return _tela_lote([], aba="arquivo", opcoes=opcoes)
            if not arquivo.filename.lower().endswith((".csv", ".xlsx", ".txt")):
                flash("Formato não suportado: use .csv ou .xlsx (no Excel: Arquivo › Salvar como).", "erro")
                return _tela_lote([], aba="arquivo", opcoes=opcoes)
            try:
                linhas = importacao.ler_arquivo(arquivo.filename, arquivo.read(), planos)
            except Exception:  # noqa: BLE001 - planilha corrompida ou protegida
                flash("Não foi possível ler esse arquivo. Salve como .csv ou .xlsx e tente de novo.", "erro")
                return _tela_lote([], aba="arquivo", opcoes=opcoes)
        linhas = [l for l in linhas if importacao.preenchida(l)]
        if not linhas:
            flash("Nenhuma ficha encontrada. Confira se a primeira coluna tem o nome do aluno.", "erro")
            return _tela_lote([], aba=acao, opcoes=opcoes)
        for l in linhas:
            l["plano_id"] = l["plano_id"] or opcoes["plano_padrao"]
        return _tela_lote(linhas, importacao.validar(linhas), opcoes, lidas=len(linhas))

    opcoes = _opcoes_lote()
    linhas = importacao.linhas_do_formulario(request.form)
    if acao == "mais":
        return _tela_lote(linhas + [{} for _ in range(5)], opcoes=opcoes)

    preenchidas = [l for l in linhas if importacao.preenchida(l)]
    if not preenchidas:
        flash("Preencha pelo menos uma ficha.", "erro")
        return _tela_lote(linhas, opcoes=opcoes)
    erros = importacao.validar(preenchidas)
    if erros:
        flash(f"Revise {len(erros)} ficha(s) marcada(s) em vermelho antes de salvar.", "erro")
        return _tela_lote(preenchidas, erros, opcoes)

    agora_iso = datetime.now().isoformat(timespec="seconds")
    nota = f"Cadastro feito a partir da ficha em papel ({db.hoje().strftime('%d/%m/%Y')})."
    with db.conectar() as con:
        for l in preenchidas:
            plano = l["plano_id"] or opcoes["plano_padrao"]
            con.execute(
                "INSERT INTO alunos (nome, cpf, email, telefone, plano_id, data_inscricao, data_vencimento, observacoes, "
                "aceita_email, aceita_whatsapp, termos_aceitos_em) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (l["nome"], l["cpf"] or None, l["email"].lower() or None, l["telefone"] or None,
                 int(plano) if str(plano).isdigit() else None,
                 importacao.ler_data(l["data_inscricao"]) or db.hoje().isoformat(),
                 importacao.ler_data(l["data_vencimento"]), nota,
                 1 if opcoes["aceita_email"] else 0, 1 if opcoes["aceita_whatsapp"] else 0,
                 agora_iso if opcoes["termos"] else None),
            )
    flash(f"{len(preenchidas)} aluno(s) cadastrado(s) a partir das fichas em papel.", "ok")
    return redirect(url_for("alunos", ordem="recentes"))


@app.route("/alunos/cadastro-rapido/modelo.csv")
@login_obrigatorio
def alunos_lote_modelo():
    return Response(importacao.modelo_csv(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=modelo-fichas-alunos.csv"})


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
        valor_sugerido=notificacoes.valor_cobranca(aluno) or 0,
        fila=db.fila_envio(aluno_id),
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
    mensagem = f"Pagamento de {moeda(valor)} registrado. Nova validade: {data_br(nova_validade)}."
    if request.form.get("comprovante"):
        atualizado = db.obter_aluno(aluno_id)
        res = notificacoes.notificar(atualizado, tipo="comprovante", chave=f"comprovante:{data_pag}:{nova_validade}",
                                     mensagem=notificacoes.montar_comprovante(atualizado, valor, data_pag, nova_validade,
                                                                              request.form.get("forma")))
        if "pendente" in res.values():
            mensagem += " O comprovante está pronto para você enviar (veja logo abaixo)."
        elif any(v == "enviado" for v in res.values()):
            mensagem += " Comprovante enviado ao aluno."
    flash(mensagem, "ok")
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
                    "pendente": "pronto na fila para você enviar",
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
        enviados += any(s in notificacoes.ENTREGUES for s in res.values())
        erros += "erro" in res.values()
    flash(f"Avisos disparados para {enviados} inadimplente(s)" + (f" · {erros} com erro" if erros else "") + ".",
          "erro" if erros else "ok")
    return redirect(url_for("dashboard"))


TIPOS_AVISO = {"lembrete": "Lembrete", "vencimento": "Vencimento", "atraso": "Atraso", "manual": "Manual",
               "reajuste": "Reajuste", "comprovante": "Comprovante"}
STATUS_AVISO = {"enviado": "Enviado", "pendente": "Na fila", "erro": "Erro", "simulado": "Simulado",
                "descartado": "Descartado"}


def _modos_envio() -> dict:
    email, wa = ajustes.provedor_email(), ajustes.whatsapp()["provedor"]
    return {
        "email": email, "whatsapp": wa,
        "email_nome": NOMES_EMAIL[email] + (f" · {ajustes.smtp()['host']}" if email == "smtp" else ""),
        "whatsapp_nome": NOMES_WHATSAPP[wa],
        "automatico": email in ("smtp", "resend") and wa not in ("manual", "simulado"),
    }


@app.route("/avisos")
@login_obrigatorio
def avisos():
    a = request.args
    filtros = {"canal": a.get("canal", "") if a.get("canal") in ("email", "whatsapp") else "",
               "status": a.get("status", "") if a.get("status") in STATUS_AVISO else "",
               "tipo": a.get("tipo", "") if a.get("tipo") in TIPOS_AVISO else "",
               "q": a.get("q", "").strip()}
    return render_template(
        "avisos.html",
        avisos=db.notificacoes_recentes(200, canal=filtros["canal"], status=filtros["status"], tipo=filtros["tipo"],
                                        termo=filtros["q"]),
        filtros=filtros, tipos=TIPOS_AVISO, status_aviso=STATUS_AVISO, modos=_modos_envio(),
        cfg={"dias": config.DIAS_AVISO, "hora": config.HORA_COBRANCA},
        ultima=db.get_sistema("ultima_cobranca"),
        proxima=cobranca.proxima_execucao(),
    )


@app.route("/avisos/fila")
@login_obrigatorio
def fila():
    itens = db.fila_envio()
    return render_template("fila.html", itens=itens, tipos=TIPOS_AVISO, modos=_modos_envio())


@app.post("/avisos/<int:notificacao_id>/marcar")
@login_obrigatorio
def fila_marcar(notificacao_id):
    status = "descartado" if request.form.get("descartar") else "enviado"
    db.marcar_notificacao(notificacao_id, status) or abort(404)
    if request.headers.get("X-Requested-With") == "fetch":  # toque em "Abrir WhatsApp" na fila
        return jsonify({"ok": True, "restantes": db.contar_fila()})
    flash("Aviso descartado." if status == "descartado" else "Aviso marcado como enviado.", "ok")
    return redirect(request.form.get("voltar") or url_for("fila"))


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


# ---------------------------------------------------------------- reajuste da mensalidade

ANTECEDENCIA_RECOMENDADA = 30  # dias de aviso antes do novo valor valer


def _alunos_do_plano(plano_id: int) -> list[dict]:
    return [a for a in db.buscar_alunos(plano_id=plano_id) if a["ativo"]]


@app.route("/reajustes", methods=["GET", "POST"])
@login_obrigatorio
def reajustes():
    planos = db.listar_planos(somente_ativos=True)
    if request.method == "POST":
        f = request.form
        vigencia = importacao.ler_data(f.get("vigencia", ""))
        canais = tuple(c for c in ("email", "whatsapp") if f.get("canal_" + c))
        if not vigencia or vigencia <= db.hoje().isoformat():
            flash("Escolha uma data de vigência a partir de amanhã.", "erro")
            return redirect(url_for("reajustes"))
        if not canais:
            flash("Escolha pelo menos um canal (e-mail ou WhatsApp) para avisar.", "erro")
            return redirect(url_for("reajustes"))
        agendados = {r["plano_id"] for r in db.reajustes_agendados()}
        escolhidos = []
        for p in planos:
            if not f.get(f"plano_{p['id']}"):
                continue
            try:
                novo = _valor(f.get(f"valor_{p['id']}", ""))
            except ValueError:
                novo = 0
            if novo <= 0:
                flash(f"Informe o novo valor do plano {p['nome']}.", "erro")
                return redirect(url_for("reajustes"))
            if p["id"] in agendados:
                flash(f"O plano {p['nome']} já tem um reajuste agendado. Cancele o anterior antes de criar outro.", "erro")
                return redirect(url_for("reajustes"))
            escolhidos.append((p, round(novo, 2)))
        if not escolhidos:
            flash("Marque pelo menos um plano e informe o novo valor.", "erro")
            return redirect(url_for("reajustes"))

        observacao = f.get("observacao", "").strip()[:500] or None
        total = na_fila = sem_contato = 0
        for p, novo in escolhidos:
            with db.conectar() as con:
                reajuste_id = con.execute(
                    "INSERT INTO reajustes (plano_id, valor_anterior, valor_novo, vigencia, observacao) "
                    "VALUES (?,?,?,?,?) RETURNING id", (p["id"], p["valor"], novo, vigencia, observacao),
                ).fetchone()[0]
            reajuste = {"id": reajuste_id, "plano_nome": p["nome"], "valor_anterior": p["valor"],
                        "valor_novo": novo, "vigencia": vigencia, "observacao": observacao}
            avisados = 0
            for aluno in _alunos_do_plano(p["id"]):
                res = notificacoes.notificar(aluno, canais=canais, chave=f"reajuste:{reajuste_id}", tipo="reajuste",
                                             mensagem=notificacoes.montar_reajuste(aluno, reajuste))
                if any(v in notificacoes.ENTREGUES for v in res.values()):
                    avisados += 1
                    na_fila += "pendente" in res.values()
                else:
                    sem_contato += 1
            with db.conectar() as con:
                con.execute("UPDATE reajustes SET avisados = ? WHERE id = ?", (avisados, reajuste_id))
            total += avisados
        texto = f"Reajuste agendado para {data_br(vigencia)}. {total} aluno(s) avisado(s)"
        if na_fila:
            texto += f", {na_fila} com a mensagem pronta na fila de envio"
        if sem_contato:
            texto += f". {sem_contato} sem contato ou sem autorização para avisos"
        flash(texto + ".", "ok")
        return redirect(url_for("fila") if na_fila else url_for("reajustes"))

    with db.conectar() as con:
        contagem = dict(con.execute(
            "SELECT plano_id, COUNT(*) FROM alunos WHERE ativo = 1 GROUP BY plano_id").fetchall())
    sugestao = (db.hoje() + timedelta(days=ANTECEDENCIA_RECOMENDADA + 1)).replace(day=1)
    if (sugestao - db.hoje()).days < ANTECEDENCIA_RECOMENDADA:
        sugestao = (sugestao + timedelta(days=32)).replace(day=1)
    exemplo = {**_aluno_exemplo(), "plano_nome": planos[0]["nome"] if planos else "Mensal"}
    previa = notificacoes.montar_reajuste(exemplo, {
        "plano_nome": exemplo["plano_nome"], "valor_anterior": planos[0]["valor"] if planos else 120,
        "valor_novo": round((planos[0]["valor"] if planos else 120) * 1.1, 2), "vigencia": sugestao.isoformat(),
        "observacao": None})[1]
    return render_template("reajustes.html", planos=planos, contagem=contagem, historico=db.listar_reajustes(),
                           agendados={r["plano_id"] for r in db.reajustes_agendados()},
                           vigencia_sugerida=sugestao.isoformat(), minimo=(db.hoje() + timedelta(days=1)).isoformat(),
                           antecedencia=ANTECEDENCIA_RECOMENDADA, previa=previa, modos=_modos_envio())


@app.post("/reajustes/<int:reajuste_id>/<acao>")
@login_obrigatorio
def reajuste_acao(reajuste_id, acao):
    with db.conectar() as con:
        r = con.execute("SELECT * FROM reajustes WHERE id = ? AND status = 'agendado'", (reajuste_id,)).fetchone() or abort(404)
        if acao == "cancelar":
            con.execute("UPDATE reajustes SET status = 'cancelado' WHERE id = ?", (reajuste_id,))
            con.execute("UPDATE notificacoes SET status = 'descartado' WHERE chave = ? AND status = 'pendente'",
                        (f"reajuste:{reajuste_id}",))
        elif acao == "aplicar":
            con.execute("UPDATE planos SET valor = ? WHERE id = ?", (r["valor_novo"], r["plano_id"]))
            con.execute("UPDATE reajustes SET status = 'aplicado', aplicado_em = ? WHERE id = ?", (db.agora(), reajuste_id))
        else:
            abort(404)
    flash("Reajuste cancelado. Os avisos que ainda estavam na fila foram descartados; quem já recebeu não é avisado de novo."
          if acao == "cancelar" else "Novo valor aplicado ao plano a partir de hoje.", "ok")
    return redirect(url_for("reajustes"))


# ---------------------------------------------------------------- configurações

PRESETS_SMTP = {
    "Gmail": ("smtp.gmail.com", 587, "tls"),
    "Outlook / Hotmail": ("smtp-mail.outlook.com", 587, "tls"),
    "Microsoft 365": ("smtp.office365.com", 587, "tls"),
    "Hostinger": ("smtp.hostinger.com", 465, "ssl"),
    "Locaweb": ("email-ssl.com.br", 465, "ssl"),
    "Zoho": ("smtp.zoho.com", 465, "ssl"),
}


NOMES_WHATSAPP = {"manual": "Pelo meu WhatsApp", "simulado": "Simulado", "zapi": "Z-API", "evolution": "Evolution API",
                  "meta": "Meta Cloud API", "twilio": "Twilio"}
NOMES_EMAIL = {"manual": "Pelo meu e-mail", "smtp": "Servidor de e-mail (SMTP)", "resend": "Resend", "simulado": "Simulado"}
# (chave, descrição, ícone, cor)
PROVEDORES_EMAIL_TELA = [
    ("manual", "Sem configurar nada: você envia da fila com um toque", "fila", "g-azul"),
    ("smtp", "Envio automático pelo Gmail, Outlook ou o e-mail da academia", "mail", "g-verde"),
    ("resend", "Envio automático por API, com domínio próprio", "send", "g-violeta"),
    ("simulado", "Só registra, não envia (para testes)", "lock", "g-cinza"),
]
PROVEDORES_WHATSAPP_TELA = [
    ("manual", "Sem custo: abre o seu WhatsApp com a mensagem pronta", "fila", "g-verde"),
    ("simulado", "Só registra, não envia (para testes)", "lock", "g-cinza"),
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
            valores["wa_provedor"] = "manual"
        if valores.get("email_provedor") not in ajustes.PROVEDORES_EMAIL:
            valores["email_provedor"] = "manual"
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
    valores["email_provedor"] = ajustes.provedor_email()
    return render_template("configuracoes.html", v=valores, salvos=salvos, presets=PRESETS_SMTP,
                           provedores=PROVEDORES_WHATSAPP_TELA, provedores_email=PROVEDORES_EMAIL_TELA,
                           nomes_wa=NOMES_WHATSAPP, nomes_email=NOMES_EMAIL, modos=_modos_envio())


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
    if status == "pendente":
        flash("O e-mail está no modo manual: escolha Servidor de e-mail (SMTP) ou Resend, salve e teste de novo.", "erro")
    elif status == "simulado":
        flash("O e-mail está no modo simulado: escolha um provedor de envio e salve antes de testar.", "erro")
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
    if status in ("simulado", "pendente"):
        link = f"https://wa.me/{numero}"
        flash(f"No modo {'manual' if status == 'pendente' else 'simulado'} não há envio automático. "
              f"Para testar o envio manual, abra {link} no celular.", "erro")
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
