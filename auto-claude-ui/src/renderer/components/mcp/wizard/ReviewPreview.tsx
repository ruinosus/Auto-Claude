import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { FileText, Code, Settings, ChevronDown, ChevronRight } from 'lucide-react';
import type { FastMCPServerConfig } from '../../../../shared/types/mcp';
import {
  generateServerPy,
  generatePyprojectToml,
  generateReadmeMd,
  generatePythonVersion,
} from '../../../lib/fastmcp-generator';

interface ReviewPreviewProps {
  config: FastMCPServerConfig;
  onGenerate: () => Promise<void>;
  onBack: () => void;
  isGenerating?: boolean;
}

interface FilePreview {
  filename: string;
  content: string;
  icon: typeof FileText;
  language: string;
}

export function ReviewPreview({
  config,
  onGenerate,
  onBack,
  isGenerating = false,
}: ReviewPreviewProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set(['server.py']));

  // Generate file previews using the generator functions
  const filePreviews: FilePreview[] = useMemo(
    () => [
      {
        filename: 'pyproject.toml',
        content: generatePyprojectToml(config),
        icon: Settings,
        language: 'toml',
      },
      {
        filename: 'server.py',
        content: generateServerPy(config),
        icon: Code,
        language: 'python',
      },
      {
        filename: '.python-version',
        content: generatePythonVersion(config.pythonVersion),
        icon: FileText,
        language: 'text',
      },
      {
        filename: 'README.md',
        content: generateReadmeMd(config),
        icon: FileText,
        language: 'markdown',
      },
    ],
    [config]
  );

  const toggleFile = (filename: string) => {
    setExpandedFiles((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(filename)) {
        newSet.delete(filename);
      } else {
        newSet.add(filename);
      }
      return newSet;
    });
  };

  const handleGenerate = async () => {
    await onGenerate();
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">Review & Preview</h3>
        <p className="text-sm text-muted-foreground">
          Review your server configuration before generating files
        </p>
      </div>

      {/* Server Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle>{config.serverName}</CardTitle>
          <CardDescription>{config.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Tools:</span>{' '}
              <span className="font-medium">
                {config.tools.length} {config.tools.length === 1 ? 'tool' : 'tools'}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Dependencies:</span>{' '}
              <span className="font-medium">
                {config.dependencies.length}{' '}
                {config.dependencies.length === 1 ? 'dependency' : 'dependencies'}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Python:</span>{' '}
              <span className="font-medium">{config.pythonVersion}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Directory:</span>{' '}
              <span className="font-medium text-xs">{config.workingDir}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* File Previews */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium">Generated Files</h4>
        {filePreviews.map((file) => {
          const Icon = file.icon;
          const isExpanded = expandedFiles.has(file.filename);

          return (
            <Card key={file.filename}>
              <CardHeader className="pb-3">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => toggleFile(file.filename)}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span className="font-mono text-sm font-medium">{file.filename}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              </CardHeader>
              {isExpanded && (
                <CardContent>
                  <pre className="bg-muted p-4 rounded-md overflow-x-auto text-xs">
                    <code>{file.content}</code>
                  </pre>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onBack} disabled={isGenerating}>
          Back
        </Button>
        <Button onClick={handleGenerate} disabled={isGenerating}>
          {isGenerating ? 'Generating...' : 'Generate & Save'}
        </Button>
      </div>
    </div>
  );
}
