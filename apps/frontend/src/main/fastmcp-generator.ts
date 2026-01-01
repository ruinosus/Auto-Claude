import type { FastMCPServerConfig, FastMCPTool, FastMCPToolParameter, FastMCPResource, FastMCPPrompt } from '../shared/types/mcp';

/**
 * FastMCP Code Generator - Production Ready
 * Following MCP Specification 2025-06-18 and FastMCP best practices
 *
 * Features:
 * - ToolError for error handling
 * - Tool annotations (readOnlyHint, destructiveHint, etc.)
 * - Async/await support
 * - Pydantic validation
 * - Resources and Prompts generation
 *
 * Sources:
 * - https://gofastmcp.com/servers/tools
 * - https://modelcontextprotocol.io/specification/2025-06-18/server/tools
 * - https://thinhdanggroup.github.io/mcp-production-ready/
 */

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

/**
 * Generate imports based on what the template needs
 */
function generateImports(config: FastMCPServerConfig): string {
  const imports = new Set<string>();

  // Core imports always needed
  imports.add('from typing import Any');
  imports.add('from fastmcp import FastMCP');
  imports.add('from fastmcp.exceptions import ToolError');

  // Check if we need async (httpx, aiofiles, etc.)
  const hasAsync = config.tools.some(t => t.isAsync);
  if (hasAsync) {
    // Imports handled by specific template
  }

  // Check dependencies for specific imports
  const deps = config.dependencies.join(' ');
  if (deps.includes('httpx')) {
    imports.add('import httpx');
  }
  if (deps.includes('aiofiles')) {
    imports.add('import aiofiles');
    imports.add('from pathlib import Path');
  }
  if (deps.includes('sqlalchemy')) {
    imports.add('from sqlalchemy import text');
    imports.add('from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession');
  }
  if (deps.includes('pathspec')) {
    imports.add('from pathlib import Path');
    imports.add('import os');
  }

  // Check if any tool has enum parameters (need Literal)
  const hasEnum = config.tools.some(t =>
    t.parameters.some(p => p.enum && p.enum.length > 0)
  );
  if (hasEnum) {
    imports.add('from typing import Literal');
  }

  return Array.from(imports).sort().join('\n');
}

/**
 * Generate tool annotations string
 */
function generateAnnotations(tool: FastMCPTool): string {
  if (!tool.annotations) {
    return '';
  }

  const parts: string[] = [];
  if (tool.annotations.readOnlyHint !== undefined) {
    parts.push(`"readOnlyHint": ${tool.annotations.readOnlyHint ? 'True' : 'False'}`);
  }
  if (tool.annotations.destructiveHint !== undefined) {
    parts.push(`"destructiveHint": ${tool.annotations.destructiveHint ? 'True' : 'False'}`);
  }
  if (tool.annotations.idempotentHint !== undefined) {
    parts.push(`"idempotentHint": ${tool.annotations.idempotentHint ? 'True' : 'False'}`);
  }
  if (tool.annotations.openWorldHint !== undefined) {
    parts.push(`"openWorldHint": ${tool.annotations.openWorldHint ? 'True' : 'False'}`);
  }

  if (parts.length === 0) {
    return '';
  }

  return `annotations={${parts.join(', ')}}`;
}

/**
 * Generate parameter type with Literal for enums
 */
function generateParamType(param: FastMCPToolParameter): string {
  const typeMap: Record<string, string> = {
    'string': 'str',
    'number': 'int',
    'boolean': 'bool',
    'object': 'dict[str, Any]',
    'array': 'list[Any]'
  };

  // If enum is defined, use Literal type
  if (param.enum && param.enum.length > 0) {
    const enumValues = param.enum.map(v => `"${v}"`).join(', ');
    return `Literal[${enumValues}]`;
  }

  return typeMap[param.type] || 'str';
}

/**
 * Generate production-ready server.py
 */
export function generateServerPy(config: FastMCPServerConfig): string {
  const sanitizedServerName = sanitizePythonString(config.serverName);
  const imports = generateImports(config);
  const tools = config.tools.map(tool => generateToolFunction(tool)).join('\n\n\n');
  const resources = generateResourceFunctions(config.resources || []);
  const prompts = generatePromptFunctions(config.prompts || []);

  return `"""
${config.serverName} - MCP Server

${config.description}

Generated with Auto-Claude MCP Manager
Following MCP Specification 2025-06-18 and FastMCP best practices.
"""
${imports}

# Create MCP server with error masking for production
mcp = FastMCP("${sanitizedServerName}", mask_error_details=True)


# ============================================================
# TOOLS
# ============================================================

${tools}

${resources ? `
# ============================================================
# RESOURCES
# ============================================================

${resources}
` : ''}
${prompts ? `
# ============================================================
# PROMPTS
# ============================================================

${prompts}
` : ''}

if __name__ == "__main__":
    mcp.run()
`;
}

/**
 * Generate production-ready tool function
 */
function generateToolFunction(tool: FastMCPTool): string {
  const sanitizedToolName = sanitizePythonIdentifier(tool.name, 'tool name');
  const sanitizedDescription = sanitizePythonString(tool.description);

  // Generate parameters
  const params = tool.parameters.map(p => {
    const sanitizedParamName = sanitizePythonIdentifier(p.name, 'parameter name');
    const pythonType = generateParamType(p);

    // Handle optional parameters with None default
    if (!p.required && p.default === undefined) {
      return `${sanitizedParamName}: ${pythonType} | None = None`;
    }

    const defaultValue = p.default !== undefined ? ` = ${toPythonValue(p.default)}` : '';
    return `${sanitizedParamName}: ${pythonType}${defaultValue}`;
  }).join(',\n    ');

  // Generate annotations decorator
  const annotationsStr = generateAnnotations(tool);
  const decorator = annotationsStr
    ? `@mcp.tool(${annotationsStr})`
    : '@mcp.tool()';

  // Generate async or sync function
  const asyncPrefix = tool.isAsync ? 'async ' : '';
  const defKeyword = `${asyncPrefix}def`;

  // Generate return type
  const returnType = tool.returnType || 'dict[str, Any]';

  // Generate docstring with parameters
  const paramDocs = tool.parameters.map(p => {
    const desc = p.description || `${p.name} parameter`;
    const reqStr = p.required ? '' : ' (optional)';
    return `        ${p.name}: ${desc}${reqStr}`;
  }).join('\n');

  // Generate validation code
  const validations = generateValidations(tool.parameters);

  return `${decorator}
${defKeyword} ${sanitizedToolName}(
    ${params}
) -> ${returnType}:
    """
    ${sanitizedDescription}

    Args:
${paramDocs}

    Returns:
        Result dictionary with success indicator and data

    Raises:
        ToolError: If validation fails or operation encounters an error
    """
${validations}
    try:
        # TODO: Implement ${sanitizedToolName}
        return {
            "success": True,
            "message": "Not implemented yet",
            "tool": "${sanitizedToolName}"
        }
    except Exception as e:
        raise ToolError(f"${sanitizedToolName} failed: {str(e)}", code=-32603)`;
}

/**
 * Generate validation code for parameters
 */
function generateValidations(params: FastMCPToolParameter[]): string {
  const validations: string[] = [];

  for (const param of params) {
    const name = param.name;

    // Required string validation
    if (param.required && param.type === 'string') {
      validations.push(`    if not ${name} or not ${name}.strip():
        raise ToolError("${name} cannot be empty", code=-32602)`);
    }

    // Min/max length for strings
    if (param.minLength !== undefined) {
      validations.push(`    if ${name} and len(${name}) < ${param.minLength}:
        raise ToolError("${name} must be at least ${param.minLength} characters", code=-32602)`);
    }
    if (param.maxLength !== undefined) {
      validations.push(`    if ${name} and len(${name}) > ${param.maxLength}:
        raise ToolError("${name} cannot exceed ${param.maxLength} characters", code=-32602)`);
    }

    // Min/max value for numbers
    if (param.minValue !== undefined) {
      validations.push(`    if ${name} is not None and ${name} < ${param.minValue}:
        raise ToolError("${name} must be at least ${param.minValue}", code=-32602)`);
    }
    if (param.maxValue !== undefined) {
      validations.push(`    if ${name} is not None and ${name} > ${param.maxValue}:
        raise ToolError("${name} cannot exceed ${param.maxValue}", code=-32602)`);
    }

    // Pattern validation (URL pattern)
    if (param.pattern === '^https?://.+') {
      validations.push(`    if ${name} and not ${name}.startswith(('http://', 'https://')):
        raise ToolError("${name} must start with http:// or https://", code=-32602)`);
    }
  }

  if (validations.length === 0) {
    return '';
  }

  return '\n    # Input validation\n' + validations.join('\n\n') + '\n';
}

/**
 * Generate resource functions
 */
function generateResourceFunctions(resources: FastMCPResource[]): string {
  if (!resources || resources.length === 0) {
    return '';
  }

  return resources.map(resource => {
    const params = resource.parameters || [];
    const paramStr = params.length > 0
      ? params.map(p => `${p.name}: str`).join(', ')
      : '';

    const hasParams = params.length > 0;
    const isAsync = resource.uri.includes('stats') || resource.uri.includes('session');

    const funcName = resource.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const asyncPrefix = isAsync ? 'async ' : '';

    return `@mcp.resource("${resource.uri}")
${asyncPrefix}def get_${funcName}(${paramStr}) -> str:
    """
    ${resource.description}

    Returns:
        ${resource.mimeType || 'text/plain'} content
    """
    # TODO: Implement resource
    import json
    return json.dumps({
        "resource": "${resource.name}",
        "uri": "${resource.uri}",
        "status": "not_implemented"
    }, indent=2)`;
  }).join('\n\n\n');
}

/**
 * Generate prompt functions
 */
function generatePromptFunctions(prompts: FastMCPPrompt[]): string {
  if (!prompts || prompts.length === 0) {
    return '';
  }

  return prompts.map(prompt => {
    const args = prompt.arguments || [];
    const paramStr = args.map(a => {
      const defaultVal = a.required ? '' : ' = None';
      return `${a.name}: str${defaultVal}`;
    }).join(', ');

    const funcName = prompt.name.toLowerCase().replace(/[^a-z0-9]/g, '_');

    const argDocs = args.map(a => {
      const req = a.required ? '' : ' (optional)';
      return `        ${a.name}: ${a.description}${req}`;
    }).join('\n');

    return `@mcp.prompt()
def ${funcName}(${paramStr}) -> str:
    """
    ${prompt.description}

    Args:
${argDocs}

    Returns:
        Prompt message for the AI assistant
    """
    # TODO: Implement prompt
    parts = []
    parts.append(f"Prompt: ${prompt.name}")
${args.map(a => `    if ${a.name}:
        parts.append(f"${a.name}: {${a.name}}")`).join('\n')}
    return "\\n".join(parts)`;
  }).join('\n\n\n');
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

/**
 * Generate modular file structure for complete-showcase template
 * Returns array of files with nested paths (e.g., "src/showcase/server.py")
 */
export function generateCompleteShowcaseFiles(config: FastMCPServerConfig): Array<{ filename: string; content: string }> {
  const packageName = config.serverName.toLowerCase().replace(/[^a-z0-9]/g, '_');

  return [
    // Root level files
    { filename: 'pyproject.toml', content: generateCompleteShowcasePyproject(config, packageName) },
    { filename: 'README.md', content: generateCompleteShowcaseReadme(config) },
    { filename: '.python-version', content: config.pythonVersion },

    // Package structure
    { filename: `src/${packageName}/__init__.py`, content: '' },
    { filename: `src/${packageName}/__main__.py`, content: generateMainPy(packageName) },
    { filename: `src/${packageName}/server.py`, content: generateModularServerPy(config, packageName) },
    { filename: `src/${packageName}/config.py`, content: generateConfigPy(config, packageName) },

    // Tools sub-server
    { filename: `src/${packageName}/tools/__init__.py`, content: generateToolsInit() },
    { filename: `src/${packageName}/tools/server.py`, content: generateToolsServer(config) },

    // Resources sub-server
    { filename: `src/${packageName}/resources/__init__.py`, content: generateResourcesInit() },
    { filename: `src/${packageName}/resources/server.py`, content: generateResourcesServer(packageName) },

    // Prompts sub-server
    { filename: `src/${packageName}/prompts/__init__.py`, content: generatePromptsInit() },
    { filename: `src/${packageName}/prompts/server.py`, content: generatePromptsServer() },

    // Middleware
    { filename: `src/${packageName}/middleware/__init__.py`, content: generateMiddlewareInit() },
    { filename: `src/${packageName}/middleware/logging.py`, content: generateLoggingMiddleware() },
    { filename: `src/${packageName}/middleware/auth.py`, content: generateAuthMiddleware() },

    // Assets directory
    { filename: 'assets/sample-data.json', content: generateSampleData() }
  ];
}

function generateCompleteShowcasePyproject(config: FastMCPServerConfig, packageName: string): string {
  const deps = config.dependencies.map(d => `    "${d}"`).join(',\n');

  return `[project]
name = "${config.serverName}"
version = "1.0.0"
description = "${sanitizePythonString(config.description)}"
readme = "README.md"
authors = [{ name = "Auto-Claude", email = "info@auto-claude.com" }]
requires-python = ">=${config.pythonVersion}"
dependencies = [
${deps}
]

[project.scripts]
${packageName} = "${packageName}.__main__:main"

[dependency-groups]
dev = ["ruff", "pytest", "pytest-asyncio", "ipython"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/${packageName}"]

[tool.ruff]
line-length = 100
target-version = "py${config.pythonVersion.replace('.', '')}"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
`;
}

function generateCompleteShowcaseReadme(config: FastMCPServerConfig): string {
  return `# ${config.serverName}

${config.description}

Generated with Auto-Claude MCP Manager - Complete MCP Showcase Template

## Features

This server demonstrates ALL FastMCP capabilities:

- **Tools**: Text analysis, HTTP client, image processing, PDF reading, pagination
- **Resources**: Static config, dynamic data, URI templates, file serving, real-time stats
- **Prompts**: Code review, debugging, data analysis, documentation generation
- **Middleware**: Logging, authentication
- **Server Composition**: Modular sub-servers using mount()
- **Full Type Annotations**: Python 3.10+ type hints throughout
- **Async/Await**: Proper async patterns for I/O operations

## Installation

\`\`\`bash
uv sync
\`\`\`

## Usage

\`\`\`bash
uv run ${config.serverName.toLowerCase().replace(/[^a-z0-9]/g, '_')}
\`\`\`

Or directly:

\`\`\`bash
uv run server.py
\`\`\`

## Structure

- \`src/${config.serverName.toLowerCase().replace(/[^a-z0-9]/g, '_')}/\` - Main package
  - \`server.py\` - Main server with sub-server composition
  - \`config.py\` - Pydantic settings with environment variable support
  - \`tools/\` - Tools sub-server
  - \`resources/\` - Resources sub-server
  - \`prompts/\` - Prompts sub-server
  - \`middleware/\` - Middleware implementations
- \`assets/\` - Sample data files

## Configuration

Environment variables (prefix: \`SHOWCASE_\`):

- \`SHOWCASE_ENABLE_AUTH\` - Enable authentication middleware (default: false)
- \`SHOWCASE_ENABLE_CACHING\` - Enable caching (default: true)
- \`SHOWCASE_ENABLE_LOGGING\` - Enable logging (default: true)
- \`SHOWCASE_MAX_PAGE_SIZE\` - Maximum page size for pagination (default: 100)

## Learn More

- FastMCP Documentation: https://github.com/jlowin/fastmcp
- MCP Specification: https://modelcontextprotocol.io/
`;
}

function generateMainPy(packageName: string): string {
  return `from ${packageName}.server import mcp

def main():
    """Run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
`;
}

function generateModularServerPy(config: FastMCPServerConfig, packageName: string): string {
  const sanitizedServerName = sanitizePythonString(config.serverName);

  return `"""
${config.serverName} - Complete MCP Showcase Server

Demonstrates all FastMCP capabilities with a modular architecture.
"""
from fastmcp import FastMCP
from ${packageName}.config import settings
from ${packageName}.tools import tools_mcp
from ${packageName}.resources import resources_mcp
from ${packageName}.prompts import prompts_mcp
from ${packageName}.middleware.logging import LoggingMiddleware
from ${packageName}.middleware.auth import SimpleAuthMiddleware

# Create main server
mcp = FastMCP(settings.server_name)

# Mount sub-servers with prefixes
mcp.mount(tools_mcp, prefix="tools")
mcp.mount(resources_mcp, prefix="resources")
mcp.mount(prompts_mcp, prefix="prompts")

# Add middleware
if settings.enable_logging:
    mcp.add_middleware(LoggingMiddleware(verbose=True))

if settings.enable_auth:
    mcp.add_middleware(SimpleAuthMiddleware(enabled=True))
`;
}

function generateConfigPy(config: FastMCPServerConfig, packageName: string): string {
  return `"""
Configuration for ${config.serverName}
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SHOWCASE_",
        case_sensitive=False
    )

    # Server settings
    server_name: str = "${sanitizePythonString(config.serverName)}"
    server_version: str = "1.0.0"

    # Paths
    assets_dir: Path = Path(__file__).parent.parent.parent / "assets"

    # Feature flags
    enable_auth: bool = False
    enable_caching: bool = True
    enable_logging: bool = True

    # Pagination defaults
    default_page_size: int = 10
    max_page_size: int = 100


# Global settings instance
settings = Settings()
`;
}

function generateToolsInit(): string {
  return `from .server import tools_mcp

__all__ = ["tools_mcp"]
`;
}

function generateToolsServer(config: FastMCPServerConfig): string {
  return `"""
Tools Sub-Server - Demonstrates modern MCP tool patterns with FastMCP 2.14+

Best Practices Demonstrated:
- ToolResult with structured_content for rich responses
- Cursor-based pagination (industry standard)
- ToolError for validation failures
- Async patterns for I/O operations
- Comprehensive type hints
- Detailed docstrings with Args/Returns
"""
from typing import Literal, Any
import httpx
from PIL import Image as PILImage, ImageFilter, ImageOps
import pypdf
import base64
from io import BytesIO

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.tool import ToolResult
from mcp.types import ImageContent, TextContent

# Create tools sub-server
tools_mcp = FastMCP("Showcase Tools")


@tools_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "requiresAuth": False
    }
)
def analyze_text(
    text: str,
    operation: Literal["count_words", "sentiment", "summary"]
) -> dict[str, Any]:
    """
    Analyze text with various operations.

    Demonstrates: Basic tool with enum parameters and structured output.

    Args:
        text: Input text to analyze
        operation: Type of analysis (count_words, sentiment, summary)

    Returns:
        Dictionary with operation type and analysis results

    Examples:
        - count_words: Returns word count, char count, unique words
        - sentiment: Returns positive/negative/neutral with indicators
        - summary: Returns first sentence summary with total length
    """
    # Input validation
    if not text or not text.strip():
        raise ToolError("Text cannot be empty", code=-32602)

    if operation == "count_words":
        words = text.split()
        return {
            "operation": "count_words",
            "word_count": len(words),
            "char_count": len(text),
            "unique_words": len(set(words)),
            "success": True
        }

    elif operation == "sentiment":
        # Simple sentiment (in real case, use a library)
        positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "horrible", "poor"]

        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "operation": "sentiment",
            "sentiment": sentiment,
            "positive_indicators": pos_count,
            "negative_indicators": neg_count,
            "confidence": abs(pos_count - neg_count) / max(pos_count + neg_count, 1),
            "success": True
        }

    elif operation == "summary":
        # Simple summary: first sentence + word count
        first_sentence = text.split('.')[0] if '.' in text else text[:100]
        return {
            "operation": "summary",
            "summary": first_sentence + "...",
            "total_length": len(text),
            "compression_ratio": len(first_sentence) / len(text),
            "success": True
        }

    return {"success": False, "error": "Unknown operation"}


@tools_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "requiresAuth": False
    }
)
async def fetch_data(
    url: str,
    method: Literal["GET", "POST"] = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 30
) -> dict[str, Any]:
    """
    Make HTTP requests to external APIs.

    Demonstrates: Async tool, HTTP client usage, comprehensive error handling.

    Args:
        url: Full URL to request (must be valid HTTP/HTTPS)
        method: HTTP method (GET or POST)
        headers: Optional HTTP headers dictionary
        body: Optional request body for POST requests
        timeout: Request timeout in seconds (default: 30, max: 60)

    Returns:
        Dictionary with status_code, headers, data, and success indicator

    Raises:
        ToolError: If URL is invalid or timeout exceeds maximum
    """
    # Input validation
    if not url.startswith(('http://', 'https://')):
        raise ToolError("URL must start with http:// or https://", code=-32602)

    if timeout > 60:
        raise ToolError("Timeout cannot exceed 60 seconds", code=-32602)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            else:  # POST
                response = await client.post(url, headers=headers, json=body)

            content_type = response.headers.get("content-type", "")

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response.json() if "json" in content_type else response.text,
                "success": response.is_success,
                "elapsed_ms": response.elapsed.total_seconds() * 1000
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timed out",
                "error_type": "TimeoutError",
                "timeout": timeout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


@tools_mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "requiresAuth": False
    }
)
def process_image(
    image_path: str,
    operation: Literal["resize", "rotate", "grayscale", "blur"]
) -> ToolResult:
    """
    Process images with various operations.

    Demonstrates: ToolResult with BOTH structured data AND image content.

    Args:
        image_path: Path to image file
        operation: Image operation (resize, rotate, grayscale, blur)

    Returns:
        ToolResult with operation metadata and processed image

    Note:
        Returns ToolResult combining structured_content (metadata)
        and content (the actual image). This is the modern FastMCP pattern.
    """
    try:
        img = PILImage.open(image_path)
        original_size = img.size
        original_mode = img.mode

        if operation == "resize":
            img = img.resize((200, 200))
        elif operation == "rotate":
            img = img.rotate(90, expand=True)
        elif operation == "grayscale":
            img = ImageOps.grayscale(img)
        elif operation == "blur":
            img = img.filter(ImageFilter.BLUR)

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        # Return ToolResult with BOTH structured data AND image
        return ToolResult(
            structured_content={
                "operation": operation,
                "success": True,
                "original_size": original_size,
                "original_mode": original_mode,
                "new_size": img.size,
                "new_mode": img.mode,
                "format": "PNG",
                "file_size_bytes": len(img_bytes)
            },
            content=[
                ImageContent(
                    type="image",
                    data=base64.b64encode(img_bytes).decode(),
                    mimeType="image/png"
                )
            ]
        )
    except FileNotFoundError:
        return ToolResult(
            structured_content={
                "success": False,
                "error": f"Image file not found: {image_path}",
                "error_type": "FileNotFoundError"
            }
        )
    except Exception as e:
        return ToolResult(
            structured_content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


@tools_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "requiresAuth": False
    }
)
def read_pdf(
    file_path: str,
    page_range: str | None = None
) -> ToolResult:
    """
    Extract text from PDF files.

    Demonstrates: Binary file handling with ToolResult.

    Args:
        file_path: Path to PDF file
        page_range: Page range (e.g., "1-3" or "all", default: "all")

    Returns:
        ToolResult with metadata and extracted text content
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            # Parse page range (e.g., "1-3" or "all")
            if page_range and page_range != "all":
                try:
                    start, end = map(int, page_range.split('-'))
                    pages_to_read = range(start - 1, min(end, total_pages))
                except ValueError:
                    raise ToolError("Invalid page range format. Use '1-3' or 'all'", code=-32602)
            else:
                pages_to_read = range(total_pages)

            text_content = []
            for page_num in pages_to_read:
                page = pdf_reader.pages[page_num]
                text_content.append({
                    "page": page_num + 1,
                    "text": page.extract_text()
                })

            return ToolResult(
                structured_content={
                    "success": True,
                    "total_pages": total_pages,
                    "pages_read": len(text_content),
                    "metadata": dict(pdf_reader.metadata) if pdf_reader.metadata else {}
                },
                content=[
                    TextContent(
                        type="text",
                        text=f"Extracted {len(text_content)} pages from PDF\\n\\n" +
                             "\\n\\n".join([f"Page {p['page']}:\\n{p['text']}" for p in text_content])
                    )
                ]
            )
    except FileNotFoundError:
        return ToolResult(
            structured_content={
                "success": False,
                "error": f"PDF file not found: {file_path}",
                "error_type": "FileNotFoundError"
            }
        )
    except Exception as e:
        return ToolResult(
            structured_content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


@tools_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "requiresAuth": False
    }
)
def search_with_cursor(
    query: str,
    cursor: str | None = None,
    limit: int = 10
) -> dict[str, Any]:
    """
    Search with cursor-based pagination (MODERN BEST PRACTICE).

    Demonstrates: Efficient cursor pagination for large datasets.
    This is the industry-standard approach used by GitHub, Stripe, Twitter, etc.

    Why cursor pagination is better than offset:
    - O(1) performance vs O(n) with offset
    - Works correctly with dynamic data (inserts/deletes)
    - More efficient for large datasets
    - No missing or duplicate results

    Args:
        query: Search query string
        cursor: Continuation token from previous response (None for first page)
        limit: Maximum results per page (default: 10, max: 100)

    Returns:
        Dictionary with results, has_more, next_cursor, and count

    Raises:
        ToolError: If limit exceeds maximum allowed value

    Example Usage:
        # First page
        response = search_with_cursor("python", limit=10)

        # Next page (if has_more is True)
        response = search_with_cursor("python", cursor=response["next_cursor"], limit=10)
    """
    # Input validation
    if limit > 100:
        raise ToolError("Limit cannot exceed 100", code=-32602)

    if limit < 1:
        raise ToolError("Limit must be at least 1", code=-32602)

    # Simulated dataset (in production, this would be a database query)
    all_results = [
        {"id": i, "title": f"Result {i}", "content": f"Content for {query} - item {i}"}
        for i in range(1, 501)  # 500 mock results to demonstrate pagination
    ]

    # Decode cursor to get last_id (start position)
    last_id = int(cursor) if cursor else 0

    # Fetch results AFTER cursor (more efficient than offset)
    # In production: SELECT * FROM data WHERE id > ? AND query LIKE ? LIMIT ?
    results = [r for r in all_results if r["id"] > last_id][:limit + 1]

    # Check if more results exist
    has_more = len(results) > limit
    if has_more:
        results = results[:limit]

    # Generate next cursor (ID of last item)
    next_cursor = str(results[-1]["id"]) if results and has_more else None

    return {
        "query": query,
        "results": results,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "count": len(results),
        "cursor_used": cursor,
        "pagination_type": "cursor",
        "note": "Use next_cursor for the next page. More efficient than offset pagination."
    }
`;
}

function generateResourcesInit(): string {
  return `from .server import resources_mcp

__all__ = ["resources_mcp"]
`;
}

function generateResourcesServer(packageName: string): string {
  return `"""
Resources Sub-Server - Demonstrates modern context-aware MCP resource patterns

Best Practices Demonstrated:
- Context-aware resources using FastMCP Context
- Real-time dynamic data (not fake static data)
- URI templates with parameter extraction
- Mix of sync and async resource patterns
- Comprehensive error handling
- Session/user aware data fetching
"""
from datetime import datetime
from pathlib import Path
import json
import psutil
from typing import Any

from fastmcp import FastMCP, Context
from ${packageName}.config import settings

# Create resources sub-server
resources_mcp = FastMCP("Showcase Resources")


@resources_mcp.resource("config://settings")
def get_config() -> str:
    """
    Server configuration (static resource).

    Returns current server settings and feature flags.
    Useful for clients to discover server capabilities.

    Demonstrates: Static resource pattern with JSON data
    """
    config_data = {
        "server_name": settings.server_name,
        "server_version": settings.server_version,
        "features": {
            "auth_enabled": settings.enable_auth,
            "caching_enabled": settings.enable_caching,
            "logging_enabled": settings.enable_logging
        },
        "pagination": {
            "default_page_size": settings.default_page_size,
            "max_page_size": settings.max_page_size
        }
    }
    return json.dumps(config_data, indent=2)


@resources_mcp.resource("stats://server/realtime")
async def get_server_stats_realtime(ctx: Context) -> str:
    """
    Real-time server statistics (dynamic context-aware resource).

    Returns live metrics including:
    - CPU and memory usage
    - Active connections
    - Request statistics
    - Uptime

    Demonstrates: Real-time data with Context awareness

    Args:
        ctx: FastMCP Context with session metadata

    Returns:
        JSON with real-time server metrics
    """
    # Access context metadata (if available)
    metadata = getattr(ctx.request_context, 'meta', None) if hasattr(ctx, 'request_context') else None
    requester = metadata.user_id if metadata and hasattr(metadata, 'user_id') else "anonymous"

    # Fetch REAL-TIME data (not static fake data)
    process = psutil.Process()
    now = datetime.now()

    stats: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "requester": requester,
        "system": {
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "threads": process.num_threads(),
            "uptime_seconds": round(
                (now - datetime.fromtimestamp(process.create_time())).total_seconds()
            )
        },
        "server": {
            "name": settings.server_name,
            "version": settings.server_version,
            "started_at": datetime.fromtimestamp(process.create_time()).isoformat()
        },
        "note": "This is REAL-TIME data, not static - values change on each request"
    }

    return json.dumps(stats, indent=2)


@resources_mcp.resource("session://current")
async def get_session_info(ctx: Context) -> str:
    """
    Current session information for the authenticated request.

    Returns session metadata, authentication status, and context data.
    Shows how to access request context and user information.

    Demonstrates: Context-aware resource with session data

    Args:
        ctx: FastMCP Context with session/user metadata

    Returns:
        JSON with session information
    """
    # Extract metadata from context
    metadata = getattr(ctx.request_context, 'meta', None) if hasattr(ctx, 'request_context') else None
    session_id = getattr(ctx, 'session_id', None)

    session_info: dict[str, Any] = {
        "session_id": session_id or "no_session",
        "timestamp": datetime.now().isoformat(),
        "authentication": {
            "authenticated": metadata is not None,
            "user_id": metadata.user_id if metadata and hasattr(metadata, 'user_id') else None,
            "workspace": metadata.workspace if metadata and hasattr(metadata, 'workspace') else None
        },
        "context_available": {
            "has_metadata": metadata is not None,
            "has_session_id": session_id is not None,
            "request_context_exists": hasattr(ctx, 'request_context')
        },
        "server_info": {
            "name": settings.server_name,
            "version": settings.server_version
        },
        "note": "Context-aware resource - data varies by session/user"
    }

    return json.dumps(session_info, indent=2)


@resources_mcp.resource("logs://{date}")
def get_logs_by_date(date: str) -> str:
    """
    Server logs for specific date (parameterized resource).

    URI template pattern: logs://2024-01-20 -> date parameter extracted
    In production, this would query actual log storage (files, DB, etc.)

    Demonstrates: URI template with parameter extraction

    Args:
        date: Date string from URI (e.g., "2024-01-20")

    Returns:
        Log entries for the specified date
    """
    # In production, fetch actual logs from storage
    # Example: log_entries = LogStorage.get_logs_for_date(date)

    return f"""# Server Logs for {date}

[{date} 00:15:23] INFO - Server started successfully
[{date} 02:30:45] INFO - Tool 'analyze_text' called (50 requests)
[{date} 05:45:12] INFO - Resource 'config://settings' accessed
[{date} 08:20:33] INFO - Cache hit rate: 87.5%
[{date} 12:10:45] WARN - High memory usage: 1.2GB
[{date} 15:30:12] INFO - Tool 'process_image' completed in 2.3s
[{date} 18:45:23] INFO - Daily statistics updated
[{date} 23:59:59] INFO - Total requests today: 1,247

NOTE: In production, these would be REAL logs from log storage.
This demonstrates the URI parameter pattern: logs://{{date}}
"""


@resources_mcp.resource("data://users/{user_id}")
async def get_user_data(ctx: Context, user_id: str) -> str:
    """
    Fetch specific user data by ID (context-aware parameterized resource).

    Combines URI parameters with context awareness.
    In production, this would:
    1. Check requester permissions via ctx
    2. Fetch actual user data from database
    3. Filter fields based on requester role

    Demonstrates: Context + parameters + access control pattern

    Args:
        ctx: FastMCP Context for permission checking
        user_id: User ID from URI (e.g., "data://users/123")

    Returns:
        JSON with user data (filtered by permissions)
    """
    # Check requester permissions from context
    metadata = getattr(ctx.request_context, 'meta', None) if hasattr(ctx, 'request_context') else None
    requester = metadata.user_id if metadata and hasattr(metadata, 'user_id') else "anonymous"

    # In production:
    # - Verify requester has access to this user_id
    # - Fetch from database: user = await db.users.get(user_id)
    # - Filter sensitive fields based on requester role

    # Simulated response showing the pattern
    user_data: dict[str, Any] = {
        "user_id": user_id,
        "requested_by": requester,
        "data": {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "role": "user",
            "created_at": "2024-01-01T00:00:00Z",
            "last_seen": datetime.now().isoformat()
        },
        "permissions": {
            "can_edit": requester == user_id,  # Users can edit their own data
            "can_delete": False,
            "can_view_sensitive": requester == user_id
        },
        "note": "In production: data from DB, filtered by requester permissions"
    }

    return json.dumps(user_data, indent=2)


@resources_mcp.resource("file://assets/{filename}")
def get_asset_file(filename: str) -> str:
    """
    Serve files from assets directory (file resource pattern).

    Demonstrates: File serving with error handling
    In production: Add MIME type detection, streaming for large files

    Args:
        filename: File name from URI (e.g., "file://assets/logo.png")

    Returns:
        File contents or error JSON
    """
    asset_path = settings.assets_dir / filename

    if not asset_path.exists():
        return json.dumps({
            "error": "File not found",
            "path": str(asset_path),
            "available_files": [f.name for f in settings.assets_dir.iterdir()] if settings.assets_dir.exists() else []
        }, indent=2)

    try:
        with open(asset_path, 'r') as f:
            return f.read()
    except UnicodeDecodeError:
        # Binary file - in production, return as base64 or stream
        return json.dumps({
            "error": "Binary file - use appropriate client",
            "filename": filename,
            "note": "In production: return as base64 or stream"
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@resources_mcp.resource("data://search/{query}")
def search_data(query: str) -> str:
    """
    Search data with query parameter (parameterized search resource).

    In production: Query actual search index/database
    Show cursor-based pagination pattern in results

    Demonstrates: Search pattern with URI parameters

    Args:
        query: Search query from URI

    Returns:
        JSON with search results
    """
    # In production:
    # - Query search index (Elasticsearch, etc.)
    # - Apply filters, ranking
    # - Return cursor for pagination

    results = {
        "query": query,
        "total_results": 42,  # In production: actual count
        "results": [
            {
                "id": i,
                "title": f"Result {i} for: {query}",
                "score": round(1.0 - (i * 0.1), 2),
                "snippet": f"...matching content for {query}...",
                "url": f"data://item/{i}"
            }
            for i in range(1, 6)
        ],
        "pagination": {
            "has_more": True,
            "next_cursor": "cursor_123",  # Use cursor-based pagination
            "note": "Use cursor for next page (best practice)"
        },
        "note": "In production: real search results from index/database"
    }

    return json.dumps(results, indent=2)
`;
}

function generatePromptsInit(): string {
  return `from .server import prompts_mcp

__all__ = ["prompts_mcp"]
`;
}

function generatePromptsServer(): string {
  return `"""
Prompts Sub-Server - Demonstrates modern context-aware MCP prompt patterns

Best Practices Demonstrated:
- Context-aware prompts using FastMCP Context
- Dynamic content based on session/user data
- Parameterized prompts with sensible defaults
- Comprehensive docstrings with use cases
- Mix of static and dynamic prompts
"""
from fastmcp import FastMCP, Context

# Create prompts sub-server
prompts_mcp = FastMCP("Showcase Prompts")


@prompts_mcp.prompt()
def code_review(
    language: str = "python",
    focus: str = "general"
) -> str:
    """
    Generate a code review prompt with specific focus areas.

    Demonstrates: Basic parameterized prompt with language and focus options.

    Args:
        language: Programming language (default: python)
        focus: Review focus area (default: general)

    Returns:
        Formatted code review prompt tailored to language and focus
    """
    return f"""You are an expert {language} code reviewer.

Focus area: {focus}

Please review the following code for:
- Code quality and readability
- Performance optimizations
- Security vulnerabilities
- Best practices for {language}
- {"Specific focus on: " + focus if focus != "general" else "General code quality"}

Provide constructive feedback with examples.
"""


@prompts_mcp.prompt()
async def workspace_insights(ctx: Context) -> str:
    """
    Context-aware workspace analysis prompt.

    Demonstrates: Dynamic prompt using Context to access session metadata.
    This prompt adapts based on the authenticated user's environment.

    Args:
        ctx: FastMCP Context with session and metadata

    Returns:
        Personalized workspace insights prompt

    Note:
        In production, this would fetch real user/workspace data.
        For this example, it demonstrates the pattern using metadata.
    """
    # Access metadata from context (set by client or middleware)
    metadata = getattr(ctx.request_context, 'meta', None) if hasattr(ctx, 'request_context') else None

    # Extract user info from metadata
    user_id = None
    workspace = "default"

    if metadata and hasattr(metadata, 'user_id'):
        user_id = metadata.user_id
    if metadata and hasattr(metadata, 'workspace'):
        workspace = metadata.workspace

    # Build dynamic prompt based on context
    return f"""You are an intelligent workspace assistant analyzing workspace: {workspace}

{"User context: " + user_id if user_id else "Anonymous session"}

## Your Task

Analyze the user's workspace and provide:

1. **Resource Patterns**
   - Common naming conventions
   - Organizational structure
   - Usage patterns

2. **Smart Recommendations**
   - Workflow optimizations
   - Best practices specific to this workspace
   - Efficiency improvements

3. **Context-Aware Examples**
   - Use actual workspace conventions
   - Reference real patterns
   - Provide actionable insights

## Dynamic Analysis

This prompt adapts to YOUR specific workspace context, providing personalized
recommendations based on actual usage patterns and conventions.

{"NOTE: Authenticated as " + user_id if user_id else "NOTE: For authenticated users, this prompt provides even more personalized insights."}
"""


@prompts_mcp.prompt()
def bug_diagnosis(
    error_type: str = "general",
    severity: str = "medium"
) -> str:
    """
    Interactive debugging assistant prompt.

    Demonstrates: Severity-aware debugging guidance.

    Args:
        error_type: Type of error (default: general)
        severity: Bug severity level (default: medium)

    Returns:
        Debugging prompt tailored to error type and severity
    """
    urgency_note = {
        "critical": "URGENT: Production system affected. Immediate action required.",
        "high": "High priority: Significant impact on functionality.",
        "medium": "Medium priority: Notable issue requiring attention.",
        "low": "Low priority: Minor issue or enhancement."
    }.get(severity.lower(), "")

    return f"""You are a debugging expert helping diagnose a {severity} severity {error_type} issue.

{urgency_note}

Please help by:
1. Analyzing the error message and stack trace
2. Identifying the root cause
3. Suggesting potential fixes
4. Recommending preventive measures
5. {"Providing immediate mitigation steps" if severity in ["critical", "high"] else "Suggesting long-term improvements"}

{"Ask clarifying questions if needed to understand the context better." if severity not in ["critical"] else "Focus on immediate resolution steps."}
"""


@prompts_mcp.prompt()
async def personalized_workflow(
    ctx: Context,
    workflow_type: str,
    target: str = "production"
) -> str:
    """
    Generate workflow guide personalized to user's environment.

    Demonstrates: Context-aware prompt with user preferences and history.

    Args:
        ctx: FastMCP Context with user session
        workflow_type: Type of workflow (deployment, testing, migration)
        target: Target environment (default: production)

    Returns:
        Workflow guide customized to user's context and patterns
    """
    # Access user context
    metadata = getattr(ctx.request_context, 'meta', None) if hasattr(ctx, 'request_context') else None
    user_id = metadata.user_id if metadata and hasattr(metadata, 'user_id') else "anonymous"

    return f"""# {workflow_type.title()} Workflow Guide

**Target Environment:** {target}
**User:** {user_id}

## Personalized Workflow

This guide is customized based on your environment and preferences.

### 1. Preparation Phase

Based on YOUR typical patterns:
- Environment configuration: {target}
- Naming conventions: [Auto-detected from your history]
- Quality standards: [Based on your project settings]

### 2. Execution Steps

**{workflow_type.title()} Process:**

1. Pre-flight checks
   - Validate {target} environment
   - Check dependencies
   - Review change impact

2. Execute {workflow_type}
   - Follow your established patterns
   - Use your preferred tools
   - Apply your quality gates

3. Validation
   - Run your standard test suite
   - Verify against your acceptance criteria
   - Check {target}-specific requirements

### 3. Best Practices for {target.title()}

{"- Zero-downtime deployment" if target == "production" else ""}
{"- Comprehensive testing" if target == "staging" else ""}
{"- Rapid iteration" if target == "development" else ""}
- Rollback procedures
- Monitoring and alerts

## Context-Aware Notes

This workflow adapts to YOUR specific environment, tools, and preferences.
{"For authenticated users, we analyze your actual workflow history to provide even more precise guidance." if user_id == "anonymous" else ""}
"""


@prompts_mcp.prompt()
def data_analysis(
    data_type: str = "tabular",
    analysis_goal: str = "insights"
) -> str:
    """
    Data analysis prompt for various data types.

    Demonstrates: Goal-oriented analysis with data type awareness.

    Args:
        data_type: Type of data (default: tabular)
        analysis_goal: Analysis objective (default: insights)

    Returns:
        Data analysis prompt tailored to data type and goal
    """
    analysis_steps = {
        "insights": [
            "Identify key patterns and trends",
            "Discover correlations and anomalies",
            "Generate actionable insights",
            "Suggest next steps"
        ],
        "predictions": [
            "Analyze historical patterns",
            "Build predictive models",
            "Validate predictions",
            "Quantify confidence intervals"
        ],
        "optimization": [
            "Identify bottlenecks",
            "Suggest optimizations",
            "Quantify potential improvements",
            "Prioritize actions"
        ]
    }.get(analysis_goal, ["Perform comprehensive analysis"])

    return f"""You are a data analysis expert working with {data_type} data.

Analysis goal: {analysis_goal}

## Your Task

{"".join([f"{i+1}. {step}" + chr(10) for i, step in enumerate(analysis_steps)])}

## Data Type Considerations

{"Focus on: rows, columns, aggregations, joins" if data_type == "tabular" else ""}
{"Focus on: document structure, text analysis, embeddings" if data_type == "text" else ""}
{"Focus on: time patterns, seasonality, trends, forecasting" if data_type == "time-series" else ""}
{"Focus on: nodes, edges, paths, communities" if data_type == "graph" else ""}

## Expected Output

- Detailed findings
- Visualizations (describe them)
- Actionable recommendations
- Next steps for deeper analysis
"""


@prompts_mcp.prompt()
def api_documentation(
    api_type: str = "REST",
    audience: str = "developers"
) -> str:
    """
    Generate API documentation tailored to audience.

    Demonstrates: Audience-aware documentation generation.

    Args:
        api_type: API type (default: REST)
        audience: Target audience (default: developers)

    Returns:
        API documentation prompt customized for audience level
    """
    technical_depth = "comprehensive" if audience == "developers" else "simplified"
    code_examples = "multiple languages" if audience == "developers" else "simple examples"

    return f"""You are creating {api_type} API documentation for {audience}.

## Documentation Style

- Technical depth: {technical_depth}
- Code examples: {code_examples}
- {"Include architectural details and best practices" if audience == "developers" else "Focus on getting started quickly"}

## Required Sections

- Clear endpoint descriptions
- Request/response examples
- Authentication details
- Error handling
- Rate limiting information
- {"Advanced usage patterns" if audience == "developers" else "Common use cases"}
- {"Performance optimization tips" if audience == "developers" else "Troubleshooting guide"}

Make it {"technically comprehensive with implementation details" if audience == "developers" else "beginner-friendly with step-by-step guidance"}.
"""
`;
}

function generateMiddlewareInit(): string {
  return `from .logging import LoggingMiddleware
from .auth import SimpleAuthMiddleware

__all__ = ["LoggingMiddleware", "SimpleAuthMiddleware"]
`;
}

function generateLoggingMiddleware(): string {
  return `"""
Logging Middleware - Logs all tool calls and resource accesses
"""
from datetime import datetime
from typing import Any
from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
import mcp.types as mt


class LoggingMiddleware(Middleware):
    """Logs all MCP operations (tools, resources, prompts)."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, Any]
    ) -> Any:
        tool_name = context.message.name
        timestamp = datetime.now().isoformat()

        print(f"[{timestamp}] Tool called: {tool_name}")

        if self.verbose:
            print(f"  Arguments: {context.message.arguments}")

        result = await call_next(context)

        if self.verbose:
            print(f"  Result: {result}")

        return result

    async def on_read_resource(
        self,
        context: MiddlewareContext[mt.ReadResourceRequestParams],
        call_next: CallNext[mt.ReadResourceRequestParams, Any]
    ) -> Any:
        uri = context.message.uri
        timestamp = datetime.now().isoformat()

        print(f"[{timestamp}] Resource accessed: {uri}")

        return await call_next(context)

    async def on_get_prompt(
        self,
        context: MiddlewareContext[mt.GetPromptRequestParams],
        call_next: CallNext[mt.GetPromptRequestParams, Any]
    ) -> Any:
        prompt_name = context.message.name
        timestamp = datetime.now().isoformat()

        print(f"[{timestamp}] Prompt requested: {prompt_name}")

        return await call_next(context)
`;
}

function generateAuthMiddleware(): string {
  return `"""
Simple Authentication Middleware - Demonstrates auth pattern
"""
from typing import Any
from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
import mcp.types as mt


class SimpleAuthMiddleware(Middleware):
    """Simple API key authentication middleware (demo only)."""

    def __init__(self, enabled: bool = False, api_key: str | None = None):
        self.enabled = enabled
        self.api_key = api_key or "demo-api-key-12345"

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, Any]
    ) -> Any:
        if self.enabled:
            # In a real implementation, check request headers for API key
            # For demo, we'll just log that auth check happened
            print(f"[AUTH] Checking authentication for tool: {context.message.name}")

        return await call_next(context)
`;
}

function generateSampleData(): string {
  return `{
  "example": "This is a sample JSON file",
  "purpose": "Demonstrates file resources in MCP",
  "data": [
    {"id": 1, "value": "First item"},
    {"id": 2, "value": "Second item"},
    {"id": 3, "value": "Third item"}
  ]
}
`;
}
