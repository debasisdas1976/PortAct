import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Stack,
  IconButton,
  Tooltip,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { insightsAPI } from '../services/api';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

const FALLBACK_COLORS = [
  '#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0',
  '#00BCD4', '#FF5722', '#607D8B', '#8BC34A', '#FFC107',
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

interface AttributeValueData {
  label: string;
  color: string | null;
  current_value: number;
  asset_count: number;
}

interface AttributeData {
  attribute_id: number;
  attribute_name: string;
  display_label: string;
  icon: string | null;
  values: AttributeValueData[];
}

const AttributeInsight: React.FC = () => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  const selectedPortfolioId = useSelectedPortfolio();

  const [hideNumbers, setHideNumbers] = useState(false);
  const [data, setData] = useState<AttributeData[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await insightsAPI.getAttributeAllocation(selectedPortfolioId);
      setData(res.attributes || []);
    } catch (err) {
      console.error('Failed to fetch attribute allocation', err);
    } finally {
      setLoading(false);
    }
  }, [selectedPortfolioId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const ValueTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <Paper sx={{ p: 1.5, boxShadow: 3 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          {d.label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Current Value: {formatCurrency(d.current_value, hideNumbers)}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Assets: {d.asset_count}
        </Typography>
      </Paper>
    );
  };

  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Page Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">Attribute Based Insight</Typography>
        <Tooltip title={hideNumbers ? 'Show numbers' : 'Hide numbers'}>
          <IconButton onClick={() => setHideNumbers(!hideNumbers)} size="small">
            {hideNumbers ? <VisibilityOff /> : <Visibility />}
          </IconButton>
        </Tooltip>
      </Stack>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : data.length === 0 ? (
        <Paper sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography color="text.secondary" align="center">
            No active attributes configured. Create attributes in Master Data &gt; Asset Attributes
            and assign them to your assets.
          </Typography>
        </Paper>
      ) : (
        data.map((attr) => (
          <Paper key={attr.attribute_id} sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              {attr.display_label}
            </Typography>

            {attr.values.length === 0 ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <Typography color="text.secondary">
                  No values defined for this attribute.
                </Typography>
              </Box>
            ) : (
              <ResponsiveContainer width="100%" height={isSmall ? 300 : 350}>
                <BarChart
                  data={attr.values}
                  margin={{ top: 10, right: 20, left: 10, bottom: isSmall ? 80 : 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
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
                  <RechartsTooltip content={<ValueTooltip />} />
                  <Bar dataKey="current_value" name="Current Value" radius={[4, 4, 0, 0]}>
                    {attr.values.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.color || FALLBACK_COLORS[index % FALLBACK_COLORS.length]}
                        fillOpacity={0.85}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </Paper>
        ))
      )}
    </Box>
  );
};

export default AttributeInsight;
