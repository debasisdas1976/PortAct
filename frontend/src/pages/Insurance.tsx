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
  Alert,
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
  Snackbar,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
} from '@mui/material';
import { Add, Edit, Delete, Shield as InsuranceIcon } from '@mui/icons-material';
import api from '../services/api';

const POLICY_TYPES = [
  { value: 'term_life', label: 'Term Life' },
  { value: 'endowment', label: 'Endowment' },
  { value: 'ulip', label: 'ULIP' },
  { value: 'health', label: 'Health' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'home', label: 'Home' },
  { value: 'personal_accident', label: 'Personal Accident' },
];

const PREMIUM_FREQUENCIES = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'semi_annual', label: 'Semi-Annual' },
  { value: 'annual', label: 'Annual' },
  { value: 'single_premium', label: 'Single Premium' },
];

// Policy types that carry an investment / surrender value
const INVESTMENT_POLICY_TYPES = ['endowment', 'ulip'];

interface InsurancePolicy {
  id: number;
  user_id: number;
  asset_id: number;
  nickname: string;
  policy_name: string;
  policy_number: string;
  insurer_name: string;
  policy_type: string;
  insured_name: string;
  sum_assured: number;
  premium_amount: number;
  premium_frequency: string;
  policy_start_date: string;
  policy_end_date?: string;
  current_value: number;
  total_premium_paid?: number;
  nominee?: string;
  is_active: boolean;
  notes?: string;
  annual_premium: number;
  created_at: string;
  updated_at?: string;
}

interface InsuranceSummary {
  total_policies: number;
  active_policies: number;
  total_sum_assured: number;
  total_current_value: number;
  total_annual_premium: number;
  total_premium_paid: number;
  policies: InsurancePolicy[];
}

const emptyForm = {
  nickname: '',
  policy_name: '',
  policy_number: '',
  insurer_name: '',
  policy_type: 'term_life',
  insured_name: '',
  sum_assured: '',
  premium_amount: '',
  premium_frequency: 'annual',
  policy_start_date: '',
  policy_end_date: '',
  current_value: '',
  total_premium_paid: '',
  nominee: '',
  is_active: true,
  notes: '',
};

const getPolicyTypeLabel = (value: string) =>
  POLICY_TYPES.find((t) => t.value === value)?.label || value;

const getPolicyTypeColor = (type: string): 'primary' | 'success' | 'info' | 'warning' | 'secondary' | 'default' => {
  const map: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'secondary' | 'default'> = {
    term_life: 'primary',
    endowment: 'success',
    ulip: 'secondary',
    health: 'info',
    vehicle: 'warning',
    home: 'warning',
    personal_accident: 'default',
  };
  return map[type] || 'default';
};

const getFrequencyLabel = (value: string) =>
  PREMIUM_FREQUENCIES.find((f) => f.value === value)?.label || value;

const Insurance: React.FC = () => {
  const [summary, setSummary] = useState<InsuranceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/insurance/summary');
      setSummary(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load insurance data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const handleOpenAdd = () => {
    setEditingId(null);
    setForm(emptyForm);
    setDialogOpen(true);
  };

  const handleOpenEdit = (policy: InsurancePolicy) => {
    setEditingId(policy.id);
    setForm({
      nickname: policy.nickname,
      policy_name: policy.policy_name,
      policy_number: policy.policy_number,
      insurer_name: policy.insurer_name,
      policy_type: policy.policy_type,
      insured_name: policy.insured_name,
      sum_assured: String(policy.sum_assured),
      premium_amount: String(policy.premium_amount),
      premium_frequency: policy.premium_frequency,
      policy_start_date: policy.policy_start_date,
      policy_end_date: policy.policy_end_date || '',
      current_value: policy.current_value ? String(policy.current_value) : '',
      total_premium_paid: policy.total_premium_paid ? String(policy.total_premium_paid) : '',
      nominee: policy.nominee || '',
      is_active: policy.is_active,
      notes: policy.notes || '',
    });
    setDialogOpen(true);
  };

  const handleClose = () => {
    setDialogOpen(false);
    setEditingId(null);
  };

  const handleSave = async () => {
    if (!form.nickname || !form.policy_name || !form.policy_number || !form.insurer_name ||
        !form.insured_name || !form.sum_assured || !form.premium_amount || !form.policy_start_date) {
      setSnackbarMessage('Please fill in all required fields');
      setSnackbarOpen(true);
      return;
    }
    const payload: any = {
      nickname: form.nickname,
      policy_name: form.policy_name,
      policy_number: form.policy_number,
      insurer_name: form.insurer_name,
      policy_type: form.policy_type,
      insured_name: form.insured_name,
      sum_assured: parseFloat(form.sum_assured),
      premium_amount: parseFloat(form.premium_amount),
      premium_frequency: form.premium_frequency,
      policy_start_date: form.policy_start_date,
      policy_end_date: form.policy_end_date || null,
      current_value: form.current_value ? parseFloat(form.current_value) : null,
      total_premium_paid: form.total_premium_paid ? parseFloat(form.total_premium_paid) : null,
      nominee: form.nominee || null,
      is_active: form.is_active,
      notes: form.notes || null,
    };
    try {
      setSaving(true);
      if (editingId) {
        await api.put(`/insurance/${editingId}`, payload);
        setSnackbarMessage('Insurance policy updated successfully');
      } else {
        await api.post('/insurance/', payload);
        setSnackbarMessage('Insurance policy added successfully');
      }
      setSnackbarOpen(true);
      handleClose();
      fetchData();
    } catch (err: any) {
      setSnackbarMessage(err.response?.data?.detail || 'Failed to save insurance policy');
      setSnackbarOpen(true);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete insurance policy "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/insurance/${id}`);
      setSnackbarMessage('Insurance policy deleted');
      setSnackbarOpen(true);
      fetchData();
    } catch (err: any) {
      setSnackbarMessage(err.response?.data?.detail || 'Failed to delete insurance policy');
      setSnackbarOpen(true);
    }
  };

  const isInvestmentType = INVESTMENT_POLICY_TYPES.includes(form.policy_type);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>;
  }

  const policies = summary?.policies || [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <InsuranceIcon color="primary" />
          <Typography variant="h4">Insurance Policies</Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={handleOpenAdd}>
          Add Policy
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Policies</Typography>
              <Typography variant="h5">{summary?.total_policies ?? 0}</Typography>
              <Typography variant="caption" color="text.secondary">{summary?.active_policies ?? 0} active</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Sum Assured</Typography>
              <Typography variant="h5">{formatCurrency(summary?.total_sum_assured ?? 0)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Current Fund Value</Typography>
              <Typography variant="h5" color="success.main">
                {formatCurrency(summary?.total_current_value ?? 0)}
              </Typography>
              <Typography variant="caption" color="text.secondary">Endowment / ULIP only</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Annual Premium</Typography>
              <Typography variant="h5">{formatCurrency(summary?.total_annual_premium ?? 0)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" gutterBottom>Total Premium Paid</Typography>
              <Typography variant="h5">{formatCurrency(summary?.total_premium_paid ?? 0)}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Policies Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nickname</TableCell>
                <TableCell>Policy Name</TableCell>
                <TableCell>Insurer</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Insured</TableCell>
                <TableCell align="right">Sum Assured</TableCell>
                <TableCell align="right">Premium</TableCell>
                <TableCell align="right">Fund Value</TableCell>
                <TableCell>Expiry</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {policies.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={11} align="center">
                    <Typography color="text.secondary">
                      No insurance policies found. Add one to start tracking.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell>{policy.nickname}</TableCell>
                    <TableCell>
                      <Box>
                        <Typography variant="body2">{policy.policy_name}</Typography>
                        <Typography variant="caption" color="text.secondary">{policy.policy_number}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{policy.insurer_name}</TableCell>
                    <TableCell>
                      <Chip
                        label={getPolicyTypeLabel(policy.policy_type)}
                        color={getPolicyTypeColor(policy.policy_type)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{policy.insured_name}</TableCell>
                    <TableCell align="right">{formatCurrency(policy.sum_assured)}</TableCell>
                    <TableCell align="right">
                      <Box>
                        <Typography variant="body2">{formatCurrency(policy.premium_amount)}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {getFrequencyLabel(policy.premium_frequency)}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      {INVESTMENT_POLICY_TYPES.includes(policy.policy_type) && policy.current_value > 0
                        ? formatCurrency(policy.current_value)
                        : '-'}
                    </TableCell>
                    <TableCell>
                      {policy.policy_end_date
                        ? new Date(policy.policy_end_date).toLocaleDateString('en-IN')
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={policy.is_active ? 'Active' : 'Inactive'}
                        color={policy.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                        <IconButton size="small" color="info" onClick={() => handleOpenEdit(policy)} title="Edit">
                          <Edit fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDelete(policy.id, policy.nickname)} title="Delete">
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
      <Dialog open={dialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>{editingId ? 'Edit Insurance Policy' : 'Add Insurance Policy'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Nickname"
                value={form.nickname}
                onChange={(e) => setForm({ ...form, nickname: e.target.value })}
                required fullWidth
                helperText="e.g., LIC Term Plan, Star Health"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Policy Type</InputLabel>
                <Select
                  value={form.policy_type}
                  label="Policy Type"
                  onChange={(e) => setForm({ ...form, policy_type: e.target.value })}
                >
                  {POLICY_TYPES.map((t) => (
                    <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Policy Name"
                value={form.policy_name}
                onChange={(e) => setForm({ ...form, policy_name: e.target.value })}
                required fullWidth
                helperText="Official name of the policy"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Policy Number"
                value={form.policy_number}
                onChange={(e) => setForm({ ...form, policy_number: e.target.value })}
                required fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Insurer Name"
                value={form.insurer_name}
                onChange={(e) => setForm({ ...form, insurer_name: e.target.value })}
                required fullWidth
                helperText="e.g., LIC, Star Health, HDFC Life"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Insured Name"
                value={form.insured_name}
                onChange={(e) => setForm({ ...form, insured_name: e.target.value })}
                required fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Sum Assured (₹)"
                type="number"
                value={form.sum_assured}
                onChange={(e) => setForm({ ...form, sum_assured: e.target.value })}
                required fullWidth
                inputProps={{ min: 0 }}
                helperText="Coverage / maturity amount"
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <TextField
                label="Premium Amount (₹)"
                type="number"
                value={form.premium_amount}
                onChange={(e) => setForm({ ...form, premium_amount: e.target.value })}
                required fullWidth
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth required>
                <InputLabel>Frequency</InputLabel>
                <Select
                  value={form.premium_frequency}
                  label="Frequency"
                  onChange={(e) => setForm({ ...form, premium_frequency: e.target.value })}
                >
                  {PREMIUM_FREQUENCIES.map((f) => (
                    <MenuItem key={f.value} value={f.value}>{f.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Policy Start Date"
                type="date"
                value={form.policy_start_date}
                onChange={(e) => setForm({ ...form, policy_start_date: e.target.value })}
                required fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Policy End / Maturity Date"
                type="date"
                value={form.policy_end_date}
                onChange={(e) => setForm({ ...form, policy_end_date: e.target.value })}
                fullWidth
                InputLabelProps={{ shrink: true }}
                helperText="Leave empty for renewable / lifelong policies"
              />
            </Grid>
            {isInvestmentType && (
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Current Fund / Surrender Value (₹)"
                  type="number"
                  value={form.current_value}
                  onChange={(e) => setForm({ ...form, current_value: e.target.value })}
                  fullWidth
                  inputProps={{ min: 0 }}
                  helperText="Current fund value or surrender value"
                />
              </Grid>
            )}
            <Grid item xs={12} sm={isInvestmentType ? 6 : 12}>
              <TextField
                label="Total Premium Paid to Date (₹)"
                type="number"
                value={form.total_premium_paid}
                onChange={(e) => setForm({ ...form, total_premium_paid: e.target.value })}
                fullWidth
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Nominee (Optional)"
                value={form.nominee}
                onChange={(e) => setForm({ ...form, nominee: e.target.value })}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    color="primary"
                  />
                }
                label="Policy Active"
                sx={{ mt: 1 }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes (Optional)"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                fullWidth multiline rows={2}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>
            {saving ? <CircularProgress size={24} /> : editingId ? 'Save Changes' : 'Add Policy'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </Box>
  );
};

export default Insurance;
