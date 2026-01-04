import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Copy,
  Check,
  Clock,
  DollarSign,
  Hash,
  FileText,
  AlertCircle,
  Loader2,
  Download,
  Code,
  Tag,
  CheckCircle
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { LocalArtifact, RichLocalArtifact } from '../../../../shared/types/analytics-v2';
import { formatCurrency } from '../utils/formatters';
import { MarkdownPreview } from './MarkdownPreview';
import { MermaidPreview } from './MermaidPreview';
import { ArtifactMetadataPanel } from './ArtifactMetadataPanel';

// Custom dark theme matching the UI background (#0f0f1a)
const customDarkTheme: { [key: string]: React.CSSProperties } = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...(oneDark['pre[class*="language-"]'] as React.CSSProperties),
    background: '#0f0f1a',
    margin: 0,
    padding: '1rem',
    fontSize: '0.875rem',
    lineHeight: '1.5',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  'code[class*="language-"]': {
    ...(oneDark['code[class*="language-"]'] as React.CSSProperties),
    background: '#0f0f1a',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
};

// Map artifact formats to syntax highlighter language identifiers
const getLanguageFromFormat = (format?: string): string => {
  const languageMap: Record<string, string> = {
    typescript: 'typescript',
    javascript: 'javascript',
    python: 'python',
    json: 'json',
    diff: 'diff',
    mermaid: 'markdown',
    code: 'typescript', // Default code to typescript
  };
  return format ? languageMap[format] || 'text' : 'text';
};

interface ArtifactDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  artifactId: string;
  // Optional: pass artifact data directly if already loaded
  initialArtifact?: Partial<LocalArtifact>;
}

type TabType = 'content' | 'metadata' | 'raw';

export function ArtifactDetailModal({
  isOpen,
  onClose,
  projectId,
  artifactId,
  initialArtifact
}: ArtifactDetailModalProps) {
  const { t } = useTranslation(['analytics']);
  const [artifact, setArtifact] = useState<RichLocalArtifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('content');

  useEffect(() => {
    if (!isOpen || !artifactId) return;

    async function loadArtifact() {
      try {
        setLoading(true);
        setError(null);

        // If we have projectId, try to load full content from local storage
        if (projectId && window.electronAPI?.artifact?.get) {
          const result = await window.electronAPI.artifact.get(projectId, artifactId);

          if (result.success && result.data) {
            // Convert to RichLocalArtifact format (data may have optional rich fields)
            const data = result.data as RichLocalArtifact;
            const richArtifact: RichLocalArtifact = {
              ...data,
              metadata: data.metadata || {},
              rationale: data.rationale,
              acceptance_criteria: data.acceptance_criteria || [],
              user_stories: data.user_stories || [],
              dependencies: data.dependencies || [],
            };
            setArtifact(richArtifact);
            return;
          }
        }

        // Fall back to initialArtifact (preview from API)
        if (initialArtifact) {
          const richArtifact: RichLocalArtifact = {
            id: artifactId,
            type: initialArtifact.type || 'unknown',
            content: initialArtifact.content || '(Content preview)',
            value_usd: initialArtifact.value_usd || 0,
            description: initialArtifact.description,
            format: initialArtifact.format,
            created_at: initialArtifact.created_at || new Date().toISOString(),
            trace_id: initialArtifact.trace_id,
            spec_id: initialArtifact.spec_id,
            agent_type: initialArtifact.agent_type,
            metadata: (initialArtifact as any).metadata || {},
            rationale: (initialArtifact as any).rationale,
            acceptance_criteria: (initialArtifact as any).acceptance_criteria || [],
            user_stories: (initialArtifact as any).user_stories || [],
            dependencies: (initialArtifact as any).dependencies || [],
          };
          setArtifact(richArtifact);
        } else {
          setError('No artifact data available');
        }
      } catch (err) {
        console.error('[ArtifactDetailModal] Failed to load artifact:', err);
        // On error, still try to show initialArtifact
        if (initialArtifact) {
          const richArtifact: RichLocalArtifact = {
            id: artifactId,
            type: initialArtifact.type || 'unknown',
            content: initialArtifact.content || '(Content preview)',
            value_usd: initialArtifact.value_usd || 0,
            description: initialArtifact.description,
            format: initialArtifact.format,
            created_at: initialArtifact.created_at || new Date().toISOString(),
            trace_id: initialArtifact.trace_id,
            spec_id: initialArtifact.spec_id,
            agent_type: initialArtifact.agent_type,
            metadata: (initialArtifact as any).metadata || {},
            rationale: (initialArtifact as any).rationale,
            acceptance_criteria: (initialArtifact as any).acceptance_criteria || [],
            user_stories: (initialArtifact as any).user_stories || [],
            dependencies: (initialArtifact as any).dependencies || [],
          };
          setArtifact(richArtifact);
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load artifact');
        }
      } finally {
        setLoading(false);
      }
    }

    loadArtifact();
  }, [isOpen, projectId, artifactId, initialArtifact]);

  const handleCopy = async () => {
    if (!artifact?.content) return;

    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const getFileExtension = (format?: string): string => {
    switch (format) {
      case 'typescript':
        return 'ts';
      case 'javascript':
        return 'js';
      case 'python':
        return 'py';
      case 'json':
        return 'json';
      case 'mermaid':
        return 'mmd';
      case 'diff':
        return 'diff';
      case 'markdown':
        return 'md';
      default:
        return 'txt';
    }
  };

  const handleDownload = () => {
    if (!artifact?.content) return;

    const ext = getFileExtension(artifact.format);
    const filename = `${artifact.type}_${artifact.id.slice(0, 8)}.${ext}`;

    const blob = new Blob([artifact.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getTypeLabel = (type: string) => {
    // Convert snake_case to Title Case
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const isCodeContent = (artifact: LocalArtifact) => {
    const codeFormats = ['code', 'json', 'typescript', 'javascript', 'python', 'diff'];
    const codeTypes = ['code_example', 'code_implementation', 'code_suggestion', 'code_choice', 'fix_applied'];
    return codeFormats.includes(artifact.format || '') || codeTypes.includes(artifact.type);
  };

  const isMarkdownContent = (artifact: LocalArtifact) => {
    return artifact.format === 'markdown' || artifact.type === 'documentation';
  };

  const isMermaidContent = (artifact: LocalArtifact) => {
    return artifact.format === 'mermaid' || (artifact.type === 'diagram' && artifact.format === 'mermaid');
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#1e1e2e] rounded-lg shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-purple-400" />
            <div>
              <h2 className="text-lg font-semibold text-white">
                {artifact?.description || getTypeLabel(artifact?.type || 'artifact')}
              </h2>
              {artifact && (
                <p className="text-sm text-gray-400">
                  {getTypeLabel(artifact.type)} {artifact.format && `(${artifact.format})`}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={!artifact?.content}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-200 transition-colors disabled:opacity-50"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-green-400" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  <span>Copy</span>
                </>
              )}
            </button>

            <button
              onClick={handleDownload}
              disabled={!artifact?.content}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-200 transition-colors disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              <span>Download</span>
            </button>

            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64 p-4">
              <Loader2 className="h-8 w-8 text-purple-400 animate-spin" />
              <span className="ml-3 text-gray-400">Loading artifact...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-3 p-4 bg-red-500/10 rounded-lg m-4">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
              <div>
                <p className="text-red-400 font-medium">Failed to load artifact</p>
                <p className="text-red-300 text-sm mt-1">{error}</p>
              </div>
            </div>
          ) : artifact ? (
            <div className="flex flex-col h-full">
              {/* Top metadata bar */}
              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400 p-4 border-b border-gray-700">
                {artifact.value_usd > 0 && (
                  <div className="flex items-center gap-1">
                    <DollarSign className="h-4 w-4 text-emerald-400" />
                    <span className="text-emerald-400 font-medium">
                      {formatCurrency(artifact.value_usd)}
                    </span>
                  </div>
                )}

                {artifact.created_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    <span>{formatTimestamp(artifact.created_at)}</span>
                  </div>
                )}

                {artifact.spec_id && (
                  <div className="flex items-center gap-1">
                    <Hash className="h-4 w-4" />
                    <span>Spec: {artifact.spec_id}</span>
                  </div>
                )}

                {artifact.agent_type && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-purple-500/10 rounded text-purple-400">
                    {artifact.agent_type}
                  </div>
                )}

                {/* Quality badges */}
                {artifact.metadata?.has_rationale && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-green-500/10 rounded text-green-400 text-xs">
                    <CheckCircle className="h-3 w-3" />
                    Rationale
                  </div>
                )}
                {artifact.metadata?.has_acceptance_criteria && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-500/10 rounded text-blue-400 text-xs">
                    <CheckCircle className="h-3 w-3" />
                    AC
                  </div>
                )}
                {artifact.metadata?.priority && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-500/10 rounded text-orange-400 text-xs">
                    <Tag className="h-3 w-3" />
                    {artifact.metadata.priority}
                  </div>
                )}
              </div>

              {/* Tabs */}
              <div className="flex border-b border-gray-700">
                <button
                  onClick={() => setActiveTab('content')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'content'
                      ? 'text-blue-400 border-b-2 border-blue-400 -mb-px'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <FileText className="h-4 w-4" />
                  {t('analytics:artifacts.tabs.content')}
                </button>
                <button
                  onClick={() => setActiveTab('metadata')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'metadata'
                      ? 'text-blue-400 border-b-2 border-blue-400 -mb-px'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <Tag className="h-4 w-4" />
                  {t('analytics:artifacts.tabs.metadata')}
                </button>
                <button
                  onClick={() => setActiveTab('raw')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'raw'
                      ? 'text-blue-400 border-b-2 border-blue-400 -mb-px'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <Code className="h-4 w-4" />
                  {t('analytics:artifacts.tabs.raw')}
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-auto p-4">
                {activeTab === 'content' && (
                  <div className="space-y-4">
                    {/* Full content */}
                    <div className="bg-[#0f0f1a] rounded-lg overflow-hidden">
                      {isMermaidContent(artifact) ? (
                        <MermaidPreview content={artifact.content} />
                      ) : isMarkdownContent(artifact) ? (
                        <MarkdownPreview content={artifact.content} />
                      ) : isCodeContent(artifact) ? (
                        <SyntaxHighlighter
                          language={getLanguageFromFormat(artifact.format)}
                          style={customDarkTheme}
                          customStyle={{
                            background: '#0f0f1a',
                            margin: 0,
                            borderRadius: '0.5rem',
                          }}
                          wrapLines={true}
                          wrapLongLines={true}
                        >
                          {artifact.content}
                        </SyntaxHighlighter>
                      ) : (
                        <div className="p-4 text-gray-200 whitespace-pre-wrap break-words leading-relaxed">
                          {artifact.content}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'metadata' && (
                  <ArtifactMetadataPanel artifact={artifact} />
                )}

                {activeTab === 'raw' && (
                  <div className="space-y-4">
                    <pre className="text-xs text-gray-300 bg-gray-900 rounded p-4 overflow-x-auto">
                      {JSON.stringify(artifact, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Trace link */}
                {artifact.trace_id && (
                  <div className="flex items-center justify-between text-xs text-gray-500 pt-4 mt-4 border-t border-gray-700">
                    <span>
                      Artifact ID: <code className="text-gray-400">{artifact.id}</code>
                    </span>
                    <a
                      href={`http://localhost:3001/traces/${artifact.trace_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300"
                    >
                      View trace in Langfuse
                    </a>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
