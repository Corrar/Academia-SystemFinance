"""Popula o banco com alunos e pagamentos fictícios para demonstração.

    python seed.py          # adiciona dados de exemplo
    python seed.py --limpar # apaga tudo antes
"""
import random
import sys
from datetime import timedelta

import db

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "João",
         "Larissa", "Marcos", "Natália", "Otávio", "Paula", "Rafael", "Sabrina", "Thiago", "Vanessa", "Wesley",
         "Beatriz", "Caio", "Débora", "Enzo", "Fernanda", "Gustavo", "Helena", "Igor", "Juliana", "Lucas"]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Pereira", "Lima", "Costa", "Ferreira", "Almeida", "Ribeiro"]


def main() -> None:
    db.iniciar_banco()
    rnd = random.Random(42)
    hoje = db.hoje()
    with db.conectar() as con:
        if "--limpar" in sys.argv:
            con.execute("DELETE FROM notificacoes")
            con.execute("DELETE FROM pagamentos")
            con.execute("DELETE FROM alunos")
        planos = con.execute("SELECT * FROM planos WHERE ativo = 1").fetchall()

        for i, nome in enumerate(NOMES):
            completo = f"{nome} {rnd.choice(SOBRENOMES)}"
            plano = planos[0] if rnd.random() < 0.75 else rnd.choice(planos)
            # distribui vencimentos entre 40 dias atrás e 45 dias à frente
            vencimento = hoje + timedelta(days=rnd.randint(-40, 45))
            inscricao = vencimento - timedelta(days=plano["duracao_dias"] * rnd.randint(1, 6))
            cur = con.execute(
                "INSERT INTO alunos (nome, cpf, email, telefone, plano_id, data_inscricao, data_vencimento, ativo) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (completo, f"{rnd.randint(100,999)}.{rnd.randint(100,999)}.{rnd.randint(100,999)}-{i:02d}",
                 f"{nome.lower()}.{i}@exemplo.com", f"(11) 9{rnd.randint(1000,9999)}-{rnd.randint(1000,9999)}",
                 plano["id"], inscricao.isoformat(), vencimento.isoformat(), 0 if i % 13 == 12 else 1),
            )
            # histórico de pagamentos: um por ciclo, da inscrição até o vencimento atual
            ini = inscricao
            while ini < vencimento:
                fim = ini + timedelta(days=plano["duracao_dias"])
                pago_em = min(ini + timedelta(days=rnd.randint(-2, 4)), hoje)
                con.execute(
                    "INSERT INTO pagamentos (aluno_id, valor, data_pagamento, validade_anterior, nova_validade, forma) "
                    "VALUES (?,?,?,?,?,?)",
                    (cur.lastrowid, plano["valor"], pago_em.isoformat(), ini.isoformat(), fim.isoformat(),
                     rnd.choice(["PIX", "PIX", "PIX", "Dinheiro", "Cartão de crédito", "Cartão de débito"])),
                )
                ini = fim
    print(f"{len(NOMES)} alunos FICTÍCIOS de demonstração cadastrados. Não use em produção: apague academia.db antes.")


if __name__ == "__main__":
    main()
