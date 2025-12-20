# Auto-Claude Architecture

Documentacao da arquitetura do Auto-Claude e integracao com proxy LiteLLM.

**Criado em:** 2025-12-19

---

## Visao Geral

O Auto-Claude e composto por dois componentes principais:

1. **Electron Frontend** (`auto-claude-ui/`) - Interface grafica desktop
2. **Python Backend** (`auto-claude/`) - Framework de agentes autonomos

O Python backend usa o **Claude Agent SDK** para comunicacao com a API.

---

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ELECTRON (Frontend)                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Profile Manager                                              │    │
│  │  - hasValidAuth() → verifica proxy mode                     │    │
│  │  - getProfileEnv() → retorna ANTHROPIC_BASE_URL + TOKEN     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Agent Manager → spawna processos Python com env vars        │    │
│  │  - Spec Creation: spec_runner.py                            │    │
│  │  - Task Execution: run.py                                   │    │
│  │  - QA: run.py --qa                                          │    │
│  │  - Ideation: ideation_runner.py                             │    │
│  │  - Roadmap: roadmap_runner.py                               │    │
│  │  - Insights: insights_runner.py                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ spawn(python, args, env)
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PYTHON (Backend)                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ core/auth.py                                                 │    │
│  │  - get_auth_token() → CLAUDE_CODE_OAUTH_TOKEN               │    │
│  │                     → ANTHROPIC_AUTH_TOKEN (proxy)          │    │
│  │  - get_sdk_env_vars() → passa ANTHROPIC_BASE_URL etc        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ claude_agent_sdk (Claude Agent SDK)                          │    │
│  │  - Usa env vars para configurar API endpoint                │    │
│  │  - Faz chamadas HTTP para ANTHROPIC_BASE_URL                │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTP requests
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LiteLLM PROXY (:3456)                            │
│  - Recebe requests no formato Anthropic                             │
│  - Converte para formato OpenAI                                     │
│  - Roteia para Azure OpenAI (GPT-4o)                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Componentes do Electron Frontend

### Profile Manager (`claude-profile-manager.ts`)

Gerencia perfis de autenticacao Claude. Suporta:

- **OAuth Token** - Token nativo do Claude Code
- **Config Dir** - Diretorio de configuracao (~/.claude)
- **Proxy Mode** - Credenciais de proxy (LiteLLM/Azure)

```typescript
// Verificacao de autenticacao (ordem de prioridade)
hasValidAuth(): boolean {
  // 1. Proxy mode habilitado
  if (profile.proxyEnabled && profile.proxyBaseUrl && profile.proxyApiKey) {
    return true;
  }
  // 2. OAuth token valido
  if (hasValidToken(profile)) {
    return true;
  }
  // 3. ConfigDir com credenciais
  if (isProfileAuthenticated(profile)) {
    return true;
  }
  return false;
}
```

### Agent Manager (`agent-manager.ts`)

Orquestra o ciclo de vida dos processos Python:

| Funcao | Script Python | Descricao |
|--------|---------------|-----------|
| `startSpecCreation()` | `spec_runner.py` | Cria especificacao de tarefa |
| `startTaskExecution()` | `run.py` | Executa implementacao |
| `startQAProcess()` | `run.py --qa` | Executa QA/review |
| `startIdeationGeneration()` | `ideation_runner.py` | Gera ideias |
| `startRoadmapGeneration()` | `roadmap_runner.py` | Gera roadmap |

### Environment Variables

O Electron passa variaveis de ambiente para os processos Python:

```typescript
// agent-queue.ts
const finalEnv = {
  ...process.env,           // Sistema
  ...combinedEnv,           // auto-claude/.env
  ...profileEnv,            // Profile (proxy ou OAuth)
  PYTHONPATH: autoBuildSource,
  PYTHONUNBUFFERED: '1',
};
```

Quando proxy mode esta ativo, `profileEnv` contem:

```typescript
{
  ANTHROPIC_BASE_URL: "http://127.0.0.1:3456",
  ANTHROPIC_AUTH_TOKEN: "sk-litellm-master-key"
}
```

---

## Componentes do Python Backend

### Autenticacao (`core/auth.py`)

Resolve token de autenticacao em ordem de prioridade:

```python
AUTH_TOKEN_ENV_VARS = [
    "CLAUDE_CODE_OAUTH_TOKEN",  # Original (maior prioridade)
    "ANTHROPIC_AUTH_TOKEN",     # CCR/proxy token
    "ANTHROPIC_API_KEY",        # API key direta
]

SDK_ENV_VARS = [
    "ANTHROPIC_BASE_URL",       # URL do proxy
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "NO_PROXY",
    "DISABLE_TELEMETRY",
    "DISABLE_COST_WARNINGS",
]
```

### Cliente SDK (`core/client.py`)

Configura o Claude Agent SDK:

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from core.auth import get_sdk_env_vars, require_auth_token

# SDK usa variaveis de ambiente automaticamente
# ANTHROPIC_BASE_URL → endpoint customizado
# ANTHROPIC_AUTH_TOKEN → autenticacao
```

### Runners Python

| Runner | Arquivo | Funcao |
|--------|---------|--------|
| Spec Runner | `runners/spec_runner.py` | Pipeline de criacao de spec |
| Task Runner | `run.py` | Executa planner → coder → QA |
| Ideation | `runners/ideation_runner.py` | Gera ideias de features |
| Roadmap | `runners/roadmap_runner.py` | Gera roadmap do projeto |
| Insights | `runners/insights_runner.py` | Chat com contexto do projeto |

---

## Proxy Mode (LiteLLM)

### Configuracao

**1. Profile de Proxy** (`~/Library/Application Support/auto-claude-ui/config/claude-profiles.json`):

```json
{
  "version": 3,
  "profiles": [
    {
      "id": "proxy-litellm",
      "name": "LiteLLM Proxy (Azure)",
      "isDefault": true,
      "proxyEnabled": true,
      "proxyBaseUrl": "http://127.0.0.1:3456",
      "proxyApiKey": "sk-litellm-master-key"
    }
  ],
  "activeProfileId": "proxy-litellm"
}
```

**2. LiteLLM Config** (`~/projects/claude-code-router/litellm_config.yaml`):

```yaml
model_list:
  - model_name: "claude-opus-4-5-20251101"
    litellm_params:
      model: "azure/gpt-4o"
      api_base: "https://your-azure-endpoint.openai.azure.com"
      api_key: "os.environ/AZURE_OPENAI_API_KEY"
      api_version: "2025-01-01-preview"

general_settings:
  master_key: "sk-litellm-master-key"
```

### Fluxo de Request

```
1. Electron → hasValidAuth() → proxy mode detectado
2. Electron → spawn Python com ANTHROPIC_BASE_URL
3. Python → claude_agent_sdk usa ANTHROPIC_BASE_URL
4. SDK → POST http://127.0.0.1:3456/v1/messages
5. LiteLLM → converte Anthropic → OpenAI format
6. LiteLLM → POST Azure OpenAI (GPT-4o)
7. LiteLLM → converte OpenAI → Anthropic format
8. SDK → retorna resposta para Python
```

---

## Features e Proxy

| Feature | Usa Proxy? | Como |
|---------|------------|------|
| Tasks (spec/build/QA) | ✅ | profileEnv → Python → SDK |
| Ideation | ✅ | profileEnv → Python → SDK |
| Roadmap | ✅ | profileEnv → Python → SDK |
| Insights | ✅ | profileEnv → Python → SDK |
| Terminal (Claude CLI) | ❌ | Usa Claude Code nativo |

**Nota:** O terminal integrado usa o Claude Code CLI diretamente, que tem sua propria configuracao.

---

## Arquivos Principais

### Electron Frontend

| Arquivo | Funcao |
|---------|--------|
| `src/main/claude-profile-manager.ts` | Gerencia perfis e proxy mode |
| `src/main/agent/agent-manager.ts` | Orquestra processos Python |
| `src/main/agent/agent-process.ts` | Spawna processos com env vars |
| `src/main/agent/agent-queue.ts` | Fila de execucao |
| `src/main/rate-limit-detector.ts` | getProfileEnv() |
| `src/main/ipc-handlers/autobuild-source-handlers.ts` | checkSourceToken() |

### Python Backend

| Arquivo | Funcao |
|---------|--------|
| `core/auth.py` | Resolve autenticacao |
| `core/client.py` | Configura Claude SDK |
| `run.py` | Entry point principal |
| `runners/spec_runner.py` | Pipeline de spec |
| `runners/ideation_runner.py` | Geracao de ideias |
| `runners/roadmap_runner.py` | Geracao de roadmap |

---

## Troubleshooting

### Verificar se proxy esta ativo

Nos logs do Electron, procure por:

```
[ClaudeProfileManager] Using proxy mode for profile: LiteLLM Proxy (Azure)
[CHECK_TOKEN] Proxy mode enabled for profile: LiteLLM Proxy (Azure)
[getProfileEnv] Using proxy mode for profile: LiteLLM Proxy (Azure) { baseUrl: 'http://127.0.0.1:3456' }
```

### Verificar requests no proxy

```bash
# Ver logs do LiteLLM
tail -f /tmp/litellm.log

# Deve mostrar requests como:
# POST /v1/messages 200 OK
```

### Profile nao carrega

Verificar path correto do config:
- **Correto:** `~/Library/Application Support/auto-claude-ui/config/claude-profiles.json`
- **Incorreto:** `~/Library/Application Support/Auto Claude/config/` (usa `name` do package.json, nao `productName`)

---

## Referencias

- [LiteLLM Docs](https://docs.litellm.ai/)
- [Claude Agent SDK](https://github.com/anthropics/claude-code)
- [Auto-Claude GitHub](https://github.com/AndyMik90/Auto-Claude)
