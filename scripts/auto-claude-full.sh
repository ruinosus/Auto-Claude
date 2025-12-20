#!/bin/bash
# ===========================================
# Auto-Claude Full Setup
# Abre LiteLLM + Auto-Claude em terminais separados
# ===========================================

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Auto-Claude - Setup Completo${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Verificar AZURE_OPENAI_API_KEY
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    # Tentar carregar do .env
    ENV_FILE="$HOME/projects/claude-code-router/.env"
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi
fi

if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}AZURE_OPENAI_API_KEY nao encontrada${NC}"
    echo "Crie o arquivo: ~/projects/claude-code-router/.env"
    echo "Com o conteudo: AZURE_OPENAI_API_KEY=sua-chave"
    exit 1
fi

echo -e "${GREEN}Abrindo terminais...${NC}"
echo ""

# Detectar terminal (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Terminal 1: LiteLLM
    osascript -e "
    tell application \"Terminal\"
        do script \"cd $SCRIPT_DIR && ./start-litellm.sh\"
        activate
    end tell
    "

    # Esperar LiteLLM iniciar
    echo "Aguardando LiteLLM iniciar..."
    sleep 3

    # Terminal 2: Auto-Claude
    osascript -e "
    tell application \"Terminal\"
        do script \"cd $SCRIPT_DIR && ./start-auto-claude.sh\"
        activate
    end tell
    "

    echo ""
    echo -e "${GREEN}Terminais abertos!${NC}"
    echo ""
    echo "Terminal 1: LiteLLM Proxy (porta 3456)"
    echo "Terminal 2: Auto-Claude CLI"
else
    echo "Este script so funciona no macOS."
    echo "Use os scripts individuais:"
    echo "  Terminal 1: ./scripts/start-litellm.sh"
    echo "  Terminal 2: ./scripts/start-auto-claude.sh"
fi
