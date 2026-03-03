import React from 'react';
import { Box, Typography, IconButton, Chip, useMediaQuery, useTheme } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface ChartDataItem {
  key: string;
  name: string;
  value: number;
}

interface AssetAllocationChartProps {
  data: ChartDataItem[];
  selectedCategory: string | null;
  onSliceClick: (name: string) => void;
  onTypeClick?: (typeKey: string) => void;
  onBack: () => void;
}

// Colors match the asset_categories master table (seed_data.json)
const CATEGORY_COLORS: Record<string, string> = {
  'Equity': '#1976d2',
  'Hybrid': '#5c6bc0',
  'Fixed Income': '#0097a7',
  'Govt. Schemes': '#388e3c',
  'Commodities': '#f57c00',
  'Retirement Plans': '#00695c',
  'Crypto': '#7b1fa2',
  'Real Estate': '#d32f2f',
  'Cash': '#26a69a',
  'Other': '#757575',
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
  onTypeClick,
  onBack,
}) => {
  const theme = useTheme();
  const isLarge = useMediaQuery(theme.breakpoints.up('lg'));
  const isMedium = useMediaQuery(theme.breakpoints.up('md'));
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));

  // Adaptive sizing based on viewport
  const containerHeight = isSmall ? 500 : 400;
  const legendFontSize = isLarge ? '14px' : isMedium ? '13px' : '12px';
  // On small screens, stack legend below the pie; otherwise legend on the right
  const legendLayout = isSmall ? 'horizontal' as const : 'vertical' as const;
  const legendAlign = isSmall ? 'center' as const : 'right' as const;
  const legendVerticalAlign = isSmall ? 'bottom' as const : 'middle' as const;
  // Percentage-based radius scales with actual container size
  const outerRadius = isSmall ? '35%' : '60%';
  const pieCx = isSmall ? '50%' : '35%';
  const chartMargin = isSmall
    ? { left: 0, right: 0, top: 0, bottom: 0 }
    : { left: 0, right: 0, top: 0, bottom: 0 };

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
    <Box sx={{ height: isSmall ? 540 : 440 }}>
      {selectedCategory && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <IconButton size="small" onClick={onBack} title="Back to categories">
            <ArrowBack fontSize="small" />
          </IconButton>
          <Chip label={selectedCategory} size="small" color="primary" variant="outlined" />
        </Box>
      )}
      <ResponsiveContainer width="100%" height={containerHeight}>
        <PieChart margin={chartMargin}>
          <Pie
            data={data}
            cx={pieCx}
            cy={isSmall ? '40%' : '50%'}
            labelLine={false}
            label={false}
            outerRadius={outerRadius}
            fill="#8884d8"
            dataKey="value"
            style={{ cursor: 'pointer' }}
            onClick={(_, index) => {
              if (!selectedCategory) {
                onSliceClick(data[index].name);
              } else if (onTypeClick) {
                onTypeClick(data[index].key);
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
            layout={legendLayout}
            verticalAlign={legendVerticalAlign}
            align={legendAlign}
            wrapperStyle={{
              paddingLeft: isSmall ? '0' : '20px',
              paddingTop: isSmall ? '10px' : '0',
              fontSize: legendFontSize,
              cursor: 'pointer',
            }}
            formatter={(value: string, entry: any) => {
              const total = data.reduce((sum, d) => sum + d.value, 0);
              const pct = total > 0 ? ((entry.payload.value / total) * 100).toFixed(1) : '0.0';
              return `${value} (${pct}%)`;
            }}
            onClick={(entry: any) => {
              if (!selectedCategory && entry?.value) {
                onSliceClick(entry.value as string);
              } else if (selectedCategory && onTypeClick && entry?.payload?.key) {
                onTypeClick(entry.payload.key);
              }
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default AssetAllocationChart;
