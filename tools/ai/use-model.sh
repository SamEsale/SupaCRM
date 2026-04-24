#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-auto}"
PROMPT="${*:2}"
PROMPT_LC="$(printf "%s" "$MODE $PROMPT" | tr '[:upper:]' '[:lower:]')"

route_architect() {
  cat > .codex/config.toml <<'TOML'
model = "qwen3.5:397b-cloud"
model_provider = "ollama"
model_reasoning_effort = "high"
TOML
  echo "Codex routed to qwen3.5:397b-cloud / high reasoning."
}

route_coder() {
  cat > .codex/config.toml <<'TOML'
model = "gemma4:31b-cloud"
model_provider = "ollama"
model_reasoning_effort = "medium"
TOML
  echo "Codex routed to gemma4:31b-cloud / medium reasoning."
}

route_fast_coder() {
  cat > .codex/config.toml <<'TOML'
model = "gemma4:31b-cloud"
model_provider = "ollama"
model_reasoning_effort = "low"
TOML
  echo "Codex routed to gemma4:31b-cloud / low reasoning."
}

case "$MODE" in
  architect|qwen|audit|plan|verify|review)
    route_architect
    ;;
  coder|gemma|implement|fix)
    route_coder
    ;;
  fast)
    route_fast_coder
    ;;
  auto)
    if echo "$PROMPT_LC" | grep -Eq "audit|architecture|architect|compare|alignment|align|backend.*frontend|frontend.*backend|migration|alembic|contract|recovery|recover|lost|forensic|phase|roadmap|plan|verify|review|risk"; then
      route_architect
    elif echo "$PROMPT_LC" | grep -Eq "typo|format|lint|small fix|css|copy|rename|simple|quick"; then
      route_fast_coder
    else
      route_coder
    fi
    ;;
  *)
    echo "Usage:"
    echo "  tools/ai/use-model.sh auto '<task prompt>'"
    echo "  tools/ai/use-model.sh architect"
    echo "  tools/ai/use-model.sh coder"
    echo "  tools/ai/use-model.sh fast"
    exit 1
    ;;
esac

printf "\nActive config:\n"
cat .codex/config.toml
