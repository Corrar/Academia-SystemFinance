#!/bin/bash
# Prepara a sessão do Claude Code na web: dependências do projeto (testes/linter)
# e o Graphify, que mantém o grafo do código em graphify-out/ como memória do projeto.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"
GRAPHIFY_VERSAO="0.9.93"
GRAPHIFY_VENV="$HOME/.local/share/graphify-venv"

# 1. Dependências do projeto num venv local (.venv já está no .gitignore e no .vercelignore)
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install --quiet --disable-pip-version-check -r requirements-dev.txt

# 2. Graphify num venv separado, fora do projeto, para não misturar com as dependências do app
if ! "$GRAPHIFY_VENV/bin/pip" show graphifyy 2>/dev/null | grep -qx "Version: $GRAPHIFY_VERSAO"; then
  python3 -m venv "$GRAPHIFY_VENV"
  "$GRAPHIFY_VENV/bin/pip" install --quiet --disable-pip-version-check "graphifyy==$GRAPHIFY_VERSAO"
fi
if [ -w /usr/local/bin ]; then
  ln -sf "$GRAPHIFY_VENV/bin/graphify" /usr/local/bin/graphify
else
  mkdir -p "$HOME/.local/bin"
  ln -sf "$GRAPHIFY_VENV/bin/graphify" "$HOME/.local/bin/graphify"
  [ -z "${CLAUDE_ENV_FILE:-}" ] || echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

# 3. O venv do projeto vira o Python padrão da sessão (pytest, pyflakes, flask)
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$PWD/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

# 4. Atualiza o grafo só com a AST (tree-sitter): sem LLM, sem chave de API, sem custo
GRAPHIFY_BACKEND=none "$GRAPHIFY_VENV/bin/graphify" update . >/dev/null
echo "Sessão pronta: dependências instaladas e grafo do Graphify atualizado em graphify-out/." >&2
