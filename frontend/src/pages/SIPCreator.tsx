import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Preview as PreviewIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import api, { sipCreatorAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

// ── Types ──

interface MFAsset {
  id: number;
  name: string;
  symbol: string;
  isin?: string;
  quantity: number;
  current_price: number;
  current_value: number;
  asset_type: string;
}

interface SIPTopupForm {
  topup_type: 'percentage' | 'fixed';
  topup_value: string;
}

interface SIPPeriodForm {
  sip_amount: string;
  start_date: string;
  end_date: string;
  periodicity: 'weekly' | 'monthly' | 'quarterly';
  topup_enabled: boolean;
  topup: SIPTopupForm;
}

interface SIPTransactionPreview {
  sip_number: number;
  total_sips_in_period: number;
  period_index: number;
  transaction_date: string;
  nav_date: string;
  sip_amount: number;
  nav: number;
  units: number;
  description: string;
  nav_source: string;
}

interface SIPPreviewResponse {
  asset_id: number;
  asset_name: string;
  scheme_code: string;
  total_transactions: number;
  total_amount: number;
  total_units: number;
  average_nav: number;
  transactions: SIPTransactionPreview[];
  warnings: string[];
}

// ── Helpers ──

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatNav = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 4 }).format(value);

const formatUnits = (value: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 4 }).format(value);

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

const defaultPeriod = (): SIPPeriodForm => ({
  sip_amount: '',
  start_date: '',
  end_date: '',
  periodicity: 'monthly',
  topup_enabled: false,
  topup: { topup_type: 'percentage', topup_value: '' },
});

const MF_TYPES = ['equity_mutual_fund', 'hybrid_mutual_fund', 'debt_mutual_fund'];

// ── Component ──

const SIPCreator: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();

  // State
  const [mfAssets, setMFAssets] = useState<MFAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | ''>('');
  const [periods, setPeriods] = useState<SIPPeriodForm[]>([defaultPeriod()]);
  const [preview, setPreview] = useState<SIPPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [creating, setCreating] = useState(false);

  // Load MF assets
  useEffect(() => {
    const fetchAssets = async () => {
      try {
        setLoading(true);
        const params: any = {};
        if (selectedPortfolioId) params.portfolio_id = selectedPortfolioId;
        const data = await api.get('/assets/', { params });
        const mfs = (data.data || []).filter((a: any) =>
          MF_TYPES.includes(a.asset_type?.toLowerCase())
        );
        setMFAssets(mfs);
      } catch (err) {
        notify.error(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    fetchAssets();
  }, [selectedPortfolioId]);

  // Reset preview when form changes
  useEffect(() => {
    setPreview(null);
  }, [selectedAssetId, periods]);

  // ── Period CRUD ──

  const updatePeriod = (index: number, field: string, value: any) => {
    setPeriods(prev => {
      const updated = [...prev];
      if (field.startsWith('topup.')) {
        const topupField = field.split('.')[1];
        updated[index] = {
          ...updated[index],
          topup: { ...updated[index].topup, [topupField]: value },
        };
      } else {
        updated[index] = { ...updated[index], [field]: value };
      }
      return updated;
    });
  };

  const addPeriod = () => {
    setPeriods(prev => [...prev, defaultPeriod()]);
  };

  const removePeriod = (index: number) => {
    setPeriods(prev => prev.filter((_, i) => i !== index));
  };

  // ── Validation ──

  const validateForm = (): string | null => {
    if (!selectedAssetId) return 'Please select a mutual fund';
    for (let i = 0; i < periods.length; i++) {
      const p = periods[i];
      if (!p.sip_amount || Number(p.sip_amount) <= 0) return `Period ${i + 1}: SIP amount must be greater than 0`;
      if (!p.start_date) return `Period ${i + 1}: Start date is required`;
      if (!p.end_date) return `Period ${i + 1}: End date is required`;
      if (p.end_date <= p.start_date) return `Period ${i + 1}: End date must be after start date`;
      if (p.topup_enabled && (!p.topup.topup_value || Number(p.topup.topup_value) <= 0)) {
        return `Period ${i + 1}: Topup value must be greater than 0`;
      }
    }
    return null;
  };

  // ── Build API payload ──

  const buildPayload = () => ({
    asset_id: selectedAssetId,
    periods: periods.map(p => ({
      sip_amount: Number(p.sip_amount),
      start_date: p.start_date,
      end_date: p.end_date,
      periodicity: p.periodicity,
      topup: p.topup_enabled
        ? { topup_type: p.topup.topup_type, topup_value: Number(p.topup.topup_value) }
        : null,
    })),
  });

  // ── Preview ──

  const handlePreview = async () => {
    const err = validateForm();
    if (err) { notify.error(err); return; }
    try {
      setPreviewing(true);
      const result = await sipCreatorAPI.preview(buildPayload());
      setPreview(result);
      if (result.total_transactions === 0) {
        notify.warning('No transactions generated. Check dates — future dates are skipped.');
      }
    } catch (err) {
      notify.error(getErrorMessage(err));
    } finally {
      setPreviewing(false);
    }
  };

  // ── Create ──

  const handleCreate = async () => {
    try {
      setCreating(true);
      const result = await sipCreatorAPI.create({
        ...buildPayload(),
        update_asset_metrics: true,
      });
      notify.success(`Created ${result.total_transactions} SIP transactions successfully!`);
      setPreview(null);
      setPeriods([defaultPeriod()]);
      setSelectedAssetId('');
    } catch (err) {
      notify.error(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  // ── Render ──

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  const selectedAsset = mfAssets.find(a => a.id === selectedAssetId);

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h5" fontWeight="bold" gutterBottom>
        SIP Transaction Creator
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Generate historical SIP (Systematic Investment Plan) buy transactions for a mutual fund
        using actual NAV data. Transactions are only created for past dates.
      </Typography>

      {/* Fund Selector */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Select Mutual Fund
          </Typography>
          {mfAssets.length === 0 ? (
            <Alert severity="info">
              No mutual fund assets found. Please add a mutual fund asset first (with ISIN) from the
              Equity MF, Hybrid MF, or Debt Funds page.
            </Alert>
          ) : (
            <TextField
              select
              fullWidth
              size="small"
              label="Mutual Fund"
              value={selectedAssetId}
              onChange={e => setSelectedAssetId(Number(e.target.value))}
            >
              {mfAssets.map(asset => (
                <MenuItem key={asset.id} value={asset.id}>
                  {asset.name}
                  {asset.isin ? ` (${asset.isin})` : ' — No ISIN'}
                </MenuItem>
              ))}
            </TextField>
          )}
          {selectedAsset && (
            <Box sx={{ mt: 1, display: 'flex', gap: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Current NAV: {formatNav(selectedAsset.current_price)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Units: {formatUnits(selectedAsset.quantity)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Value: {formatCurrency(selectedAsset.current_value)}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* SIP Periods */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            SIP Periods
          </Typography>

          {periods.map((period, idx) => (
            <Paper key={idx} variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                <Typography variant="subtitle2" color="primary">
                  Period {idx + 1}
                </Typography>
                {periods.length > 1 && (
                  <IconButton size="small" color="error" onClick={() => removePeriod(idx)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                )}
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="SIP Amount (₹)"
                    type="number"
                    value={period.sip_amount}
                    onChange={e => updatePeriod(idx, 'sip_amount', e.target.value)}
                    inputProps={{ min: 1 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Start Date"
                    type="date"
                    value={period.start_date}
                    onChange={e => updatePeriod(idx, 'start_date', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="End Date"
                    type="date"
                    value={period.end_date}
                    onChange={e => updatePeriod(idx, 'end_date', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Periodicity"
                    value={period.periodicity}
                    onChange={e => updatePeriod(idx, 'periodicity', e.target.value)}
                  >
                    <MenuItem value="weekly">Weekly</MenuItem>
                    <MenuItem value="monthly">Monthly</MenuItem>
                    <MenuItem value="quarterly">Quarterly</MenuItem>
                  </TextField>
                </Grid>
              </Grid>

              {/* Topup */}
              <Box sx={{ mt: 1.5 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      size="small"
                      checked={period.topup_enabled}
                      onChange={e => updatePeriod(idx, 'topup_enabled', e.target.checked)}
                    />
                  }
                  label={<Typography variant="body2">Enable Annual Topup (Step-up SIP)</Typography>}
                />
                {period.topup_enabled && (
                  <Grid container spacing={2} sx={{ mt: 0.5 }}>
                    <Grid item xs={6} sm={3}>
                      <TextField
                        select
                        fullWidth
                        size="small"
                        label="Topup Type"
                        value={period.topup.topup_type}
                        onChange={e => updatePeriod(idx, 'topup.topup_type', e.target.value)}
                      >
                        <MenuItem value="percentage">Percentage (%)</MenuItem>
                        <MenuItem value="fixed">Fixed Amount (₹)</MenuItem>
                      </TextField>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <TextField
                        fullWidth
                        size="small"
                        label={period.topup.topup_type === 'percentage' ? 'Annual Increase (%)' : 'Annual Increase (₹)'}
                        type="number"
                        value={period.topup.topup_value}
                        onChange={e => updatePeriod(idx, 'topup.topup_value', e.target.value)}
                        inputProps={{ min: 0.01, step: period.topup.topup_type === 'percentage' ? 1 : 100 }}
                      />
                    </Grid>
                  </Grid>
                )}
              </Box>
            </Paper>
          ))}

          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <Button size="small" startIcon={<AddIcon />} onClick={addPeriod}>
              Add SIP Period
            </Button>
            <Button
              variant="contained"
              startIcon={previewing ? <CircularProgress size={16} color="inherit" /> : <PreviewIcon />}
              onClick={handlePreview}
              disabled={previewing || !selectedAssetId}
            >
              {previewing ? 'Fetching NAV...' : 'Preview Transactions'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Preview Results */}
      {preview && (
        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              Preview — {preview.asset_name}
            </Typography>

            {/* Summary Cards */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6} sm={3}>
                <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">Total Transactions</Typography>
                  <Typography variant="h6" fontWeight="bold">{preview.total_transactions}</Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">Total Invested</Typography>
                  <Typography variant="h6" fontWeight="bold">{formatCurrency(preview.total_amount)}</Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">Total Units</Typography>
                  <Typography variant="h6" fontWeight="bold">{formatUnits(preview.total_units)}</Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">Avg NAV</Typography>
                  <Typography variant="h6" fontWeight="bold">{formatNav(preview.average_nav)}</Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Warnings */}
            {preview.warnings.length > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                {preview.warnings.map((w, i) => (
                  <Typography key={i} variant="body2">{w}</Typography>
                ))}
              </Alert>
            )}

            {/* Transaction Table */}
            {preview.transactions.length > 0 && (
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400, mb: 2 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>#</TableCell>
                      <TableCell>SIP Date</TableCell>
                      <TableCell>NAV Date</TableCell>
                      <TableCell align="right">NAV</TableCell>
                      <TableCell align="right">Amount (₹)</TableCell>
                      <TableCell align="right">Units</TableCell>
                      <TableCell>Period</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {preview.transactions.map((txn, idx) => (
                      <TableRow key={idx} hover>
                        <TableCell>{idx + 1}</TableCell>
                        <TableCell>{formatDate(txn.transaction_date)}</TableCell>
                        <TableCell>
                          <Tooltip title={txn.nav_source === 'exact' ? 'Exact match' : 'Previous trading day'}>
                            <span>
                              {formatDate(txn.nav_date)}
                              {txn.nav_source !== 'exact' && ' *'}
                            </span>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="right">{formatNav(txn.nav)}</TableCell>
                        <TableCell align="right">{formatCurrency(txn.sip_amount)}</TableCell>
                        <TableCell align="right">{formatUnits(txn.units)}</TableCell>
                        <TableCell>P{txn.period_index + 1} — {txn.sip_number}/{txn.total_sips_in_period}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
              <Button onClick={() => setPreview(null)}>Cancel</Button>
              <Button
                variant="contained"
                color="success"
                startIcon={creating ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
                onClick={handleCreate}
                disabled={creating || preview.total_transactions === 0}
              >
                {creating
                  ? 'Creating...'
                  : `Create ${preview.total_transactions} Transaction${preview.total_transactions !== 1 ? 's' : ''}`}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default SIPCreator;
