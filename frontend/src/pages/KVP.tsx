import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Alert, Button,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, IconButton, MenuItem,
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
  id: number; name: string; symbol: string; total_invested: number; current_value: number;
  asset_type: string; broker_name?: string; account_id?: string; notes?: string; details?: Record<string, any>;
  xirr?: number | null;
}

const ASSET_TYPE = 'kvp';
const PAGE_TITLE = 'Kisan Vikas Patra (KVP)';
const EMPTY_FORM = { name: '', symbol: '', total_invested: '', current_value: '', interest_rate: '', maturity_date: '', broker_name: '', notes: '', xirr: '' as string, portfolio_id: '' as number | '' };

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const KVP: React.FC = () => {
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

  const handleAdd = () => { setEditingId(null); setForm({ ...EMPTY_FORM, portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '') }); setDialogOpen(true); };
  const handleEdit = (asset: AssetItem) => {
    setEditingId(asset.id);
    setForm({ name: asset.name || '', symbol: asset.symbol || '', total_invested: String(asset.total_invested || ''), current_value: String(asset.current_value || ''),
      interest_rate: String(asset.details?.interest_rate || ''), maturity_date: asset.details?.maturity_date || '', broker_name: asset.broker_name || '', notes: asset.notes || '',
      xirr: String(asset.xirr || ''),
      portfolio_id: (asset as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '') });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name) { setDialogError('Name is required'); return; }
    setDialogError('');
    const invested = parseFloat(form.total_invested) || 0;
    const value = parseFloat(form.current_value) || invested;
    const details: Record<string, any> = {};
    if (form.interest_rate) details.interest_rate = parseFloat(form.interest_rate);
    if (form.maturity_date) details.maturity_date = form.maturity_date;
    const payload = { asset_type: ASSET_TYPE, name: form.name, symbol: form.symbol || undefined, total_invested: invested, quantity: 1, purchase_price: invested, current_price: value, broker_name: form.broker_name || undefined, notes: form.notes || undefined, details, ...(form.xirr ? { xirr: parseFloat(form.xirr) } : {}), portfolio_id: form.portfolio_id || undefined };
    try {
      setSaving(true);
      if (editingId) { await assetsAPI.update(editingId, payload); } else { await assetsAPI.create(payload); }
      notify.success(editingId ? 'Certificate updated successfully' : 'Certificate added successfully');
      setDialogOpen(false); fetchData();
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to save')); } finally { setSaving(false); }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try { await assetsAPI.delete(id); notify.success('Certificate deleted successfully'); fetchData(); }
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
        <Grid item xs={12} sm={6} md={4}><Card><CardContent><Typography color="text.secondary" variant="body2">Certificates</Typography><Typography variant="h4">{assets.length}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={4}><Card><CardContent><Typography color="text.secondary" variant="body2">Total Invested</Typography><Typography variant="h5">{formatCurrency(totalInvested)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md={4}><Card><CardContent><Typography color="text.secondary" variant="body2">Current Value</Typography><Typography variant="h5">{formatCurrency(totalValue)}</Typography></CardContent></Card></Grid>
      </Grid>
      <TableContainer component={Paper}>
        <Table>
          <TableHead><TableRow>
            <TableCell><strong>Name</strong></TableCell><TableCell><strong>Certificate No.</strong></TableCell>
            <TableCell align="right"><strong>Invested</strong></TableCell><TableCell align="right"><strong>Current Value</strong></TableCell>
            <TableCell align="right"><strong>Interest Rate</strong></TableCell><TableCell><strong>Maturity Date</strong></TableCell>
            <TableCell align="right"><strong>XIRR</strong></TableCell><TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow></TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={8} align="center"><Typography color="text.secondary">No holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : assets.map((asset) => (
              <TableRow key={asset.id} hover>
                <TableCell><Typography variant="body2" fontWeight="medium">{asset.name}</Typography>{asset.broker_name && <Typography variant="caption" color="text.secondary">{asset.broker_name}</Typography>}</TableCell>
                <TableCell>{asset.symbol || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                <TableCell align="right">{asset.details?.interest_rate ? `${asset.details.interest_rate}%` : '-'}</TableCell>
                <TableCell>{asset.details?.maturity_date ? new Date(asset.details.maturity_date).toLocaleDateString('en-IN') : '-'}</TableCell>
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
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? 'Edit' : 'Add'} {PAGE_TITLE}</DialogTitle>
        <DialogContent>
          {dialogError && <Alert severity="error" sx={{ mb: 2 }}>{dialogError}</Alert>}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}><TextField fullWidth label="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Certificate / Account No." value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Institution / Branch" value={form.broker_name} onChange={(e) => setForm({ ...form, broker_name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Amount Invested" type="number" value={form.total_invested} onChange={(e) => setForm({ ...form, total_invested: e.target.value })} inputProps={{ min: 0, step: '0.01' }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Current Value" type="number" value={form.current_value} onChange={(e) => setForm({ ...form, current_value: e.target.value })} inputProps={{ min: 0, step: '0.01' }} helperText="Leave empty to use invested amount" /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Interest Rate (%)" type="number" value={form.interest_rate} onChange={(e) => setForm({ ...form, interest_rate: e.target.value })} inputProps={{ min: 0, step: '0.01' }} /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="Maturity Date" type="date" value={form.maturity_date} onChange={(e) => setForm({ ...form, maturity_date: e.target.value })} InputLabelProps={{ shrink: true }} /></Grid>
            <Grid item xs={12} sm={6}><TextField select fullWidth label="Portfolio" value={form.portfolio_id} onChange={(e) => setForm({ ...form, portfolio_id: e.target.value ? Number(e.target.value) : '' })}>{portfolios.map((p: any) => (<MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>))}</TextField></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth label="XIRR (%)" type="number" value={form.xirr} onChange={(e) => setForm({ ...form, xirr: e.target.value })} helperText="Enter annualized return rate" /></Grid>
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

export default KVP;
