import { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';
import { AlertCircle, Maximize2, X, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

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
  const fullscreenContainerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [svgContent, setSvgContent] = useState<string>('');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    setZoom(prev => Math.min(prev + 0.25, 4));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom(prev => Math.max(prev - 0.25, 0.25));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Mouse wheel zoom - using ref to attach non-passive listener
  const handleWheelRef = useCallback((e: WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(prev => Math.min(Math.max(prev + delta, 0.25), 4));
  }, []);

  // Attach wheel listener with passive: false
  useEffect(() => {
    const container = fullscreenContainerRef.current;
    if (container && isFullscreen) {
      container.addEventListener('wheel', handleWheelRef, { passive: false });
      return () => {
        container.removeEventListener('wheel', handleWheelRef);
      };
    }
  }, [isFullscreen, handleWheelRef]);

  // Pan/drag handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) { // Left click only
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Reset zoom when closing fullscreen
  const handleCloseFullscreen = useCallback(() => {
    setIsFullscreen(false);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

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
          className="bg-[#0f0f1a] rounded-lg p-4 overflow-auto max-h-[600px] min-h-[200px]"
          style={{
            // Allow diagram to scale properly within container
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        />
        <button
          onClick={() => setIsFullscreen(true)}
          className="absolute top-2 right-2 p-2 bg-gray-800/80 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-700 z-10"
          title="View fullscreen"
        >
          <Maximize2 className="h-4 w-4 text-gray-300" />
        </button>
      </div>

      {/* Fullscreen Modal with Zoom Controls */}
      {isFullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex flex-col"
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* Top toolbar */}
          <div className="flex items-center justify-between p-4 bg-gray-900/80">
            {/* Zoom controls */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleZoomOut}
                className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
                title="Zoom out"
              >
                <ZoomOut className="h-5 w-5 text-white" />
              </button>
              <span className="text-white text-sm font-medium min-w-[60px] text-center">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
                title="Zoom in"
              >
                <ZoomIn className="h-5 w-5 text-white" />
              </button>
              <button
                onClick={handleZoomReset}
                className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors ml-2"
                title="Reset zoom"
              >
                <RotateCcw className="h-5 w-5 text-white" />
              </button>
            </div>

            {/* Instructions */}
            <span className="text-gray-400 text-sm">
              Scroll to zoom • Drag to pan
            </span>

            {/* Close button */}
            <button
              onClick={handleCloseFullscreen}
              className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
              title="Close"
            >
              <X className="h-5 w-5 text-white" />
            </button>
          </div>

          {/* Diagram container with zoom/pan */}
          <div
            ref={fullscreenContainerRef}
            className="flex-1 overflow-hidden bg-[#0f0f1a] cursor-grab active:cursor-grabbing"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
          >
            <div
              className="w-full h-full flex items-center justify-center"
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                transformOrigin: 'center center',
                transition: isDragging ? 'none' : 'transform 0.1s ease-out',
              }}
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          </div>
        </div>
      )}
    </>
  );
}
