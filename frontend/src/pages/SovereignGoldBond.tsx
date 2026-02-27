import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, MenuItem, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Chip, Alert, Button,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, IconButton,
} from '@mui/material';
import { Add, Edit, Delete, Refresh, TrendingUp, TrendingDown } from '@mui/icons-material';
import { assetsAPI } from '../services/api';
import api from '../services/api';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface AssetItem {
  id: number; name: string; symbol: string; quantity: number; purchase_price: number;
  current_price: number; total_invested: number; current_value: number;
  profit_loss: number; profit_loss_percentage: number; asset_type: string;
  demat_account_id?: number; broker_name?: string; account_id?: string;
  account_holder_name?: string; notes?: string; details?: Record<string, any>;
}
interface DematAccount { id: number; broker_name: string; account_id: string; account_holder_name?: string; nickname?: string; }

const ASSET_TYPE = 'sovereign_gold_bond';
const PAGE_TITLE = 'Sovereign Gold Bonds';
const EMPTY_FORM = { name: '', symbol: '', quantity: '', purchase_price: '', current_price: '', broker_name: '', account_id: '', notes: '', portfolio_id: '' as number | '' };

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const SovereignGoldBond: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [assetsRes, dematRes] = await Promise.all([api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} }), api.get('/demat-accounts/')]);
      setAssets((assetsRes.data as AssetItem[]).filter((a) => a.asset_type?.toLowerCase() === ASSET_TYPE));
      const labelMap: Record<number, string> = {};
      for (const da of dematRes.data as DematAccount[]) labelMap[da.id] = buildDematLabel(da);
      setDematLabelMap(labelMap);
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to load data')); } finally { setLoading(false); }
  }, [notify, selectedPortfolioId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const totalInvested = assets.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;
  const totalQuantity = assets.reduce((s, a) => s + (a.quantity || 0), 0);

  const groups: Record<string, AssetItem[]> = {};
  for (const asset of assets) {
    const key = asset.demat_account_id != null ? String(asset.demat_account_id) : ([asset.broker_name, asset.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(asset);
  }
  const groupLabel = (ga: AssetItem[]) => {
    const f = ga[0];
    if (f.demat_account_id != null && dematLabelMap[f.demat_account_id]) return dematLabelMap[f.demat_account_id];
    const parts: string[] = [];
    if (f.broker_name) parts.push(f.broker_name);
    if (f.account_id) parts.push(`(${f.account_id})`);
    if (f.account_holder_name) parts.push(`— ${f.account_holder_name}`);
    return parts.length ? parts.join(' ') : 'Unlinked Holdings';
  };

  const handlePriceUpdate = async (assetId: number, assetName: string) => {
    try {
      setUpdatingAssetId(assetId);
      const response = await api.post(`/assets/${assetId}/update-price`, {});
      await fetchData();
      if (response.data?.price_update_failed) {
        notify.error(`Failed to update price for ${assetName}: ${response.data.price_update_error || 'Price source unavailable'}`);
      } else {
        notify.success(`Price updated for ${assetName}`);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to update price for ${assetName}`));
    } finally {
      setUpdatingAssetId(null);
    }
  };

  const handleAdd = () => { setEditingId(null); setForm({ ...EMPTY_FORM, portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '') }); setDialogOpen(true); };
  const handleEdit = (asset: AssetItem) => {
    setEditingId(asset.id);
    setForm({ name: asset.name || '', symbol: asset.symbol || '', quantity: String(asset.quantity || ''), purchase_price: String(asset.purchase_price || ''), current_price: String(asset.current_price || ''), broker_name: asset.broker_name || '', account_id: asset.account_id || '', notes: asset.notes || '', portfolio_id: (asset as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '') });
    setDialogOpen(true);
  };
  const [dialogError, setDialogError] = useState('');
  const handleSave = async () => {
    if (!form.name) { setDialogError('Name is required'); return; }
    setDialogError('');
    const qty = parseFloat(form.quantity) || 1;
    const buyPrice = parseFloat(form.purchase_price) || 0;
    const curPrice = parseFloat(form.current_price) || buyPrice;
    const payload = { asset_type: ASSET_TYPE, name: form.name, symbol: form.symbol || undefined, quantity: qty, purchase_price: buyPrice, current_price: curPrice, total_invested: qty * buyPrice, broker_name: form.broker_name || undefined, account_id: form.account_id || undefined, notes: form.notes || undefined, portfolio_id: form.portfolio_id || undefined };
    try {
      setSaving(true);
      if (editingId) { await assetsAPI.update(editingId, payload); } else { await assetsAPI.create(payload); }
      notify.success(editingId ? 'SGB updated successfully' : 'SGB added successfully');
      setDialogOpen(false); fetchData();
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to save')); } finally { setSaving(false); }
  };
  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try { await assetsAPI.delete(id); notify.success('SGB deleted successfully'); fetchData(); }
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
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Holdings</Typography><Typography variant="h4">{assets.length}</Typography><Typography variant="caption" color="text.secondary">{totalQuantity.toFixed(2)} grams</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Current Value</Typography><Typography variant="h5">{formatCurrency(totalValue)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Total Invested</Typography><Typography variant="h5">{formatCurrency(totalInvested)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Total P&L</Typography><Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>{formatCurrency(totalPnL)}</Typography><Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>{totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%</Typography></CardContent></Card></Grid>
      </Grid>
      <TableContainer component={Paper}>
        <Table>
          <TableHead><TableRow>
            <TableCell><strong>SGB Series</strong></TableCell><TableCell align="right"><strong>Qty (grams)</strong></TableCell>
            <TableCell align="right"><strong>Issue Price</strong></TableCell><TableCell align="right"><strong>Current Price</strong></TableCell>
            <TableCell align="right"><strong>Invested</strong></TableCell><TableCell align="right"><strong>Value</strong></TableCell>
            <TableCell align="right"><strong>P&L</strong></TableCell><TableCell align="right"><strong>P&L %</strong></TableCell>
            <TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow></TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={9} align="center"><Typography color="text.secondary">No holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : Object.entries(groups).map(([key, ga]) => {
              const gI = ga.reduce((s, a) => s + (a.total_invested || 0), 0);
              const gV = ga.reduce((s, a) => s + (a.current_value || 0), 0);
              const gP = gV - gI;
              return (
                <React.Fragment key={key}>
                  <TableRow sx={{ bgcolor: 'action.hover' }}>
                    <TableCell colSpan={4}><Typography variant="subtitle2" fontWeight="bold">{groupLabel(ga)}</Typography><Typography variant="caption" color="text.secondary">{ga.length} holding{ga.length !== 1 ? 's' : ''}</Typography></TableCell>
                    <TableCell align="right"><Typography variant="caption" color="text.secondary">Invested</Typography><Typography variant="body2" fontWeight="medium">{formatCurrency(gI)}</Typography></TableCell>
                    <TableCell align="right"><Typography variant="caption" color="text.secondary">Value</Typography><Typography variant="body2" fontWeight="medium">{formatCurrency(gV)}</Typography></TableCell>
                    <TableCell align="right" colSpan={3}><Typography variant="caption" color="text.secondary">P&L</Typography><Typography variant="body2" fontWeight="medium" color={gP >= 0 ? 'success.main' : 'error.main'}>{formatCurrency(gP)}</Typography></TableCell>
                  </TableRow>
                  {ga.map((asset) => (
                    <TableRow key={asset.id} hover>
                      <TableCell><Typography variant="body2" fontWeight="medium">{asset.symbol || asset.name}</Typography><Typography variant="caption" color="text.secondary">{asset.name}</Typography></TableCell>
                      <TableCell align="right">{asset.quantity?.toFixed(4)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.purchase_price)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.current_price)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                      <TableCell align="right" sx={{ color: asset.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>{formatCurrency(asset.profit_loss)}</TableCell>
                      <TableCell align="right"><Chip label={`${asset.profit_loss_percentage >= 0 ? '+' : ''}${asset.profit_loss_percentage?.toFixed(2)}%`} color={asset.profit_loss_percentage >= 0 ? 'success' : 'error'} size="small" icon={asset.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />} /></TableCell>
                      <TableCell align="center">
                        <IconButton size="small" color="info" title="Refresh Price" onClick={() => handlePriceUpdate(asset.id, asset.symbol || asset.name)} disabled={updatingAssetId === asset.id}>{updatingAssetId === asset.id ? <CircularProgress size={16} /> : <Refresh fontSize="small" />}</IconButton>
                        <IconButton size="small" color="primary" onClick={() => handleEdit(asset)} title="Edit"><Edit fontSize="small" /></IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDelete(asset.id, asset.name)} title="Delete"><Delete fontSize="small" /></IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? 'Edit' : 'Add'} {PAGE_TITLE}</DialogTitle>
        <DialogContent>
          {dialogError && <Alert severity="error" sx={{ mb: 2 }}>{dialogError}</Alert>}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}><TextField fullWidth label="SGB Series Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} helperText="e.g., SGB 2024-25 Series I" /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Symbol / Ticker" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Quantity (grams)" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} inputProps={{ min: 0, step: '0.001' }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Issue / Purchase Price" type="number" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} inputProps={{ min: 0, step: '0.01' }} helperText="Price per gram at purchase" /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Current Price" type="number" value={form.current_price} onChange={(e) => setForm({ ...form, current_price: e.target.value })} inputProps={{ min: 0, step: '0.01' }} helperText="Current gold price per gram" /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Broker" value={form.broker_name} onChange={(e) => setForm({ ...form, broker_name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Account ID" value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })} /></Grid>
            <Grid item xs={12}><TextField fullWidth label="Notes" multiline rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Grid>
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Portfolio"
                value={form.portfolio_id}
                onChange={(e) => setForm({ ...form, portfolio_id: e.target.value ? Number(e.target.value) : '' })}
              >
                {portfolios.map((p: any) => (
                  <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
                ))}
              </TextField>
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

export default SovereignGoldBond;
