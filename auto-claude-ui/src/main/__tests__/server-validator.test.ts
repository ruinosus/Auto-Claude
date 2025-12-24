/**
 * Tests for FastMCP server configuration validation
 */

import { describe, it, expect } from 'vitest';
import {
  validateServerConfig,
  validateServerName,
  validateWorkingDirectory,
  validateToolName,
  validateDependencies,
  ValidationError
} from '../server-validator';
import type { FastMCPServerConfig } from '../../shared/types/mcp';

describe('server-validator', () => {
  const validConfig: FastMCPServerConfig = {
    templateId: 'file-system',
    serverName: 'my-server',
    description: 'Test server',
    pythonVersion: '3.12',
    workingDir: '/tmp/test-server',
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

  describe('validateServerName', () => {
    it('should accept valid server names', () => {
      expect(() => validateServerName('my-server')).not.toThrow();
      expect(() => validateServerName('test_server')).not.toThrow();
      expect(() => validateServerName('server123')).not.toThrow();
    });

    it('should reject empty server name', () => {
      expect(() => validateServerName('')).toThrow(ValidationError);
      expect(() => validateServerName('')).toThrow('Server name cannot be empty');
    });

    it('should reject server names with spaces', () => {
      expect(() => validateServerName('my server')).toThrow(ValidationError);
      expect(() => validateServerName('my server')).toThrow('spaces');
    });

    it('should reject server names with special characters', () => {
      expect(() => validateServerName('my-server!')).toThrow(ValidationError);
      expect(() => validateServerName('my@server')).toThrow(ValidationError);
    });

    it('should reject server names longer than 50 characters', () => {
      const longName = 'a'.repeat(51);
      expect(() => validateServerName(longName)).toThrow(ValidationError);
      expect(() => validateServerName(longName)).toThrow('50 characters');
    });
  });

  describe('validateWorkingDirectory', () => {
    it('should accept valid absolute paths', () => {
      expect(() => validateWorkingDirectory('/tmp/test')).not.toThrow();
      expect(() => validateWorkingDirectory('/home/user/projects/server')).not.toThrow();
    });

    it('should reject empty path', () => {
      expect(() => validateWorkingDirectory('')).toThrow(ValidationError);
      expect(() => validateWorkingDirectory('')).toThrow('Working directory cannot be empty');
    });

    it('should reject relative paths', () => {
      expect(() => validateWorkingDirectory('./relative')).toThrow(ValidationError);
      expect(() => validateWorkingDirectory('relative/path')).toThrow(ValidationError);
      expect(() => validateWorkingDirectory('./relative')).toThrow('absolute path');
    });

    it('should reject paths with invalid characters', () => {
      expect(() => validateWorkingDirectory('/tmp/test\0null')).toThrow(ValidationError);
    });
  });

  describe('validateToolName', () => {
    it('should accept valid Python identifiers', () => {
      expect(() => validateToolName('read_file')).not.toThrow();
      expect(() => validateToolName('get_data')).not.toThrow();
      expect(() => validateToolName('_private_tool')).not.toThrow();
    });

    it('should reject empty tool name', () => {
      expect(() => validateToolName('')).toThrow(ValidationError);
    });

    it('should reject tool names starting with numbers', () => {
      expect(() => validateToolName('1read_file')).toThrow(ValidationError);
    });

    it('should reject Python keywords', () => {
      expect(() => validateToolName('def')).toThrow(ValidationError);
      expect(() => validateToolName('class')).toThrow(ValidationError);
      expect(() => validateToolName('return')).toThrow(ValidationError);
    });

    it('should reject tool names with spaces or special characters', () => {
      expect(() => validateToolName('read file')).toThrow(ValidationError);
      expect(() => validateToolName('read-file')).toThrow(ValidationError);
    });
  });

  describe('validateDependencies', () => {
    it('should accept valid dependency specifications', () => {
      expect(() => validateDependencies(['fastmcp>=0.1.0'])).not.toThrow();
      expect(() => validateDependencies(['fastmcp>=0.1.0', 'requests>=2.0.0', 'httpx==0.25.0'])).not.toThrow();
    });

    it('should reject empty dependencies array', () => {
      expect(() => validateDependencies([])).toThrow(ValidationError);
      expect(() => validateDependencies([])).toThrow('fastmcp');
    });

    it('should reject dependencies without package name', () => {
      expect(() => validateDependencies(['>=0.1.0'])).toThrow(ValidationError);
    });

    it('should reject malformed version specifiers', () => {
      expect(() => validateDependencies(['fastmcp>==0.1.0'])).toThrow(ValidationError);
    });

    it('should require fastmcp dependency', () => {
      expect(() => validateDependencies(['requests>=2.0.0'])).toThrow(ValidationError);
      expect(() => validateDependencies(['requests>=2.0.0'])).toThrow('fastmcp');
    });
  });

  describe('validateServerConfig', () => {
    it('should accept valid configuration', () => {
      expect(() => validateServerConfig(validConfig)).not.toThrow();
    });

    it('should reject missing server name', () => {
      const invalid = { ...validConfig, serverName: '' };
      expect(() => validateServerConfig(invalid)).toThrow(ValidationError);
    });

    it('should reject invalid working directory', () => {
      const invalid = { ...validConfig, workingDir: './relative' };
      expect(() => validateServerConfig(invalid)).toThrow(ValidationError);
    });

    it('should reject invalid tool names', () => {
      const invalid = {
        ...validConfig,
        tools: [{ name: 'invalid-name', description: 'Test', parameters: [] }]
      };
      expect(() => validateServerConfig(invalid)).toThrow(ValidationError);
    });

    it('should reject duplicate tool names', () => {
      const invalid = {
        ...validConfig,
        tools: [
          { name: 'read_file', description: 'Read', parameters: [] },
          { name: 'read_file', description: 'Read again', parameters: [] }
        ]
      };
      expect(() => validateServerConfig(invalid)).toThrow(ValidationError);
      expect(() => validateServerConfig(invalid)).toThrow('Duplicate');
    });

    it('should reject invalid Python version', () => {
      const invalid = { ...validConfig, pythonVersion: '2.7' as any };
      expect(() => validateServerConfig(invalid)).toThrow(ValidationError);
    });

    it('should reject empty description', () => {
      const invalid = { ...validConfig, description: '' };
      expect(() => validateServerConfig(invalid)).toThrow(ValidationError);
    });
  });
});
