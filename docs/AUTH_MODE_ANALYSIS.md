# Auth Mode Detection Analysis

## Executive Summary

O sistema apresenta uma **desconexão entre a configuração de Profile (Azure Foundry) e a detecção de auth mode no backend**. Quando o usuário configura Azure Foundry via Profile, o log mostra incorretamente "Using auth mode: oauth" porque a detecção lê de uma fonte diferente da configuração.

**Resultado:** O sistema **funciona corretamente** (Azure Foundry é usado), mas **reporta incorretamente** o modo de autenticação nos logs.

---

## O Problema Principal

### Duas Fontes de Configuração Não Sincronizadas

| Fonte | Onde Armazena | Quem Lê |
|-------|---------------|---------|
| **ClaudeProfile** (UI) | `proxyEnabled`, `proxyBaseUrl`, `proxyApiKey` | `getProfileEnv()` → seta `CLAUDE_CODE_USE_FOUNDRY=1` |
| **Project .env** | `CLAUDE_AUTH_MODE=oauth\|azure-foundry\|auth-token` | `hasValidProjectAuth()` → loga o auth mode |

### O Fluxo Atual (Bug)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Usuário configura Azure Foundry no Profile UI                          │
│                           ↓                                             │
│  Profile salvo com: proxyEnabled=true, proxyBaseUrl, proxyApiKey        │
│                           ↓                                             │
│  getProfileEnv() detecta proxy Azure → seta CLAUDE_CODE_USE_FOUNDRY=1   │
│                           ↓                                             │
│  ✅ Environment correto: ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN       │
│                                                                         │
│  MAS TAMBÉM...                                                          │
│                           ↓                                             │
│  hasValidProjectAuth() lê CLAUDE_AUTH_MODE do project .env              │
│                           ↓                                             │
│  CLAUDE_AUTH_MODE não existe no .env → default = 'oauth'                │
│                           ↓                                             │
│  ❌ Log: "Using auth mode: oauth"  ← INCORRETO!                         │
│                           ↓                                             │
│  ✅ Backend recebe CLAUDE_CODE_USE_FOUNDRY=1 → usa Foundry corretamente │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Arquivos Envolvidos

### Frontend (TypeScript)

| Arquivo | Linhas | Função | Descrição |
|---------|--------|--------|-----------|
| `apps/frontend/src/main/claude-profile-manager.ts` | 347-400 | `getActiveProfileEnv()` | Detecta proxy mode, seta `CLAUDE_CODE_USE_FOUNDRY='1'` |
| `apps/frontend/src/main/rate-limit-detector.ts` | 253-342 | `getProfileEnv()` | Lógica similar de detecção de proxy |
| `apps/frontend/src/main/ipc-handlers/task/execution-handlers.ts` | 18-96 | `hasValidProjectAuth()` | Lê `CLAUDE_AUTH_MODE` do project `.env` |
| `apps/frontend/src/main/ipc-handlers/task/execution-handlers.ts` | **183** | - | **LINHA DO LOG**: `Using auth mode: ${authCheck.mode}` |
| `apps/frontend/src/main/ipc-handlers/env-handlers.ts` | 45-295 | `generateEnvContent()` | Escreve project `.env` |

### Backend (Python)

| Arquivo | Linhas | Função | Descrição |
|---------|--------|--------|-----------|
| `apps/backend/core/auth.py` | 205-213 | `is_foundry_mode()` | Detecta Foundry via `CLAUDE_CODE_USE_FOUNDRY` |
| `apps/backend/core/auth.py` | 216-262 | `cleanup_conflicting_env_vars()` | Remove vars conflitantes baseado no modo |
| `apps/backend/core/auth.py` | 265-335 | `get_sdk_env_vars()` | Filtra env vars para o SDK baseado no modo |

---

## Detalhes Técnicos

### Como Azure Foundry é Detectado (Profile)

**Arquivo:** `apps/frontend/src/main/claude-profile-manager.ts` (linhas 359-374)

```typescript
// Priority 1: Proxy mode (LiteLLM/Azure OpenAI)
if (profile?.proxyEnabled && profile.proxyBaseUrl && profile.proxyApiKey) {
  env.ANTHROPIC_BASE_URL = profile.proxyBaseUrl;
  env.ANTHROPIC_AUTH_TOKEN = profile.proxyApiKey;

  // Detecção automática de Azure Foundry
  const isAzureFoundry = profile.proxyBaseUrl.includes('.azure.com') ||
                         profile.proxyBaseUrl.includes('azure') ||
                         profile.proxyBaseUrl.includes('foundry');

  if (isAzureFoundry) {
    env.CLAUDE_CODE_USE_FOUNDRY = '1';  // ← Seta corretamente!
    env.ANTHROPIC_DEFAULT_SONNET_MODEL = 'claude-sonnet-4-5';
    env.ANTHROPIC_DEFAULT_HAIKU_MODEL = 'claude-haiku-4-5';
    env.ANTHROPIC_DEFAULT_OPUS_MODEL = 'claude-opus-4-5';
  }
}
```

### Como Auth Mode é Reportado (Bug)

**Arquivo:** `apps/frontend/src/main/ipc-handlers/task/execution-handlers.ts` (linhas 36-37)

```typescript
// Só lê do project .env, ignora profile!
const authMode = vars['CLAUDE_AUTH_MODE'] || 'oauth';  // ← Default 'oauth'
```

**Linha 183:**
```typescript
console.log(`[TASK_START] Using auth mode: ${authCheck.mode}`);  // ← Log incorreto
```

### Como Backend Usa Foundry (Funciona)

**Arquivo:** `apps/backend/core/auth.py` (linhas 205-213)

```python
def is_foundry_mode() -> bool:
    """Check if Azure Foundry authentication mode is enabled."""
    foundry = os.environ.get("CLAUDE_CODE_USE_FOUNDRY", "")
    return foundry in ("1", "true", "True")  # ← Detecta corretamente!
```

---

## Onde `CLAUDE_CODE_USE_FOUNDRY` é Setado

| Arquivo | Linha | Trigger |
|---------|-------|---------|
| `claude-profile-manager.ts` | 364 | Profile proxy enabled + URL contém 'azure', 'foundry', ou '.azure.com' |
| `rate-limit-detector.ts` | 291-296 | Profile proxy enabled + URL contém 'azure', 'foundry', ou '.azure.com' |
| `env-handlers.ts` | 66 | Usuário salva config Azure Foundry manualmente no project .env |

## Onde `CLAUDE_AUTH_MODE` é Lido/Escrito

**Leitura:**
- `execution-handlers.ts:37` - `hasValidProjectAuth()` lê do project .env
- `env-handlers.ts:346-348` - Carregando config do projeto

**Escrita:**
- `env-handlers.ts:54-56` - Salvando config do projeto manualmente

**Nunca escrito automaticamente quando Profile é setado!**

---

## Impacto

| Aspecto | Status | Descrição |
|---------|--------|-----------|
| **Funcionalidade** | ✅ OK | Azure Foundry funciona corretamente (env var `CLAUDE_CODE_USE_FOUNDRY=1` é setada pelo Profile) |
| **Logs** | ❌ Incorreto | Reporta "oauth" quando deveria reportar "azure-foundry" ou "profile-proxy" |
| **Confusão** | ⚠️ Alto | Usuário vê log dizendo OAuth mas configurou Azure Foundry |
| **Backend** | ✅ OK | Detecta corretamente via `is_foundry_mode()` usando `CLAUDE_CODE_USE_FOUNDRY` |

---

## Soluções Recomendadas

### Solução 1: Atualizar `hasValidProjectAuth()` (Recomendada)

Modificar para verificar **ambas** as fontes de configuração:

**Arquivo:** `apps/frontend/src/main/ipc-handlers/task/execution-handlers.ts`

```typescript
import { getClaudeProfileManager } from '../../claude-profile-manager';

function hasValidProjectAuth(project: Project): { valid: boolean; mode: string; error?: string } {
  // 1. Primeiro verifica profile ativo (tem precedência)
  const profileManager = getClaudeProfileManager();
  const activeProfile = profileManager.getActiveProfile();

  if (activeProfile?.proxyEnabled && activeProfile?.proxyBaseUrl && activeProfile?.proxyApiKey) {
    const isAzure = activeProfile.proxyBaseUrl.includes('azure') ||
                    activeProfile.proxyBaseUrl.includes('foundry') ||
                    activeProfile.proxyBaseUrl.includes('.azure.com');

    if (isAzure) {
      return { valid: true, mode: 'azure-foundry (profile)' };
    }
    return { valid: true, mode: 'proxy (profile)' };
  }

  // 2. Verifica OAuth token no profile
  if (profileManager.hasValidAuth()) {
    return { valid: true, mode: 'oauth (profile)' };
  }

  // 3. Fallback para project .env
  // ... código existente para ler CLAUDE_AUTH_MODE do .env ...
}
```

### Solução 2: Sincronizar Profile → Project .env

Quando profile é ativado, atualizar `CLAUDE_AUTH_MODE` no project `.env`:

**Arquivo:** `apps/frontend/src/main/claude-profile-manager.ts`

```typescript
async setActiveProfile(profileId: string, projectPath?: string): Promise<void> {
  // ... código existente ...

  // Sincronizar auth mode no project .env
  if (projectPath && profile.proxyEnabled) {
    const isAzure = profile.proxyBaseUrl?.includes('azure');
    const authMode = isAzure ? 'azure-foundry' : 'proxy';
    await this.updateProjectAuthMode(projectPath, authMode);
  }
}
```

### Solução 3: Logging Unificado

Criar função centralizada para reportar auth mode:

```typescript
function getEffectiveAuthMode(): string {
  const profileManager = getClaudeProfileManager();
  const profile = profileManager.getActiveProfile();

  // Profile proxy tem precedência
  if (profile?.proxyEnabled && profile?.proxyBaseUrl) {
    const isAzure = profile.proxyBaseUrl.includes('azure') ||
                    profile.proxyBaseUrl.includes('foundry');
    return isAzure ? 'azure-foundry' : 'proxy';
  }

  // Profile OAuth token
  if (profile?.oauthToken) {
    return 'oauth';
  }

  // Fallback para CLAUDE_AUTH_MODE do .env
  return process.env.CLAUDE_AUTH_MODE || 'oauth';
}
```

---

## Verificação Rápida

Para confirmar que Azure Foundry está funcionando apesar do log incorreto:

```bash
# No log você deve ver AMBOS:
[TASK_START] Using auth mode: oauth           # ← Log incorreto (bug)
[ClaudeProfileManager] Using proxy mode...    # ← Confirma que proxy está ativo
[getProfileEnv] Using proxy mode...           # ← Confirma Azure Foundry detectado
[getProfileEnv] Azure Foundry detected...     # ← Confirma model overrides
```

O fato de ver "Azure Foundry detected" significa que **está funcionando**, apenas o log de auth mode está incorreto.

---

## Arquivos para Modificar (Ordem de Prioridade)

1. **`apps/frontend/src/main/ipc-handlers/task/execution-handlers.ts`**
   - Função: `hasValidProjectAuth()` (linhas 18-96)
   - Mudança: Verificar profile ativo além do project .env
   - Impacto: Corrige o log e a validação de auth

2. **`apps/frontend/src/main/claude-profile-manager.ts`**
   - Função: `setActiveProfile()` (linhas 250-260)
   - Mudança: Sincronizar auth mode no project quando profile muda (opcional)

3. **`apps/frontend/src/main/ipc-handlers/env-handlers.ts`**
   - Função: `generateEnvContent()` (linhas 45-295)
   - Mudança: Garantir consistência entre fontes (opcional)

---

## Conclusão

O sistema tem uma **arquitetura de configuração dividida** que causa confusão:

- **Profile system** (UI) → gerencia credenciais de proxy/Azure via `getActiveProfileEnv()` e `getProfileEnv()`
- **Project .env** → gerencia auth mode reportado via `hasValidProjectAuth()`

Quando usuário usa Profile com Azure Foundry:
- ✅ Funciona corretamente (env vars corretas são setadas pelo Profile)
- ❌ Reporta incorretamente como "oauth" (hasValidProjectAuth lê do .env, não do Profile)

**Recomendação:** Implementar Solução 1 (mais simples e focada) para unificar a detecção de auth mode, garantindo que o log reflita a configuração real.

---

## Anexo: Fluxo Completo de Environment Variables

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROFILE SYSTEM                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ClaudeProfileManager.getActiveProfileEnv()                           │   │
│  │ - Lê: profile.proxyEnabled, proxyBaseUrl, proxyApiKey               │   │
│  │ - Detecta: URL contém 'azure' ou 'foundry'                          │   │
│  │ - Seta: CLAUDE_CODE_USE_FOUNDRY=1, ANTHROPIC_BASE_URL, etc.         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                           ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ rate-limit-detector.ts: getProfileEnv()                              │   │
│  │ - Mesma lógica de detecção                                          │   │
│  │ - Usado para spawn de processos Claude                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
                    Environment Variables passadas
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND PYTHON                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ core/auth.py: is_foundry_mode()                                      │   │
│  │ - Lê: CLAUDE_CODE_USE_FOUNDRY                                       │   │
│  │ - Retorna: True se == '1' ou 'true'                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                           ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ core/auth.py: get_sdk_env_vars()                                     │   │
│  │ - Se Foundry: inclui ANTHROPIC_FOUNDRY_* vars                       │   │
│  │ - Se Standard: inclui ANTHROPIC_BASE_URL                            │   │
│  │ - Filtra vars conflitantes                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                           ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ core/client.py: create_client()                                      │   │
│  │ - Usa get_sdk_env_vars() para configurar Claude Agent SDK           │   │
│  │ - SDK recebe as env vars corretas baseado no modo                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Documento atualizado em: 2025-12-31*
