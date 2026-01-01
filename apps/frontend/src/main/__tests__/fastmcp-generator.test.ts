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
    expect(code).toContain('mcp = FastMCP("test-server"');
  });

  it('should generate ToolError import for production-ready code', () => {
    const code = generateServerPy(config);
    expect(code).toContain('from fastmcp.exceptions import ToolError');
  });

  it('should generate tools with decorators', () => {
    const code = generateServerPy(config);
    expect(code).toContain('@mcp.tool()');
    expect(code).toContain('def read_file(');
    expect(code).toContain('path: str');
    expect(code).toContain('Read a file');
  });

  it('should generate tool with annotations', () => {
    const configWithAnnotations: FastMCPServerConfig = {
      ...config,
      tools: [{
        name: 'read_file',
        description: 'Read a file',
        parameters: [{ name: 'path', type: 'string', required: true }],
        annotations: { readOnlyHint: true, destructiveHint: false }
      }]
    };
    const code = generateServerPy(configWithAnnotations);
    expect(code).toContain('@mcp.tool(annotations=');
    expect(code).toContain('"readOnlyHint": True');
    expect(code).toContain('"destructiveHint": False');
  });

  it('should generate async functions when isAsync is true', () => {
    const configWithAsync: FastMCPServerConfig = {
      ...config,
      tools: [{
        name: 'fetch_data',
        description: 'Fetch data',
        parameters: [{ name: 'url', type: 'string', required: true }],
        isAsync: true
      }]
    };
    const code = generateServerPy(configWithAsync);
    expect(code).toContain('async def fetch_data(');
  });

  it('should generate validation code for required string parameters', () => {
    const code = generateServerPy(config);
    expect(code).toContain('if not path or not path.strip():');
    expect(code).toContain('raise ToolError("path cannot be empty"');
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

  describe('Enum parameters with Literal type', () => {
    it('should generate Literal type for enum parameters', () => {
      const configWithEnum: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'process',
          description: 'Process data',
          parameters: [
            {
              name: 'operation',
              type: 'string',
              required: true,
              enum: ['read', 'write', 'delete']
            }
          ]
        }]
      };
      const code = generateServerPy(configWithEnum);
      expect(code).toContain('from typing import Literal');
      expect(code).toContain('Literal["read", "write", "delete"]');
    });
  });

  describe('Validation constraints', () => {
    it('should generate minLength validation', () => {
      const configWithMinLength: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'text', type: 'string', required: true, minLength: 3 }
          ]
        }]
      };
      const code = generateServerPy(configWithMinLength);
      expect(code).toContain('len(text) < 3');
      expect(code).toContain('must be at least 3 characters');
    });

    it('should generate maxValue validation for numbers', () => {
      const configWithMaxValue: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'timeout', type: 'number', required: false, maxValue: 60 }
          ]
        }]
      };
      const code = generateServerPy(configWithMaxValue);
      expect(code).toContain('timeout > 60');
      expect(code).toContain('cannot exceed 60');
    });

    it('should generate URL pattern validation', () => {
      const configWithPattern: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'fetch',
          description: 'Fetch URL',
          parameters: [
            { name: 'url', type: 'string', required: true, pattern: '^https?://.+' }
          ]
        }]
      };
      const code = generateServerPy(configWithPattern);
      expect(code).toContain("startswith(('http://', 'https://'))");
    });
  });

  describe('Resources generation', () => {
    it('should generate resource functions', () => {
      const configWithResources: FastMCPServerConfig = {
        ...config,
        resources: [
          {
            uri: 'data://config',
            name: 'Server Config',
            description: 'Get server configuration',
            mimeType: 'application/json'
          }
        ]
      };
      const code = generateServerPy(configWithResources);
      expect(code).toContain('@mcp.resource("data://config")');
      expect(code).toContain('def get_server_config()');
      expect(code).toContain('Get server configuration');
    });
  });

  describe('Prompts generation', () => {
    it('should generate prompt functions', () => {
      const configWithPrompts: FastMCPServerConfig = {
        ...config,
        prompts: [
          {
            name: 'analyze_code',
            description: 'Analyze code for issues',
            arguments: [
              { name: 'code', description: 'Code to analyze', required: true }
            ]
          }
        ]
      };
      const code = generateServerPy(configWithPrompts);
      expect(code).toContain('@mcp.prompt()');
      expect(code).toContain('def analyze_code(code: str)');
      expect(code).toContain('Analyze code for issues');
    });
  });

  describe('Python value conversion', () => {
    it('should convert boolean true to True', () => {
      const configWithBool: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'flag', type: 'boolean', required: false, default: true }
          ]
        }]
      };
      const code = generateServerPy(configWithBool);
      expect(code).toContain('flag: bool = True');
    });

    it('should convert boolean false to False', () => {
      const configWithBool: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'flag', type: 'boolean', required: false, default: false }
          ]
        }]
      };
      const code = generateServerPy(configWithBool);
      expect(code).toContain('flag: bool = False');
    });

    it('should handle optional parameters without default as None', () => {
      const configWithOptional: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'value', type: 'string', required: false }
          ]
        }]
      };
      const code = generateServerPy(configWithOptional);
      expect(code).toContain('value: str | None = None');
    });

    it('should handle string defaults with quotes', () => {
      const configWithString: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'value', type: 'string', required: false, default: 'default' }
          ]
        }]
      };
      const code = generateServerPy(configWithString);
      expect(code).toContain('value: str = "default"');
    });

    it('should handle number defaults', () => {
      const configWithNumber: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'count', type: 'number', required: false, default: 42 }
          ]
        }]
      };
      const code = generateServerPy(configWithNumber);
      expect(code).toContain('count: int = 42');
    });
  });

  describe('Security - Identifier validation', () => {
    it('should reject invalid tool names', () => {
      const configWithInvalidTool: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'invalid-name',  // Hyphens are not allowed
          description: 'Test',
          parameters: []
        }]
      };
      expect(() => generateServerPy(configWithInvalidTool)).toThrow('Invalid Python tool name');
    });

    it('should reject Python reserved keywords as tool names', () => {
      const configWithKeyword: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'def',  // Reserved keyword
          description: 'Test',
          parameters: []
        }]
      };
      expect(() => generateServerPy(configWithKeyword)).toThrow('reserved keyword');
    });

    it('should reject invalid parameter names', () => {
      const configWithInvalidParam: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: '123invalid', type: 'string', required: true }  // Cannot start with digit
          ]
        }]
      };
      expect(() => generateServerPy(configWithInvalidParam)).toThrow('Invalid Python parameter name');
    });

    it('should allow valid identifiers with underscores', () => {
      const configWithValidName: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'valid_function_name',
          description: 'Test',
          parameters: [
            { name: 'valid_param_name', type: 'string', required: true }
          ]
        }]
      };
      const code = generateServerPy(configWithValidName);
      expect(code).toContain('def valid_function_name(');
      expect(code).toContain('valid_param_name: str');
    });
  });

  describe('Security - String escaping', () => {
    it('should escape triple quotes in descriptions', () => {
      const configWithTripleQuotes: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'This is a """malicious""" description',
          parameters: []
        }]
      };
      const code = generateServerPy(configWithTripleQuotes);
      // Triple quotes should be escaped as \"\"\" in the output
      expect(code).toContain('\\\"\\\"\\\"malicious\\\"\\\"\\\"');
    });

    it('should escape backslashes in server name', () => {
      const configWithBackslash: FastMCPServerConfig = {
        ...config,
        serverName: 'test\\server'
      };
      const code = generateServerPy(configWithBackslash);
      expect(code).toContain('mcp = FastMCP("test\\\\server"');
    });

    it('should handle quotes in server name', () => {
      const configWithQuotes: FastMCPServerConfig = {
        ...config,
        serverName: 'test"server'
      };
      const code = generateServerPy(configWithQuotes);
      // Quotes should be escaped with backslash
      expect(code).toContain('mcp = FastMCP("test\\"server"');
    });
  });

  describe('Error handling', () => {
    it('should generate try-except blocks in tools', () => {
      const code = generateServerPy(config);
      expect(code).toContain('try:');
      expect(code).toContain('except Exception as e:');
      expect(code).toContain('raise ToolError(');
    });
  });
});
