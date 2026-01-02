import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Maximize2, X, Code, Eye } from 'lucide-react';

// Custom dark theme for code blocks inside markdown
const codeBlockTheme: { [key: string]: React.CSSProperties } = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...(oneDark['pre[class*="language-"]'] as React.CSSProperties),
    background: '#0a0a12',
    margin: '1rem 0',
    padding: '1rem',
    fontSize: '0.8rem',
    lineHeight: '1.5',
    borderRadius: '0.5rem',
  },
  'code[class*="language-"]': {
    ...(oneDark['code[class*="language-"]'] as React.CSSProperties),
    background: '#0a0a12',
  },
};

interface MarkdownPreviewProps {
  content: string;
  className?: string;
}

export function MarkdownPreview({ content, className = '' }: MarkdownPreviewProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const handleCloseFullscreen = useCallback(() => {
    setIsFullscreen(false);
  }, []);

  // Custom components for ReactMarkdown
  const markdownComponents = {
    // Safe link rendering
    a: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
      const isValidUrl = href && (
        href.startsWith('http://') ||
        href.startsWith('https://') ||
        href.startsWith('/') ||
        href.startsWith('#')
      );

      if (!isValidUrl) {
        return <span className="text-gray-400">{children}</span>;
      }

      const isExternal = href?.startsWith('http://') || href?.startsWith('https://');
      return (
        <a
          href={href}
          {...props}
          {...(isExternal && {
            target: '_blank',
            rel: 'noopener noreferrer',
          })}
          className="text-blue-400 hover:text-blue-300 hover:underline"
        >
          {children}
        </a>
      );
    },
    // Code blocks with syntax highlighting
    code: ({ className, children, ...props }: React.HTMLAttributes<HTMLElement> & { inline?: boolean }) => {
      const match = /language-(\w+)/.exec(className || '');
      const isInline = !match && typeof children === 'string' && !children.includes('\n');

      if (isInline) {
        return (
          <code className="bg-gray-800 text-pink-400 px-1.5 py-0.5 rounded text-sm" {...props}>
            {children}
          </code>
        );
      }

      return (
        <SyntaxHighlighter
          style={codeBlockTheme}
          language={match ? match[1] : 'text'}
          PreTag="div"
          customStyle={{
            background: '#0a0a12',
            borderRadius: '0.5rem',
            margin: '1rem 0',
          }}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      );
    },
    // Tables
    table: ({ children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) => (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border border-gray-700 rounded-lg" {...props}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
      <thead className="bg-gray-800" {...props}>{children}</thead>
    ),
    th: ({ children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
      <th className="px-4 py-2 text-left text-sm font-semibold text-gray-200 border-b border-gray-700" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
      <td className="px-4 py-2 text-sm text-gray-300 border-b border-gray-700/50" {...props}>
        {children}
      </td>
    ),
    // Blockquotes
    blockquote: ({ children, ...props }: React.BlockquoteHTMLAttributes<HTMLQuoteElement>) => (
      <blockquote
        className="border-l-4 border-purple-500 pl-4 my-4 italic text-gray-300 bg-purple-500/5 py-2 rounded-r"
        {...props}
      >
        {children}
      </blockquote>
    ),
    // Lists
    ul: ({ children, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
      <ul className="list-disc list-inside my-2 space-y-1 text-gray-300" {...props}>{children}</ul>
    ),
    ol: ({ children, ...props }: React.OlHTMLAttributes<HTMLOListElement>) => (
      <ol className="list-decimal list-inside my-2 space-y-1 text-gray-300" {...props}>{children}</ol>
    ),
    // Headings
    h1: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h1 className="text-2xl font-bold text-white mt-6 mb-3 pb-2 border-b border-gray-700" {...props}>{children}</h1>
    ),
    h2: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h2 className="text-xl font-semibold text-white mt-5 mb-2" {...props}>{children}</h2>
    ),
    h3: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h3 className="text-lg font-medium text-gray-100 mt-4 mb-2" {...props}>{children}</h3>
    ),
    h4: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h4 className="text-base font-medium text-gray-200 mt-3 mb-1" {...props}>{children}</h4>
    ),
    // Paragraphs
    p: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
      <p className="text-gray-300 my-2 leading-relaxed" {...props}>{children}</p>
    ),
    // Horizontal rule
    hr: ({ ...props }: React.HTMLAttributes<HTMLHRElement>) => (
      <hr className="my-6 border-gray-700" {...props} />
    ),
    // Strong/Bold
    strong: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
      <strong className="font-semibold text-white" {...props}>{children}</strong>
    ),
    // Emphasis/Italic
    em: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
      <em className="italic text-gray-200" {...props}>{children}</em>
    ),
  };

  const PreviewContent = () => (
    <div className="prose prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );

  const RawContent = () => (
    <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
      {content}
    </pre>
  );

  return (
    <>
      <div className={`relative group ${className}`}>
        <div className="bg-[#0f0f1a] rounded-lg p-4 overflow-auto max-h-[400px] min-h-[100px]">
          {showRaw ? <RawContent /> : <PreviewContent />}
        </div>

        {/* Toolbar */}
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
          <button
            onClick={() => setShowRaw(!showRaw)}
            className="p-2 bg-gray-800/80 rounded-lg hover:bg-gray-700"
            title={showRaw ? 'Show preview' : 'Show raw'}
          >
            {showRaw ? (
              <Eye className="h-4 w-4 text-gray-300" />
            ) : (
              <Code className="h-4 w-4 text-gray-300" />
            )}
          </button>
          <button
            onClick={() => setIsFullscreen(true)}
            className="p-2 bg-gray-800/80 rounded-lg hover:bg-gray-700"
            title="View fullscreen"
          >
            <Maximize2 className="h-4 w-4 text-gray-300" />
          </button>
        </div>
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col">
          {/* Top toolbar */}
          <div className="flex items-center justify-between p-4 bg-gray-900/80 border-b border-gray-700">
            <div className="flex items-center gap-4">
              <span className="text-white font-medium">Markdown Preview</span>
              <button
                onClick={() => setShowRaw(!showRaw)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${
                  showRaw
                    ? 'bg-gray-700 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {showRaw ? (
                  <>
                    <Code className="h-4 w-4" />
                    <span className="text-sm">Raw</span>
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4" />
                    <span className="text-sm">Preview</span>
                  </>
                )}
              </button>
            </div>

            <button
              onClick={handleCloseFullscreen}
              className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
              title="Close"
            >
              <X className="h-5 w-5 text-white" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto bg-[#0f0f1a] p-8">
            <div className="max-w-4xl mx-auto">
              {showRaw ? <RawContent /> : <PreviewContent />}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
