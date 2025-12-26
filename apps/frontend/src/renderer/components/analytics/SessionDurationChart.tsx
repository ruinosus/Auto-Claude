import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../ui/card';

interface SessionDurationData {
  phase: string;
  avg_duration_seconds: number;
}

interface SessionDurationChartProps {
  data: SessionDurationData[];
}

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border bg-background p-2 shadow-sm">
        <div className="grid grid-cols-2 gap-2">
          <div className="flex flex-col">
            <span className="text-[0.70rem] uppercase text-muted-foreground">
              Phase
            </span>
            <span className="font-bold text-muted-foreground capitalize">
              {payload[0].payload.phase}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-[0.70rem] uppercase text-muted-foreground">
              Duration
            </span>
            <span className="font-bold">
              {formatDuration(payload[0].value)}
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export function SessionDurationChart({ data }: SessionDurationChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Session Duration by Phase</CardTitle>
          <CardDescription>Average time spent in each phase</CardDescription>
        </CardHeader>
        <CardContent className="flex h-[300px] items-center justify-center">
          <p className="text-sm text-muted-foreground">
            No data available. Session duration will appear once sessions are completed.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Session Duration by Phase</CardTitle>
        <CardDescription>Average time spent in each phase</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              tickFormatter={formatDuration}
            />
            <YAxis
              dataKey="phase"
              type="category"
              tickFormatter={(value) => value.charAt(0).toUpperCase() + value.slice(1)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="avg_duration_seconds"
              fill="hsl(var(--primary))"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
