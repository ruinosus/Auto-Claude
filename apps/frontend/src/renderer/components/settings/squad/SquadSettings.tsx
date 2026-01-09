import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Edit2, Trash2, Users, Download, Upload, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { SettingsSection } from '../SettingsSection';
import { SquadFormModal } from './SquadFormModal';
import { useSquadStore, fetchSquads, deleteSquad } from '../../../stores/squad-store';
import type { Squad } from '../../../../shared/types/squad';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../ui/alert-dialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';

interface ImportResult {
  imported: number;
  skipped: string[];
  errors: string[];
}

/**
 * Squad Settings - Manage team configurations for ROI calculations
 */
export function SquadSettings() {
  const { t } = useTranslation(['settings', 'common']);
  const { squads, isLoading, error, setSquads } = useSquadStore();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingSquad, setEditingSquad] = useState<Squad | null>(null);
  const [deletingSquad, setDeletingSquad] = useState<Squad | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  useEffect(() => {
    fetchSquads();
  }, []);

  const handleCreate = () => {
    setEditingSquad(null);
    setIsFormOpen(true);
  };

  const handleEdit = (squad: Squad) => {
    setEditingSquad(squad);
    setIsFormOpen(true);
  };

  const handleDelete = async () => {
    if (deletingSquad) {
      try {
        await deleteSquad(deletingSquad.id);
      } catch (err) {
        console.error('Failed to delete squad:', err);
      }
      setDeletingSquad(null);
    }
  };

  const handleFormClose = () => {
    setIsFormOpen(false);
    setEditingSquad(null);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const result = await window.electronAPI.squad.export();
      if (!result.success && !result.canceled) {
        console.error('Export failed:', result.error);
      }
    } catch (err) {
      console.error('Failed to export squads:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleImport = async () => {
    setIsImporting(true);
    try {
      const result = await window.electronAPI.squad.import();
      if (result.success && !result.canceled) {
        // Update the store with the new squads
        if (result.allSquads) {
          setSquads(result.allSquads);
        }
        // Show import result
        setImportResult({
          imported: result.imported?.length || 0,
          skipped: result.skipped || [],
          errors: result.errors || [],
        });
      }
    } catch (err) {
      console.error('Failed to import squads:', err);
    } finally {
      setIsImporting(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (isLoading && squads.length === 0) {
    return (
      <SettingsSection
        title={t('settings:squads.title')}
        description={t('settings:squads.description')}
      >
        <div className="space-y-4">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-24 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title={t('settings:squads.title')}
      description={t('settings:squads.description')}
    >
      <div className="space-y-4">
        {/* Error Display */}
        {error && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
            {error}
          </div>
        )}

        {/* Squad List */}
        {squads.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-8">
              <Users className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-center mb-4">
                {t('settings:squads.emptyState')}
              </p>
              <Button onClick={handleCreate}>
                <Plus className="h-4 w-4 mr-2" />
                {t('settings:squads.createFirst')}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid gap-4">
              {squads.map((squad) => (
                <Card key={squad.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-lg">{squad.name}</CardTitle>
                        {squad.description && (
                          <CardDescription className="mt-1">
                            {squad.description}
                          </CardDescription>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(squad)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeletingSquad(squad)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">
                          {t('settings:squads.defaultRate')}:
                        </span>
                        <span className="ml-2 font-medium">
                          {formatCurrency(squad.defaultHourlyRate)}/hr
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {t('settings:squads.stakeholders')}:
                        </span>
                        <span className="ml-2 font-medium">
                          {Object.keys(squad.stakeholderRates).length}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {t('settings:squads.updated')}:
                        </span>
                        <span className="ml-2 font-medium">
                          {new Date(squad.updatedAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="flex gap-2">
              <Button onClick={handleCreate} className="flex-1">
                <Plus className="h-4 w-4 mr-2" />
                {t('settings:squads.addSquad')}
              </Button>
              <Button
                variant="outline"
                onClick={handleExport}
                disabled={isExporting || squads.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                {t('settings:squads.export')}
              </Button>
              <Button
                variant="outline"
                onClick={handleImport}
                disabled={isImporting}
              >
                <Upload className="h-4 w-4 mr-2" />
                {t('settings:squads.import')}
              </Button>
            </div>
          </>
        )}

        {/* Import/Export buttons when no squads exist */}
        {squads.length === 0 && (
          <div className="flex justify-center gap-2 mt-4">
            <Button
              variant="outline"
              onClick={handleImport}
              disabled={isImporting}
            >
              <Upload className="h-4 w-4 mr-2" />
              {t('settings:squads.import')}
            </Button>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <SquadFormModal
        isOpen={isFormOpen}
        onClose={handleFormClose}
        squad={editingSquad}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={!!deletingSquad} onOpenChange={() => setDeletingSquad(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('settings:squads.deleteConfirmTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('settings:squads.deleteConfirmDescription', {
                name: deletingSquad?.name,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              {t('common:delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Import Result Dialog */}
      <Dialog open={!!importResult} onOpenChange={() => setImportResult(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('settings:squads.importResultTitle')}</DialogTitle>
            <DialogDescription>
              {t('settings:squads.importResultDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Success count */}
            {importResult && importResult.imported > 0 && (
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <CheckCircle2 className="h-5 w-5" />
                <span>
                  {t('settings:squads.importedCount', { count: importResult.imported })}
                </span>
              </div>
            )}

            {/* Skipped items */}
            {importResult && importResult.skipped.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400">
                  <AlertCircle className="h-5 w-5" />
                  <span>{t('settings:squads.skippedTitle')}</span>
                </div>
                <ul className="text-sm text-muted-foreground ml-7 list-disc">
                  {importResult.skipped.map((msg, i) => (
                    <li key={i}>{msg}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Errors */}
            {importResult && importResult.errors.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  <span>{t('settings:squads.errorsTitle')}</span>
                </div>
                <ul className="text-sm text-muted-foreground ml-7 list-disc">
                  {importResult.errors.map((msg, i) => (
                    <li key={i}>{msg}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* No changes */}
            {importResult && importResult.imported === 0 && importResult.skipped.length === 0 && importResult.errors.length === 0 && (
              <p className="text-muted-foreground">
                {t('settings:squads.noChanges')}
              </p>
            )}
          </div>
          <div className="flex justify-end mt-4">
            <Button onClick={() => setImportResult(null)}>
              {t('common:buttons.gotIt')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </SettingsSection>
  );
}
