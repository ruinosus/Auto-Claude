import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Checkbox } from '../../ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Plus, Trash2 } from 'lucide-react';
import type { FastMCPTool, FastMCPToolParameter } from '../../../../shared/types/mcp';

interface ToolEditorDialogProps {
  open: boolean;
  tool?: FastMCPTool | null;
  onSave: (tool: FastMCPTool) => void;
  onCancel: () => void;
}

interface ValidationErrors {
  toolName?: string;
  description?: string;
  parameters?: Array<{
    name?: string;
    type?: string;
  }>;
}

const PARAMETER_TYPES = ['string', 'number', 'boolean', 'object', 'array'] as const;

function isPythonIdentifier(name: string): boolean {
  // Python identifier: starts with letter or underscore, contains only letters, digits, underscores
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

export function ToolEditorDialog({ open, tool, onSave, onCancel }: ToolEditorDialogProps) {
  const [toolName, setToolName] = useState('');
  const [description, setDescription] = useState('');
  const [parameters, setParameters] = useState<FastMCPToolParameter[]>([]);
  const [errors, setErrors] = useState<ValidationErrors>({});

  // Initialize form when tool changes
  useEffect(() => {
    if (tool) {
      setToolName(tool.name);
      setDescription(tool.description);
      setParameters(tool.parameters || []);
    } else {
      setToolName('');
      setDescription('');
      setParameters([]);
    }
    setErrors({});
  }, [tool, open]);

  const handleAddParameter = () => {
    setParameters([
      ...parameters,
      {
        name: '',
        type: 'string',
        required: false,
        description: ''
      }
    ]);
  };

  const handleRemoveParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };

  const handleParameterChange = (
    index: number,
    field: keyof FastMCPToolParameter,
    value: any
  ) => {
    const updated = [...parameters];
    updated[index] = { ...updated[index], [field]: value };
    setParameters(updated);
  };

  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {};

    // Validate tool name
    if (!toolName.trim()) {
      newErrors.toolName = 'Tool name is required';
    } else if (!isPythonIdentifier(toolName)) {
      newErrors.toolName = 'Tool name must be a valid Python identifier';
    }

    // Validate description
    if (!description.trim()) {
      newErrors.description = 'Description is required';
    }

    // Validate parameters
    const paramErrors: Array<{ name?: string; type?: string }> = [];
    parameters.forEach((param, index) => {
      const paramError: { name?: string; type?: string } = {};

      if (!param.name.trim()) {
        paramError.name = 'Parameter name is required';
      } else if (!isPythonIdentifier(param.name)) {
        paramError.name = 'Parameter name must be a valid Python identifier';
      }

      if (Object.keys(paramError).length > 0) {
        paramErrors[index] = paramError;
      }
    });

    if (paramErrors.length > 0) {
      newErrors.parameters = paramErrors;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateForm()) {
      const toolData: FastMCPTool = {
        name: toolName.trim(),
        description: description.trim(),
        parameters: parameters.map((p) => ({
          name: p.name.trim(),
          type: p.type,
          required: p.required,
          default: p.default,
          description: p.description?.trim()
        }))
      };
      onSave(toolData);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onCancel()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{tool ? 'Edit Tool' : 'Add Tool'}</DialogTitle>
          <DialogDescription>
            {tool
              ? 'Modify tool properties and parameters'
              : 'Define a new tool with its parameters'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Tool Name */}
          <div className="space-y-2">
            <Label htmlFor="tool-name">
              Tool Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="tool-name"
              value={toolName}
              onChange={(e) => setToolName(e.target.value)}
              placeholder="e.g., read_file"
              className={errors.toolName ? 'border-destructive' : ''}
            />
            {errors.toolName && (
              <p className="text-sm text-destructive">{errors.toolName}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Must be a valid Python identifier (letters, digits, underscores)
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="tool-description">
              Description <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="tool-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this tool does..."
              rows={3}
              className={errors.description ? 'border-destructive' : ''}
            />
            {errors.description && (
              <p className="text-sm text-destructive">{errors.description}</p>
            )}
          </div>

          {/* Parameters */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Parameters</Label>
              <Button variant="outline" size="sm" onClick={handleAddParameter}>
                <Plus className="h-4 w-4 mr-2" />
                Add Parameter
              </Button>
            </div>

            {parameters.length === 0 ? (
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No parameters defined. Click "Add Parameter" to add one.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {parameters.map((param, index) => (
                  <Card key={index}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          Parameter {index + 1}
                        </CardTitle>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveParameter(index)}
                          aria-label={`Remove parameter ${index + 1}`}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        {/* Parameter Name */}
                        <div className="space-y-2">
                          <Label htmlFor={`param-name-${index}`}>
                            Parameter Name <span className="text-destructive">*</span>
                          </Label>
                          <Input
                            id={`param-name-${index}`}
                            value={param.name}
                            onChange={(e) =>
                              handleParameterChange(index, 'name', e.target.value)
                            }
                            placeholder="e.g., file_path"
                            className={
                              errors.parameters?.[index]?.name ? 'border-destructive' : ''
                            }
                          />
                          {errors.parameters?.[index]?.name && (
                            <p className="text-xs text-destructive">
                              {errors.parameters[index].name}
                            </p>
                          )}
                        </div>

                        {/* Parameter Type */}
                        <div className="space-y-2">
                          <Label htmlFor={`param-type-${index}`}>Type</Label>
                          <Select
                            value={param.type}
                            onValueChange={(value) =>
                              handleParameterChange(
                                index,
                                'type',
                                value as FastMCPToolParameter['type']
                              )
                            }
                          >
                            <SelectTrigger id={`param-type-${index}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {PARAMETER_TYPES.map((type) => (
                                <SelectItem key={type} value={type}>
                                  {type}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* Parameter Description */}
                      <div className="space-y-2">
                        <Label htmlFor={`param-desc-${index}`}>Description (optional)</Label>
                        <Input
                          id={`param-desc-${index}`}
                          value={param.description || ''}
                          onChange={(e) =>
                            handleParameterChange(index, 'description', e.target.value)
                          }
                          placeholder="Describe this parameter..."
                        />
                      </div>

                      {/* Required Checkbox and Default Value */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="flex items-center space-x-2">
                          <Checkbox
                            id={`param-required-${index}`}
                            checked={param.required}
                            onCheckedChange={(checked) =>
                              handleParameterChange(index, 'required', checked)
                            }
                          />
                          <Label
                            htmlFor={`param-required-${index}`}
                            className="text-sm font-normal cursor-pointer"
                          >
                            Required
                          </Label>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor={`param-default-${index}`}>Default (optional)</Label>
                          <Input
                            id={`param-default-${index}`}
                            value={param.default || ''}
                            onChange={(e) =>
                              handleParameterChange(index, 'default', e.target.value)
                            }
                            placeholder="Default value..."
                            disabled={param.required}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
