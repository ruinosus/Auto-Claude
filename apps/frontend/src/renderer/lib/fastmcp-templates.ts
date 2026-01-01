/**
 * FastMCP Templates - Production-Ready
 * Following MCP Specification 2025-06-18 and FastMCP best practices
 *
 * Each template includes:
 * - Tools with proper annotations (readOnlyHint, destructiveHint, etc.)
 * - Resources for data access
 * - Prompts for common workflows
 * - Validation constraints
 * - Async support where appropriate
 *
 * Sources:
 * - https://gofastmcp.com/servers/tools
 * - https://modelcontextprotocol.io/specification/2025-06-18/server/tools
 * - https://thinhdanggroup.github.io/mcp-production-ready/
 */

import type { FastMCPTemplate } from '../../shared/types/mcp';

export const FASTMCP_TEMPLATES: FastMCPTemplate[] = [
  // ============================================================
  // FILE SYSTEM TEMPLATE - Production Ready
  // ============================================================
  {
    id: 'file-system',
    name: 'File System Tools',
    description: 'Read/write files, list directories, search content with proper error handling and security',
    icon: 'FolderOpen',
    tools: [
      {
        name: 'read_file',
        description: 'Read contents of a file with encoding support. Returns file content as text.',
        parameters: [
          {
            name: 'path',
            type: 'string',
            required: true,
            description: 'Absolute or relative file path to read',
            minLength: 1,
            maxLength: 4096
          },
          {
            name: 'encoding',
            type: 'string',
            required: false,
            default: 'utf-8',
            description: 'Text encoding (utf-8, latin-1, ascii)',
            enum: ['utf-8', 'latin-1', 'ascii', 'utf-16']
          }
        ],
        annotations: { readOnlyHint: true, idempotentHint: true },
        isAsync: true,
        returnType: 'str'
      },
      {
        name: 'write_file',
        description: 'Write content to a file. Creates parent directories if needed.',
        parameters: [
          {
            name: 'path',
            type: 'string',
            required: true,
            description: 'File path to write to',
            minLength: 1,
            maxLength: 4096
          },
          {
            name: 'content',
            type: 'string',
            required: true,
            description: 'Content to write'
          },
          {
            name: 'encoding',
            type: 'string',
            required: false,
            default: 'utf-8',
            description: 'Text encoding',
            enum: ['utf-8', 'latin-1', 'ascii']
          },
          {
            name: 'create_parents',
            type: 'boolean',
            required: false,
            default: true,
            description: 'Create parent directories if they do not exist'
          }
        ],
        annotations: { destructiveHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'list_directory',
        description: 'List files and directories with optional recursive traversal and filtering.',
        parameters: [
          {
            name: 'path',
            type: 'string',
            required: true,
            description: 'Directory path to list',
            minLength: 1
          },
          {
            name: 'recursive',
            type: 'boolean',
            required: false,
            default: false,
            description: 'Include subdirectories recursively'
          },
          {
            name: 'pattern',
            type: 'string',
            required: false,
            description: 'Glob pattern to filter files (e.g., "*.py", "**/*.json")'
          },
          {
            name: 'include_hidden',
            type: 'boolean',
            required: false,
            default: false,
            description: 'Include hidden files (starting with .)'
          }
        ],
        annotations: { readOnlyHint: true, idempotentHint: true },
        isAsync: true,
        returnType: 'list[dict[str, Any]]'
      },
      {
        name: 'search_files',
        description: 'Search for files matching pattern with content search support.',
        parameters: [
          {
            name: 'directory',
            type: 'string',
            required: true,
            description: 'Base directory to search in'
          },
          {
            name: 'pattern',
            type: 'string',
            required: true,
            description: 'Glob pattern for file names (e.g., "*.py")'
          },
          {
            name: 'content_pattern',
            type: 'string',
            required: false,
            description: 'Regex pattern to search within file contents'
          },
          {
            name: 'max_results',
            type: 'number',
            required: false,
            default: 100,
            description: 'Maximum number of results to return',
            minValue: 1,
            maxValue: 1000
          }
        ],
        annotations: { readOnlyHint: true },
        isAsync: true,
        returnType: 'list[dict[str, Any]]'
      },
      {
        name: 'delete_file',
        description: 'Delete a file or empty directory.',
        parameters: [
          {
            name: 'path',
            type: 'string',
            required: true,
            description: 'Path to file or directory to delete'
          },
          {
            name: 'force',
            type: 'boolean',
            required: false,
            default: false,
            description: 'Force delete non-empty directories'
          }
        ],
        annotations: { destructiveHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      }
    ],
    resources: [
      {
        uri: 'file://{path}',
        name: 'File Content',
        description: 'Access file contents by path',
        mimeType: 'text/plain',
        parameters: [
          { name: 'path', description: 'File path to read', required: true }
        ]
      },
      {
        uri: 'directory://{path}',
        name: 'Directory Listing',
        description: 'List contents of a directory',
        mimeType: 'application/json',
        parameters: [
          { name: 'path', description: 'Directory path', required: true }
        ]
      },
      {
        uri: 'data://file-stats',
        name: 'File Statistics',
        description: 'Server statistics: files processed, cache status',
        mimeType: 'application/json'
      }
    ],
    prompts: [
      {
        name: 'analyze_codebase',
        description: 'Analyze a codebase structure and provide insights',
        arguments: [
          { name: 'directory', description: 'Root directory to analyze', required: true },
          { name: 'focus', description: 'Specific aspect to focus on (structure, dependencies, patterns)', required: false }
        ]
      },
      {
        name: 'find_and_replace',
        description: 'Find and replace text across multiple files',
        arguments: [
          { name: 'directory', description: 'Directory to search', required: true },
          { name: 'find_pattern', description: 'Pattern to find', required: true },
          { name: 'replace_with', description: 'Replacement text', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=2.0.0', 'aiofiles>=23.0.0', 'pathspec>=0.11.0']
  },

  // ============================================================
  // API WRAPPER TEMPLATE - Production Ready
  // ============================================================
  {
    id: 'api-wrapper',
    name: 'API Wrapper',
    description: 'HTTP client with authentication, rate limiting, retries, and proper error handling',
    icon: 'Globe',
    tools: [
      {
        name: 'http_request',
        description: 'Make HTTP requests with full control over method, headers, body, and timeouts.',
        parameters: [
          {
            name: 'url',
            type: 'string',
            required: true,
            description: 'Full URL to request (must start with http:// or https://)',
            pattern: '^https?://.+'
          },
          {
            name: 'method',
            type: 'string',
            required: false,
            default: 'GET',
            description: 'HTTP method',
            enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
          },
          {
            name: 'headers',
            type: 'object',
            required: false,
            description: 'Request headers as key-value pairs'
          },
          {
            name: 'body',
            type: 'object',
            required: false,
            description: 'Request body (JSON serializable)'
          },
          {
            name: 'timeout',
            type: 'number',
            required: false,
            default: 30,
            description: 'Request timeout in seconds',
            minValue: 1,
            maxValue: 120
          },
          {
            name: 'follow_redirects',
            type: 'boolean',
            required: false,
            default: true,
            description: 'Follow HTTP redirects'
          }
        ],
        annotations: { openWorldHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'get_json',
        description: 'Fetch JSON data from a URL with automatic parsing.',
        parameters: [
          {
            name: 'url',
            type: 'string',
            required: true,
            description: 'URL to fetch JSON from',
            pattern: '^https?://.+'
          },
          {
            name: 'headers',
            type: 'object',
            required: false,
            description: 'Optional request headers'
          },
          {
            name: 'query_params',
            type: 'object',
            required: false,
            description: 'URL query parameters'
          }
        ],
        annotations: { readOnlyHint: true, openWorldHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'post_json',
        description: 'POST JSON data to a URL.',
        parameters: [
          {
            name: 'url',
            type: 'string',
            required: true,
            description: 'URL to post to',
            pattern: '^https?://.+'
          },
          {
            name: 'data',
            type: 'object',
            required: true,
            description: 'JSON data to send'
          },
          {
            name: 'headers',
            type: 'object',
            required: false,
            description: 'Optional request headers'
          }
        ],
        annotations: { openWorldHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'download_file',
        description: 'Download a file from URL to local path.',
        parameters: [
          {
            name: 'url',
            type: 'string',
            required: true,
            description: 'URL to download from',
            pattern: '^https?://.+'
          },
          {
            name: 'output_path',
            type: 'string',
            required: true,
            description: 'Local path to save file'
          },
          {
            name: 'overwrite',
            type: 'boolean',
            required: false,
            default: false,
            description: 'Overwrite if file exists'
          }
        ],
        annotations: { openWorldHint: true, destructiveHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      }
    ],
    resources: [
      {
        uri: 'api://{base_url}/health',
        name: 'API Health Check',
        description: 'Check if an API endpoint is reachable',
        mimeType: 'application/json',
        parameters: [
          { name: 'base_url', description: 'Base URL of the API', required: true }
        ]
      },
      {
        uri: 'data://request-stats',
        name: 'Request Statistics',
        description: 'Statistics about requests made: count, avg latency, error rate',
        mimeType: 'application/json'
      },
      {
        uri: 'data://rate-limit-status',
        name: 'Rate Limit Status',
        description: 'Current rate limiting status and remaining quota',
        mimeType: 'application/json'
      }
    ],
    prompts: [
      {
        name: 'explore_api',
        description: 'Explore an API by making requests and analyzing responses',
        arguments: [
          { name: 'base_url', description: 'Base URL of the API', required: true },
          { name: 'auth_header', description: 'Authorization header value', required: false }
        ]
      },
      {
        name: 'debug_request',
        description: 'Debug a failing HTTP request',
        arguments: [
          { name: 'url', description: 'URL that is failing', required: true },
          { name: 'error_message', description: 'Error message received', required: true }
        ]
      }
    ],
    dependencies: ['fastmcp>=2.0.0', 'httpx>=0.27.0', 'pydantic>=2.0.0', 'tenacity>=8.0.0']
  },

  // ============================================================
  // DATABASE TEMPLATE - Production Ready
  // ============================================================
  {
    id: 'database',
    name: 'Database Connector',
    description: 'SQL database tools with connection pooling, transactions, and parameterized queries',
    icon: 'Database',
    tools: [
      {
        name: 'execute_query',
        description: 'Execute a parameterized SQL query. Uses prepared statements to prevent SQL injection.',
        parameters: [
          {
            name: 'query',
            type: 'string',
            required: true,
            description: 'SQL query with $1, $2 placeholders for parameters',
            minLength: 1
          },
          {
            name: 'params',
            type: 'array',
            required: false,
            description: 'Query parameters (positional)'
          },
          {
            name: 'fetch_results',
            type: 'boolean',
            required: false,
            default: true,
            description: 'Fetch and return query results'
          },
          {
            name: 'timeout',
            type: 'number',
            required: false,
            default: 30,
            description: 'Query timeout in seconds',
            minValue: 1,
            maxValue: 300
          }
        ],
        annotations: { openWorldHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'fetch_rows',
        description: 'Fetch rows from a table with optional filtering and pagination.',
        parameters: [
          {
            name: 'table',
            type: 'string',
            required: true,
            description: 'Table name (will be escaped)',
            pattern: '^[a-zA-Z_][a-zA-Z0-9_]*$'
          },
          {
            name: 'columns',
            type: 'array',
            required: false,
            description: 'Columns to select (default: all)'
          },
          {
            name: 'where',
            type: 'object',
            required: false,
            description: 'WHERE conditions as key-value pairs'
          },
          {
            name: 'order_by',
            type: 'string',
            required: false,
            description: 'Column to order by'
          },
          {
            name: 'limit',
            type: 'number',
            required: false,
            default: 100,
            description: 'Maximum rows to return',
            minValue: 1,
            maxValue: 10000
          },
          {
            name: 'offset',
            type: 'number',
            required: false,
            default: 0,
            description: 'Number of rows to skip'
          }
        ],
        annotations: { readOnlyHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'insert_rows',
        description: 'Insert one or more rows into a table.',
        parameters: [
          {
            name: 'table',
            type: 'string',
            required: true,
            description: 'Table name',
            pattern: '^[a-zA-Z_][a-zA-Z0-9_]*$'
          },
          {
            name: 'rows',
            type: 'array',
            required: true,
            description: 'Array of row objects to insert'
          },
          {
            name: 'returning',
            type: 'array',
            required: false,
            description: 'Columns to return after insert'
          }
        ],
        annotations: { destructiveHint: false },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'update_rows',
        description: 'Update rows matching conditions.',
        parameters: [
          {
            name: 'table',
            type: 'string',
            required: true,
            description: 'Table name',
            pattern: '^[a-zA-Z_][a-zA-Z0-9_]*$'
          },
          {
            name: 'set_values',
            type: 'object',
            required: true,
            description: 'Column-value pairs to update'
          },
          {
            name: 'where',
            type: 'object',
            required: true,
            description: 'WHERE conditions (required for safety)'
          }
        ],
        annotations: { destructiveHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'delete_rows',
        description: 'Delete rows matching conditions.',
        parameters: [
          {
            name: 'table',
            type: 'string',
            required: true,
            description: 'Table name',
            pattern: '^[a-zA-Z_][a-zA-Z0-9_]*$'
          },
          {
            name: 'where',
            type: 'object',
            required: true,
            description: 'WHERE conditions (required for safety)'
          },
          {
            name: 'limit',
            type: 'number',
            required: false,
            description: 'Maximum rows to delete (safety limit)',
            maxValue: 1000
          }
        ],
        annotations: { destructiveHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      }
    ],
    resources: [
      {
        uri: 'schema://tables',
        name: 'Database Schema',
        description: 'List all tables and their columns',
        mimeType: 'application/json'
      },
      {
        uri: 'schema://table/{table_name}',
        name: 'Table Schema',
        description: 'Get schema for a specific table',
        mimeType: 'application/json',
        parameters: [
          { name: 'table_name', description: 'Name of the table', required: true }
        ]
      },
      {
        uri: 'data://connection-pool',
        name: 'Connection Pool Status',
        description: 'Database connection pool statistics',
        mimeType: 'application/json'
      }
    ],
    prompts: [
      {
        name: 'write_query',
        description: 'Help write a SQL query for a specific task',
        arguments: [
          { name: 'task', description: 'What you want to accomplish', required: true },
          { name: 'tables', description: 'Available tables (comma-separated)', required: false }
        ]
      },
      {
        name: 'optimize_query',
        description: 'Analyze and optimize a SQL query',
        arguments: [
          { name: 'query', description: 'SQL query to optimize', required: true }
        ]
      },
      {
        name: 'explain_schema',
        description: 'Explain database schema and relationships',
        arguments: [
          { name: 'focus', description: 'Specific table or area to focus on', required: false }
        ]
      }
    ],
    dependencies: [
      'fastmcp>=2.0.0',
      'sqlalchemy>=2.0.0',
      'asyncpg>=0.29.0',
      'pydantic>=2.0.0'
    ]
  },

  // ============================================================
  // COMPLETE SHOWCASE TEMPLATE - Already Production Ready
  // ============================================================
  {
    id: 'complete-showcase',
    name: 'Complete MCP Showcase',
    description: 'Comprehensive template demonstrating ALL FastMCP capabilities: tools, resources, prompts, middleware, and server composition',
    icon: 'Sparkles',
    tools: [
      {
        name: 'analyze_text',
        description: 'Analyze text with various operations (count_words, sentiment, summary)',
        parameters: [
          {
            name: 'text',
            type: 'string',
            required: true,
            description: 'Input text to analyze',
            minLength: 1,
            maxLength: 100000
          },
          {
            name: 'operation',
            type: 'string',
            required: true,
            description: 'Type of analysis',
            enum: ['count_words', 'sentiment', 'summary', 'keywords']
          }
        ],
        annotations: { readOnlyHint: true, idempotentHint: true },
        returnType: 'dict[str, Any]'
      },
      {
        name: 'fetch_data',
        description: 'Make HTTP requests to external APIs with timeout and error handling',
        parameters: [
          {
            name: 'url',
            type: 'string',
            required: true,
            description: 'Full URL to request',
            pattern: '^https?://.+'
          },
          {
            name: 'method',
            type: 'string',
            required: false,
            default: 'GET',
            description: 'HTTP method',
            enum: ['GET', 'POST']
          },
          {
            name: 'headers',
            type: 'object',
            required: false,
            description: 'Optional HTTP headers'
          },
          {
            name: 'body',
            type: 'object',
            required: false,
            description: 'Optional request body for POST'
          },
          {
            name: 'timeout',
            type: 'number',
            required: false,
            default: 30,
            description: 'Request timeout in seconds',
            minValue: 1,
            maxValue: 60
          }
        ],
        annotations: { readOnlyHint: true, openWorldHint: true },
        isAsync: true,
        returnType: 'dict[str, Any]'
      },
      {
        name: 'process_image',
        description: 'Process images with various operations',
        parameters: [
          {
            name: 'image_path',
            type: 'string',
            required: true,
            description: 'Path to image file'
          },
          {
            name: 'operation',
            type: 'string',
            required: true,
            description: 'Image operation',
            enum: ['resize', 'rotate', 'grayscale', 'blur', 'thumbnail']
          },
          {
            name: 'options',
            type: 'object',
            required: false,
            description: 'Operation-specific options (width, height, angle, etc.)'
          }
        ],
        annotations: { readOnlyHint: false },
        returnType: 'dict[str, Any]'
      },
      {
        name: 'read_pdf',
        description: 'Extract text from PDF files',
        parameters: [
          {
            name: 'file_path',
            type: 'string',
            required: true,
            description: 'Path to PDF file'
          },
          {
            name: 'page_range',
            type: 'string',
            required: false,
            default: 'all',
            description: 'Page range (e.g., "1-3", "1,3,5", or "all")'
          },
          {
            name: 'extract_images',
            type: 'boolean',
            required: false,
            default: false,
            description: 'Also extract embedded images'
          }
        ],
        annotations: { readOnlyHint: true, idempotentHint: true },
        returnType: 'dict[str, Any]'
      },
      {
        name: 'search_with_cursor',
        description: 'Search with cursor-based pagination (modern best practice)',
        parameters: [
          {
            name: 'query',
            type: 'string',
            required: true,
            description: 'Search query string',
            minLength: 1
          },
          {
            name: 'cursor',
            type: 'string',
            required: false,
            description: 'Continuation token from previous response'
          },
          {
            name: 'limit',
            type: 'number',
            required: false,
            default: 10,
            description: 'Maximum results per page',
            minValue: 1,
            maxValue: 100
          }
        ],
        annotations: { readOnlyHint: true, idempotentHint: true },
        returnType: 'dict[str, Any]'
      }
    ],
    resources: [
      {
        uri: 'data://config',
        name: 'Server Configuration',
        description: 'Current server configuration settings',
        mimeType: 'application/json'
      },
      {
        uri: 'data://stats',
        name: 'Server Statistics',
        description: 'Real-time server statistics (requests, latency, memory)',
        mimeType: 'application/json'
      },
      {
        uri: 'file://{path}',
        name: 'File Content',
        description: 'Read file content by path',
        mimeType: 'text/plain',
        parameters: [
          { name: 'path', description: 'File path', required: true }
        ]
      }
    ],
    prompts: [
      {
        name: 'code_review',
        description: 'Review code for quality, security, and best practices',
        arguments: [
          { name: 'code', description: 'Code to review', required: true },
          { name: 'language', description: 'Programming language', required: false }
        ]
      },
      {
        name: 'debug_issue',
        description: 'Help debug an issue with systematic approach',
        arguments: [
          { name: 'error_message', description: 'Error message or symptom', required: true },
          { name: 'context', description: 'Additional context about the issue', required: false }
        ]
      },
      {
        name: 'explain_concept',
        description: 'Explain a technical concept clearly',
        arguments: [
          { name: 'concept', description: 'Concept to explain', required: true },
          { name: 'audience', description: 'Target audience level (beginner, intermediate, expert)', required: false }
        ]
      }
    ],
    dependencies: [
      'fastmcp>=2.14.0',
      'httpx>=0.27.0',
      'pillow>=10.0.0',
      'pypdf>=5.1.0',
      'pydantic>=2.0.0',
      'pydantic-settings>=2.0.0',
      'psutil>=6.0.0'
    ]
  },

  // ============================================================
  // BLANK TEMPLATE
  // ============================================================
  {
    id: 'blank',
    name: 'Blank Template',
    description: 'Start from scratch with basic FastMCP structure and best practices setup',
    icon: 'FileCode',
    tools: [],
    resources: [
      {
        uri: 'data://status',
        name: 'Server Status',
        description: 'Basic server status information',
        mimeType: 'application/json'
      }
    ],
    prompts: [
      {
        name: 'help',
        description: 'Get help with using this MCP server',
        arguments: [
          { name: 'topic', description: 'Specific topic to get help with', required: false }
        ]
      }
    ],
    dependencies: ['fastmcp>=2.0.0', 'pydantic>=2.0.0']
  }
];

export function getTemplateById(id: string): FastMCPTemplate | undefined {
  return FASTMCP_TEMPLATES.find(t => t.id === id);
}
