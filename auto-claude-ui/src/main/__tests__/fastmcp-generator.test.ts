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
