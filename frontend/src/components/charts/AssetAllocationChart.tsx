import React from 'react';
import { useSelector } from 'react-redux';
import { Box, CircularProgress, Typography } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { RootState } from '../../store';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

const AssetAllocationChart: React.FC = () => {
  const { assets, loading } = useSelector((state: RootState) => state.assets);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  // Group assets by type and calculate total value
  const assetsByType = assets.reduce((acc: any, asset: any) => {
    const type = asset.asset_type || 'Other';
    if (!acc[type]) {
      acc[type] = 0;
    }
    acc[type] += asset.current_value || 0;
    return acc;
  }, {});

  const chartData = Object.entries(assetsByType).map(([name, value]) => ({
    name: name.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
    value,
  }));

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (chartData.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
        <Typography color="text.secondary">No assets to display</Typography>
      </Box>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart margin={{ left: 20, right: 20 }}>
        <Pie
          data={chartData}
          cx="35%"
          cy="50%"
          labelLine={true}
          label={({ percent }) => `${(percent * 100).toFixed(1)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => formatCurrency(value)}
          contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
        />
        <Legend
          layout="vertical"
          verticalAlign="middle"
          align="right"
          wrapperStyle={{ paddingLeft: '20px', fontSize: '12px' }}
          formatter={(value) => value}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default AssetAllocationChart;

// Made with Bob
