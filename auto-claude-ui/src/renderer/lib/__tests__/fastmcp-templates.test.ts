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
