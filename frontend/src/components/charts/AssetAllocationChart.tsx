import React from 'react';
import { Box, Typography, IconButton, Chip } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface ChartDataItem {
  name: string;
  value: number;
}

interface AssetAllocationChartProps {
  data: ChartDataItem[];
  selectedCategory: string | null;
  onSliceClick: (name: string) => void;
  onBack: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  'Equity': '#1976d2',
  'Debt Mutual Fund': '#00838f',
  'Fixed Income': '#0097a7',
  'Govt. Schemes': '#388e3c',
  'Commodities': '#f57c00',
  'Crypto': '#7b1fa2',
  'Real Estate': '#d32f2f',
  'Other': '#757575',
  'Bank Accounts': '#0288d1',
  'Demat Cash': '#5d4037',
};

const TYPE_COLORS = [
  '#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0',
  '#00BCD4', '#FF5722', '#607D8B', '#8BC34A', '#FFC107',
  '#3F51B5', '#009688', '#795548', '#CDDC39', '#F44336',
];

const AssetAllocationChart: React.FC<AssetAllocationChartProps> = ({
  data,
  selectedCategory,
  onSliceClick,
  onBack,
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (data.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
        <Typography color="text.secondary">No assets to display</Typography>
      </Box>
    );
  }

  const getColor = (index: number, name: string) => {
    if (!selectedCategory) {
      return CATEGORY_COLORS[name] || TYPE_COLORS[index % TYPE_COLORS.length];
    }
    return TYPE_COLORS[index % TYPE_COLORS.length];
  };

  return (
    <Box>
      {selectedCategory && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <IconButton size="small" onClick={onBack} title="Back to categories">
            <ArrowBack fontSize="small" />
          </IconButton>
          <Chip label={selectedCategory} size="small" color="primary" variant="outlined" />
        </Box>
      )}
      <ResponsiveContainer width="100%" height={selectedCategory ? 270 : 300}>
        <PieChart margin={{ left: 20, right: 20 }}>
          <Pie
            data={data}
            cx="35%"
            cy="50%"
            labelLine={false}
            label={false}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            style={{ cursor: selectedCategory ? 'default' : 'pointer' }}
            onClick={(_, index) => {
              if (!selectedCategory) {
                onSliceClick(data[index].name);
              }
            }}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(index, entry.name)} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }: any) => {
              if (!active || !payload?.length) return null;
              return (
                <Box sx={{ bgcolor: '#fff', border: '1px solid #ccc', p: 1.5, borderRadius: 1, boxShadow: 1 }}>
                  <Typography variant="body2" fontWeight="bold">{payload[0].name}</Typography>
                  <Typography variant="body2" color="text.secondary">{formatCurrency(payload[0].value)}</Typography>
                </Box>
              );
            }}
          />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            wrapperStyle={{
              paddingLeft: '20px',
              fontSize: '12px',
              cursor: selectedCategory ? 'default' : 'pointer',
            }}
            formatter={(value: string, entry: any) => {
              const total = data.reduce((sum, d) => sum + d.value, 0);
              const pct = total > 0 ? ((entry.payload.value / total) * 100).toFixed(1) : '0.0';
              return `${value} (${pct}%)`;
            }}
            onClick={(data: any) => {
              if (!selectedCategory && data?.value) {
                onSliceClick(data.value as string);
              }
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default AssetAllocationChart;
