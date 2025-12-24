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
