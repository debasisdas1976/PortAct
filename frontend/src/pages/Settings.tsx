import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, TextField, Button, Grid, Alert,
  CircularProgress, Snackbar, Tabs, Tab, MenuItem, Select,
  FormControl, FormControlLabel, Switch, InputLabel, InputAdornment, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, IconButton, Chip, Tooltip, Radio,
  Dialog, DialogActions, DialogContent, DialogTitle,
} from '@mui/material';
import {
  Save, RestartAlt, Visibility, VisibilityOff, Schedule, Work, AccountBalance, Public, Refresh,
  Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon,
} from '@mui/icons-material';
import { authAPI, settingsAPI } from '../services/api';

/* ─────────────────── types ─────────────────── */

interface UserProfile {
  email: string;
  username: string;
  full_name?: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  is_employed?: boolean;
  basic_salary?: number;
  da_percentage?: number;
  employer_name?: string;
  date_of_joining?: string;
  pf_employee_pct?: number;
  pf_employer_pct?: number;
}

interface AppSetting {
  key: string;
  value: string | null;
  value_type: string;
  category: string | null;
  label: string | null;
  description: string | null;
}

const formatCurrency = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v);

/* ─────────────────── constants ─────────────────── */

const AI_PROVIDERS = [
  { value: 'openai', label: 'OpenAI (GPT)' },
  { value: 'grok', label: 'Grok (xAI)' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'anthropic', label: 'Anthropic Claude' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'mistral', label: 'Mistral AI' },
];

const AI_PROVIDERS_MAP: Record<string, { key: string; label: string }> = {
  openai: { key: 'ai_openai_api_key', label: 'OpenAI API Key' },
  grok: { key: 'ai_grok_api_key', label: 'Grok API Key' },
  gemini: { key: 'ai_gemini_api_key', label: 'Google Gemini API Key' },
  anthropic: { key: 'ai_anthropic_api_key', label: 'Anthropic Claude API Key' },
  deepseek: { key: 'ai_deepseek_api_key', label: 'DeepSeek API Key' },
  mistral: { key: 'ai_mistral_api_key', label: 'Mistral API Key' },
};

const MARKET_API_KEY_FIELDS = [
  {
    key: 'finnhub_api_key',
    label: 'Finnhub API Key',
    helperText: 'Used for stock quotes and market data. Free tier at finnhub.io',
  },
  {
    key: 'fred_api_key',
    label: 'FRED API Key',
    helperText: 'Federal Reserve Economic Data — used for Global Liquidity Insight (M2 money supply). Free key at fred.stlouisfed.org',
  },
  {
    key: 'cmc_api_key',
    label: 'CoinMarketCap API Key',
    helperText: 'Used for Bitcoin Fear & Greed Index. Free tier at coinmarketcap.com/api',
  },
  {
    key: 'alpha_vantage_api_key',
    label: 'Alpha Vantage API Key',
    helperText: 'Used for US stock market data. Free tier at alphavantage.co',
  },
  {
    key: 'rapidapi_key',
    label: 'RapidAPI Key',
    helperText: 'Used for various market data endpoints via RapidAPI hub.',
  },
];

/* ─────────────────── scheduler tasks ─────────────────── */

type SchedFreq = 'interval' | 'daily' | 'weekly' | 'monthly' | 'bimonthly' | 'annual';

interface SchedulerTask {
  id: string;
  name: string;
  description: string;
  category: 'portfolio' | 'market' | 'contribution';
  freq: SchedFreq;
  /** settings keys */
  keys: {
    interval_minutes?: string;
    hour?: string;
    minute?: string;
    day?: string;
    day_of_week?: string;
    month?: string;
    ist_hour?: string;    // if hour is IST not UTC
    count?: string;       // non-schedule config (e.g. news_limit_per_user)
  };
}

const SCHEDULER_TASKS: SchedulerTask[] = [
  // ── Portfolio ──
  { id: 'price', name: 'Price Updates', description: 'Auto-fetch latest prices for stocks, MF, crypto, commodities.', category: 'portfolio', freq: 'interval', keys: { interval_minutes: 'price_update_interval_minutes' } },
  { id: 'eod', name: 'EOD Portfolio Snapshot', description: 'Capture daily portfolio value for charts & tracking.', category: 'portfolio', freq: 'daily', keys: { hour: 'eod_snapshot_hour', minute: 'eod_snapshot_minute' } },
  { id: 'news_am', name: 'Morning News Alerts', description: 'AI-generated portfolio news (morning run).', category: 'portfolio', freq: 'daily', keys: { ist_hour: 'news_morning_hour' } },
  { id: 'news_pm', name: 'Evening News Alerts', description: 'AI-generated portfolio news (evening run).', category: 'portfolio', freq: 'daily', keys: { ist_hour: 'news_evening_hour' } },
  { id: 'news_limit', name: 'News Coverage', description: 'Number of assets analysed per scheduled news run.', category: 'portfolio', freq: 'daily', keys: { count: 'news_limit_per_user' } },
  { id: 'forex', name: 'Forex Refresh', description: 'Daily update of foreign currency asset values.', category: 'portfolio', freq: 'daily', keys: { hour: 'forex_refresh_hour', minute: 'forex_refresh_minute' } },
  { id: 'mf_plan', name: 'MF Systematic Plans', description: 'Daily SIP/STP/SWP execution for mutual funds.', category: 'portfolio', freq: 'daily', keys: { hour: 'mf_systematic_plan_hour', minute: 'mf_systematic_plan_minute' } },
  { id: 'ai_models', name: 'AI Models Refresh', description: 'Refresh available AI model lists from all providers.', category: 'portfolio', freq: 'daily', keys: { hour: 'ai_models_refresh_hour', minute: 'ai_models_refresh_minute' } },
  // ── Market Insight ──
  { id: 'mmi_am', name: 'India MMI (Morning)', description: 'Market Mood Index scrape after NSE open.', category: 'market', freq: 'daily', keys: { hour: 'mmi_morning_hour', minute: 'mmi_morning_minute' } },
  { id: 'mmi_pm', name: 'India MMI (Afternoon)', description: 'Intraday MMI update.', category: 'market', freq: 'daily', keys: { hour: 'mmi_afternoon_hour', minute: 'mmi_afternoon_minute' } },
  { id: 'btc_fng', name: 'BTC Fear & Greed', description: 'Daily Bitcoin Fear & Greed Index.', category: 'market', freq: 'daily', keys: { hour: 'btc_fng_hour', minute: 'btc_fng_minute' } },
  { id: 'us_fng_open', name: 'US Fear & Greed (Open)', description: 'US Fear & Greed Index at market open.', category: 'market', freq: 'daily', keys: { hour: 'us_fng_open_hour', minute: 'us_fng_open_minute' } },
  { id: 'us_fng_close', name: 'US Fear & Greed (Close)', description: 'US Fear & Greed Index at market close.', category: 'market', freq: 'daily', keys: { hour: 'us_fng_close_hour', minute: 'us_fng_close_minute' } },
  { id: 'news_cache', name: 'Financial News Cache', description: 'Refresh upcoming financial events & news.', category: 'market', freq: 'interval', keys: { interval_minutes: 'news_cache_refresh_minutes' } },
  { id: 'liquidity', name: 'Global Liquidity Data', description: 'M2 money supply (FRED) + asset prices (Yahoo).', category: 'market', freq: 'weekly', keys: { day_of_week: 'liquidity_refresh_day_of_week', hour: 'liquidity_refresh_hour' } },
  { id: 'macro', name: 'Macro Data Refresh', description: 'US CPI, unemployment, India CPI, VIX, Nifty PE, FII/DII, SIP.', category: 'market', freq: 'monthly', keys: { day: 'macro_data_refresh_day', hour: 'macro_data_refresh_hour' } },
  { id: 'rbi', name: 'RBI Repo Rate', description: 'Bimonthly scrape on MPC meeting months.', category: 'market', freq: 'bimonthly', keys: { day: 'rbi_rate_refresh_day', hour: 'rbi_rate_refresh_hour' } },
  { id: 'bank_fd', name: 'Bank FD Rates', description: 'Monthly scrape of bank FD interest rates.', category: 'market', freq: 'monthly', keys: { day: 'bank_fd_refresh_day', hour: 'bank_fd_refresh_hour' } },
  { id: 'govt', name: 'Govt Scheme Rates', description: 'Monthly scrape of PPF, SSY, NSC, etc.', category: 'market', freq: 'monthly', keys: { day: 'govt_scheme_refresh_day', hour: 'govt_scheme_refresh_hour', minute: 'govt_scheme_refresh_minute' } },
  { id: 'nse', name: 'NSE Holidays', description: 'Annual refresh of NSE trading holidays.', category: 'market', freq: 'annual', keys: { month: 'nse_holidays_refresh_month', day: 'nse_holidays_refresh_day' } },
  // ── Contribution ──
  { id: 'pf', name: 'PF & Gratuity', description: 'Monthly PF contributions and Gratuity revaluation.', category: 'contribution', freq: 'monthly', keys: { day: 'monthly_contribution_day', hour: 'monthly_contribution_hour', minute: 'monthly_contribution_minute' } },
];

const FREQ_LABELS: Record<SchedFreq, string> = {
  interval: 'Interval',
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  bimonthly: 'Bimonthly',
  annual: 'Annual',
};

const FREQ_COLORS: Record<SchedFreq, 'primary' | 'success' | 'info' | 'warning' | 'secondary' | 'default'> = {
  interval: 'info',
  daily: 'success',
  weekly: 'primary',
  monthly: 'warning',
  bimonthly: 'secondary',
  annual: 'default',
};

const WEEKDAY_OPTIONS = [
  { value: 'mon', label: 'Monday' },
  { value: 'tue', label: 'Tuesday' },
  { value: 'wed', label: 'Wednesday' },
  { value: 'thu', label: 'Thursday' },
  { value: 'fri', label: 'Friday' },
  { value: 'sat', label: 'Saturday' },
  { value: 'sun', label: 'Sunday' },
];

const CATEGORY_LABELS: Record<string, string> = {
  portfolio: 'Portfolio',
  market: 'Market Insight',
  contribution: 'Contributions',
};

/* ─────────────────── component ─────────────────── */

const Settings: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTab = useMemo(() => {
    const t = parseInt(searchParams.get('tab') ?? '0', 10);
    return isNaN(t) ? 0 : Math.max(0, Math.min(t, 4));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [tab, setTab] = useState(initialTab);
  const [loading, setLoading] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  // Profile state
  const [profile, setProfile] = useState<UserProfile>({} as UserProfile);
  const [profileSaving, setProfileSaving] = useState(false);

  // Employment state
  const [employment, setEmployment] = useState<UserProfile>({} as UserProfile);
  const [employmentSaving, setEmploymentSaving] = useState(false);

  // App settings state
  const [appSettings, setAppSettings] = useState<AppSetting[]>([]);
  const [settingsForm, setSettingsForm] = useState<Record<string, string>>({});
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const savedSettingsRef = useRef<Record<string, string>>({});

  // Automations state
  const [automations, setAutomations] = useState<{
    system_automations: any[];
    asset_automations: any[];
  } | null>(null);
  const [automationsLoading, setAutomationsLoading] = useState(false);

  // API key visibility toggles
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});

  // AI provider dialog state
  const [aiDialogOpen, setAiDialogOpen] = useState(false);
  const [aiEditingProvider, setAiEditingProvider] = useState<string | null>(null);
  const [aiDialogForm, setAiDialogForm] = useState({ provider: '', api_key: '', model: '', endpoint: '', set_primary: false });
  const [aiModelsCache, setAiModelsCache] = useState<Record<string, string[]>>({});
  const [aiModelsLoading, setAiModelsLoading] = useState(false);

  // Market data key dialog state
  const [mktDialogOpen, setMktDialogOpen] = useState(false);
  const [mktEditingKey, setMktEditingKey] = useState<string | null>(null);
  const [mktDialogForm, setMktDialogForm] = useState({ api_key: '' });

  // Scheduler edit dialog state
  const [schedDialogOpen, setSchedDialogOpen] = useState(false);
  const [schedEditingTask, setSchedEditingTask] = useState<SchedulerTask | null>(null);

  const toggleApiKeyVisibility = (key: string) => {
    setShowApiKeys(prev => ({ ...prev, [key]: !prev[key] }));
  };

  /* ── fetch ── */
  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [user, settings] = await Promise.all([
        authAPI.getCurrentUser(),
        settingsAPI.getAll(),
      ]);
      setProfile(user);
      setEmployment(user);
      setAppSettings(settings);
      const form: Record<string, string> = {};
      for (const s of settings as AppSetting[]) {
        form[s.key] = s.value ?? '';
        if (s.key === 'session_timeout_minutes') {
          localStorage.setItem('sessionTimeoutMinutes', s.value ?? '30');
        }
      }
      setSettingsForm(form);
      savedSettingsRef.current = form;
    } catch {
      setSnackbar({ open: true, message: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const fetchAutomations = useCallback(async () => {
    setAutomationsLoading(true);
    try {
      const data = await settingsAPI.getAutomations();
      setAutomations(data);
    } catch {
      setSnackbar({ open: true, message: 'Failed to load automations' });
    } finally {
      setAutomationsLoading(false);
    }
  }, []);

  // Fetch automations when the tab is selected
  useEffect(() => {
    if (tab === 4 && !automations) fetchAutomations();
  }, [tab, automations, fetchAutomations]);

  // Fetch AI models cache when Application Settings tab is active
  const fetchAiModels = useCallback(async (refresh = false) => {
    setAiModelsLoading(true);
    try {
      const data = await settingsAPI.getAiModels(refresh);
      setAiModelsCache(data.models || {});
    } catch {
      // Silently fail — model dropdown will just allow free-text
    } finally {
      setAiModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 2) fetchAiModels();
  }, [tab, fetchAiModels]);

  // Auto-save Application Settings (tab 2) on change with debounce
  useEffect(() => {
    // Only auto-save on Application Settings tab
    if (tab !== 2 && tab !== 3) return;
    // Skip if no settings loaded yet
    if (Object.keys(savedSettingsRef.current).length === 0) return;
    // Compute changed keys
    const changed: { key: string; value: string }[] = [];
    for (const s of appSettings) {
      const saved = savedSettingsRef.current[s.key] ?? (s.value ?? '');
      if (settingsForm[s.key] !== saved) {
        changed.push({ key: s.key, value: settingsForm[s.key] });
      }
    }
    if (changed.length === 0) return;

    const timer = setTimeout(async () => {
      setSettingsSaving(true);
      try {
        const updated = await settingsAPI.bulkUpdate(changed);
        setAppSettings(updated);
        const form: Record<string, string> = {};
        for (const s of updated as AppSetting[]) {
          form[s.key] = s.value ?? '';
          if (s.key === 'session_timeout_minutes') {
            localStorage.setItem('sessionTimeoutMinutes', s.value ?? '30');
          }
        }
        setSettingsForm(form);
        savedSettingsRef.current = form;
        setSnackbar({ open: true, message: `${changed.length} setting(s) saved automatically` });
      } catch (err: any) {
        setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to auto-save settings' });
      } finally {
        setSettingsSaving(false);
      }
    }, 1500);

    return () => clearTimeout(timer);
  }, [settingsForm, appSettings, tab]);

  /* ── profile save ── */
  const handleSaveProfile = async () => {
    setProfileSaving(true);
    try {
      const data: Record<string, any> = {};
      for (const k of ['full_name', 'phone', 'date_of_birth', 'gender', 'address', 'city', 'state', 'pincode'] as const) {
        const v = (profile as any)[k];
        if (v !== undefined && v !== null) data[k] = v;
      }
      await authAPI.updateProfile(data);
      setSnackbar({ open: true, message: 'Profile saved successfully' });
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to save profile' });
    } finally {
      setProfileSaving(false);
    }
  };

  /* ── employment save ── */
  const handleSaveEmployment = async () => {
    setEmploymentSaving(true);
    try {
      const data: Record<string, any> = {};
      if (employment.is_employed !== undefined && employment.is_employed !== null) {
        data['is_employed'] = employment.is_employed;
      }
      for (const k of ['employer_name', 'date_of_joining', 'basic_salary', 'da_percentage', 'pf_employee_pct', 'pf_employer_pct'] as const) {
        const v = (employment as any)[k];
        if (v !== undefined && v !== null) data[k] = v;
      }
      await authAPI.updateProfile(data);
      setSnackbar({ open: true, message: 'Employment details saved successfully' });
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to save' });
    } finally {
      setEmploymentSaving(false);
    }
  };

  const handleResetSettings = async () => {
    if (!window.confirm('Reset all application settings to their defaults? This will also clear any saved API keys.')) return;
    setResetting(true);
    try {
      const updated = await settingsAPI.reset();
      setAppSettings(updated);
      const form: Record<string, string> = {};
      for (const s of updated as AppSetting[]) {
        form[s.key] = s.value ?? '';
        if (s.key === 'session_timeout_minutes') {
          localStorage.setItem('sessionTimeoutMinutes', s.value ?? '30');
        }
      }
      setSettingsForm(form);
      savedSettingsRef.current = form;
      setSnackbar({ open: true, message: 'Settings reset to defaults' });
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to reset' });
    } finally {
      setResetting(false);
    }
  };

  /* ── computed salary preview ── */
  const basicSalary = employment.basic_salary || 0;
  const daPct = employment.da_percentage || 0;
  const pfEmpPct = employment.pf_employee_pct ?? 12;
  const pfErPct = employment.pf_employer_pct ?? 12;
  const basicPlusDa = basicSalary + (basicSalary * daPct / 100);
  const monthlyEmployeePF = basicSalary * pfEmpPct / 100;
  const monthlyEmployerPF = basicSalary * pfErPct / 100;
  const dojStr = employment.date_of_joining;
  const yearsOfService = dojStr ? Math.max(0, (Date.now() - new Date(dojStr).getTime()) / (365.25 * 24 * 60 * 60 * 1000)) : 0;
  const completedYears = Math.floor(yearsOfService);
  const gratuityAmount = completedYears >= 5 ? Math.min((basicPlusDa * 15 * completedYears) / 26, 2000000) : 0;

  /* ── helpers ── */
  const utcToIst = (h: number, m: number) => {
    const d = new Date(Date.UTC(2024, 0, 1, h, m));
    return d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true });
  };

  /** Build a human-readable schedule summary for a scheduler task */
  const schedSummary = (t: SchedulerTask): string => {
    const k = t.keys;
    if (k.count) return `${settingsForm[k.count] ?? '—'} assets`;
    if (k.interval_minutes) return `Every ${settingsForm[k.interval_minutes] ?? '—'} min`;
    if (k.ist_hour) return `${settingsForm[k.ist_hour] ?? '—'}:00 IST`;
    const h = k.hour ? parseInt(settingsForm[k.hour] ?? '0') : 0;
    const m = k.minute ? parseInt(settingsForm[k.minute] ?? '0') : 0;
    const timeStr = utcToIst(h, m);
    if (t.freq === 'annual') {
      const mo = settingsForm[k.month ?? ''] ?? '—';
      const dy = settingsForm[k.day ?? ''] ?? '—';
      return `${mo}/${dy} at ${timeStr}`;
    }
    if (t.freq === 'monthly' || t.freq === 'bimonthly') {
      const dy = settingsForm[k.day ?? ''] ?? '1';
      return `Day ${dy} at ${timeStr}`;
    }
    if (t.freq === 'weekly') {
      const dow = settingsForm[k.day_of_week ?? ''] ?? 'mon';
      const dayLabel = WEEKDAY_OPTIONS.find(w => w.value === dow)?.label ?? dow;
      return `${dayLabel} at ${timeStr}`;
    }
    return timeStr;
  };

  const selectedProvider = settingsForm['ai_news_provider'] ?? 'openai';

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
      <CircularProgress />
    </Box>
  );

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Application Setup</Typography>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }} variant="scrollable" scrollButtons="auto">
        <Tab label="Profile" />
        <Tab label="Employment & Salary" />
        <Tab label="Application Settings" />
        <Tab label="Scheduler Setup" />
        <Tab label="Automation Setup" />
      </Tabs>

      {/* ════════════ TAB 0 — Profile ════════════ */}
      {tab === 0 && (
        <Box>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Personal Information</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Full Name" value={profile.full_name || ''}
                    onChange={e => setProfile({ ...profile, full_name: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Email" value={profile.email || ''} disabled
                    helperText="Email cannot be changed here" />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Phone" value={profile.phone || ''}
                    onChange={e => setProfile({ ...profile, phone: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Date of Birth" type="date" InputLabelProps={{ shrink: true }}
                    value={profile.date_of_birth || ''}
                    onChange={e => setProfile({ ...profile, date_of_birth: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Gender</InputLabel>
                    <Select value={profile.gender || ''} label="Gender"
                      onChange={e => setProfile({ ...profile, gender: e.target.value })}>
                      <MenuItem value="">Prefer not to say</MenuItem>
                      <MenuItem value="Male">Male</MenuItem>
                      <MenuItem value="Female">Female</MenuItem>
                      <MenuItem value="Other">Other</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Address</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField fullWidth label="Address" multiline rows={2} value={profile.address || ''}
                    onChange={e => setProfile({ ...profile, address: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="City" value={profile.city || ''}
                    onChange={e => setProfile({ ...profile, city: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="State" value={profile.state || ''}
                    onChange={e => setProfile({ ...profile, state: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField fullWidth label="Pincode" value={profile.pincode || ''}
                    onChange={e => setProfile({ ...profile, pincode: e.target.value })} />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Button variant="contained" startIcon={profileSaving ? <CircularProgress size={20} /> : <Save />}
            onClick={handleSaveProfile} disabled={profileSaving}>
            Save Profile
          </Button>
        </Box>
      )}

      {/* ════════════ TAB 1 — Employment & Salary ════════════ */}
      {tab === 1 && (
        <Box>
          <Alert severity="info" sx={{ mb: 3 }}>
            Your salary and employment details are used to automatically calculate your <strong>Gratuity</strong> eligibility
            and amount each month, and to track your <strong>PF (Provident Fund)</strong> contributions based on your basic salary.
            These values help keep your retirement savings overview accurate and up-to-date.
          </Alert>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Employment Details</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={employment.is_employed ?? true}
                        onChange={e => setEmployment({ ...employment, is_employed: e.target.checked })}
                        color="primary"
                      />
                    }
                    label="Currently Employed"
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', ml: 6, mt: -0.5 }}>
                    When enabled, PF contributions and Gratuity are automatically calculated and updated each month.
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Employer Name" value={employment.employer_name || ''}
                    onChange={e => setEmployment({ ...employment, employer_name: e.target.value })} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Date of Joining" type="date" InputLabelProps={{ shrink: true }}
                    value={employment.date_of_joining || ''}
                    onChange={e => setEmployment({ ...employment, date_of_joining: e.target.value })} />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Salary & PF Configuration</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Basic Monthly Salary" type="number"
                    InputProps={{ startAdornment: <InputAdornment position="start">&#8377;</InputAdornment> }}
                    value={employment.basic_salary ?? ''}
                    onChange={e => setEmployment({ ...employment, basic_salary: parseFloat(e.target.value) || 0 })} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Dearness Allowance (%)" type="number"
                    value={employment.da_percentage ?? ''}
                    onChange={e => setEmployment({ ...employment, da_percentage: parseFloat(e.target.value) || 0 })}
                    helperText="Set to 0 if DA is not applicable" />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Employee PF Contribution (%)" type="number"
                    value={employment.pf_employee_pct ?? 12}
                    onChange={e => setEmployment({ ...employment, pf_employee_pct: parseFloat(e.target.value) || 0 })}
                    helperText="Standard is 12% of basic salary" />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth label="Employer PF Contribution (%)" type="number"
                    value={employment.pf_employer_pct ?? 12}
                    onChange={e => setEmployment({ ...employment, pf_employer_pct: parseFloat(e.target.value) || 0 })}
                    helperText="Standard is 12% of basic salary (3.67% EPF + 8.33% EPS)" />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Computed preview */}
          {basicSalary > 0 && (
            <Card sx={{ mb: 3, bgcolor: 'action.hover' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>Computed Preview</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="body2" color="text.secondary">Monthly Employee PF</Typography>
                    <Typography variant="h6">{formatCurrency(monthlyEmployeePF)}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatCurrency(basicSalary)} x {pfEmpPct}%
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="body2" color="text.secondary">Monthly Employer PF</Typography>
                    <Typography variant="h6">{formatCurrency(monthlyEmployerPF)}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatCurrency(basicSalary)} x {pfErPct}%
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="body2" color="text.secondary">Estimated Gratuity</Typography>
                    <Typography variant="h6" color={gratuityAmount > 0 ? 'success.main' : 'text.secondary'}>
                      {gratuityAmount > 0 ? formatCurrency(gratuityAmount) : 'Not yet eligible'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {completedYears > 0 ? `${completedYears} year(s) of service` : 'Requires 5+ years'}
                      {completedYears >= 5 ? ` | (${formatCurrency(basicPlusDa)} x 15 x ${completedYears}) / 26` : ''}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}

          <Button variant="contained" startIcon={employmentSaving ? <CircularProgress size={20} /> : <Save />}
            onClick={handleSaveEmployment} disabled={employmentSaving}>
            Save Employment Details
          </Button>
        </Box>
      )}

      {/* ════════════ TAB 2 — Application Settings ════════════ */}
      {tab === 2 && (
        <Box>
          {/* AI Provider Configuration */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6">AI Provider Configuration</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Tooltip title="Refresh available models from all providers">
                    <IconButton size="small" onClick={() => fetchAiModels(true)} disabled={aiModelsLoading}>
                      <Refresh fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Button variant="contained" size="small" startIcon={<AddIcon />}
                    onClick={() => {
                      setAiEditingProvider(null);
                      setAiDialogForm({ provider: '', api_key: '', model: '', endpoint: '', set_primary: true });
                      setAiDialogOpen(true);
                    }}>
                    Add API Key
                  </Button>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure AI providers for portfolio news summaries. The primary provider is tried first.
                If it fails, the system automatically falls back to the next configured provider.
              </Typography>

              {/* Provider table */}
              {(() => {
                const configuredProviders = AI_PROVIDERS.filter(
                  p => (settingsForm[AI_PROVIDERS_MAP[p.value]?.key] ?? '').length > 0
                );
                return configuredProviders.length === 0 ? (
                  <Alert severity="info">
                    No AI provider keys configured. Click "Add API Key" to add your first provider, or keys from the server .env file will be used.
                  </Alert>
                ) : (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell align="center"><strong>Primary</strong></TableCell>
                          <TableCell><strong>Provider</strong></TableCell>
                          <TableCell><strong>Role</strong></TableCell>
                          <TableCell><strong>API Key</strong></TableCell>
                          <TableCell><strong>Model</strong></TableCell>
                          <TableCell><strong>Endpoint</strong></TableCell>
                          <TableCell align="center"><strong>Actions</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {configuredProviders.map(p => {
                          const keyVal = settingsForm[AI_PROVIDERS_MAP[p.value].key] ?? '';
                          const modelVal = settingsForm[`ai_${p.value}_model`] ?? '';
                          const endpointVal = settingsForm[`ai_${p.value}_endpoint`] ?? '';
                          const isPrimary = p.value === selectedProvider;
                          return (
                            <TableRow key={p.value} selected={isPrimary}>
                              <TableCell align="center" padding="checkbox">
                                <Tooltip title="Set as primary provider">
                                  <Radio size="small" checked={isPrimary}
                                    onChange={() => setSettingsForm({ ...settingsForm, ai_news_provider: p.value })} />
                                </Tooltip>
                              </TableCell>
                              <TableCell>{p.label}</TableCell>
                              <TableCell>
                                {isPrimary
                                  ? <Chip label="Primary" color="success" size="small" />
                                  : <Chip label="Fallback" color="default" size="small" variant="outlined" />}
                              </TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                                {keyVal.startsWith('***') ? keyVal : '••••••••' + keyVal.slice(-4)}
                              </TableCell>
                              <TableCell>{modelVal || <Typography variant="body2" color="text.secondary">Default</Typography>}</TableCell>
                              <TableCell>{endpointVal || <Typography variant="body2" color="text.secondary">Default</Typography>}</TableCell>
                              <TableCell align="center">
                                <Tooltip title="Edit">
                                  <IconButton size="small" onClick={async () => {
                                    setAiEditingProvider(p.value);
                                    let realKey = '';
                                    if (keyVal.length > 0) {
                                      try { realKey = await settingsAPI.getSecretValue(AI_PROVIDERS_MAP[p.value].key); } catch { /* keep blank */ }
                                    }
                                    setAiDialogForm({
                                      provider: p.value,
                                      api_key: realKey,
                                      model: modelVal,
                                      endpoint: endpointVal,
                                      set_primary: isPrimary,
                                    });
                                    setAiDialogOpen(true);
                                  }}>
                                    <EditIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Remove">
                                  <IconButton size="small" color="error" onClick={() => {
                                    setSettingsForm(prev => ({
                                      ...prev,
                                      [AI_PROVIDERS_MAP[p.value].key]: '',
                                      [`ai_${p.value}_model`]: '',
                                      [`ai_${p.value}_endpoint`]: '',
                                    }));
                                  }}>
                                    <DeleteIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                );
              })()}
            </CardContent>
          </Card>

          {/* AI Provider Dialog */}
          <Dialog open={aiDialogOpen} onClose={() => setAiDialogOpen(false)} maxWidth="sm" fullWidth>
            <DialogTitle>{aiEditingProvider ? `Edit ${AI_PROVIDERS.find(p => p.value === aiEditingProvider)?.label}` : 'Add AI Provider Key'}</DialogTitle>
            <DialogContent>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                <TextField
                  select label="AI Provider" value={aiDialogForm.provider}
                  onChange={e => setAiDialogForm({ ...aiDialogForm, provider: e.target.value })}
                  fullWidth required disabled={!!aiEditingProvider}
                >
                  {AI_PROVIDERS
                    .filter(p => !!aiEditingProvider || !(settingsForm[AI_PROVIDERS_MAP[p.value]?.key] ?? '').length)
                    .map(p => (
                      <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                    ))}
                </TextField>

                <TextField
                  label="API Key" fullWidth required
                  type={showApiKeys['ai_dialog_key'] ? 'text' : 'password'}
                  value={aiDialogForm.api_key}
                  onChange={e => setAiDialogForm({ ...aiDialogForm, api_key: e.target.value })}
                  placeholder={aiEditingProvider ? 'Enter new key or leave blank to keep existing' : 'Enter API key'}
                  helperText={aiEditingProvider ? 'Leave blank to keep the existing key unchanged' : undefined}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => toggleApiKeyVisibility('ai_dialog_key')} edge="end">
                          {showApiKeys['ai_dialog_key'] ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />

                {(() => {
                  const provModels = aiDialogForm.provider ? (aiModelsCache[aiDialogForm.provider] || []) : [];
                  return provModels.length > 0 ? (
                    <TextField
                      select label="Model" fullWidth
                      value={provModels.includes(aiDialogForm.model) ? aiDialogForm.model : ''}
                      onChange={e => setAiDialogForm({ ...aiDialogForm, model: e.target.value })}
                      helperText={aiModelsLoading ? 'Loading models...' : 'Select a model or leave blank for provider default'}
                    >
                      <MenuItem value="">
                        <em>Default</em>
                      </MenuItem>
                      {provModels.map(m => (
                        <MenuItem key={m} value={m}>{m}</MenuItem>
                      ))}
                    </TextField>
                  ) : (
                    <TextField
                      label="Model Name (optional)" fullWidth
                      value={aiDialogForm.model}
                      onChange={e => setAiDialogForm({ ...aiDialogForm, model: e.target.value })}
                      helperText={aiModelsLoading ? 'Loading models...' : 'Enter model name or leave blank for provider default'}
                    />
                  );
                })()}

                <TextField
                  label="API Endpoint (optional)" fullWidth
                  value={aiDialogForm.endpoint}
                  onChange={e => setAiDialogForm({ ...aiDialogForm, endpoint: e.target.value })}
                  helperText="Override for proxies or custom deployments"
                />

                <FormControlLabel
                  control={
                    <Switch checked={aiDialogForm.set_primary}
                      onChange={e => setAiDialogForm({ ...aiDialogForm, set_primary: e.target.checked })} />
                  }
                  label="Set as primary provider"
                />
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setAiDialogOpen(false)}>Cancel</Button>
              <Button variant="contained" disabled={!aiDialogForm.provider || (!aiEditingProvider && !aiDialogForm.api_key)}
                onClick={() => {
                  const prov = aiDialogForm.provider;
                  const updates: Record<string, string> = {};
                  if (aiDialogForm.api_key) {
                    updates[AI_PROVIDERS_MAP[prov].key] = aiDialogForm.api_key;
                  }
                  updates[`ai_${prov}_model`] = aiDialogForm.model;
                  updates[`ai_${prov}_endpoint`] = aiDialogForm.endpoint;
                  if (aiDialogForm.set_primary) {
                    updates['ai_news_provider'] = prov;
                  }
                  setSettingsForm(prev => ({ ...prev, ...updates }));
                  setAiDialogOpen(false);
                }}>
                {aiEditingProvider ? 'Update' : 'Add'}
              </Button>
            </DialogActions>
          </Dialog>

          {/* Market Data API Keys */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Market Data API Keys</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                API keys for external market data providers. Keys from the server .env file are used when not configured here.
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Provider</strong></TableCell>
                      <TableCell><strong>Description</strong></TableCell>
                      <TableCell><strong>API Key</strong></TableCell>
                      <TableCell align="center"><strong>Actions</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {MARKET_API_KEY_FIELDS.map(({ key, label, helperText }) => {
                      const keyVal = settingsForm[key] ?? '';
                      const hasKey = keyVal.length > 0;
                      return (
                        <TableRow key={key}>
                          <TableCell><Typography variant="body2" fontWeight="medium">{label}</Typography></TableCell>
                          <TableCell><Typography variant="body2" color="text.secondary">{helperText}</Typography></TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                            {hasKey
                              ? (keyVal.startsWith('***') ? keyVal : '••••••••' + keyVal.slice(-4))
                              : <Chip label="Not Set" size="small" variant="outlined" color="warning" />}
                          </TableCell>
                          <TableCell align="center">
                            <Tooltip title={hasKey ? 'Edit API Key' : 'Add API Key'}>
                              <IconButton size="small" onClick={async () => {
                                setMktEditingKey(key);
                                let realKey = '';
                                if (hasKey) {
                                  try { realKey = await settingsAPI.getSecretValue(key); } catch { /* keep blank */ }
                                }
                                setMktDialogForm({ api_key: realKey });
                                setMktDialogOpen(true);
                              }}>
                                {hasKey ? <EditIcon fontSize="small" /> : <AddIcon fontSize="small" color="primary" />}
                              </IconButton>
                            </Tooltip>
                            {hasKey && (
                              <Tooltip title="Remove API Key">
                                <IconButton size="small" color="error" onClick={() => {
                                  setSettingsForm(prev => ({ ...prev, [key]: '' }));
                                }}>
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* Market Data Key Dialog */}
          <Dialog open={mktDialogOpen} onClose={() => setMktDialogOpen(false)} maxWidth="sm" fullWidth>
            <DialogTitle>
              {(() => {
                const field = MARKET_API_KEY_FIELDS.find(f => f.key === mktEditingKey);
                const hasExisting = (settingsForm[mktEditingKey ?? ''] ?? '').length > 0;
                return `${hasExisting ? 'Edit' : 'Add'} ${field?.label ?? 'API Key'}`;
              })()}
            </DialogTitle>
            <DialogContent>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {MARKET_API_KEY_FIELDS.find(f => f.key === mktEditingKey)?.helperText}
                </Typography>
                <TextField
                  label="API Key" fullWidth
                  type={showApiKeys['mkt_dialog_key'] ? 'text' : 'password'}
                  value={mktDialogForm.api_key}
                  onChange={e => setMktDialogForm({ api_key: e.target.value })}
                  placeholder={(settingsForm[mktEditingKey ?? ''] ?? '').length > 0
                    ? 'Enter new key or leave blank to keep existing' : 'Enter API key'}
                  helperText={(settingsForm[mktEditingKey ?? ''] ?? '').length > 0
                    ? 'Leave blank to keep the existing key unchanged' : undefined}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => toggleApiKeyVisibility('mkt_dialog_key')} edge="end">
                          {showApiKeys['mkt_dialog_key'] ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setMktDialogOpen(false)}>Cancel</Button>
              <Button variant="contained"
                disabled={!mktDialogForm.api_key && !(settingsForm[mktEditingKey ?? ''] ?? '').length}
                onClick={() => {
                  if (mktEditingKey && mktDialogForm.api_key) {
                    setSettingsForm(prev => ({ ...prev, [mktEditingKey]: mktDialogForm.api_key }));
                  }
                  setMktDialogOpen(false);
                }}>
                Save
              </Button>
            </DialogActions>
          </Dialog>

          {/* Session */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Session</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField fullWidth size="small" type="number" label="Session Timeout (minutes)"
                    value={settingsForm['session_timeout_minutes'] ?? ''}
                    onChange={e => setSettingsForm({ ...settingsForm, session_timeout_minutes: e.target.value })}
                    inputProps={{ min: 5, max: 1440 }}
                    helperText="Idle time before requiring re-login" />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {settingsSaving && <CircularProgress size={20} />}
            {settingsSaving && <Typography variant="body2" color="text.secondary">Saving...</Typography>}
            <Button variant="outlined" color="warning" startIcon={resetting ? <CircularProgress size={20} /> : <RestartAlt />}
              onClick={handleResetSettings} disabled={settingsSaving || resetting}>
              Reset to Defaults
            </Button>
          </Box>
        </Box>
      )}

      {/* ════════════ TAB 3 — Scheduler Setup ════════════ */}
      {tab === 3 && (
        <Box>
          {(['portfolio', 'market', 'contribution'] as const).map(cat => (
            <Card sx={{ mb: 3 }} key={cat}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>{CATEGORY_LABELS[cat]} Tasks</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Task</strong></TableCell>
                        <TableCell><strong>Description</strong></TableCell>
                        <TableCell><strong>Frequency</strong></TableCell>
                        <TableCell><strong>Schedule</strong></TableCell>
                        <TableCell align="center"><strong>Edit</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {SCHEDULER_TASKS.filter(t => t.category === cat).map(t => (
                        <TableRow key={t.id}>
                          <TableCell><Typography variant="body2" fontWeight="medium">{t.name}</Typography></TableCell>
                          <TableCell><Typography variant="body2" color="text.secondary">{t.description}</Typography></TableCell>
                          <TableCell>
                            <Chip label={FREQ_LABELS[t.freq]} color={FREQ_COLORS[t.freq]} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell><Typography variant="body2">{schedSummary(t)}</Typography></TableCell>
                          <TableCell align="center">
                            <IconButton size="small" onClick={() => { setSchedEditingTask(t); setSchedDialogOpen(true); }}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          ))}

          {/* Scheduler Edit Dialog */}
          <Dialog open={schedDialogOpen} onClose={() => setSchedDialogOpen(false)} maxWidth="sm" fullWidth>
            {schedEditingTask && (() => {
              const t = schedEditingTask;
              const k = t.keys;
              return (
                <>
                  <DialogTitle>Edit Schedule — {t.name}</DialogTitle>
                  <DialogContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                      <Typography variant="body2" color="text.secondary">{t.description}</Typography>

                      <TextField select label="Frequency" value={t.freq} disabled fullWidth size="small">
                        {Object.entries(FREQ_LABELS).map(([v, l]) => (
                          <MenuItem key={v} value={v}>{l}</MenuItem>
                        ))}
                      </TextField>

                      {/* Interval: minutes */}
                      {k.interval_minutes && (
                        <TextField type="number" label="Interval (minutes)" fullWidth size="small"
                          value={settingsForm[k.interval_minutes] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, [k.interval_minutes!]: e.target.value })}
                          inputProps={{ min: 5, max: 1440 }}
                          helperText="How often this task runs (in minutes)" />
                      )}

                      {/* IST hour (news alerts) */}
                      {k.ist_hour && (
                        <TextField type="number" label="Hour (IST)" fullWidth size="small"
                          value={settingsForm[k.ist_hour] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, [k.ist_hour!]: e.target.value })}
                          inputProps={{ min: 0, max: 23 }}
                          helperText="Hour in IST (0-23) when this task runs" />
                      )}

                      {/* Count (non-schedule config) */}
                      {k.count && (
                        <TextField type="number" label="Count" fullWidth size="small"
                          value={settingsForm[k.count] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, [k.count!]: e.target.value })}
                          inputProps={{ min: 1, max: 100 }}
                          helperText="Number of items to process per run" />
                      )}

                      {/* Annual: month + day */}
                      {t.freq === 'annual' && k.month && (
                        <TextField type="number" label="Month" fullWidth size="small"
                          value={settingsForm[k.month] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, [k.month!]: e.target.value })}
                          inputProps={{ min: 1, max: 12 }}
                          helperText="Month (1-12)" />
                      )}

                      {/* Weekly: day of week */}
                      {k.day_of_week && (
                        <TextField select label="Day of Week" fullWidth size="small"
                          value={settingsForm[k.day_of_week] ?? 'mon'}
                          onChange={e => setSettingsForm({ ...settingsForm, [k.day_of_week!]: e.target.value })}>
                          {WEEKDAY_OPTIONS.map(d => (
                            <MenuItem key={d.value} value={d.value}>{d.label}</MenuItem>
                          ))}
                        </TextField>
                      )}

                      {/* Monthly / bimonthly / annual: day of month */}
                      {k.day && (t.freq === 'monthly' || t.freq === 'bimonthly' || t.freq === 'annual') && (
                        <TextField type="number" label="Day of Month" fullWidth size="small"
                          value={settingsForm[k.day] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, [k.day!]: e.target.value })}
                          inputProps={{ min: 1, max: 28 }}
                          helperText="Day of the month (1-28)" />
                      )}

                      {/* UTC hour + minute (for daily/weekly/monthly/bimonthly tasks that have hour key) */}
                      {k.hour && !k.ist_hour && (
                        <Box sx={{ display: 'flex', gap: 2 }}>
                          <TextField type="number" label="Hour (UTC)" fullWidth size="small"
                            value={settingsForm[k.hour] ?? ''}
                            onChange={e => setSettingsForm({ ...settingsForm, [k.hour!]: e.target.value })}
                            inputProps={{ min: 0, max: 23 }}
                            helperText={`IST: ${utcToIst(parseInt(settingsForm[k.hour] ?? '0'), parseInt(settingsForm[k.minute ?? ''] ?? '0'))}`} />
                          {k.minute && (
                            <TextField type="number" label="Minute" fullWidth size="small"
                              value={settingsForm[k.minute] ?? ''}
                              onChange={e => setSettingsForm({ ...settingsForm, [k.minute!]: e.target.value })}
                              inputProps={{ min: 0, max: 59 }} />
                          )}
                        </Box>
                      )}
                    </Box>
                  </DialogContent>
                  <DialogActions>
                    <Button onClick={() => setSchedDialogOpen(false)}>Close</Button>
                  </DialogActions>
                </>
              );
            })()}
          </Dialog>

          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {settingsSaving && <CircularProgress size={20} />}
            {settingsSaving && <Typography variant="body2" color="text.secondary">Saving...</Typography>}
            <Button variant="outlined" color="warning" startIcon={resetting ? <CircularProgress size={20} /> : <RestartAlt />}
              onClick={handleResetSettings} disabled={settingsSaving || resetting}>
              Reset to Defaults
            </Button>
          </Box>
        </Box>
      )}

      {/* ════════════ TAB 4 — Automation Setup ════════════ */}
      {tab === 4 && (
        <Box>
          <Alert severity="info" sx={{ mb: 3 }}>
            This page shows all automations configured in your account — both system-level scheduled tasks
            and per-asset automations like auto-generated FD interest or RD installments.
          </Alert>

          {automationsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : automations ? (
            <>
              {/* System Automations */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Schedule color="primary" />
                    <Typography variant="h6">System Automations</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Background tasks that run automatically to keep your portfolio data up-to-date.
                  </Typography>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>Automation</strong></TableCell>
                          <TableCell><strong>Description</strong></TableCell>
                          <TableCell align="center"><strong>Status</strong></TableCell>
                          <TableCell align="right"><strong>Schedule</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {automations.system_automations
                          .filter(a => a.category === 'scheduler')
                          .map((a, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                <Typography variant="body2" fontWeight="medium">{a.name}</Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">{a.description}</Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Chip label={a.enabled ? 'Active' : 'Inactive'}
                                  color={a.enabled ? 'success' : 'default'} size="small" />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">{a.schedule}</Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Market Insight Automations */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Public color="primary" />
                    <Typography variant="h6">Market Insight Automations</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Scheduled data fetches for the Market Insight and Liquidity Insight pages.
                  </Typography>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>Automation</strong></TableCell>
                          <TableCell><strong>Description</strong></TableCell>
                          <TableCell align="center"><strong>Status</strong></TableCell>
                          <TableCell align="right"><strong>Schedule</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {automations.system_automations
                          .filter(a => a.category === 'market_insight')
                          .map((a, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                <Typography variant="body2" fontWeight="medium">{a.name}</Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">{a.description}</Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Chip label={a.enabled ? 'Active' : 'Inactive'}
                                  color={a.enabled ? 'success' : 'default'} size="small" />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">{a.schedule}</Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Employment Automations */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Work color="primary" />
                    <Typography variant="h6">Employment-Based Automations</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Automated calculations based on your employment and salary configuration.
                  </Typography>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>Automation</strong></TableCell>
                          <TableCell><strong>Description</strong></TableCell>
                          <TableCell align="center"><strong>Status</strong></TableCell>
                          <TableCell align="right"><strong>Schedule</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {automations.system_automations
                          .filter(a => a.category === 'employment')
                          .map((a, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                <Typography variant="body2" fontWeight="medium">{a.name}</Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">{a.description}</Typography>
                                {a.prerequisite && !a.enabled && (
                                  <Typography variant="caption" color="warning.main">{a.prerequisite}</Typography>
                                )}
                              </TableCell>
                              <TableCell align="center">
                                <Chip label={a.enabled ? 'Active' : 'Inactive'}
                                  color={a.enabled ? 'success' : 'default'} size="small" />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">{a.schedule}</Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Asset Automations */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <AccountBalance color="primary" />
                    <Typography variant="h6">Asset-Level Automations</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Per-asset automations for Fixed Deposits and Recurring Deposits. Toggle auto-update from the respective asset pages.
                  </Typography>
                  {automations.asset_automations.length === 0 ? (
                    <Alert severity="info" variant="outlined">
                      No Fixed Deposits or Recurring Deposits found. Add FD/RD assets and enable auto-update to see them here.
                    </Alert>
                  ) : (
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell><strong>Asset</strong></TableCell>
                            <TableCell><strong>Type</strong></TableCell>
                            <TableCell><strong>Automation</strong></TableCell>
                            <TableCell><strong>Details</strong></TableCell>
                            <TableCell align="center"><strong>Auto-Update</strong></TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {automations.asset_automations.map((a, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                <Typography variant="body2" fontWeight="medium">{a.asset_name}</Typography>
                                {a.details.bank_name && (
                                  <Typography variant="caption" color="text.secondary">{a.details.bank_name}</Typography>
                                )}
                              </TableCell>
                              <TableCell>
                                <Chip label={a.asset_type} size="small" variant="outlined" />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">{a.automation}</Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2">
                                  {a.details.interest_rate ? `${a.details.interest_rate}% ` : ''}
                                  {a.details.interest_type || ''}
                                  {a.details.monthly_installment ? `₹${Number(a.details.monthly_installment).toLocaleString('en-IN')}/mo` : ''}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Chip label={a.enabled ? 'Enabled' : 'Disabled'}
                                  color={a.enabled ? 'success' : 'default'} size="small" />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </CardContent>
              </Card>

              <Button variant="outlined" onClick={fetchAutomations} disabled={automationsLoading}>
                Refresh
              </Button>
            </>
          ) : null}
        </Box>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })} message={snackbar.message} />
    </Box>
  );
};

export default Settings;
