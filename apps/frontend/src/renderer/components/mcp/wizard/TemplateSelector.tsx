import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { FolderOpen, Globe, Database, FileCode } from 'lucide-react';
import { FASTMCP_TEMPLATES } from '../../../lib/fastmcp-templates';
import { cn } from '../../../lib/utils';

interface TemplateSelectorProps {
  onSelect: (templateId: string) => void;
  selectedId?: string;
}

const ICON_MAP = {
  'FolderOpen': FolderOpen,
  'Globe': Globe,
  'Database': Database,
  'FileCode': FileCode
};

export function TemplateSelector({ onSelect, selectedId }: TemplateSelectorProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Choose a Template</h3>
        <p className="text-sm text-muted-foreground">
          Select a starting point for your FastMCP server
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {FASTMCP_TEMPLATES.map((template) => {
          const IconComponent = ICON_MAP[template.icon as keyof typeof ICON_MAP];
          const isSelected = selectedId === template.id;

          return (
            <button
              key={template.id}
              onClick={() => onSelect(template.id)}
              className="text-left"
            >
              <Card className={cn(
                'cursor-pointer transition-colors hover:border-primary/50',
                isSelected && 'border-primary border-2'
              )}>
                <CardHeader>
                  <div className="flex items-start gap-3">
                    {IconComponent && (
                      <div className="p-2 rounded-lg bg-primary/10">
                        <IconComponent className="h-5 w-5 text-primary" />
                      </div>
                    )}
                    <div className="flex-1">
                      <CardTitle className="text-base">{template.name}</CardTitle>
                      <CardDescription className="mt-1">
                        {template.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground">
                    {template.tools.length > 0 ? (
                      <span>{template.tools.length} tools included</span>
                    ) : (
                      <span>Empty template</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </button>
          );
        })}
      </div>
    </div>
  );
}
