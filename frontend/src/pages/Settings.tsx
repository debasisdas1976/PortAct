import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button, Grid, Alert,
  CircularProgress, Snackbar, Tabs, Tab, MenuItem, Select,
  FormControl, FormControlLabel, Switch, InputLabel, InputAdornment, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, IconButton,
  Accordion, AccordionSummary, AccordionDetails,
} from '@mui/material';
import { Save, RestartAlt, Visibility, VisibilityOff, ExpandMore } from '@mui/icons-material';
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

const API_KEY_FIELDS = [
  { key: 'ai_openai_api_key', label: 'OpenAI API Key', provider: 'openai' },
  { key: 'ai_grok_api_key', label: 'Grok API Key', provider: 'grok' },
  { key: 'ai_gemini_api_key', label: 'Google Gemini API Key', provider: 'gemini' },
  { key: 'ai_anthropic_api_key', label: 'Anthropic Claude API Key', provider: 'anthropic' },
  { key: 'ai_deepseek_api_key', label: 'DeepSeek API Key', provider: 'deepseek' },
  { key: 'ai_mistral_api_key', label: 'Mistral API Key', provider: 'mistral' },
];

/* ─────────────────── component ─────────────────── */

const Settings: React.FC = () => {
  const [tab, setTab] = useState(0);
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

  // API key visibility toggles
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});

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
      for (const s of settings as AppSetting[]) form[s.key] = s.value ?? '';
      setSettingsForm(form);
    } catch {
      setSnackbar({ open: true, message: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

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

  /* ── app settings save ── */
  const handleSaveSettings = async () => {
    setSettingsSaving(true);
    try {
      const changed: { key: string; value: string }[] = [];
      for (const s of appSettings) {
        if (settingsForm[s.key] !== (s.value ?? '')) {
          changed.push({ key: s.key, value: settingsForm[s.key] });
        }
      }
      if (changed.length === 0) {
        setSnackbar({ open: true, message: 'No changes to save' });
        setSettingsSaving(false);
        return;
      }
      const updated = await settingsAPI.bulkUpdate(changed);
      setAppSettings(updated);
      const form: Record<string, string> = {};
      for (const s of updated as AppSetting[]) form[s.key] = s.value ?? '';
      setSettingsForm(form);
      setSnackbar({ open: true, message: `${changed.length} setting(s) updated. Schedulers rescheduled.` });
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to save settings' });
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleResetSettings = async () => {
    if (!window.confirm('Reset all application settings to their defaults? This will also clear any saved API keys.')) return;
    setResetting(true);
    try {
      const updated = await settingsAPI.reset();
      setAppSettings(updated);
      const form: Record<string, string> = {};
      for (const s of updated as AppSetting[]) form[s.key] = s.value ?? '';
      setSettingsForm(form);
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

  const selectedProvider = settingsForm['ai_news_provider'] ?? 'openai';

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
      <CircularProgress />
    </Box>
  );

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Application Setup</Typography>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Profile" />
        <Tab label="Employment & Salary" />
        <Tab label="Application Settings" />
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
          {/* Scheduled Tasks */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>Scheduled Tasks</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                These background tasks run automatically to keep your portfolio data up-to-date.
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Task</strong></TableCell>
                      <TableCell><strong>Description</strong></TableCell>
                      <TableCell align="right" sx={{ minWidth: 160 }}><strong>Schedule</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {/* Price Updates */}
                    <TableRow>
                      <TableCell><Typography variant="body2" fontWeight="medium">Price Updates</Typography></TableCell>
                      <TableCell><Typography variant="body2" color="text.secondary">Auto-fetches latest prices for stocks, mutual funds, crypto, and commodities.</Typography></TableCell>
                      <TableCell align="right">
                        <TextField size="small" type="number" label="Minutes" sx={{ width: 100 }}
                          value={settingsForm['price_update_interval_minutes'] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, price_update_interval_minutes: e.target.value })}
                          inputProps={{ min: 5, max: 1440 }} />
                      </TableCell>
                    </TableRow>

                    {/* EOD Snapshot */}
                    <TableRow>
                      <TableCell><Typography variant="body2" fontWeight="medium">EOD Portfolio Snapshot</Typography></TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">Captures daily portfolio value for historical tracking and performance charts.</Typography>
                        {settingsForm['eod_snapshot_hour'] && (
                          <Typography variant="caption" color="primary">
                            IST: {utcToIst(parseInt(settingsForm['eod_snapshot_hour'] || '13'), parseInt(settingsForm['eod_snapshot_minute'] || '30'))}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                          <TextField size="small" type="number" label="Hour (UTC)" sx={{ width: 100 }}
                            value={settingsForm['eod_snapshot_hour'] ?? ''}
                            onChange={e => setSettingsForm({ ...settingsForm, eod_snapshot_hour: e.target.value })}
                            inputProps={{ min: 0, max: 23 }} />
                          <TextField size="small" type="number" label="Min" sx={{ width: 80 }}
                            value={settingsForm['eod_snapshot_minute'] ?? ''}
                            onChange={e => setSettingsForm({ ...settingsForm, eod_snapshot_minute: e.target.value })}
                            inputProps={{ min: 0, max: 59 }} />
                        </Box>
                      </TableCell>
                    </TableRow>

                    {/* Morning News */}
                    <TableRow>
                      <TableCell><Typography variant="body2" fontWeight="medium">Morning News Alerts</Typography></TableCell>
                      <TableCell><Typography variant="body2" color="text.secondary">AI-generated news alerts for your portfolio holdings (morning run).</Typography></TableCell>
                      <TableCell align="right">
                        <TextField size="small" type="number" label="Hour (IST)" sx={{ width: 100 }}
                          value={settingsForm['news_morning_hour'] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, news_morning_hour: e.target.value })}
                          inputProps={{ min: 0, max: 23 }} />
                      </TableCell>
                    </TableRow>

                    {/* Evening News */}
                    <TableRow>
                      <TableCell><Typography variant="body2" fontWeight="medium">Evening News Alerts</Typography></TableCell>
                      <TableCell><Typography variant="body2" color="text.secondary">AI-generated news alerts for your portfolio holdings (evening run).</Typography></TableCell>
                      <TableCell align="right">
                        <TextField size="small" type="number" label="Hour (IST)" sx={{ width: 100 }}
                          value={settingsForm['news_evening_hour'] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, news_evening_hour: e.target.value })}
                          inputProps={{ min: 0, max: 23 }} />
                      </TableCell>
                    </TableRow>

                    {/* News Limit */}
                    <TableRow>
                      <TableCell><Typography variant="body2" fontWeight="medium">News Coverage</Typography></TableCell>
                      <TableCell><Typography variant="body2" color="text.secondary">Number of portfolio assets analysed per scheduled news run.</Typography></TableCell>
                      <TableCell align="right">
                        <TextField size="small" type="number" label="Assets" sx={{ width: 100 }}
                          value={settingsForm['news_limit_per_user'] ?? ''}
                          onChange={e => setSettingsForm({ ...settingsForm, news_limit_per_user: e.target.value })}
                          inputProps={{ min: 1, max: 100 }} />
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* AI Configuration */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>AI Configuration</Typography>

              {/* Provider Selection */}
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>AI News Provider</InputLabel>
                    <Select value={selectedProvider} label="AI News Provider"
                      onChange={e => setSettingsForm({ ...settingsForm, ai_news_provider: e.target.value })}>
                      {AI_PROVIDERS.map(p => (
                        <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              {/* API Keys */}
              <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>API Keys</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter API keys for your AI providers. Leave blank to use keys from the server .env file.
                Existing keys are masked for security.
              </Typography>
              <Grid container spacing={2}>
                {API_KEY_FIELDS.map(({ key, label, provider }) => (
                  <Grid item xs={12} sm={6} key={key}>
                    <TextField
                      fullWidth size="small" label={label}
                      type={showApiKeys[key] ? 'text' : 'password'}
                      value={settingsForm[key] ?? ''}
                      onChange={e => setSettingsForm({ ...settingsForm, [key]: e.target.value })}
                      placeholder="Enter API key or leave blank for .env"
                      InputProps={{
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton size="small" onClick={() => toggleApiKeyVisibility(key)} edge="end">
                              {showApiKeys[key] ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          ...(provider === selectedProvider ? { borderColor: 'primary.main' } : {}),
                        },
                      }}
                      helperText={provider === selectedProvider ? 'Active provider' : undefined}
                      color={provider === selectedProvider ? 'primary' : undefined}
                      focused={provider === selectedProvider}
                    />
                  </Grid>
                ))}
              </Grid>

              {/* Advanced AI Settings */}
              <Accordion sx={{ mt: 3 }} disableGutters elevation={0} variant="outlined">
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle2">Advanced AI Settings</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Override the model name and API endpoint for the currently selected provider ({AI_PROVIDERS.find(p => p.value === selectedProvider)?.label}).
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth size="small" label="Model Name"
                        value={settingsForm[`ai_${selectedProvider}_model`] ?? ''}
                        onChange={e => setSettingsForm({ ...settingsForm, [`ai_${selectedProvider}_model`]: e.target.value })}
                        helperText="Leave default unless you need a specific model version"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth size="small" label="API Endpoint"
                        value={settingsForm[`ai_${selectedProvider}_endpoint`] ?? ''}
                        onChange={e => setSettingsForm({ ...settingsForm, [`ai_${selectedProvider}_endpoint`]: e.target.value })}
                        helperText="Override for proxies or custom deployments"
                      />
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            </CardContent>
          </Card>

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

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button variant="contained" startIcon={settingsSaving ? <CircularProgress size={20} /> : <Save />}
              onClick={handleSaveSettings} disabled={settingsSaving || resetting}>
              Save Settings
            </Button>
            <Button variant="outlined" color="warning" startIcon={resetting ? <CircularProgress size={20} /> : <RestartAlt />}
              onClick={handleResetSettings} disabled={settingsSaving || resetting}>
              Reset to Defaults
            </Button>
          </Box>
        </Box>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })} message={snackbar.message} />
    </Box>
  );
};

export default Settings;
