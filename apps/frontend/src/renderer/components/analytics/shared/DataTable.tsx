import { type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  className?: string;
}

export function DataTable<T extends object>({
  columns,
  data,
  loading,
  emptyMessage,
  onRowClick,
  className = ''
}: DataTableProps<T>) {
  const { t } = useTranslation(['analytics']);

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 bg-gray-200 dark:bg-gray-700 rounded" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        {emptyMessage ? t(emptyMessage) : t('common.noData')}
      </div>
    );
  }

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {columns.map((col) => (
              <th key={String(col.key)} className={`text-left py-2 px-3 text-gray-600 dark:text-gray-400 font-medium ${col.className || ''}`}>
                {t(col.header)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr
              key={rowIdx}
              onClick={() => onRowClick?.(row)}
              className={`border-b border-gray-100 dark:border-gray-800 ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700' : ''}`}
            >
              {columns.map((col, colIdx) => (
                <td key={`${rowIdx}-${colIdx}`} className={`py-2 px-3 text-gray-900 dark:text-gray-100 ${col.className || ''}`}>
                  {col.render ? col.render(row) : String(row[col.key as keyof T] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
