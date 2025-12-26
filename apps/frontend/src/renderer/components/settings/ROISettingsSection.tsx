import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Switch } from '../ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { SettingsSection } from './SettingsSection';
import type { ROISettings, Currency } from '../../../shared/types/roi';
import { DEFAULT_ROI_SETTINGS } from '../../../shared/types/roi';

/**
 * ROI Settings section for configuring ROI calculation parameters
 */
export function ROISettingsSection() {
  const { t } = useTranslation(['settings']);
  const [settings, setSettings] = useState<ROISettings>(DEFAULT_ROI_SETTINGS);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const result = await window.electronAPI.roi.getSettings();
      setSettings(result);
    } catch (error) {
      console.error('Failed to load ROI settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async (updates: Partial<ROISettings>) => {
    try {
      await window.electronAPI.roi.saveSettings({ ...settings, ...updates });
      setSettings((prev) => ({ ...prev, ...updates }));
    } catch (error) {
      console.error('Failed to save ROI settings:', error);
    }
  };

  if (isLoading) {
    return (
      <SettingsSection
        title={t('settings:roi.title')}
        description={t('settings:roi.description')}
      >
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-10 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title={t('settings:roi.title')}
      description={t('settings:roi.description')}
    >
      <div className="space-y-6">
        {/* Developer Hourly Rate */}
        <div className="grid gap-2">
          <Label htmlFor="hourlyRate">{t('settings:roi.hourlyRate')}</Label>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">$</span>
            <Input
              id="hourlyRate"
              type="number"
              value={settings.developerHourlyRate}
              onChange={(e) => saveSettings({ developerHourlyRate: parseFloat(e.target.value) || 0 })}
              className="max-w-[150px]"
              min={0}
              step={5}
            />
            <span className="text-muted-foreground">/hr</span>
          </div>
          <p className="text-sm text-muted-foreground">{t('settings:roi.hourlyRateHint')}</p>
        </div>

        {/* Primary Currency */}
        <div className="grid gap-2">
          <Label htmlFor="primaryCurrency">{t('settings:roi.primaryCurrency')}</Label>
          <Select
            value={settings.primaryCurrency}
            onValueChange={(value: Currency) => saveSettings({ primaryCurrency: value })}
          >
            <SelectTrigger className="max-w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="USD">USD ($)</SelectItem>
              <SelectItem value="EUR">EUR (E)</SelectItem>
              <SelectItem value="BRL">BRL (R$)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Secondary Currency */}
        <div className="grid gap-2">
          <Label htmlFor="secondaryCurrency">{t('settings:roi.secondaryCurrency')}</Label>
          <Select
            value={settings.secondaryCurrency || 'none'}
            onValueChange={(value) => saveSettings({
              secondaryCurrency: value === 'none' ? null : value as Currency
            })}
          >
            <SelectTrigger className="max-w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t('settings:roi.none')}</SelectItem>
              <SelectItem value="USD">USD ($)</SelectItem>
              <SelectItem value="EUR">EUR (E)</SelectItem>
              <SelectItem value="BRL">BRL (R$)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Exchange Rate (if secondary currency) */}
        {settings.secondaryCurrency && (
          <div className="grid gap-2">
            <Label htmlFor="exchangeRate">{t('settings:roi.exchangeRate')}</Label>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">1 {settings.primaryCurrency} =</span>
              <Input
                id="exchangeRate"
                type="number"
                value={settings.exchangeRate}
                onChange={(e) => saveSettings({
                  exchangeRate: parseFloat(e.target.value) || 1,
                  exchangeRateUpdatedAt: new Date().toISOString()
                })}
                className="max-w-[100px]"
                min={0}
                step={0.01}
              />
              <span className="text-muted-foreground">{settings.secondaryCurrency}</span>
            </div>
          </div>
        )}

        {/* Auto Estimate Hours */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>{t('settings:roi.autoEstimate')}</Label>
            <p className="text-sm text-muted-foreground">{t('settings:roi.autoEstimateHint')}</p>
          </div>
          <Switch
            checked={settings.autoEstimateHours}
            onCheckedChange={(checked) => saveSettings({ autoEstimateHours: checked })}
          />
        </div>

        {/* Minutes Per Line (if auto estimate enabled) */}
        {settings.autoEstimateHours && (
          <div className="grid gap-2">
            <Label htmlFor="minutesPerLine">{t('settings:roi.minutesPerLine')}</Label>
            <div className="flex items-center gap-2">
              <Input
                id="minutesPerLine"
                type="number"
                value={settings.minutesPerLine}
                onChange={(e) => saveSettings({ minutesPerLine: parseFloat(e.target.value) || 0 })}
                className="max-w-[100px]"
                min={0}
                step={0.5}
              />
              <span className="text-muted-foreground">{t('settings:roi.minPerLine')}</span>
            </div>
            <p className="text-sm text-muted-foreground">{t('settings:roi.minutesPerLineHint')}</p>
          </div>
        )}
      </div>
    </SettingsSection>
  );
}
