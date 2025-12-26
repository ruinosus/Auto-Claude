import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { formatCurrency } from './utils/formatters';
import { useChartColors } from './utils/useChartColors';

interface CostDataPoint {
  timestamp: string;
  cost: number;
}

interface CostChartProps {
  data: CostDataPoint[];
  budgetLimit?: number;
}

export function CostChart({ data, budgetLimit }: CostChartProps) {
  const chartColors = useChartColors();

  if (data.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Cost Over Time</h3>
        <div className="flex items-center justify-center h-[300px]">
          <div className="text-center">
            <p className="text-muted-foreground">No data available for this period</p>
            <p className="text-sm text-muted-foreground mt-1">
              Run a spec to start collecting analytics
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Format data for Recharts
  const formattedData = data.map((point) => ({
    ...point,
    date: format(parseISO(point.timestamp), 'MMM dd')
  }));

  return (
    <div className="rounded-lg border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Cost Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            className="text-xs"
            tick={{ fill: chartColors.muted }}
          />
          <YAxis
            className="text-xs"
            tick={{ fill: chartColors.muted }}
            tickFormatter={(value) => formatCurrency(value, 2)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: chartColors.card,
              border: `1px solid ${chartColors.border}`,
              borderRadius: '8px'
            }}
            formatter={(value: number) => [formatCurrency(value, 2), 'Cost']}
          />
          <Line
            type="monotone"
            dataKey="cost"
            stroke={chartColors.chart1}
            strokeWidth={2}
            dot={{ fill: chartColors.chart1 }}
          />
          {budgetLimit && (
            <ReferenceLine
              y={budgetLimit}
              stroke={chartColors.destructive}
              strokeDasharray="3 3"
              label={{ value: 'Budget', position: 'right' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
