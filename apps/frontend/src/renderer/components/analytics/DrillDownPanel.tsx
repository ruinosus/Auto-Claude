/**
 * DrillDownPanel - Slide-in panel for detailed analytics views
 *
 * A slide-in panel component that displays detailed information about
 * analytics data at various drill-down levels (spec, session, message).
 *
 * Features:
 * - Slides in from right side (400px width)
 * - Semi-transparent backdrop that closes on click
 * - Close on Escape key press
 * - Breadcrumb navigation showing path
 * - Scrollable content area
 * - Focus trap for accessibility
 *
 * @example
 * ```tsx
 * // Add to Analytics.tsx
 * <DrillDownPanel />
 * ```
 */
import { useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { X, ChevronRight } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useAnalyticsStore } from '../../stores/analytics-store';
import { cn } from '../../lib/utils';

export function DrillDownPanel() {
  const { t } = useTranslation(['analytics']);
  const { drillDown, closeDrillDown, data } = useAnalyticsStore();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drillDown.isOpen) {
        closeDrillDown();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [drillDown.isOpen, closeDrillDown]);

  // Focus trap and restore focus on close
  useEffect(() => {
    if (drillDown.isOpen) {
      // Store the currently focused element
      previousActiveElement.current = document.activeElement as HTMLElement;

      // Focus the close button when panel opens
      setTimeout(() => {
        closeButtonRef.current?.focus();
      }, 100);
    } else {
      // Restore focus when panel closes
      if (previousActiveElement.current) {
        previousActiveElement.current.focus();
        previousActiveElement.current = null;
      }
    }
  }, [drillDown.isOpen]);

  // Handle focus trap within panel
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !panelRef.current) return;

    const focusableElements = panelRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    if (e.shiftKey) {
      // Shift+Tab: if on first element, wrap to last
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
    } else {
      // Tab: if on last element, wrap to first
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }
  }, []);

  // Get the display label for the current drill-down level
  const getLevelLabel = useCallback((level: string): string => {
    switch (level) {
      case 'aggregate':
        return t('analytics:drillDown.levels.aggregate');
      case 'spec':
        return t('analytics:drillDown.levels.spec');
      case 'session':
        return t('analytics:drillDown.levels.session');
      case 'message':
        return t('analytics:drillDown.levels.message');
      default:
        return level;
    }
  }, [t]);

  // Format currency values
  const formatCurrency = (amount: number | undefined): string => {
    if (amount === undefined || amount === null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    }).format(amount);
  };

  // Format number with locale
  const formatNumber = (num: number | undefined): string => {
    if (num === undefined || num === null) return '-';
    return num.toLocaleString();
  };

  // Get content based on drill-down level
  const getContent = () => {
    switch (drillDown.level) {
      case 'spec': {
        const spec = data?.conversations?.find(c => c.specId === drillDown.specId);
        if (!spec) {
          return (
            <p className="text-muted-foreground">
              {t('analytics:drillDown.specNotFound')}
            </p>
          );
        }
        return (
          <div className="space-y-6">
            <div>
              <h3 className="font-semibold text-lg">{spec.specId}</h3>
              <p className="text-sm text-muted-foreground">
                {t('analytics:drillDown.specDetails')}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  {t('analytics:drillDown.fields.phase')}
                </p>
                <p className="font-medium">{spec.phase}</p>
              </div>
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  {t('analytics:drillDown.fields.cost')}
                </p>
                <p className="font-medium">{formatCurrency(spec.cost)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  {t('analytics:drillDown.fields.inputTokens')}
                </p>
                <p className="font-medium">{formatNumber(spec.tokens?.input)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  {t('analytics:drillDown.fields.outputTokens')}
                </p>
                <p className="font-medium">{formatNumber(spec.tokens?.output)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  {t('analytics:drillDown.fields.model')}
                </p>
                <p className="font-medium">{spec.model || '-'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  {t('analytics:drillDown.fields.duration')}
                </p>
                <p className="font-medium">
                  {spec.durationSeconds
                    ? `${Math.round(spec.durationSeconds)}s`
                    : '-'}
                </p>
              </div>
            </div>
          </div>
        );
      }
      case 'session': {
        return (
          <div className="space-y-4">
            <p className="text-muted-foreground">
              {t('analytics:drillDown.sessionDetails')}
            </p>
            {drillDown.sessionId && (
              <div className="text-sm">
                <span className="text-muted-foreground">
                  {t('analytics:drillDown.fields.sessionId')}:
                </span>{' '}
                <span className="font-mono">{drillDown.sessionId}</span>
              </div>
            )}
          </div>
        );
      }
      case 'message': {
        return (
          <div className="space-y-4">
            <p className="text-muted-foreground">
              {t('analytics:drillDown.messageDetails')}
            </p>
          </div>
        );
      }
      default:
        return (
          <p className="text-muted-foreground">
            {t('analytics:drillDown.selectItem')}
          </p>
        );
    }
  };

  if (!drillDown.isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={closeDrillDown}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drill-down-title"
        aria-describedby="drill-down-description"
        onKeyDown={handleKeyDown}
        className={cn(
          'fixed right-0 top-0 h-full w-[400px] bg-background border-l z-50',
          'transform transition-transform duration-300 ease-out',
          'shadow-lg',
          drillDown.isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div
            id="drill-down-title"
            className="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <span>{t('analytics:title')}</span>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
            <span className="text-foreground font-medium">
              {getLevelLabel(drillDown.level)}
            </span>
          </div>
          <Button
            ref={closeButtonRef}
            variant="ghost"
            size="icon"
            onClick={closeDrillDown}
            aria-label={t('analytics:drillDown.close')}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <ScrollArea className="h-[calc(100%-60px)]">
          <div id="drill-down-description" className="p-4">
            {getContent()}
          </div>
        </ScrollArea>
      </div>
    </>
  );
}
