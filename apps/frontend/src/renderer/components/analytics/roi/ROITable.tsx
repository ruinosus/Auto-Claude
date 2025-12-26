import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../ui/table';
import { Badge } from '../../ui/badge';
import { CheckCircle, XCircle } from 'lucide-react';
import type { SpecROIWithMetrics } from '../../../../shared/types/roi';

export interface ROITableProps {
  specs: SpecROIWithMetrics[];
  isLoading?: boolean;
  onSpecClick?: (specId: string) => void;
}

export function ROITable({ specs, isLoading, onSpecClick }: ROITableProps) {
  const { t } = useTranslation(['analytics']);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="h-5 w-32 bg-muted rounded animate-pulse" />
          <div className="h-4 w-48 bg-muted rounded animate-pulse mt-1" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (specs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:roi.table.title')}</CardTitle>
          <CardDescription>{t('analytics:roi.table.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">
            {t('analytics:roi.table.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics:roi.table.title')}</CardTitle>
        <CardDescription>{t('analytics:roi.table.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border overflow-auto max-h-[400px]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('analytics:roi.table.spec')}</TableHead>
                <TableHead className="text-right">{t('analytics:roi.table.actualCost')}</TableHead>
                <TableHead className="text-right">{t('analytics:roi.table.savings')}</TableHead>
                <TableHead className="text-right">{t('analytics:roi.table.roi')}</TableHead>
                <TableHead className="text-center">{t('analytics:roi.table.status')}</TableHead>
                <TableHead className="text-right">{t('analytics:roi.table.linesChanged')}</TableHead>
                <TableHead>{t('analytics:roi.table.date')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {specs.map((spec) => (
                <TableRow
                  key={spec.specId}
                  className={onSpecClick ? 'cursor-pointer hover:bg-muted/50' : ''}
                  onClick={() => onSpecClick?.(spec.specId)}
                >
                  <TableCell className="font-mono text-sm">
                    {spec.specId.slice(0, 16)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(spec.actualCost)}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={spec.metrics.costSavings >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatCurrency(spec.metrics.costSavings)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge variant={spec.metrics.roiPercentage >= 0 ? 'default' : 'destructive'}>
                      {spec.metrics.roiPercentage.toFixed(0)}%
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    {spec.qaPassed ? (
                      <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mx-auto" />
                    )}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    +{spec.linesAdded}/-{spec.linesRemoved}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(spec.completedAt || spec.createdAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
