"""Versão do sistema e histórico de novidades (lidos de VERSION e CHANGELOG.md).

Uso na linha de comando (o workflow de release usa):
    python versao.py              -> imprime a versão atual
    python versao.py titulo 1.9.0 -> título da versão
    python versao.py notas 1.9.0  -> notas da versão em Markdown
"""
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
_SECAO = re.compile(r"^## \[(?P<versao>[^\]]+)\] - (?P<data>\d{4}-\d{2}-\d{2})(?: · (?P<titulo>.+))?$")

VERSAO = (RAIZ / "VERSION").read_text(encoding="utf-8").strip()
# a Vercel informa o commit publicado; fora dela fica vazio
COMMIT = (os.environ.get("VERCEL_GIT_COMMIT_SHA") or "")[:7]


@lru_cache(maxsize=1)
def historico() -> list[dict]:
    """Seções do CHANGELOG: [{versao, data, titulo, itens: [texto em Markdown]}], da mais nova à mais antiga."""
    secoes: list[dict] = []
    for linha in (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        m = _SECAO.match(linha.strip())
        if m:
            secoes.append({**m.groupdict(), "itens": []})
        elif secoes and linha.startswith("- "):
            secoes[-1]["itens"].append(linha[2:].strip())
    return secoes


def secao(versao: str) -> dict | None:
    return next((s for s in historico() if s["versao"] == versao), None)


def notas(versao: str) -> str:
    s = secao(versao)
    if not s:
        return ""
    return "\n".join("- " + item for item in s["itens"]) + (
        "\n\nHistórico completo: [CHANGELOG.md](https://github.com/Corrar/Academia-SystemFinance/blob/main/CHANGELOG.md)")


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else "versao"
    alvo = sys.argv[2] if len(sys.argv) > 2 else VERSAO
    if comando == "titulo":
        s = secao(alvo)
        print(f"v{alvo}" + (f" · {s['titulo']}" if s and s["titulo"] else ""))
    elif comando == "lista":
        # da mais antiga para a mais nova
        print("\n".join(s["versao"] for s in reversed(historico())))
    elif comando == "notas":
        texto = notas(alvo)
        if not texto:
            sys.exit(f"Versão {alvo} não encontrada no CHANGELOG.md")
        print(texto)
    else:
        print(VERSAO)
