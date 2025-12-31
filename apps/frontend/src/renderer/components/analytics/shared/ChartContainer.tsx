import { type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface ChartContainerProps {
  title: string;
  children: ReactNode;
  loading?: boolean;
  error?: string;
  className?: string;
}

export function ChartContainer({ title, children, loading, error, className = '' }: ChartContainerProps) {
  const { t } = useTranslation(['analytics']);

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">{t(title)}</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="animate-pulse text-gray-400">{t('common.loading')}</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">{t(title)}</h3>
        <div className="h-64 flex items-center justify-center text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">{t(title)}</h3>
      <div className="h-64">{children}</div>
    </div>
  );
}

export default ChartContainer;
