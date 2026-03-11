import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton,
  Stack,
  IconButton,
  Tooltip,
  useMediaQuery,
  useTheme,
  Chip,
  Autocomplete,
  TextField,
} from '@mui/material';
import { Visibility, VisibilityOff, ArrowBack } from '@mui/icons-material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  ReferenceLine,
} from 'recharts';
import { insightsAPI, dashboardAPI } from '../services/api';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

// Colors match the asset_categories master table
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

const ASSET_COLORS = [
  '#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0',
  '#00BCD4', '#FF5722', '#607D8B', '#8BC34A', '#FFC107',
  '#3F51B5', '#009688', '#795548', '#CDDC39', '#F44336',
];

const formatCurrency = (value: number, hide: boolean = false) => {
  if (hide) return '\u20B9 \u2022\u2022\u2022\u2022\u2022\u2022';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
};

const formatCompactCurrency = (value: number, hide: boolean = false) => {
  if (hide) return '\u2022\u2022\u2022';
  if (value >= 10000000) return `${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
  return value.toFixed(0);
};

const formatDate = (dateString: string) => {
  const d = new Date(dateString);
  return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
};

const AssetInsight: React.FC = () => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  const selectedPortfolioId = useSelectedPortfolio();

  const [hideNumbers, setHideNumbers] = useState(false);

  // Bar chart state
  const [barData, setBarData] = useState<any[]>([]);
  const [barLoading, setBarLoading] = useState(true);
  const [portfolioXirr, setPortfolioXirr] = useState<number | null>(null);

  // Line chart state
  const [lineData, setLineData] = useState<any[]>([]);
  const [lineLoading, setLineLoading] = useState(true);
  const [timePeriod, setTimePeriod] = useState(90);
  const [lineViewMode, setLineViewMode] = useState<'value' | 'xirr'>('value');
  const [drillCategory, setDrillCategory] = useState<string | null>(null);

  // XIRR trend state
  const [xirrTrendData, setXirrTrendData] = useState<any[]>([]);
  const [xirrTrendLoading, setXirrTrendLoading] = useState(false);

  // Track all category/asset keys for line chart
  const [lineKeys, setLineKeys] = useState<string[]>([]);
  // Filter to show specific category or asset in the line chart
  const [selectedLineFilter, setSelectedLineFilter] = useState<string | null>(null);

  // Fetch bar chart data + portfolio XIRR from dashboard overview
  const fetchBarData = useCallback(async () => {
    setBarLoading(true);
    try {
      const [catRes, overviewRes] = await Promise.all([
        insightsAPI.getCategoryAllocationXirr(selectedPortfolioId),
        dashboardAPI.getOverview(selectedPortfolioId),
      ]);
      setBarData(catRes.categories || []);
      setPortfolioXirr(overviewRes.portfolio_summary?.portfolio_xirr ?? null);
    } catch (err) {
      console.error('Failed to fetch category allocation XIRR', err);
    } finally {
      setBarLoading(false);
    }
  }, [selectedPortfolioId]);

  // Fetch line chart data
  const fetchLineData = useCallback(async () => {
    setLineLoading(true);
    try {
      const res = await insightsAPI.getCategoryPerformanceHistory(
        timePeriod,
        selectedPortfolioId,
        drillCategory,
      );

      if (drillCategory && res.data) {
        // Drill-down: data[].assets = { assetName: { invested, value } }
        const allAssetNames = new Set<string>();
        res.data.forEach((d: any) => {
          Object.keys(d.assets || {}).forEach((name) => allAssetNames.add(name));
        });
        const assetNames = Array.from(allAssetNames);
        setLineKeys(assetNames);

        const chartData = res.data.map((d: any) => {
          const point: any = { date: formatDate(d.date) };
          assetNames.forEach((name) => {
            point[name] = d.assets?.[name]?.value ?? null;
          });
          return point;
        });
        setLineData(chartData);
      } else if (res.data) {
        // Category-level: data[].categories = { catName: { invested, value } }
        const allCats = new Set<string>();
        res.data.forEach((d: any) => {
          Object.keys(d.categories || {}).forEach((c) => allCats.add(c));
        });
        const catNames = Array.from(allCats);
        setLineKeys(catNames);

        const chartData = res.data.map((d: any) => {
          const point: any = { date: formatDate(d.date) };
          catNames.forEach((cat) => {
            point[cat] = d.categories?.[cat]?.value ?? null;
          });
          return point;
        });
        setLineData(chartData);
      }
    } catch (err) {
      console.error('Failed to fetch category performance history', err);
    } finally {
      setLineLoading(false);
    }
  }, [timePeriod, selectedPortfolioId, drillCategory]);

  // Fetch XIRR trend data
  const fetchXirrTrend = useCallback(async () => {
    setXirrTrendLoading(true);
    try {
      const res = await insightsAPI.getCategoryXirrTrend(timePeriod, selectedPortfolioId);
      if (res.data) {
        const allCats = new Set<string>();
        res.data.forEach((d: any) => {
          Object.keys(d.categories || {}).forEach((c) => allCats.add(c));
        });
        const catNames = Array.from(allCats);
        setLineKeys(catNames);

        const chartData = res.data.map((d: any) => {
          const point: any = { date: formatDate(d.date) };
          catNames.forEach((cat) => {
            point[cat] = d.categories?.[cat] ?? null;
          });
          return point;
        });
        setXirrTrendData(chartData);
      }
    } catch (err) {
      console.error('Failed to fetch XIRR trend', err);
    } finally {
      setXirrTrendLoading(false);
    }
  }, [timePeriod, selectedPortfolioId]);

  useEffect(() => {
    fetchBarData();
  }, [fetchBarData]);

  useEffect(() => {
    if (lineViewMode === 'value') {
      fetchLineData();
    } else {
      fetchXirrTrend();
    }
  }, [lineViewMode, fetchLineData, fetchXirrTrend]);

  const handleTimePeriodChange = (_e: React.MouseEvent<HTMLElement>, val: number | null) => {
    if (val !== null) setTimePeriod(val);
  };

  const handleLineViewChange = (_e: React.MouseEvent<HTMLElement>, val: 'value' | 'xirr' | null) => {
    if (val !== null) {
      setLineViewMode(val);
      setSelectedLineFilter(null);
      if (val === 'xirr') setDrillCategory(null); // XIRR trend is category-only
    }
  };

  const handleCategoryDrill = (catName: string) => {
    if (lineViewMode === 'value' && !drillCategory) {
      setDrillCategory(catName);
      setSelectedLineFilter(null);
    }
  };

  const handleDrillBack = () => {
    setDrillCategory(null);
    setSelectedLineFilter(null);
  };

  const getColor = (key: string, index: number) => {
    return CATEGORY_COLORS[key] || ASSET_COLORS[index % ASSET_COLORS.length];
  };

  // Tooltip for current value bar chart
  const ValueTooltipContent = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <Paper sx={{ p: 1.5, boxShadow: 3 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          {d.name}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Current Value: {formatCurrency(d.current_value, hideNumbers)}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Invested: {formatCurrency(d.total_invested, hideNumbers)}
        </Typography>
      </Paper>
    );
  };

  // Tooltip for XIRR bar chart
  const XirrTooltipContent = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <Paper sx={{ p: 1.5, boxShadow: 3 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          {d.name}
        </Typography>
        <Typography variant="body2" sx={{ color: d.xirr != null && d.xirr >= 0 ? 'success.main' : 'error.main' }}>
          XIRR: {hideNumbers ? '\u2022\u2022\u2022\u2022' : d.xirr != null ? `${d.xirr.toFixed(2)}%` : 'N/A'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Assets: {d.asset_count}
        </Typography>
      </Paper>
    );
  };

  // Custom line chart tooltip
  const LineTooltipContent = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <Paper sx={{ p: 1.5, boxShadow: 3, maxWidth: 280 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          {label}
        </Typography>
        {payload.map((entry: any, i: number) => (
          <Typography key={i} variant="body2" sx={{ color: entry.color }}>
            {entry.name}:{' '}
            {hideNumbers
              ? '\u2022\u2022\u2022\u2022'
              : lineViewMode === 'xirr'
                ? `${entry.value?.toFixed(2)}%`
                : formatCurrency(entry.value)}
          </Typography>
        ))}
      </Paper>
    );
  };

  const isLineChartLoading = lineViewMode === 'value' ? lineLoading : xirrTrendLoading;
  const activeLineData = lineViewMode === 'value' ? lineData : xirrTrendData;
  const visibleLineKeys = selectedLineFilter ? [selectedLineFilter] : lineKeys;

  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Page Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">Asset Insight</Typography>
        <Tooltip title={hideNumbers ? 'Show numbers' : 'Hide numbers'}>
          <IconButton onClick={() => setHideNumbers(!hideNumbers)} size="small">
            {hideNumbers ? <VisibilityOff /> : <Visibility />}
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Section 1a: Category Current Value */}
      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Asset Category — Current Value
        </Typography>

        {barLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : barData.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <Typography color="text.secondary">No asset data available.</Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={isSmall ? 300 : 350}>
            <BarChart
              data={barData}
              margin={{ top: 10, right: 20, left: 10, bottom: isSmall ? 80 : 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: isSmall ? 10 : 12 }}
                angle={isSmall ? -45 : -30}
                textAnchor="end"
                interval={0}
                height={isSmall ? 80 : 60}
              />
              <YAxis
                tickFormatter={(v) => formatCompactCurrency(v, hideNumbers)}
                tick={{ fontSize: 11 }}
              />
              <RechartsTooltip content={<ValueTooltipContent />} />
              <Bar dataKey="current_value" name="Current Value" radius={[4, 4, 0, 0]}>
                {barData.map((entry, index) => (
                  <Cell
                    key={`val-${index}`}
                    fill={CATEGORY_COLORS[entry.name] || '#757575'}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Paper>

      {/* Section 1b: Category XIRR */}
      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Asset Category — XIRR
        </Typography>

        {barLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : barData.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <Typography color="text.secondary">No asset data available.</Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={isSmall ? 300 : 350}>
            <BarChart
              data={barData}
              margin={{ top: 10, right: isSmall ? 100 : 140, left: 10, bottom: isSmall ? 80 : 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: isSmall ? 10 : 12 }}
                angle={isSmall ? -45 : -30}
                textAnchor="end"
                interval={0}
                height={isSmall ? 80 : 60}
              />
              <YAxis
                tickFormatter={(v) => (hideNumbers ? '\u2022\u2022' : `${v}%`)}
                tick={{ fontSize: 11 }}
              />
              <RechartsTooltip content={<XirrTooltipContent />} />
              {portfolioXirr != null && (
                <ReferenceLine
                  y={portfolioXirr}
                  stroke="#E91E63"
                  strokeDasharray="6 4"
                  strokeWidth={2}
                  label={{
                    value: hideNumbers ? 'Portfolio XIRR' : `Portfolio XIRR: ${portfolioXirr}%`,
                    position: 'right',
                    fill: '#E91E63',
                    fontSize: isSmall ? 10 : 12,
                    fontWeight: 600,
                  }}
                />
              )}
              <Bar dataKey="xirr" name="XIRR %" radius={[4, 4, 0, 0]}>
                {barData.map((entry, index) => (
                  <Cell
                    key={`xirr-${index}`}
                    fill={CATEGORY_COLORS[entry.name] || '#757575'}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Paper>

      {/* Section 2: Category Performance Line Chart */}
      <Paper sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
          {drillCategory && (
            <Tooltip title="Back to categories">
              <IconButton onClick={handleDrillBack} size="small">
                <ArrowBack />
              </IconButton>
            </Tooltip>
          )}
          <Typography variant="h6">
            {drillCategory
              ? `${drillCategory} — Asset Performance`
              : lineViewMode === 'xirr'
                ? 'Category XIRR Trend'
                : 'Category Performance Over Time'}
          </Typography>
          {drillCategory && (
            <Chip label={drillCategory} size="small" sx={{ ml: 1 }} />
          )}
        </Stack>

        <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap alignItems="center">
          <ToggleButtonGroup
            value={lineViewMode}
            exclusive
            onChange={handleLineViewChange}
            size="small"
          >
            <ToggleButton value="value">Value</ToggleButton>
            <ToggleButton value="xirr">XIRR Trend</ToggleButton>
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

          {lineKeys.length > 1 && (
            <Autocomplete
              size="small"
              options={lineKeys}
              value={selectedLineFilter}
              onChange={(_e, val) => setSelectedLineFilter(val)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  placeholder={drillCategory ? 'Filter asset...' : 'Filter category...'}
                  variant="outlined"
                  size="small"
                />
              )}
              sx={{ minWidth: 200, maxWidth: 300 }}
              clearOnEscape
            />
          )}
        </Stack>

        {!drillCategory && lineViewMode === 'value' && (
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Click a category in the legend to drill down to individual assets
          </Typography>
        )}

        {isLineChartLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : activeLineData.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <Typography color="text.secondary">
              No performance data available yet. Historical data is captured daily at 7 PM.
            </Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={isSmall ? 350 : 400}>
            <LineChart
              data={activeLineData}
              margin={{ top: 10, right: isSmall ? 80 : 120, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis
                tickFormatter={(v) =>
                  lineViewMode === 'xirr'
                    ? hideNumbers ? '\u2022\u2022' : `${v}%`
                    : formatCompactCurrency(v, hideNumbers)
                }
                tick={{ fontSize: 11 }}
                width={70}
              />
              <RechartsTooltip content={<LineTooltipContent />} />
              <Legend
                onClick={(e: any) => {
                  if (lineViewMode === 'value' && !drillCategory && e?.value) {
                    handleCategoryDrill(e.value);
                  }
                }}
                wrapperStyle={{ cursor: lineViewMode === 'value' && !drillCategory ? 'pointer' : 'default' }}
              />
              {visibleLineKeys.map((key) => {
                const color = getColor(key, lineKeys.indexOf(key));
                const lastIndex = activeLineData.length - 1;
                return (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={color}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                    name={key}
                    label={({ x, y, index }: any) => (
                      <text
                        x={index === lastIndex ? x + 8 : 0}
                        y={index === lastIndex ? y : 0}
                        fill={index === lastIndex ? color : 'none'}
                        fontSize={isSmall ? 10 : 11}
                        fontWeight={600}
                        dominantBaseline="middle"
                      >
                        {index === lastIndex ? key : ''}
                      </text>
                    )}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        )}
      </Paper>
    </Box>
  );
};

export default AssetInsight;
