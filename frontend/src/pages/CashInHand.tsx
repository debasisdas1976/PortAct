import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Alert, Button,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, IconButton, MenuItem, Chip,
} from '@mui/material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { Add, Edit, Delete } from '@mui/icons-material';
import { assetsAPI } from '../services/api';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface AssetItem {
  id: number;
  name: string;
  symbol: string;
  total_invested: number;
  current_value: number;
  asset_type: string;
  notes?: string;
  details?: Record<string, any>;
  xirr?: number | null;
}

const ASSET_TYPE = 'cash';
const PAGE_TITLE = 'Cash In Hand';

const CURRENCIES = [
  { code: 'INR', symbol: '\u20B9', name: 'Indian Rupee' },
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '\u20AC', name: 'Euro' },
  { code: 'GBP', symbol: '\u00A3', name: 'British Pound' },
  { code: 'AED', symbol: 'AED', name: 'UAE Dirham' },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar' },
  { code: 'JPY', symbol: '\u00A5', name: 'Japanese Yen' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc' },
];

const EMPTY_FORM = {
  name: '',
  currency: 'INR',
  original_amount: '',
  inr_value: '',
  notes: '',
  xirr: '' as string,
  portfolio_id: '' as number | '',
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatAmount = (amount: number, currencyCode: string) => {
  const curr = CURRENCIES.find(c => c.code === currencyCode);
  return `${curr?.symbol || currencyCode} ${amount.toLocaleString('en-IN')}`;
};

const CashInHand: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [dialogError, setDialogError] = useState('');
  const [exchangeRates, setExchangeRates] = useState<Record<string, number>>({});

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setAssets((res.data as AssetItem[]).filter((a) => a.asset_type?.toLowerCase() === ASSET_TYPE));
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  }, [selectedPortfolioId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);

  const fetchExchangeRates = useCallback(async () => {
    try {
      const res = await api.get('/prices/exchange-rates');
      setExchangeRates(res.data.rates || {});
    } catch {
      // Rates unavailable — user can still enter manually
    }
  }, []);

  const handleAdd = () => {
    setEditingId(null);
    setForm({ ...EMPTY_FORM, portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '') });
    setDialogError('');
    setDialogOpen(true);
    fetchExchangeRates();
  };

  const handleEdit = (asset: AssetItem) => {
    setEditingId(asset.id);
    const currency = asset.details?.currency || asset.symbol || 'INR';
    const originalAmount = asset.details?.original_amount ?? asset.current_value ?? '';
    setForm({
      name: asset.name || '',
      currency,
      original_amount: String(originalAmount),
      inr_value: String(asset.current_value || ''),
      notes: asset.notes || '',
      xirr: String(asset.xirr || ''),
      portfolio_id: (asset as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
    });
    setDialogError('');
    setDialogOpen(true);
    fetchExchangeRates();
  };

  const computeInrValue = (currency: string, amount: string, rates: Record<string, number>): string => {
    if (currency === 'INR') return amount;
    const rate = rates[currency];
    const parsed = parseFloat(amount);
    if (!rate || !parsed) return '';
    return (parsed * rate).toFixed(2);
  };

  const handleFormChange = (field: string, value: string) => {
    const updated = { ...form, [field]: value };
    if (field === 'currency' || field === 'original_amount') {
      updated.inr_value = computeInrValue(updated.currency, updated.original_amount, exchangeRates);
    }
    setForm(updated);
  };

  const handleSave = async () => {
    if (!form.currency) { setDialogError('Currency is required'); return; }
    if (!form.original_amount) { setDialogError('Amount is required'); return; }

    const originalAmount = parseFloat(form.original_amount) || 0;
    const isINR = form.currency === 'INR';
    const inrValue = isINR ? originalAmount : (parseFloat(form.inr_value) || 0);

    if (!isINR && !inrValue) { setDialogError('INR equivalent value is required for non-INR currencies'); return; }

    setDialogError('');

    const details: Record<string, any> = {
      currency: form.currency,
      original_amount: originalAmount,
    };

    const autoName = form.name || `${form.currency} Cash`;

    const payload = {
      asset_type: ASSET_TYPE,
      name: autoName,
      symbol: form.currency,
      total_invested: inrValue,
      quantity: 1,
      purchase_price: inrValue,
      current_price: inrValue,
      notes: form.notes || undefined,
      details,
      ...(form.xirr ? { xirr: parseFloat(form.xirr) } : {}),
      portfolio_id: form.portfolio_id || undefined,
    };

    try {
      setSaving(true);
      if (editingId) { await assetsAPI.update(editingId, payload); }
      else { await assetsAPI.create(payload); }
      notify.success(editingId ? 'Cash holding updated successfully' : 'Cash holding added successfully');
      setDialogOpen(false);
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save'));
    } finally { setSaving(false); }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await assetsAPI.delete(id);
      notify.success('Cash holding deleted successfully');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete'));
    }
  };

  if (loading) {
    return (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}><CircularProgress /></Box>);
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{PAGE_TITLE}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleAdd}>Add</Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{assets.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Total Value (INR)</Typography>
            <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Currencies</Typography>
            <Typography variant="h4">{new Set(assets.map(a => a.details?.currency || a.symbol)).size}</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Currency</strong></TableCell>
              <TableCell align="right"><strong>Amount</strong></TableCell>
              <TableCell align="right"><strong>INR Value</strong></TableCell>
              <TableCell align="right"><strong>XIRR</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={6} align="center"><Typography color="text.secondary">No cash holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : (
              assets.map((asset) => {
                const currency = asset.details?.currency || asset.symbol || 'INR';
                const originalAmount = asset.details?.original_amount ?? asset.current_value ?? 0;
                return (
                  <TableRow key={asset.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">{asset.name}</Typography>
                      {asset.notes && <Typography variant="caption" color="text.secondary">{asset.notes}</Typography>}
                    </TableCell>
                    <TableCell><Chip label={currency} size="small" variant="outlined" /></TableCell>
                    <TableCell align="right">{formatAmount(originalAmount, currency)}</TableCell>
                    <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                    <TableCell align="right">
                      {asset.xirr != null ? (
                        <Typography variant="body2" color={asset.xirr >= 0 ? 'success.main' : 'error.main'}>
                          {asset.xirr >= 0 ? '+' : ''}{asset.xirr.toFixed(2)}%
                        </Typography>
                      ) : (
                        <Typography variant="caption" color="text.secondary">N/A</Typography>
                      )}
                    </TableCell>
                    <TableCell align="center">
                      <IconButton size="small" color="primary" onClick={() => handleEdit(asset)} title="Edit"><Edit fontSize="small" /></IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDelete(asset.id, asset.name)} title="Delete"><Delete fontSize="small" /></IconButton>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? 'Edit' : 'Add'} Cash Holding</DialogTitle>
        <DialogContent>
          {dialogError && <Alert severity="error" sx={{ mb: 2 }}>{dialogError}</Alert>}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}>
              <TextField fullWidth label="Name" value={form.name} onChange={(e) => handleFormChange('name', e.target.value)} helperText="Optional. Auto-generated from currency if left empty." />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField select fullWidth label="Currency" required value={form.currency} onChange={(e) => handleFormChange('currency', e.target.value)}>
                {CURRENCIES.map((c) => (<MenuItem key={c.code} value={c.code}>{c.code} — {c.name}</MenuItem>))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="Amount" type="number" required value={form.original_amount} onChange={(e) => handleFormChange('original_amount', e.target.value)} inputProps={{ min: 0, step: '0.01' }} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth label="INR Value" type="number" required
                value={form.inr_value}
                onChange={(e) => handleFormChange('inr_value', e.target.value)}
                inputProps={{ min: 0, step: '0.01' }}
                disabled={form.currency === 'INR'}
                InputProps={{ readOnly: form.currency !== 'INR' && !!exchangeRates[form.currency] }}
                helperText={
                  form.currency === 'INR'
                    ? 'Auto-filled for INR'
                    : exchangeRates[form.currency]
                      ? `Rate: 1 ${form.currency} = ₹${exchangeRates[form.currency].toFixed(2)}`
                      : 'Enter INR equivalent value'
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField select fullWidth label="Portfolio" value={form.portfolio_id} onChange={(e) => handleFormChange('portfolio_id', e.target.value ? e.target.value : '')}>
                {portfolios.map((p: any) => (<MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="XIRR (%)" type="number" value={form.xirr} onChange={(e) => handleFormChange('xirr', e.target.value)} helperText="Enter annualized return rate" />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth label="Notes" multiline rows={2} value={form.notes} onChange={(e) => handleFormChange('notes', e.target.value)} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>{saving ? <CircularProgress size={24} /> : editingId ? 'Save' : 'Add'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CashInHand;
