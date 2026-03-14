import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RechartTooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useNavigate } from 'react-router-dom';
import { liquidityAPI } from '../services/api';

// ── Types ──────────────────────────────────────────────────────────────────────

interface DataPoint {
  date: string;
  value: number;
}

interface DebtMeta {
  unit: string;
  label: string;
}

interface LiquidityData {
  m2: Record<string, DataPoint[]>;
  assets: {
    spx: DataPoint[];
    gold: DataPoint[];
    btc: DataPoint[];
  };
  debt: Record<string, DataPoint[]>;
  debt_meta: Record<string, DebtMeta>;
  m2_errors: Record<string, string>;
  last_updated: string | null;
  fred_configured: boolean;
  m2_series: string[];
  m2_units: Record<string, string>;
}

interface ChartRow {
  date: string;
  globalM2: number | null;
  spx: number | null;
  gold: number | null;
  btc: number | null;
  [key: string]: number | null | string;
}

type Period = '1Y' | '2Y' | '3Y' | '5Y' | 'ALL';

// ── Constants ──────────────────────────────────────────────────────────────────

const PERIOD_MONTHS: Record<Period, number | null> = {
  '1Y': 12,
  '2Y': 24,
  '3Y': 36,
  '5Y': 60,
  'ALL': null,
};

const SERIES_CONFIG = {
  globalM2: { label: 'Global M2 (Indexed)', color: '#4fc3f7', strokeWidth: 2.5, dash: '' },
  spx:      { label: 'S&P 500 (Indexed)',   color: '#81c784', strokeWidth: 2,   dash: '' },
  gold:     { label: 'Gold (Indexed)',       color: '#ffd54f', strokeWidth: 2,   dash: '' },
  btc:      { label: 'Bitcoin (Indexed)',    color: '#ff8a65', strokeWidth: 2,   dash: '4 2' },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function getStartDate(period: Period): string | null {
  const months = PERIOD_MONTHS[period];
  if (months === null) return null;
  const d = new Date();
  d.setMonth(d.getMonth() - months);
  return d.toISOString().slice(0, 10);
}

function indexSeries(data: DataPoint[], startDate: string | null): DataPoint[] {
  const filtered = startDate ? data.filter((d) => d.date >= startDate) : data;
  if (filtered.length === 0) return [];
  const base = filtered[0].value;
  if (!base) return [];
  return filtered.map((d) => ({ date: d.date, value: Math.round((d.value / base) * 1000) / 10 }));
}

function computeGlobalM2Index(
  m2: Record<string, DataPoint[]>,
  startDate: string | null
): DataPoint[] {
  const indexed: Record<string, DataPoint[]> = {};
  for (const [country, series] of Object.entries(m2)) {
    const idx = indexSeries(series, startDate);
    if (idx.length > 0) indexed[country] = idx;
  }
  if (Object.keys(indexed).length === 0) return [];

  // Collect all unique dates across all countries
  const dateSet = new Set<string>();
  Object.values(indexed).forEach((s) => s.forEach((d) => dateSet.add(d.date)));
  const sortedDates = [...dateSet].sort();

  // For each date, average the indexed values of available countries
  return sortedDates.map((date) => {
    const vals = Object.values(indexed)
      .map((s) => s.find((d) => d.date === date)?.value)
      .filter((v): v is number => v !== undefined);
    return {
      date,
      value: vals.length > 0 ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : 0,
    };
  }).filter((d) => d.value > 0);
}

function buildChartData(
  m2: Record<string, DataPoint[]>,
  assets: LiquidityData['assets'],
  startDate: string | null
): ChartRow[] {
  const globalM2 = computeGlobalM2Index(m2, startDate);
  const spx = indexSeries(assets.spx || [], startDate);
  const gold = indexSeries(assets.gold || [], startDate);
  const btc = indexSeries(assets.btc || [], startDate);

  // Collect all dates
  const dateSet = new Set<string>();
  [globalM2, spx, gold, btc].forEach((s) => s.forEach((d) => dateSet.add(d.date)));
  const sortedDates = [...dateSet].sort();

  const lookup = (series: DataPoint[], date: string): number | null =>
    series.find((d) => d.date === date)?.value ?? null;

  return sortedDates.map((date) => ({
    date,
    globalM2: lookup(globalM2, date),
    spx: lookup(spx, date),
    gold: lookup(gold, date),
    btc: lookup(btc, date),
  }));
}

function pctChange(series: DataPoint[], startDate: string | null): number | null {
  const filtered = startDate ? series.filter((d) => d.date >= startDate) : series;
  if (filtered.length < 2) return null;
  const start = filtered[0].value;
  const end = filtered[filtered.length - 1].value;
  if (!start) return null;
  return Math.round(((end - start) / start) * 1000) / 10;
}

/**
 * Format a Trillion value for axis ticks / compact display.
 * Backend stores all M2 series in Trillions of native currency.
 */
function compactT(value: number): string {
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  if (value >= 100) return `${Math.round(value)}`;
  if (value >= 10) return `${value.toFixed(1)}`;
  return value.toFixed(2);
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', timeZone: 'UTC' });
}

function formatLastUpdated(ts: string | null): string {
  if (!ts) return 'Never';
  try {
    const d = new Date(ts + 'Z');
    return d.toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return ts;
  }
}

// ── Summary Card ───────────────────────────────────────────────────────────────

interface SummaryCardProps {
  label: string;
  color: string;
  pct: number | null;
  period: string;
  currentValue?: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ label, color, pct, period, currentValue }) => {
  const positive = pct !== null && pct >= 0;
  return (
    <Card sx={{ border: `1px solid ${color}33`, background: `${color}08` }}>
      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.8 }}>
          {label}
        </Typography>
        {currentValue && (
          <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500, mt: 0.25 }}>
            {currentValue}
          </Typography>
        )}
        {pct !== null ? (
          <Stack direction="row" alignItems="center" spacing={0.5} mt={0.5}>
            {positive ? (
              <TrendingUpIcon sx={{ fontSize: 16, color: '#81c784' }} />
            ) : (
              <TrendingDownIcon sx={{ fontSize: 16, color: '#ef5350' }} />
            )}
            <Typography variant="h6" sx={{ color: positive ? '#81c784' : '#ef5350', fontWeight: 700 }}>
              {positive ? '+' : ''}{pct}%
            </Typography>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.disabled" mt={0.5}>No data</Typography>
        )}
        <Typography variant="caption" color="text.disabled">{period}</Typography>
      </CardContent>
    </Card>
  );
};

// ── Custom Tooltip ─────────────────────────────────────────────────────────────

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', minWidth: 180 }}>
      <Typography variant="caption" fontWeight={700} display="block" mb={0.5}>
        {formatDate(label)}
      </Typography>
      {payload.map((entry: any) => (
        <Stack key={entry.dataKey} direction="row" justifyContent="space-between" spacing={2}>
          <Typography variant="caption" sx={{ color: entry.color }}>
            {SERIES_CONFIG[entry.dataKey as keyof typeof SERIES_CONFIG]?.label ?? entry.dataKey}
          </Typography>
          <Typography variant="caption" fontWeight={600}>
            {entry.value != null ? `${entry.value.toFixed(1)}` : '—'}
          </Typography>
        </Stack>
      ))}
      <Typography variant="caption" color="text.disabled" display="block" mt={0.5}>
        Index (100 = period start)
      </Typography>
    </Paper>
  );
};

// ── Main Component ─────────────────────────────────────────────────────────────

const LiquidityInsight: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();

  const [data, setData] = useState<LiquidityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>('5Y');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await liquidityAPI.getData();
      setData(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load liquidity data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await liquidityAPI.refresh();
      await fetchData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Refresh failed');
    } finally {
      setRefreshing(false);
    }
  }, [fetchData]);

  const startDate = useMemo(() => getStartDate(period), [period]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return buildChartData(data.m2, data.assets, startDate);
  }, [data, startDate]);

  // Percentage changes for summary cards
  const m2Pct = useMemo(() => {
    if (!data) return null;
    const globalM2 = computeGlobalM2Index(data.m2, startDate);
    if (globalM2.length < 2) return null;
    const s = globalM2[0].value;
    const e = globalM2[globalM2.length - 1].value;
    return s ? Math.round(((e - s) / s) * 1000) / 10 : null;
  }, [data, startDate]);

  const spxPct = useMemo(() => data ? pctChange(data.assets.spx || [], startDate) : null, [data, startDate]);
  const goldPct = useMemo(() => data ? pctChange(data.assets.gold || [], startDate) : null, [data, startDate]);
  const btcPct = useMemo(() => data ? pctChange(data.assets.btc || [], startDate) : null, [data, startDate]);

  // Latest raw values for cards
  const latestValue = (series: DataPoint[]) => series.length > 0 ? series[series.length - 1] : null;

  const availableM2Countries = data ? Object.keys(data.m2) : [];
  const hasM2 = availableM2Countries.length > 0;

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Stack alignItems="center" spacing={2}>
          <CircularProgress />
          <Typography color="text.secondary">Loading global liquidity data…</Typography>
        </Stack>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      {/* ── Header ── */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2} flexWrap="wrap" gap={1}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Global Liquidity Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Global M2 money supply vs. S&P 500, Gold & Bitcoin — normalized to 100 at period start
          </Typography>
        </Box>
        <Stack direction="row" alignItems="center" spacing={1}>
          {data?.last_updated && (
            <Typography variant="caption" color="text.disabled">
              Updated: {formatLastUpdated(data.last_updated)}
            </Typography>
          )}
          <Tooltip title="Force-refresh data from FRED & Yahoo Finance">
            <span>
              <IconButton
                onClick={handleRefresh}
                disabled={refreshing}
                size="small"
                sx={{ border: '1px solid', borderColor: 'divider' }}
              >
                {refreshing ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      {/* ── Alerts ── */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!data?.fred_configured && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            <Button
              size="small"
              startIcon={<SettingsIcon />}
              onClick={() => navigate('/settings')}
            >
              Add Key
            </Button>
          }
        >
          <strong>FRED API key not configured.</strong> M2 money supply data requires a free FRED API key.
          Set it in Administration → Application Setup → Market API Keys.
        </Alert>
      )}

      {data?.fred_configured && !hasM2 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          M2 data is being fetched for the first time. This may take a moment — click{' '}
          <strong>Refresh</strong> to trigger an immediate update.
        </Alert>
      )}

      {/* ── Period selector ── */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2} flexWrap="wrap" gap={1}>
        <Stack direction="row" alignItems="center" spacing={1}>
          {hasM2 && (
            <Stack direction="row" spacing={0.5} flexWrap="wrap">
              {availableM2Countries.map((c) => (
                <Chip key={c} label={c} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
              ))}
              <Tooltip title="Countries with M2 data from FRED">
                <InfoIcon sx={{ fontSize: 16, color: 'text.disabled', alignSelf: 'center' }} />
              </Tooltip>
            </Stack>
          )}
        </Stack>
        <ButtonGroup size="small" variant="outlined">
          {(['1Y', '2Y', '3Y', '5Y', 'ALL'] as Period[]).map((p) => (
            <Button
              key={p}
              onClick={() => setPeriod(p)}
              variant={period === p ? 'contained' : 'outlined'}
            >
              {p}
            </Button>
          ))}
        </ButtonGroup>
      </Stack>

      {/* ── Summary Cards ── */}
      <Grid container spacing={1.5} mb={2}>
        <Grid item xs={6} sm={3}>
          <SummaryCard
            label="Global M2"
            color={SERIES_CONFIG.globalM2.color}
            pct={m2Pct}
            period={period}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <SummaryCard
            label="S&P 500"
            color={SERIES_CONFIG.spx.color}
            pct={spxPct}
            period={period}
            currentValue={
              latestValue(data?.assets.spx || [])
                ? `$${Math.round(latestValue(data!.assets.spx)!.value).toLocaleString()}`
                : undefined
            }
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <SummaryCard
            label="Gold"
            color={SERIES_CONFIG.gold.color}
            pct={goldPct}
            period={period}
            currentValue={
              latestValue(data?.assets.gold || [])
                ? `$${Math.round(latestValue(data!.assets.gold)!.value).toLocaleString()}/oz`
                : undefined
            }
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <SummaryCard
            label="Bitcoin"
            color={SERIES_CONFIG.btc.color}
            pct={btcPct}
            period={period}
            currentValue={
              latestValue(data?.assets.btc || [])
                ? `$${Math.round(latestValue(data!.assets.btc)!.value).toLocaleString()}`
                : undefined
            }
          />
        </Grid>
      </Grid>

      {/* ── Main Chart ── */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1.5}>
          <Typography variant="subtitle1" fontWeight={600}>
            Normalized Index (100 = Start of {period} Period)
          </Typography>
        </Stack>

        {chartData.length === 0 ? (
          <Box display="flex" justifyContent="center" alignItems="center" height={300}>
            <Typography color="text.secondary">
              {data?.fred_configured ? 'No data available for the selected period' : 'Configure FRED API key to see M2 data'}
            </Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                dataKey="date"
                tickFormatter={(d) => new Date(d + 'T00:00:00Z').getFullYear().toString()}
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                tickLine={false}
                minTickGap={50}
              />
              <YAxis
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                tickLine={false}
                axisLine={false}
                domain={['auto', 'auto']}
                tickFormatter={(v) => `${v}`}
                label={{ value: 'Index', angle: -90, position: 'insideLeft', offset: -2, style: { fontSize: 11, fill: theme.palette.text.disabled } }}
                width={56}
              />
              <RechartTooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) =>
                  SERIES_CONFIG[value as keyof typeof SERIES_CONFIG]?.label ?? value
                }
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              />
              <ReferenceLine y={100} stroke={theme.palette.divider} strokeDasharray="6 3" />
              {Object.entries(SERIES_CONFIG).map(([key, cfg]) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={cfg.color}
                  strokeWidth={cfg.strokeWidth}
                  strokeDasharray={cfg.dash || undefined}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </Paper>

      {/* ── Actual M2 Values Chart (US + China only) ── */}
      {hasM2 && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={0.5}>
            Actual M2 Money Supply — Full History (Raw Values)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
            Each series shown in its native unit. US data starts 1959; China as available from FRED.
          </Typography>
          <ActualM2Charts m2={data!.m2} units={data!.m2_units || {}} exclude={['IN', 'EU', 'JP']} />
        </Paper>
      )}

      {/* ── National Debt ── */}
      {data?.fred_configured && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={0.5}>
            National Debt
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
            US: Gross Federal Debt (Quarterly through Q4 2025) · Source: FRED (GFDEBTN)
          </Typography>
          <NationalDebtCharts
            debt={data.debt || {}}
            debtMeta={data.debt_meta || {}}
          />
        </Paper>
      )}

      {/* ── Data Notes ── */}
      <Paper sx={{ p: 2, bgcolor: 'action.hover' }}>
        <Typography variant="caption" color="text.secondary" display="block" fontWeight={600} mb={0.5}>
          Data Sources & Methodology
        </Typography>
        <Stack spacing={0.5}>
          {[
            'Global M2: Aggregate of US, Eurozone, China, Japan, India — each series normalized to Trillions of native currency, indexed to 100 at period start, then averaged.',
            'S&P 500 & Gold (GC=F): Monthly closing prices via Yahoo Finance.',
            'Bitcoin (BTC-USD): Monthly closing prices via Yahoo Finance.',
            'All series are normalized to 100 at the start of the selected period to show relative performance.',
            'Data is cached weekly and auto-refreshed every Monday at 02:00 UTC.',
          ].map((note, i) => (
            <Typography key={i} variant="caption" color="text.secondary">
              • {note}
            </Typography>
          ))}
        </Stack>
      </Paper>
    </Box>
  );
};

// ── Actual M2 Values Grid ─────────────────────────────────────────────────────

const COUNTRY_COLORS: Record<string, string> = {
  US: '#4fc3f7',
  EU: '#ce93d8',
  CN: '#ef5350',
  JP: '#ff7043',
  IN: '#66bb6a',
};

const COUNTRY_META: Record<string, { label: string; currency: string; symbol: string }> = {
  US: { label: 'United States M2', currency: 'Trillion USD', symbol: '$' },
  EU: { label: 'Eurozone M2',      currency: 'Trillion EUR', symbol: '€' },
  CN: { label: 'China M2',         currency: 'Trillion CNY', symbol: '¥' },
  JP: { label: 'Japan M2',         currency: 'Trillion JPY', symbol: '¥' },
  IN: { label: 'India M2',         currency: 'Trillion INR', symbol: '₹' },
};

interface M2ChartCanvasProps {
  country: string;
  series: DataPoint[];
  meta: { label: string; currency: string; symbol: string };
  color: string;
  defaultStart: number;
  onBrushChange: (range: { startIndex: number; endIndex: number }) => void;
}

const M2ChartCanvas = React.memo<M2ChartCanvasProps>(({ country, series, meta, color, defaultStart, onBrushChange }) => {
  const theme = useTheme();

  const handleBrush = useCallback((range: any) => {
    if (range?.startIndex != null && range?.endIndex != null) {
      onBrushChange({ startIndex: range.startIndex, endIndex: range.endIndex });
    }
  }, [onBrushChange]);

  return (
    <ResponsiveContainer width="100%" height={420}>
      <AreaChart data={series} margin={{ top: 8, right: 24, left: 16, bottom: 0 }}>
        <defs>
          <linearGradient id={`m2grad-${country}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.35} />
            <stop offset="95%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
        <XAxis
          dataKey="date"
          tickFormatter={(d) => new Date(d + 'T00:00:00Z').getFullYear().toString()}
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          minTickGap={50}
        />
        <YAxis
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${meta.symbol}${compactT(v)}T`}
          width={72}
        />
        <RechartTooltip
          labelFormatter={(label) => formatDate(label)}
          formatter={(value: any) => [`${meta.symbol}${Number(value).toFixed(2)} T`, meta.label]}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            fontSize: 13,
          }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2.5}
          fill={`url(#m2grad-${country})`}
          dot={false}
          isAnimationActive={false}
        />
        <Brush
          dataKey="date"
          height={30}
          stroke={theme.palette.divider}
          fill={theme.palette.background.default}
          tickFormatter={(d) => new Date(d + 'T00:00:00Z').getFullYear().toString()}
          startIndex={defaultStart}
          travellerWidth={8}
          onChange={handleBrush}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
});

interface ActualM2ChartsProps {
  m2: Record<string, DataPoint[]>;
  units: Record<string, string>;
  exclude?: string[];
}

const ActualM2Charts: React.FC<ActualM2ChartsProps> = ({ m2, exclude = [] }) => {
  const countries = Object.keys(m2).filter((c) => m2[c].length > 0 && !exclude.includes(c));

  if (countries.length === 0) {
    return <Typography color="text.secondary" align="center">No data available</Typography>;
  }

  return (
    <Stack spacing={3}>
      {countries.map((country) => {
        const series = m2[country];
        const meta = COUNTRY_META[country] ?? { label: `${country} M2`, currency: 'Native Units', symbol: '' };
        const color = COUNTRY_COLORS[country] ?? '#90caf9';
        return <M2CountryChart key={country} country={country} series={series} meta={meta} color={color} />;
      })}
    </Stack>
  );
};

interface M2CountryChartProps {
  country: string;
  series: DataPoint[];
  meta: { label: string; currency: string; symbol: string };
  color: string;
}

const M2CountryChart: React.FC<M2CountryChartProps> = ({ country, series, meta, color }) => {
  const defaultStart = Math.max(0, series.length - 80);
  const [brushRange, setBrushRange] = useState({ startIndex: defaultStart, endIndex: series.length - 1 });

  const visibleStart = series[brushRange.startIndex];
  const visibleEnd   = series[brushRange.endIndex];
  const pct = visibleStart?.value && visibleEnd?.value
    ? Math.round(((visibleEnd.value - visibleStart.value) / visibleStart.value) * 1000) / 10
    : null;

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={1.5}>
        <Box>
          <Typography variant="subtitle2" fontWeight={700}>{meta.label}</Typography>
          <Typography variant="caption" color="text.secondary">{meta.currency} · Drag the brush below to zoom</Typography>
        </Box>
        <Box textAlign="right">
          <Typography variant="h6" fontWeight={700} sx={{ color }}>
            {meta.symbol}{compactT(visibleEnd.value)} T
          </Typography>
          <Typography variant="caption" color="text.secondary">
            as of {formatDate(visibleEnd.date)}
          </Typography>
          {pct !== null && (
            <Typography variant="caption" display="block" sx={{ color: pct >= 0 ? '#81c784' : '#ef5350' }}>
              {pct >= 0 ? '+' : ''}{pct}% since {formatDate(visibleStart.date)}
            </Typography>
          )}
        </Box>
      </Stack>
      <M2ChartCanvas
        country={country}
        series={series}
        meta={meta}
        color={color}
        defaultStart={defaultStart}
        onBrushChange={setBrushRange}
      />
    </Box>
  );
};

// ── National Debt Charts ──────────────────────────────────────────────────────

const DEBT_EXCLUDE = ['IN'];

interface NationalDebtChartsProps {
  debt: Record<string, DataPoint[]>;
  debtMeta: Record<string, DebtMeta>;
}

interface DebtChartCanvasProps {
  country: string;
  series: DataPoint[];
  defaultStart: number;
  onBrushChange: (range: { startIndex: number; endIndex: number }) => void;
}

const DebtChartCanvas = React.memo<DebtChartCanvasProps>(({ country, series, defaultStart, onBrushChange }) => {
  const theme = useTheme();
  const color = '#4fc3f7';

  const handleBrush = useCallback((range: any) => {
    if (range?.startIndex != null && range?.endIndex != null) {
      onBrushChange({ startIndex: range.startIndex, endIndex: range.endIndex });
    }
  }, [onBrushChange]);

  return (
    <ResponsiveContainer width="100%" height={420}>
      <AreaChart data={series} margin={{ top: 8, right: 24, left: 16, bottom: 0 }}>
        <defs>
          <linearGradient id={`debtGrad-${country}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.35} />
            <stop offset="95%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
        <XAxis
          dataKey="date"
          tickFormatter={(d) => new Date(d + 'T00:00:00Z').getFullYear().toString()}
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          minTickGap={50}
        />
        <YAxis
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `$${compactT(v)}T`}
          width={72}
        />
        <RechartTooltip
          labelFormatter={(label) => formatDate(label)}
          formatter={(value: any) => [`$${compactT(Number(value))} Trillion`, 'US Federal Debt']}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            fontSize: 13,
          }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2.5}
          fill={`url(#debtGrad-${country})`}
          dot={false}
          isAnimationActive={false}
        />
        <Brush
          dataKey="date"
          height={30}
          stroke={theme.palette.divider}
          fill={theme.palette.background.default}
          tickFormatter={(d) => new Date(d + 'T00:00:00Z').getFullYear().toString()}
          startIndex={defaultStart}
          travellerWidth={8}
          onChange={handleBrush}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
});

interface DebtChartProps {
  country: string;
  series: DataPoint[];
  meta: DebtMeta;
}

const DebtChart: React.FC<DebtChartProps> = ({ country, series, meta }) => {
  const color = '#4fc3f7';
  const defaultStart = Math.max(0, series.length - 80);

  const [brushRange, setBrushRange] = useState({ startIndex: defaultStart, endIndex: series.length - 1 });

  const visibleStart = series[brushRange.startIndex];
  const visibleEnd   = series[brushRange.endIndex];
  const pct = visibleStart?.value && visibleEnd?.value
    ? Math.round(((visibleEnd.value - visibleStart.value) / visibleStart.value) * 1000) / 10
    : null;

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={1.5}>
        <Box>
          <Typography variant="subtitle2" fontWeight={700}>{meta.label}</Typography>
          <Typography variant="caption" color="text.secondary">{meta.unit} · Drag the brush below to zoom</Typography>
        </Box>
        <Box textAlign="right">
          <Typography variant="h6" fontWeight={700} sx={{ color }}>
            ${compactT(visibleEnd.value)} T
          </Typography>
          <Typography variant="caption" color="text.secondary">
            as of {formatDate(visibleEnd.date)}
          </Typography>
          {pct !== null && (
            <Typography variant="caption" display="block" sx={{ color: pct >= 0 ? '#ef5350' : '#81c784' }}>
              {pct >= 0 ? '+' : ''}{pct}% since {formatDate(visibleStart.date)}
            </Typography>
          )}
        </Box>
      </Stack>
      <DebtChartCanvas
        country={country}
        series={series}
        defaultStart={defaultStart}
        onBrushChange={setBrushRange}
      />
    </Box>
  );
};

const NationalDebtCharts: React.FC<NationalDebtChartsProps> = ({ debt, debtMeta }) => {
  const entries = Object.entries(debt).filter(
    ([country, series]) => !DEBT_EXCLUDE.includes(country) && series.length > 0,
  );

  if (entries.length === 0) {
    return (
      <Typography color="text.secondary" align="center" py={4}>
        No debt data available — click Refresh to fetch from FRED.
      </Typography>
    );
  }

  return (
    <Stack spacing={3}>
      {entries.map(([country, series]) => (
        <DebtChart
          key={country}
          country={country}
          series={series}
          meta={debtMeta[country] ?? { unit: '', label: country }}
        />
      ))}
    </Stack>
  );
};

export default LiquidityInsight;
