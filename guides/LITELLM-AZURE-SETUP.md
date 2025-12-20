# Auto-Claude + LiteLLM + Azure OpenAI

Guia completo de setup - Criado em: 2025-12-19

---

## Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Auto-Claude   │────▶│    LiteLLM      │────▶│  Azure OpenAI   │
│   (Python CLI)  │     │    (Proxy)      │     │   (GPT-4o)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   Formato API             Converte                Formato API
   Anthropic               formatos                 OpenAI
```

**Por que precisa de proxy?**
- Auto-Claude usa o Claude Code SDK que espera API no formato Anthropic
- Azure OpenAI usa formato diferente (OpenAI)
- LiteLLM converte entre os formatos automaticamente

---

## Estrutura de Diretorios

```
~/projects/
├── claude-code-router/           # Configuracoes do proxy
│   ├── litellm_config.yaml       # Config do LiteLLM (PRINCIPAL)
│   ├── LITELLM-SETUP.md          # Documentacao LiteLLM
│   ├── AZURE-INTEGRATION-OPTIONS.md
│   └── config.json               # Config antiga do ccr (ignorar)
│
├── misc/Auto-Claude/             # Projeto Auto-Claude
│   ├── auto-claude/              # Codigo fonte do framework
│   │   ├── .venv/                # Virtual environment Python
│   │   ├── .env                  # Variaveis de ambiente
│   │   ├── run.py                # Ponto de entrada CLI
│   │   └── ...
│   ├── .auto-claude/             # Dados por projeto (gitignored)
│   │   └── specs/                # Specs criados
│   │       └── 001-test-litellm/
│   └── guides/                   # Documentacao
│       └── LITELLM-AZURE-SETUP.md  # ESTE ARQUIVO
│
└── .venv/                        # Outro venv (NAO USAR para Auto-Claude)
```

---

## Arquivos de Configuracao

### 1. LiteLLM Config (`~/projects/claude-code-router/litellm_config.yaml`)

```yaml
# Mapeia modelos Claude para Azure OpenAI
model_list:
  - model_name: "claude-opus-4-5-20251101"  # Modelo que Auto-Claude usa
    litellm_params:
      model: "azure/gpt-4o"
      api_base: "https://oai-cockpit-brazil-dev01.openai.azure.com"
      api_key: "os.environ/AZURE_OPENAI_API_KEY"
      api_version: "2025-01-01-preview"
      max_tokens: 16384  # Limite do Azure (IMPORTANTE!)

  # ... outros modelos ...

litellm_settings:
  drop_params: true
  modify_params: true

general_settings:
  master_key: "sk-litellm-master-key"  # Senha do proxy
```

### 2. Auto-Claude .env (`~/projects/misc/Auto-Claude/auto-claude/.env`)

```bash
# Aponta para o proxy LiteLLM
ANTHROPIC_BASE_URL=http://127.0.0.1:3456
ANTHROPIC_AUTH_TOKEN=sk-litellm-master-key
DISABLE_TELEMETRY=true
DISABLE_COST_WARNINGS=true
```

### 3. Azure API Key (variavel de ambiente)

```bash
# Definir no shell ANTES de iniciar o LiteLLM
export AZURE_OPENAI_API_KEY="sua-chave-aqui"
```

---

## Como Iniciar (Passo a Passo)

### Terminal 1: Iniciar LiteLLM Proxy

```bash
# 1. Definir API Key do Azure
export AZURE_OPENAI_API_KEY="sua-chave-aqui"

# 2. Ir para o diretorio de config
cd ~/projects/claude-code-router

# 3. Iniciar o proxy
litellm --config litellm_config.yaml --port 3456

# O proxy vai mostrar:
# INFO: Uvicorn running on http://127.0.0.1:3456
```

### Terminal 2: Usar Auto-Claude

```bash
# 1. Ir para o diretorio do Auto-Claude
cd ~/projects/misc/Auto-Claude/auto-claude

# 2. Ativar o virtual environment CORRETO
source .venv/bin/activate

# 3. Listar specs disponiveis
python run.py --list

# 4. Rodar um spec
python run.py --spec 001 --force
```

---

## Verificar se Esta Funcionando

### Testar LiteLLM (com proxy rodando)

```bash
# Health check
curl http://127.0.0.1:3456/health -H "Authorization: Bearer sk-litellm-master-key"

# Teste de request (formato Anthropic)
curl http://127.0.0.1:3456/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-litellm-master-key" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model": "claude-opus-4-5-20251101", "max_tokens": 50, "messages": [{"role": "user", "content": "Ola"}]}'
```

### Verificar Auto-Claude

```bash
cd ~/projects/misc/Auto-Claude/auto-claude
source .venv/bin/activate
python run.py --spec 001

# Deve mostrar:
# Auth: Using token from ANTHROPIC_AUTH_TOKEN
# API Endpoint: http://127.0.0.1:3456
```

---

## Mapeamento de Modelos

| Auto-Claude envia | LiteLLM roteia para | Uso |
|-------------------|---------------------|-----|
| claude-opus-4-5-20251101 | azure/gpt-4o | Modelo principal |
| claude-sonnet-4-20250514 | azure/gpt-4o | Tarefas gerais |
| claude-opus-4-20250514 | azure/gpt-4o | Tarefas complexas |
| claude-haiku-4-20250514 | azure/gpt-4o-mini | Background (barato) |
| claude-* (fallback) | azure/gpt-4o | Qualquer outro |

---

## Problemas Comuns

### Erro: "max_tokens is too large"

**Causa**: Azure GPT-4o suporta max 16384 tokens, mas Claude pede mais.

**Solucao**: Ja configurado no `litellm_config.yaml` com `max_tokens: 16384`.

### Erro: "No api key passed in"

**Causa**: Faltando header de autenticacao.

**Solucao**: Verificar que `ANTHROPIC_AUTH_TOKEN=sk-litellm-master-key` no `.env`.

### Erro: "Spec not found"

**Causa**: Specs ficam em `.auto-claude/specs/`, nao em `auto-claude/specs/`.

**Solucao**: Criar specs com `claude /spec` ou manualmente em `.auto-claude/specs/`.

### LiteLLM nao inicia

**Causa**: AZURE_OPENAI_API_KEY nao definida.

**Solucao**: `export AZURE_OPENAI_API_KEY="sua-chave"` antes de iniciar.

---

## Comandos Uteis

```bash
# === LITELLM ===
# Iniciar proxy
cd ~/projects/claude-code-router && litellm --config litellm_config.yaml --port 3456

# Parar proxy
Ctrl+C no terminal do LiteLLM

# === AUTO-CLAUDE ===
# Ativar ambiente
cd ~/projects/misc/Auto-Claude/auto-claude && source .venv/bin/activate

# Listar specs
python run.py --list

# Criar novo spec (interativo)
# Use: claude /spec

# Rodar spec
python run.py --spec 001 --force

# Ver status de um spec
python run.py --spec 001 --review-status
```

---

## Resumo Visual

```
ANTES DE USAR:
┌─────────────────────────────────────────────────────────┐
│  Terminal 1: export AZURE_OPENAI_API_KEY="..."          │
│              cd ~/projects/claude-code-router           │
│              litellm --config litellm_config.yaml       │
│                                                         │
│  Terminal 2: cd ~/projects/misc/Auto-Claude/auto-claude │
│              source .venv/bin/activate                  │
│              python run.py --spec 001 --force           │
└─────────────────────────────────────────────────────────┘

FLUXO DE DADOS:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Auto-Claude │───▶│  LiteLLM    │───▶│ Azure GPT-4o│
│   :auto     │    │  :3456      │    │   :443      │
│             │◀───│             │◀───│             │
└─────────────┘    └─────────────┘    └─────────────┘
  API Anthropic      Converte         API OpenAI
```

---

## Scripts de Inicializacao

Criamos scripts para facilitar:

```
scripts/
├── start-litellm.sh      # Inicia o proxy LiteLLM
├── start-auto-claude.sh  # Inicia o Auto-Claude CLI
└── auto-claude-full.sh   # Abre os dois em terminais separados (macOS)
```

### Uso Rapido (macOS)

```bash
# Opcao 1: Script que abre tudo
cd ~/projects/misc/Auto-Claude
./scripts/auto-claude-full.sh

# Opcao 2: Manualmente em 2 terminais
# Terminal 1:
./scripts/start-litellm.sh

# Terminal 2:
./scripts/start-auto-claude.sh
```

### Uso com argumentos

```bash
# Rodar spec diretamente
./scripts/start-auto-claude.sh --spec 001 --force

# Listar specs
./scripts/start-auto-claude.sh --list
```

---

## Status

**TESTADO E FUNCIONANDO** - 2025-12-19

A integracao foi validada com sucesso:
- Auto-Claude criou um spec, implementou e passou pelo QA
- O Proxy Wrapper intercepta e limita max_tokens corretamente
- GPT-4o responde no formato esperado pelo Claude Code SDK

## Links

- [LiteLLM Docs](https://docs.litellm.ai/)
- [LiteLLM Azure](https://docs.litellm.ai/docs/providers/azure)
- [Auto-Claude GitHub](https://github.com/...)
