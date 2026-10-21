"""Banco de dados SQLite: esquema, conexão e consultas de negócio."""
import sqlite3
from datetime import date, timedelta

import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS planos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    valor         REAL    NOT NULL,
    duracao_dias  INTEGER NOT NULL DEFAULT 30,
    ativo         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alunos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nome             TEXT NOT NULL,
    cpf              TEXT UNIQUE,
    email            TEXT,
    telefone         TEXT,
    data_nascimento  TEXT,
    plano_id         INTEGER REFERENCES planos(id),
    data_inscricao   TEXT NOT NULL,
    data_vencimento  TEXT NOT NULL,
    ativo            INTEGER NOT NULL DEFAULT 1,
    observacoes      TEXT,
    aceita_email     INTEGER NOT NULL DEFAULT 1,
    aceita_whatsapp  INTEGER NOT NULL DEFAULT 1,
    termos_aceitos_em TEXT,
    anonimizado_em   TEXT
);

CREATE TABLE IF NOT EXISTS pagamentos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id         INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    valor            REAL NOT NULL,
    data_pagamento   TEXT NOT NULL,
    validade_anterior TEXT,
    nova_validade    TEXT NOT NULL,
    forma            TEXT,
    criado_em        TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS notificacoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id     INTEGER REFERENCES alunos(id) ON DELETE CASCADE,
    canal        TEXT NOT NULL,          -- email | whatsapp
    tipo         TEXT NOT NULL,          -- lembrete | vencimento | atraso | manual
    chave        TEXT,                   -- evita aviso automático duplicado
    destino      TEXT,
    status       TEXT NOT NULL,          -- enviado | simulado | erro
    erro         TEXT,
    mensagem     TEXT,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS sistema (
    chave  TEXT PRIMARY KEY,
    valor  TEXT
);

CREATE INDEX IF NOT EXISTS idx_alunos_venc ON alunos(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_pag_data ON pagamentos(data_pagamento);
CREATE INDEX IF NOT EXISTS idx_notif_chave ON notificacoes(aluno_id, chave, canal);
"""

PLANOS_PADRAO = [
    ("Mensal", 120.00, 30),
    ("Trimestral", 330.00, 90),
    ("Semestral", 600.00, 180),
]


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


# Colunas adicionadas depois da primeira versão (bancos antigos recebem via ALTER TABLE)
MIGRACOES = {
    "alunos": {
        "aceita_email": "INTEGER NOT NULL DEFAULT 1",
        "aceita_whatsapp": "INTEGER NOT NULL DEFAULT 1",
        "termos_aceitos_em": "TEXT",
        "anonimizado_em": "TEXT",
    },
}


def iniciar_banco() -> None:
    with conectar() as con:
        con.executescript(ESQUEMA)
        for tabela, colunas in MIGRACOES.items():
            existentes = {r[1] for r in con.execute(f"PRAGMA table_info({tabela})")}
            for coluna, tipo in colunas.items():
                if coluna not in existentes:
                    con.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        if con.execute("SELECT COUNT(*) FROM planos").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO planos (nome, valor, duracao_dias) VALUES (?,?,?)", PLANOS_PADRAO
            )


# ---------------------------------------------------------------- utilidades

def hoje() -> date:
    return date.today()


def dias_para_vencer(data_vencimento: str) -> int:
    """Positivo = dias restantes; negativo = dias em atraso."""
    return (date.fromisoformat(data_vencimento) - hoje()).days


def status_aluno(aluno) -> str:
    if not aluno["ativo"]:
        return "inativo"
    dias = dias_para_vencer(aluno["data_vencimento"])
    if dias <= -config.DIAS_INADIMPLENCIA:
        return "inadimplente"
    if dias < 0:
        return "vencido"
    if dias <= 7:
        return "a_vencer"
    return "em_dia"


SQL_ALUNO = """
SELECT a.*, p.nome AS plano_nome, p.valor AS plano_valor, p.duracao_dias AS plano_duracao
FROM alunos a LEFT JOIN planos p ON p.id = a.plano_id
"""


def _enriquecer(linhas):
    lista = []
    for r in linhas:
        d = dict(r)
        d["dias"] = dias_para_vencer(d["data_vencimento"])
        d["status"] = status_aluno(d)
        # progresso do ciclo atual (0 a 100%), usado na barra dos cards
        duracao = d.get("plano_duracao") or 30
        d["ciclo_pct"] = max(0, min(100, round((duracao - d["dias"]) / duracao * 100)))
        d["inicio_ciclo"] = (date.fromisoformat(d["data_vencimento"]) - timedelta(days=duracao)).isoformat()
        lista.append(d)
    return lista


def avisos_do_ciclo(alunos: list[dict]) -> None:
    """Preenche `avisos_enviados` (dias relativos já avisados no vencimento atual)."""
    if not alunos:
        return
    marcadores = ",".join("?" * len(alunos))
    with conectar() as con:
        linhas = con.execute(
            f"SELECT DISTINCT aluno_id, chave FROM notificacoes WHERE aluno_id IN ({marcadores}) "
            "AND chave IS NOT NULL AND status IN ('enviado','simulado')",
            [a["id"] for a in alunos],
        ).fetchall()
    for a in alunos:
        prefixo = a["data_vencimento"] + ":"
        a["avisos_enviados"] = {int(c[len(prefixo):]) for i, c in linhas if i == a["id"] and c.startswith(prefixo)}


# ---------------------------------------------------------------- consultas

def buscar_alunos(termo: str = "", status: str = "") -> list[dict]:
    sql = SQL_ALUNO
    params: list = []
    if termo:
        digitos = "".join(c for c in termo if c.isdigit())
        sql += " WHERE (a.nome LIKE ? OR a.email LIKE ?"
        params += [f"%{termo}%", f"%{termo}%"]
        if digitos:
            sql += " OR REPLACE(REPLACE(REPLACE(a.cpf,'.',''),'-',''),' ','') LIKE ?"
            sql += " OR REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(a.telefone,'(',''),')',''),'-',''),' ',''),'+','') LIKE ?"
            params += [f"%{digitos}%", f"%{digitos}%"]
        sql += ")"
    sql += " ORDER BY a.nome COLLATE NOCASE"
    with conectar() as con:
        alunos = _enriquecer(con.execute(sql, params).fetchall())
    if status:
        alunos = [a for a in alunos if a["status"] == status]
    return alunos


def obter_aluno(aluno_id: int) -> dict | None:
    with conectar() as con:
        r = con.execute(SQL_ALUNO + " WHERE a.id = ?", (aluno_id,)).fetchone()
    return _enriquecer([r])[0] if r else None


def inadimplentes(dias_min: int | None = None) -> list[dict]:
    """Alunos ativos com `dias_min`+ dias após o vencimento (sem pagamento)."""
    dias_min = config.DIAS_INADIMPLENCIA if dias_min is None else dias_min
    limite = (hoje() - timedelta(days=dias_min)).isoformat()
    with conectar() as con:
        linhas = con.execute(
            SQL_ALUNO + " WHERE a.ativo = 1 AND a.data_vencimento <= ? ORDER BY a.data_vencimento",
            (limite,),
        ).fetchall()
    return _enriquecer(linhas)


def proximos_vencimentos(dias: int = 7) -> list[dict]:
    with conectar() as con:
        linhas = con.execute(
            SQL_ALUNO + " WHERE a.ativo = 1 AND a.data_vencimento BETWEEN ? AND ? ORDER BY a.data_vencimento",
            (hoje().isoformat(), (hoje() + timedelta(days=dias)).isoformat()),
        ).fetchall()
    return _enriquecer(linhas)


def resumo_dashboard() -> dict:
    h = hoje()
    inicio_mes = h.replace(day=1).isoformat()
    with conectar() as con:
        q = lambda sql, *p: con.execute(sql, p).fetchone()[0]
        ativos = q("SELECT COUNT(*) FROM alunos WHERE ativo = 1")
        em_dia = q("SELECT COUNT(*) FROM alunos WHERE ativo = 1 AND data_vencimento >= ?", h.isoformat())
        faturado_mes = q(
            "SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE data_pagamento >= ? AND data_pagamento <= ?",
            inicio_mes, h.isoformat(),
        )
        pagamentos_mes = q("SELECT COUNT(*) FROM pagamentos WHERE data_pagamento >= ?", inicio_mes)
        # Receita mensal recorrente: valor do plano convertido para 30 dias
        mrr = q(
            "SELECT COALESCE(SUM(p.valor * 30.0 / p.duracao_dias),0) FROM alunos a "
            "JOIN planos p ON p.id = a.plano_id WHERE a.ativo = 1"
        )
        novos_mes = q("SELECT COUNT(*) FROM alunos WHERE data_inscricao >= ?", inicio_mes)

        historico = []
        for i in range(5, -1, -1):
            ano, mes = h.year, h.month - i
            while mes <= 0:
                mes += 12
                ano -= 1
            prefixo = f"{ano:04d}-{mes:02d}"
            total = q("SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE substr(data_pagamento,1,7) = ?", prefixo)
            historico.append({"mes": prefixo, "total": total})

    devedores = inadimplentes()
    return {
        "ativos": ativos,
        "em_dia": em_dia,
        "vencidos": ativos - em_dia,
        "faturado_mes": faturado_mes,
        "pagamentos_mes": pagamentos_mes,
        "mrr": mrr,
        "novos_mes": novos_mes,
        "inadimplentes": devedores,
        "valor_em_aberto": sum(a["plano_valor"] or 0 for a in devedores),
        "historico": historico,
    }


def pagamentos_aluno(aluno_id: int):
    with conectar() as con:
        return con.execute(
            "SELECT * FROM pagamentos WHERE aluno_id = ? ORDER BY data_pagamento DESC, id DESC", (aluno_id,)
        ).fetchall()


def pagamentos_periodo(inicio: str, fim: str):
    with conectar() as con:
        return con.execute(
            "SELECT pg.*, a.nome FROM pagamentos pg JOIN alunos a ON a.id = pg.aluno_id "
            "WHERE pg.data_pagamento BETWEEN ? AND ? ORDER BY pg.data_pagamento DESC, pg.id DESC",
            (inicio, fim),
        ).fetchall()


def listar_planos(somente_ativos: bool = False):
    sql = "SELECT * FROM planos" + (" WHERE ativo = 1" if somente_ativos else "") + " ORDER BY duracao_dias, valor"
    with conectar() as con:
        return con.execute(sql).fetchall()


def notificacoes_recentes(limite: int = 100, aluno_id: int | None = None):
    sql = "SELECT n.*, a.nome FROM notificacoes n LEFT JOIN alunos a ON a.id = n.aluno_id"
    params: tuple = ()
    if aluno_id:
        sql += " WHERE n.aluno_id = ?"
        params = (aluno_id,)
    sql += " ORDER BY n.id DESC LIMIT ?"
    with conectar() as con:
        return con.execute(sql, params + (limite,)).fetchall()


def get_sistema(chave: str) -> str | None:
    with conectar() as con:
        r = con.execute("SELECT valor FROM sistema WHERE chave = ?", (chave,)).fetchone()
    return r[0] if r else None


def set_sistema(chave: str, valor: str) -> None:
    with conectar() as con:
        con.execute(
            "INSERT INTO sistema (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, valor),
        )


# ---------------------------------------------------------------- LGPD

def exportar_aluno(aluno_id: int) -> dict | None:
    """Todos os dados pessoais do aluno (direito de acesso/portabilidade, art. 18 da LGPD)."""
    with conectar() as con:
        aluno = con.execute(SQL_ALUNO + " WHERE a.id = ?", (aluno_id,)).fetchone()
        if not aluno:
            return None
        pagamentos = con.execute("SELECT * FROM pagamentos WHERE aluno_id = ? ORDER BY data_pagamento", (aluno_id,)).fetchall()
        avisos = con.execute("SELECT canal, tipo, destino, status, mensagem, criado_em FROM notificacoes "
                             "WHERE aluno_id = ? ORDER BY id", (aluno_id,)).fetchall()
    return {"aluno": dict(aluno), "pagamentos": [dict(p) for p in pagamentos], "avisos": [dict(a) for a in avisos]}


def anonimizar_aluno(aluno_id: int) -> None:
    """Apaga os dados pessoais e mantém só os valores pagos (exigidos pela legislação fiscal)."""
    with conectar() as con:
        con.execute(
            "UPDATE alunos SET nome = ?, cpf = NULL, email = NULL, telefone = NULL, data_nascimento = NULL, "
            "observacoes = NULL, ativo = 0, aceita_email = 0, aceita_whatsapp = 0, "
            "anonimizado_em = datetime('now','localtime') WHERE id = ?",
            (f"Aluno removido #{aluno_id}", aluno_id),
        )
        con.execute("DELETE FROM notificacoes WHERE aluno_id = ?", (aluno_id,))


def limpar_avisos_antigos(dias: int) -> int:
    with conectar() as con:
        return con.execute("DELETE FROM notificacoes WHERE criado_em < datetime('now','localtime', ?)",
                           (f"-{dias} days",)).rowcount
