/**
 * Artifact Value Table
 * ====================
 *
 * Detailed table showing per-artifact metrics including
 * artifact_id, type, role, hours, rate, value, and quality_score.
 * Uses ROI Engine API to fetch artifact data.
 *
 * Phase M3: Artifact Visualization Component
 */

import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Table,
  AlertCircle,
  Loader2,
  ChevronUp,
  ChevronDown,
  Search,
  Filter,
  HardHat,
  Code2,
  TestTube,
  Settings,
  Briefcase,
  Server,
  CheckCircle,
  Clock,
  Star,
} from 'lucide-react';
import * as roiEngineApi from '../../../services/roi-engine-api';
import type { ArtifactsByRoleResponse, ArtifactDetail, Role } from '../../../services/roi-engine-api';

interface ArtifactValueTableProps {
  projectDir: string;
  specId?: string;
  className?: string;
  pageSize?: number;
}

// Extended artifact type for display
interface DisplayArtifact extends ArtifactDetail {
  role: Role;
  hourly_rate?: number;
}

// Role configuration for icons and colors
const ROLE_CONFIG: Record<string, {
  color: string;
  bgColor: string;
  icon: React.ReactNode;
  label: string;
}> = {
  architect: {
    color: 'text-violet-500',
    bgColor: 'bg-violet-100 dark:bg-violet-900/30',
    icon: <HardHat className="h-4 w-4" />,
    label: 'Architect',
  },
  developer: {
    color: 'text-blue-500',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    icon: <Code2 className="h-4 w-4" />,
    label: 'Developer',
  },
  qa: {
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
    icon: <TestTube className="h-4 w-4" />,
    label: 'QA',
  },
  tech_lead: {
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-100 dark:bg-indigo-900/30',
    icon: <Settings className="h-4 w-4" />,
    label: 'Tech Lead',
  },
  pm: {
    color: 'text-amber-500',
    bgColor: 'bg-amber-100 dark:bg-amber-900/30',
    icon: <Briefcase className="h-4 w-4" />,
    label: 'PM',
  },
  devops: {
    color: 'text-red-500',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    icon: <Server className="h-4 w-4" />,
    label: 'DevOps',
  },
};

type SortField = 'type' | 'role' | 'hours' | 'value' | 'quality';
type SortDirection = 'asc' | 'desc';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatHours(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)}m`;
  }
  return `${hours.toFixed(1)}h`;
}

function QualityBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) {
    return <span className="text-gray-400 dark:text-gray-500">-</span>;
  }

  const percentage = Math.round(score * 100);
  let colorClass = 'text-gray-500 bg-gray-100 dark:bg-gray-700';

  if (score >= 0.8) {
    colorClass = 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400';
  } else if (score >= 0.5) {
    colorClass = 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400';
  } else {
    colorClass = 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400';
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      <Star className="h-3 w-3" />
      {percentage}%
    </span>
  );
}

function StatusBadge({ status }: { status?: 'draft' | 'complete' }) {
  if (status === 'draft') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-orange-600 bg-orange-100 dark:bg-orange-900/30 dark:text-orange-400">
        <Clock className="h-3 w-3" />
        Draft
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400">
      <CheckCircle className="h-3 w-3" />
      Complete
    </span>
  );
}

function SortableHeader({
  label,
  field,
  currentSort,
  currentDirection,
  onSort,
}: {
  label: string;
  field: SortField;
  currentSort: SortField;
  currentDirection: SortDirection;
  onSort: (field: SortField) => void;
}) {
  const isActive = currentSort === field;

  return (
    <button
      onClick={() => onSort(field)}
      className={`flex items-center gap-1 text-left font-medium hover:text-blue-500 transition-colors ${
        isActive ? 'text-blue-500' : 'text-gray-700 dark:text-gray-300'
      }`}
    >
      {label}
      {isActive ? (
        currentDirection === 'asc' ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )
      ) : (
        <div className="h-4 w-4" /> // Placeholder for alignment
      )}
    </button>
  );
}

export function ArtifactValueTable({
  projectDir,
  specId,
  className = '',
  pageSize = 10,
}: ArtifactValueTableProps) {
  const { t } = useTranslation(['analytics']);
  const [data, setData] = useState<ArtifactsByRoleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(0);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const response = await roiEngineApi.getArtifactsByRole({
          project_dir: projectDir,
          spec_id: specId,
        });
        setData(response);
      } catch (err) {
        console.error('Failed to fetch artifacts by role:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [projectDir, specId]);

  // Flatten artifacts from all roles into a single list
  const allArtifacts = useMemo((): DisplayArtifact[] => {
    if (!data) return [];

    const artifacts: DisplayArtifact[] = [];
    for (const roleItem of data.by_role) {
      for (const artifact of roleItem.top_artifacts) {
        artifacts.push({
          ...artifact,
          role: roleItem.role,
          hourly_rate: artifact.value && artifact.estimated_hours > 0
            ? artifact.value / artifact.estimated_hours
            : undefined,
        });
      }
    }
    return artifacts;
  }, [data]);

  // Get unique roles for filter
  const availableRoles = useMemo(() => {
    const roles = new Set<string>();
    allArtifacts.forEach((a) => roles.add(a.role));
    return Array.from(roles).sort();
  }, [allArtifacts]);

  // Filter and sort artifacts
  const filteredAndSortedArtifacts = useMemo(() => {
    let filtered = [...allArtifacts];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (a) =>
          a.artifact_id.toLowerCase().includes(query) ||
          a.artifact_type.toLowerCase().includes(query)
      );
    }

    // Apply role filter
    if (selectedRole !== 'all') {
      filtered = filtered.filter((a) => a.role === selectedRole);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'type':
          comparison = a.artifact_type.localeCompare(b.artifact_type);
          break;
        case 'role':
          comparison = a.role.localeCompare(b.role);
          break;
        case 'hours':
          comparison = a.estimated_hours - b.estimated_hours;
          break;
        case 'value':
          comparison = a.value - b.value;
          break;
        case 'quality':
          comparison = (a.quality_score ?? 0) - (b.quality_score ?? 0);
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [allArtifacts, searchQuery, selectedRole, sortField, sortDirection]);

  // Paginate
  const paginatedArtifacts = useMemo(() => {
    const start = currentPage * pageSize;
    return filteredAndSortedArtifacts.slice(start, start + pageSize);
  }, [filteredAndSortedArtifacts, currentPage, pageSize]);

  const totalPages = Math.ceil(filteredAndSortedArtifacts.length / pageSize);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(0);
  };

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-500 dark:text-gray-400">Loading artifacts...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center gap-2 text-red-500">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!data || allArtifacts.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <Table className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('analytics:artifacts.valueTable.title', 'Artifact Details')}
          </h3>
        </div>
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          {t('analytics:artifacts.valueTable.noData', 'No artifact data available')}
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Table className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('analytics:artifacts.valueTable.title', 'Artifact Details')}
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            ({filteredAndSortedArtifacts.length} {filteredAndSortedArtifacts.length === 1 ? 'artifact' : 'artifacts'})
          </span>
        </div>

        {/* Total Value */}
        <div className="text-sm">
          <span className="text-gray-500 dark:text-gray-400">Total: </span>
          <span className="font-bold text-green-600 dark:text-green-400">
            {formatCurrency(data.total_value)}
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder={t('analytics:artifacts.valueTable.searchPlaceholder', 'Search by ID or type...')}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(0);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Role Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <select
            value={selectedRole}
            onChange={(e) => {
              setSelectedRole(e.target.value);
              setCurrentPage(0);
            }}
            className="pl-9 pr-8 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none cursor-pointer"
          >
            <option value="all">{t('analytics:artifacts.valueTable.allRoles', 'All Roles')}</option>
            {availableRoles.map((role) => (
              <option key={role} value={role}>
                {ROLE_CONFIG[role]?.label || role}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-3 px-2">
                <span className="text-gray-700 dark:text-gray-300 font-medium">ID</span>
              </th>
              <th className="text-left py-3 px-2">
                <SortableHeader
                  label={t('analytics:artifacts.valueTable.type', 'Type')}
                  field="type"
                  currentSort={sortField}
                  currentDirection={sortDirection}
                  onSort={handleSort}
                />
              </th>
              <th className="text-left py-3 px-2">
                <SortableHeader
                  label={t('analytics:artifacts.valueTable.role', 'Role')}
                  field="role"
                  currentSort={sortField}
                  currentDirection={sortDirection}
                  onSort={handleSort}
                />
              </th>
              <th className="text-right py-3 px-2">
                <SortableHeader
                  label={t('analytics:artifacts.valueTable.hours', 'Hours')}
                  field="hours"
                  currentSort={sortField}
                  currentDirection={sortDirection}
                  onSort={handleSort}
                />
              </th>
              <th className="text-right py-3 px-2">
                <SortableHeader
                  label={t('analytics:artifacts.valueTable.value', 'Value')}
                  field="value"
                  currentSort={sortField}
                  currentDirection={sortDirection}
                  onSort={handleSort}
                />
              </th>
              <th className="text-center py-3 px-2">
                <SortableHeader
                  label={t('analytics:artifacts.valueTable.quality', 'Quality')}
                  field="quality"
                  currentSort={sortField}
                  currentDirection={sortDirection}
                  onSort={handleSort}
                />
              </th>
              <th className="text-center py-3 px-2">
                <span className="text-gray-700 dark:text-gray-300 font-medium">
                  {t('analytics:artifacts.valueTable.status', 'Status')}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedArtifacts.map((artifact, index) => {
              const roleConfig = ROLE_CONFIG[artifact.role];
              return (
                <tr
                  key={`${artifact.artifact_id}-${index}`}
                  className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td className="py-3 px-2">
                    <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-600 dark:text-gray-300">
                      {artifact.artifact_id.slice(0, 12)}...
                    </code>
                  </td>
                  <td className="py-3 px-2">
                    <span className="text-gray-900 dark:text-white capitalize">
                      {artifact.artifact_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-2">
                    <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full ${roleConfig?.bgColor || 'bg-gray-100 dark:bg-gray-700'}`}>
                      <span className={roleConfig?.color || 'text-gray-500'}>
                        {roleConfig?.icon}
                      </span>
                      <span className={`text-xs font-medium ${roleConfig?.color || 'text-gray-500'}`}>
                        {roleConfig?.label || artifact.role}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-2 text-right">
                    <span className="text-gray-600 dark:text-gray-400">
                      {formatHours(artifact.estimated_hours)}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-right">
                    <span className="font-medium text-green-600 dark:text-green-400">
                      {formatCurrency(artifact.value)}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-center">
                    <QualityBadge score={artifact.quality_score} />
                  </td>
                  <td className="py-3 px-2 text-center">
                    <StatusBadge status={artifact.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {t('analytics:artifacts.valueTable.showing', 'Showing {{start}}-{{end}} of {{total}}', {
              start: currentPage * pageSize + 1,
              end: Math.min((currentPage + 1) * pageSize, filteredAndSortedArtifacts.length),
              total: filteredAndSortedArtifacts.length,
            })}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {t('analytics:artifacts.valueTable.previous', 'Previous')}
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {currentPage + 1} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages - 1, prev + 1))}
              disabled={currentPage >= totalPages - 1}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {t('analytics:artifacts.valueTable.next', 'Next')}
            </button>
          </div>
        </div>
      )}

      {/* Summary Row */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {data.total_artifacts}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics:artifacts.valueTable.totalArtifacts', 'Total Artifacts')}
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {formatCurrency(data.total_value)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics:artifacts.valueTable.totalValue', 'Total Value')}
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {data.by_role.length}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics:artifacts.valueTable.rolesActive', 'Roles Active')}
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {data.total_artifacts > 0
                ? formatCurrency(data.total_value / data.total_artifacts)
                : '$0'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics:artifacts.valueTable.avgValue', 'Avg Value')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ArtifactValueTable;
