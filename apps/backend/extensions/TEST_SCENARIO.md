# Cenário de Teste - Extensions Layer via Frontend

## Pré-requisitos

1. **Langfuse rodando** (opcional, mas recomendado):
   ```bash
   cd infra/langfuse && ./setup.sh start
   # Dashboard: http://localhost:3001
   ```

2. **wrapt instalado**:
   ```bash
   cd apps/backend && pip install wrapt
   ```

3. **EXTENSIONS_ENABLED=true** no `.env` (já configurado)

## Cenário de Teste

### Passo 1: Iniciar o Frontend

```bash
npm run dev
```

### Passo 2: Criar uma Task Simples

1. Abra o app Electron
2. Selecione um projeto (ou crie um novo)
3. Clique em **"Create New Task"**
4. Digite uma descrição simples:
   ```
   Create a hello.py file that prints "Hello from Extensions Test!"
   ```
5. Clique em **"Start"**

### Passo 3: Verificar os Logs

Nos logs do terminal onde o frontend está rodando, você deve ver:

```
[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Extensions] 🔌 Auto-Claude Extensions Layer Activating...
[Extensions] ✅ Patches registered successfully
[Extensions] ✅ Langfuse analytics initialized
[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Passo 4: Verificar no Langfuse (se configurado)

1. Abra http://localhost:3001
2. Vá para **Traces**
3. Você deve ver um novo trace para a sessão do agente

## O Que Está Sendo Testado

| Componente | Verificação |
|------------|-------------|
| `sitecustomize.py` | Carrega automaticamente com PYTHONPATH |
| `extensions/patches` | Registra patches via wrapt |
| `extensions/analytics` | Inicializa Langfuse |
| Frontend → Backend | Passa `EXTENSIONS_ENABLED` via env |

## Troubleshooting

### Extensions não aparecem nos logs

1. Verifique se `EXTENSIONS_ENABLED=true` está no `.env`:
   ```bash
   grep EXTENSIONS_ENABLED apps/backend/.env
   ```

2. Verifique se wrapt está instalado:
   ```bash
   cd apps/backend && python -c "import wrapt; print('OK')"
   ```

3. Teste manualmente:
   ```bash
   cd apps/backend
   PYTHONPATH=. EXTENSIONS_ENABLED=true python -c "print('test')"
   ```

### Langfuse não inicializa

1. Verifique se Langfuse está rodando:
   ```bash
   curl -s http://localhost:3001/api/health | jq
   ```

2. Verifique as keys no `.env`:
   ```bash
   grep LANGFUSE apps/backend/.env
   ```

## Fluxo Interno

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Frontend (Electron)                                         │
│                                                                 │
│     AgentManager.startSpecCreation()                           │
│         ↓                                                       │
│     getCombinedEnv(projectPath)                                │
│         ↓                                                       │
│     Lê apps/backend/.env (inclui EXTENSIONS_ENABLED=true)      │
│         ↓                                                       │
│     spawn("python", ["spec_runner.py", ...], { env: {...} })   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Python Startup                                              │
│                                                                 │
│     PYTHONPATH inclui apps/backend                             │
│         ↓                                                       │
│     Python encontra sitecustomize.py                           │
│         ↓                                                       │
│     sitecustomize.py executa ANTES de qualquer código          │
│         ↓                                                       │
│     Verifica EXTENSIONS_ENABLED=true                           │
│         ↓                                                       │
│     Importa e registra patches via wrapt                       │
│         ↓                                                       │
│     Inicializa Langfuse analytics                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Script Principal (spec_runner.py, run.py, etc.)            │
│                                                                 │
│     Executa normalmente                                        │
│     Quando importa core.client → patch já está registrado      │
│     Todas as chamadas a create_client() são instrumentadas     │
└─────────────────────────────────────────────────────────────────┘
```

## Resultado Esperado

✅ Banner "[Extensions]" aparece nos logs
✅ Patches registrados com sucesso
✅ Langfuse inicializado (se configurado)
✅ Task executa normalmente
✅ Trace aparece no Langfuse dashboard
