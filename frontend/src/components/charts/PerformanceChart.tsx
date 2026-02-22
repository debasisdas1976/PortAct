import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  CircularProgress,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ToggleButtonGroup,
  ToggleButton,
  Stack,
} from '@mui/material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { AppDispatch, RootState } from '../../store';
import { fetchPortfolioPerformance, fetchAssetPerformance, fetchAssetsList } from '../../store/slices/portfolioSlice';

interface PerformanceChartProps {
  hideNumbers?: boolean;
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({ hideNumbers = false }) => {
  const dispatch = useDispatch<AppDispatch>();
  const { performanceData, assetPerformanceData, assetsList, performanceLoading: loading, performanceError: error, selectedPortfolioId } = useSelector(
    (state: RootState) => state.portfolio
  );

  const [viewMode, setViewMode] = useState<'portfolio' | 'asset'>('portfolio');
  const [selectedAssetId, setSelectedAssetId] = useState<number | ''>('');
  const [timePeriod, setTimePeriod] = useState<number>(30);

  useEffect(() => {
    // Fetch assets list for current portfolio
    dispatch(fetchAssetsList(selectedPortfolioId));
    // Fetch initial portfolio performance data
    dispatch(fetchPortfolioPerformance({ days: 30, portfolioId: selectedPortfolioId }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPortfolioId]);

  useEffect(() => {
    if (viewMode === 'portfolio') {
      dispatch(fetchPortfolioPerformance({ days: timePeriod, portfolioId: selectedPortfolioId }));
    } else if (viewMode === 'asset' && selectedAssetId) {
      dispatch(fetchAssetPerformance({ assetId: selectedAssetId as number, days: timePeriod }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, selectedAssetId, timePeriod]);

  const formatCurrency = (value: number, hide: boolean = false) => {
    if (hide) {
      return '₹ ••••••';
    }
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

  const handleViewModeChange = (_event: React.MouseEvent<HTMLElement>, newMode: 'portfolio' | 'asset' | null) => {
    if (newMode !== null) {
      setViewMode(newMode);
      if (newMode === 'asset' && assetsList.length > 0 && !selectedAssetId) {
        setSelectedAssetId(assetsList[0].id);
      }
    }
  };

  const handleAssetChange = (event: any) => {
    setSelectedAssetId(event.target.value);
  };

  const handleTimePeriodChange = (_event: React.MouseEvent<HTMLElement>, newPeriod: number | null) => {
    if (newPeriod !== null) {
      setTimePeriod(newPeriod);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
        <Typography color="error">
          Failed to load performance data. Please try refreshing the page.
        </Typography>
      </Box>
    );
  }

  // Prepare chart data based on view mode
  let chartData: any[] = [];

  if (viewMode === 'portfolio' && performanceData?.snapshots) {
    chartData = performanceData.snapshots.map((item: any) => ({
      date: formatDate(item.date),
      value: item.total_current_value,
      invested: item.total_invested,
      gainLoss: item.total_profit_loss,
      returnPercentage: item.total_profit_loss_percentage,
    }));
  } else if (viewMode === 'asset' && assetPerformanceData?.snapshots) {
    chartData = assetPerformanceData.snapshots.map((item: any) => ({
      date: formatDate(item.date),
      value: item.current_value,
      invested: item.total_invested,
      gainLoss: item.profit_loss,
      returnPercentage: item.profit_loss_percentage,
    }));
  }

  if (chartData.length === 0) {
    return (
      <Box>
        <Stack spacing={2} sx={{ mb: 2 }}>
          <Stack direction="row" spacing={2} flexWrap="wrap" alignItems="center">
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={handleViewModeChange}
              size="small"
            >
              <ToggleButton value="portfolio">Portfolio</ToggleButton>
              <ToggleButton value="asset">Individual Asset</ToggleButton>
            </ToggleButtonGroup>
  
            <ToggleButtonGroup
              value={timePeriod}
              exclusive
              onChange={handleTimePeriodChange}
              size="small"
            >
              <ToggleButton value={7}>7D</ToggleButton>
              <ToggleButton value={30}>30D</ToggleButton>
              <ToggleButton value={90}>90D</ToggleButton>
              <ToggleButton value={180}>6M</ToggleButton>
              <ToggleButton value={365}>1Y</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
  
          {viewMode === 'asset' && (
            <FormControl size="small" sx={{ minWidth: 250, maxWidth: 400 }}>
              <InputLabel sx={{ fontSize: '0.875rem' }}>Select Asset</InputLabel>
              <Select
                value={selectedAssetId}
                onChange={handleAssetChange}
                label="Select Asset"
                sx={{ fontSize: '0.875rem' }}
              >
                {assetsList.map((asset: any) => (
                  <MenuItem
                    key={asset.id}
                    value={asset.id}
                    sx={{ fontSize: '0.875rem' }}
                  >
                    {asset.name} ({asset.symbol || asset.type})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Stack>

        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
          <Typography color="text.secondary">
            No performance data available yet. Historical data will be captured daily at 7 PM.
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap">
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewModeChange}
          size="small"
        >
          <ToggleButton value="portfolio">Portfolio</ToggleButton>
          <ToggleButton value="asset">Individual Asset</ToggleButton>
        </ToggleButtonGroup>

        {viewMode === 'asset' && (
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Select Asset</InputLabel>
            <Select
              value={selectedAssetId}
              onChange={handleAssetChange}
              label="Select Asset"
            >
              {assetsList.map((asset: any) => (
                <MenuItem key={asset.id} value={asset.id}>
                  {asset.name} ({asset.symbol || asset.type})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        <ToggleButtonGroup
          value={timePeriod}
          exclusive
          onChange={handleTimePeriodChange}
          size="small"
        >
          <ToggleButton value={7}>7D</ToggleButton>
          <ToggleButton value={30}>30D</ToggleButton>
          <ToggleButton value={90}>90D</ToggleButton>
          <ToggleButton value={180}>6M</ToggleButton>
          <ToggleButton value={365}>1Y</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2196f3" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#2196f3" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorInvested" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff9800" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ff9800" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis
            tickFormatter={(value) => hideNumbers ? '•••' : formatCurrency(value)}
            width={100}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'returnPercentage') {
                return [hideNumbers ? '••••' : `${value.toFixed(2)}%`, 'Return %'];
              }
              if (name === 'value') {
                return [formatCurrency(value, hideNumbers), 'Current Value'];
              }
              if (name === 'invested') {
                return [formatCurrency(value, hideNumbers), 'Invested'];
              }
              if (name === 'gainLoss') {
                return [formatCurrency(value, hideNumbers), 'Gain/Loss'];
              }
              return [formatCurrency(value, hideNumbers), name];
            }}
            labelStyle={{ color: '#000' }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#2196f3"
            fillOpacity={1}
            fill="url(#colorValue)"
            name="Current Value"
          />
          <Area
            type="monotone"
            dataKey="invested"
            stroke="#ff9800"
            fillOpacity={1}
            fill="url(#colorInvested)"
            name="Invested"
          />
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default PerformanceChart;

// Made with Bob
