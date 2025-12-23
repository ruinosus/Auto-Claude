import { useState } from 'react';
import { Button } from '../ui/button';
import type { MCPPrompt } from '../../../shared/types/mcp';

interface MCPPromptsListProps {
  prompts: MCPPrompt[];
}

export function MCPPromptsList({ prompts }: MCPPromptsListProps) {
  const [selectedPrompt, setSelectedPrompt] = useState<MCPPrompt | null>(null);

  if (prompts.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        No prompts available
      </div>
    );
  }

  return (
    <>
      <div className="space-y-2">
        {prompts.map(prompt => (
          <div key={prompt.name} className="border rounded p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="font-medium">{prompt.displayName}</div>
                <p className="text-sm text-muted-foreground">{prompt.description}</p>

                {prompt.arguments && prompt.arguments.length > 0 && (
                  <div className="mt-2 text-sm">
                    <span className="font-medium">Arguments: </span>
                    {prompt.arguments.map(arg => (
                      <span key={arg.name} className="mr-2">
                        <code>{arg.name}</code>
                        {arg.required && <span className="text-red-500">*</span>}
                      </span>
                    ))}
                  </div>
                )}

                {prompt.template && (
                  <div className="mt-2 text-xs text-muted-foreground font-mono bg-muted p-2 rounded">
                    {prompt.template.split('\n').slice(0, 3).join('\n')}
                    {prompt.template.split('\n').length > 3 && '\n...'}
                  </div>
                )}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedPrompt(prompt)}
              >
                Use this prompt →
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Prompt argument fill dialog would go here */}
    </>
  );
}
