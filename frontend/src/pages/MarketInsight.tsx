import React, { useEffect, useState, useCallback } from 'react';
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

interface MacroData {
  rbi_repo_rate: Array<{ date: string; rate: number }>;
  india_cpi: Array<{ month: string; value: number }>;
  us_cpi: Array<{ month: string; value: number }> | null;
  us_unemployment: Array<{ month: string; value: number }> | null;
  us_fed_rate: Array<{ month: string; value: number }> | null;
  us_10y_yield: Array<{ month: string; value: number }> | null;
  nifty_pe: Array<{ month: string; value: number }> | null;
  india_vix: Array<{ month: string; value: number }> | null;
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

const US_FED_RATE_DATA = [
  { month: "Jan'23", value: 4.33 }, { month: "Feb'23", value: 4.57 },
  { month: "Mar'23", value: 4.79 }, { month: "Apr'23", value: 4.83 },
  { month: "May'23", value: 5.06 }, { month: "Jun'23", value: 5.08 },
  { month: "Jul'23", value: 5.12 }, { month: "Aug'23", value: 5.33 },
  { month: "Sep'23", value: 5.33 }, { month: "Oct'23", value: 5.33 },
  { month: "Nov'23", value: 5.33 }, { month: "Dec'23", value: 5.33 },
  { month: "Jan'24", value: 5.33 }, { month: "Feb'24", value: 5.33 },
  { month: "Mar'24", value: 5.33 }, { month: "Apr'24", value: 5.33 },
  { month: "May'24", value: 5.33 }, { month: "Jun'24", value: 5.33 },
  { month: "Jul'24", value: 5.33 }, { month: "Aug'24", value: 5.33 },
  { month: "Sep'24", value: 5.13 }, { month: "Oct'24", value: 4.83 },
  { month: "Nov'24", value: 4.64 }, { month: "Dec'24", value: 4.48 },
  { month: "Jan'25", value: 4.33 }, { month: "Feb'25", value: 4.33 },
  { month: "Mar'25", value: 4.33 }, { month: "Apr'25", value: 4.33 },
  { month: "May'25", value: 4.33 }, { month: "Jun'25", value: 4.33 },
  { month: "Jul'25", value: 4.08 }, { month: "Aug'25", value: 3.83 },
  { month: "Sep'25", value: 3.83 }, { month: "Oct'25", value: 3.58 },
  { month: "Nov'25", value: 3.33 }, { month: "Dec'25", value: 3.33 },
  { month: "Jan'26", value: 3.33 }, { month: "Feb'26", value: 3.33 },
];

const US_10Y_YIELD_DATA = [
  { month: "Jan'23", value: 3.53 }, { month: "Feb'23", value: 3.82 },
  { month: "Mar'23", value: 3.96 }, { month: "Apr'23", value: 3.57 },
  { month: "May'23", value: 3.57 }, { month: "Jun'23", value: 3.84 },
  { month: "Jul'23", value: 3.97 }, { month: "Aug'23", value: 4.26 },
  { month: "Sep'23", value: 4.57 }, { month: "Oct'23", value: 4.93 },
  { month: "Nov'23", value: 4.47 }, { month: "Dec'23", value: 4.02 },
  { month: "Jan'24", value: 4.05 }, { month: "Feb'24", value: 4.29 },
  { month: "Mar'24", value: 4.20 }, { month: "Apr'24", value: 4.67 },
  { month: "May'24", value: 4.49 }, { month: "Jun'24", value: 4.36 },
  { month: "Jul'24", value: 4.26 }, { month: "Aug'24", value: 3.94 },
  { month: "Sep'24", value: 3.65 }, { month: "Oct'24", value: 4.06 },
  { month: "Nov'24", value: 4.42 }, { month: "Dec'24", value: 4.25 },
  { month: "Jan'25", value: 4.69 }, { month: "Feb'25", value: 4.51 },
  { month: "Mar'25", value: 4.27 }, { month: "Apr'25", value: 4.29 },
  { month: "May'25", value: 4.48 }, { month: "Jun'25", value: 4.32 },
  { month: "Jul'25", value: 4.20 }, { month: "Aug'25", value: 3.99 },
  { month: "Sep'25", value: 3.73 }, { month: "Oct'25", value: 4.15 },
  { month: "Nov'25", value: 4.41 }, { month: "Dec'25", value: 4.54 },
  { month: "Jan'26", value: 4.60 }, { month: "Feb'26", value: 4.43 },
];

const NIFTY_PE_DATA = [
  { month: "Jan'23", value: 22.5 }, { month: "Feb'23", value: 21.3 },
  { month: "Mar'23", value: 21.8 }, { month: "Apr'23", value: 23.6 },
  { month: "May'23", value: 22.3 }, { month: "Jun'23", value: 23.1 },
  { month: "Jul'23", value: 23.9 }, { month: "Aug'23", value: 22.2 },
  { month: "Sep'23", value: 23.3 }, { month: "Oct'23", value: 22.5 },
  { month: "Nov'23", value: 24.6 }, { month: "Dec'23", value: 24.7 },
  { month: "Jan'24", value: 23.4 }, { month: "Feb'24", value: 21.6 },
  { month: "Mar'24", value: 22.2 }, { month: "Apr'24", value: 22.8 },
  { month: "May'24", value: 22.5 }, { month: "Jun'24", value: 23.1 },
  { month: "Jul'24", value: 24.0 }, { month: "Aug'24", value: 24.2 },
  { month: "Sep'24", value: 23.5 }, { month: "Oct'24", value: 22.5 },
  { month: "Nov'24", value: 22.2 }, { month: "Dec'24", value: 22.4 },
  { month: "Jan'25", value: 21.5 }, { month: "Feb'25", value: 20.2 },
  { month: "Mar'25", value: 19.8 }, { month: "Apr'25", value: 21.3 },
  { month: "May'25", value: 21.8 }, { month: "Jun'25", value: 22.5 },
  { month: "Jul'25", value: 23.1 }, { month: "Aug'25", value: 22.6 },
  { month: "Sep'25", value: 23.2 }, { month: "Oct'25", value: 22.8 },
  { month: "Nov'25", value: 21.6 }, { month: "Dec'25", value: 22.1 },
  { month: "Jan'26", value: 21.9 }, { month: "Feb'26", value: 20.3 },
];

const INDIA_VIX_DATA = [
  { month: "Jan'23", value: 13.82 }, { month: "Feb'23", value: 13.25 },
  { month: "Mar'23", value: 11.59 }, { month: "Apr'23", value: 11.68 },
  { month: "May'23", value: 11.52 }, { month: "Jun'23", value: 10.89 },
  { month: "Jul'23", value: 10.83 }, { month: "Aug'23", value: 11.57 },
  { month: "Sep'23", value: 10.92 }, { month: "Oct'23", value: 12.78 },
  { month: "Nov'23", value: 12.14 }, { month: "Dec'23", value: 13.01 },
  { month: "Jan'24", value: 14.11 }, { month: "Feb'24", value: 14.52 },
  { month: "Mar'24", value: 13.46 }, { month: "Apr'24", value: 15.83 },
  { month: "May'24", value: 20.38 }, { month: "Jun'24", value: 14.07 },
  { month: "Jul'24", value: 14.33 }, { month: "Aug'24", value: 15.28 },
  { month: "Sep'24", value: 13.56 }, { month: "Oct'24", value: 14.90 },
  { month: "Nov'24", value: 15.17 }, { month: "Dec'24", value: 14.62 },
  { month: "Jan'25", value: 16.04 }, { month: "Feb'25", value: 15.62 },
  { month: "Mar'25", value: 14.85 }, { month: "Apr'25", value: 17.23 },
  { month: "May'25", value: 16.44 }, { month: "Jun'25", value: 14.18 },
  { month: "Jul'25", value: 13.72 }, { month: "Aug'25", value: 14.39 },
  { month: "Sep'25", value: 13.15 }, { month: "Oct'25", value: 14.86 },
  { month: "Nov'25", value: 15.33 }, { month: "Dec'25", value: 14.27 },
  { month: "Jan'26", value: 15.81 }, { month: "Feb'26", value: 16.44 },
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
  const [, setLastRefreshBtc] = useState<Date | null>(null);

  const [macroData, setMacroData] = useState<MacroData>({
    rbi_repo_rate: RBI_REPO_RATE_HISTORY,
    india_cpi: INDIA_INFLATION_DATA,
    us_cpi: US_INFLATION_DATA,
    us_unemployment: US_UNEMPLOYMENT_DATA,
    us_fed_rate: US_FED_RATE_DATA,
    us_10y_yield: US_10Y_YIELD_DATA,
    nifty_pe: NIFTY_PE_DATA,
    india_vix: INDIA_VIX_DATA,
  });

  const [referenceRates, setReferenceRates] = useState<ReferenceRatesData>({
    bank_fd: [
      { name: 'sbi',      rate: 6.05, sub_info: null, updated_at: '' },
      { name: 'hdfc',     rate: 6.15, sub_info: null, updated_at: '' },
      { name: 'icici',    rate: 6.50, sub_info: null, updated_at: '' },
      { name: 'axis',     rate: 6.45, sub_info: null, updated_at: '' },
      { name: 'kotak',    rate: 6.25, sub_info: null, updated_at: '' },
      { name: 'bob',      rate: 6.00, sub_info: null, updated_at: '' },
      { name: 'indusind', rate: 6.50, sub_info: null, updated_at: '' },
      { name: 'yesbank',  rate: 6.75, sub_info: null, updated_at: '' },
    ],
    govt_schemes: [
      { name: 'ppf',      rate: 7.10, sub_info: null, updated_at: '' },
      { name: 'epf',      rate: 8.25, sub_info: 'FY 24-25', updated_at: '' },
      { name: 'ssy',      rate: 8.20, sub_info: null, updated_at: '' },
      { name: 'kvp',      rate: 7.50, sub_info: null, updated_at: '' },
      { name: 'scss',     rate: 8.20, sub_info: null, updated_at: '' },
      { name: 'rbi_bond', rate: 8.05, sub_info: null, updated_at: '' },
      { name: 'nsc',      rate: 7.70, sub_info: null, updated_at: '' },
      { name: 'mis',      rate: 7.40, sub_info: null, updated_at: '' },
    ],
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
        rbi_repo_rate:   data.rbi_repo_rate?.length  ? data.rbi_repo_rate   : prev.rbi_repo_rate,
        india_cpi:       data.india_cpi?.length      ? data.india_cpi       : prev.india_cpi,
        us_cpi:          data.us_cpi                 ? data.us_cpi          : prev.us_cpi,
        us_unemployment: data.us_unemployment        ? data.us_unemployment : prev.us_unemployment,
        us_fed_rate:     data.us_fed_rate            ? data.us_fed_rate     : prev.us_fed_rate,
        us_10y_yield:    data.us_10y_yield           ? data.us_10y_yield    : prev.us_10y_yield,
        nifty_pe:        data.nifty_pe               ? data.nifty_pe        : prev.nifty_pe,
        india_vix:       data.india_vix              ? data.india_vix       : prev.india_vix,
      }));
    }).catch(() => { /* keep hardcoded fallback */ });
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

  const [calendarOffset, setCalendarOffset] = useState(0);

  const btc = quotes['btc'];

  // Derived from live macro data
  const latestRbi = macroData.rbi_repo_rate[macroData.rbi_repo_rate.length - 1];
  const rbiRate    = latestRbi?.rate ?? 6.00;
  const rbiDate    = latestRbi?.date ?? '';
  const sdfRate    = (rbiRate - 0.25).toFixed(2) + '%';
  const msfRate    = (rbiRate + 0.25).toFixed(2) + '%';
  const chartRange = (data: Array<{ month: string }>) =>
    data.length ? `${data[0].month} – ${data[data.length - 1].month}` : '';

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
              <Typography variant="caption" color="text.secondary">YoY % · {chartRange(macroData.india_cpi)}</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={macroData.india_cpi} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
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

        {/* Nifty 50 P/E Ratio */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#1a0a00,#331500)' : 'linear-gradient(145deg,#fff8f0,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#e65100,#ff8f00)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇮🇳</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Nifty 50 P/E Ratio</Typography>
              <Typography variant="caption" color="text.secondary">Price-to-Earnings · {chartRange(macroData.nifty_pe ?? NIFTY_PE_DATA)} · Live via NSE</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={macroData.nifty_pe ?? NIFTY_PE_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[15, 28]} />
              <RechartTooltip content={<ChartTip unit="x" />} />
              <ReferenceLine y={20} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '20x avg', fontSize: 9, fill: '#f59e0b' }} />
              <Line type="monotone" dataKey="value" stroke="#f97316" strokeWidth={2.5} dot={{ r: 2, fill: '#f97316' }} />
            </LineChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSE India</Typography>
        </Paper>

        {/* India VIX */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#15001a,#2a0035)' : 'linear-gradient(145deg,#fdf4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#4a0072,#9c27b0)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>📉</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>India VIX</Typography>
              <Typography variant="caption" color="text.secondary">Fear Index · {chartRange(macroData.india_vix ?? INDIA_VIX_DATA)} · Live via NSE</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={macroData.india_vix ?? INDIA_VIX_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradVix" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#9c27b0" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#9c27b0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[8, 26]} />
              <RechartTooltip content={<ChartTip unit="" />} />
              <ReferenceLine y={20} stroke="#ef5350" strokeDasharray="4 2" label={{ value: 'High fear', fontSize: 9, fill: '#ef5350' }} />
              <Area type="monotone" dataKey="value" stroke="#9c27b0" fill="url(#gradVix)" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: NSE India / Yahoo Finance</Typography>
        </Paper>

        {/* US CPI */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#0d0020,#1a0040)' : 'linear-gradient(145deg,#f8f4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#7c4dff,#b47cff)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇺🇸</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US CPI Inflation</Typography>
              <Typography variant="caption" color="text.secondary">YoY % · {macroData.us_cpi ? chartRange(macroData.us_cpi) : chartRange(US_INFLATION_DATA)} · Live via BLS</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={macroData.us_cpi ?? US_INFLATION_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
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
              <Typography variant="caption" color="text.secondary">Seasonally Adjusted % · {macroData.us_unemployment ? chartRange(macroData.us_unemployment) : chartRange(US_UNEMPLOYMENT_DATA)} · Live via BLS</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={macroData.us_unemployment ?? US_UNEMPLOYMENT_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[2.5, 5.5]} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Line type="monotone" dataKey="value" stroke="#00bcd4" strokeWidth={2.5} dot={{ r: 2, fill: '#00bcd4' }} />
            </LineChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: BLS</Typography>
        </Paper>

        {/* US Fed Funds Rate */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#001433,#002766)' : 'linear-gradient(145deg,#f0f4ff,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#003087,#0052cc)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>🇺🇸</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US Fed Funds Rate</Typography>
              <Typography variant="caption" color="text.secondary">Effective Rate % · {chartRange(macroData.us_fed_rate ?? US_FED_RATE_DATA)} · Live via FRED</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={macroData.us_fed_rate ?? US_FED_RATE_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradFed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1565c0" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#1565c0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[2, 6]} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Area type="stepAfter" dataKey="value" stroke="#1565c0" fill="url(#gradFed)" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: FRED (FEDFUNDS)</Typography>
        </Paper>

        {/* US 10Y Treasury Yield */}
        <Paper elevation={2} sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, background: theme.palette.mode === 'dark' ? 'linear-gradient(145deg,#0a1a00,#1a3300)' : 'linear-gradient(145deg,#f4fff0,#fff)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Box sx={{ px: 1.2, py: 0.5, borderRadius: 1.5, background: 'linear-gradient(135deg,#1b5e20,#43a047)', mr: 0.5 }}>
              <Typography sx={{ fontSize: 16 }}>📜</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>US 10Y Treasury Yield</Typography>
              <Typography variant="caption" color="text.secondary">Monthly Avg % · {chartRange(macroData.us_10y_yield ?? US_10Y_YIELD_DATA)} · Live via FRED</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={macroData.us_10y_yield ?? US_10Y_YIELD_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradTreasury" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2e7d32" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#2e7d32" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} domain={[2.5, 5.5]} unit="%" />
              <RechartTooltip content={<ChartTip unit="%" />} />
              <Area type="monotone" dataKey="value" stroke="#2e7d32" fill="url(#gradTreasury)" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}>Source: FRED (GS10)</Typography>
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
                {rbiRate.toFixed(2)}<Typography component="span" sx={{ fontSize: 18, fontWeight: 700, color: '#1e88e5' }}>%</Typography>
              </Typography>
              <Typography variant="caption" color="text.secondary">Current · Effective {rbiDate}</Typography>
            </Box>
          </Box>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={macroData.rbi_repo_rate} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
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
              <ReferenceLine y={rbiRate} stroke="#1e88e5" strokeDasharray="4 3" label={{ value: `Current ${rbiRate.toFixed(2)}%`, position: 'insideTopRight', fontSize: 11, fill: '#1e88e5' }} />
              <Area type="stepAfter" dataKey="rate" stroke="#1e88e5" strokeWidth={2.5} fill="url(#rbiGrad)" dot={{ r: 3, fill: '#1e88e5' }} activeDot={{ r: 5 }} />
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
