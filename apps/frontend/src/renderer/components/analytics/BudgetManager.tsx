import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { formatCurrencyDual } from './utils/formatters';

interface BudgetManagerProps {
  currentCost: number;
  budgetLimit?: number;
  onBudgetChange?: (limit: number) => void;
}

export function BudgetManager({ currentCost, budgetLimit, onBudgetChange }: BudgetManagerProps) {
  const [budgetInput, setBudgetInput] = useState(budgetLimit?.toString() || '');

  const handleSetBudget = () => {
    const limit = parseFloat(budgetInput);
    if (!isNaN(limit) && limit > 0) {
      if (onBudgetChange) {
        onBudgetChange(limit);
      }
    }
  };

  const budgetProgress = budgetLimit ? (currentCost / budgetLimit) * 100 : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Budget Manager</CardTitle>
        <CardDescription>Set and track your spending limits</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Budget input form */}
          <div className="flex gap-2">
            <Input
              type="number"
              placeholder="Budget limit ($)"
              value={budgetInput}
              onChange={(e) => setBudgetInput(e.target.value)}
              min="0"
              step="0.01"
            />
            <Button onClick={handleSetBudget}>Set Budget</Button>
          </div>

          {/* Current usage display */}
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Current Cost:</span>
            <span className="font-semibold">{formatCurrencyDual(currentCost, 2)}</span>
          </div>

          {budgetLimit && (
            <>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Budget Limit:</span>
                <span className="font-semibold">{formatCurrencyDual(budgetLimit, 2)}</span>
              </div>

              {/* Progress bar with color coding */}
              <div>
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>Usage</span>
                  <span>{budgetProgress.toFixed(1)}%</span>
                </div>
                <div className="h-2 rounded-full bg-secondary" role="progressbar">
                  <div
                    className={`h-full rounded-full transition-all ${
                      budgetProgress >= 90
                        ? 'bg-destructive'
                        : budgetProgress >= 80
                        ? 'bg-yellow-500'
                        : 'bg-primary'
                    }`}
                    style={{ width: `${Math.min(budgetProgress, 100)}%` }}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
