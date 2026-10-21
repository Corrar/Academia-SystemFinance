#!/bin/bash
# PreToolUse: sugere `graphify query` antes de buscas/leituras brutas de código.
# Só orienta (nunca bloqueia) e não faz nada se o Graphify não estiver instalado.
GRAPHIFY="$HOME/.local/share/graphify-venv/bin/graphify"
[ -x "$GRAPHIFY" ] || GRAPHIFY="$(command -v graphify || true)"
[ -n "$GRAPHIFY" ] || exit 0
exec "$GRAPHIFY" hook-guard "$1"
