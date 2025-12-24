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
