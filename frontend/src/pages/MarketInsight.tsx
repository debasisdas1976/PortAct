import React, { useEffect, useState, useCallback } from 'react';
import GaugeComponent from 'react-gauge-component';
import {
  Box, Paper, Typography,
  Chip, IconButton, Tooltip, Stack,
  useTheme, Alert,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  CurrencyBitcoin as BitcoinIcon,
  EventNote as EventIcon,
  AccountBalance as BankIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Brush,
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

interface MacroData {
  rbi_repo_rate: Array<{ date: string; rate: number }> | null;
  india_cpi: Array<{ month: string; value: number }> | null;
  india_gdp_growth: Array<{ month: string; value: number }> | null;
  us_cpi: Array<{ month: string; value: number }> | null;
  us_unemployment: Array<{ month: string; value: number }> | null;
  us_fed_rate: Array<{ month: string; value: number }> | null;
  us_10y_yield: Array<{ month: string; value: number }> | null;
  nifty_pe: Array<{ month: string; value: number }> | null;
  india_vix: Array<{ month: string; value: number }> | null;
  fii_equity_flow: Array<{ month: string; value: number }> | null;
  dii_equity_flow: Array<{ month: string; value: number }> | null;
  india_sip_inflow: Array<{ month: string; value: number }> | null;
}

interface ReferenceRateItem {
  name: string;
  rate: number;
  sub_info: string | null;
  updated_at: string;
}

interface ReferenceRatesData {
  bank_fd: ReferenceRateItem[];
  govt_schemes: ReferenceRateItem[];
}

interface FinancialEvent {
  title: string;
  subtitle: string;
  date: string;
  category: 'central_bank' | 'tax' | 'market' | 'economic_data' | 'policy';
  region: string;
  flag: string;
  description: string;
  importance: 'high' | 'medium' | 'low';
  days_until: number;
}

interface GlobalNewsItem {
  title: string;
  url: string;
  published: string | null;
  source: string;
  category: string;
  summary: string;
}

interface MarketHoliday {
  date: string;
  name: string;
}

interface UpcomingEventsData {
  calendar_events: FinancialEvent[];
  global_news: GlobalNewsItem[];
  market_holidays: MarketHoliday[];
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

const CATEGORY_CARD_META: Record<string, { emoji: string; label: string; gradient: string; chip: string }> = {
  central_bank: { emoji: '🏦', label: 'Central Bank',  gradient: 'linear-gradient(135deg,#3d0072,#7b1fa2)', chip: '#ce93d8' },
  markets:      { emoji: '📈', label: 'Markets',        gradient: 'linear-gradient(135deg,#012f5c,#0277bd)', chip: '#81d4fa' },
  economy:      { emoji: '📊', label: 'Economy',        gradient: 'linear-gradient(135deg,#003328,#00796b)', chip: '#80cbc4' },
  commodities:  { emoji: '🛢️', label: 'Commodities',   gradient: 'linear-gradient(135deg,#7a2900,#e65100)', chip: '#ffcc80' },
  crypto:       { emoji: '₿',  label: 'Crypto',         gradient: 'linear-gradient(135deg,#3e1a00,#e65100)', chip: '#ffe082' },
  corporate:    { emoji: '🏢', label: 'Corporate',      gradient: 'linear-gradient(135deg,#0d1257,#303f9f)', chip: '#9fa8da' },
  india:        { emoji: '🇮🇳', label: 'India',         gradient: 'linear-gradient(135deg,#7f0000,#c62828)', chip: '#ef9a9a' },
  policy:       { emoji: '🏛️', label: 'Policy',        gradient: 'linear-gradient(135deg,#1c2a30,#37474f)', chip: '#b0bec5' },
};

// Static display config for bank FDs — rates come from API (/market/reference-rates)
const BANK_FD_DISPLAY = [
  { key: 'sbi',      displayName: 'SBI',        gradient: 'linear-gradient(135deg,#002d6e,#004b8d)' },
  { key: 'hdfc',     displayName: 'HDFC Bank',  gradient: 'linear-gradient(135deg,#002060,#003b8f)' },
  { key: 'icici',    displayName: 'ICICI Bank', gradient: 'linear-gradient(135deg,#5c0a00,#a31300)' },
  { key: 'axis',     displayName: 'Axis Bank',  gradient: 'linear-gradient(135deg,#3d0030,#7a005e)' },
  { key: 'kotak',    displayName: 'Kotak',      gradient: 'linear-gradient(135deg,#6b0014,#b8001f)' },
  { key: 'bob',      displayName: 'BoB',        gradient: 'linear-gradient(135deg,#3d2000,#7a4a00)' },
  { key: 'indusind', displayName: 'IndusInd',   gradient: 'linear-gradient(135deg,#0a2a4a,#0f4a80)' },
  { key: 'yesbank',  displayName: 'Yes Bank',   gradient: 'linear-gradient(135deg,#003d4a,#006b80)' },
];



// Static display config for govt schemes — rates come from API (/market/reference-rates)
const GOVT_SCHEME_DISPLAY = [
  { key: 'ppf',      displayName: 'PPF',      gradient: 'linear-gradient(135deg,#0d2b6e,#1565c0)' },
  { key: 'epf',      displayName: 'EPF/PF',   gradient: 'linear-gradient(135deg,#1a4a1c,#2e7d32)' },
  { key: 'ssy',      displayName: 'SSY',      gradient: 'linear-gradient(135deg,#4a0628,#880e4f)' },
  { key: 'kvp',      displayName: 'KVP',      gradient: 'linear-gradient(135deg,#5c1800,#a33700)' },
  { key: 'scss',     displayName: 'SCSS',     gradient: 'linear-gradient(135deg,#250948,#4a148c)' },
  { key: 'rbi_bond', displayName: 'RBI Bond', gradient: 'linear-gradient(135deg,#003540,#006064)' },
  { key: 'nsc',      displayName: 'NSC',      gradient: 'linear-gradient(135deg,#6b1c07,#bf360c)' },
  { key: 'mis',      displayName: 'MIS',      gradient: 'linear-gradient(135deg,#2a1a16,#5d4037)' },
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

const fetchMMI = async (): Promise<{ value: number | null; sentiment: string | null; source: string }> => {
  const token = getToken();
  const res = await axios.get('/api/v1/market/mmi', { headers: { Authorization: `Bearer ${token}` } });
  return res.data;
};

const fetchBtcFng = async (): Promise<{ value: number | null; sentiment: string | null; source: string }> => {
  const token = getToken();
  const res = await axios.get('/api/v1/market/btc-fng', { headers: { Authorization: `Bearer ${token}` } });
  return res.data;
};

const fetchUsFng = async (): Promise<{ value: number | null; sentiment: string | null; source: string }> => {
  const token = getToken();
  const res = await axios.get('/api/v1/market/us-fng', { headers: { Authorization: `Bearer ${token}` } });
  return res.data;
};

const fetchMacroIndicators = async (): Promise<MacroData> => {
  const token = getToken();
  const res = await axios.get<MacroData>(
    '/api/v1/market/macro-indicators',
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return res.data;
};

const fetchReferenceRates = async (): Promise<ReferenceRatesData> => {
  const token = getToken();
  const res = await axios.get<ReferenceRatesData>(
    '/api/v1/market/reference-rates',
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return res.data;
};

const fetchUpcomingEvents = async (): Promise<UpcomingEventsData> => {
  const token = getToken();
  const res = await axios.get<UpcomingEventsData>(
    '/api/v1/market/upcoming-events',
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return res.data;
};

// ── Sub-components ─────────────────────────────────────────────────────────────

// News card — category gradient banner + headline + summary
const NewsCard: React.FC<{ news: GlobalNewsItem }> = ({ news }) => {
  const theme = useTheme();
  const meta = CATEGORY_CARD_META[news.category] ?? { emoji: '📰', label: 'Finance', gradient: 'linear-gradient(135deg,#1a2a3a,#2c3e52)', chip: '#90caf9' };
  const pubMs = news.published ? new Date(news.published).getTime() : null;
  const agoMins = pubMs ? Math.floor((Date.now() - pubMs) / 60000) : null;
  const agoLabel = agoMins === null ? '' : agoMins < 60 ? `${agoMins}m ago` : agoMins < 1440 ? `${Math.floor(agoMins / 60)}h ago` : `${Math.floor(agoMins / 1440)}d ago`;

  return (
    <Paper
      component="a"
      href={news.url}
      target="_blank"
      rel="noopener noreferrer"
      elevation={2}
      sx={{
        display: 'flex', flexDirection: 'column',
        borderRadius: 3, overflow: 'hidden', textDecoration: 'none',
        background: theme.palette.mode === 'dark' ? '#0f1923' : '#fff',
        border: `1px solid ${theme.palette.divider}`,
        transition: 'transform 0.18s, box-shadow 0.18s',
        '&:hover': { transform: 'translateY(-4px)', boxShadow: 8 },
        height: '100%',
      }}
    >
      {/* Category banner — acts as the card image */}
      <Box
        sx={{
          background: meta.gradient,
          px: 2.5, py: 2,
          display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
          minHeight: 88,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Large background emoji for depth */}
        <Typography
          sx={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            fontSize: 72, lineHeight: 1, opacity: 0.15, userSelect: 'none', pointerEvents: 'none',
          }}
        >
          {meta.emoji}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, zIndex: 1 }}>
          <Typography sx={{ fontSize: 28, lineHeight: 1 }}>{meta.emoji}</Typography>
          <Box>
            <Typography sx={{ fontWeight: 800, fontSize: 13, color: '#fff', letterSpacing: 0.5, textTransform: 'uppercase' }}>
              {meta.label}
            </Typography>
            <Typography sx={{ fontSize: 11, color: 'rgba(255,255,255,0.65)', fontWeight: 500 }}>
              {news.source}
            </Typography>
          </Box>
        </Box>
        {agoLabel && (
          <Chip
            label={agoLabel}
            size="small"
            sx={{ height: 20, fontSize: 10, bgcolor: 'rgba(0,0,0,0.35)', color: 'rgba(255,255,255,0.85)', zIndex: 1, '& .MuiChip-label': { px: 1 } }}
          />
        )}
      </Box>

      {/* Card body */}
      <Box sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 700, lineHeight: 1.45, color: 'text.primary', fontSize: '0.9rem',
            display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}
        >
          {news.title}
        </Typography>
        {news.summary && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              lineHeight: 1.5, flex: 1,
              display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
            }}
          >
            {news.summary}
          </Typography>
        )}
      </Box>

      {/* Footer */}
      <Box
        sx={{
          px: 2, py: 1, borderTop: `1px solid ${theme.palette.divider}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}
      >
        <Typography variant="caption" sx={{ fontWeight: 600, color: meta.chip, fontSize: '0.68rem', letterSpacing: 0.3 }}>
          {news.source}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.68rem' }}>Read more</Typography>
          <OpenInNewIcon sx={{ fontSize: 11, color: 'text.disabled' }} />
        </Box>
      </Box>
    </Paper>
  );
};

// Compact ticker item for the scrolling strip
const TickerItem: React.FC<{ config: IndexConfig; quote: LiveQuote }> = ({ config, quote }) => {
  const changePercent = quote.changePercent ?? 0;
  const positive = changePercent >= 0;
  const changeColor = (quote.error || quote.price === null) ? 'rgba(255,255,255,0.35)' : positive ? '#4caf50' : '#f44336';
  return (
    <Box
      onClick={() => window.open(config.tradingViewUrl, '_blank', 'noopener,noreferrer')}
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 1,
        px: 2.5,
        py: 1,
        cursor: 'pointer',
        borderRight: '1px solid rgba(255,255,255,0.07)',
        '&:hover': { background: 'rgba(255,255,255,0.06)' },
        whiteSpace: 'nowrap',
        userSelect: 'none',
      }}
    >
      <Typography sx={{ fontSize: 17, lineHeight: 1 }}>{config.flag}</Typography>
      <Box>
        <Typography sx={{ fontWeight: 700, fontSize: 12, color: 'rgba(255,255,255,0.75)', letterSpacing: 0.5, lineHeight: 1 }}>
          {config.shortName}
        </Typography>
        {quote.loading ? (
          <Typography sx={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>…</Typography>
        ) : (quote.error || quote.price === null) ? (
          <Typography sx={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>N/A</Typography>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, lineHeight: 1 }}>
            <Typography sx={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 13, color: '#fff', lineHeight: 1.4 }}>
              {formatIndexPrice(quote.price, config.currency)}
            </Typography>
            <Typography sx={{ fontSize: 11, fontWeight: 700, color: changeColor, lineHeight: 1.4 }}>
              {positive ? '+' : ''}{changePercent.toFixed(2)}%
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

// Compact commodity ticker item — shows USD price + INR equivalent side by side
interface CommodityTickerItemProps {
  icon: React.ReactNode;
  label: string;
  usdPrice: number | null;
  inrPrice: number | null;
  changePercent: number | null;
  loading: boolean;
  error: boolean;
  link?: string;
  usdLabel?: string;
}
const CommodityTickerItem: React.FC<CommodityTickerItemProps> = ({
  icon, label, usdPrice, inrPrice, changePercent, loading, error, link, usdLabel = 'USD',
}) => {
  const positive = (changePercent ?? 0) >= 0;
  const changeColor = (error || usdPrice === null) ? 'rgba(255,255,255,0.35)' : positive ? '#4caf50' : '#f44336';
  const handleClick = link ? () => window.open(link, '_blank', 'noopener,noreferrer') : undefined;
  return (
    <Box
      onClick={handleClick}
      sx={{
        display: 'inline-flex', alignItems: 'center', gap: 1.5,
        px: 3, py: 1, cursor: link ? 'pointer' : 'default',
        borderRight: '1px solid rgba(255,255,255,0.07)',
        '&:hover': link ? { background: 'rgba(255,255,255,0.05)' } : {},
        whiteSpace: 'nowrap', userSelect: 'none',
      }}
    >
      {icon}
      <Box>
        <Typography sx={{ fontWeight: 700, fontSize: 12, color: 'rgba(255,255,255,0.7)', letterSpacing: 0.5, lineHeight: 1 }}>
          {label}
        </Typography>
        {loading ? (
          <Typography sx={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>…</Typography>
        ) : (error || usdPrice === null) ? (
          <Typography sx={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>N/A</Typography>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, lineHeight: 1 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
              <Typography sx={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 13, color: '#93c5fd', lineHeight: 1.2 }}>
                {formatUSD(usdPrice)} <Typography component="span" sx={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{usdLabel}</Typography>
              </Typography>
              {inrPrice !== null && (
                <Typography sx={{ fontFamily: 'monospace', fontSize: 11, color: 'rgba(255,255,255,0.55)', lineHeight: 1.2 }}>
                  {formatINR(inrPrice)}
                </Typography>
              )}
            </Box>
            <Typography sx={{ fontSize: 11, fontWeight: 700, color: changeColor }}>
              {positive ? '+' : ''}{(changePercent ?? 0).toFixed(2)}%
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

// Compact forex ticker item
const ForexTickerItem: React.FC<{ config: typeof FOREX_CONFIG[0]; quote: LiveQuote }> = ({ config, quote }) => {
  const positive = (quote.changePercent ?? 0) >= 0;
  const changeColor = (quote.error || quote.price === null) ? 'rgba(255,255,255,0.35)' : positive ? '#4caf50' : '#f44336';
  return (
    <Box
      sx={{
        display: 'inline-flex', alignItems: 'center', gap: 1,
        px: 2.5, py: 1, whiteSpace: 'nowrap', userSelect: 'none',
        borderRight: '1px solid rgba(255,255,255,0.07)',
        '&:hover': { background: 'rgba(255,255,255,0.05)' },
      }}
    >
      <Typography sx={{ fontSize: 17, lineHeight: 1 }}>{config.flag}</Typography>
      <Box>
        <Typography sx={{ fontWeight: 700, fontSize: 12, color: 'rgba(255,255,255,0.7)', letterSpacing: 0.5, lineHeight: 1 }}>
          {config.code} / INR
        </Typography>
        {quote.loading ? (
          <Typography sx={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>…</Typography>
        ) : (quote.error || quote.price === null) ? (
          <Typography sx={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>N/A</Typography>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Typography sx={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 13, color: '#93c5fd', lineHeight: 1.4 }}>
              {formatINR(quote.price, config.decimals)}
            </Typography>
            <Typography sx={{ fontSize: 11, fontWeight: 700, color: changeColor }}>
              {positive ? '+' : ''}{(quote.changePercent ?? 0).toFixed(2)}%
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

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

// SIP inflow tooltip — formats value as ₹ X,XXX cr
const SipTooltip: React.FC<{ active?: boolean; payload?: Array<{ value: number }>; label?: string }> =
  ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <Paper sx={{ p: 1, fontSize: 12 }}>
        <Typography variant="caption" sx={{ fontWeight: 700, display: 'block' }}>{label}</Typography>
        <Typography variant="caption">
          ₹ {new Intl.NumberFormat('en-IN').format(payload[0].value)} cr
        </Typography>
      </Paper>
    );
  };

// ── Market Mood Index ─────────────────────────────────────────────────────────

/** Derive an MMI-style score (0–100) from India VIX and Nifty 50 P/E. */
function computeMMI(
  vixArr: Array<{ month: string; value: number }> | null | undefined,
  peArr:  Array<{ month: string; value: number }> | null | undefined,
): number {
  const v = vixArr?.length ? vixArr[vixArr.length - 1].value : null;
  const p = peArr?.length  ? peArr[peArr.length  - 1].value  : null;

  // VIX → score (higher VIX = more fear = lower score)
  let vs = 50;
  if (v !== null) {
    if      (v >= 30) vs = Math.max(0, 8 - (v - 30));
    else if (v >= 25) vs = 8  + (30 - v) * 2;
    else if (v >= 20) vs = 18 + (25 - v) * 2.4;
    else if (v >= 17) vs = 30 + (20 - v) * 3.3;
    else if (v >= 14) vs = 40 + (17 - v) * 7;
    else if (v >= 11) vs = 61 + (14 - v) * 6.3;
    else              vs = Math.min(100, 80 + (11 - v) * 10);
  }

  // P/E → score (higher PE = more greed = higher score)
  let ps = 50;
  if (p !== null) {
    if      (p <= 15) ps = Math.max(0, p * 1.5);
    else if (p <= 18) ps = 15 + (p - 15) * 5;
    else if (p <= 21) ps = 30 + (p - 18) * 5;
    else if (p <= 24) ps = 45 + (p - 21) * 5;
    else if (p <= 28) ps = 60 + (p - 24) * 5;
    else              ps = Math.min(100, 80 + (p - 28) * 5);
  }

  return Math.round(0.6 * vs + 0.4 * ps);
}

// ── Shared zone type ─────────────────────────────────────────────────────────
type ZoneConfig = { limit: number; color: string; label: string; desc: string };

const MMI_ZONES: ZoneConfig[] = [
  { limit: 30,  color: '#1b5e20', label: 'Extreme Fear',  desc: 'Market deeply oversold — investors fearful'    },
  { limit: 50,  color: '#e65100', label: 'Fear',          desc: 'Bearish sentiment below neutral'               },
  { limit: 70,  color: '#b71c1c', label: 'Greed',         desc: 'Positive sentiment — some overconfidence'      },
  { limit: 100, color: '#7b003c', label: 'Extreme Greed', desc: 'Market overbought — investors exuberant'       },
];

const BTC_FNG_ZONES: ZoneConfig[] = [
  { limit: 25,  color: '#1b5e20', label: 'Extreme Fear',  desc: 'Panic selling — historically a buy signal'     },
  { limit: 45,  color: '#e65100', label: 'Fear',          desc: 'Bearish sentiment — investors cautious'        },
  { limit: 55,  color: '#f57f17', label: 'Neutral',       desc: 'Balanced market sentiment'                     },
  { limit: 75,  color: '#b71c1c', label: 'Greed',         desc: 'Bullish momentum — FOMO building'              },
  { limit: 100, color: '#7b003c', label: 'Extreme Greed', desc: 'Market overbought — correction risk elevated'  },
];

function zoneFor(value: number, zones: ZoneConfig[]): ZoneConfig {
  return zones.find((z) => value < z.limit) ?? zones[zones.length - 1];
}

// ── Generic SentimentGauge ────────────────────────────────────────────────────
const SentimentGauge: React.FC<{
  value: number;
  zones: ZoneConfig[];
  unavailable: boolean;
  sourceChip: React.ReactNode;
  extraChips?: React.ReactNode;
}> = ({ value, zones, unavailable, sourceChip, extraChips }) => {
  const theme  = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const greyMid  = isDark ? '#555' : '#bdbdbd';
  const greyDark = isDark ? '#444' : '#9e9e9e';

  const clamped  = unavailable ? 50 : Math.max(0, Math.min(100, value));
  const zone     = zoneFor(clamped, zones);
  const valColor = unavailable ? greyMid : zone.color;

  const subArcs = zones.map((z) => ({ limit: z.limit, color: z.color, showTick: false }));
  const tickValues = zones.length === 4
    ? [{ v: 15, lbl: 'Ext. Fear', col: '#2e7d32' }, { v: 40, lbl: 'Fear', col: '#e65100' },
       { v: 60, lbl: 'Greed', col: '#b71c1c' },     { v: 85, lbl: 'Ext. Greed', col: '#7b003c' }]
    : [{ v: 12, lbl: 'Ext. Fear', col: '#2e7d32' }, { v: 35, lbl: 'Fear', col: '#e65100' },
       { v: 50, lbl: 'Neutral', col: '#f57f17' },   { v: 65, lbl: 'Greed', col: '#b71c1c' },
       { v: 88, lbl: 'Ext. Greed', col: '#7b003c' }];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5, width: '100%' }}>
      <Box sx={{ position: 'relative', width: '100%' }}>
        <GaugeComponent
          key={unavailable ? 'unavailable' : Math.round(clamped)}
          value={clamped}
          minValue={0} maxValue={100}
          type="semicircle"
          arc={{
            width: 0.25, padding: 0.02, cornerRadius: 2,
            subArcs: unavailable ? [{ limit: 100, color: greyDark, showTick: false }] : subArcs,
          }}
          pointer={{ color: valColor, length: 0.75, width: 10, elastic: false }}
          labels={{
            valueLabel: { formatTextValue: () => '', style: { fontSize: '0px', display: 'none' } },
            tickLabels: {
              type: 'outer',
              hideMinMax: true,
              ticks: unavailable ? [] : tickValues.map((t) => ({
                value: t.v,
                valueConfig: { formatTextValue: () => t.lbl, style: { fontSize: '8px', fill: t.col } },
              })),
            },
          }}
          style={{ width: '100%', opacity: unavailable ? 0.4 : 1 }}
        />
        {unavailable && (
          <Box sx={{
            position: 'absolute', top: '28%', left: 0, right: 0,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5,
          }}>
            <Typography sx={{ fontSize: 24, lineHeight: 1 }}>📡</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600, color: greyMid, textAlign: 'center', px: 1 }}>
              Data unavailable
            </Typography>
          </Box>
        )}
      </Box>

      {!unavailable && (
        <>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: -1 }}>
            <Typography sx={{ fontWeight: 900, fontSize: '2.4rem', lineHeight: 1, color: valColor }}>
              {clamped.toFixed(1)}
            </Typography>
            <Typography sx={{ fontWeight: 800, fontSize: '0.85rem', letterSpacing: 1.2,
              textTransform: 'uppercase', color: valColor }}>
              {zone.label}
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', px: 1 }}>
            {zone.desc}
          </Typography>
        </>
      )}

      <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap', justifyContent: 'center' }}>
        {unavailable
          ? <Chip size="small" label="Unavailable — retry later"
              sx={{ fontSize: 10, bgcolor: isDark ? '#1e1e1e' : '#f5f5f5',
                color: greyMid, border: `1px solid ${greyDark}44` }} />
          : <>{sourceChip}{extraChips}</>}
      </Stack>
    </Box>
  );
};

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
  const [, setLastRefreshBtc] = useState<Date | null>(null);

  const [macroData, setMacroData] = useState<MacroData>({
    rbi_repo_rate: null,
    india_cpi: null,
    india_gdp_growth: null,
    us_cpi: null,
    us_unemployment: null,
    us_fed_rate: null,
    us_10y_yield: null,
    nifty_pe: null,
    india_vix: null,
    fii_equity_flow: null,
    dii_equity_flow: null,
    india_sip_inflow: null,
  });

  const [referenceRates, setReferenceRates] = useState<ReferenceRatesData>({
    bank_fd: [],
    govt_schemes: [],
  });

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

  useEffect(() => {
    fetchMacroIndicators().then((data) => {
      setMacroData((prev) => ({
        rbi_repo_rate:    data.rbi_repo_rate?.length  ? data.rbi_repo_rate    : prev.rbi_repo_rate,
        india_cpi:        data.india_cpi?.length      ? data.india_cpi        : prev.india_cpi,
        india_gdp_growth: data.india_gdp_growth       ? data.india_gdp_growth : prev.india_gdp_growth,
        us_cpi:           data.us_cpi                 ? data.us_cpi           : prev.us_cpi,
        us_unemployment:  data.us_unemployment        ? data.us_unemployment  : prev.us_unemployment,
        us_fed_rate:      data.us_fed_rate            ? data.us_fed_rate      : prev.us_fed_rate,
        us_10y_yield:     data.us_10y_yield           ? data.us_10y_yield     : prev.us_10y_yield,
        nifty_pe:         data.nifty_pe               ? data.nifty_pe         : prev.nifty_pe,
        india_vix:        data.india_vix              ? data.india_vix        : prev.india_vix,
        fii_equity_flow:  data.fii_equity_flow        ? data.fii_equity_flow  : prev.fii_equity_flow,
        dii_equity_flow:  data.dii_equity_flow        ? data.dii_equity_flow  : prev.dii_equity_flow,
        india_sip_inflow: data.india_sip_inflow       ? data.india_sip_inflow : prev.india_sip_inflow,
      }));
    }).catch(() => { /* keep DB-loaded data on API error */ });
  }, []);

  useEffect(() => {
    fetchReferenceRates().then((data) => {
      if (data.bank_fd?.length || data.govt_schemes?.length) setReferenceRates(data);
    }).catch(() => { /* keep seeded fallback */ });
  }, []);

  const [upcomingEvents, setUpcomingEvents] = useState<UpcomingEventsData>({ calendar_events: [], global_news: [], market_holidays: [] });
  useEffect(() => {
    fetchUpcomingEvents().then(setUpcomingEvents).catch(() => { /* silently ignore */ });
  }, []);

  type SentimentData = { value: number | null; sentiment: string | null; source: string };
  const [mmiData, setMmiData] = useState<SentimentData>({ value: null, sentiment: null, source: 'loading' });
  useEffect(() => {
    fetchMMI().then(setMmiData).catch(() => setMmiData({ value: null, sentiment: null, source: 'error' }));
  }, []);

  const [btcFngData, setBtcFngData] = useState<SentimentData>({ value: null, sentiment: null, source: 'loading' });
  useEffect(() => {
    fetchBtcFng().then(setBtcFngData).catch(() => setBtcFngData({ value: null, sentiment: null, source: 'error' }));
  }, []);

  const [usFngData, setUsFngData] = useState<SentimentData>({ value: null, sentiment: null, source: 'loading' });
  useEffect(() => {
    fetchUsFng().then(setUsFngData).catch(() => setUsFngData({ value: null, sentiment: null, source: 'error' }));
  }, []);

  const [calendarOffset, setCalendarOffset] = useState(0);

  const btc = quotes['btc'];

  // Derived from live macro data
  const latestRbi = macroData.rbi_repo_rate?.[macroData.rbi_repo_rate.length - 1] ?? null;
  const rbiRate    = latestRbi?.rate ?? null;
  const rbiDate    = latestRbi?.date ?? '';
  const sdfRate    = rbiRate != null ? (rbiRate - 0.25).toFixed(2) + '%' : '—';
  const msfRate    = rbiRate != null ? (rbiRate + 0.25).toFixed(2) + '%' : '—';
  const chartRange = (data: Array<{ month: string }> | null) =>
    data?.length ? `${data[0].month} – ${data[data.length - 1].month}` : '';

  // Pad monthly chart data with null entries up to the current month so the
  // X-axis always extends to today even when the source data lags.
  const _ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const _parseMonthLabel = (lbl: string): { y: number; m: number } | null => {
    const match = lbl.match(/^([A-Za-z]{3})'(\d{2})$/);
    if (!match) return null;
    const m = _ABBR.indexOf(match[1]) + 1;
    return m > 0 ? { y: 2000 + parseInt(match[2]), m } : null;
  };
  const _monthLabel = (y: number, m: number) => `${_ABBR[m - 1]}'${String(y).slice(2)}`;
  const padToCurrentMonth = (
    data: Array<{ month: string; value: number }> | null | undefined
  ): Array<{ month: string; value: number | null }> => {
    if (!data?.length) return data ?? [];
    const now = new Date();
    const cy = now.getFullYear(), cm = now.getMonth() + 1;
    const last = _parseMonthLabel(data[data.length - 1].month);
    if (!last) return data;
    const result: Array<{ month: string; value: number | null }> = [...data];
    let { y, m } = last;
    while (y < cy || (y === cy && m < cm)) {
      m++; if (m > 12) { m = 1; y++; }
      result.push({ month: _monthLabel(y, m), value: null });
    }
    return result;
  };

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 } }}>

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

      {/* ── Section 1: Global Market Indices Ticker ─────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          mb: 2.5,
          background: 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)',
          border: `1px solid rgba(255,255,255,0.08)`,
          overflow: 'hidden',
        }}
      >
        {/* Header row */}
        <Box sx={{ display: 'flex', alignItems: 'center', px: 2.5, pt: 1.25, pb: 1, gap: 1 }}>
          <Typography sx={{ fontSize: 18, lineHeight: 1 }}>🌐</Typography>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#fff', letterSpacing: -0.2 }}>
            Global Market Indices
          </Typography>
          <Chip
            label="Click any index for live chart"
            size="small"
            sx={{ ml: 'auto', fontSize: 10, height: 20, color: 'rgba(255,255,255,0.55)', borderColor: 'rgba(255,255,255,0.18)', bgcolor: 'transparent' }}
            variant="outlined"
          />
        </Box>

        {/* Ticker strip */}
        <Box
          sx={{
            position: 'relative',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            /* Pause animation on hover */
            '&:hover .ticker-track': { animationPlayState: 'paused' },
          }}
        >
          {/* Left fade */}
          <Box sx={{
            position: 'absolute', left: 0, top: 0, bottom: 0, width: 48, zIndex: 2,
            background: 'linear-gradient(to right, #0d1b2a 30%, transparent)',
            pointerEvents: 'none',
          }} />
          {/* Right fade */}
          <Box sx={{
            position: 'absolute', right: 0, top: 0, bottom: 0, width: 48, zIndex: 2,
            background: 'linear-gradient(to left, #1b2838 30%, transparent)',
            pointerEvents: 'none',
          }} />

          <Box sx={{ overflow: 'hidden' }}>
            <Box
              className="ticker-track"
              sx={{
                display: 'flex',
                width: 'max-content',
                '@keyframes tickerScroll': {
                  from: { transform: 'translateX(0)' },
                  to:   { transform: 'translateX(-50%)' },
                },
                animation: 'tickerScroll 70s linear infinite',
              }}
            >
              {/* Duplicate for seamless loop */}
              {[...WORLD_INDICES, ...WORLD_INDICES].map((idx, i) => (
                <TickerItem key={`${idx.id}-${i}`} config={idx} quote={quotes[idx.id]} />
              ))}
            </Box>
          </Box>
        </Box>
      </Paper>

      {/* ── Section 2: Commodity Prices Ticker ───────────────────────────── */}
      {(() => {
        const usdInr = quotes['usdinr']?.price ?? null;
        const usdInrLoading = quotes['usdinr']?.loading ?? true;
        const commodityItems = [
          {
            key: 'gold', icon: <Typography sx={{ fontSize: 22, lineHeight: 1 }}>🥇</Typography>,
            label: 'Gold', link: COMMODITY_CONFIG['gold'].link,
            q: quotes['gold'],
            inrPrice: (!usdInrLoading && usdInr && quotes['gold']?.price)
              ? INDIA_COMMODITY_CONFIG['gold'].convert(quotes['gold'].price!, usdInr) : null,
          },
          {
            key: 'silver', icon: <Typography sx={{ fontSize: 22, lineHeight: 1 }}>🥈</Typography>,
            label: 'Silver', link: COMMODITY_CONFIG['silver'].link,
            q: quotes['silver'],
            inrPrice: (!usdInrLoading && usdInr && quotes['silver']?.price)
              ? INDIA_COMMODITY_CONFIG['silver'].convert(quotes['silver'].price!, usdInr) : null,
          },
          {
            key: 'brent', icon: <Typography sx={{ fontSize: 22, lineHeight: 1 }}>🛢️</Typography>,
            label: 'Brent Crude', link: COMMODITY_CONFIG['brent'].link,
            q: quotes['brent'],
            inrPrice: (!usdInrLoading && usdInr && quotes['brent']?.price)
              ? INDIA_COMMODITY_CONFIG['brent'].convert(quotes['brent'].price!, usdInr) : null,
          },
          {
            key: 'btc', icon: <BitcoinIcon sx={{ fontSize: 22, color: '#f97316' }} />,
            label: 'Bitcoin', link: undefined,
            q: btc,
            inrPrice: (!usdInrLoading && usdInr && btc.price)
              ? INDIA_COMMODITY_CONFIG['btc'].convert(btc.price, usdInr) : null,
          },
        ];
        return (
          <Paper
            elevation={0}
            sx={{
              borderRadius: 3,
              mb: 2.5,
              background: 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)',
              border: '1px solid rgba(255,255,255,0.08)',
              overflow: 'hidden',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', px: 2.5, pt: 1.25, pb: 1, gap: 1 }}>
              <Typography sx={{ fontSize: 18, lineHeight: 1 }}>📦</Typography>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#fff', letterSpacing: -0.2 }}>
                Commodity Prices
              </Typography>
              <Chip
                label="USD · INR"
                size="small"
                sx={{ ml: 'auto', fontSize: 10, height: 20, color: 'rgba(255,255,255,0.55)', borderColor: 'rgba(255,255,255,0.18)', bgcolor: 'transparent' }}
                variant="outlined"
              />
            </Box>
            <Box
              sx={{
                position: 'relative',
                borderTop: '1px solid rgba(255,255,255,0.06)',
                '&:hover .commodity-ticker-track': { animationPlayState: 'paused' },
              }}
            >
              <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 48, zIndex: 2, background: 'linear-gradient(to right, #0d1b2a 30%, transparent)', pointerEvents: 'none' }} />
              <Box sx={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 48, zIndex: 2, background: 'linear-gradient(to left, #1b2838 30%, transparent)', pointerEvents: 'none' }} />
              <Box sx={{ overflow: 'hidden' }}>
                <Box
                  className="commodity-ticker-track"
                  sx={{
                    display: 'flex', width: 'max-content',
                    '@keyframes commodityTickerScroll': {
                      from: { transform: 'translateX(0)' },
                      to:   { transform: 'translateX(-25%)' },
                    },
                    animation: 'commodityTickerScroll 50s linear infinite',
                  }}
                >
                  {[...commodityItems, ...commodityItems, ...commodityItems, ...commodityItems].map((item, i) => (
                    <CommodityTickerItem
                      key={`${item.key}-${i}`}
                      icon={item.icon}
                      label={item.label}
                      usdPrice={item.q?.price ?? null}
                      inrPrice={item.inrPrice}
                      changePercent={item.q?.changePercent ?? null}
                      loading={item.q?.loading ?? true}
                      error={item.q?.error ?? false}
                      link={item.link}
                    />
                  ))}
                </Box>
              </Box>
            </Box>
          </Paper>
        );
      })()}

      {/* ── Section 2c: Currency Conversion Rates Ticker ────────────────── */}
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          mb: 2.5,
          background: 'linear-gradient(135deg,#0d1b2a 0%,#1b2838 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', px: 2.5, pt: 1.25, pb: 1, gap: 1 }}>
          <Typography sx={{ fontSize: 18, lineHeight: 1 }}>💱</Typography>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#fff', letterSpacing: -0.2 }}>
            Currency Rates to INR
          </Typography>
          <Chip
            label="1 unit → INR"
            size="small"
            sx={{ ml: 'auto', fontSize: 10, height: 20, color: 'rgba(255,255,255,0.55)', borderColor: 'rgba(255,255,255,0.18)', bgcolor: 'transparent' }}
            variant="outlined"
          />
        </Box>
        <Box
          sx={{
            position: 'relative',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            '&:hover .forex-ticker-track': { animationPlayState: 'paused' },
          }}
        >
          <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 48, zIndex: 2, background: 'linear-gradient(to right, #0d1b2a 30%, transparent)', pointerEvents: 'none' }} />
          <Box sx={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 48, zIndex: 2, background: 'linear-gradient(to left, #1b2838 30%, transparent)', pointerEvents: 'none' }} />
          <Box sx={{ overflow: 'hidden' }}>
            <Box
              className="forex-ticker-track"
              sx={{
                display: 'flex', width: 'max-content',
                '@keyframes forexTickerScroll': {
                  from: { transform: 'translateX(0)' },
                  to:   { transform: 'translateX(-50%)' },
                },
                animation: 'forexTickerScroll 55s linear infinite',
              }}
            >
              {[...FOREX_CONFIG, ...FOREX_CONFIG].map((fx, i) => (
                <ForexTickerItem key={`${fx.id}-${i}`} config={fx} quote={quotes[fx.id]} />
              ))}
            </Box>
          </Box>
        </Box>
      </Paper>

      {/* ── Top Financial News ───────────────────────────────────────────── */}
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
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2.5, gap: 1 }}>
          <Typography sx={{ fontSize: 22 }}>📰</Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Top Financial News</Typography>
          <Chip label="Live · RSS" size="small" variant="outlined" sx={{ fontSize: 11 }} />
        </Box>
        {upcomingEvents.global_news.length === 0 ? (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">Loading news…</Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' }, gap: 2 }}>
            {upcomingEvents.global_news.map((news, i) => (
              <NewsCard key={i} news={news} />
            ))}
          </Box>
        )}
      </Paper>

      {/* ── Section 2d: India Market Mood Index ─────────────────────────── */}
      {(() => {
        const vixArr      = macroData.india_vix;
        const peArr       = macroData.nifty_pe;
        const latestVix   = vixArr?.length ? vixArr[vixArr.length - 1] : null;
        const latestPe    = peArr?.length  ? peArr[peArr.length  - 1]  : null;
        const isUnavail   = mmiData.source === 'error' || mmiData.source === 'loading';
        const isLive      = !isUnavail && mmiData.value !== null;
        const mmiValue    = isLive ? mmiData.value! : computeMMI(vixArr, peArr);

        // BTC Fear & Greed
        const isBtcUnavail = btcFngData.source === 'error' || btcFngData.source === 'loading';
        const btcValue     = btcFngData.value ?? 50;

        // US Fear & Greed
        const isUsUnavail  = usFngData.source === 'error' || usFngData.source === 'loading';
        const usValue      = usFngData.value ?? 50;

        const isDark = theme.palette.mode === 'dark';

        // Source chips
        const mmiSourceChip = isLive
          ? <Chip size="small" label="Tickertape"
              sx={{ fontSize: 10, bgcolor: isDark ? '#0a180d' : '#e8f5e9', color: '#2e7d32', border: '1px solid #2e7d3233' }} />
          : <Chip size="small" label="Estimated (VIX + P/E)"
              sx={{ fontSize: 10, bgcolor: isDark ? '#1a1200' : '#fffde7', color: '#f57f17', border: '1px solid #f57f1733' }} />;

        const mmiExtraChips = !isLive && !isUnavail ? (
          <>
            {latestVix && <Chip size="small" label={`VIX ${latestVix.value.toFixed(1)}`}
              sx={{ fontSize: 10, bgcolor: isDark ? '#0a180d' : '#e8f5e9', color: '#2e7d32', border: '1px solid #2e7d3233' }} />}
            {latestPe && <Chip size="small" label={`P/E ${latestPe.value.toFixed(1)}×`}
              sx={{ fontSize: 10, bgcolor: isDark ? '#190c00' : '#fff3e0', color: '#e65100', border: '1px solid #e6510033' }} />}
          </>
        ) : undefined;

        const btcSourceLabel = btcFngData.source === 'coinmarketcap' ? 'CoinMarketCap' : 'Alternative.me';
        const btcSourceChip = <Chip size="small"
          label={isBtcUnavail ? 'Unavailable' : btcSourceLabel}
          sx={{ fontSize: 10, bgcolor: isDark ? '#100520' : '#f3e8ff', color: '#7b1fa2', border: '1px solid #7b1fa233' }} />;

        const usSourceChip = <Chip size="small"
          label={isUsUnavail ? 'Unavailable' : 'CNN'}
          sx={{ fontSize: 10, bgcolor: isDark ? '#0a0f1f' : '#e8eaf6', color: '#1a237e', border: '1px solid #1a237e33' }} />;

        return (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr' }, gap: 2, mb: 2.5 }}>

            {/* India MMI card */}
            <Paper elevation={0} sx={{
              p: { xs: 2, sm: 3 }, borderRadius: 3,
              background: isDark
                ? 'linear-gradient(135deg,#080f18 0%,#0c1622 100%)'
                : 'linear-gradient(135deg,#f0f7f0 0%,#f8f9fc 100%)',
              border: `1px solid ${theme.palette.divider}`,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5, gap: 1 }}>
                <Typography sx={{ fontSize: 20, lineHeight: 1.2 }}>🌡️</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>India Market Mood Index</Typography>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, textAlign: 'center' }}>
                {isLive ? 'Live from Tickertape' : 'Derived from VIX & Nifty P/E'} · 0 = Extreme Fear · 100 = Extreme Greed
              </Typography>
              <SentimentGauge
                value={mmiValue}
                zones={MMI_ZONES}
                unavailable={isUnavail}
                sourceChip={mmiSourceChip}
                extraChips={mmiExtraChips}
              />
            </Paper>

            {/* BTC Fear & Greed card */}
            <Paper elevation={0} sx={{
              p: { xs: 2, sm: 3 }, borderRadius: 3,
              background: isDark
                ? 'linear-gradient(135deg,#100520 0%,#0c0818 100%)'
                : 'linear-gradient(135deg,#f3e8ff 0%,#faf5ff 100%)',
              border: `1px solid ${theme.palette.divider}`,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5, gap: 1 }}>
                <Typography sx={{ fontSize: 20, lineHeight: 1.2 }}>₿</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Bitcoin Fear & Greed Index</Typography>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, textAlign: 'center' }}>
                Live from {btcSourceLabel} · 0 = Extreme Fear · 100 = Extreme Greed
              </Typography>
              <SentimentGauge
                value={btcValue}
                zones={BTC_FNG_ZONES}
                unavailable={isBtcUnavail}
                sourceChip={btcSourceChip}
              />
            </Paper>

            {/* US Fear & Greed card */}
            <Paper elevation={0} sx={{
              p: { xs: 2, sm: 3 }, borderRadius: 3,
              background: isDark
                ? 'linear-gradient(135deg,#000d1f 0%,#001533 100%)'
                : 'linear-gradient(135deg,#e8eaf6 0%,#f5f5ff 100%)',
              border: `1px solid ${theme.palette.divider}`,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5, gap: 1 }}>
                <Typography sx={{ fontSize: 20, lineHeight: 1.2 }}>🦅</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>US Fear & Greed Index</Typography>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, textAlign: 'center' }}>
                Live from CNN · 0 = Extreme Fear · 100 = Extreme Greed
              </Typography>
              <SentimentGauge
                value={usValue}
                zones={BTC_FNG_ZONES}
                unavailable={isUsUnavail}
                sourceChip={usSourceChip}
              />
            </Paper>

          </Box>
        );
      })()}

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
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2 }}>

        {/* India CPI */}
        {macroData.india_cpi?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#1a0a00,#2a1100)' : 'linear-gradient(145deg,#fff8f4,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#ff6b35,#f7c59f)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇮🇳</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India CPI Inflation</Typography>
              <Typography variant="caption" color="text.secondary">YoY % · {chartRange(macroData.india_cpi)}</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={padToCurrentMonth(macroData.india_cpi)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradIndia" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff6b35" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#ff6b35" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <ReferenceLine y={4} stroke="#4caf50" strokeDasharray="4 2" label={{ value: '4% target', fontSize: 9, fill: '#4caf50' }} />
              <Area type="monotone" dataKey="value" stroke="#ff6b35" fill="url(#gradIndia)" strokeWidth={2.5} dot={false} />
              <Brush dataKey="month" height={24} stroke="#ff6b35" fill={theme.palette.mode === 'dark' ? '#1a0a00' : '#fff3ee'} travellerWidth={6} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: MoSPI / World Bank</Typography>
        </Paper>
        ) : null}

        {/* India GDP */}
        {macroData.india_gdp_growth?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#000d1a,#001a33)' : 'linear-gradient(145deg,#f0f6ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#0052cc,#4c9aff)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>📈</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India GDP Growth</Typography>
              <Typography variant="caption" color="text.secondary">Annual Real GDP % · {chartRange(macroData.india_gdp_growth)}</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={macroData.india_gdp_growth} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <ReferenceLine y={0} stroke={theme.palette.divider} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {macroData.india_gdp_growth.map((entry, i) => (
                  <Cell key={i} fill={entry.value < 0 ? '#f44336' : '#2196f3'} />
                ))}
              </Bar>
              <Brush dataKey="month" height={24} stroke="#2196f3" fill={theme.palette.mode === 'dark' ? '#000d1a' : '#f0f6ff'} travellerWidth={6} />
            </BarChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSO / World Bank</Typography>
        </Paper>
        ) : null}

        {/* India SIP Net Inflows */}
        {(() => {
          const sipData = macroData.india_sip_inflow;
          if (!sipData?.length) return null;
          const sipLatest = sipData[sipData.length - 1];
          const sipPadded = padToCurrentMonth(sipData);
          const isDark = theme.palette.mode === 'dark';
          return (
            <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: isDark ? 'linear-gradient(145deg,#001a0d,#002e1a)' : 'linear-gradient(145deg,#f0fdf6,#fff)' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#00695c,#26a69a)', mr: 0.5 }}>
                  <Typography sx={{ fontSize: 16 }}>🇮🇳</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India SIP Net Inflows</Typography>
                  <Typography variant="caption" color="text.secondary">Monthly · ₹ Crore · {sipData[0].month} – {sipLatest.month}</Typography>
                </Box>
                <Chip label={`Latest ₹ ${new Intl.NumberFormat('en-IN').format(sipLatest.value)} cr`} size="small" sx={{ ml: 'auto', fontSize: 10, bgcolor: isDark ? '#002e1a' : '#e8f5e9', color: '#2e7d32', border: '1px solid #2e7d3233' }} />
              </Box>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={sipPadded} margin={{ top: 4, right: 8, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 9 }} interval={3} />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  />
                  <RechartTooltip content={<SipTooltip />} />
                  <ReferenceLine y={20000} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '₹20k cr', fontSize: 9, fill: '#f59e0b', position: 'insideTopRight' }} />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {sipData.map((entry, i) => (
                      <Cell key={i} fill={entry.value >= 25000 ? '#00897b' : entry.value >= 20000 ? '#26a69a' : '#4db6ac'} />
                    ))}
                  </Bar>
                  <Brush dataKey="month" height={24} stroke="#26a69a" fill={theme.palette.mode === 'dark' ? '#001a0d' : '#f0fdf6'} travellerWidth={6} />
                </BarChart>
              </ResponsiveContainer>
              <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: AMFI</Typography>
            </Paper>
          );
        })()}

        {/* FII Net Equity Flows */}
        {(() => {
          const fiiData = macroData.fii_equity_flow;
          if (!fiiData?.length) return null;
          const fiiLatest = fiiData[fiiData.length - 1];
          const fiiPadded = padToCurrentMonth(fiiData);
          const isDark = theme.palette.mode === 'dark';
          return (
            <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: isDark ? 'linear-gradient(145deg,#0d0020,#1a0040)' : 'linear-gradient(145deg,#f3f0ff,#fff)' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#4a148c,#7b1fa2)', mr: 0.5 }}>
                  <Typography sx={{ fontSize: 16 }}>🌐</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>FII Net Equity Flows</Typography>
                  <Typography variant="caption" color="text.secondary">Foreign Institutional Investors · Monthly · ₹ Crore · {fiiData[0].month} – {fiiLatest.month}</Typography>
                </Box>
                <Chip
                  label={`Latest ${fiiLatest.value >= 0 ? '+' : ''}₹ ${new Intl.NumberFormat('en-IN').format(fiiLatest.value)} cr`}
                  size="small"
                  sx={{ ml: 'auto', fontSize: 10, bgcolor: isDark ? (fiiLatest.value >= 0 ? '#0a180d' : '#1a0000') : (fiiLatest.value >= 0 ? '#e8f5e9' : '#ffebee'), color: fiiLatest.value >= 0 ? '#2e7d32' : '#c62828', border: `1px solid ${fiiLatest.value >= 0 ? '#2e7d3233' : '#c6282833'}` }}
                />
              </Box>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={fiiPadded} margin={{ top: 4, right: 8, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 9 }} interval={3} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <RechartTooltip content={<SipTooltip />} />
                  <ReferenceLine y={0} stroke={theme.palette.divider} strokeWidth={1.5} />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {fiiPadded.map((entry, i) => (
                      <Cell key={i} fill={(entry.value ?? 0) >= 0 ? '#7b1fa2' : '#d32f2f'} />
                    ))}
                  </Bar>
                  <Brush dataKey="month" height={24} stroke="#7b1fa2" fill={theme.palette.mode === 'dark' ? '#0d0020' : '#f3f0ff'} travellerWidth={6} />
                </BarChart>
              </ResponsiveContainer>
              <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSE · Equity segment · Live via daily refresh</Typography>
            </Paper>
          );
        })()}

        {/* DII Net Equity Flows */}
        {(() => {
          const diiData = macroData.dii_equity_flow;
          if (!diiData?.length) return null;
          const diiLatest = diiData[diiData.length - 1];
          const diiPadded = padToCurrentMonth(diiData);
          const isDark = theme.palette.mode === 'dark';
          return (
            <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: isDark ? 'linear-gradient(145deg,#001433,#002766)' : 'linear-gradient(145deg,#e8f0ff,#fff)' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#003087,#1565c0)', mr: 0.5 }}>
                  <Typography sx={{ fontSize: 16 }}>🇮🇳</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>DII Net Equity Flows</Typography>
                  <Typography variant="caption" color="text.secondary">Domestic Institutional Investors · Monthly · ₹ Crore · {diiData[0].month} – {diiLatest.month}</Typography>
                </Box>
                <Chip
                  label={`Latest ${diiLatest.value >= 0 ? '+' : ''}₹ ${new Intl.NumberFormat('en-IN').format(diiLatest.value)} cr`}
                  size="small"
                  sx={{ ml: 'auto', fontSize: 10, bgcolor: isDark ? (diiLatest.value >= 0 ? '#001433' : '#1a0000') : (diiLatest.value >= 0 ? '#e8f0ff' : '#ffebee'), color: diiLatest.value >= 0 ? '#1565c0' : '#c62828', border: `1px solid ${diiLatest.value >= 0 ? '#1565c033' : '#c6282833'}` }}
                />
              </Box>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={diiPadded} margin={{ top: 4, right: 8, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 9 }} interval={3} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <RechartTooltip content={<SipTooltip />} />
                  <ReferenceLine y={0} stroke={theme.palette.divider} strokeWidth={1.5} />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {diiPadded.map((entry, i) => (
                      <Cell key={i} fill={(entry.value ?? 0) >= 0 ? '#1565c0' : '#d32f2f'} />
                    ))}
                  </Bar>
                  <Brush dataKey="month" height={24} stroke="#1565c0" fill={theme.palette.mode === 'dark' ? '#001433' : '#e8f0ff'} travellerWidth={6} />
                </BarChart>
              </ResponsiveContainer>
              <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSE · Equity segment · Live via daily refresh</Typography>
            </Paper>
          );
        })()}

        {/* Nifty 50 P/E Ratio */}
        {macroData.nifty_pe?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#1a0a00,#331500)' : 'linear-gradient(145deg,#fff8f0,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#e65100,#ff8f00)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇮🇳</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Nifty 50 P/E Ratio</Typography>
              <Typography variant="caption" color="text.secondary">Price-to-Earnings · {chartRange(macroData.nifty_pe)} · Live via NSE</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={padToCurrentMonth(macroData.nifty_pe)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <RechartTooltip content={<ChartTip unit="x" />} />
              <ReferenceLine y={20} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '20x avg', fontSize: 9, fill: '#f59e0b' }} />
              <Line type="monotone" dataKey="value" stroke="#f97316" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: '#f97316', strokeWidth: 0 }} />
              <Brush dataKey="month" height={24} stroke="#f97316" fill={theme.palette.mode === 'dark' ? '#1a0a00' : '#fff8f0'} travellerWidth={6} />
            </LineChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSE India</Typography>
        </Paper>
        ) : null}

        {/* India VIX */}
        {macroData.india_vix?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#15001a,#2a0035)' : 'linear-gradient(145deg,#fdf4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#4a0072,#9c27b0)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>📉</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India VIX</Typography>
              <Typography variant="caption" color="text.secondary">Fear Index · {chartRange(macroData.india_vix)} · Live via NSE</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={padToCurrentMonth(macroData.india_vix)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradVix" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#9c27b0" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#9c27b0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <RechartTooltip content={<ChartTip unit="" />} />
              <ReferenceLine y={20} stroke="#ef5350" strokeDasharray="4 2" label={{ value: 'High fear', fontSize: 9, fill: '#ef5350' }} />
              <Area type="monotone" dataKey="value" stroke="#9c27b0" fill="url(#gradVix)" strokeWidth={2.5} dot={false} />
              <Brush dataKey="month" height={24} stroke="#9c27b0" fill={theme.palette.mode === 'dark' ? '#15001a' : '#fdf4ff'} travellerWidth={6} startIndex={Math.max(0, (macroData.india_vix?.length ?? 0) - 60)} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSE India / Yahoo Finance</Typography>
        </Paper>
        ) : null}

        {/* US CPI */}
        {macroData.us_cpi?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#0d0020,#1a0040)' : 'linear-gradient(145deg,#f8f4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#7c4dff,#b47cff)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇺🇸</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US CPI Inflation</Typography>
              <Typography variant="caption" color="text.secondary">YoY % · {chartRange(macroData.us_cpi)} · Live via BLS</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={310}>
            <AreaChart data={padToCurrentMonth(macroData.us_cpi)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradUS" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7c4dff" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#7c4dff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <ReferenceLine y={2} stroke="#4caf50" strokeDasharray="4 2" label={{ value: '2% target', fontSize: 9, fill: '#4caf50' }} />
              <Area type="monotone" dataKey="value" stroke="#7c4dff" fill="url(#gradUS)" strokeWidth={2.5} dot={false} />
              <Brush dataKey="month" height={24} stroke="#7c4dff" fill={theme.palette.mode === 'dark' ? '#0d0020' : '#f8f4ff'} travellerWidth={6} startIndex={Math.max(0, (macroData.us_cpi?.length ?? 0) - 60)} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: BLS</Typography>
        </Paper>
        ) : null}

        {/* US Unemployment */}
        {macroData.us_unemployment?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#001a1a,#003333)' : 'linear-gradient(145deg,#f0ffff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#006064,#26c6da)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>👷</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US Unemployment Rate</Typography>
              <Typography variant="caption" color="text.secondary">Seasonally Adjusted % · {chartRange(macroData.us_unemployment)} · Live via BLS</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={310}>
            <LineChart data={padToCurrentMonth(macroData.us_unemployment)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Line type="monotone" dataKey="value" stroke="#00bcd4" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: '#00bcd4', strokeWidth: 0 }} />
              <Brush dataKey="month" height={24} stroke="#00bcd4" fill={theme.palette.mode === 'dark' ? '#001a1a' : '#f0ffff'} travellerWidth={6} startIndex={Math.max(0, (macroData.us_unemployment?.length ?? 0) - 60)} />
            </LineChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: BLS</Typography>
        </Paper>
        ) : null}

        {/* US Fed Funds Rate */}
        {macroData.us_fed_rate?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#001433,#002766)' : 'linear-gradient(145deg,#f0f4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#003087,#0052cc)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇺🇸</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US Fed Funds Rate</Typography>
              <Typography variant="caption" color="text.secondary">Effective Rate % · {chartRange(macroData.us_fed_rate)} · Live via FRED</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={310}>
            <AreaChart data={padToCurrentMonth(macroData.us_fed_rate)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradFed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1565c0" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#1565c0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Area type="stepAfter" dataKey="value" stroke="#1565c0" fill="url(#gradFed)" strokeWidth={2.5} dot={false} />
              <Brush dataKey="month" height={24} stroke="#1565c0" fill={theme.palette.mode === 'dark' ? '#001433' : '#f0f4ff'} travellerWidth={6} startIndex={Math.max(0, (macroData.us_fed_rate?.length ?? 0) - 60)} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: FRED (FEDFUNDS)</Typography>
        </Paper>
        ) : null}

        {/* US 10Y Treasury Yield */}
        {macroData.us_10y_yield?.length ? (
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#0a1a00,#1a3300)' : 'linear-gradient(145deg,#f4fff0,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#1b5e20,#43a047)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>📜</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US 10Y Treasury Yield</Typography>
              <Typography variant="caption" color="text.secondary">Monthly Avg % · {chartRange(macroData.us_10y_yield)} · Live via FRED</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={310}>
            <AreaChart data={padToCurrentMonth(macroData.us_10y_yield)} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradTreasury" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2e7d32" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#2e7d32" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} minTickGap={80} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Area type="monotone" dataKey="value" stroke="#2e7d32" fill="url(#gradTreasury)" strokeWidth={2.5} dot={false} />
              <Brush dataKey="month" height={24} stroke="#2e7d32" fill={theme.palette.mode === 'dark' ? '#0a1a00' : '#f4fff0'} travellerWidth={6} startIndex={Math.max(0, (macroData.us_10y_yield?.length ?? 0) - 60)} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: FRED (GS10)</Typography>
        </Paper>
        ) : null}

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
        {macroData.rbi_repo_rate?.length ? (
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
              <Typography variant="caption" color="text.secondary">Reserve Bank of India · {macroData.rbi_repo_rate[0].date} – present</Typography>
            </Box>
            <Box sx={{ textAlign: 'right' }}>
              <Typography sx={{ fontWeight: 900, fontSize: 36, color: '#1e88e5', fontFamily: 'monospace', lineHeight: 1 }}>
                {rbiRate != null ? rbiRate.toFixed(2) : '—'}<Typography component="span" sx={{ fontSize: 18, fontWeight: 700, color: '#1e88e5' }}>%</Typography>
              </Typography>
              <Typography variant="caption" color="text.secondary">Current · Effective {rbiDate}</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={310}>
            <AreaChart data={macroData.rbi_repo_rate} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="rbiGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#1e88e5" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#1e88e5" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={80} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 'auto']} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={42} tickLine={false} axisLine={false} />
              <RechartTooltip formatter={(v: number) => [`${v.toFixed(2)}%`, 'Repo Rate']} labelStyle={{ fontWeight: 600 }} contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, fontSize: 13 }} />
              {rbiRate != null && (
                <ReferenceLine y={rbiRate} stroke="#1e88e5" strokeDasharray="5 3" label={{ value: `Current ${rbiRate.toFixed(2)}%`, position: 'insideTopRight', fontSize: 11, fill: '#1e88e5' }} />
              )}
              <Area type="stepAfter" dataKey="rate" stroke="#1e88e5" strokeWidth={2} fill="url(#rbiGrad)" dot={false} activeDot={{ r: 4, fill: '#1e88e5', strokeWidth: 0 }} />
              <Brush dataKey="date" height={24} stroke="#1e88e5" fill={theme.palette.mode === 'dark' ? '#071220' : '#f0f7ff'} travellerWidth={6} startIndex={Math.max(0, (macroData.rbi_repo_rate?.length ?? 0) - 60)} />
            </AreaChart>
          </ResponsiveContainer>
          <Box sx={{ display: 'flex', gap: 3, mt: 1.5, flexWrap: 'wrap' }}>
            {[{ label: 'SDF', val: sdfRate }, { label: 'MSF', val: msfRate }, { label: 'CRR', val: '4.00%' }, { label: 'SLR', val: '18.00%' }].map((r) => (
              <Box key={r.label}>
                <Typography variant="caption" color="text.secondary">{r.label}</Typography>
                <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{r.val}</Typography>
              </Box>
            ))}
          </Box>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 1, textAlign: 'right' }}>Source: RBI</Typography>
        </Paper>
        ) : null}

        {/* Bank FD Rates */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, 1fr)', md: 'repeat(8, 1fr)' }, gap: 1.5 }}>
          {BANK_FD_DISPLAY.map((config) => {
            const fd = referenceRates.bank_fd.find((f) => f.name === config.key);
            return (
              <Box
                key={config.key}
                sx={{
                  p: 2, borderRadius: 2.5, textAlign: 'center',
                  background: config.gradient,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                  color: '#fff',
                  display: 'flex', flexDirection: 'column', gap: 0.5,
                }}
              >
                <Typography sx={{ fontWeight: 800, fontSize: 15, color: '#fff', lineHeight: 1.2 }}>{config.displayName}</Typography>
                <Typography sx={{ fontWeight: 900, fontSize: 28, lineHeight: 1, color: '#fff' }}>
                  {fd ? fd.rate : '—'}<Typography component="span" sx={{ fontSize: 16, fontWeight: 700 }}>{fd ? '%' : ''}</Typography>
                </Typography>
                <Typography sx={{ fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>{fd?.sub_info ?? ''}</Typography>
              </Box>
            );
          })}
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
          <Chip
            label={referenceRates.govt_schemes.find((s) => s.name === 'ppf')?.sub_info ?? 'Current Quarter'}
            size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 11 }}
          />
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(4, 1fr)', md: 'repeat(8, 1fr)' }, gap: 1.5 }}>
          {GOVT_SCHEME_DISPLAY.map((config) => {
            const scheme = referenceRates.govt_schemes.find((s) => s.name === config.key);
            return (
              <Box
                key={config.key}
                sx={{
                  p: 2, borderRadius: 2.5, textAlign: 'center',
                  background: config.gradient,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                  color: '#fff',
                  display: 'flex', flexDirection: 'column', gap: 0.5,
                }}
              >
                <Typography sx={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: 0.5, fontSize: 15, color: '#fff', lineHeight: 1.2 }}>
                  {config.displayName}
                </Typography>
                <Typography sx={{ fontWeight: 900, fontSize: 28, lineHeight: 1, color: '#fff' }}>
                  {scheme ? scheme.rate : '—'}<Typography component="span" sx={{ fontSize: 16, fontWeight: 700 }}>{scheme ? '%' : ''}</Typography>
                </Typography>
                <Typography sx={{ fontSize: 12, color: 'rgba(255,255,255,0.85)' }}>{scheme?.sub_info ?? ''}</Typography>
              </Box>
            );
          })}
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

        {/* ── Financial Calendar ─────────────────────────────────────── */}
        {(() => {
          const CAT_COLORS: Record<string, { badge: string; label: string }> = {
            central_bank:  { badge: '#7c4dff', label: 'Central Bank' },
            tax:           { badge: '#ff6d00', label: 'Tax' },
            market:        { badge: '#0091ea', label: 'Market' },
            economic_data: { badge: '#00a572', label: 'Economic Data' },
            policy:        { badge: '#dd2c00', label: 'Policy' },
          };
          const SHORT_TITLE: Record<string, string> = {
            'Fed FOMC Meeting': 'FOMC',
            'RBI MPC Meeting': 'RBI MPC',
            'ECB Policy Meeting': 'ECB',
            'Bank of England MPC': 'BoE MPC',
            'Advance Tax Deadline': 'Adv. Tax',
            'ITR Filing Deadline': 'ITR Filing',
            'ITR Filing (Audit)': 'ITR Audit',
            'NSE F&O Monthly Expiry': 'F&O Expiry',
            'US Non-Farm Payrolls': 'NFP',
            'US CPI Inflation Data': 'US CPI',
            'GST Return (GSTR-1)': 'GST-1',
            'India Q4 FY26 Earnings Season': 'Earnings',
            'US Q1 2026 Earnings Season': 'Earnings',
            'US Q2 2026 Earnings Season': 'Earnings',
            'India Union Budget 2027': 'Budget',
            'US Fiscal Year End': 'US FY End',
            'G7 Summit 2026': 'G7 Summit',
          };

          const todayDate = new Date();
          const calBase = new Date(todayDate.getFullYear(), todayDate.getMonth() + calendarOffset, 1);
          const calYear = calBase.getFullYear();
          const calMonth = calBase.getMonth();
          const monthLabel = calBase.toLocaleString('default', { month: 'long', year: 'numeric' });

          // Index events by YYYY-MM-DD for O(1) lookup
          const eventsByDate: Record<string, FinancialEvent[]> = {};
          upcomingEvents.calendar_events.forEach((ev) => {
            if (!eventsByDate[ev.date]) eventsByDate[ev.date] = [];
            eventsByDate[ev.date].push(ev);
          });

          // Index market holidays by date
          const holidaysByDate: Record<string, string> = {};
          upcomingEvents.market_holidays.forEach((h) => {
            holidaysByDate[h.date] = h.name;
          });

          // Build calendar cell array (null = empty padding day)
          const firstDow = new Date(calYear, calMonth, 1).getDay();
          const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
          const cells: (number | null)[] = [];
          for (let i = 0; i < firstDow; i++) cells.push(null);
          for (let d = 1; d <= daysInMonth; d++) cells.push(d);
          while (cells.length % 7 !== 0) cells.push(null);

          const DAY_HDRS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
          const totalRows = cells.length / 7;

          return (
            <>
              {/* Section header + month navigation */}
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1, flexWrap: 'wrap' }}>
                <EventIcon sx={{ fontSize: 18, color: '#7c4dff' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  Financial Calendar — India &amp; Global
                </Typography>
                <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <IconButton
                    size="small"
                    onClick={() => setCalendarOffset((o) => Math.max(0, o - 1))}
                    disabled={calendarOffset === 0}
                  >
                    <ChevronLeftIcon fontSize="small" />
                  </IconButton>
                  <Typography variant="body2" sx={{ fontWeight: 700, minWidth: 130, textAlign: 'center', letterSpacing: 0.3 }}>
                    {monthLabel}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => setCalendarOffset((o) => Math.min(2, o + 1))}
                    disabled={calendarOffset === 2}
                  >
                    <ChevronRightIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Box>

              {/* Calendar grid */}
              {upcomingEvents.calendar_events.length === 0 && (
                <Alert severity="info" sx={{ mb: 1.5, borderRadius: 2, py: 0.5 }} icon={false}>
                  <Typography variant="caption">Loading calendar events — please wait or restart the backend if this persists.</Typography>
                </Alert>
              )}
              <Box
                sx={{
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 2,
                  overflow: 'hidden',
                  mb: 2.5,
                  width: '100%',
                }}
              >
                {/* Day-of-week header row */}
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(7, 1fr)',
                    background: theme.palette.mode === 'dark'
                      ? 'linear-gradient(135deg,#1a2740,#0f1e30)'
                      : 'linear-gradient(135deg,#eef2ff,#e8f0fe)',
                  }}
                >
                  {DAY_HDRS.map((d, i) => (
                    <Box
                      key={d}
                      sx={{
                        py: 1, textAlign: 'center',
                        borderRight: i < 6 ? `1px solid ${theme.palette.divider}` : 'none',
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 700, fontSize: { xs: 10, sm: 12 },
                          color: i === 0 || i === 6
                            ? (theme.palette.mode === 'dark' ? '#ff7070' : '#d32f2f')
                            : 'text.secondary',
                        }}
                      >
                        {d}
                      </Typography>
                    </Box>
                  ))}
                </Box>

                {/* Day cells */}
                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)' }}>
                  {cells.map((day, i) => {
                    const colIdx = i % 7;
                    const rowIdx = Math.floor(i / 7);
                    const isLastRow = rowIdx === totalRows - 1;
                    const isLastCol = colIdx === 6;
                    const dateStr = day
                      ? `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                      : '';
                    const dayEvents = dateStr ? (eventsByDate[dateStr] ?? []) : [];
                    const isToday =
                      day !== null &&
                      calYear === todayDate.getFullYear() &&
                      calMonth === todayDate.getMonth() &&
                      day === todayDate.getDate();
                    const isWeekend = colIdx === 0 || colIdx === 6;
                    const holidayName = dateStr ? (holidaysByDate[dateStr] ?? null) : null;
                    const isHoliday = !!holidayName;

                    return (
                      <Box
                        key={i}
                        sx={{
                          minHeight: { xs: 90, sm: 110 },
                          p: { xs: '5px', sm: '8px' },
                          borderRight: !isLastCol ? `1px solid ${theme.palette.divider}` : 'none',
                          borderBottom: !isLastRow ? `1px solid ${theme.palette.divider}` : 'none',
                          background: day === null
                            ? (theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.25)' : 'rgba(0,0,0,0.03)')
                            : isToday
                              ? (theme.palette.mode === 'dark' ? '#0d2744' : '#e3f2fd')
                              : isHoliday
                                ? (theme.palette.mode === 'dark' ? '#1e0a0a' : '#fff5f5')
                                : isWeekend
                                  ? (theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.018)')
                                  : 'transparent',
                          transition: 'background 0.1s',
                        }}
                      >
                        {day !== null && (
                          <>
                            {/* Date number */}
                            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: (dayEvents.length > 0 || isHoliday) ? '4px' : 0 }}>
                              <Box
                                sx={{
                                  width: { xs: 20, sm: 24 },
                                  height: { xs: 20, sm: 24 },
                                  borderRadius: '50%',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  background: isToday ? '#1e88e5' : 'transparent',
                                  flexShrink: 0,
                                }}
                              >
                                <Typography
                                  sx={{
                                    fontWeight: isToday ? 900 : isWeekend || isHoliday ? 600 : 400,
                                    fontSize: { xs: 11, sm: 13 },
                                    lineHeight: 1,
                                    color: isToday
                                      ? '#fff'
                                      : isHoliday
                                        ? (theme.palette.mode === 'dark' ? '#ff8a80' : '#c62828')
                                        : isWeekend
                                          ? (theme.palette.mode === 'dark' ? '#ff7070' : '#d32f2f')
                                          : 'text.primary',
                                  }}
                                >
                                  {day}
                                </Typography>
                              </Box>
                            </Box>

                            {/* Market holiday banner */}
                            {isHoliday && (
                              <Tooltip title={`NSE Market Closed — ${holidayName}`} placement="top" arrow>
                                <Box
                                  sx={{
                                    display: 'flex', alignItems: 'center', gap: '3px',
                                    bgcolor: theme.palette.mode === 'dark' ? '#3e0000' : '#ffebee',
                                    border: `1px solid ${theme.palette.mode === 'dark' ? '#7f1111' : '#ef9a9a'}`,
                                    borderRadius: '4px',
                                    px: { xs: '4px', sm: '6px' },
                                    py: { xs: '3px', sm: '4px' },
                                    mb: dayEvents.length > 0 ? '4px' : 0,
                                    cursor: 'default',
                                  }}
                                >
                                  <Typography sx={{ fontSize: { xs: 10, sm: 11 }, lineHeight: 1, flexShrink: 0 }}>🏖️</Typography>
                                  <Typography
                                    sx={{
                                      fontSize: { xs: 10, sm: 11 },
                                      fontWeight: 600,
                                      color: theme.palette.mode === 'dark' ? '#ff8a80' : '#c62828',
                                      lineHeight: 1.4,
                                      whiteSpace: 'normal',
                                      wordBreak: 'break-word',
                                    }}
                                  >
                                    {holidayName}
                                  </Typography>
                                </Box>
                              </Tooltip>
                            )}

                            {/* Event pills */}
                            <Stack spacing={0.4}>
                              {dayEvents.map((ev, j) => {
                                const badgeColor = CAT_COLORS[ev.category]?.badge ?? '#888';
                                const label = dayEvents.length > 1
                                  ? (SHORT_TITLE[ev.title] ?? ev.title.substring(0, 11))
                                  : ev.title;
                                return (
                                  <Tooltip
                                    key={j}
                                    title={
                                      <Box>
                                        <Typography sx={{ fontWeight: 700, fontSize: 13 }}>{ev.flag} {ev.title}</Typography>
                                        <Typography sx={{ fontSize: 12, opacity: 0.85 }}>{ev.subtitle}</Typography>
                                        <Typography sx={{ fontSize: 11, opacity: 0.7, mt: 0.3 }}>{ev.description}</Typography>
                                        {ev.importance === 'high' && (
                                          <Chip label="HIGH IMPACT" size="small" sx={{ mt: 0.5, height: 16, fontSize: 10, fontWeight: 700, bgcolor: '#ff1744', color: '#fff' }} />
                                        )}
                                      </Box>
                                    }
                                    placement="top"
                                    arrow
                                  >
                                    <Box
                                      sx={{
                                        display: 'flex', alignItems: 'flex-start', gap: '3px',
                                        bgcolor: badgeColor,
                                        borderRadius: '4px',
                                        px: { xs: '4px', sm: '6px' },
                                        py: { xs: '3px', sm: '4px' },
                                        cursor: 'default',
                                        boxShadow: ev.importance === 'high' ? `0 0 0 1.5px #ff174488 inset` : 'none',
                                      }}
                                    >
                                      <Typography sx={{ fontSize: { xs: 11, sm: 13 }, lineHeight: 1.3, flexShrink: 0 }}>{ev.flag}</Typography>
                                      <Typography
                                        sx={{
                                          fontSize: { xs: 11, sm: 12 },
                                          fontWeight: 700,
                                          color: '#fff',
                                          lineHeight: 1.4,
                                          whiteSpace: 'normal',
                                          wordBreak: 'break-word',
                                          flex: 1,
                                        }}
                                      >
                                        {label}
                                      </Typography>
                                    </Box>
                                  </Tooltip>
                                );
                              })}
                            </Stack>
                          </>
                        )}
                      </Box>
                    );
                  })}
                </Box>
              </Box>

              {/* Legend */}
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: { xs: 1, sm: 2 }, mb: 3, px: 0.5 }}>
                {Object.entries(CAT_COLORS).map(([, { badge, label }]) => (
                  <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
                    <Box sx={{ width: 10, height: 10, borderRadius: '2px', bgcolor: badge, flexShrink: 0 }} />
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: 11 }}>{label}</Typography>
                  </Box>
                ))}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
                  <Box sx={{ width: 10, height: 10, borderRadius: '2px', bgcolor: '#888', flexShrink: 0, boxShadow: '0 0 0 1.5px #ff174488 inset' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: 11 }}>High Impact (red border)</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
                  <Box sx={{ width: 10, height: 10, borderRadius: '2px', bgcolor: theme.palette.mode === 'dark' ? '#3e0000' : '#ffebee', border: `1px solid ${theme.palette.mode === 'dark' ? '#7f1111' : '#ef9a9a'}`, flexShrink: 0 }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: 11 }}>NSE Market Holiday</Typography>
                </Box>
              </Box>
            </>
          );
        })()}

      </Paper>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <Alert severity="info" sx={{ borderRadius: 2, mt: 1 }} icon={false}>
        <Typography variant="caption" color="text.secondary">
          <strong>Live data:</strong> Indices &amp; commodities via Yahoo Finance (server-side proxy) — auto-refresh every <strong>30 min</strong>.
          Bitcoin via CoinGecko — auto-refresh every <strong>5 min</strong>.
          Macro indicators from BLS &amp; World Bank — refreshed daily. RBI repo rate scraped from BankBazaar — updated every two months.
          Bank FD rates scraped monthly; govt scheme rates scraped quarterly. Verify with official sources before investing.
        </Typography>
      </Alert>
    </Box>
  );
};

export default MarketInsight;
