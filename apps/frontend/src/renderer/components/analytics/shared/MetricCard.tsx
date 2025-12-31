import { type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface MetricCardProps {
  title: string;           // i18n key for title
  value: string | number;  // Main value to display
  subtitle?: string;       // Optional subtitle
  icon?: ReactNode;        // Optional icon
  trend?: {
    value: number;         // +5 or -3
    isPositive: boolean;   // Green or red
  };
  className?: string;      // Additional classes
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  className = ''
}: MetricCardProps) {
  const { t } = useTranslation(['analytics']);

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t(title)}
          </p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {subtitle}
            </p>
          )}
        </div>
        {icon && (
          <div className="text-gray-400 dark:text-gray-500">
            {icon}
          </div>
        )}
      </div>
      {trend && (
        <div className={`mt-2 text-sm flex items-center gap-1 ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
          <span>{trend.isPositive ? '↑' : '↓'}</span>
          <span>{Math.abs(trend.value)}%</span>
        </div>
      )}
    </div>
  );
}

export default MetricCard;
