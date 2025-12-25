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

    it('should convert null to None', () => {
      const configWithNull: FastMCPServerConfig = {
        ...config,
        tools: [{
          name: 'test_func',
          description: 'Test',
          parameters: [
            { name: 'value', type: 'string', required: false, default: null }
          ]
        }]
      };
      const code = generateServerPy(configWithNull);
      expect(code).toContain('value: str = None');
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
      expect(code).toContain('def valid_function_name(valid_param_name: str):');
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
      expect(code).toContain('"""This is a \\\"\\\"\\\"malicious\\\"\\\"\\\" description"""');
      // Verify the function is properly closed and doesn't break out
      expect(code).toContain('# TODO: Implement test_func');
      expect(code).toContain('pass');
    });

    it('should escape backslashes in server name', () => {
      const configWithBackslash: FastMCPServerConfig = {
        ...config,
        serverName: 'test\\server'
      };
      const code = generateServerPy(configWithBackslash);
      expect(code).toContain('mcp = FastMCP("test\\\\server")');
    });

    it('should handle quotes in server name', () => {
      const configWithQuotes: FastMCPServerConfig = {
        ...config,
        serverName: 'test"server'
      };
      const code = generateServerPy(configWithQuotes);
      // Quotes should be escaped with backslash
      expect(code).toContain('mcp = FastMCP("test\\"server")');
    });
  });
});
