/**
 * Type tests for MCP custom server configuration
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import type {
  CustomServerConfig,
  ProcessInfo,
  MCPServerExport
} from '../mcp';

describe('CustomServerConfig type', () => {
  it('should allow http configuration', () => {
    const config: CustomServerConfig = {
      connectionType: 'http',
      baseUrl: 'http://localhost:8000',
      authType: 'bearer',
      authValue: 'token123',
      headers: { 'X-Custom': 'value' }
    };
    expect(config.connectionType).toBe('http');
  });

  it('should allow stdio configuration', () => {
    const config: CustomServerConfig = {
      connectionType: 'stdio',
      command: 'python3',
      args: ['server.py'],
      workingDir: '/path/to/server',
      env: { PORT: '8000' }
    };
    expect(config.connectionType).toBe('stdio');
  });

  it('should allow sse configuration', () => {
    const config: CustomServerConfig = {
      connectionType: 'sse',
      baseUrl: 'http://localhost:8000/events',
      reconnectOnDisconnect: true,
      reconnectDelay: 5
    };
    expect(config.connectionType).toBe('sse');
  });
});

describe('ProcessInfo type', () => {
  it('should define process status correctly', () => {
    const info: ProcessInfo = {
      pid: 1234,
      status: 'running',
      uptime: 3600,
      startedAt: '2025-12-23T10:00:00Z'
    };
    expect(info.status).toBe('running');
  });
});
