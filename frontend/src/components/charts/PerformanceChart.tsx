import React from 'react';
import { useSelector } from 'react-redux';
import { Box, CircularProgress, Typography } from '@mui/material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { RootState } from '../../store';

const PerformanceChart: React.FC = () => {
  const { history, loading } = useSelector((state: RootState) => state.portfolio);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  };

  if (!history || history.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
        <Typography color="text.secondary">No performance data available yet</Typography>
      </Box>
    );
  }

  const chartData = history.map((item) => ({
    date: formatDate(item.date),
    gainLoss: item.total_value - item.total_invested,
    returnPercentage: ((item.total_value - item.total_invested) / item.total_invested) * 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="colorGainLoss" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#4caf50" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#4caf50" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis tickFormatter={(value) => formatCurrency(value)} />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === 'returnPercentage') {
              return [`${value.toFixed(2)}%`, 'Return %'];
            }
            return [formatCurrency(value), 'Gain/Loss'];
          }}
          labelStyle={{ color: '#000' }}
        />
        <Area
          type="monotone"
          dataKey="gainLoss"
          stroke="#4caf50"
          fillOpacity={1}
          fill="url(#colorGainLoss)"
          name="Gain/Loss"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default PerformanceChart;

// Made with Bob
