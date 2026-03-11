import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
  useMediaQuery,
  useTheme,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Stack,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
// No recharts — custom SVG timeline for proportional bar placement
import { insightsAPI } from '../services/api';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface MaturityItem {
  asset_id: number;
  asset_name: string;
  asset_type: string;
  maturity_date: string;
  days_remaining: number;
  current_value: number;
  total_invested: number;
  interest_rate: number | null;
  maturity_amount: number;
  status: string;
}

const STATUS_COLORS: Record<string, 'error' | 'warning' | 'info' | 'success' | 'default'> = {
  'Matured': 'default',
  'Maturing Soon': 'error',
  'Approaching': 'warning',
  'On Track': 'success',
};

const BAR_COLORS: Record<string, string> = {
  'Matured': '#9e9e9e',
  'Maturing Soon': '#f44336',
  'Approaching': '#ff9800',
  'On Track': '#4caf50',
};

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

const formatAssetType = (type: string) =>
  type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
};

const formatDaysRemaining = (days: number) => {
  if (days < 0) return `${Math.abs(days)}d ago`;
  if (days === 0) return 'Today';
  if (days < 30) return `${days}d`;
  if (days < 365) return `${Math.floor(days / 30)}m ${days % 30}d`;
  const years = Math.floor(days / 365);
  const months = Math.floor((days % 365) / 30);
  return months > 0 ? `${years}y ${months}m` : `${years}y`;
};

const MaturityTimeline: React.FC = () => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  const selectedPortfolioId = useSelectedPortfolio();
  const [items, setItems] = useState<MaturityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hideNumbers, setHideNumbers] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await insightsAPI.getMaturityTimeline(selectedPortfolioId);
      setItems(res.items || []);
    } catch (err) {
      console.error('Failed to fetch maturity timeline:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedPortfolioId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Prepare chart data — only upcoming (from today onwards), sorted by date
  const upcomingItems = items.filter((i) => i.days_remaining >= 0);
  const sortedUpcoming = upcomingItems
    .slice()
    .sort((a, b) => new Date(a.maturity_date).getTime() - new Date(b.maturity_date).getTime());

  // Chart container ref for measuring width — callback ref so it works inside conditional render
  const observerRef = React.useRef<ResizeObserver | null>(null);
  const [chartWidth, setChartWidth] = useState(0);
  const chartRef = useCallback((node: HTMLDivElement | null) => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    if (node) {
      const obs = new ResizeObserver((entries) => {
        for (const entry of entries) setChartWidth(entry.contentRect.width);
      });
      obs.observe(node);
      observerRef.current = obs;
    }
  }, []);

  // Tooltip state
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Summary stats
  const totalCurrentValue = upcomingItems.reduce((s, i) => s + i.current_value, 0);
  const totalMaturityAmount = upcomingItems.reduce((s, i) => s + i.maturity_amount, 0);
  const maturingSoonCount = items.filter((i) => i.status === 'Maturing Soon').length;

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="40vh">
        <CircularProgress />
      </Box>
    );
  }

  if (items.length === 0) {
    return (
      <Box p={3}>
        <Typography variant="h5" gutterBottom>Maturity Timeline</Typography>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No assets with maturity dates found. Add Fixed Deposits, Bonds, or other
            maturity-based investments to see them here.
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box p={isSmall ? 1 : 3}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="h5">Maturity Timeline</Typography>
        <Tooltip title={hideNumbers ? 'Show numbers' : 'Hide numbers'}>
          <IconButton onClick={() => setHideNumbers(!hideNumbers)} size="small">
            {hideNumbers ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Summary cards */}
      <Stack direction="row" spacing={2} mb={3} flexWrap="wrap" useFlexGap>
        <Paper sx={{ px: 2.5, py: 1.5, minWidth: 160 }}>
          <Typography variant="caption" color="text.secondary">Upcoming Maturities</Typography>
          <Typography variant="h6">{upcomingItems.length}</Typography>
        </Paper>
        <Paper sx={{ px: 2.5, py: 1.5, minWidth: 160 }}>
          <Typography variant="caption" color="text.secondary">Current Value</Typography>
          <Typography variant="h6">{formatCurrency(totalCurrentValue, hideNumbers)}</Typography>
        </Paper>
        <Paper sx={{ px: 2.5, py: 1.5, minWidth: 160 }}>
          <Typography variant="caption" color="text.secondary">Est. Maturity Value</Typography>
          <Typography variant="h6">{formatCurrency(totalMaturityAmount, hideNumbers)}</Typography>
        </Paper>
        {maturingSoonCount > 0 && (
          <Paper sx={{ px: 2.5, py: 1.5, minWidth: 160, borderLeft: '3px solid', borderColor: 'error.main' }}>
            <Typography variant="caption" color="error">Maturing Soon (&le;6m)</Typography>
            <Typography variant="h6" color="error">{maturingSoonCount}</Typography>
          </Paper>
        )}
      </Stack>

      {/* Timeline Chart — custom SVG with proportionally placed bars */}
      {sortedUpcoming.length > 0 && (() => {
        const todayTs = Date.now();
        const maxAmount = Math.max(...sortedUpcoming.map((i) => i.maturity_amount));
        const lastTs = new Date(sortedUpcoming[sortedUpcoming.length - 1].maturity_date + 'T00:00:00').getTime();
        const timeSpan = lastTs - todayTs;

        // Layout ratios (all relative to chartWidth)
        const yAxisW = chartWidth * 0.06;
        const plotLeft = yAxisW + chartWidth * 0.02;
        const plotRight = chartWidth * 0.97;
        const plotW = plotRight - plotLeft;
        const svgH = isSmall ? chartWidth * 0.55 : chartWidth * 0.32;
        const plotTop = svgH * 0.12;
        const plotBottom = svgH * 0.82;
        const plotH = plotBottom - plotTop;
        const barW = Math.max(chartWidth * 0.012, Math.min(chartWidth * 0.03, plotW / (sortedUpcoming.length * 5)));
        const fontSize = Math.max(9, Math.min(12, svgH * 0.035));
        const labelFontSize = fontSize * 0.9;

        // Y-axis ticks (4 ticks)
        const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
          value: maxAmount * f,
          y: plotBottom - plotH * f,
        }));

        // Position each bar proportionally on the time axis
        const barData = sortedUpcoming.map((item) => {
          const itemTs = new Date(item.maturity_date + 'T00:00:00').getTime();
          const xFrac = timeSpan > 0 ? (itemTs - todayTs) / timeSpan : 0.5;
          const x = plotLeft + xFrac * plotW;
          const hFrac = maxAmount > 0 ? item.maturity_amount / maxAmount : 0;
          const barH = hFrac * plotH;
          return { ...item, cx: x, barH, barY: plotBottom - barH };
        });

        return (
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom fontWeight={600}>
              Maturity Timeline
            </Typography>
            <Box ref={chartRef} sx={{ width: '100%', position: 'relative' }}>
              {chartWidth > 0 && (
                <svg width={chartWidth} height={svgH} style={{ display: 'block' }}>
                  {/* Background */}
                  <defs>
                    <linearGradient id="chartBg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f0f4ff" />
                      <stop offset="100%" stopColor="#e8edf8" />
                    </linearGradient>
                  </defs>
                  <rect x={0} y={0} width={chartWidth} height={svgH} rx={8} fill="url(#chartBg)" />
                  <rect x={plotLeft} y={plotTop} width={plotW} height={plotH} rx={4} fill="rgba(255,255,255,0.55)" />
                  {/* Grid lines */}
                  {yTicks.map((t, i) => (
                    <line key={i} x1={plotLeft} x2={plotRight} y1={t.y} y2={t.y}
                      stroke="#e0e0e0" strokeDasharray="4 3" />
                  ))}
                  {/* Baseline */}
                  <line x1={plotLeft} x2={plotRight} y1={plotBottom} y2={plotBottom} stroke="#bdbdbd" />

                  {/* Y-axis labels */}
                  {yTicks.map((t, i) => (
                    <text key={i} x={yAxisW} y={t.y + 4} textAnchor="end"
                      fill="#888" fontSize={fontSize * 0.85}>
                      {formatCompactCurrency(t.value, hideNumbers)}
                    </text>
                  ))}

                  {/* "Today" label */}
                  <text x={plotLeft} y={plotBottom + fontSize * 2} textAnchor="middle"
                    fill="#999" fontSize={fontSize * 0.8}>Today</text>

                  {/* Bars + labels */}
                  {barData.map((d, i) => {
                    const barX = d.cx - barW / 2;
                    return (
                      <g key={d.asset_id}
                        onMouseEnter={() => setHoveredIdx(i)}
                        onMouseLeave={() => setHoveredIdx(null)}
                        style={{ cursor: 'pointer' }}
                      >
                        {/* Bar */}
                        <rect
                          x={barX} y={d.barY} width={barW} height={d.barH}
                          rx={barW * 0.12}
                          fill={BAR_COLORS[d.status] || '#4caf50'}
                          opacity={hoveredIdx === null || hoveredIdx === i ? 1 : 0.4}
                        />
                        {/* Amount label above bar */}
                        <text x={d.cx} y={d.barY - labelFontSize * 0.4}
                          textAnchor="middle" fill="#333" fontSize={labelFontSize} fontWeight={600}>
                          {formatCompactCurrency(d.maturity_amount, hideNumbers)}
                        </text>
                        {/* Asset name above amount */}
                        <text x={d.cx} y={d.barY - labelFontSize * 1.6}
                          textAnchor="middle" fill="#666" fontSize={labelFontSize * 0.88}>
                          {d.asset_name.length > 16 ? d.asset_name.substring(0, 14) + '…' : d.asset_name}
                        </text>
                        {/* Date label below axis */}
                        <text x={d.cx} y={plotBottom + fontSize * 1.3} textAnchor="middle"
                          fill="#666" fontSize={fontSize * 0.85}>
                          {formatDate(d.maturity_date)}
                        </text>
                        {/* Time remaining below date */}
                        <text x={d.cx} y={plotBottom + fontSize * 2.5} textAnchor="middle"
                          fill="#999" fontSize={fontSize * 0.75}>
                          {formatDaysRemaining(d.days_remaining)}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}

              {/* Hover tooltip */}
              {hoveredIdx !== null && barData[hoveredIdx] && (() => {
                const d = barData[hoveredIdx];
                const tooltipLeft = d.cx > chartWidth * 0.7 ? d.cx - chartWidth * 0.22 : d.cx + barW;
                return (
                  <Paper
                    elevation={4}
                    sx={{
                      position: 'absolute',
                      left: tooltipLeft,
                      top: d.barY,
                      p: 1.5,
                      pointerEvents: 'none',
                      zIndex: 10,
                      minWidth: '15%',
                      maxWidth: '35%',
                    }}
                  >
                    <Typography variant="subtitle2" gutterBottom>{d.asset_name}</Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {formatAssetType(d.asset_type)}
                    </Typography>
                    <Typography variant="body2">
                      Matures: {formatDate(d.maturity_date)} ({formatDaysRemaining(d.days_remaining)})
                    </Typography>
                    <Typography variant="body2">
                      Current: {formatCurrency(d.current_value, hideNumbers)}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      Est. Maturity: {formatCurrency(d.maturity_amount, hideNumbers)}
                    </Typography>
                    {d.interest_rate && (
                      <Typography variant="body2">Rate: {d.interest_rate}%</Typography>
                    )}
                  </Paper>
                );
              })()}
            </Box>
            {/* Legend */}
            <Stack direction="row" spacing={2} justifyContent="center" mt={1}>
              {Object.entries(BAR_COLORS).filter(([k]) => k !== 'Matured').map(([label, color]) => (
                <Stack key={label} direction="row" alignItems="center" spacing={0.5}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '2px', bgcolor: color }} />
                  <Typography variant="caption">{label}</Typography>
                </Stack>
              ))}
            </Stack>
          </Paper>
        );
      })()}

      {/* Data Table */}
      <Paper>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Asset</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Maturity Date</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Time Left</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Current Value</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Rate</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Est. Maturity</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="center">Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.asset_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>{item.asset_name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatAssetType(item.asset_type)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">{formatDate(item.maturity_date)}</TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      color={item.days_remaining <= 30 ? 'error.main' : item.days_remaining <= 90 ? 'warning.main' : 'text.primary'}
                      fontWeight={item.days_remaining <= 30 ? 600 : 400}
                    >
                      {formatDaysRemaining(item.days_remaining)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">{formatCurrency(item.current_value, hideNumbers)}</TableCell>
                  <TableCell align="right">
                    {item.interest_rate != null ? `${item.interest_rate}%` : '—'}
                  </TableCell>
                  <TableCell align="right">{formatCurrency(item.maturity_amount, hideNumbers)}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={item.status}
                      color={STATUS_COLORS[item.status] || 'default'}
                      size="small"
                      variant={item.status === 'Matured' ? 'outlined' : 'filled'}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
};

export default MaturityTimeline;
