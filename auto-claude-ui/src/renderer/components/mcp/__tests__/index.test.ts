/**
 * Unit tests for MCP components index exports
 * Verifies all components are properly exported
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import * as MCPComponents from '../index';

describe('MCP Components - Exports', () => {
  it('exports all manager components', () => {
    expect(MCPComponents.MCPManager).toBeDefined();
    expect(MCPComponents.MCPServerCard).toBeDefined();
    expect(MCPComponents.MCPStatusIndicator).toBeDefined();
    expect(MCPComponents.MCPServerConfig).toBeDefined();
  });

  it('exports all capability view components', () => {
    expect(MCPComponents.MCPCapabilitiesView).toBeDefined();
    expect(MCPComponents.MCPToolsList).toBeDefined();
    expect(MCPComponents.MCPPromptsList).toBeDefined();
    expect(MCPComponents.MCPResourcesList).toBeDefined();
  });

  it('exports are functions/components', () => {
    expect(typeof MCPComponents.MCPManager).toBe('function');
    expect(typeof MCPComponents.MCPServerCard).toBe('function');
    expect(typeof MCPComponents.MCPStatusIndicator).toBe('function');
    expect(typeof MCPComponents.MCPServerConfig).toBe('function');
    expect(typeof MCPComponents.MCPCapabilitiesView).toBe('function');
    expect(typeof MCPComponents.MCPToolsList).toBe('function');
    expect(typeof MCPComponents.MCPPromptsList).toBe('function');
    expect(typeof MCPComponents.MCPResourcesList).toBe('function');
  });
});
