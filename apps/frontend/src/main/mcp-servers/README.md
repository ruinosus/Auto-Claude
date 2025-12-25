# Auto-Claude Tools MCP Server

Este diretório contém **duas implementações** do servidor MCP `auto-claude-tools`, que expõe funcionalidades internas do Auto-Claude via Model Context Protocol.

## 🎯 Objetivo

Permitir que clientes externos (Claude Desktop, VS Code, outros agentes) acessem funcionalidades do Auto-Claude:
- **get_build_progress**: Obter status de builds em tempo real
- **get_context**: Contexto do projeto e codebase
- **search_code**: Buscar padrões no código

## 📁 Arquivos

```
mcp-servers/
├── auto-claude-tools-stdio.ts    # Option A: Subprocess com STDIO transport
├── auto-claude-tools-http.ts     # Option B: In-process com HTTP transport
├── electron-api-bridge.ts        # API bridge para Option A
├── index.ts                      # Inicialização automática
└── README.md                     # Esta documentação
```

## 🔀 Duas Implementações

### **Option A: STDIO Subprocess** 🔄

**Como funciona:**
```
Cliente MCP
    ↓ (stdio)
auto-claude-tools-stdio.ts (subprocess)
    ↓ (HTTP API)
electron-api-bridge.ts (porta 9824)
    ↓ (IPC)
Electron Main Process
```

**Características:**
- ✅ Isolamento de processo (mais seguro)
- ✅ Padrão MCP clássico (stdio)
- ✅ Fácil debug (logs separados)
- ❌ Overhead de processo spawn
- ❌ Requer API bridge (HTTP intermediário)

**Quando usar:**
- Testes e debug
- Ambientes com múltiplos processos
- Quando precisa isolar o servidor MCP do Electron

---

### **Option B: HTTP Localhost** 🚀 **(Padrão)**

**Como funciona:**
```
Cliente MCP
    ↓ (HTTP)
auto-claude-tools-http.ts (in-process)
    ↓ (direto)
Electron Main Process
```

**Características:**
- ✅ **Acesso direto** a dados do Electron (sem bridge!)
- ✅ **Melhor performance** (sem spawn, sem HTTP extra)
- ✅ Spec MCP 2025 (Streamable HTTP)
- ✅ Reutiliza código existente
- ❌ Precisa gerenciar porta (9823)
- ❌ Acoplado ao Electron main process

**Quando usar:**
- **Produção** (recomendado)
- Máxima performance
- Integração profunda com Electron

## ⚙️ Configuração

### Escolher Implementação

Use a variável de ambiente `AUTO_CLAUDE_TOOLS_MODE`:

```bash
# Option A: STDIO subprocess
export AUTO_CLAUDE_TOOLS_MODE=stdio
npm run dev

# Option B: HTTP localhost (PADRÃO)
export AUTO_CLAUDE_TOOLS_MODE=http
npm run dev

# Ou não configure nada (usa HTTP por padrão)
npm run dev
```

### Configurar Portas

**Para Option A (STDIO + API Bridge):**
```bash
export ELECTRON_API_PORT=9824  # Porta do API bridge
```

**Para Option B (HTTP):**
- Porta fixa: `9823` (hardcoded em `auto-claude-tools-http.ts`)
- Para mudar, edite `const PORT = 9823;`

## 🔌 Como Conectar Clientes

### Claude Desktop

Adicione em `~/Library/Application Support/Claude/claude_desktop_config.json`:

**Option A (STDIO):**
```json
{
  "mcpServers": {
    "auto-claude-tools": {
      "command": "npx",
      "args": [
        "tsx",
        "/path/to/auto-claude-fork-clean/apps/frontend/src/main/mcp-servers/auto-claude-tools-stdio.ts"
      ],
      "env": {
        "ELECTRON_API_PORT": "9824"
      }
    }
  }
}
```

**Option B (HTTP):**
```json
{
  "mcpServers": {
    "auto-claude-tools": {
      "url": "http://localhost:9823/mcp"
    }
  }
}
```

### VS Code / Cursor

Em `.cursor/mcp.json` ou settings:

**Option A:**
```json
{
  "mcpServers": {
    "auto-claude-tools": {
      "command": "npx",
      "args": ["tsx", "./apps/frontend/src/main/mcp-servers/auto-claude-tools-stdio.ts"]
    }
  }
}
```

**Option B:**
```json
{
  "mcpServers": {
    "auto-claude-tools": {
      "transport": "http",
      "url": "http://localhost:9823/mcp"
    }
  }
}
```

## 🧪 Testar

### Testar HTTP Server (Option B)

```bash
# 1. Iniciar Auto-Claude
npm run dev

# 2. Health check
curl http://localhost:9823/health

# 3. Testar MCP endpoint
curl -X POST http://localhost:9823/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Testar STDIO Server (Option A)

```bash
# 1. Iniciar API bridge separadamente (em terminal separado)
export AUTO_CLAUDE_TOOLS_MODE=stdio
npm run dev

# 2. Testar API bridge
curl http://localhost:9824/api/health

# 3. Executar servidor STDIO diretamente
npx tsx apps/frontend/src/main/mcp-servers/auto-claude-tools-stdio.ts
# Digite: {"jsonrpc":"2.0","method":"tools/list","id":1}
# (Ctrl+C para sair)
```

## 🛠️ Desenvolvimento

### Adicionar Nova Ferramenta

Edite **ambos** os arquivos:
1. `auto-claude-tools-stdio.ts`
2. `auto-claude-tools-http.ts`

Exemplo:
```typescript
server.registerTool(
  'nova_ferramenta',
  {
    title: 'Nova Ferramenta',
    description: 'Descrição da ferramenta',
    inputSchema: {
      param1: z.string().describe('Parâmetro 1')
    },
    outputSchema: {
      result: z.string()
    }
  },
  async ({ param1 }) => {
    // Implementação
    return {
      content: [{ type: 'text', text: 'resultado' }],
      structuredContent: { result: 'resultado' }
    };
  }
);
```

### Implementar Dados Reais

Atualmente as ferramentas retornam dados **mock**. Para implementar dados reais:

**Option A (STDIO):** Edite `electron-api-bridge.ts`
```typescript
async function getBuildProgress(specId: string): Promise<BuildProgressResponse> {
  // TODO: Chamar IPC handlers reais
  const result = await ipcMain.handle('task:list', ...);
  return result;
}
```

**Option B (HTTP):** Edite `auto-claude-tools-http.ts`
```typescript
// Acesso direto aos managers/handlers
import { taskManager } from '../task-manager';

const data = await taskManager.getProgress(specId);
```

## 📊 Comparação

| Aspecto | STDIO (A) | HTTP (B) |
|---------|-----------|----------|
| **Performance** | ⚠️ Médio (spawn + HTTP bridge) | ✅ Alta (in-process) |
| **Isolamento** | ✅ Alto (subprocess) | ⚠️ Baixo (same process) |
| **Complexidade** | ⚠️ Média (2 processos) | ✅ Baixa (1 processo) |
| **Debug** | ✅ Fácil (logs separados) | ⚠️ Médio (mixed logs) |
| **Padrão MCP** | ✅ Clássico (stdio) | ✅ Moderno (HTTP 2025) |
| **Produção** | ⚠️ Aceitável | ✅ **Recomendado** |

## 🚀 Recomendação

**Use Option B (HTTP) por padrão** - melhor performance e mais simples.

Use Option A (STDIO) apenas para:
- Testes e desenvolvimento
- Debugging de problemas do MCP
- Ambientes que exigem isolamento de processo

## 🔍 Troubleshooting

### "Port 9823 already in use"
```bash
# Encontrar processo usando a porta
lsof -i :9823
kill -9 <PID>
```

### "Failed to connect to Electron API"
```bash
# Verificar se API bridge está rodando (Option A)
curl http://localhost:9824/api/health

# Se não estiver, verificar se AUTO_CLAUDE_TOOLS_MODE=stdio
echo $AUTO_CLAUDE_TOOLS_MODE
```

### "Server not responding"
```bash
# Verificar logs do Electron
# Buscar por "[MCP Servers]" ou "[Auto-Claude Tools]"
```

## 📚 Referências

- [MCP Specification 2025](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [Building MCP Servers](https://medium.com/@yagmur.sahin/building-mcp-servers-architecture-transports-and-the-modern-way-to-connect-mcp-clients-cef042d80384)
