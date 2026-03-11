import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Paper, Typography,
  Chip, IconButton, Tooltip, Stack,
  useTheme, Alert,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  CurrencyBitcoin as BitcoinIcon,
  EventNote as EventIcon,
  AccountBalance as BankIcon,
} from '@mui/icons-material';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid,
  Tooltip as RechartTooltip, ResponsiveContainer, ReferenceLine,
  Cell,
} from 'recharts';
import axios from 'axios';

// ── Types ─────────────────────────────────────────────────────────────────────

interface LiveQuote {
  price: number | null;
  changePercent: number | null;
  loading: boolean;
  error: boolean;
  lastUpdated: Date | null;
}

interface IndexConfig {
  id: string;
  name: string;
  shortName: string;
  yahooSymbol: string;
  tradingViewUrl: string;
  flag: string;
  country: string;
  currency: string;
  gradient: string;
}

// ── Static Config ──────────────────────────────────────────────────────────────

const WORLD_INDICES: IndexConfig[] = [
  { id: 'nifty',    name: 'NIFTY 50',           shortName: 'NIFTY 50', yahooSymbol: '^NSEI',     tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=NSE%3ANIFTY',          flag: '🇮🇳', country: 'India',   currency: 'INR', gradient: 'linear-gradient(135deg,#7a2b00,#c8441a)' },
  { id: 'sensex',   name: 'BSE SENSEX',          shortName: 'SENSEX',   yahooSymbol: '^BSESN',    tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=BSE%3ASENSEX',         flag: '🇮🇳', country: 'India',   currency: 'INR', gradient: 'linear-gradient(135deg,#6b0f1a,#b02030)' },
  { id: 'sp500',    name: 'S&P 500',             shortName: 'S&P 500',  yahooSymbol: '^GSPC',     tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=SP%3ASPX',             flag: '🇺🇸', country: 'USA',     currency: 'USD', gradient: 'linear-gradient(135deg,#003087,#0052cc)' },
  { id: 'nasdaq',   name: 'NASDAQ 100',          shortName: 'NASDAQ',   yahooSymbol: '^NDX',      tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=NASDAQ%3ANDX',        flag: '🇺🇸', country: 'USA',     currency: 'USD', gradient: 'linear-gradient(135deg,#062b7a,#1a5fd4)' },
  { id: 'dowjones', name: 'Dow Jones',           shortName: 'DOW',      yahooSymbol: '^DJI',      tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=DJ%3ADJI',            flag: '🇺🇸', country: 'USA',     currency: 'USD', gradient: 'linear-gradient(135deg,#060d1f,#172b4d)' },
  { id: 'nikkei',   name: 'Nikkei 225',          shortName: 'NIKKEI',   yahooSymbol: '^N225',     tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=TVC%3ANI225',         flag: '🇯🇵', country: 'Japan',   currency: 'JPY', gradient: 'linear-gradient(135deg,#660018,#bc002d)' },
  { id: 'shanghai', name: 'Shanghai Composite',  shortName: 'SSE',      yahooSymbol: '000001.SS', tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=SSE%3A000001',        flag: '🇨🇳', country: 'China',   currency: 'CNY', gradient: 'linear-gradient(135deg,#7a0019,#c0392b)' },
  { id: 'dax',      name: 'DAX 40',              shortName: 'DAX',      yahooSymbol: '^GDAXI',    tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=XETR%3ADAX',          flag: '🇩🇪', country: 'Germany', currency: 'EUR', gradient: 'linear-gradient(135deg,#0a2e12,#1a6335)' },
  { id: 'bovespa',  name: 'Bovespa',             shortName: 'IBOV',     yahooSymbol: '^BVSP',     tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=BMFBOVESPA%3AIBOV',   flag: '🇧🇷', country: 'Brazil',  currency: 'BRL', gradient: 'linear-gradient(135deg,#0a3d0a,#1e7a1e)' },
  { id: 'ftse',     name: 'FTSE 100',            shortName: 'FTSE 100', yahooSymbol: '^FTSE',     tradingViewUrl: 'https://www.tradingview.com/chart/?symbol=TVC%3AUKX',           flag: '🇬🇧', country: 'UK',      currency: 'GBP', gradient: 'linear-gradient(135deg,#0a1260,#1a237e)' },
];

const COMMODITY_IDS = ['gold', 'silver', 'brent'] as const;
const COMMODITY_CONFIG: Record<string, { yahooSymbol: string; label: string; unit: string; icon: string; link: string; gradient: string; priceColor: string; darkText?: boolean; headerFontSize?: string }> = {
  gold:   { yahooSymbol: 'GC=F', label: 'Gold',        unit: 'USD per Troy Ounce', icon: '🥇', link: 'https://goldprice.org/',                                 gradient: 'linear-gradient(135deg,#a07d00,#e8b800)', priceColor: '#1a1000', darkText: true },
  silver: { yahooSymbol: 'SI=F', label: 'Silver',      unit: 'USD per Troy Ounce', icon: '🥈', link: 'https://silverprice.org/',                               gradient: 'linear-gradient(135deg,#3a4a52,#637b87)',  priceColor: '#e2eaed' },
  brent:  { yahooSymbol: 'BZ=F', label: 'Brent Crude', unit: 'USD per Barrel · ICE Futures', icon: '🛢️', link: 'https://www.tradingview.com/chart/?symbol=TVC%3AUKOIL', gradient: 'linear-gradient(135deg,#06130e,#0f2e1e)', priceColor: '#6ee7b7', headerFontSize: '1.6rem' },
};

const INDIA_COMMODITY_CONFIG: Record<string, { label: string; unit: string; icon: string; gradient: string; priceColor: string; headerFontSize?: string; convert: (usdPrice: number, usdInr: number) => number }> = {
  gold:   { label: 'Gold',        unit: '₹ per 10g · MCX',          icon: '🥇', gradient: 'linear-gradient(135deg,#2e2000,#5a4400)', priceColor: '#fde68a', convert: (p, r) => p * r / 31.1035 * 10 },
  silver: { label: 'Silver',      unit: '₹ per kg · MCX',           icon: '🥈', gradient: 'linear-gradient(135deg,#1a2428,#2c3d4a)',  priceColor: '#e2eaed', convert: (p, r) => p * r / 31.1035 * 1000 },
  brent:  { label: 'Brent Crude', unit: '₹ per barrel · MCX',       icon: '🛢️', gradient: 'linear-gradient(135deg,#030a06,#071a0d)', priceColor: '#6ee7b7', headerFontSize: '1.6rem', convert: (p, r) => p * r },
  btc:    { label: 'Bitcoin',     unit: 'BTC · INR · 24h change',   icon: '₿',  gradient: 'linear-gradient(135deg,#2e1400,#5a2a00)', priceColor: '#fdba74', convert: (p, r) => p * r },
};

const FOREX_CONFIG = [
  { id: 'usdinr', symbol: 'USDINR=X', code: 'USD', name: 'US Dollar',        flag: '🇺🇸', decimals: 2 },
  { id: 'eurinr', symbol: 'EURINR=X', code: 'EUR', name: 'Euro',              flag: '🇪🇺', decimals: 2 },
  { id: 'gbpinr', symbol: 'GBPINR=X', code: 'GBP', name: 'British Pound',     flag: '🇬🇧', decimals: 2 },
  { id: 'aedinr', symbol: 'AEDINR=X', code: 'AED', name: 'UAE Dirham',        flag: '🇦🇪', decimals: 2 },
  { id: 'sgdinr', symbol: 'SGDINR=X', code: 'SGD', name: 'Singapore Dollar',  flag: '🇸🇬', decimals: 2 },
  { id: 'jpyinr', symbol: 'JPYINR=X', code: 'JPY', name: 'Japanese Yen',      flag: '🇯🇵', decimals: 4 },
  { id: 'chfinr', symbol: 'CHFINR=X', code: 'CHF', name: 'Swiss Franc',       flag: '🇨🇭', decimals: 2 },
  { id: 'audinr', symbol: 'AUDINR=X', code: 'AUD', name: 'Australian Dollar', flag: '🇦🇺', decimals: 2 },
];

const BANK_FD_RATES = [
  { name: 'SBI',        fullName: 'State Bank of India',    rate: 7.00, tenure: '400 days',   gradient: 'linear-gradient(135deg,#002d6e,#004b8d)' },
  { name: 'HDFC Bank',  fullName: 'HDFC Bank',              rate: 7.40, tenure: '55 months',  gradient: 'linear-gradient(135deg,#002060,#003b8f)' },
  { name: 'ICICI Bank', fullName: 'ICICI Bank',             rate: 7.25, tenure: '15–18 mo',   gradient: 'linear-gradient(135deg,#5c0a00,#a31300)' },
  { name: 'Axis Bank',  fullName: 'Axis Bank',              rate: 7.20, tenure: '1–13 mo',    gradient: 'linear-gradient(135deg,#3d0030,#7a005e)' },
  { name: 'Kotak',      fullName: 'Kotak Mahindra Bank',    rate: 7.40, tenure: '390 days',   gradient: 'linear-gradient(135deg,#6b0014,#b8001f)' },
  { name: 'BoB',        fullName: 'Bank of Baroda',         rate: 7.25, tenure: '400 days',   gradient: 'linear-gradient(135deg,#3d2000,#7a4a00)' },
  { name: 'IndusInd',   fullName: 'IndusInd Bank',          rate: 7.75, tenure: '1–2 years',  gradient: 'linear-gradient(135deg,#0a2a4a,#0f4a80)' },
  { name: 'Yes Bank',   fullName: 'Yes Bank',               rate: 7.75, tenure: '18 months',  gradient: 'linear-gradient(135deg,#003d4a,#006b80)' },
];

const RBI_REPO_RATE_HISTORY = [
  { date: "Jan'19", rate: 6.50 },
  { date: "Feb'19", rate: 6.25 },
  { date: "Apr'19", rate: 6.00 },
  { date: "Jun'19", rate: 5.75 },
  { date: "Aug'19", rate: 5.40 },
  { date: "Oct'19", rate: 5.15 },
  { date: "Mar'20", rate: 4.40 },
  { date: "May'20", rate: 4.00 },
  { date: "May'22", rate: 4.40 },
  { date: "Jun'22", rate: 4.90 },
  { date: "Aug'22", rate: 5.40 },
  { date: "Sep'22", rate: 5.90 },
  { date: "Dec'22", rate: 6.25 },
  { date: "Feb'23", rate: 6.50 },
  { date: "Feb'25", rate: 6.25 },
  { date: "Apr'25", rate: 6.00 },
];

const FOMC_MEETINGS = [
  { label: 'Mar 17–18, 2026', date: '2026-03-17' },
  { label: 'May 5–6, 2026',   date: '2026-05-05' },
  { label: 'Jun 16–17, 2026', date: '2026-06-16' },
  { label: 'Jul 28–29, 2026', date: '2026-07-28' },
  { label: 'Sep 15–16, 2026', date: '2026-09-15' },
  { label: 'Oct 27–28, 2026', date: '2026-10-27' },
  { label: 'Dec 8–9, 2026',   date: '2026-12-08' },
];

const GOVT_SCHEME_RATES = [
  { name: 'PPF',      rate: 7.10, period: 'Q4 FY25-26', gradient: 'linear-gradient(135deg,#0d2b6e,#1565c0)' },
  { name: 'EPF/PF',  rate: 8.25, period: 'FY 24-25',   gradient: 'linear-gradient(135deg,#1a4a1c,#2e7d32)' },
  { name: 'SSY',     rate: 8.20, period: 'Q4 FY25-26', gradient: 'linear-gradient(135deg,#4a0628,#880e4f)' },
  { name: 'KVP',     rate: 7.50, period: 'Q4 FY25-26', gradient: 'linear-gradient(135deg,#5c1800,#a33700)' },
  { name: 'SCSS',    rate: 8.20, period: 'Q4 FY25-26', gradient: 'linear-gradient(135deg,#250948,#4a148c)' },
  { name: 'RBI Bond',rate: 8.05, period: 'Current',    gradient: 'linear-gradient(135deg,#003540,#006064)' },
  { name: 'NSC',     rate: 7.70, period: 'Q4 FY25-26', gradient: 'linear-gradient(135deg,#6b1c07,#bf360c)' },
  { name: 'MIS',     rate: 7.40, period: 'Q4 FY25-26', gradient: 'linear-gradient(135deg,#2a1a16,#5d4037)' },
];

// ── Chart Data ─────────────────────────────────────────────────────────────────

const INDIA_INFLATION_DATA = [
  { month: "Jan'23", value: 6.52 }, { month: "Mar'23", value: 5.66 },
  { month: "May'23", value: 4.25 }, { month: "Jul'23", value: 7.44 },
  { month: "Sep'23", value: 5.02 }, { month: "Nov'23", value: 5.55 },
  { month: "Jan'24", value: 5.69 }, { month: "Mar'24", value: 4.85 },
  { month: "May'24", value: 4.75 }, { month: "Jul'24", value: 3.54 },
  { month: "Sep'24", value: 5.49 }, { month: "Nov'24", value: 5.48 },
  { month: "Jan'25", value: 4.26 }, { month: "Mar'25", value: 3.34 },
  { month: "May'25", value: 3.60 }, { month: "Jul'25", value: 3.96 },
  { month: "Sep'25", value: 3.73 }, { month: "Nov'25", value: 3.82 },
];

const INDIA_GDP_DATA = [
  { year: 'FY17', value: 8.3 }, { year: 'FY18', value: 6.8 },
  { year: 'FY19', value: 6.5 }, { year: 'FY20', value: 5.0 },
  { year: 'FY21', value: -5.8 }, { year: 'FY22', value: 9.1 },
  { year: 'FY23', value: 7.2 }, { year: 'FY24', value: 8.2 },
  { year: 'FY25', value: 6.4 }, { year: 'FY26*', value: 6.8 },
];

const US_INFLATION_DATA = [
  { month: "Jan'23", value: 6.4 }, { month: "Mar'23", value: 5.0 },
  { month: "May'23", value: 4.0 }, { month: "Jul'23", value: 3.2 },
  { month: "Sep'23", value: 3.7 }, { month: "Nov'23", value: 3.1 },
  { month: "Jan'24", value: 3.1 }, { month: "Mar'24", value: 3.5 },
  { month: "May'24", value: 3.3 }, { month: "Jul'24", value: 2.9 },
  { month: "Sep'24", value: 2.4 }, { month: "Nov'24", value: 2.7 },
  { month: "Jan'25", value: 3.0 }, { month: "Mar'25", value: 2.6 },
  { month: "May'25", value: 2.4 }, { month: "Jul'25", value: 2.9 },
  { month: "Sep'25", value: 2.6 }, { month: "Nov'25", value: 2.7 },
];

const US_UNEMPLOYMENT_DATA = [
  { month: "Jan'23", value: 3.4 }, { month: "Mar'23", value: 3.5 },
  { month: "May'23", value: 3.7 }, { month: "Jul'23", value: 3.5 },
  { month: "Sep'23", value: 3.8 }, { month: "Nov'23", value: 3.7 },
  { month: "Jan'24", value: 3.7 }, { month: "Mar'24", value: 3.8 },
  { month: "May'24", value: 4.0 }, { month: "Jul'24", value: 4.3 },
  { month: "Sep'24", value: 4.1 }, { month: "Nov'24", value: 4.2 },
  { month: "Jan'25", value: 4.0 }, { month: "Mar'25", value: 4.2 },
  { month: "May'25", value: 4.0 }, { month: "Jul'25", value: 4.0 },
  { month: "Sep'25", value: 4.0 }, { month: "Nov'25", value: 4.0 },
];

// ── Utilities ──────────────────────────────────────────────────────────────────

const defaultQuote = (): LiveQuote => ({
  price: null, changePercent: null, loading: true, error: false, lastUpdated: null,
});

const formatIndexPrice = (price: number, currency: string): string => {
  if (currency === 'INR') return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(price);
  if (currency === 'JPY' || currency === 'BRL' || currency === 'CNY')
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(price);
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(price);
};

const formatUSD = (price: number, dec = 2) =>
  `$${new Intl.NumberFormat('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(price)}`;

const formatBTC = (price: number) =>
  `$${new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(price)}`;

const formatINR = (price: number, dec = 0) =>
  `₹${new Intl.NumberFormat('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(price)}`;

const formatLastUpdated = (d: Date | null) => {
  if (!d) return '';
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins === 1) return '1 min ago';
  return `${mins} min ago`;
};

const getToken = () => localStorage.getItem('token');

// ── API calls via backend proxy ────────────────────────────────────────────────

const fetchQuotesBatch = async (symbols: string[]): Promise<Record<string, { price: number; changePercent: number; ok: boolean }>> => {
  const token = getToken();
  const symbolStr = symbols.join(',');
  const res = await axios.get<{ quotes: Array<{ symbol: string; price: number | null; change_pct: number | null; ok: boolean }> }>(
    `/api/v1/market/quotes?symbols=${encodeURIComponent(symbolStr)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const out: Record<string, { price: number; changePercent: number; ok: boolean }> = {};
  for (const q of res.data.quotes) {
    out[q.symbol] = { price: q.price ?? 0, changePercent: q.change_pct ?? 0, ok: q.ok };
  }
  return out;
};

const fetchBtcProxy = async (): Promise<{ price: number; changePercent: number }> => {
  const token = getToken();
  const res = await axios.get<{ price: number; change_pct: number; ok: boolean }>(
    '/api/v1/market/bitcoin',
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.data.ok) throw new Error('BTC fetch failed');
  return { price: res.data.price, changePercent: res.data.change_pct };
};

// ── Sub-components ─────────────────────────────────────────────────────────────

const ChangeLabel: React.FC<{ change: number | null; white?: boolean; darkOnLight?: boolean; large?: boolean; medium?: boolean }> = ({ change, white, darkOnLight, large, medium }) => {
  if (change === null) return <Typography variant="caption" sx={{ opacity: 0.5 }}>—</Typography>;
  const positive = change >= 0;
  const color = darkOnLight
    ? (positive ? '#1a5200' : '#7a0000')
    : white
      ? (positive ? '#a5f3a5' : '#ffb3b3')
      : (positive ? '#4caf50' : '#f44336');
  const Icon = positive ? TrendingUpIcon : TrendingDownIcon;
  const iconSize = large ? 26 : medium ? 20 : 13;
  const fontSize = large ? '1.5rem' : medium ? '1.1rem' : '0.75rem';
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.3 }}>
      <Icon sx={{ fontSize: iconSize, color }} />
      <Typography sx={{ color, fontWeight: 700, lineHeight: 1, fontSize }}>
        {positive ? '+' : ''}{change.toFixed(2)}%
      </Typography>
    </Box>
  );
};

// Colorful index card
const IndexCard: React.FC<{ config: IndexConfig; quote: LiveQuote }> = ({ config, quote }) => (
  <Box
    onClick={() => window.open(config.tradingViewUrl, '_blank', 'noopener,noreferrer')}
    sx={{
      p: 2.5,
      borderRadius: 2.5,
      background: 'linear-gradient(135deg,#1e2a38,#2c3e52)',
      cursor: 'pointer',
      color: '#fff',
      transition: 'transform 0.18s, box-shadow 0.18s',
      boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
      '&:hover': { transform: 'translateY(-3px)', boxShadow: '0 8px 20px rgba(0,0,0,0.4)' },
    }}
  >
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography sx={{ fontSize: 26, lineHeight: 1 }}>{config.flag}</Typography>
        <Typography sx={{ color: '#fff', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, fontSize: 14 }}>
          {config.country}
        </Typography>
      </Box>
      <OpenInNewIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.7)' }} />
    </Box>
    <Typography sx={{ fontWeight: 800, display: 'block', color: '#fff', mb: 1, lineHeight: 1.2, fontSize: 20 }}>
      {config.shortName}
    </Typography>
    {quote.loading ? (
      <Typography sx={{ color: '#ffffffaa', fontSize: 14 }}>Loading…</Typography>
    ) : quote.error || quote.price === null ? (
      <Typography sx={{ color: '#ffffffaa', fontSize: 14 }}>N/A</Typography>
    ) : (
      <>
        <Typography sx={{ fontWeight: 900, fontFamily: 'monospace', lineHeight: 1.2, fontSize: 22, color: '#fff' }}>
          {formatIndexPrice(quote.price, config.currency)}
        </Typography>
        <ChangeLabel change={quote.changePercent} white medium />
      </>
    )}
  </Box>
);

// Recharts tooltip
const ChartTip: React.FC<{ active?: boolean; payload?: Array<{ value: number }>; label?: string; unit?: string }> =
  ({ active, payload, label, unit = '%' }) => {
    if (!active || !payload?.length) return null;
    return (
      <Paper sx={{ p: 1, fontSize: 12 }}>
        <Typography variant="caption" sx={{ fontWeight: 700, display: 'block' }}>{label}</Typography>
        <Typography variant="caption">{payload[0].value.toFixed(2)}{unit}</Typography>
      </Paper>
    );
  };

// Colorful stat card for charts section header
// ── Main Component ─────────────────────────────────────────────────────────────

const MarketInsight: React.FC = () => {
  const theme = useTheme();

  const [quotes, setQuotes] = useState<Record<string, LiveQuote>>(() => {
    const init: Record<string, LiveQuote> = {};
    WORLD_INDICES.forEach((idx) => { init[idx.id] = defaultQuote(); });
    COMMODITY_IDS.forEach((c) => { init[c] = defaultQuote(); });
    init['btc'] = defaultQuote();
    FOREX_CONFIG.forEach((f) => { init[f.id] = defaultQuote(); });
    return init;
  });

  const [lastRefreshIndices, setLastRefreshIndices] = useState<Date | null>(null);
  const [lastRefreshBtc, setLastRefreshBtc] = useState<Date | null>(null);

  const setLoading = (ids: string[]) => {
    setQuotes((prev) => {
      const next = { ...prev };
      ids.forEach((id) => { next[id] = { ...next[id], loading: true, error: false }; });
      return next;
    });
  };

  const applyQuotes = useCallback((updates: Record<string, { price: number | null; changePercent: number | null; ok: boolean }>) => {
    setQuotes((prev) => {
      const next = { ...prev };
      for (const [id, q] of Object.entries(updates)) {
        next[id] = {
          price: q.ok ? q.price : null,
          changePercent: q.ok ? q.changePercent : null,
          loading: false,
          error: !q.ok,
          lastUpdated: q.ok ? new Date() : prev[id]?.lastUpdated ?? null,
        };
      }
      return next;
    });
  }, []);

  const refreshIndices = useCallback(async () => {
    const indexSymbols = WORLD_INDICES.map((i) => i.yahooSymbol);
    const commSymbols = COMMODITY_IDS.map((c) => COMMODITY_CONFIG[c].yahooSymbol);
    const forexSymbols = FOREX_CONFIG.map((f) => f.symbol);
    const allSymbols = [...indexSymbols, ...commSymbols, ...forexSymbols];
    setLoading([...WORLD_INDICES.map((i) => i.id), ...COMMODITY_IDS, ...FOREX_CONFIG.map((f) => f.id)]);
    try {
      const result = await fetchQuotesBatch(allSymbols);
      const updates: Record<string, { price: number | null; changePercent: number | null; ok: boolean }> = {};
      WORLD_INDICES.forEach((idx) => {
        const r = result[idx.yahooSymbol];
        updates[idx.id] = r ? { price: r.price, changePercent: r.changePercent, ok: r.ok } : { price: null, changePercent: null, ok: false };
      });
      COMMODITY_IDS.forEach((c) => {
        const r = result[COMMODITY_CONFIG[c].yahooSymbol];
        updates[c] = r ? { price: r.price, changePercent: r.changePercent, ok: r.ok } : { price: null, changePercent: null, ok: false };
      });
      FOREX_CONFIG.forEach((f) => {
        const r = result[f.symbol];
        updates[f.id] = r ? { price: r.price, changePercent: r.changePercent, ok: r.ok } : { price: null, changePercent: null, ok: false };
      });
      applyQuotes(updates);
      setLastRefreshIndices(new Date());
    } catch {
      const failed: Record<string, { price: null; changePercent: null; ok: boolean }> = {};
      [...WORLD_INDICES.map((i) => i.id), ...COMMODITY_IDS, ...FOREX_CONFIG.map((f) => f.id)].forEach((id) => {
        failed[id] = { price: null, changePercent: null, ok: false };
      });
      applyQuotes(failed);
    }
  }, [applyQuotes]);

  const refreshBtc = useCallback(async () => {
    setQuotes((prev) => ({ ...prev, btc: { ...prev['btc'], loading: true, error: false } }));
    try {
      const { price, changePercent } = await fetchBtcProxy();
      setQuotes((prev) => ({ ...prev, btc: { price, changePercent, loading: false, error: false, lastUpdated: new Date() } }));
      setLastRefreshBtc(new Date());
    } catch {
      setQuotes((prev) => ({ ...prev, btc: { ...prev['btc'], loading: false, error: true } }));
    }
  }, []);

  useEffect(() => { refreshIndices(); refreshBtc(); }, [refreshIndices, refreshBtc]);
  useEffect(() => { const id = setInterval(refreshIndices, 30 * 60 * 1000); return () => clearInterval(id); }, [refreshIndices]);
  useEffect(() => { const id = setInterval(refreshBtc, 5 * 60 * 1000); return () => clearInterval(id); }, [refreshBtc]);

  const btc = quotes['btc'];
  const upcomingFomc = FOMC_MEETINGS.filter((m) => new Date(m.date) >= new Date());
  const nextFomc = upcomingFomc[0];
  const daysToNext = nextFomc ? Math.ceil((new Date(nextFomc.date).getTime() - Date.now()) / 86400000) : null;

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 }, maxWidth: 1600, mx: 'auto' }}>

      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: -0.5 }}>Market Insight</Typography>
          <Typography variant="body2" color="text.secondary">
            Live indices · commodities · macro indicators · policy rates
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {lastRefreshIndices && (
            <Typography variant="caption" color="text.secondary">
              Updated {formatLastUpdated(lastRefreshIndices)}
            </Typography>
          )}
          <Tooltip title="Refresh all live prices">
            <IconButton size="small" onClick={() => { refreshIndices(); refreshBtc(); }}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* ── Section 1: Global Market Indices ────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 },
          borderRadius: 3,
          mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>🌐</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Global Market Indices</Typography>
          <Chip label="Click any index for live chart" size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 11 }} />
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)', md: 'repeat(5, 1fr)' }, gap: 1.5 }}>
          {WORLD_INDICES.map((idx) => (
            <IndexCard key={idx.id} config={idx} quote={quotes[idx.id]} />
          ))}
        </Box>
      </Paper>

      {/* ── Section 2: Commodity Prices ──────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 },
          borderRadius: 3,
          mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>📦</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Commodity Prices</Typography>
          <Chip label="Global (USD) · India (INR)" size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 11 }} />
        </Box>

        {/* USD row */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2, mb: 2 }}>

        {/* Gold, Silver, Brent Crude — uniform cards */}
        {COMMODITY_IDS.map((id) => {
          const cfg = COMMODITY_CONFIG[id];
          const q = quotes[id];
          return (
            <Paper
              key={id}
              elevation={3}
              onClick={() => window.open(cfg.link, '_blank', 'noopener,noreferrer')}
              sx={{
                p: 2.5, borderRadius: 3, background: cfg.gradient, cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
                transition: 'transform 0.18s, box-shadow 0.18s',
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 170,
                '&:hover': { transform: 'translateY(-3px)', boxShadow: '0 10px 28px rgba(0,0,0,0.5)' },
              }}
            >
              <Box>
                {/* Header: icon + name */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
                  <Typography sx={{ fontSize: 40, lineHeight: 1 }}>{cfg.icon}</Typography>
                  <Typography sx={{ fontWeight: 800, fontSize: cfg.headerFontSize ?? '2rem', color: cfg.darkText ? '#1a1000' : '#fff', lineHeight: 1.1, flex: 1 }}>{cfg.label}</Typography>
                  <OpenInNewIcon sx={{ fontSize: 14, color: cfg.darkText ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.55)', flexShrink: 0 }} />
                </Box>
                {/* Price */}
                {q.loading ? (
                  <Typography variant="body2" sx={{ color: cfg.darkText ? 'rgba(0,0,0,0.5)' : 'rgba(255,255,255,0.6)' }}>Loading…</Typography>
                ) : q.error || q.price === null ? (
                  <Typography variant="body2" sx={{ color: cfg.darkText ? 'rgba(0,0,0,0.5)' : 'rgba(255,255,255,0.6)' }}>N/A</Typography>
                ) : (
                  <>
                    <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: 'monospace', color: cfg.priceColor, lineHeight: 1.1 }}>
                      {formatUSD(q.price, 2)}
                    </Typography>
                    <ChangeLabel change={q.changePercent} white={!cfg.darkText} darkOnLight={cfg.darkText} medium />
                  </>
                )}
              </Box>
              {/* Footer: unit */}
              <Typography variant="caption" sx={{ color: cfg.darkText ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.5)', display: 'block', mt: 1.5 }}>{cfg.unit}</Typography>
            </Paper>
          );
        })}

        {/* Bitcoin — same structure */}
        <Paper
          elevation={3}
          sx={{
            p: 2.5, borderRadius: 3,
            background: 'linear-gradient(135deg,#4a2200,#9e4800)',
            boxShadow: '0 4px 16px rgba(158,72,0,0.5)',
            transition: 'transform 0.18s, box-shadow 0.18s',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 170,
            '&:hover': { transform: 'translateY(-3px)', boxShadow: '0 10px 28px rgba(158,72,0,0.6)' },
          }}
        >
          <Box>
            {/* Header: icon + name */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
              <BitcoinIcon sx={{ fontSize: 40, color: '#f97316' }} />
              <Typography sx={{ fontWeight: 800, fontSize: '2rem', color: '#fff', lineHeight: 1.1, flex: 1 }}>Bitcoin</Typography>
              <Tooltip title="Refresh (auto every 5 min)">
                <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.6)', p: 0.5 }} onClick={(e) => { e.stopPropagation(); refreshBtc(); }}>
                  <RefreshIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            </Box>
            {/* Price */}
            {btc.loading ? (
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>Loading…</Typography>
            ) : btc.error || btc.price === null ? (
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>N/A</Typography>
            ) : (
              <>
                <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: 'monospace', color: '#fdba74', lineHeight: 1.1 }}>
                  {formatBTC(btc.price)}
                </Typography>
                <ChangeLabel change={btc.changePercent} white medium />
              </>
            )}
          </Box>
          {/* Footer: unit + last refresh */}
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block' }}>BTC · USD · 24h change</Typography>
            {lastRefreshBtc && (
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>
                Updated {formatLastUpdated(lastRefreshBtc)}
              </Typography>
            )}
          </Box>
        </Paper>
      </Box>

        {/* INR row */}
        {(() => {
        const usdInr = quotes['usdinr']?.price;
        const loading = !usdInr || quotes['usdinr']?.loading;
        const inrCards: Array<{ id: 'gold' | 'silver' | 'brent' | 'btc'; usdPrice: number | null; changePct: number | null; usdLoading: boolean }> = [
          { id: 'gold',   usdPrice: quotes['gold']?.price,   changePct: quotes['gold']?.changePercent,   usdLoading: quotes['gold']?.loading },
          { id: 'silver', usdPrice: quotes['silver']?.price, changePct: quotes['silver']?.changePercent, usdLoading: quotes['silver']?.loading },
          { id: 'brent',  usdPrice: quotes['brent']?.price,  changePct: quotes['brent']?.changePercent,  usdLoading: quotes['brent']?.loading },
          { id: 'btc',    usdPrice: btc.price,               changePct: btc.changePercent,               usdLoading: btc.loading },
        ];
        return (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
            {inrCards.map(({ id, usdPrice, changePct, usdLoading }) => {
              const cfg = INDIA_COMMODITY_CONFIG[id];
              const isLoading = loading || usdLoading;
              const inrPrice = !isLoading && usdPrice && usdInr ? cfg.convert(usdPrice, usdInr) : null;
              return (
                <Paper
                  key={`inr-${id}`}
                  elevation={3}
                  sx={{
                    p: 2.5, borderRadius: 3, background: cfg.gradient,
                    boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
                    transition: 'transform 0.18s, box-shadow 0.18s',
                    display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 170,
                    '&:hover': { transform: 'translateY(-3px)', boxShadow: '0 10px 28px rgba(0,0,0,0.5)' },
                  }}
                >
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
                      {id === 'btc'
                        ? <BitcoinIcon sx={{ fontSize: 40, color: '#f97316' }} />
                        : <Typography sx={{ fontSize: 40, lineHeight: 1 }}>{cfg.icon}</Typography>
                      }
                      <Box sx={{ flex: 1 }}>
                        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.6)', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase', mb: 0.2 }}>🇮🇳 India</Typography>
                        <Typography sx={{ fontWeight: 800, fontSize: cfg.headerFontSize ?? '2rem', color: '#fff', lineHeight: 1.1 }}>{cfg.label}</Typography>
                      </Box>
                    </Box>
                    {isLoading ? (
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>Loading…</Typography>
                    ) : inrPrice === null ? (
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>N/A</Typography>
                    ) : (
                      <>
                        <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: 'monospace', color: cfg.priceColor, lineHeight: 1.1 }}>
                          {formatINR(inrPrice)}
                        </Typography>
                        <ChangeLabel change={changePct} white medium />
                      </>
                    )}
                  </Box>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mt: 1.5 }}>{cfg.unit}</Typography>
                </Paper>
              );
            })}
          </Box>
        );
      })()}
      </Paper>

      {/* ── Section 2c: Currency Conversion Rates ───────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 },
          borderRadius: 3,
          mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>💱</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Currency Conversion Rates</Typography>
          <Chip label="1 unit → INR" size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 11 }} />
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, 1fr)', md: 'repeat(4, 1fr)' }, gap: 1.5 }}>
          {FOREX_CONFIG.map((fx) => {
            const q = quotes[fx.id];
            return (
              <Box
                key={fx.id}
                sx={{
                  p: 2, borderRadius: 2.5,
                  background: 'linear-gradient(135deg,#1e2a38,#2c3e52)',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                  transition: 'transform 0.18s, box-shadow 0.18s',
                  '&:hover': { transform: 'translateY(-3px)', boxShadow: '0 8px 20px rgba(0,0,0,0.4)' },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography sx={{ fontSize: 26, lineHeight: 1 }}>{fx.flag}</Typography>
                  <Box>
                    <Typography sx={{ fontWeight: 800, fontSize: 20, color: '#fff', lineHeight: 1 }}>{fx.code}</Typography>
                    <Typography sx={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', lineHeight: 1.2 }}>{fx.name}</Typography>
                  </Box>
                </Box>
                {q.loading ? (
                  <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>Loading…</Typography>
                ) : q.error || q.price === null ? (
                  <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>N/A</Typography>
                ) : (
                  <>
                    <Typography sx={{ fontWeight: 900, fontFamily: 'monospace', fontSize: 22, color: '#93c5fd', lineHeight: 1.2 }}>
                      {formatINR(q.price, fx.decimals)}
                    </Typography>
                    <ChangeLabel change={q.changePercent} white medium />
                  </>
                )}
              </Box>
            );
          })}
        </Box>
      </Paper>

      {/* ── Section 3: Macro Charts ──────────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 },
          borderRadius: 3,
          mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>📊</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Macroeconomic Indicators</Typography>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>

        {/* India CPI */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#1a0a00,#2a1100)' : 'linear-gradient(145deg,#fff8f4,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#ff6b35,#f7c59f)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇮🇳</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India CPI Inflation</Typography>
              <Typography variant="caption" color="text.secondary">YoY % · Jan 2023 – Nov 2025</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={INDIA_INFLATION_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradIndia" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff6b35" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#ff6b35" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[2, 9]} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <ReferenceLine y={4} stroke="#4caf50" strokeDasharray="4 2" label={{ value: '4% target', fontSize: 9, fill: '#4caf50' }} />
              <Area type="monotone" dataKey="value" stroke="#ff6b35" fill="url(#gradIndia)" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: MoSPI / RBI</Typography>
        </Paper>

        {/* India GDP */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#000d1a,#001a33)' : 'linear-gradient(145deg,#f0f6ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#0052cc,#4c9aff)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>📈</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India GDP Growth</Typography>
              <Typography variant="caption" color="text.secondary">Annual Real GDP % · FY17 – FY26</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={INDIA_GDP_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <ReferenceLine y={0} stroke={theme.palette.divider} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {INDIA_GDP_DATA.map((entry, i) => (
                  <Cell key={i} fill={entry.value < 0 ? '#f44336' : entry.year.includes('*') ? '#90caf9' : '#2196f3'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>* FY26 estimate · Source: NSO / World Bank</Typography>
        </Paper>

        {/* US CPI */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#0d0020,#1a0040)' : 'linear-gradient(145deg,#f8f4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#7c4dff,#b47cff)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇺🇸</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US CPI Inflation</Typography>
              <Typography variant="caption" color="text.secondary">YoY % · Jan 2023 – Nov 2025</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={US_INFLATION_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradUS" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7c4dff" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#7c4dff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[1, 8]} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <ReferenceLine y={2} stroke="#4caf50" strokeDasharray="4 2" label={{ value: '2% target', fontSize: 9, fill: '#4caf50' }} />
              <Area type="monotone" dataKey="value" stroke="#7c4dff" fill="url(#gradUS)" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: BLS</Typography>
        </Paper>

        {/* US Unemployment */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#001a1a,#003333)' : 'linear-gradient(145deg,#f0ffff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#006064,#26c6da)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>👷</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US Unemployment Rate</Typography>
              <Typography variant="caption" color="text.secondary">Seasonally Adjusted % · Jan 2023 – Nov 2025</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={US_UNEMPLOYMENT_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[2.5, 5.5]} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Line type="monotone" dataKey="value" stroke="#00bcd4" strokeWidth={2.5} dot={{ r: 2, fill: '#00bcd4' }} />
            </LineChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: BLS</Typography>
        </Paper>
        </Box>
      </Paper>

      {/* ── Section 4: Interest Rates ────────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 }, borderRadius: 3, mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>📈</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Interest Rates</Typography>
          <Chip label="General Public · Best available rate" size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 11 }} />
        </Box>

        {/* RBI Repo Rate — historical chart */}
        <Paper
          elevation={2}
          sx={{
            p: { xs: 2, sm: 2.5 }, borderRadius: 3, mb: 2,
            background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#071220,#0d1f35)' : 'linear-gradient(145deg,#f0f7ff,#fff)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 1 }}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BankIcon sx={{ color: '#1e88e5' }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>RBI Repo Rate — Historical</Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">Reserve Bank of India · Jan 2019 – present</Typography>
            </Box>
            <Box sx={{ textAlign: 'right' }}>
              <Typography sx={{ fontWeight: 900, fontSize: 36, color: '#1e88e5', fontFamily: 'monospace', lineHeight: 1 }}>
                6.00<Typography component="span" sx={{ fontSize: 18, fontWeight: 700, color: '#1e88e5' }}>%</Typography>
              </Typography>
              <Typography variant="caption" color="text.secondary">Current · Effective Apr 2025</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={RBI_REPO_RATE_HISTORY} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="rbiGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#1e88e5" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#1e88e5" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis domain={[3.5, 7.0]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={42} />
              <RechartTooltip formatter={(v: number) => [`${v.toFixed(2)}%`, 'Repo Rate']} />
              <ReferenceLine y={6.00} stroke="#1e88e5" strokeDasharray="4 3" label={{ value: 'Current 6%', position: 'insideTopRight', fontSize: 11, fill: '#1e88e5' }} />
              <Area type="stepAfter" dataKey="rate" stroke="#1e88e5" strokeWidth={2.5} fill="url(#rbiGrad)" dot={{ r: 3, fill: '#1e88e5' }} activeDot={{ r: 5 }} />
            </AreaChart>
          </ResponsiveContainer>
          <Box sx={{ display: 'flex', gap: 3, mt: 1.5, flexWrap: 'wrap' }}>
            {[{ label: 'SDF', val: '5.75%' }, { label: 'MSF', val: '6.25%' }, { label: 'CRR', val: '4.00%' }, { label: 'SLR', val: '18.00%' }].map((r) => (
              <Box key={r.label}>
                <Typography variant="caption" color="text.secondary">{r.label}</Typography>
                <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{r.val}</Typography>
              </Box>
            ))}
          </Box>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 1, textAlign: 'right' }}>Source: RBI</Typography>
        </Paper>

        {/* Bank FD Rates */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, 1fr)', md: 'repeat(8, 1fr)' }, gap: 1.5 }}>
          {BANK_FD_RATES.map((b) => (
            <Box
              key={b.name}
              sx={{
                p: 2, borderRadius: 2.5, textAlign: 'center',
                background: b.gradient,
                boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                color: '#fff',
                display: 'flex', flexDirection: 'column', gap: 0.5,
              }}
            >
              <Typography sx={{ fontWeight: 800, fontSize: 15, color: '#fff', lineHeight: 1.2 }}>{b.name}</Typography>
              <Typography sx={{ fontWeight: 900, fontSize: 28, lineHeight: 1, color: '#fff' }}>
                {b.rate}<Typography component="span" sx={{ fontSize: 16, fontWeight: 700 }}>%</Typography>
              </Typography>
              <Typography sx={{ fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>{b.tenure}</Typography>
            </Box>
          ))}
        </Box>
      </Paper>

      {/* ── Section 5: Govt. Scheme Interest Rates ───────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 }, borderRadius: 3, mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>💰</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Govt. Scheme Interest Rates</Typography>
          <Chip label="Q4 FY 2025–26" size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 11 }} />
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(4, 1fr)', md: 'repeat(8, 1fr)' }, gap: 1.5 }}>
          {GOVT_SCHEME_RATES.map((s) => (
            <Box
              key={s.name}
              sx={{
                p: 2, borderRadius: 2.5, textAlign: 'center',
                background: s.gradient,
                boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                color: '#fff',
                display: 'flex', flexDirection: 'column', gap: 0.5,
              }}
            >
              <Typography sx={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: 0.5, fontSize: 15, color: '#fff', lineHeight: 1.2 }}>
                {s.name}
              </Typography>
              <Typography sx={{ fontWeight: 900, fontSize: 28, lineHeight: 1, color: '#fff' }}>
                {s.rate}<Typography component="span" sx={{ fontSize: 16, fontWeight: 700 }}>%</Typography>
              </Typography>
              <Typography sx={{ fontSize: 12, color: 'rgba(255,255,255,0.85)' }}>{s.period}</Typography>
            </Box>
          ))}
        </Box>
      </Paper>

      {/* ── Upcoming Events ──────────────────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 }, borderRadius: 3, mb: 2.5,
          background: theme.palette.mode === 'dark'
            ? 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)'
            : 'linear-gradient(135deg,#e8f0fe 0%,#f0f4ff 100%)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>📅</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Upcoming Events</Typography>
        </Box>
        <Paper
          elevation={2}
          sx={{
            p: { xs: 2, sm: 2.5 }, borderRadius: 3,
            background: theme.palette.mode === 'dark'
              ? 'linear-gradient(145deg,#0d0d2b,#1a1a4e)'
              : 'linear-gradient(145deg,#f5f4ff,#eef0ff)',
            border: `1px solid ${theme.palette.mode === 'dark' ? '#2d2d7a' : '#c5c3f0'}`,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <EventIcon sx={{ color: '#7c4dff' }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Fed FOMC Meetings 2026</Typography>
          </Box>
          {daysToNext !== null && (
            <Box sx={{
              mb: 1.5, p: 1.5, borderRadius: 2,
              background: daysToNext <= 10 ? 'linear-gradient(135deg,#b71c1c22,#f4433644)' : 'linear-gradient(135deg,#1a237e22,#3f51b544)',
              border: `1px solid ${daysToNext <= 10 ? '#f44336' : '#3f51b5'}66`,
            }}>
              <Typography variant="caption" color="text.secondary">⏰ Next meeting</Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{nextFomc.label}</Typography>
              <Chip
                label={daysToNext <= 0 ? 'Today!' : `In ${daysToNext} days`}
                size="small"
                color={daysToNext <= 10 ? 'error' : 'primary'}
                sx={{ mt: 0.5, height: 20, fontSize: 11 }}
              />
            </Box>
          )}
        </Paper>
      </Paper>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <Alert severity="info" sx={{ borderRadius: 2, mt: 1 }} icon={false}>
        <Typography variant="caption" color="text.secondary">
          <strong>Live data:</strong> Indices &amp; commodities via Yahoo Finance (server-side proxy) — auto-refresh every <strong>30 min</strong>.
          Bitcoin via CoinGecko — auto-refresh every <strong>5 min</strong>.
          Macro charts show representative historical data (MoSPI, RBI, BLS). Policy rates are manually maintained — verify with official sources before investing.
        </Typography>
      </Alert>
    </Box>
  );
};

export default MarketInsight;
