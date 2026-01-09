import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Plus, Info, Loader2, Check, DollarSign } from 'lucide-react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Card, CardContent } from '../ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { SquadFormModal } from '../settings/squad/SquadFormModal';
import { useSquadStore, fetchSquads } from '../../stores/squad-store';
import type { Squad } from '../../../shared/types/squad';

interface SquadStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

/**
 * Squad configuration step for the onboarding wizard.
 *
 * Allows users to select or create a squad for ROI calculations.
 * Squads define team rates and configurations used to calculate
 * the value of AI-assisted development.
 */
export function SquadStep({ onNext, onBack, onSkip }: SquadStepProps) {
  const { t } = useTranslation(['onboarding', 'settings', 'common']);
  const { squads, isLoading } = useSquadStore();
  const [selectedSquadId, setSelectedSquadId] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [justCreatedSquad, setJustCreatedSquad] = useState<Squad | null>(null);

  // Load squads on mount
  useEffect(() => {
    fetchSquads();
  }, []);

  // Auto-select newly created squad
  useEffect(() => {
    if (justCreatedSquad) {
      setSelectedSquadId(justCreatedSquad.id);
      setJustCreatedSquad(null);
    }
  }, [justCreatedSquad, squads]);

  // Auto-select first squad if only one exists
  useEffect(() => {
    if (squads.length === 1 && !selectedSquadId) {
      setSelectedSquadId(squads[0].id);
    }
  }, [squads, selectedSquadId]);

  const handleCreateNew = () => {
    setIsFormOpen(true);
  };

  const handleFormClose = () => {
    setIsFormOpen(false);
    // Refresh squads list
    fetchSquads();
  };

  const handleContinue = useCallback(() => {
    // Just proceed - squad selection is optional and will be used per-project
    onNext();
  }, [onNext]);

  const selectedSquad = squads.find(s => s.id === selectedSquadId);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Users className="h-7 w-7" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            {t('onboarding:squad.title')}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t('onboarding:squad.description')}
          </p>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-3 text-muted-foreground">
              {t('common:loading')}
            </span>
          </div>
        )}

        {/* Main content */}
        {!isLoading && (
          <div className="space-y-6">
            {/* Info card */}
            <Card className="border border-info/30 bg-info/10">
              <CardContent className="p-5">
                <div className="flex items-start gap-4">
                  <Info className="h-5 w-5 text-info shrink-0 mt-0.5" />
                  <div className="flex-1 space-y-3">
                    <p className="text-sm font-medium text-foreground">
                      {t('onboarding:squad.whySquads')}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {t('onboarding:squad.whySquadsDescription')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Squad Selection or Empty State */}
            {squads.length === 0 ? (
              <Card className="border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-8">
                  <Users className="h-10 w-10 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground text-center mb-4">
                    {t('onboarding:squad.emptyState')}
                  </p>
                  <Button onClick={handleCreateNew}>
                    <Plus className="h-4 w-4 mr-2" />
                    {t('onboarding:squad.createFirst')}
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {/* Squad Selector */}
                <div className="space-y-3">
                  <Label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    {t('onboarding:squad.selectSquad')}
                  </Label>
                  <Select
                    value={selectedSquadId || ''}
                    onValueChange={(value) => setSelectedSquadId(value || null)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('onboarding:squad.selectPlaceholder')} />
                    </SelectTrigger>
                    <SelectContent>
                      {squads.map((squad) => (
                        <SelectItem key={squad.id} value={squad.id}>
                          <div className="flex items-center gap-2">
                            <span>{squad.name}</span>
                            <span className="text-xs text-muted-foreground">
                              ({formatCurrency(squad.defaultHourlyRate)}/hr)
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {t('onboarding:squad.selectDescription')}
                  </p>
                </div>

                {/* Selected Squad Preview */}
                {selectedSquad && (
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h4 className="font-medium">{selectedSquad.name}</h4>
                          {selectedSquad.description && (
                            <p className="text-sm text-muted-foreground">
                              {selectedSquad.description}
                            </p>
                          )}
                        </div>
                        <Check className="h-5 w-5 text-green-500" />
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">
                            {t('settings:squads.defaultRate')}:
                          </span>
                          <span className="ml-2 font-medium">
                            {formatCurrency(selectedSquad.defaultHourlyRate)}/hr
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">
                            {t('settings:squads.stakeholders')}:
                          </span>
                          <span className="ml-2 font-medium">
                            {Object.keys(selectedSquad.stakeholderRates).length}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Create New Button */}
                <Button
                  variant="outline"
                  onClick={handleCreateNew}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  {t('onboarding:squad.createNew')}
                </Button>
              </div>
            )}

            {/* Skip hint */}
            <p className="text-xs text-muted-foreground text-center">
              {t('onboarding:squad.skipHint')}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-between items-center mt-10 pt-6 border-t border-border">
          <Button
            variant="ghost"
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground"
          >
            {t('common:back')}
          </Button>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onSkip}>
              {t('common:skip')}
            </Button>
            <Button onClick={handleContinue}>
              {t('common:buttons.continue')}
            </Button>
          </div>
        </div>
      </div>

      {/* Create/Edit Modal */}
      <SquadFormModal
        isOpen={isFormOpen}
        onClose={handleFormClose}
        squad={null}
      />
    </div>
  );
}
