import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { StakeholderRatesEditor } from './StakeholderRatesEditor';
import { createSquad, updateSquad } from '../../../stores/squad-store';
import type { Squad, SquadFormData, TimeSavingsConfig, PreventionValuesConfig, QualityMultipliersConfig } from '../../../../shared/types/squad';
import { DEFAULT_SQUAD_CONFIG, generateDefaultStakeholderRates } from '../../../../shared/types/squad';

interface SquadFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  squad: Squad | null;
}

type FormTab = 'general' | 'stakeholders' | 'timeSavings' | 'prevention' | 'quality';

/**
 * Modal for creating or editing a Squad
 */
export function SquadFormModal({ isOpen, onClose, squad }: SquadFormModalProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [activeTab, setActiveTab] = useState<FormTab>('general');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [defaultHourlyRate, setDefaultHourlyRate] = useState(150);
  const [stakeholderRates, setStakeholderRates] = useState<Record<string, number>>({});
  const [timeSavings, setTimeSavings] = useState<TimeSavingsConfig>(DEFAULT_SQUAD_CONFIG.timeSavings);
  const [preventionValues, setPreventionValues] = useState<PreventionValuesConfig>(DEFAULT_SQUAD_CONFIG.preventionValues);
  const [qualityMultipliers, setQualityMultipliers] = useState<QualityMultipliersConfig>(DEFAULT_SQUAD_CONFIG.qualityMultipliers);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      if (squad) {
        // Editing existing squad
        setName(squad.name);
        setDescription(squad.description || '');
        setDefaultHourlyRate(squad.defaultHourlyRate);
        setStakeholderRates(squad.stakeholderRates);
        setTimeSavings(squad.timeSavings);
        setPreventionValues(squad.preventionValues);
        setQualityMultipliers(squad.qualityMultipliers);
      } else {
        // Creating new squad
        setName('');
        setDescription('');
        setDefaultHourlyRate(DEFAULT_SQUAD_CONFIG.defaultHourlyRate);
        setStakeholderRates(generateDefaultStakeholderRates());
        setTimeSavings(DEFAULT_SQUAD_CONFIG.timeSavings);
        setPreventionValues(DEFAULT_SQUAD_CONFIG.preventionValues);
        setQualityMultipliers(DEFAULT_SQUAD_CONFIG.qualityMultipliers);
      }
      setActiveTab('general');
    }
  }, [isOpen, squad]);

  const handleSubmit = async () => {
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      const formData: SquadFormData = {
        name: name.trim(),
        description: description.trim() || undefined,
        defaultHourlyRate,
        stakeholderRates,
        timeSavings,
        preventionValues,
        qualityMultipliers,
      };

      if (squad) {
        await updateSquad(squad.id, formData);
      } else {
        await createSquad(formData);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save squad:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {squad ? t('settings:squads.editSquad') : t('settings:squads.createSquad')}
          </DialogTitle>
          <DialogDescription>
            {t('settings:squads.formDescription')}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as FormTab)}>
          <TabsList className="grid grid-cols-5 w-full">
            <TabsTrigger value="general">{t('settings:squads.tabs.general')}</TabsTrigger>
            <TabsTrigger value="stakeholders">{t('settings:squads.tabs.stakeholders')}</TabsTrigger>
            <TabsTrigger value="timeSavings">{t('settings:squads.tabs.timeSavings')}</TabsTrigger>
            <TabsTrigger value="prevention">{t('settings:squads.tabs.prevention')}</TabsTrigger>
            <TabsTrigger value="quality">{t('settings:squads.tabs.quality')}</TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="space-y-4 mt-4">
            <div className="grid gap-2">
              <Label htmlFor="name">{t('settings:squads.name')}</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('settings:squads.namePlaceholder')}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">{t('settings:squads.descriptionLabel')}</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('settings:squads.descriptionPlaceholder')}
                rows={3}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="defaultRate">{t('settings:squads.defaultHourlyRate')}</Label>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">$</span>
                <Input
                  id="defaultRate"
                  type="number"
                  value={defaultHourlyRate}
                  onChange={(e) => setDefaultHourlyRate(parseFloat(e.target.value) || 0)}
                  className="max-w-[150px]"
                  min={0}
                  step={5}
                />
                <span className="text-muted-foreground">/hr</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {t('settings:squads.defaultRateHint')}
              </p>
            </div>
          </TabsContent>

          {/* Stakeholders Tab */}
          <TabsContent value="stakeholders" className="mt-4">
            <StakeholderRatesEditor
              rates={stakeholderRates}
              onChange={setStakeholderRates}
            />
          </TabsContent>

          {/* Time Savings Tab */}
          <TabsContent value="timeSavings" className="space-y-4 mt-4">
            <p className="text-sm text-muted-foreground mb-4">
              {t('settings:squads.timeSavingsDescription')}
            </p>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(timeSavings).map(([key, value]) => (
                <div key={key} className="grid gap-2">
                  <Label htmlFor={`time-${key}`}>
                    {t(`settings:squads.timeSavings.${key}`)}
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id={`time-${key}`}
                      type="number"
                      value={value}
                      onChange={(e) => setTimeSavings({
                        ...timeSavings,
                        [key]: parseInt(e.target.value) || 0,
                      })}
                      className="max-w-[100px]"
                      min={0}
                    />
                    <span className="text-muted-foreground">{t('common:minutes')}</span>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* Prevention Tab */}
          <TabsContent value="prevention" className="space-y-4 mt-4">
            <p className="text-sm text-muted-foreground mb-4">
              {t('settings:squads.preventionDescription')}
            </p>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(preventionValues).map(([key, value]) => (
                <div key={key} className="grid gap-2">
                  <Label htmlFor={`prevention-${key}`}>
                    {t(`settings:squads.prevention.${key}`)}
                  </Label>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">$</span>
                    <Input
                      id={`prevention-${key}`}
                      type="number"
                      value={value}
                      onChange={(e) => setPreventionValues({
                        ...preventionValues,
                        [key]: parseFloat(e.target.value) || 0,
                      })}
                      className="max-w-[120px]"
                      min={0}
                      step={100}
                    />
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* Quality Tab */}
          <TabsContent value="quality" className="space-y-4 mt-4">
            <p className="text-sm text-muted-foreground mb-4">
              {t('settings:squads.qualityDescription')}
            </p>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(qualityMultipliers)
                .filter(([key]) => !['minMultiplier', 'maxMultiplier'].includes(key))
                .map(([key, value]) => (
                  <div key={key} className="grid gap-2">
                    <Label htmlFor={`quality-${key}`}>
                      {t(`settings:squads.quality.${key}`)}
                    </Label>
                    <div className="flex items-center gap-2">
                      <Input
                        id={`quality-${key}`}
                        type="number"
                        value={Math.round(value * 100)}
                        onChange={(e) => setQualityMultipliers({
                          ...qualityMultipliers,
                          [key]: (parseFloat(e.target.value) || 0) / 100,
                        })}
                        className="max-w-[80px]"
                        step={5}
                      />
                      <span className="text-muted-foreground">%</span>
                    </div>
                  </div>
                ))}
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            {t('common:cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting || !name.trim()}>
            {isSubmitting
              ? t('common:saving')
              : squad
                ? t('common:save')
                : t('common:create')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
