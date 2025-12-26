import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

interface TokensDataPoint {
  spec_id: string;
  input_tokens: number;
  output_tokens: number;
}

interface TokensChartProps {
  data: TokensDataPoint[];
}

export function TokensChart({ data }: TokensChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Tokens By Spec</h3>
        <div className="flex items-center justify-center h-[300px]">
          <div className="text-center">
            <p className="text-muted-foreground">No data available</p>
          </div>
        </div>
      </div>
    );
  }

  // Format large numbers for axis
  const formatTokens = (value: number): string => {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
    return value.toString();
  };

  return (
    <div className="rounded-lg border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Tokens By Spec</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="spec_id"
            className="text-xs"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
          />
          <YAxis
            className="text-xs"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
            tickFormatter={formatTokens}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px'
            }}
            formatter={(value: number) => [formatTokens(value), '']}
          />
          <Legend />
          <Bar dataKey="input_tokens" stackId="a" fill="hsl(var(--primary))" name="Input" />
          <Bar dataKey="output_tokens" stackId="a" fill="hsl(var(--chart-2))" name="Output" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
