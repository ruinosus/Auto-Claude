import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  Cloud,
  Key,
  Users,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { cn } from '../../lib/utils';

export type AuthMode = 'oauth' | 'azure-foundry' | 'auth-token';

interface AuthModeStepProps {
  onNext: (mode: AuthMode) => void;
  onBack: () => void;
  onSkip: () => void;
  selectedMode?: AuthMode;
}

interface AuthModeOption {
  id: AuthMode;
  title: string;
  description: string;
  icon: React.ElementType;
  recommended?: boolean;
  enterprise?: boolean;
}

const AUTH_MODE_OPTIONS: AuthModeOption[] = [
  {
    id: 'oauth',
    title: 'Claude OAuth',
    description: 'Use your personal Claude account with OAuth authentication. Supports multiple accounts with automatic rate limit switching.',
    icon: Users,
    recommended: true
  },
  {
    id: 'azure-foundry',
    title: 'Azure Foundry',
    description: 'Use Azure OpenAI with Anthropic models via Azure Foundry. Requires API key and endpoint configuration.',
    icon: Cloud,
    enterprise: true
  },
  {
    id: 'auth-token',
    title: 'Auth Token',
    description: 'Use a direct Anthropic API token or proxy authentication. For CCR (Claude Code Router) or custom setups.',
    icon: Key,
    enterprise: true
  }
];

/**
 * Auth mode selection step for the onboarding wizard.
 * Allows users to choose their preferred authentication method before
 * being prompted for specific credentials.
 */
export function AuthModeStep({ onNext, onBack, onSkip, selectedMode }: AuthModeStepProps) {
  const { t } = useTranslation('onboarding');
  const [selected, setSelected] = useState<AuthMode | null>(selectedMode || null);

  const handleContinue = () => {
    if (selected) {
      onNext(selected);
    }
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Shield className="h-7 w-7" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            Choose Authentication Method
          </h1>
          <p className="mt-2 text-muted-foreground">
            Select how you want to authenticate with Claude
          </p>
        </div>

        {/* Auth mode options */}
        <div className="space-y-3 mb-8">
          {AUTH_MODE_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isSelected = selected === option.id;

            return (
              <Card
                key={option.id}
                className={cn(
                  "cursor-pointer transition-all hover:border-primary/50",
                  isSelected
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border hover:bg-muted/30"
                )}
                onClick={() => setSelected(option.id)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className={cn(
                      "h-10 w-10 rounded-lg flex items-center justify-center shrink-0",
                      isSelected
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-foreground">{option.title}</span>
                        {option.recommended && (
                          <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                            Recommended
                          </span>
                        )}
                        {option.enterprise && (
                          <span className="text-xs bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                            Enterprise
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {option.description}
                      </p>
                    </div>
                    {isSelected && (
                      <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Info about changing later */}
        <p className="text-sm text-muted-foreground text-center mb-8">
          You can change this later in Project Settings for each project individually.
        </p>

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-6 border-t border-border">
          <Button
            variant="ghost"
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground"
          >
            Back
          </Button>
          <div className="flex gap-4">
            <Button
              variant="ghost"
              onClick={onSkip}
              className="text-muted-foreground hover:text-foreground"
            >
              Skip
            </Button>
            <Button
              onClick={handleContinue}
              disabled={!selected}
              className="gap-2"
            >
              Continue
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
