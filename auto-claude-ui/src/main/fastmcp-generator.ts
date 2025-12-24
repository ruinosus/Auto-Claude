import type { FastMCPServerConfig, FastMCPTool } from '../shared/types/mcp';

/**
 * Converts JavaScript values to Python syntax
 */
function toPythonValue(value: any): string {
  if (value === null || value === undefined) {
    return 'None';
  }
  if (typeof value === 'boolean') {
    return value ? 'True' : 'False';
  }
  if (typeof value === 'string') {
    // Escape quotes and backslashes
    const escaped = value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    return `"${escaped}"`;
  }
  if (typeof value === 'number') {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(toPythonValue).join(', ')}]`;
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value).map(([k, v]) => `"${k}": ${toPythonValue(v)}`);
    return `{${entries.join(', ')}}`;
  }
  return 'None';
}

/**
 * Validates and sanitizes Python identifiers (function names, parameter names)
 * Throws an error if the identifier is invalid
 */
function sanitizePythonIdentifier(identifier: string, context: string = 'identifier'): string {
  // Python identifier rules: must start with letter or underscore, followed by letters, digits, or underscores
  const validIdentifier = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

  if (!validIdentifier.test(identifier)) {
    throw new Error(`Invalid Python ${context}: "${identifier}". Must start with letter or underscore and contain only letters, digits, and underscores.`);
  }

  // Check for Python reserved keywords
  const pythonKeywords = new Set([
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class',
    'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global',
    'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
    'return', 'try', 'while', 'with', 'yield'
  ]);

  if (pythonKeywords.has(identifier)) {
    throw new Error(`Invalid Python ${context}: "${identifier}" is a reserved keyword.`);
  }

  return identifier;
}

/**
 * Escapes strings for safe use in Python docstrings and string literals
 */
function sanitizePythonString(str: string): string {
  // Escape backslashes first, then double quotes
  // This handles both single quotes in strings and triple quotes in docstrings
  return str.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

export function generateServerPy(config: FastMCPServerConfig): string {
  // Sanitize server name to prevent code injection
  const sanitizedServerName = sanitizePythonString(config.serverName);
  const tools = config.tools.map(tool => generateToolFunction(tool)).join('\n\n');

  return `from fastmcp import FastMCP

mcp = FastMCP("${sanitizedServerName}")

${tools}

if __name__ == "__main__":
    mcp.run()
`;
}

function generateToolFunction(tool: FastMCPTool): string {
  // Validate tool name as a valid Python identifier
  const sanitizedToolName = sanitizePythonIdentifier(tool.name, 'tool name');

  // Escape description to prevent docstring injection
  const sanitizedDescription = sanitizePythonString(tool.description);

  const params = tool.parameters.map(p => {
    // Validate parameter name as a valid Python identifier
    const sanitizedParamName = sanitizePythonIdentifier(p.name, 'parameter name');

    const typeMap = {
      'string': 'str',
      'number': 'int',
      'boolean': 'bool',
      'object': 'dict',
      'array': 'list'
    };
    const pythonType = typeMap[p.type] || 'str';

    // Convert default value to Python syntax (true → True, false → False, null → None)
    const defaultValue = p.default !== undefined ? ` = ${toPythonValue(p.default)}` : '';

    return `${sanitizedParamName}: ${pythonType}${defaultValue}`;
  }).join(', ');

  return `@mcp.tool()
def ${sanitizedToolName}(${params}):
    """${sanitizedDescription}"""
    # TODO: Implement ${sanitizedToolName}
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
