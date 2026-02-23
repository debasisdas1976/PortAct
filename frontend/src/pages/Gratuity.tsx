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
  Tooltip,
  Switch,
  FormControlLabel,
  MenuItem,
} from '@mui/material';
import { Add, Edit, Delete, Work as GratuityIcon, InfoOutlined } from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { RootState } from '../store';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface GratuityAccount {
  id: number;
  user_id: number;
  asset_id: number;
  nickname: string;
  employer_name: string;
  employee_name: string;
  date_of_joining: string;
  basic_pay: number;
  is_active: boolean;
  notes?: string;
  years_of_service: number;
  completed_years: number;
  gratuity_amount: number;
  is_eligible: boolean;
  is_capped: boolean;
  created_at: string;
  updated_at?: string;
}

interface GratuitySummary {
  total_accounts: number;
  active_accounts: number;
  total_gratuity: number;
  accounts: GratuityAccount[];
}

const emptyForm = {
  portfolio_id: '' as number | '',
  nickname: '',
  employer_name: '',
  employee_name: '',
  date_of_joining: '',
  basic_pay: '',
  is_active: true,
  notes: '',
};

const Gratuity: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [summary, setSummary] = useState<GratuitySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/gratuity/summary', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setSummary(response.data);
    } catch (err) {
      setLoadError(getErrorMessage(err, 'Failed to load gratuity data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedPortfolioId]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const handleOpenAdd = () => {
    setEditingId(null);
    setForm({...emptyForm, portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '')});
    setDialogOpen(true);
  };

  const handleOpenEdit = (account: GratuityAccount) => {
    setEditingId(account.id);
    setForm({
      portfolio_id: (account as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
      nickname: account.nickname,
      employer_name: account.employer_name,
      employee_name: account.employee_name,
      date_of_joining: account.date_of_joining,
      basic_pay: String(account.basic_pay),
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
    if (!form.nickname || !form.employer_name || !form.employee_name || !form.date_of_joining || !form.basic_pay) {
      notify.error('Please fill in all required fields');
      return;
    }
    const payload = {
      portfolio_id: form.portfolio_id || undefined,
      nickname: form.nickname,
      employer_name: form.employer_name,
      employee_name: form.employee_name,
      date_of_joining: form.date_of_joining,
      basic_pay: parseFloat(form.basic_pay),
      is_active: form.is_active,
      notes: form.notes || null,
    };
    try {
      setSaving(true);
      if (editingId) {
        await api.put(`/gratuity/${editingId}`, payload);
        notify.success('Gratuity account updated successfully');
      } else {
        await api.post('/gratuity/', payload);
        notify.success('Gratuity account added successfully');
      }
      handleClose();
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save gratuity account'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete gratuity account "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/gratuity/${id}`);
      notify.success('Gratuity account deleted successfully');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete gratuity account'));
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
          <GratuityIcon color="primary" />
          <Typography variant="h4">Gratuity</Typography>
          <Tooltip title="Calculated using Payment of Gratuity Act formula: (Basic Pay × 15 × Completed Years) / 26. Capped at ₹20,00,000. Minimum 5 years for eligibility.">
            <InfoOutlined fontSize="small" color="action" sx={{ cursor: 'pointer' }} />
          </Tooltip>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={handleOpenAdd}>
          Add Account
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Accounts</Typography>
              <Typography variant="h5">{summary?.total_accounts ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Active Accounts</Typography>
              <Typography variant="h5">{summary?.active_accounts ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Gratuity Accrued</Typography>
              <Typography variant="h5" color="success.main">
                {formatCurrency(summary?.total_gratuity ?? 0)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Sum of active accounts (eligible only)
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
                <TableCell>Employer</TableCell>
                <TableCell>Employee</TableCell>
                <TableCell>Date of Joining</TableCell>
                <TableCell align="right">Years of Service</TableCell>
                <TableCell align="right">Monthly Basic Pay</TableCell>
                <TableCell align="right">Gratuity Accrued</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {accounts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    <Typography color="text.secondary">
                      No gratuity accounts found. Add one to start tracking.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell>{account.nickname}</TableCell>
                    <TableCell>{account.employer_name}</TableCell>
                    <TableCell>{account.employee_name}</TableCell>
                    <TableCell>{new Date(account.date_of_joining).toLocaleDateString('en-IN')}</TableCell>
                    <TableCell align="right">
                      <Box>
                        <Typography variant="body2">{account.completed_years} yrs</Typography>
                        <Typography variant="caption" color="text.secondary">
                          ({account.years_of_service.toFixed(1)} actual)
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">{formatCurrency(account.basic_pay)}</TableCell>
                    <TableCell align="right">
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {formatCurrency(account.gratuity_amount)}
                        </Typography>
                        {account.is_capped && (
                          <Chip label="Capped at ₹20L" color="warning" size="small" sx={{ mt: 0.5 }} />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                        <Chip
                          label={account.is_active ? 'Active' : 'Inactive'}
                          color={account.is_active ? 'success' : 'default'}
                          size="small"
                        />
                        {!account.is_eligible && account.is_active && (
                          <Chip label="< 5 yrs (not eligible)" color="warning" size="small" />
                        )}
                      </Box>
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
        <DialogTitle>{editingId ? 'Edit Gratuity Account' : 'Add Gratuity Account'}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Nickname"
              value={form.nickname}
              onChange={(e) => setForm({ ...form, nickname: e.target.value })}
              required
              fullWidth
              helperText="e.g., Current Job, Previous Employer"
            />
            <TextField
              select
              fullWidth
              margin="normal"
              label="Portfolio"
              value={form.portfolio_id}
              onChange={(e) => setForm({ ...form, portfolio_id: e.target.value ? Number(e.target.value) : '' })}
            >
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </TextField>
            <TextField
              label="Employer Name"
              value={form.employer_name}
              onChange={(e) => setForm({ ...form, employer_name: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Employee Name"
              value={form.employee_name}
              onChange={(e) => setForm({ ...form, employee_name: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Date of Joining"
              type="date"
              value={form.date_of_joining}
              onChange={(e) => setForm({ ...form, date_of_joining: e.target.value })}
              required
              fullWidth
              InputLabelProps={{ shrink: true }}
              helperText="Date when employment started with this employer"
            />
            <TextField
              label="Monthly Basic Pay (₹)"
              type="number"
              value={form.basic_pay}
              onChange={(e) => setForm({ ...form, basic_pay: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, step: 100 }}
              helperText="Latest basic salary component only (excludes HRA, allowances, etc.)"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  color="primary"
                />
              }
              label="Currently Employed (Active)"
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

export default Gratuity;
