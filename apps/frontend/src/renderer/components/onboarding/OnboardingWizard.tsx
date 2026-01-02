import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Wand2 } from 'lucide-react';
import {
  FullScreenDialog,
  FullScreenDialogContent,
  FullScreenDialogHeader,
  FullScreenDialogBody,
  FullScreenDialogTitle,
  FullScreenDialogDescription
} from '../ui/full-screen-dialog';
import { ScrollArea } from '../ui/scroll-area';
import { WizardProgress, WizardStep } from './WizardProgress';
import { WelcomeStep } from './WelcomeStep';
import { AuthModeStep, AuthMode } from './AuthModeStep';
import { AuthChoiceStep } from './AuthChoiceStep';
import { OAuthStep } from './OAuthStep';
import { AzureFoundryStep } from './AzureFoundryStep';
import { ClaudeCodeStep } from './ClaudeCodeStep';
import { DevToolsStep } from './DevToolsStep';
import { GraphitiStep } from './GraphitiStep';
import { CompletionStep } from './CompletionStep';
import { useSettingsStore } from '../../stores/settings-store';

interface OnboardingWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenTaskCreator?: () => void;
  onOpenSettings?: () => void;
}

// Wizard step identifiers
type WizardStepId = 'welcome' | 'auth-mode' | 'auth-choice' | 'oauth' | 'azure-foundry' | 'auth-token' | 'claude-code' | 'devtools' | 'memory' | 'graphiti' | 'completion';

// Step configuration with translation keys
interface WizardStepConfig {
  id: WizardStepId;
  labelKey: string;
}

// Base steps always shown
const BASE_STEPS: WizardStepConfig[] = [
  { id: 'welcome', labelKey: 'steps.welcome' },
  { id: 'auth-mode', labelKey: 'steps.authMode' }
];

// Auth-specific steps based on selected mode
const AUTH_STEPS: Record<AuthMode, WizardStepConfig> = {
  'oauth': { id: 'oauth', labelKey: 'steps.auth' },
  'azure-foundry': { id: 'azure-foundry', labelKey: 'steps.azureFoundry' },
  'auth-token': { id: 'auth-token', labelKey: 'steps.authToken' }
};

// Alternative steps for auth-choice flow (from develop)
const WIZARD_STEPS: WizardStepConfig[] = [
  { id: 'welcome', labelKey: 'steps.welcome' },
  { id: 'auth-choice', labelKey: 'steps.authChoice' },
  { id: 'oauth', labelKey: 'steps.auth' },
  { id: 'claude-code', labelKey: 'steps.claudeCode' },
  { id: 'devtools', labelKey: 'steps.devtools' },
  { id: 'graphiti', labelKey: 'steps.memory' },
  { id: 'completion', labelKey: 'steps.done' }
];

// Final steps always shown
const FINAL_STEPS: WizardStepConfig[] = [
  { id: 'claude-code', labelKey: 'steps.claudeCode' },
  { id: 'devtools', labelKey: 'steps.devtools' },
  { id: 'graphiti', labelKey: 'steps.memory' },
  { id: 'completion', labelKey: 'steps.done' }
];

/**
 * Build dynamic wizard steps based on selected auth mode
 */
function buildWizardSteps(authMode: AuthMode | null): WizardStepConfig[] {
  if (!authMode) {
    // Before auth mode is selected, only show base steps
    return [...BASE_STEPS];
  }
  return [...BASE_STEPS, AUTH_STEPS[authMode], ...FINAL_STEPS];
}

/**
 * Main onboarding wizard component.
 * Provides a full-screen, multi-step wizard experience for new users
 * to configure their Auto Claude environment.
 *
 * Features:
 * - Step progress indicator
 * - Navigation between steps (next, back, skip)
 * - Persists completion state to settings
 * - Can be re-run from settings
 */
export function OnboardingWizard({
  open,
  onOpenChange,
  onOpenTaskCreator,
  onOpenSettings
}: OnboardingWizardProps) {
  const { t } = useTranslation('onboarding');
  const { updateSettings } = useSettingsStore();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStepId>>(new Set());
  const [selectedAuthMode, setSelectedAuthMode] = useState<AuthMode | null>(null);
  // Track if oauth step was bypassed (API key path chosen)
  const [oauthBypassed, setOauthBypassed] = useState(false);

  // Build dynamic wizard steps based on selected auth mode
  const wizardSteps = useMemo(() => buildWizardSteps(selectedAuthMode), [selectedAuthMode]);

  // Get current step ID
  const currentStepId = wizardSteps[currentStepIndex]?.id ?? 'welcome';

  // Build step data for progress indicator
  const steps: WizardStep[] = wizardSteps.map((step, index) => ({
    id: step.id,
    label: t(step.labelKey),
    completed: completedSteps.has(step.id) || index < currentStepIndex
  }));

  // Navigation handlers
  const goToNextStep = useCallback(() => {
    // Mark current step as completed
    setCompletedSteps(prev => new Set(prev).add(currentStepId));

    // If leaving auth-choice, reset oauth bypassed flag
    if (currentStepId === 'auth-choice') {
      setOauthBypassed(false);
    }

    if (currentStepIndex < wizardSteps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  }, [currentStepIndex, currentStepId, wizardSteps.length]);

  // Handle auth mode selection and advance to next step
  const handleAuthModeSelect = useCallback((mode: AuthMode) => {
    setSelectedAuthMode(mode);
    // Mark auth-mode step as completed and advance
    setCompletedSteps(prev => new Set(prev).add('auth-mode'));
    setCurrentStepIndex(prev => prev + 1);
  }, []);

  const goToPreviousStep = useCallback(() => {
    // If going back from graphiti and oauth was bypassed, go back to auth-choice (skip oauth)
    if (currentStepId === 'graphiti' && oauthBypassed) {
      // Find index of auth-choice step
      const authChoiceIndex = WIZARD_STEPS.findIndex(step => step.id === 'auth-choice');
      setCurrentStepIndex(authChoiceIndex);
      setOauthBypassed(false);
      return;
    }

    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  }, [currentStepIndex, currentStepId, oauthBypassed]);

  // Handler for when API key path is chosen - skips oauth step
  const handleSkipToGraphiti = useCallback(() => {
    setOauthBypassed(true);
    setCompletedSteps(prev => new Set(prev).add('auth-choice'));

    // Find index of graphiti step
    const graphitiIndex = WIZARD_STEPS.findIndex(step => step.id === 'graphiti');
    setCurrentStepIndex(graphitiIndex);
  }, []);

  // Reset wizard state (for re-running) - defined before skipWizard/finishWizard that use it
  const resetWizard = useCallback(() => {
    setCurrentStepIndex(0);
    setCompletedSteps(new Set());
    setSelectedAuthMode(null);
    setOauthBypassed(false);
  }, []);

  const skipWizard = useCallback(async () => {
    // Mark onboarding as completed and close - save to disk AND update local state
    try {
      const result = await window.electronAPI.saveSettings({ onboardingCompleted: true });
      if (!result?.success) {
        console.error('Failed to save onboarding completion:', result?.error);
      }
    } catch (err) {
      console.error('Error saving onboarding completion:', err);
    }
    updateSettings({ onboardingCompleted: true });
    onOpenChange(false);
    resetWizard();
  }, [updateSettings, onOpenChange, resetWizard]);

  const finishWizard = useCallback(async () => {
    // Mark onboarding as completed - save to disk AND update local state
    try {
      const result = await window.electronAPI.saveSettings({ onboardingCompleted: true });
      if (!result?.success) {
        console.error('Failed to save onboarding completion:', result?.error);
      }
    } catch (err) {
      console.error('Error saving onboarding completion:', err);
    }
    updateSettings({ onboardingCompleted: true });
    onOpenChange(false);
    resetWizard();
  }, [updateSettings, onOpenChange, resetWizard]);

  // Handle opening task creator from within wizard
  const handleOpenTaskCreator = useCallback(() => {
    if (onOpenTaskCreator) {
      // Close wizard first, then open task creator
      onOpenChange(false);
      onOpenTaskCreator();
    }
  }, [onOpenTaskCreator, onOpenChange]);

  // Handle opening settings from completion step
  const handleOpenSettings = useCallback(() => {
    if (onOpenSettings) {
      // Finish wizard first, then open settings
      finishWizard();
      onOpenSettings();
    }
  }, [onOpenSettings, finishWizard]);

  // Render current step content
  const renderStepContent = () => {
    switch (currentStepId) {
      case 'welcome':
        return (
          <WelcomeStep
            onGetStarted={goToNextStep}
            onSkip={skipWizard}
          />
        );
      case 'auth-mode':
        return (
          <AuthModeStep
            onNext={handleAuthModeSelect}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
            selectedMode={selectedAuthMode ?? undefined}
          />
        );
      case 'auth-choice':
        return (
          <AuthChoiceStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
            onAPIKeyPathComplete={handleSkipToGraphiti}
          />
        );
      case 'oauth':
        return (
          <OAuthStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
          />
        );
      case 'azure-foundry':
        return (
          <AzureFoundryStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
          />
        );
      case 'auth-token':
        // TODO: Create AuthTokenStep component
        // For now, skip to next step
        return (
          <div className="flex h-full flex-col items-center justify-center px-8 py-6">
            <p className="text-muted-foreground">
              Auth Token configuration coming soon. Click Continue to proceed.
            </p>
            <button
              onClick={goToNextStep}
              className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded"
            >
              Continue
            </button>
          </div>
        );
      case 'claude-code':
        return (
          <ClaudeCodeStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
          />
        );
      case 'devtools':
        return (
          <DevToolsStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
          />
        );
      case 'graphiti':
        return (
          <GraphitiStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
          />
        );
      case 'completion':
        return (
          <CompletionStep
            onFinish={finishWizard}
            onOpenTaskCreator={handleOpenTaskCreator}
            onOpenSettings={handleOpenSettings}
          />
        );
      default:
        return null;
    }
  };

  // Handle dialog close - ask for confirmation if not completed
  const handleOpenChange = useCallback((newOpen: boolean) => {
    if (!newOpen) {
      // If closing before completion, skip the wizard
      skipWizard();
    } else {
      onOpenChange(newOpen);
    }
  }, [skipWizard, onOpenChange]);

  return (
    <FullScreenDialog open={open} onOpenChange={handleOpenChange}>
      <FullScreenDialogContent>
        <FullScreenDialogHeader>
          <FullScreenDialogTitle className="flex items-center gap-3">
            <Wand2 className="h-6 w-6" />
            {t('wizard.title')}
          </FullScreenDialogTitle>
          <FullScreenDialogDescription>
            {t('wizard.description')}
          </FullScreenDialogDescription>

          {/* Progress indicator - show for all steps except welcome and completion */}
          {currentStepId !== 'welcome' && currentStepId !== 'completion' && (
            <div className="mt-6">
              <WizardProgress currentStep={currentStepIndex} steps={steps} />
            </div>
          )}
        </FullScreenDialogHeader>

        <FullScreenDialogBody>
          <ScrollArea className="h-full">
            {renderStepContent()}
          </ScrollArea>
        </FullScreenDialogBody>
      </FullScreenDialogContent>
    </FullScreenDialog>
  );
}
