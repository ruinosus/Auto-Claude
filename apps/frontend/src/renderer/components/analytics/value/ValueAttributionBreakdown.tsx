import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Treemap,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import { useChartColors, useChartColorArray } from '../utils/useChartColors';
import { cn } from '../../../lib/utils';

// Types matching the backend API response
export interface SubcategoryValue {
  subcategory: string;
  parent_type: string;
  value_usd: number;
  confidence: number;
  count: number;
  evidence_count: number;
}

export interface ValueBreakdownByCategory {
  category: string;
  total_value: number;
  subcategories: SubcategoryValue[];
}

export interface ValueBreakdownExpanded {
  execution_value: number;
  decision_value: number;
  prevention_value: number;
  knowledge_value: number;
  total_value: number;
  by_category: ValueBreakdownByCategory[];
  by_subcategory: Record<string, SubcategoryValue>;
  attribution_count: number;
  average_confidence: number;
}

export interface ValueBreakdownData {
  breakdown: ValueBreakdownExpanded;
  period?: { from: string | null; to: string | null };
  filters_applied?: Record<string, unknown>;
}

export interface ValueAttributionBreakdownProps {
  data?: ValueBreakdownData;
  isLoading?: boolean;
  onCategoryClick?: (category: string) => void;
  onSubcategoryClick?: (subcategory: string, parentCategory: string) => void;
}

// Category display names and colors
const CATEGORY_CONFIG: Record<string, { label: string; color: string; description: string }> = {
  execution: {
    label: 'Execution',
    color: '#479FFA', // Blue
    description: 'Direct work value (code, tests, refactoring)',
  },
  decision: {
    label: 'Decision',
    color: '#4EBE96', // Green
    description: 'Strategic value (architecture, prioritization)',
  },
  prevention: {
    label: 'Prevention',
    color: '#D84F68', // Red
    description: 'Problems avoided (bugs, security issues)',
  },
  knowledge: {
    label: 'Knowledge',
    color: '#D2D714', // Yellow
    description: 'Learning value (docs, diagrams, patterns)',
  },
};

// Subcategory display names
const SUBCATEGORY_LABELS: Record<string, string> = {
  // Execution
  code_generated: 'Code Generated',
  boilerplate_saved: 'Boilerplate Saved',
  refactoring_done: 'Refactoring',
  tests_written: 'Tests Written',
  bug_fixed: 'Bugs Fixed',
  // Decision
  feature_prioritized: 'Features Prioritized',
  architecture_decision: 'Architecture Decisions',
  technology_choice: 'Technology Choices',
  scope_decision: 'Scope Decisions',
  risk_assessment: 'Risk Assessments',
  // Prevention
  bug_prevented: 'Bugs Prevented',
  security_issue_found: 'Security Issues Found',
  performance_issue_found: 'Performance Issues',
  rework_avoided: 'Rework Avoided',
  tech_debt_prevented: 'Tech Debt Prevented',
  // Knowledge
  documentation_created: 'Documentation Created',
  diagram_generated: 'Diagrams Generated',
  onboarding_accelerated: 'Onboarding Accelerated',
  pattern_documented: 'Patterns Documented',
  code_explained: 'Code Explained',
  insight_discovered: 'Insights Discovered',
};

// Format currency for display
function formatCurrency(value: number): string {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
}

// Transform data for Recharts Treemap
function transformToTreemapData(breakdown: ValueBreakdownExpanded) {
  const children = breakdown.by_category.map((cat) => {
    const config = CATEGORY_CONFIG[cat.category] || {
      label: cat.category,
      color: '#A5A66A',
      description: '',
    };

    return {
      name: config.label,
      category: cat.category,
      value: cat.total_value,
      color: config.color,
      children: cat.subcategories.map((sub) => ({
        name: SUBCATEGORY_LABELS[sub.subcategory] || sub.subcategory,
        subcategory: sub.subcategory,
        parentCategory: cat.category,
        value: sub.value_usd,
        count: sub.count,
        confidence: sub.confidence,
        color: config.color,
      })),
    };
  });

  return {
    name: 'Value',
    children,
  };
}

// Custom Treemap cell content
interface CustomContentProps {
  x: number;
  y: number;
  width: number;
  height: number;
  name: string;
  value: number;
  color: string;
  depth: number;
  index: number;
}

function CustomTreemapContent(props: CustomContentProps) {
  const { x, y, width, height, name, value, color, depth, index } = props;

  // Don't render if too small
  if (width < 30 || height < 30) {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill={color}
          stroke="#fff"
          strokeWidth={2}
          style={{ opacity: depth === 1 ? 1 : 0.85 }}
        />
      </g>
    );
  }

  const fontSize = Math.min(14, Math.max(10, width / 10));
  const showValue = width > 60 && height > 40;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        stroke="#fff"
        strokeWidth={2}
        style={{
          opacity: depth === 1 ? 1 : 0.85,
          cursor: 'pointer',
        }}
      />
      {depth === 1 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - (showValue ? 8 : 0)}
            textAnchor="middle"
            fill="#fff"
            fontSize={fontSize}
            fontWeight="bold"
            style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.5)' }}
          >
            {name}
          </text>
          {showValue && (
            <text
              x={x + width / 2}
              y={y + height / 2 + 12}
              textAnchor="middle"
              fill="#fff"
              fontSize={fontSize - 2}
              style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.5)' }}
            >
              {formatCurrency(value)}
            </text>
          )}
        </>
      )}
      {depth === 2 && width > 50 && height > 30 && (
        <text
          x={x + width / 2}
          y={y + height / 2}
          textAnchor="middle"
          fill="#fff"
          fontSize={Math.min(11, fontSize - 1)}
          style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.5)' }}
        >
          {name.length > 15 ? `${name.slice(0, 12)}...` : name}
        </text>
      )}
    </g>
  );
}

// Custom tooltip
interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      name: string;
      value: number;
      category?: string;
      subcategory?: string;
      count?: number;
      confidence?: number;
    };
  }>;
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload;
  const isCategory = !data.subcategory;

  return (
    <div className="bg-card border rounded-lg p-3 shadow-lg">
      <p className="font-semibold text-sm">{data.name}</p>
      <p className="text-lg font-mono font-bold">{formatCurrency(data.value)}</p>
      {!isCategory && (
        <>
          {data.count !== undefined && (
            <p className="text-xs text-muted-foreground">
              Count: {data.count}
            </p>
          )}
          {data.confidence !== undefined && (
            <p className="text-xs text-muted-foreground">
              Confidence: {(data.confidence * 100).toFixed(0)}%
            </p>
          )}
        </>
      )}
      {isCategory && data.category && (
        <p className="text-xs text-muted-foreground mt-1">
          {CATEGORY_CONFIG[data.category]?.description || ''}
        </p>
      )}
    </div>
  );
}

// Category summary cards
function CategorySummaryCards({
  breakdown,
  onCategoryClick,
}: {
  breakdown: ValueBreakdownExpanded;
  onCategoryClick?: (category: string) => void;
}) {
  const categories = [
    { key: 'execution', value: breakdown.execution_value },
    { key: 'decision', value: breakdown.decision_value },
    { key: 'prevention', value: breakdown.prevention_value },
    { key: 'knowledge', value: breakdown.knowledge_value },
  ];

  const total = breakdown.total_value;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      {categories.map(({ key, value }) => {
        const config = CATEGORY_CONFIG[key];
        const percentage = total > 0 ? (value / total) * 100 : 0;

        return (
          <button
            key={key}
            onClick={() => onCategoryClick?.(key)}
            className={cn(
              'p-3 rounded-lg border text-left transition-all',
              'hover:shadow-md hover:border-primary/50',
              'focus:outline-none focus:ring-2 focus:ring-primary/50'
            )}
            style={{ borderLeftColor: config.color, borderLeftWidth: 4 }}
          >
            <p className="text-xs text-muted-foreground">{config.label}</p>
            <p className="text-lg font-bold font-mono">{formatCurrency(value)}</p>
            <div className="flex items-center gap-1 mt-1">
              <div
                className="h-1.5 rounded-full"
                style={{
                  width: `${Math.max(percentage, 5)}%`,
                  backgroundColor: config.color,
                }}
              />
              <span className="text-xs text-muted-foreground">
                {percentage.toFixed(0)}%
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// Subcategory detail table
function SubcategoryDetailTable({
  breakdown,
  selectedCategory,
  onSubcategoryClick,
}: {
  breakdown: ValueBreakdownExpanded;
  selectedCategory?: string;
  onSubcategoryClick?: (subcategory: string, parentCategory: string) => void;
}) {
  const subcategories = useMemo(() => {
    const all = Object.values(breakdown.by_subcategory);

    if (selectedCategory) {
      return all.filter((s) => s.parent_type === selectedCategory);
    }

    return all.sort((a, b) => b.value_usd - a.value_usd);
  }, [breakdown.by_subcategory, selectedCategory]);

  if (subcategories.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h4 className="text-sm font-medium mb-2">
        {selectedCategory
          ? `${CATEGORY_CONFIG[selectedCategory]?.label || selectedCategory} Details`
          : 'All Subcategories'}
      </h4>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-2 font-medium">Subcategory</th>
              <th className="text-right p-2 font-medium">Value</th>
              <th className="text-right p-2 font-medium">Count</th>
              <th className="text-right p-2 font-medium">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {subcategories.slice(0, 10).map((sub) => (
              <tr
                key={sub.subcategory}
                className="border-t hover:bg-muted/30 cursor-pointer"
                onClick={() =>
                  onSubcategoryClick?.(sub.subcategory, sub.parent_type)
                }
              >
                <td className="p-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{
                        backgroundColor:
                          CATEGORY_CONFIG[sub.parent_type]?.color || '#A5A66A',
                      }}
                    />
                    {SUBCATEGORY_LABELS[sub.subcategory] || sub.subcategory}
                  </div>
                </td>
                <td className="p-2 text-right font-mono">
                  {formatCurrency(sub.value_usd)}
                </td>
                <td className="p-2 text-right text-muted-foreground">
                  {sub.count}
                </td>
                <td className="p-2 text-right text-muted-foreground">
                  {(sub.confidence * 100).toFixed(0)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ValueAttributionBreakdown({
  data,
  isLoading,
  onCategoryClick,
  onSubcategoryClick,
}: ValueAttributionBreakdownProps) {
  const { t } = useTranslation(['analytics']);
  const colors = useChartColors();
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();

  const treemapData = useMemo(() => {
    if (!data?.breakdown) return null;
    return transformToTreemapData(data.breakdown);
  }, [data]);

  const handleCategoryClick = (category: string) => {
    setSelectedCategory(selectedCategory === category ? undefined : category);
    onCategoryClick?.(category);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="h-5 w-48 bg-muted rounded animate-pulse" />
          <div className="h-4 w-64 bg-muted rounded animate-pulse mt-1" />
        </CardHeader>
        <CardContent>
          <div className="h-[400px] bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (!data?.breakdown || data.breakdown.total_value === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:valueBreakdown.title', 'Value Attribution Breakdown')}</CardTitle>
          <CardDescription>
            {t('analytics:valueBreakdown.description', 'Hierarchical view of value by category and subcategory')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {t('analytics:valueBreakdown.noData', 'No value attribution data available')}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{t('analytics:valueBreakdown.title', 'Value Attribution Breakdown')}</CardTitle>
            <CardDescription>
              {t('analytics:valueBreakdown.description', 'Hierarchical view of value by category and subcategory')}
            </CardDescription>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold font-mono">
              {formatCurrency(data.breakdown.total_value)}
            </p>
            <p className="text-xs text-muted-foreground">
              {data.breakdown.attribution_count} attributions | {(data.breakdown.average_confidence * 100).toFixed(0)}% avg confidence
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Category summary cards */}
        <CategorySummaryCards
          breakdown={data.breakdown}
          onCategoryClick={handleCategoryClick}
        />

        {/* Treemap visualization */}
        {treemapData && treemapData.children.length > 0 && (
          <div className="h-[350px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={treemapData.children}
                dataKey="value"
                aspectRatio={4 / 3}
                stroke="#fff"
                fill="#8884d8"
                content={<CustomTreemapContent x={0} y={0} width={0} height={0} name="" value={0} color="" depth={0} index={0} />}
                isAnimationActive={false}
              >
                <Tooltip content={<CustomTooltip />} />
              </Treemap>
            </ResponsiveContainer>
          </div>
        )}

        {/* Subcategory detail table */}
        <SubcategoryDetailTable
          breakdown={data.breakdown}
          selectedCategory={selectedCategory}
          onSubcategoryClick={onSubcategoryClick}
        />
      </CardContent>
    </Card>
  );
}

export default ValueAttributionBreakdown;
