import { useState } from 'react';
import { TemplateSelector } from './TemplateSelector';
import { ServerConfigForm } from './ServerConfigForm';
import { ToolCustomizer } from './ToolCustomizer';
import { DependencyManager } from './DependencyManager';
import { ReviewPreview } from './ReviewPreview';
import { ToolEditorDialog } from './ToolEditorDialog';
import { getTemplateById } from '../../../lib/fastmcp-templates';
import type { FastMCPServerConfig, FastMCPTool } from '../../../../shared/types/mcp';

interface FastMCPWizardProps {
  onComplete: (config: FastMCPServerConfig) => Promise<void>;
  onCancel: () => void;
}

type WizardStep = 1 | 2 | 3 | 4 | 5;

interface ServerConfigData {
  serverName: string;
  description: string;
  pythonVersion: '3.10' | '3.11' | '3.12' | '3.13';
  workingDir: string;
}

export function FastMCPWizard({ onComplete, onCancel }: FastMCPWizardProps) {
  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);

  // Config state accumulated from all steps
  const [serverConfig, setServerConfig] = useState<ServerConfigData>({
    serverName: '',
    description: '',
    pythonVersion: '3.12',
    workingDir: ''
  });
  const [tools, setTools] = useState<FastMCPTool[]>([]);
  const [dependencies, setDependencies] = useState<string[]>(['fastmcp>=0.1.0']);

  // Tool editor state
  const [isToolEditorOpen, setIsToolEditorOpen] = useState(false);
  const [editingToolIndex, setEditingToolIndex] = useState<number | null>(null);

  // Step 1: Template Selection
  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);

    // Load template data
    const template = getTemplateById(templateId);
    if (template) {
      setTools([...template.tools]);
      setDependencies([...template.dependencies]);
    }

    // Advance to step 2
    setCurrentStep(2);
  };

  // Step 2: Server Configuration
  const handleServerConfigNext = (data: ServerConfigData) => {
    setServerConfig(data);
    setCurrentStep(3);
  };

  const handleServerConfigBack = () => {
    setCurrentStep(1);
  };

  // Step 3: Tool Customization
  const handleToolsNext = () => {
    setCurrentStep(4);
  };

  const handleToolsBack = () => {
    setCurrentStep(2);
  };

  const handleAddTool = () => {
    setEditingToolIndex(null);
    setIsToolEditorOpen(true);
  };

  const handleEditTool = (index: number) => {
    setEditingToolIndex(index);
    setIsToolEditorOpen(true);
  };

  const handleToolSave = (tool: FastMCPTool) => {
    if (editingToolIndex !== null) {
      // Update existing tool
      const updatedTools = [...tools];
      updatedTools[editingToolIndex] = tool;
      setTools(updatedTools);
    } else {
      // Add new tool
      setTools([...tools, tool]);
    }
    setIsToolEditorOpen(false);
    setEditingToolIndex(null);
  };

  const handleToolEditorCancel = () => {
    setIsToolEditorOpen(false);
    setEditingToolIndex(null);
  };

  // Step 4: Dependency Management
  const handleDependenciesNext = () => {
    setCurrentStep(5);
  };

  const handleDependenciesBack = () => {
    setCurrentStep(3);
  };

  // Step 5: Review & Generate
  const handleReviewBack = () => {
    setCurrentStep(4);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);

    try {
      const finalConfig: FastMCPServerConfig = {
        templateId: selectedTemplateId,
        serverName: serverConfig.serverName,
        description: serverConfig.description,
        pythonVersion: serverConfig.pythonVersion,
        workingDir: serverConfig.workingDir,
        tools: tools,
        dependencies: dependencies
      };

      await onComplete(finalConfig);
    } catch (error) {
      console.error('Failed to generate server:', error);
      // Error should be handled by parent component
    } finally {
      setIsGenerating(false);
    }
  };

  // Build final config for preview
  const previewConfig: FastMCPServerConfig = {
    templateId: selectedTemplateId,
    serverName: serverConfig.serverName,
    description: serverConfig.description,
    pythonVersion: serverConfig.pythonVersion,
    workingDir: serverConfig.workingDir,
    tools: tools,
    dependencies: dependencies
  };

  return (
    <>
      {/* Step 1: Template Selection */}
      {currentStep === 1 && (
        <TemplateSelector
          onSelect={handleTemplateSelect}
          selectedId={selectedTemplateId}
        />
      )}

      {/* Step 2: Server Configuration */}
      {currentStep === 2 && (
        <ServerConfigForm
          onNext={handleServerConfigNext}
          onBack={handleServerConfigBack}
          initialData={serverConfig}
        />
      )}

      {/* Step 3: Tool Customization */}
      {currentStep === 3 && (
        <ToolCustomizer
          tools={tools}
          onToolsChange={setTools}
          onAddTool={handleAddTool}
          onEditTool={handleEditTool}
          onNext={handleToolsNext}
          onBack={handleToolsBack}
        />
      )}

      {/* Step 4: Dependency Management */}
      {currentStep === 4 && (
        <DependencyManager
          dependencies={dependencies}
          onDependenciesChange={setDependencies}
          onNext={handleDependenciesNext}
          onBack={handleDependenciesBack}
        />
      )}

      {/* Step 5: Review & Preview */}
      {currentStep === 5 && (
        <ReviewPreview
          config={previewConfig}
          onGenerate={handleGenerate}
          onBack={handleReviewBack}
          isGenerating={isGenerating}
        />
      )}

      {/* Tool Editor Dialog */}
      <ToolEditorDialog
        open={isToolEditorOpen}
        tool={editingToolIndex !== null ? tools[editingToolIndex] : null}
        onSave={handleToolSave}
        onCancel={handleToolEditorCancel}
      />
    </>
  );
}
