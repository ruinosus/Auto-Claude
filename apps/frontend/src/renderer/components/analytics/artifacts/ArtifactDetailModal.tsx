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
  Loader2
} from 'lucide-react';
import type { LocalArtifact } from '../../../../shared/types/analytics-v2';
import { formatCurrency } from '../utils/formatters';

interface ArtifactDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  artifactId: string;
  // Optional: pass artifact data directly if already loaded
  initialArtifact?: Partial<LocalArtifact>;
}

export function ArtifactDetailModal({
  isOpen,
  onClose,
  projectId,
  artifactId,
  initialArtifact
}: ArtifactDetailModalProps) {
  const { t } = useTranslation(['analytics']);
  const [artifact, setArtifact] = useState<LocalArtifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

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
            setArtifact(result.data);
            return;
          }
        }

        // Fall back to initialArtifact (preview from API)
        if (initialArtifact) {
          setArtifact({
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
          });
        } else {
          setError('No artifact data available');
        }
      } catch (err) {
        console.error('[ArtifactDetailModal] Failed to load artifact:', err);
        // On error, still try to show initialArtifact
        if (initialArtifact) {
          setArtifact({
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
          });
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
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 text-purple-400 animate-spin" />
              <span className="ml-3 text-gray-400">Loading artifact...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-3 p-4 bg-red-500/10 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
              <div>
                <p className="text-red-400 font-medium">Failed to load artifact</p>
                <p className="text-red-300 text-sm mt-1">{error}</p>
              </div>
            </div>
          ) : artifact ? (
            <div className="space-y-4">
              {/* Metadata bar */}
              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
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

                {artifact.session_num !== undefined && (
                  <div className="flex items-center gap-1 text-gray-500">
                    Session #{artifact.session_num}
                  </div>
                )}
              </div>

              {/* Full content */}
              <div className="bg-[#0f0f1a] rounded-lg overflow-hidden">
                {isCodeContent(artifact) ? (
                  <pre className="p-4 text-sm text-gray-200 font-mono overflow-x-auto whitespace-pre-wrap break-words">
                    {artifact.content}
                  </pre>
                ) : (
                  <div className="p-4 text-gray-200 whitespace-pre-wrap break-words leading-relaxed">
                    {artifact.content}
                  </div>
                )}
              </div>

              {/* Additional metadata */}
              {artifact.metadata && Object.keys(artifact.metadata).length > 0 && (
                <div className="border-t border-gray-700 pt-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Additional Metadata</h3>
                  <pre className="text-xs text-gray-500 bg-gray-900 rounded p-3 overflow-x-auto">
                    {JSON.stringify(artifact.metadata, null, 2)}
                  </pre>
                </div>
              )}

              {/* Trace link */}
              {artifact.trace_id && (
                <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-700">
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
          ) : null}
        </div>
      </div>
    </div>
  );
}
