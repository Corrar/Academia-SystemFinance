"""Cobrança automática: envia avisos nos dias configurados em DIAS_AVISO.

Roda sozinha dentro do app (uma vez por dia, a partir de HORA_COBRANCA),
ou pode ser chamada pelo cron/Agendador de Tarefas:

    python cobranca.py
"""
import threading
import time
from datetime import datetime, timedelta

import config
import db
import notificacoes

_trava = threading.Lock()


def executar_cobranca() -> dict:
    """Envia avisos para quem está exatamente em um dos dias de DIAS_AVISO.

    A `chave` (vencimento + dia relativo) garante que cada aviso só seja
    enviado uma vez, mesmo que a rotina rode várias vezes no mesmo dia.
    Quem está inadimplente e passou do último dia configurado recebe
    um novo aviso a cada 7 dias até regularizar.
    """
    with _trava:
        hoje = db.hoje()
        resumo = {"avaliados": 0, "avisados": 0, "erros": 0, "detalhes": []}
        ultimo = max(config.DIAS_AVISO) if config.DIAS_AVISO else None

        for aluno in db.buscar_alunos():
            if not aluno["ativo"]:
                continue
            resumo["avaliados"] += 1
            relativo = -aluno["dias"]  # dias após o vencimento (negativo = antes)

            dia_aviso = None
            if relativo in config.DIAS_AVISO:
                dia_aviso = relativo
            elif ultimo is not None and ultimo > 0 and relativo > ultimo and (relativo - ultimo) % 7 == 0:
                dia_aviso = relativo  # lembrete semanal p/ inadimplentes

            if dia_aviso is None:
                continue

            chave = f"{aluno['data_vencimento']}:{dia_aviso:+d}"
            res = notificacoes.notificar(aluno, chave=chave)
            if any(s in ("enviado", "simulado") for s in res.values()):
                resumo["avisados"] += 1
            if "erro" in res.values():
                resumo["erros"] += 1
            resumo["detalhes"].append({"aluno": aluno["nome"], "dia": dia_aviso, "resultado": res})

        db.set_sistema("ultima_cobranca", datetime.now().isoformat(timespec="seconds"))
        db.set_sistema("ultima_cobranca_dia", hoje.isoformat())
        return resumo


def _loop_agendador() -> None:
    while True:
        try:
            agora = datetime.now()
            if agora.hour >= config.HORA_COBRANCA and db.get_sistema("ultima_cobranca_dia") != agora.date().isoformat():
                r = executar_cobranca()
                print(f"[cobrança] {agora:%d/%m %H:%M} – {r['avisados']} aluno(s) avisado(s), {r['erros']} erro(s)")
        except Exception as e:  # noqa: BLE001 - o agendador nunca deve morrer
            print(f"[cobrança] falha: {e}")
        time.sleep(600)  # verifica a cada 10 minutos


def iniciar_agendador() -> None:
    threading.Thread(target=_loop_agendador, name="agendador-cobranca", daemon=True).start()


def proxima_execucao() -> datetime:
    agora = datetime.now()
    alvo = agora.replace(hour=config.HORA_COBRANCA, minute=0, second=0, microsecond=0)
    if db.get_sistema("ultima_cobranca_dia") == agora.date().isoformat():
        return alvo + timedelta(days=1)
    return max(alvo, agora)


if __name__ == "__main__":
    db.iniciar_banco()
    r = executar_cobranca()
    print(f"Avaliados: {r['avaliados']} | Avisados: {r['avisados']} | Erros: {r['erros']}")
    for d in r["detalhes"]:
        print(f"  - {d['aluno']} (dia {d['dia']:+d}): {d['resultado']}")
