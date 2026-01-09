import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '../../ui/input';
import { SENIORITY_LEVELS, ROLE_TYPES, createStakeholderKey, type Seniority, type Role } from '../../../../shared/types/squad';

interface StakeholderRatesEditorProps {
  rates: Record<string, number>;
  onChange: (rates: Record<string, number>) => void;
}

/**
 * Matrix editor for stakeholder hourly rates
 * Rows: Seniority levels (Junior, Mid, Senior, Staff, Principal)
 * Columns: Role types (Developer, QA, DevOps, PM, Architect, Tech Lead)
 */
export function StakeholderRatesEditor({ rates, onChange }: StakeholderRatesEditorProps) {
  const { t } = useTranslation(['settings']);

  // Seniority and role labels
  const seniorityLabels = useMemo(() => ({
    junior: t('settings:squads.seniority.junior'),
    mid: t('settings:squads.seniority.mid'),
    senior: t('settings:squads.seniority.senior'),
    staff: t('settings:squads.seniority.staff'),
    principal: t('settings:squads.seniority.principal'),
  }), [t]);

  const roleLabels = useMemo(() => ({
    developer: t('settings:squads.roles.developer'),
    qa: t('settings:squads.roles.qa'),
    devops: t('settings:squads.roles.devops'),
    pm: t('settings:squads.roles.pm'),
    architect: t('settings:squads.roles.architect'),
    tech_lead: t('settings:squads.roles.techLead'),
  }), [t]);

  const handleRateChange = (seniority: Seniority, role: Role, value: number) => {
    const key = createStakeholderKey(seniority, role);
    onChange({
      ...rates,
      [key]: value,
    });
  };

  const getRate = (seniority: Seniority, role: Role): number => {
    const key = createStakeholderKey(seniority, role);
    return rates[key] || 0;
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('settings:squads.stakeholderRatesDescription')}
      </p>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left text-sm font-medium text-muted-foreground border-b">
                {t('settings:squads.seniorityRole')}
              </th>
              {ROLE_TYPES.map((role) => (
                <th
                  key={role}
                  className="p-2 text-center text-sm font-medium text-muted-foreground border-b min-w-[100px]"
                >
                  {roleLabels[role as keyof typeof roleLabels]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SENIORITY_LEVELS.map((seniority) => (
              <tr key={seniority} className="border-b last:border-b-0">
                <td className="p-2 text-sm font-medium">
                  {seniorityLabels[seniority as keyof typeof seniorityLabels]}
                </td>
                {ROLE_TYPES.map((role) => (
                  <td key={role} className="p-2">
                    <div className="flex items-center justify-center gap-1">
                      <span className="text-muted-foreground text-xs">$</span>
                      <Input
                        type="number"
                        value={getRate(seniority, role)}
                        onChange={(e) =>
                          handleRateChange(seniority, role, parseInt(e.target.value) || 0)
                        }
                        className="w-20 h-8 text-center text-sm"
                        min={0}
                        step={5}
                      />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        {t('settings:squads.stakeholderRatesHint')}
      </p>
    </div>
  );
}
