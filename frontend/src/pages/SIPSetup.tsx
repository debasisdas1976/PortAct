import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  Edit as EditIcon,
  PlayArrow as ActiveIcon,
  Pause as PausedIcon,
} from '@mui/icons-material';
import api, { mfPlansAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

// ── Types ──

interface MFAsset {
  id: number;
  name: string;
  symbol: string;
  isin?: string;
  asset_type: string;
}

interface MFPlan {
  id: number;
  plan_type: string;
  asset_id: number;
  asset_name: string;
  amount: number;
  frequency: string;
  execution_day: number | null;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  last_executed_date: string | null;
  notes: string | null;
  created_at: string;
}

interface PlanForm {
  asset_id: number | '';
  amount: string;
  frequency: string;
  execution_day: string;
  start_date: string;
  end_date: string;
  notes: string;
}

// ── Helpers ──

const MF_TYPES = ['equity_mutual_fund', 'hybrid_mutual_fund', 'debt_mutual_fund'];

const FREQUENCIES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'fortnightly', label: 'Fortnightly' },
  { value: 'monthly', label: 'Monthly' },
];

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

const defaultForm = (): PlanForm => ({
  asset_id: '',
  amount: '',
  frequency: 'monthly',
  execution_day: '1',
  start_date: '',
  end_date: '',
  notes: '',
});

// ── Component ──

const SIPSetup: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();

  const [mfAssets, setMFAssets] = useState<MFAsset[]>([]);
  const [plans, setPlans] = useState<MFPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  const [form, setForm] = useState<PlanForm>(defaultForm());
  const [submitting, setSubmitting] = useState(false);

  // Load MF assets and plans
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const params: any = {};
        if (selectedPortfolioId) params.portfolio_id = selectedPortfolioId;
        const [assetsRes, plansRes] = await Promise.all([
          api.get('/assets/', { params }),
          mfPlansAPI.getAll('sip'),
        ]);
        const mfs = (assetsRes.data || []).filter((a: any) =>
          MF_TYPES.includes(a.asset_type?.toLowerCase())
        );
        setMFAssets(mfs);
        setPlans(plansRes.plans || []);
      } catch (err) {
        notify.error(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedPortfolioId]);

  const refreshPlans = async () => {
    try {
      const res = await mfPlansAPI.getAll('sip');
      setPlans(res.plans || []);
    } catch (err) {
      notify.error(getErrorMessage(err));
    }
  };

  const openCreateDialog = () => {
    setEditingPlanId(null);
    setForm(defaultForm());
    setDialogOpen(true);
  };

  const openEditDialog = (plan: MFPlan) => {
    setEditingPlanId(plan.id);
    setForm({
      asset_id: plan.asset_id,
      amount: String(plan.amount),
      frequency: plan.frequency,
      execution_day: String(plan.execution_day ?? '1'),
      start_date: plan.start_date,
      end_date: plan.end_date || '',
      notes: plan.notes || '',
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!form.asset_id || !form.amount || !form.start_date) {
      notify.error('Please fill in all required fields');
      return;
    }
    try {
      setSubmitting(true);
      const payload: any = {
        plan_type: 'sip',
        asset_id: form.asset_id,
        amount: parseFloat(form.amount),
        frequency: form.frequency,
        start_date: form.start_date,
        notes: form.notes || null,
      };
      if (form.end_date) payload.end_date = form.end_date;
      if (form.frequency === 'monthly') {
        payload.execution_day = parseInt(form.execution_day, 10);
      } else if (form.frequency === 'weekly') {
        payload.execution_day = parseInt(form.execution_day, 10);
      }

      if (editingPlanId) {
        const { plan_type, asset_id, ...updatePayload } = payload;
        await mfPlansAPI.update(editingPlanId, updatePayload);
        notify.success('SIP plan updated');
      } else {
        await mfPlansAPI.create(payload);
        notify.success('SIP plan created');
      }
      setDialogOpen(false);
      refreshPlans();
    } catch (err) {
      notify.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = async (planId: number) => {
    try {
      await mfPlansAPI.toggle(planId);
      refreshPlans();
    } catch (err) {
      notify.error(getErrorMessage(err));
    }
  };

  const handleDelete = async (planId: number) => {
    if (!window.confirm('Delete this SIP plan?')) return;
    try {
      await mfPlansAPI.delete(planId);
      notify.success('SIP plan deleted');
      refreshPlans();
    } catch (err) {
      notify.error(getErrorMessage(err));
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h5">SIP Setup</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>
          Add SIP
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Set up Systematic Investment Plans for your mutual funds. The system will automatically
        create BUY transactions on the scheduled dates using the latest NAV.
      </Typography>

      {plans.length === 0 ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          No SIP plans configured yet. Click the + button to add your first SIP.
        </Alert>
      ) : (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Fund</TableCell>
                <TableCell align="right">Amount</TableCell>
                <TableCell>Frequency</TableCell>
                <TableCell>Day</TableCell>
                <TableCell>Start</TableCell>
                <TableCell>End</TableCell>
                <TableCell>Last Executed</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {plans.map((plan) => (
                <TableRow key={plan.id}>
                  <TableCell sx={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {plan.asset_name}
                  </TableCell>
                  <TableCell align="right">{formatCurrency(plan.amount)}</TableCell>
                  <TableCell sx={{ textTransform: 'capitalize' }}>{plan.frequency}</TableCell>
                  <TableCell>
                    {plan.frequency === 'monthly' ? `Day ${plan.execution_day}` :
                     plan.frequency === 'weekly' ? WEEKDAYS[plan.execution_day ?? 0] : '—'}
                  </TableCell>
                  <TableCell>{formatDate(plan.start_date)}</TableCell>
                  <TableCell>{formatDate(plan.end_date)}</TableCell>
                  <TableCell>{formatDate(plan.last_executed_date)}</TableCell>
                  <TableCell>
                    <Chip
                      label={plan.is_active ? 'Active' : 'Paused'}
                      color={plan.is_active ? 'success' : 'default'}
                      size="small"
                      onClick={() => handleToggle(plan.id)}
                      icon={plan.is_active ? <ActiveIcon /> : <PausedIcon />}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => openEditDialog(plan)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" color="error" onClick={() => handleDelete(plan.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingPlanId ? 'Edit SIP Plan' : 'New SIP Plan'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              select
              label="Mutual Fund"
              value={form.asset_id}
              onChange={(e) => setForm({ ...form, asset_id: Number(e.target.value) })}
              disabled={!!editingPlanId}
              fullWidth
              required
            >
              {mfAssets.map((a) => (
                <MenuItem key={a.id} value={a.id}>
                  {a.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="SIP Amount (INR)"
              type="number"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              fullWidth
              required
              inputProps={{ min: 1 }}
            />

            <TextField
              select
              label="Frequency"
              value={form.frequency}
              onChange={(e) => setForm({ ...form, frequency: e.target.value })}
              fullWidth
            >
              {FREQUENCIES.map((f) => (
                <MenuItem key={f.value} value={f.value}>
                  {f.label}
                </MenuItem>
              ))}
            </TextField>

            {form.frequency === 'monthly' && (
              <TextField
                select
                label="Day of Month"
                value={form.execution_day}
                onChange={(e) => setForm({ ...form, execution_day: e.target.value })}
                fullWidth
              >
                {Array.from({ length: 28 }, (_, i) => (
                  <MenuItem key={i + 1} value={String(i + 1)}>
                    {i + 1}
                  </MenuItem>
                ))}
              </TextField>
            )}

            {form.frequency === 'weekly' && (
              <TextField
                select
                label="Day of Week"
                value={form.execution_day}
                onChange={(e) => setForm({ ...form, execution_day: e.target.value })}
                fullWidth
              >
                {WEEKDAYS.map((day, idx) => (
                  <MenuItem key={idx} value={String(idx)}>
                    {day}
                  </MenuItem>
                ))}
              </TextField>
            )}

            <TextField
              label="Start Date"
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              fullWidth
              required
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              label="End Date (optional)"
              type="date"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              fullWidth
              InputLabelProps={{ shrink: true }}
              helperText="Leave blank for perpetual SIP"
            />

            <TextField
              label="Notes (optional)"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={submitting}>
            {submitting ? 'Saving...' : editingPlanId ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SIPSetup;
