# Setup do Auto-Claude no Mac (sem Docker Desktop)

Este guia mostra como configurar o Auto-Claude no macOS usando **Colima** como alternativa ao Docker Desktop.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      Auto-Claude                            │
├─────────────────────────────────────────────────────────────┤
│  Python Backend (auto-claude/)                              │
│    ├── claude-agent-sdk  ───────► Claude Code CLI (local)   │
│    ├── spec_runner.py            (npm package)              │
│    └── run.py                           │                   │
│                                         ▼                   │
│                                  Claude API (Anthropic)     │
├─────────────────────────────────────────────────────────────┤
│  Memory Layer (OPCIONAL)                                    │
│    └── FalkorDB ◄─── Colima (Docker runtime)                │
└─────────────────────────────────────────────────────────────┘
```

**Importante:** O Auto-Claude usa o **Claude Code CLI instalado localmente**, não a interface web. O SDK Python (`claude-agent-sdk`) spawna processos do CLI para executar os agentes.

---

## Pré-requisitos

| Componente | Versão Mínima | Como verificar |
|------------|---------------|----------------|
| macOS | 12+ | `sw_vers` |
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| Git | 2.x | `git --version` |
| Homebrew | - | `brew --version` |

---

## Passo 1: Instalar Colima (Alternativa ao Docker Desktop)

Colima é um runtime de containers leve que usa Lima (Linux virtual machines) para rodar Docker no Mac sem precisar do Docker Desktop.

```bash
# Instalar Colima + Docker CLI + Docker Compose
brew install colima docker docker-compose

# Iniciar Colima com recursos adequados
colima start --cpu 2 --memory 4 --disk 20

# Verificar se está funcionando
docker ps
docker info
```

### Comandos úteis do Colima

```bash
# Parar Colima (libera recursos)
colima stop

# Reiniciar
colima restart

# Status
colima status

# Iniciar com mais recursos (para builds pesados)
colima start --cpu 4 --memory 8
```

### Configurar Docker Compose para usar Colima

```bash
# O Colima já configura o socket automaticamente, mas se precisar:
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
```

---

## Passo 2: Instalar Claude Code CLI

O Auto-Claude depende do Claude Code CLI instalado globalmente.

```bash
# Instalar o CLI globalmente
npm install -g @anthropic-ai/claude-code

# Verificar instalação
claude --version

# Configurar autenticação (abre browser para login)
claude setup-token
```

**Requisitos de assinatura:** Claude Pro ou Claude Max é necessário para usar o Claude Code.

Após o login, o comando exibe um token. Guarde-o para o próximo passo.

---

## Passo 3: Configurar Ambiente Python

```bash
# Navegar para o diretório do auto-claude
cd /caminho/para/Auto-Claude/auto-claude

# Criar virtual environment e instalar dependências
# Opção A: usando uv (recomendado, mais rápido)
uv venv && uv pip install -r requirements.txt

# Opção B: usando pip tradicional
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Dependências instaladas

| Pacote | Propósito |
|--------|-----------|
| `claude-agent-sdk` | Wrapper Python para o Claude Code CLI |
| `python-dotenv` | Carrega variáveis do `.env` |
| `graphiti-core[falkordb]` | Memory Layer (opcional) |

---

## Passo 4: Configurar Variáveis de Ambiente

```bash
cd /caminho/para/Auto-Claude/auto-claude

# Copiar template
cp .env.example .env

# Editar com seu editor preferido
nano .env  # ou code .env, vim .env, etc.
```

### Configuração Mínima (obrigatória)

```bash
# Token obtido no Passo 2 (claude setup-token)
CLAUDE_CODE_OAUTH_TOKEN=seu-oauth-token-aqui
```

### Configuração Completa (recomendada)

```bash
# ==== AUTENTICAÇÃO (obrigatório - escolha UM) ====
CLAUDE_CODE_OAUTH_TOKEN=seu-oauth-token-aqui
# ou ANTHROPIC_API_KEY=sk-ant-...

# ==== MEMORY LAYER (opcional mas recomendado) ====
GRAPHITI_ENABLED=true
GRAPHITI_TELEMETRY_ENABLED=false

# Provider para o Graphiti (escolha um):

# Opção A: OpenAI (mais simples)
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Opção B: Ollama (totalmente offline/local)
# GRAPHITI_LLM_PROVIDER=ollama
# GRAPHITI_EMBEDDER_PROVIDER=ollama
# OLLAMA_LLM_MODEL=deepseek-r1:7b
# OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# OLLAMA_EMBEDDING_DIM=768

# ==== DEBUG (opcional) ====
# DEBUG=true
# DEBUG_LEVEL=1
```

---

## Passo 5: Iniciar FalkorDB (Memory Layer)

O Memory Layer é **opcional** mas altamente recomendado. Ele permite que os agentes lembrem contexto entre sessões.

```bash
# Certifique-se que o Colima está rodando
colima status  # deve mostrar "Running"

# Navegar para raiz do projeto
cd /caminho/para/Auto-Claude

# Iniciar apenas o FalkorDB
docker-compose up -d falkordb

# Verificar se está rodando
docker ps
# Deve mostrar: auto-claude-falkordb

# Ver logs (opcional)
docker-compose logs -f falkordb
```

### Verificar conexão

```bash
# Testar se o FalkorDB está respondendo
docker exec auto-claude-falkordb redis-cli ping
# Deve retornar: PONG
```

### Parar o FalkorDB

```bash
docker-compose down
# ou para manter os dados:
docker-compose stop falkordb
```

---

## Passo 6: Testar a Instalação

```bash
# Ativar o virtual environment
cd /caminho/para/Auto-Claude/auto-claude
source .venv/bin/activate

# Verificar se consegue importar os módulos
python -c "from claude_agent_sdk import ClaudeSDKClient; print('SDK OK')"

# Listar specs existentes (deve funcionar mesmo sem specs)
python run.py --list

# Criar uma spec de teste interativamente
python spec_runner.py --interactive
```

---

## Troubleshooting

### Colima não inicia

```bash
# Verificar logs
colima status
colima start --verbose

# Limpar e reiniciar
colima delete
colima start --cpu 2 --memory 4
```

### Docker compose não encontra o socket

```bash
# Definir o socket manualmente
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"

# Adicionar ao ~/.zshrc ou ~/.bashrc para persistir
echo 'export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"' >> ~/.zshrc
```

### Erro de autenticação do Claude

```bash
# Re-gerar o token
claude setup-token

# Verificar se o token está no .env
grep CLAUDE_CODE_OAUTH_TOKEN auto-claude/.env
```

### FalkorDB não conecta

```bash
# Verificar se o container está rodando
docker ps | grep falkordb

# Verificar logs do container
docker logs auto-claude-falkordb

# Verificar porta (deve ser 6380, não 6379)
docker port auto-claude-falkordb
```

### Graphiti não funciona

```bash
# Verificar se as variáveis estão configuradas
grep GRAPHITI auto-claude/.env

# Testar conexão com FalkorDB
docker exec auto-claude-falkordb redis-cli -p 6379 ping
```

---

## Comandos Rápidos de Referência

```bash
# ==== COLIMA ====
colima start              # Iniciar runtime
colima stop               # Parar (libera RAM)
colima status             # Ver status

# ==== FALKORDB ====
docker-compose up -d falkordb     # Iniciar
docker-compose stop falkordb      # Parar
docker-compose down               # Parar e remover

# ==== AUTO-CLAUDE ====
cd auto-claude && source .venv/bin/activate

python run.py --list                    # Listar specs
python spec_runner.py --interactive     # Criar spec interativo
python spec_runner.py --task "Descrição" # Criar spec de tarefa
python run.py --spec 001                # Executar build
python run.py --spec 001 --review       # Revisar mudanças
python run.py --spec 001 --merge        # Mergear para main
```

---

## Próximos Passos

1. Leia o [CLI-USAGE.md](CLI-USAGE.md) para uso detalhado do CLI
2. Explore o [DOCKER-SETUP.md](DOCKER-SETUP.md) para opções avançadas do Memory Layer
3. Crie sua primeira spec com `python spec_runner.py --interactive`

---

## Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| RAM | 8GB | 16GB+ |
| CPU | 2 cores | 4+ cores |
| Disco | 10GB livre | 20GB+ |

O Colima usa ~1-2GB de RAM quando rodando. O FalkorDB adiciona ~200-500MB.
