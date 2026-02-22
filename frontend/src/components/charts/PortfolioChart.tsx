import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, CircularProgress, Typography } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { AppDispatch, RootState } from '../../store';
import { fetchPortfolioPerformance } from '../../store/slices/portfolioSlice';

const PortfolioChart: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { performanceData, performanceLoading: loading, performanceError: error, selectedPortfolioId } = useSelector((state: RootState) => state.portfolio);

  useEffect(() => {
    // Fetch 90 days of data for the bottom chart
    dispatch(fetchPortfolioPerformance({ days: 90, portfolioId: selectedPortfolioId }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPortfolioId]);

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

  if (error) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
        <Typography color="error">
          Failed to load chart data. Please try refreshing the page.
        </Typography>
      </Box>
    );
  }

  if (!performanceData?.snapshots || performanceData.snapshots.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
        <Typography color="text.secondary">
          No portfolio history available yet. Historical data will be captured daily at 7 PM.
        </Typography>
      </Box>
    );
  }

  const chartData = performanceData.snapshots.map((item: any) => ({
    date: formatDate(item.date),
    value: item.total_current_value,
    invested: item.total_invested,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis tickFormatter={(value) => formatCurrency(value)} />
        <Tooltip
          formatter={(value: number) => formatCurrency(value)}
          labelStyle={{ color: '#000' }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#1976d2"
          strokeWidth={2}
          name="Portfolio Value"
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="invested"
          stroke="#9c27b0"
          strokeWidth={2}
          name="Total Invested"
          dot={false}
          strokeDasharray="5 5"
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default PortfolioChart;

// Made with Bob
