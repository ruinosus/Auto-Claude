import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { AlertCircle, Maximize2, X } from 'lucide-react';

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#6366f1',
    primaryTextColor: '#fff',
    primaryBorderColor: '#4f46e5',
    lineColor: '#94a3b8',
    secondaryColor: '#1e293b',
    tertiaryColor: '#0f172a',
    background: '#1e1e2e',
    mainBkg: '#1e1e2e',
    nodeBorder: '#4f46e5',
    clusterBkg: '#1e293b',
    clusterBorder: '#334155',
    titleColor: '#f1f5f9',
    edgeLabelBackground: '#1e293b',
  },
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
  },
  securityLevel: 'loose',
});

interface MermaidPreviewProps {
  content: string;
  className?: string;
}

export function MermaidPreview({ content, className = '' }: MermaidPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [svgContent, setSvgContent] = useState<string>('');

  useEffect(() => {
    async function renderDiagram() {
      if (!containerRef.current || !content) return;

      try {
        setError(null);
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // Clean the content
        const cleanContent = content.trim();

        // Render the diagram
        const { svg } = await mermaid.render(id, cleanContent);
        setSvgContent(svg);

        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        console.error('Mermaid render error:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      }
    }

    renderDiagram();
  }, [content]);

  if (error) {
    return (
      <div className={`flex items-center gap-2 p-4 bg-red-500/10 rounded-lg text-red-400 ${className}`}>
        <AlertCircle className="h-5 w-5 flex-shrink-0" />
        <div>
          <p className="font-medium">Failed to render diagram</p>
          <p className="text-xs text-red-300 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`relative group ${className}`}>
        <div
          ref={containerRef}
          className="bg-[#0f0f1a] rounded-lg p-4 overflow-auto max-h-96"
        />
        <button
          onClick={() => setIsFullscreen(true)}
          className="absolute top-2 right-2 p-2 bg-gray-800/80 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-700"
          title="View fullscreen"
        >
          <Maximize2 className="h-4 w-4 text-gray-300" />
        </button>
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-8">
          <button
            onClick={() => setIsFullscreen(false)}
            className="absolute top-4 right-4 p-2 bg-gray-800 rounded-lg hover:bg-gray-700"
          >
            <X className="h-6 w-6 text-white" />
          </button>
          <div
            className="max-w-full max-h-full overflow-auto bg-[#0f0f1a] rounded-lg p-8"
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        </div>
      )}
    </>
  );
}
