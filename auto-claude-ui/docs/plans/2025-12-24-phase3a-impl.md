# Phase 3A Implementation Plan: FastMCP Wizard + Process Management

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build FastMCP server generation wizard with uv integration and local process management for stdio/FastMCP servers.

**Architecture:** Hybrid template-based wizard (5 steps) → uv-managed FastMCP server → ProcessManager backend for lifecycle management → Real-time log streaming via IPC.

**Tech Stack:** React 19, TypeScript, Electron IPC, Node.js child_process, uv (Rust-based Python package manager), FastMCP, Vitest

---

## Implementation Strategy

This plan implements **Phase 3A only** - FastMCP Wizard + Process Management (Two-Tier, Tier 1).

**Phase 3B (Server CRUD) and Phase 3C (Polish) will be separate plans.**

**Task Breakdown:**
- Tasks 1-10: Foundation (types, templates, utilities)
- Tasks 11-30: FastMCP Wizard UI (5 steps, TDD)
- Tasks 31-40: Backend uv integration
- Tasks 41-55: Process Management (backend + UI)
- Tasks 56-65: Integration & Testing

**Testing Philosophy:**
- Write failing test FIRST (Red)
- Implement minimal code to pass (Green)
- Refactor if needed
- Commit after each task completion

---

## Task 1: Extend Type Definitions for FastMCP

**Files:**
- Modify: `src/shared/types/mcp.ts:115-145`

**Step 1: Write failing tests**

Create: `src/shared/types/__tests__/mcp-types.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import type {
  FastMCPTemplate,
  FastMCPTool,
  FastMCPServerConfig,
  ProcessState,
  ProcessStatus
} from '../mcp';

describe('FastMCP Type Definitions', () => {
  it('should define FastMCPTemplate with all required fields', () => {
    const template: FastMCPTemplate = {
      id: 'api-wrapper',
      name: 'API Wrapper',
      description: 'HTTP client with authentication',
      icon: 'Globe',
      tools: [],
      dependencies: ['httpx>=0.25.0', 'pydantic>=2.0.0']
    };

    expect(template.id).toBe('api-wrapper');
    expect(template.tools).toEqual([]);
  });

  it('should define FastMCPTool with parameters', () => {
    const tool: FastMCPTool = {
      name: 'read_file',
      description: 'Read file contents',
      parameters: [
        { name: 'path', type: 'string', required: true },
        { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
      ]
    };

    expect(tool.parameters).toHaveLength(2);
    expect(tool.parameters[0].required).toBe(true);
  });

  it('should define ProcessState for running servers', () => {
    const state: ProcessState = {
      serverId: 'test-123',
      pid: 12345,
      startTime: new Date(),
      logBuffer: ['Starting...', 'Ready'],
      restartCount: 0,
      autoRestart: false,
      status: 'running'
    };

    expect(state.pid).toBe(12345);
    expect(state.logBuffer).toHaveLength(2);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/shared/types/__tests__/mcp-types.test.ts`
Expected: FAIL - Types not defined

**Step 3: Implement type definitions**

Modify: `src/shared/types/mcp.ts` (add to end of file)

```typescript
// ===== FastMCP Types (Phase 3A) =====

export interface FastMCPTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;  // Lucide icon name
  tools: FastMCPTool[];
  dependencies: string[];  // Package specs like "httpx>=0.25.0"
}

export interface FastMCPTool {
  name: string;
  description: string;
  parameters: FastMCPToolParameter[];
}

export interface FastMCPToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  required: boolean;
  default?: any;
  description?: string;
}

export interface FastMCPServerConfig {
  // Wizard inputs
  templateId: string;
  serverName: string;
  description: string;
  pythonVersion: '3.10' | '3.11' | '3.12' | '3.13';
  workingDir: string;
  tools: FastMCPTool[];
  dependencies: string[];
}

// ===== Process Management Types (Phase 3A) =====

export type ProcessStatusType = 'stopped' | 'starting' | 'running' | 'stopping' | 'crashed';

export interface ProcessState {
  serverId: string;
  pid: number;
  startTime: Date;
  logBuffer: string[];  // Last 1000 lines
  restartCount: number;
  autoRestart: boolean;
  status: ProcessStatusType;
  exitCode?: number;
  signal?: string;
}

export interface ProcessStatus {
  serverId: string;
  status: ProcessStatusType;
  pid?: number;
  uptime?: number;  // milliseconds
  memory?: number;  // bytes
  restartCount: number;
  lastStarted?: Date;
  exitCode?: number;
}

export interface LogEntry {
  serverId: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
}

// Extend CustomServerConfig for FastMCP
export interface CustomServerConfig {
  // ... existing fields ...

  // FastMCP specific (Updated for Phase 3A with uv)
  isFastMCP?: boolean;
  generatedFrom?: 'wizard' | 'manual';
  template?: string;
  pythonVersion?: '3.10' | '3.11' | '3.12' | '3.13';
  sourceFiles?: {
    pyprojectToml: string;  // Changed from requirementsTxt
    serverPy: string;
    readmeMd: string;
    pythonVersion?: string;  // .python-version file path
  };
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/shared/types/__tests__/mcp-types.test.ts`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/shared/types/mcp.ts src/shared/types/__tests__/mcp-types.test.ts
git commit -m "feat(phase3a): add FastMCP and ProcessManagement type definitions

- FastMCPTemplate for wizard templates
- FastMCPTool with typed parameters
- ProcessState for tracking running servers
- ProcessStatus for UI display
- LogEntry for structured logging
- Updated CustomServerConfig with pyproject.toml (uv)"
```

---

## Task 2: Create FastMCP Template Definitions

**Files:**
- Create: `src/renderer/lib/fastmcp-templates.ts`
- Test: `src/renderer/lib/__tests__/fastmcp-templates.test.ts`

**Step 1: Write failing test**

```typescript
import { describe, it, expect } from 'vitest';
import { FASTMCP_TEMPLATES, getTemplateById } from '../fastmcp-templates';

describe('FastMCP Templates', () => {
  it('should define 4 templates', () => {
    expect(FASTMCP_TEMPLATES).toHaveLength(4);
  });

  it('should include File System template', () => {
    const template = getTemplateById('file-system');
    expect(template).toBeDefined();
    expect(template?.name).toBe('File System Tools');
    expect(template?.tools.length).toBeGreaterThan(0);
  });

  it('should include API Wrapper template', () => {
    const template = getTemplateById('api-wrapper');
    expect(template).toBeDefined();
    expect(template?.dependencies).toContain('httpx>=0.25.0');
  });

  it('should include Database Connector template', () => {
    const template = getTemplateById('database');
    expect(template).toBeDefined();
    expect(template?.dependencies).toContain('sqlalchemy>=2.0.0');
  });

  it('should include Blank template with minimal deps', () => {
    const template = getTemplateById('blank');
    expect(template).toBeDefined();
    expect(template?.tools).toHaveLength(0);
    expect(template?.dependencies).toEqual(['fastmcp>=0.1.0']);
  });

  it('should return undefined for invalid ID', () => {
    const template = getTemplateById('invalid-id');
    expect(template).toBeUndefined();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/renderer/lib/__tests__/fastmcp-templates.test.ts`
Expected: FAIL - Module not found

**Step 3: Implement template definitions**

Create: `src/renderer/lib/fastmcp-templates.ts`

```typescript
import type { FastMCPTemplate } from '../../shared/types/mcp';

export const FASTMCP_TEMPLATES: FastMCPTemplate[] = [
  {
    id: 'file-system',
    name: 'File System Tools',
    description: 'Read/write files, list directories, search content',
    icon: 'FolderOpen',
    tools: [
      {
        name: 'read_file',
        description: 'Read contents of a file',
        parameters: [
          { name: 'path', type: 'string', required: true, description: 'File path to read' },
          { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
        ]
      },
      {
        name: 'write_file',
        description: 'Write content to a file',
        parameters: [
          { name: 'path', type: 'string', required: true },
          { name: 'content', type: 'string', required: true },
          { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
        ]
      },
      {
        name: 'list_directory',
        description: 'List files in a directory',
        parameters: [
          { name: 'path', type: 'string', required: true },
          { name: 'recursive', type: 'boolean', required: false, default: false }
        ]
      },
      {
        name: 'search_files',
        description: 'Search for files matching pattern',
        parameters: [
          { name: 'directory', type: 'string', required: true },
          { name: 'pattern', type: 'string', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0']
  },

  {
    id: 'api-wrapper',
    name: 'API Wrapper',
    description: 'HTTP client with authentication and rate limiting',
    icon: 'Globe',
    tools: [
      {
        name: 'get_request',
        description: 'Make HTTP GET request',
        parameters: [
          { name: 'url', type: 'string', required: true },
          { name: 'headers', type: 'object', required: false }
        ]
      },
      {
        name: 'post_request',
        description: 'Make HTTP POST request',
        parameters: [
          { name: 'url', type: 'string', required: true },
          { name: 'body', type: 'object', required: true },
          { name: 'headers', type: 'object', required: false }
        ]
      },
      {
        name: 'put_request',
        description: 'Make HTTP PUT request',
        parameters: [
          { name: 'url', type: 'string', required: true },
          { name: 'body', type: 'object', required: true }
        ]
      },
      {
        name: 'delete_request',
        description: 'Make HTTP DELETE request',
        parameters: [
          { name: 'url', type: 'string', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0', 'httpx>=0.25.0', 'pydantic>=2.0.0']
  },

  {
    id: 'database',
    name: 'Database Connector',
    description: 'SQL/NoSQL query tools with connection pooling',
    icon: 'Database',
    tools: [
      {
        name: 'execute_query',
        description: 'Execute SQL query',
        parameters: [
          { name: 'query', type: 'string', required: true },
          { name: 'params', type: 'object', required: false }
        ]
      },
      {
        name: 'fetch_data',
        description: 'Fetch data from table',
        parameters: [
          { name: 'table', type: 'string', required: true },
          { name: 'where', type: 'object', required: false }
        ]
      },
      {
        name: 'insert_data',
        description: 'Insert data into table',
        parameters: [
          { name: 'table', type: 'string', required: true },
          { name: 'data', type: 'object', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0', 'sqlalchemy>=2.0.0', 'asyncpg>=0.29.0']
  },

  {
    id: 'blank',
    name: 'Blank Template',
    description: 'Start from scratch with basic FastMCP structure',
    icon: 'FileCode',
    tools: [],
    dependencies: ['fastmcp>=0.1.0']
  }
];

export function getTemplateById(id: string): FastMCPTemplate | undefined {
  return FASTMCP_TEMPLATES.find(t => t.id === id);
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/renderer/lib/__tests__/fastmcp-templates.test.ts`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/renderer/lib/fastmcp-templates.ts src/renderer/lib/__tests__/fastmcp-templates.test.ts
git commit -m "feat(phase3a): define 4 FastMCP wizard templates

- File System: read/write/list/search tools
- API Wrapper: HTTP request tools with httpx
- Database: SQL query tools with sqlalchemy
- Blank: empty template for custom servers

Each template includes tools and dependencies"
```

---

## Task 3: Create Code Generation Utilities

**Files:**
- Create: `src/main/fastmcp-generator.ts`
- Test: `src/main/__tests__/fastmcp-generator.test.ts`

**Step 1: Write failing test**

```typescript
import { describe, it, expect } from 'vitest';
import { generateServerPy, generatePyprojectToml, generateReadmeMd } from '../fastmcp-generator';
import type { FastMCPServerConfig } from '../../shared/types/mcp';

describe('FastMCP Code Generator', () => {
  const config: FastMCPServerConfig = {
    templateId: 'file-system',
    serverName: 'test-server',
    description: 'Test server',
    pythonVersion: '3.12',
    workingDir: '/tmp/test',
    tools: [
      {
        name: 'read_file',
        description: 'Read a file',
        parameters: [
          { name: 'path', type: 'string', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0']
  };

  it('should generate server.py with FastMCP imports', () => {
    const code = generateServerPy(config);
    expect(code).toContain('from fastmcp import FastMCP');
    expect(code).toContain('mcp = FastMCP("test-server")');
  });

  it('should generate tools with decorators', () => {
    const code = generateServerPy(config);
    expect(code).toContain('@mcp.tool()');
    expect(code).toContain('def read_file(path: str):');
    expect(code).toContain('"""Read a file"""');
  });

  it('should generate main block', () => {
    const code = generateServerPy(config);
    expect(code).toContain('if __name__ == "__main__":');
    expect(code).toContain('mcp.run()');
  });

  it('should generate pyproject.toml with uv config', () => {
    const toml = generatePyprojectToml(config);
    expect(toml).toContain('[project]');
    expect(toml).toContain('name = "test-server"');
    expect(toml).toContain('dependencies = [');
    expect(toml).toContain('"fastmcp>=0.1.0"');
  });

  it('should generate README with usage instructions', () => {
    const readme = generateReadmeMd(config);
    expect(readme).toContain('# test-server');
    expect(readme).toContain('Test server');
    expect(readme).toContain('uv run server.py');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/main/__tests__/fastmcp-generator.test.ts`
Expected: FAIL - Functions not defined

**Step 3: Implement code generation**

Create: `src/main/fastmcp-generator.ts`

```typescript
import type { FastMCPServerConfig, FastMCPTool } from '../shared/types/mcp';

export function generateServerPy(config: FastMCPServerConfig): string {
  const tools = config.tools.map(tool => generateToolFunction(tool)).join('\n\n');

  return `from fastmcp import FastMCP

mcp = FastMCP("${config.serverName}")

${tools}

if __name__ == "__main__":
    mcp.run()
`;
}

function generateToolFunction(tool: FastMCPTool): string {
  const params = tool.parameters.map(p => {
    const typeMap = {
      'string': 'str',
      'number': 'int',
      'boolean': 'bool',
      'object': 'dict',
      'array': 'list'
    };
    const pythonType = typeMap[p.type] || 'str';
    const defaultValue = p.default !== undefined ? ` = ${JSON.stringify(p.default)}` : '';
    return `${p.name}: ${pythonType}${defaultValue}`;
  }).join(', ');

  return `@mcp.tool()
def ${tool.name}(${params}):
    """${tool.description}"""
    # TODO: Implement ${tool.name}
    pass`;
}

export function generatePyprojectToml(config: FastMCPServerConfig): string {
  const deps = config.dependencies.map(d => `    "${d}"`).join(',\n');

  return `[project]
name = "${config.serverName}"
version = "0.1.0"
description = "${config.description}"
dependencies = [
${deps}
]

[tool.uv]
dev-dependencies = []
`;
}

export function generateReadmeMd(config: FastMCPServerConfig): string {
  return `# ${config.serverName}

${config.description}

Generated with Auto-Claude MCP Manager

## Usage

\`\`\`bash
uv run server.py
\`\`\`

## Tools

${config.tools.map(t => `- **${t.name}**: ${t.description}`).join('\n')}

## Dependencies

${config.dependencies.map(d => `- ${d}`).join('\n')}
`;
}

export function generatePythonVersion(version: string): string {
  return version;  // Just the version number, e.g., "3.12"
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/main/__tests__/fastmcp-generator.test.ts`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/main/fastmcp-generator.ts src/main/__tests__/fastmcp-generator.test.ts
git commit -m "feat(phase3a): add FastMCP code generation utilities

- generateServerPy: creates server.py with tools
- generatePyprojectToml: creates uv-compatible config
- generateReadmeMd: creates documentation
- Type-safe parameter generation for Python"
```

---

## Task 4: Wizard Step 1 - Template Selection Component

**Files:**
- Create: `src/renderer/components/mcp/wizard/TemplateSelector.tsx`
- Test: `src/renderer/components/mcp/wizard/__tests__/TemplateSelector.test.tsx`

**Step 1: Write failing test**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateSelector } from '../TemplateSelector';

describe('TemplateSelector', () => {
  it('should render 4 template cards', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    expect(screen.getByText('File System Tools')).toBeInTheDocument();
    expect(screen.getByText('API Wrapper')).toBeInTheDocument();
    expect(screen.getByText('Database Connector')).toBeInTheDocument();
    expect(screen.getByText('Blank Template')).toBeInTheDocument();
  });

  it('should show template descriptions', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    expect(screen.getByText(/Read\/write files/)).toBeInTheDocument();
    expect(screen.getByText(/HTTP client/)).toBeInTheDocument();
  });

  it('should call onSelect when clicking template', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    const fileSystemCard = screen.getByText('File System Tools').closest('button');
    fireEvent.click(fileSystemCard!);

    expect(onSelect).toHaveBeenCalledWith('file-system');
  });

  it('should highlight selected template', () => {
    const onSelect = vi.fn();
    const { rerender } = render(<TemplateSelector onSelect={onSelect} selectedId={undefined} />);

    const card = screen.getByText('File System Tools').closest('button');
    expect(card).not.toHaveClass('border-primary');

    rerender(<TemplateSelector onSelect={onSelect} selectedId="file-system" />);
    expect(card).toHaveClass('border-primary');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/renderer/components/mcp/wizard/__tests__/TemplateSelector.test.tsx`
Expected: FAIL - Component not found

**Step 3: Implement TemplateSelector component**

Create: `src/renderer/components/mcp/wizard/TemplateSelector.tsx`

```typescript
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { FolderOpen, Globe, Database, FileCode } from 'lucide-react';
import { FASTMCP_TEMPLATES } from '../../../lib/fastmcp-templates';
import { cn } from '../../../lib/utils';

interface TemplateSelectorProps {
  onSelect: (templateId: string) => void;
  selectedId?: string;
}

const ICON_MAP = {
  'FolderOpen': FolderOpen,
  'Globe': Globe,
  'Database': Database,
  'FileCode': FileCode
};

export function TemplateSelector({ onSelect, selectedId }: TemplateSelectorProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Choose a Template</h3>
        <p className="text-sm text-muted-foreground">
          Select a starting point for your FastMCP server
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {FASTMCP_TEMPLATES.map((template) => {
          const IconComponent = ICON_MAP[template.icon as keyof typeof ICON_MAP];
          const isSelected = selectedId === template.id;

          return (
            <button
              key={template.id}
              onClick={() => onSelect(template.id)}
              className="text-left"
            >
              <Card className={cn(
                'cursor-pointer transition-colors hover:border-primary/50',
                isSelected && 'border-primary border-2'
              )}>
                <CardHeader>
                  <div className="flex items-start gap-3">
                    {IconComponent && (
                      <div className="p-2 rounded-lg bg-primary/10">
                        <IconComponent className="h-5 w-5 text-primary" />
                      </div>
                    )}
                    <div className="flex-1">
                      <CardTitle className="text-base">{template.name}</CardTitle>
                      <CardDescription className="mt-1">
                        {template.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground">
                    {template.tools.length > 0 ? (
                      <span>{template.tools.length} tools included</span>
                    ) : (
                      <span>Empty template</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/renderer/components/mcp/wizard/__tests__/TemplateSelector.test.tsx`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/renderer/components/mcp/wizard/TemplateSelector.tsx \
        src/renderer/components/mcp/wizard/__tests__/TemplateSelector.test.tsx
git commit -m "feat(phase3a): add FastMCP template selector (Step 1)

- Grid layout with 4 template cards
- Icon, name, description for each
- Click to select, visual highlight
- Shows tool count preview"
```

---

## Task 5: Wizard Step 2 - Server Configuration Form

**Files:**
- Create: `src/renderer/components/mcp/wizard/ServerConfigForm.tsx`
- Test: `src/renderer/components/mcp/wizard/__tests__/ServerConfigForm.test.tsx`

**Step 1: Write failing test**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ServerConfigForm } from '../ServerConfigForm';

describe('ServerConfigForm', () => {
  const defaultProps = {
    onNext: vi.fn(),
    onBack: vi.fn(),
    initialData: {
      serverName: '',
      description: '',
      pythonVersion: '3.12' as const,
      workingDir: ''
    }
  };

  it('should render all form fields', () => {
    render(<ServerConfigForm {...defaultProps} />);

    expect(screen.getByLabelText(/Server Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Python Version/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Working Directory/i)).toBeInTheDocument();
  });

  it('should show validation error for empty name', async () => {
    render(<ServerConfigForm {...defaultProps} />);

    const nextButton = screen.getByRole('button', { name: /Next/i });
    fireEvent.click(nextButton);

    expect(await screen.findByText(/Server name is required/i)).toBeInTheDocument();
    expect(defaultProps.onNext).not.toHaveBeenCalled();
  });

  it('should call onNext with valid data', () => {
    render(<ServerConfigForm {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Server Name/i), {
      target: { value: 'my-api-server' }
    });

    fireEvent.change(screen.getByLabelText(/Description/i), {
      target: { value: 'API wrapper' }
    });

    const nextButton = screen.getByRole('button', { name: /Next/i });
    fireEvent.click(nextButton);

    expect(defaultProps.onNext).toHaveBeenCalledWith({
      serverName: 'my-api-server',
      description: 'API wrapper',
      pythonVersion: '3.12',
      workingDir: expect.stringContaining('my-api-server')
    });
  });

  it('should provide default working directory', () => {
    render(<ServerConfigForm {...defaultProps} />);

    const workingDirInput = screen.getByLabelText(/Working Directory/i);
    expect(workingDirInput).toHaveValue(expect.stringContaining('.auto-claude/fastmcp-servers'));
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/renderer/components/mcp/wizard/__tests__/ServerConfigForm.test.tsx`
Expected: FAIL - Component not found

**Step 3: Implement ServerConfigForm component**

Create: `src/renderer/components/mcp/wizard/ServerConfigForm.tsx`

```typescript
import { useState, useEffect } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import { FolderOpen } from 'lucide-react';
import { homedir } from 'os';
import { join } from 'path';

interface ServerConfigData {
  serverName: string;
  description: string;
  pythonVersion: '3.10' | '3.11' | '3.12' | '3.13';
  workingDir: string;
}

interface ServerConfigFormProps {
  onNext: (data: ServerConfigData) => void;
  onBack: () => void;
  initialData: ServerConfigData;
}

export function ServerConfigForm({ onNext, onBack, initialData }: ServerConfigFormProps) {
  const [serverName, setServerName] = useState(initialData.serverName);
  const [description, setDescription] = useState(initialData.description);
  const [pythonVersion, setPythonVersion] = useState<ServerConfigData['pythonVersion']>(initialData.pythonVersion);
  const [workingDir, setWorkingDir] = useState(initialData.workingDir);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Auto-generate working directory when server name changes
  useEffect(() => {
    if (serverName && !initialData.workingDir) {
      const defaultDir = join(homedir(), '.auto-claude', 'fastmcp-servers', serverName);
      setWorkingDir(defaultDir);
    }
  }, [serverName, initialData.workingDir]);

  const handleNext = () => {
    const newErrors: Record<string, string> = {};

    if (!serverName.trim()) {
      newErrors.serverName = 'Server name is required';
    }

    if (!workingDir.trim()) {
      newErrors.workingDir = 'Working directory is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    onNext({
      serverName: serverName.trim(),
      description: description.trim(),
      pythonVersion,
      workingDir: workingDir.trim()
    });
  };

  const handleBrowse = async () => {
    const result = await window.electron.showOpenDialog({
      properties: ['openDirectory', 'createDirectory']
    });

    if (!result.canceled && result.filePaths[0]) {
      setWorkingDir(result.filePaths[0]);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Server Configuration</h3>
        <p className="text-sm text-muted-foreground">
          Configure your FastMCP server settings
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="serverName">Server Name *</Label>
          <Input
            id="serverName"
            value={serverName}
            onChange={(e) => {
              setServerName(e.target.value);
              setErrors(prev => ({ ...prev, serverName: '' }));
            }}
            placeholder="my-api-server"
            className={errors.serverName ? 'border-destructive' : ''}
          />
          {errors.serverName && (
            <p className="text-sm text-destructive">{errors.serverName}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of what this server does"
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="pythonVersion">Python Version *</Label>
          <Select value={pythonVersion} onValueChange={(v) => setPythonVersion(v as any)}>
            <SelectTrigger id="pythonVersion">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3.10">Python 3.10</SelectItem>
              <SelectItem value="3.11">Python 3.11</SelectItem>
              <SelectItem value="3.12">Python 3.12</SelectItem>
              <SelectItem value="3.13">Python 3.13</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            uv will install this version automatically if needed
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="workingDir">Working Directory *</Label>
          <div className="flex gap-2">
            <Input
              id="workingDir"
              value={workingDir}
              onChange={(e) => {
                setWorkingDir(e.target.value);
                setErrors(prev => ({ ...prev, workingDir: '' }));
              }}
              className={errors.workingDir ? 'border-destructive' : ''}
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleBrowse}
            >
              <FolderOpen className="h-4 w-4" />
            </Button>
          </div>
          {errors.workingDir && (
            <p className="text-sm text-destructive">{errors.workingDir}</p>
          )}
        </div>
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={handleNext}>
          Next
        </Button>
      </div>
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/renderer/components/mcp/wizard/__tests__/ServerConfigForm.test.tsx`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/renderer/components/mcp/wizard/ServerConfigForm.tsx \
        src/renderer/components/mcp/wizard/__tests__/ServerConfigForm.test.tsx
git commit -m "feat(phase3a): add server configuration form (Step 2)

- Server name validation (required)
- Description textarea
- Python version selector (3.10-3.13)
- Working directory with file browser
- Auto-generates default directory from server name"
```

---

**[Continue with Tasks 6-65 following same pattern...]**

Due to length constraints, I'll provide the structure for remaining tasks:

## Tasks 6-10: Wizard Steps 3-5
- Task 6: Tool Customizer component (add/edit/remove tools)
- Task 7: Tool Editor Dialog (parameters, types, defaults)
- Task 8: Dependency Manager (add/remove packages with versions)
- Task 9: Review & Preview component (show generated files)
- Task 10: FastMCP Wizard orchestrator component

## Tasks 11-20: Backend uv Integration
- Task 11: uv command utilities (init, add, sync, run)
- Task 12: File system utilities (create dirs, write files)
- Task 13: Server generation IPC handler
- Task 14: Error handling for uv operations
- Task 15: Progress reporting during generation
- Task 16-20: Integration tests for generation flow

## Tasks 21-35: ProcessManager Backend
- Task 21: ProcessManager class structure
- Task 22: startServer method (spawn with uv)
- Task 23: stopServer method (SIGTERM → SIGKILL)
- Task 24: restartServer method
- Task 25: Log buffer management (1000 lines)
- Task 26: Process monitoring (PID, memory, uptime)
- Task 27: Auto-restart on crash
- Task 28: Health check ping
- Task 29: IPC event emitters
- Task 30-35: ProcessManager unit tests

## Tasks 36-50: Process Management UI
- Task 36: ProcessControls component (Start/Stop/Restart buttons)
- Task 37: ProcessStatus display (PID, uptime, memory)
- Task 38: LogViewer dialog component
- Task 39: Log filtering and search
- Task 40: Auto-scroll toggle
- Task 41: Copy/download logs
- Task 42: Integrate controls into MCPServerCard
- Task 43: Real-time log streaming (IPC events)
- Task 44: Process state management (React state)
- Task 45-50: UI component tests

## Tasks 51-60: IPC Integration
- Task 51: process:start handler
- Task 52: process:stop handler
- Task 53: process:restart handler
- Task 54: process:logs handler
- Task 55: Real-time event forwarding (process:log)
- Task 56: Process status events (process:status)
- Task 57: Crash event handling (process:crash)
- Task 58: Error handling for all handlers
- Task 59-60: IPC handler tests

## Tasks 61-65: Integration & E2E Tests
- Task 61: End-to-end FastMCP generation test
- Task 62: Process lifecycle integration test
- Task 63: Log streaming integration test
- Task 64: Error recovery test
- Task 65: Performance test (10+ concurrent servers)

---

## Testing Commands Reference

**Run all tests:**
```bash
npm test
```

**Run specific test file:**
```bash
npm test -- src/renderer/components/mcp/wizard/__tests__/TemplateSelector.test.tsx
```

**Run with coverage:**
```bash
npm test -- --coverage
```

**Watch mode during development:**
```bash
npm test -- --watch
```

---

## Dependencies to Install

No new npm packages needed - all functionality uses existing dependencies:
- React 19 (already installed)
- Vitest (already installed)
- Lucide icons (already installed)
- Electron IPC (already installed)

**System dependency (bundled or user-installed):**
- `uv` - Rust-based Python package manager (to be bundled with app)

---

## Commit Message Convention

Use conventional commits format:

```
feat(phase3a): <description>
fix(phase3a): <description>
test(phase3a): <description>
refactor(phase3a): <description>
```

---

## Next Steps After Phase 3A

Once all 65 tasks are complete:

1. **Merge to main** via @superpowers:finishing-a-development-branch
2. **Start Phase 3B** (Server CRUD: Edit/Delete/Duplicate)
3. **Start Phase 3C** (Polish, E2E tests, documentation)

---

**Status:** Ready for execution via superpowers:subagent-driven-development or superpowers:executing-plans
