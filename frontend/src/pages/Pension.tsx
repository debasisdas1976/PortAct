import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Switch,
  FormControlLabel,
  MenuItem,
} from '@mui/material';
import { Add, Edit, Delete, Savings as PensionIcon } from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { RootState } from '../store';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface PensionAccount {
  id: number;
  user_id: number;
  asset_id: number;
  nickname: string;
  plan_name: string;
  provider_name: string;
  pension_type: string;
  account_number?: string;
  account_holder_name: string;
  monthly_pension: number;
  total_corpus: number;
  annual_pension: number;
  start_date: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

interface PensionSummary {
  total_accounts: number;
  active_accounts: number;
  total_monthly_pension: number;
  total_annual_pension: number;
  total_corpus: number;
  accounts: PensionAccount[];
}

const PENSION_TYPES = [
  { value: 'eps', label: 'EPS (Employee Pension Scheme)' },
  { value: 'family_pension', label: 'Family Pension' },
  { value: 'superannuation', label: 'Superannuation' },
  { value: 'annuity', label: 'Annuity' },
  { value: 'government', label: 'Government Pension' },
  { value: 'other', label: 'Other' },
];

const emptyForm = {
  portfolio_id: '' as number | '',
  nickname: '',
  plan_name: '',
  provider_name: '',
  pension_type: '',
  account_number: '',
  account_holder_name: '',
  monthly_pension: '',
  total_corpus: '',
  start_date: '',
  is_active: true,
  notes: '',
};

const PAGE_TITLE = 'Pension';

const Pension: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [summary, setSummary] = useState<PensionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/pension/summary', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setSummary(response.data);
    } catch (err) {
      setLoadError(getErrorMessage(err, 'Failed to load pension data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedPortfolioId]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const formatPensionType = (type: string) => {
    const found = PENSION_TYPES.find((t) => t.value === type);
    return found ? found.label : type;
  };

  const handleOpenAdd = () => {
    setEditingId(null);
    setForm({...emptyForm, portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '')});
    setDialogOpen(true);
  };

  const handleOpenEdit = (account: PensionAccount) => {
    setEditingId(account.id);
    setForm({
      portfolio_id: (account as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
      nickname: account.nickname,
      plan_name: account.plan_name,
      provider_name: account.provider_name,
      pension_type: account.pension_type,
      account_number: account.account_number || '',
      account_holder_name: account.account_holder_name,
      monthly_pension: String(account.monthly_pension),
      total_corpus: String(account.total_corpus),
      start_date: account.start_date,
      is_active: account.is_active,
      notes: account.notes || '',
    });
    setDialogOpen(true);
  };

  const handleClose = () => {
    setDialogOpen(false);
    setEditingId(null);
  };

  const handleSave = async () => {
    if (!form.nickname || !form.plan_name || !form.provider_name || !form.pension_type || !form.account_holder_name || !form.monthly_pension || !form.start_date) {
      notify.error('Please fill in all required fields');
      return;
    }
    const payload = {
      portfolio_id: form.portfolio_id || undefined,
      nickname: form.nickname,
      plan_name: form.plan_name,
      provider_name: form.provider_name,
      pension_type: form.pension_type,
      account_number: form.account_number || null,
      account_holder_name: form.account_holder_name,
      monthly_pension: parseFloat(form.monthly_pension),
      total_corpus: form.total_corpus ? parseFloat(form.total_corpus) : 0,
      start_date: form.start_date,
      is_active: form.is_active,
      notes: form.notes || null,
    };
    try {
      setSaving(true);
      if (editingId) {
        await api.put(`/pension/${editingId}`, payload);
        notify.success('Pension account updated successfully');
      } else {
        await api.post('/pension/', payload);
        notify.success('Pension account added successfully');
      }
      handleClose();
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save pension account'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete pension account "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/pension/${id}`);
      notify.success('Pension account deleted successfully');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete pension account'));
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (loadError) {
    return (
      <Box sx={{ mt: 2 }}>
        <Typography color="error">{loadError}</Typography>
      </Box>
    );
  }

  const accounts = summary?.accounts || [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PensionIcon color="primary" />
          <Typography variant="h4">{PAGE_TITLE}</Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={handleOpenAdd}>
          Add Account
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Accounts</Typography>
              <Typography variant="h5">{summary?.total_accounts ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Active Accounts</Typography>
              <Typography variant="h5">{summary?.active_accounts ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Monthly Pension</Typography>
              <Typography variant="h5" color="success.main">
                {formatCurrency(summary?.total_monthly_pension ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Corpus</Typography>
              <Typography variant="h5" color="primary.main">
                {formatCurrency(summary?.total_corpus ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Accounts Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nickname</TableCell>
                <TableCell>Plan Name</TableCell>
                <TableCell>Provider</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Holder</TableCell>
                <TableCell>Start Date</TableCell>
                <TableCell align="right">Monthly Pension</TableCell>
                <TableCell align="right">Annual Pension</TableCell>
                <TableCell align="right">Corpus</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {accounts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={11} align="center">
                    <Typography color="text.secondary">
                      No pension accounts found. Add one to start tracking.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell>{account.nickname}</TableCell>
                    <TableCell>{account.plan_name}</TableCell>
                    <TableCell>{account.provider_name}</TableCell>
                    <TableCell>{formatPensionType(account.pension_type)}</TableCell>
                    <TableCell>{account.account_holder_name}</TableCell>
                    <TableCell>{account.start_date ? new Date(account.start_date).toLocaleDateString('en-IN') : '-'}</TableCell>
                    <TableCell align="right">{formatCurrency(account.monthly_pension)}</TableCell>
                    <TableCell align="right">{formatCurrency(account.annual_pension)}</TableCell>
                    <TableCell align="right">{formatCurrency(account.total_corpus)}</TableCell>
                    <TableCell>
                      <Chip
                        label={account.is_active ? 'Active' : 'Inactive'}
                        color={account.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                        <IconButton size="small" color="info" onClick={() => handleOpenEdit(account)} title="Edit">
                          <Edit fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDelete(account.id, account.nickname)} title="Delete">
                          <Delete fontSize="small" />
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Add / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? 'Edit Pension Account' : 'Add Pension Account'}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Nickname"
              value={form.nickname}
              onChange={(e) => setForm({ ...form, nickname: e.target.value })}
              required
              fullWidth
              helperText="e.g., EPS - Current Employer, Govt Pension"
            />
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
            <TextField
              label="Plan Name"
              value={form.plan_name}
              onChange={(e) => setForm({ ...form, plan_name: e.target.value })}
              required
              fullWidth
              helperText="e.g., Employee Pension Scheme, NPS Annuity"
            />
            <TextField
              label="Provider Name"
              value={form.provider_name}
              onChange={(e) => setForm({ ...form, provider_name: e.target.value })}
              required
              fullWidth
              helperText="e.g., EPFO, LIC, SBI Life"
            />
            <TextField
              select
              label="Pension Type"
              value={form.pension_type}
              onChange={(e) => setForm({ ...form, pension_type: e.target.value })}
              required
              fullWidth
            >
              {PENSION_TYPES.map((t) => (
                <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>
              ))}
            </TextField>
            <TextField
              label="Account Number (Optional)"
              value={form.account_number}
              onChange={(e) => setForm({ ...form, account_number: e.target.value })}
              fullWidth
            />
            <TextField
              label="Account Holder Name"
              value={form.account_holder_name}
              onChange={(e) => setForm({ ...form, account_holder_name: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Monthly Pension (₹)"
              type="number"
              value={form.monthly_pension}
              onChange={(e) => setForm({ ...form, monthly_pension: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, step: 100 }}
              helperText="Monthly pension amount received or expected"
            />
            <TextField
              label="Total Corpus (₹)"
              type="number"
              value={form.total_corpus}
              onChange={(e) => setForm({ ...form, total_corpus: e.target.value })}
              fullWidth
              inputProps={{ min: 0, step: 1000 }}
              helperText="Total pension fund value (if applicable)"
            />
            <TextField
              label="Start Date"
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              required
              fullWidth
              InputLabelProps={{ shrink: true }}
              helperText="Date when pension started or is expected to start"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  color="primary"
                />
              }
              label="Active"
            />
            <TextField
              label="Notes (Optional)"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>
            {saving ? <CircularProgress size={24} /> : editingId ? 'Save Changes' : 'Add Account'}
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  );
};

export default Pension;
