import { useTranslation } from 'react-i18next';

type Severity = 'info' | 'warning' | 'error' | 'success';

interface AlertBadgeProps {
  severity: Severity;
  message: string;
  count?: number;
  className?: string;
}

const severityStyles: Record<Severity, string> = {
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
};

const severityIcons: Record<Severity, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌',
  success: '✅',
};

export function AlertBadge({ severity, message, count, className = '' }: AlertBadgeProps) {
  const { t } = useTranslation(['analytics']);

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${severityStyles[severity]} ${className}`}>
      <span>{severityIcons[severity]}</span>
      <span>{t(message)}</span>
      {count !== undefined && count > 0 && (
        <span className="font-bold">({count})</span>
      )}
    </div>
  );
}

export default AlertBadge;
