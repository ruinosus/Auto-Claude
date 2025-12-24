import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Plus, Edit, Trash2 } from 'lucide-react';
import type { FastMCPTool } from '../../../../shared/types/mcp';

interface ToolCustomizerProps {
  tools: FastMCPTool[];
  onToolsChange: (tools: FastMCPTool[]) => void;
  onAddTool: () => void;
  onEditTool: (index: number) => void;
  onNext: () => void;
  onBack: () => void;
}

export function ToolCustomizer({
  tools,
  onToolsChange,
  onAddTool,
  onEditTool,
  onNext,
  onBack
}: ToolCustomizerProps) {
  const handleRemoveTool = (index: number) => {
    const newTools = tools.filter((_, i) => i !== index);
    onToolsChange(newTools);
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Customize Tools</h3>
        <p className="text-sm text-muted-foreground">
          Add, edit, or remove tools for your FastMCP server
        </p>
      </div>

      {/* Tools List */}
      <div className="space-y-3">
        {tools.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <p className="text-muted-foreground">
                  No tools defined yet. Click "Add Tool" to get started.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          tools.map((tool, index) => (
            <Card key={index}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base">{tool.name}</CardTitle>
                    <CardDescription className="mt-1">
                      {tool.description}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onEditTool(index)}
                      aria-label={`Edit ${tool.name}`}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveTool(index)}
                      aria-label={`Remove ${tool.name}`}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-xs text-muted-foreground">
                  {tool.parameters.length} {tool.parameters.length === 1 ? 'parameter' : 'parameters'}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Add Tool Button */}
      <Button
        variant="outline"
        onClick={onAddTool}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Tool
      </Button>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext}>
          Next
        </Button>
      </div>
    </div>
  );
}
