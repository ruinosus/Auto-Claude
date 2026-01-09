import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users } from 'lucide-react';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import {
  useSquadStore,
  fetchSquads,
  fetchProjectSquad,
  setProjectSquad,
} from '../../../stores/squad-store';
import type { Squad } from '../../../../shared/types/squad';

interface ProjectSquadSelectorProps {
  projectId: string;
  className?: string;
}

/**
 * Selector for associating a project with a squad
 */
export function ProjectSquadSelector({ projectId, className }: ProjectSquadSelectorProps) {
  const { t } = useTranslation(['settings']);
  const { squads } = useSquadStore();
  const [selectedSquadId, setSelectedSquadId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [projectId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Fetch all squads if not already loaded
      if (squads.length === 0) {
        await fetchSquads();
      }

      // Fetch current project squad
      const currentSquad = await fetchProjectSquad(projectId);
      setSelectedSquadId(currentSquad?.id || null);
    } catch (error) {
      console.error('Failed to load squad data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSquadChange = async (value: string) => {
    const squadId = value === 'none' ? null : value;
    try {
      await setProjectSquad(projectId, squadId);
      setSelectedSquadId(squadId);
    } catch (error) {
      console.error('Failed to set project squad:', error);
    }
  };

  if (isLoading) {
    return (
      <div className={className}>
        <div className="h-10 bg-muted rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="grid gap-2">
        <Label className="flex items-center gap-2">
          <Users className="h-4 w-4" />
          {t('settings:squads.projectSquad')}
        </Label>
        <Select
          value={selectedSquadId || 'none'}
          onValueChange={handleSquadChange}
        >
          <SelectTrigger className="w-full max-w-[300px]">
            <SelectValue placeholder={t('settings:squads.selectSquad')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">{t('settings:squads.noSquad')}</SelectItem>
            {squads.map((squad) => (
              <SelectItem key={squad.id} value={squad.id}>
                {squad.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground">
          {t('settings:squads.projectSquadHint')}
        </p>
      </div>
    </div>
  );
}
