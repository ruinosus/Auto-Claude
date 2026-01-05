/**
 * QualityMultiplierBadge - Displays quality multiplier with color coding and tooltip
 *
 * Shows the quality multiplier value as a badge:
 * - Green: multiplier > 1.0 (good quality)
 * - Gray: multiplier = 1.0 (neutral)
 * - Red: multiplier < 1.0 (poor quality)
 *
 * Hover tooltip shows breakdown of all adjustments.
 */

import React from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../../ui/tooltip';

export interface QualityAdjustment {
  reason: string;
  delta: number;
}

export interface QualityMultiplierData {
  base_value: number;
  adjustments: QualityAdjustment[];
  final_multiplier: number;
  tier: 'exceptional' | 'good' | 'neutral' | 'low' | 'poor';
  color: 'green' | 'blue' | 'gray' | 'yellow' | 'red';
}

interface QualityMultiplierBadgeProps {
  multiplier: QualityMultiplierData;
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

const colorClasses = {
  green: 'bg-green-500/10 text-green-500 border-green-500/20',
  blue: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  gray: 'bg-muted text-muted-foreground border-border',
  yellow: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  red: 'bg-red-500/10 text-red-500 border-red-500/20',
};

const tierLabels = {
  exceptional: 'Exceptional',
  good: 'Good',
  neutral: 'Neutral',
  low: 'Low',
  poor: 'Poor',
};

export function QualityMultiplierBadge({
  multiplier,
  showTooltip = true,
  size = 'md',
  className = '',
}: QualityMultiplierBadgeProps) {
  const Icon =
    multiplier.final_multiplier > 1.0
      ? TrendingUp
      : multiplier.final_multiplier < 1.0
        ? TrendingDown
        : Minus;

  const badge = (
    <span
      className={`
        inline-flex items-center gap-1 rounded-md border font-semibold
        ${sizeClasses[size]}
        ${colorClasses[multiplier.color]}
        ${className}
      `}
    >
      <Icon className={size === 'sm' ? 'h-3 w-3' : size === 'md' ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
      <span className="font-mono">{multiplier.final_multiplier.toFixed(2)}x</span>
    </span>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="space-y-2">
            {/* Header */}
            <div className="flex items-center justify-between gap-4 border-b border-border pb-2">
              <span className="font-semibold text-foreground">Quality Multiplier</span>
              <span className={`text-sm font-medium ${
                multiplier.color === 'green' ? 'text-green-500' :
                multiplier.color === 'red' ? 'text-red-500' :
                multiplier.color === 'yellow' ? 'text-yellow-500' :
                'text-muted-foreground'
              }`}>
                {tierLabels[multiplier.tier]}
              </span>
            </div>

            {/* Adjustments */}
            {multiplier.adjustments.length > 0 ? (
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Adjustments
                </div>
                <ul className="space-y-0.5">
                  {multiplier.adjustments.map((adj, idx) => (
                    <li
                      key={idx}
                      className="flex items-center justify-between gap-3 text-xs"
                    >
                      <span className="text-muted-foreground">{adj.reason}</span>
                      <span
                        className={`font-mono font-medium ${
                          adj.delta > 0
                            ? 'text-green-500'
                            : adj.delta < 0
                              ? 'text-red-500'
                              : 'text-muted-foreground'
                        }`}
                      >
                        {adj.delta > 0 ? '+' : ''}
                        {(adj.delta * 100).toFixed(0)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">No adjustments</div>
            )}

            {/* Final value */}
            <div className="flex items-center justify-between gap-4 border-t border-border pt-2">
              <span className="text-xs text-muted-foreground">Final Multiplier</span>
              <span className="font-mono font-semibold">
                {multiplier.final_multiplier.toFixed(2)}x
              </span>
            </div>

            {/* Info text */}
            <div className="flex items-start gap-1.5 pt-1 text-[10px] text-muted-foreground">
              <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
              <span>
                ROI value is multiplied by this factor based on code quality signals.
              </span>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Compact version for use in tables and lists
 */
export function QualityMultiplierCompact({
  multiplier,
  className = '',
}: {
  multiplier: QualityMultiplierData;
  className?: string;
}) {
  return (
    <QualityMultiplierBadge
      multiplier={multiplier}
      size="sm"
      className={className}
    />
  );
}

/**
 * Inline multiplier value without badge styling
 */
export function QualityMultiplierInline({
  multiplier,
  showIcon = true,
  className = '',
}: {
  multiplier: QualityMultiplierData;
  showIcon?: boolean;
  className?: string;
}) {
  const textColor =
    multiplier.color === 'green'
      ? 'text-green-500'
      : multiplier.color === 'red'
        ? 'text-red-500'
        : multiplier.color === 'yellow'
          ? 'text-yellow-500'
          : 'text-muted-foreground';

  const Icon =
    multiplier.final_multiplier > 1.0
      ? TrendingUp
      : multiplier.final_multiplier < 1.0
        ? TrendingDown
        : null;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={`inline-flex items-center gap-1 font-mono ${textColor} ${className}`}>
            {showIcon && Icon && <Icon className="h-3 w-3" />}
            {multiplier.final_multiplier.toFixed(2)}x
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          <span className="font-medium">{tierLabels[multiplier.tier]}</span>
          {' - '}
          {multiplier.adjustments.length} adjustment{multiplier.adjustments.length !== 1 ? 's' : ''}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default QualityMultiplierBadge;
