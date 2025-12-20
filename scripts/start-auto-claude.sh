#!/bin/bash
# ===========================================
# Start Auto-Claude CLI
# ===========================================

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Auto-Claude - Autonomous Builder${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Diretorio do Auto-Claude
AUTO_CLAUDE_DIR="$HOME/projects/misc/Auto-Claude/auto-claude"

# Verificar se diretorio existe
if [ ! -d "$AUTO_CLAUDE_DIR" ]; then
    echo -e "${RED}Erro: Diretorio nao encontrado: $AUTO_CLAUDE_DIR${NC}"
    exit 1
fi

cd "$AUTO_CLAUDE_DIR"

# Verificar venv
if [ ! -d ".venv" ]; then
    echo -e "${RED}Erro: Virtual environment nao encontrado${NC}"
    echo "Crie com: cd $AUTO_CLAUDE_DIR && uv venv && uv pip install -r requirements.txt"
    exit 1
fi

# Ativar venv
source .venv/bin/activate

# Verificar se LiteLLM esta rodando
if ! curl -s http://127.0.0.1:3456/health > /dev/null 2>&1; then
    echo -e "${YELLOW}Aviso: LiteLLM nao parece estar rodando na porta 3456${NC}"
    echo -e "${YELLOW}Inicie em outro terminal: ./scripts/start-litellm.sh${NC}"
    echo ""
fi

# Mostrar info
echo -e "${GREEN}Diretorio:${NC} $AUTO_CLAUDE_DIR"
echo -e "${GREEN}Venv:${NC} Ativado"
echo ""

# Se passou argumentos, executar diretamente
if [ $# -gt 0 ]; then
    echo -e "${BLUE}Executando: python run.py $@${NC}"
    echo ""
    python run.py "$@"
else
    # Menu interativo
    echo -e "${BLUE}Comandos disponiveis:${NC}"
    echo ""
    echo "  python run.py --list              # Listar specs"
    echo "  python run.py --spec 001 --force  # Rodar spec"
    echo "  claude /spec                      # Criar novo spec"
    echo ""
    echo -e "${YELLOW}Voce esta no shell do Auto-Claude. Digite os comandos acima.${NC}"
    echo ""

    # Abrir subshell
    exec $SHELL
fi
