import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Chip, Alert, Button,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, IconButton, MenuItem,
} from '@mui/material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { Add, Edit, Delete, TrendingUp, TrendingDown } from '@mui/icons-material';
import { assetsAPI } from '../services/api';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface AssetItem {
  id: number; name: string; symbol: string; isin?: string; quantity: number;
  purchase_price: number; current_price: number; total_invested: number; current_value: number;
  profit_loss: number; profit_loss_percentage: number; asset_type: string;
  broker_name?: string; account_id?: string; notes?: string; details?: Record<string, any>;
}

const ASSET_TYPE = 'rbi_bond';
const PAGE_TITLE = 'RBI Bonds';
const EMPTY_FORM = { name: '', symbol: '', isin: '', quantity: '', purchase_price: '', current_price: '', interest_rate: '', maturity_date: '', broker_name: '', notes: '', portfolio_id: '' as number | '' };

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const RBIBond: React.FC = () => {
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

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setAssets((res.data as AssetItem[]).filter((a) => a.asset_type?.toLowerCase() === ASSET_TYPE));
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to load data')); } finally { setLoading(false); }
  }, [notify, selectedPortfolioId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const totalInvested = assets.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  const handleAdd = () => { setEditingId(null); setForm({ ...EMPTY_FORM, portfolio_id: selectedPortfolioId || '' }); setDialogOpen(true); };
  const handleEdit = (asset: AssetItem) => {
    setEditingId(asset.id);
    setForm({ name: asset.name || '', symbol: asset.symbol || '', isin: asset.isin || '', quantity: String(asset.quantity || ''), purchase_price: String(asset.purchase_price || ''), current_price: String(asset.current_price || ''), interest_rate: String(asset.details?.interest_rate || ''), maturity_date: asset.details?.maturity_date || '', broker_name: asset.broker_name || '', notes: asset.notes || '',
      portfolio_id: (asset as any).portfolio_id || selectedPortfolioId || '' });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name) { setDialogError('Name is required'); return; }
    setDialogError('');
    const qty = parseFloat(form.quantity) || 1;
    const buyPrice = parseFloat(form.purchase_price) || 0;
    const curPrice = parseFloat(form.current_price) || buyPrice;
    const details: Record<string, any> = {};
    if (form.interest_rate) details.interest_rate = parseFloat(form.interest_rate);
    if (form.maturity_date) details.maturity_date = form.maturity_date;
    const payload = { asset_type: ASSET_TYPE, name: form.name, symbol: form.symbol || undefined, isin: form.isin || undefined, quantity: qty, purchase_price: buyPrice, current_price: curPrice, total_invested: qty * buyPrice, broker_name: form.broker_name || undefined, notes: form.notes || undefined, details, portfolio_id: form.portfolio_id || undefined };
    try {
      setSaving(true);
      if (editingId) { await assetsAPI.update(editingId, payload); } else { await assetsAPI.create(payload); }
      notify.success(editingId ? 'Bond updated successfully' : 'Bond added successfully');
      setDialogOpen(false); fetchData();
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to save')); } finally { setSaving(false); }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try { await assetsAPI.delete(id); notify.success('Bond deleted successfully'); fetchData(); }
    catch (err) { notify.error(getErrorMessage(err, 'Failed to delete')); }
  };

  if (loading) return (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}><CircularProgress /></Box>);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{PAGE_TITLE}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleAdd}>Add</Button>
      </Box>
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}><Card><CardContent><Typography color="text.secondary" variant="body2">Holdings</Typography><Typography variant="h4">{assets.length}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={3}><Card><CardContent><Typography color="text.secondary" variant="body2">Current Value</Typography><Typography variant="h5">{formatCurrency(totalValue)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={3}><Card><CardContent><Typography color="text.secondary" variant="body2">Total Invested</Typography><Typography variant="h5">{formatCurrency(totalInvested)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={3}><Card><CardContent><Typography color="text.secondary" variant="body2">Total P&L</Typography><Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>{formatCurrency(totalPnL)}</Typography><Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>{totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%</Typography></CardContent></Card></Grid>
      </Grid>
      <TableContainer component={Paper}>
        <Table>
          <TableHead><TableRow>
            <TableCell><strong>Bond</strong></TableCell><TableCell><strong>ISIN</strong></TableCell>
            <TableCell align="right"><strong>Qty</strong></TableCell><TableCell align="right"><strong>Invested</strong></TableCell>
            <TableCell align="right"><strong>Current Value</strong></TableCell><TableCell align="right"><strong>P&L</strong></TableCell>
            <TableCell align="right"><strong>Coupon Rate</strong></TableCell><TableCell><strong>Maturity</strong></TableCell>
            <TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow></TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={9} align="center"><Typography color="text.secondary">No holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : assets.map((asset) => (
              <TableRow key={asset.id} hover>
                <TableCell><Typography variant="body2" fontWeight="medium">{asset.name}</Typography>{asset.broker_name && <Typography variant="caption" color="text.secondary">{asset.broker_name}</Typography>}</TableCell>
                <TableCell>{asset.isin || asset.symbol || '-'}</TableCell>
                <TableCell align="right">{asset.quantity?.toFixed(2)}</TableCell>
                <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                <TableCell align="right"><Chip label={`${asset.profit_loss_percentage >= 0 ? '+' : ''}${asset.profit_loss_percentage?.toFixed(2)}%`} color={asset.profit_loss_percentage >= 0 ? 'success' : 'error'} size="small" icon={asset.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />} /></TableCell>
                <TableCell align="right">{asset.details?.interest_rate ? `${asset.details.interest_rate}%` : '-'}</TableCell>
                <TableCell>{asset.details?.maturity_date ? new Date(asset.details.maturity_date).toLocaleDateString('en-IN') : '-'}</TableCell>
                <TableCell align="center">
                  <IconButton size="small" color="primary" onClick={() => handleEdit(asset)} title="Edit"><Edit fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => handleDelete(asset.id, asset.name)} title="Delete"><Delete fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? 'Edit' : 'Add'} {PAGE_TITLE}</DialogTitle>
        <DialogContent>
          {dialogError && <Alert severity="error" sx={{ mb: 2 }}>{dialogError}</Alert>}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}><TextField fullWidth label="Bond Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Symbol" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="ISIN" value={form.isin} onChange={(e) => setForm({ ...form, isin: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Quantity" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} inputProps={{ min: 0, step: '0.01' }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Purchase Price" type="number" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} inputProps={{ min: 0, step: '0.01' }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Current Price" type="number" value={form.current_price} onChange={(e) => setForm({ ...form, current_price: e.target.value })} inputProps={{ min: 0, step: '0.01' }} helperText="Leave empty to use purchase price" /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Coupon / Interest Rate (%)" type="number" value={form.interest_rate} onChange={(e) => setForm({ ...form, interest_rate: e.target.value })} inputProps={{ min: 0, step: '0.01' }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Maturity Date" type="date" value={form.maturity_date} onChange={(e) => setForm({ ...form, maturity_date: e.target.value })} InputLabelProps={{ shrink: true }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Broker" value={form.broker_name} onChange={(e) => setForm({ ...form, broker_name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField select fullWidth label="Portfolio" value={form.portfolio_id} onChange={(e) => setForm({ ...form, portfolio_id: e.target.value ? Number(e.target.value) : '' })}>{portfolios.map((p: any) => (<MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>))}</TextField></Grid>
            <Grid item xs={12}><TextField fullWidth label="Notes" multiline rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Grid>
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

export default RBIBond;
