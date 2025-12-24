import type { FastMCPTemplate } from '../../shared/types/mcp';

export const FASTMCP_TEMPLATES: FastMCPTemplate[] = [
  {
    id: 'file-system',
    name: 'File System Tools',
    description: 'Read/write files, list directories, search content',
    icon: 'FolderOpen',
    tools: [
      {
        name: 'read_file',
        description: 'Read contents of a file',
        parameters: [
          { name: 'path', type: 'string', required: true, description: 'File path to read' },
          { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
        ]
      },
      {
        name: 'write_file',
        description: 'Write content to a file',
        parameters: [
          { name: 'path', type: 'string', required: true },
          { name: 'content', type: 'string', required: true },
          { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
        ]
      },
      {
        name: 'list_directory',
        description: 'List files in a directory',
        parameters: [
          { name: 'path', type: 'string', required: true },
          { name: 'recursive', type: 'boolean', required: false, default: false }
        ]
      },
      {
        name: 'search_files',
        description: 'Search for files matching pattern',
        parameters: [
          { name: 'directory', type: 'string', required: true },
          { name: 'pattern', type: 'string', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0']
  },

  {
    id: 'api-wrapper',
    name: 'API Wrapper',
    description: 'HTTP client with authentication and rate limiting',
    icon: 'Globe',
    tools: [
      {
        name: 'get_request',
        description: 'Make HTTP GET request',
        parameters: [
          { name: 'url', type: 'string', required: true },
          { name: 'headers', type: 'object', required: false }
        ]
      },
      {
        name: 'post_request',
        description: 'Make HTTP POST request',
        parameters: [
          { name: 'url', type: 'string', required: true },
          { name: 'body', type: 'object', required: true },
          { name: 'headers', type: 'object', required: false }
        ]
      },
      {
        name: 'put_request',
        description: 'Make HTTP PUT request',
        parameters: [
          { name: 'url', type: 'string', required: true },
          { name: 'body', type: 'object', required: true }
        ]
      },
      {
        name: 'delete_request',
        description: 'Make HTTP DELETE request',
        parameters: [
          { name: 'url', type: 'string', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0', 'httpx>=0.25.0', 'pydantic>=2.0.0']
  },

  {
    id: 'database',
    name: 'Database Connector',
    description: 'SQL/NoSQL query tools with connection pooling',
    icon: 'Database',
    tools: [
      {
        name: 'execute_query',
        description: 'Execute SQL query',
        parameters: [
          { name: 'query', type: 'string', required: true },
          { name: 'params', type: 'object', required: false }
        ]
      },
      {
        name: 'fetch_data',
        description: 'Fetch data from table',
        parameters: [
          { name: 'table', type: 'string', required: true },
          { name: 'where', type: 'object', required: false }
        ]
      },
      {
        name: 'insert_data',
        description: 'Insert data into table',
        parameters: [
          { name: 'table', type: 'string', required: true },
          { name: 'data', type: 'object', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=0.1.0', 'sqlalchemy>=2.0.0', 'asyncpg>=0.29.0']
  },

  {
    id: 'blank',
    name: 'Blank Template',
    description: 'Start from scratch with basic FastMCP structure',
    icon: 'FileCode',
    tools: [],
    dependencies: ['fastmcp>=0.1.0']
  }
];

export function getTemplateById(id: string): FastMCPTemplate | undefined {
  return FASTMCP_TEMPLATES.find(t => t.id === id);
}
