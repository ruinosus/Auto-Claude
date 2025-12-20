# Setup Completo - Auto-Claude

Data: 2025-12-19

## Arquitetura do Projeto

```
Auto-Claude/
├── auto-claude/          # Backend Python (CLI)
│   ├── .venv/            # Virtual environment
│   ├── .env              # Configuracao
│   ├── run.py            # Entry point builds
│   └── spec_runner.py    # Criador de specs
│
├── auto-claude-ui/       # Frontend Electron (Desktop App)
│   ├── dist/             # App compilado
│   │   └── mac-arm64/    # Auto Claude.app
│   └── src/              # Codigo fonte React
│
└── docker-compose.yml    # FalkorDB (Memory Layer)
```

---

## Status dos Componentes

### Infraestrutura

| Componente | Versao | Status |
|------------|--------|--------|
| Colima | 0.9.1 | Rodando |
| Docker CLI | 29.1.2 | OK |
| Docker Compose | 5.0.1 | OK |
| FalkorDB | latest | Rodando (porta 6380) |

### Backend (Python)

| Componente | Versao | Status |
|------------|--------|--------|
| Python | 3.12.12 | OK |
| uv | instalado | OK |
| claude-agent-sdk | 0.1.18 | OK |
| graphiti-core | 0.24.3 | OK |
| Dependencias | 50 pacotes | Instaladas |

### Frontend (Electron)

| Componente | Versao | Status |
|------------|--------|--------|
| Node.js | 22.21.1 | OK |
| pnpm | 10.26.1 | OK |
| Electron | 39.2.7 | OK |
| React | 19.2.3 | OK |
| Dependencias | 881 pacotes | Instaladas |
| Build | 2.5.0 | Compilado |

### CLI

| Componente | Versao | Status |
|------------|--------|--------|
| Claude Code CLI | 2.0.73 | OK |

---

## Como Iniciar

### Opcao 1: Desktop App (Recomendado)

```bash
# Abrir o app
open /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui/dist/mac-arm64/Auto\ Claude.app
```

O app oferece:
- Kanban Board visual para tarefas
- Terminais de agentes integrados
- Progresso em tempo real
- Temas claro/escuro

### Opcao 2: CLI (Terminal)

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude
source .venv/bin/activate

# Listar specs
python run.py --list

# Criar spec interativamente
python spec_runner.py --interactive
```

---

## Comandos do Backend (CLI)

### Ativar Ambiente

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude
source .venv/bin/activate
```

### Gerenciamento de Specs

```bash
# Listar specs existentes
python run.py --list

# Criar spec interativamente
python spec_runner.py --interactive

# Criar spec de uma tarefa
python spec_runner.py --task "Adicionar autenticacao"

# Forcar complexidade
python spec_runner.py --task "Corrigir botao" --complexity simple
```

### Execucao de Builds

```bash
# Executar build
python run.py --spec 001

# Revisar mudancas
python run.py --spec 001 --review

# Mergear para main
python run.py --spec 001 --merge

# Descartar build
python run.py --spec 001 --discard
```

### QA e Validacao

```bash
# Rodar QA manualmente
python run.py --spec 001 --qa

# Status do QA
python run.py --spec 001 --qa-status

# Validar spec
python validate_spec.py --spec-dir specs/001-feature --checkpoint all
```

---

## Comandos do Frontend (Electron)

### Desenvolvimento

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui

# Modo dev com hot reload
pnpm run dev

# Rodar testes
pnpm run test

# Lint
pnpm run lint
```

### Build

```bash
# Build para macOS
pnpm run package:mac

# Build para Windows
pnpm run package:win

# Build para Linux
pnpm run package:linux
```

### Executar App Compilado

```bash
# macOS (Apple Silicon)
open dist/mac-arm64/Auto\ Claude.app

# macOS (Intel)
open dist/mac/Auto\ Claude.app
```

---

## Gerenciamento de Servicos

### Colima (Docker Runtime)

```bash
# Status
colima status

# Iniciar
colima start

# Parar (libera ~2GB RAM)
colima stop

# Reiniciar
colima restart

# Com mais recursos
colima start --cpu 4 --memory 8
```

### FalkorDB (Memory Layer)

```bash
# Iniciar
docker compose -f /Users/jefferson.barnabe/projects/misc/Auto-Claude/docker-compose.yml up -d falkordb

# Parar
docker compose -f /Users/jefferson.barnabe/projects/misc/Auto-Claude/docker-compose.yml stop falkordb

# Logs
docker logs auto-claude-falkordb

# Status
docker ps --filter "name=falkordb"

# Testar conexao
docker exec auto-claude-falkordb redis-cli ping
```

---

## Configuracao

### Backend (.env)

Arquivo: `auto-claude/.env`

```bash
# Autenticacao (obrigatorio)
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...

# Memory Layer (opcional)
# GRAPHITI_ENABLED=true
# GRAPHITI_TELEMETRY_ENABLED=false

# Provider para Graphiti (escolha um):
# GRAPHITI_LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# Debug (opcional)
# DEBUG=true
```

### Frontend

O frontend le o token do backend automaticamente.
Nao precisa de configuracao adicional.

---

## Estrutura de Arquivos

```
/Users/jefferson.barnabe/projects/misc/Auto-Claude/
├── auto-claude/
│   ├── .venv/                    # Python venv
│   ├── .env                      # Config (token)
│   ├── run.py                    # Entry point
│   ├── spec_runner.py            # Cria specs
│   ├── prompts/                  # Prompts dos agentes
│   ├── core/                     # Core logic
│   └── requirements.txt          # 50 dependencias
│
├── auto-claude-ui/
│   ├── dist/
│   │   └── mac-arm64/
│   │       └── Auto Claude.app   # App compilado
│   ├── src/
│   │   ├── main/                 # Electron main
│   │   ├── preload/              # Preload scripts
│   │   └── renderer/             # React frontend
│   ├── node_modules/             # 881 pacotes
│   └── package.json
│
├── guides/
│   ├── SETUP-MAC-SEM-DOCKER-DESKTOP.md
│   ├── SETUP-COMPLETO.md         # Este arquivo
│   ├── CLI-USAGE.md
│   └── DOCKER-SETUP.md
│
└── docker-compose.yml            # FalkorDB
```

---

## Recursos do Sistema

| Componente | RAM | CPU | Disco |
|------------|-----|-----|-------|
| Colima VM | ~1-2 GB | 2 cores | ~5 GB |
| FalkorDB | ~200-500 MB | minimo | ~100 MB |
| Electron App | ~200-500 MB | minimo | ~250 MB |
| Python venv | ~100 MB | - | ~500 MB |

**Total:** ~2-4 GB RAM quando tudo rodando.

### Liberar Recursos

```bash
# Para tudo de uma vez
colima stop

# Ou individualmente
docker compose stop  # Para FalkorDB
# Fechar o app Electron
```

---

## Troubleshooting

### "colima is not running"

```bash
colima start
```

### Modulos Python nao encontrados

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude
source .venv/bin/activate
which python  # Deve mostrar .../auto-claude/.venv/bin/python
```

### App Electron nao abre

```bash
# Rebuild
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui
pnpm run package:mac
```

### FalkorDB nao conecta

```bash
docker ps -a | grep falkordb
docker start auto-claude-falkordb
```

### Token expirado

```bash
claude setup-token
# Atualizar em auto-claude/.env
```

---

## Comandos Rapidos

```bash
# ==== INICIAR TUDO ====
colima start
docker compose -f /Users/jefferson.barnabe/projects/misc/Auto-Claude/docker-compose.yml up -d falkordb
open /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui/dist/mac-arm64/Auto\ Claude.app

# ==== PARAR TUDO ====
colima stop  # Para Colima + todos containers

# ==== CLI RAPIDO ====
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude && source .venv/bin/activate
python run.py --list
python spec_runner.py --interactive

# ==== REBUILD FRONTEND ====
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui && pnpm run package:mac
```

---

## Fluxo de Desenvolvimento

### Backend (Python) - Sem build necessario

Alteracoes em Python sao imediatas - nao precisa rebuild.

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude
source .venv/bin/activate

# Edita o codigo...
# E roda direto:
python run.py --list
```

### Frontend (Electron) - Duas opcoes

**Opcao 1: Dev Mode (hot reload)** - Recomendado para desenvolvimento

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui
pnpm run dev
```

- Abre o app em modo dev
- Alteracoes no React recarregam automaticamente
- Bom para desenvolver UI

**Opcao 2: Rebuild completo** - Para testar build final

```bash
cd /Users/jefferson.barnabe/projects/misc/Auto-Claude/auto-claude-ui
pnpm run package:mac
```

- Gera novo `.app` em `dist/mac-arm64/`
- Necessario apenas para testar build final ou distribuir

### Quando fazer o que

| O que alterou | O que fazer |
|---------------|-------------|
| Codigo Python (`auto-claude/`) | Apenas rodar novamente |
| Codigo React/Electron (`auto-claude-ui/src/`) | `pnpm run dev` ou rebuild |
| Dependencias Python (`requirements.txt`) | `uv pip install -r requirements.txt` |
| Dependencias Node (`package.json`) | `pnpm install` |
| Prompts dos agentes (`auto-claude/prompts/`) | Apenas rodar novamente |
| Configuracao (`.env`) | Apenas rodar novamente |

### Estrutura de desenvolvimento

```
auto-claude/                    # Backend - edita e roda
├── core/                       # Logica principal
├── prompts/                    # Prompts dos agentes (editaveis)
├── agents/                     # Codigo dos agentes
├── spec/                       # Criacao de specs
└── qa/                         # QA e validacao

auto-claude-ui/                 # Frontend - precisa dev/rebuild
├── src/
│   ├── main/                   # Electron main process
│   ├── preload/                # Bridge main<->renderer
│   └── renderer/               # React UI
│       ├── src/
│       │   ├── components/     # Componentes React
│       │   ├── pages/          # Paginas (Kanban, Terminals, etc)
│       │   ├── stores/         # Zustand stores
│       │   └── lib/            # Utilitarios
│       └── index.html
└── dist/                       # Build final (gerado)
```

---

## Links

- [Setup Mac sem Docker Desktop](SETUP-MAC-SEM-DOCKER-DESKTOP.md)
- [CLI Usage Guide](CLI-USAGE.md)
- [Docker Setup Guide](DOCKER-SETUP.md)
