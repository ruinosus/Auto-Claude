import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { useChartColorArray } from './utils/useChartColors';

interface ModelDistributionData {
  model: string;
  count: number;
  percentage: number;
}

interface ModelDistributionChartProps {
  data: ModelDistributionData[];
}

const renderCustomLabel = (entry: any) => {
  return `${entry.percentage.toFixed(1)}%`;
};

export const ModelDistributionChart: React.FC<ModelDistributionChartProps> = ({
  data
}) => {
  const colors = useChartColorArray();

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Model Distribution</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <p className="text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={80}
              fill="#8884d8"
              dataKey="count"
              nameKey="model"
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${entry.model}`}
                  fill={colors[index % colors.length]}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [
                `${value} messages`,
                name
              ]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};
