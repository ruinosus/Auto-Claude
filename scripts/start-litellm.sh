#!/bin/bash
# ===========================================
# Start LiteLLM + Proxy Wrapper for Auto-Claude
# ===========================================
# Arquitetura:
#   Auto-Claude -> Proxy Wrapper (3456) -> LiteLLM (3457) -> Azure OpenAI
#
# O Proxy Wrapper intercepta requests e limita max_tokens para 16384
# (limite do Azure GPT-4o)

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  LiteLLM + Proxy Wrapper${NC}"
echo -e "${GREEN}  (Azure OpenAI)${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Diretorio de config
CONFIG_DIR="$HOME/projects/claude-code-router"
CONFIG_FILE="$CONFIG_DIR/litellm_config.yaml"
PROXY_FILE="$CONFIG_DIR/proxy_wrapper.py"

# Verificar arquivos
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Erro: Config nao encontrada em $CONFIG_FILE${NC}"
    exit 1
fi

if [ ! -f "$PROXY_FILE" ]; then
    echo -e "${RED}Erro: Proxy wrapper nao encontrado em $PROXY_FILE${NC}"
    exit 1
fi

# Carregar .env
ENV_FILE="$CONFIG_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo -e "${RED}Erro: AZURE_OPENAI_API_KEY nao definida${NC}"
    echo "Crie o arquivo: $ENV_FILE"
    echo "Com: AZURE_OPENAI_API_KEY=sua-chave"
    exit 1
fi

echo -e "${GREEN}API Key:${NC} ${AZURE_OPENAI_API_KEY:0:10}..."
echo ""

# Parar processos anteriores
echo -e "${YELLOW}Parando processos anteriores...${NC}"
pkill -f "litellm.*3457" 2>/dev/null || true
pkill -f "proxy_wrapper" 2>/dev/null || true
sleep 1

# Ativar venv
source "$HOME/projects/.venv/bin/activate"

cd "$CONFIG_DIR"

# Iniciar LiteLLM na porta 3457 (background)
echo -e "${YELLOW}Iniciando LiteLLM na porta 3457...${NC}"
nohup litellm --config litellm_config.yaml --port 3457 --host 127.0.0.1 > /tmp/litellm.log 2>&1 &
LITELLM_PID=$!
echo "LiteLLM PID: $LITELLM_PID"

# Aguardar LiteLLM
sleep 3
if curl -s http://127.0.0.1:3457/health > /dev/null 2>&1; then
    echo -e "${GREEN}LiteLLM: OK${NC}"
else
    echo -e "${YELLOW}Aguardando LiteLLM...${NC}"
    sleep 3
fi

# Iniciar Proxy Wrapper na porta 3456 (foreground)
echo ""
echo -e "${GREEN}Iniciando Proxy Wrapper na porta 3456...${NC}"
echo -e "${GREEN}max_tokens limitado a 16384${NC}"
echo ""
echo -e "${YELLOW}Pressione Ctrl+C para parar${NC}"
echo ""

python proxy_wrapper.py
