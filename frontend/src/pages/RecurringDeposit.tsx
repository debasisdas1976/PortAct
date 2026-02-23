import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Switch,
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
  Add,
  AutorenewOutlined,
  ChevronRight,
  Delete,
  Edit,
  ExpandMore,
  Refresh,
  Savings,
} from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelector } from 'react-redux';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { RootState } from '../store';

interface RDAccount {
  id: number;
  portfolio_id?: number;
  bank_name: string;
  nickname?: string;
  account_number?: string;
  monthly_installment: number;
  interest_rate: number;
  start_date: string;
  maturity_date?: string;
  auto_update: boolean;
  notes?: string;
  total_deposited: number;
  current_value: number;
  total_interest_earned: number;
}

interface RDTx {
  id: number;
  asset_id: number;
  transaction_date: string;
  amount: number;
  transaction_type: 'installment' | 'interest';
  description?: string;
  is_auto_generated: boolean;
}

const EMPTY_RD: Partial<RDAccount> = {
  portfolio_id: undefined,
  bank_name: '',
  nickname: '',
  account_number: '',
  monthly_installment: 0,
  interest_rate: 0,
  start_date: new Date().toISOString().split('T')[0],
  auto_update: false,
  notes: '',
};

const fmt = (v: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(v);

const RecurringDeposit: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [rds, setRds] = useState<RDAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [txMap, setTxMap] = useState<Record<number, RDTx[]>>({});
  const [txLoading, setTxLoading] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [genMessage, setGenMessage] = useState('');
  const [saving, setSaving] = useState(false);

  const [rdDlg, setRdDlg] = useState<{
    open: boolean;
    mode: 'add' | 'edit';
    data: Partial<RDAccount>;
  }>({ open: false, mode: 'add', data: { ...EMPTY_RD } });

  const [txDlg, setTxDlg] = useState<{
    open: boolean;
    mode: 'add' | 'edit';
    rdId: number;
    data: {
      id?: number;
      transaction_date: string;
      amount: number;
      transaction_type: 'installment' | 'interest';
      description: string;
    };
  }>({
    open: false,
    mode: 'add',
    rdId: 0,
    data: {
      transaction_date: '',
      amount: 0,
      transaction_type: 'installment',
      description: '',
    },
  });

  const [delRd, setDelRd] = useState<number | null>(null);
  const [delTx, setDelTx] = useState<{ rdId: number; txId: number } | null>(null);

  const loadRds = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/recurring-deposits/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      const data: RDAccount[] = res.data;
      setRds(data);

      const autoAccounts = data.filter((rd) => rd.auto_update);
      for (const rd of autoAccounts) {
        try {
          await api.post(`/recurring-deposits/${rd.id}/generate`);
        } catch (err) {
          console.warn(`Auto-update failed for RD ${rd.id}:`, err);
        }
      }
      if (autoAccounts.length > 0) {
        const res2 = await api.get('/recurring-deposits/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
        setRds(res2.data);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load recurring deposits'));
    } finally {
      setLoading(false);
    }
  }, [notify, selectedPortfolioId]);

  useEffect(() => {
    loadRds();
  }, [loadRds]);

  const loadTransactions = async (rdId: number) => {
    if (txMap[rdId] !== undefined) return;
    setTxLoading(true);
    try {
      const res = await api.get(`/recurring-deposits/${rdId}`);
      setTxMap((prev) => ({ ...prev, [rdId]: res.data.transactions || [] }));
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load transactions'));
    } finally {
      setTxLoading(false);
    }
  };

  const handleExpandRow = async (rdId: number) => {
    if (expandedId === rdId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(rdId);
    await loadTransactions(rdId);
  };

  const handleGenerate = async (rdId: number) => {
    setGenerating(rdId);
    setGenMessage('');
    try {
      const res = await api.post(`/recurring-deposits/${rdId}/generate`);
      const { installments_created, interest_transactions_created, new_current_value } = res.data;
      const total = installments_created + interest_transactions_created;
      setGenMessage(
        total > 0
          ? `Generated ${installments_created} installment(s) + ${interest_transactions_created} interest transaction(s). Current value: ${fmt(new_current_value)}`
          : 'No new transactions to generate.'
      );
      const rdRes = await api.get('/recurring-deposits/');
      setRds(rdRes.data);
      const txRes = await api.get(`/recurring-deposits/${rdId}`);
      setTxMap((prev) => ({ ...prev, [rdId]: txRes.data.transactions || [] }));
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to generate transactions'));
    } finally {
      setGenerating(null);
    }
  };

  const openAddRd = () => setRdDlg({ open: true, mode: 'add', data: { ...EMPTY_RD, portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : undefined) } });
  const openEditRd = (rd: RDAccount) =>
    setRdDlg({ open: true, mode: 'edit', data: { ...rd } });
  const closeRdDlg = () => setRdDlg((p) => ({ ...p, open: false }));

  const handleSaveRd = async () => {
    setSaving(true);
    try {
      const payload = {
        portfolio_id: rdDlg.data.portfolio_id || undefined,
        bank_name: rdDlg.data.bank_name,
        nickname: rdDlg.data.nickname || null,
        account_number: rdDlg.data.account_number || null,
        monthly_installment: rdDlg.data.monthly_installment,
        interest_rate: rdDlg.data.interest_rate,
        start_date: rdDlg.data.start_date,
        maturity_date: rdDlg.data.maturity_date || null,
        auto_update: rdDlg.data.auto_update || false,
        notes: rdDlg.data.notes || null,
      };
      if (rdDlg.mode === 'add') {
        await api.post('/recurring-deposits/', payload);
        notify.success('Recurring deposit added successfully');
      } else {
        await api.put(`/recurring-deposits/${rdDlg.data.id}`, payload);
        notify.success('Recurring deposit updated successfully');
      }
      closeRdDlg();
      await loadRds();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save recurring deposit'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRd = async () => {
    if (!delRd) return;
    try {
      await api.delete(`/recurring-deposits/${delRd}`);
      setDelRd(null);
      if (expandedId === delRd) setExpandedId(null);
      setTxMap((prev) => {
        const n = { ...prev };
        delete n[delRd];
        return n;
      });
      await loadRds();
      notify.success('Recurring deposit deleted successfully');
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete recurring deposit'));
    }
  };

  const openAddTx = (rdId: number) =>
    setTxDlg({
      open: true,
      mode: 'add',
      rdId,
      data: {
        transaction_date: new Date().toISOString().split('T')[0],
        amount: 0,
        transaction_type: 'installment',
        description: '',
      },
    });

  const openEditTx = (rdId: number, tx: RDTx) =>
    setTxDlg({
      open: true,
      mode: 'edit',
      rdId,
      data: {
        id: tx.id,
        transaction_date: tx.transaction_date,
        amount: tx.amount,
        transaction_type: tx.transaction_type,
        description: tx.description || '',
      },
    });

  const closeTxDlg = () => setTxDlg((p) => ({ ...p, open: false }));

  const handleSaveTx = async () => {
    setSaving(true);
    const { rdId, data, mode } = txDlg;
    try {
      const payload = {
        transaction_date: data.transaction_date,
        amount: data.amount,
        transaction_type: data.transaction_type,
        description: data.description || null,
      };
      if (mode === 'add') {
        await api.post(`/recurring-deposits/${rdId}/transactions`, payload);
        notify.success('Transaction added successfully');
      } else {
        await api.put(`/recurring-deposits/${rdId}/transactions/${data.id}`, payload);
        notify.success('Transaction updated successfully');
      }
      closeTxDlg();
      const txRes = await api.get(`/recurring-deposits/${rdId}`);
      setTxMap((prev) => ({ ...prev, [rdId]: txRes.data.transactions || [] }));
      const rdRes = await api.get('/recurring-deposits/');
      setRds(rdRes.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save transaction'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTx = async () => {
    if (!delTx) return;
    const { rdId, txId } = delTx;
    try {
      await api.delete(`/recurring-deposits/${rdId}/transactions/${txId}`);
      setDelTx(null);
      const txRes = await api.get(`/recurring-deposits/${rdId}`);
      setTxMap((prev) => ({ ...prev, [rdId]: txRes.data.transactions || [] }));
      const rdRes = await api.get('/recurring-deposits/');
      setRds(rdRes.data);
      notify.success('Transaction deleted successfully');
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete transaction'));
    }
  };

  const totalDeposited = rds.reduce((s, rd) => s + rd.total_deposited, 0);
  const totalValue = rds.reduce((s, rd) => s + rd.current_value, 0);
  const totalInterest = rds.reduce((s, rd) => s + rd.total_interest_earned, 0);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Savings color="primary" />
          <Typography variant="h4">Recurring Deposits</Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={openAddRd}>
          Add RD
        </Button>
      </Box>

      {genMessage && (
        <Alert severity="info" sx={{ mb: 2 }} onClose={() => setGenMessage('')}>
          {genMessage}
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        {[
          { label: 'Total RDs', value: String(rds.length) },
          { label: 'Total Deposited', value: fmt(totalDeposited) },
          { label: 'Current Value', value: fmt(totalValue) },
          { label: 'Total Interest Earned', value: fmt(totalInterest) },
        ].map(({ label, value }) => (
          <Grid item xs={12} sm={6} md={3} key={label} sx={{ display: 'flex' }}>
            <Card sx={{ width: '100%' }}>
              <CardContent>
                <Typography color="text.secondary" variant="body2">
                  {label}
                </Typography>
                <Typography variant="h5">{value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell />
              <TableCell><strong>Bank</strong></TableCell>
              <TableCell><strong>Nickname</strong></TableCell>
              <TableCell align="right"><strong>Monthly EMI</strong></TableCell>
              <TableCell align="right"><strong>Rate</strong></TableCell>
              <TableCell><strong>Start</strong></TableCell>
              <TableCell><strong>Maturity</strong></TableCell>
              <TableCell align="right"><strong>Total Deposited</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="center"><strong>Auto</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rds.length === 0 ? (
              <TableRow>
                <TableCell colSpan={11} align="center">
                  <Typography color="text.secondary">
                    No recurring deposits found. Click "Add RD" to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              rds.map((rd) => (
                <React.Fragment key={rd.id}>
                  <TableRow
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleExpandRow(rd.id)}
                  >
                    <TableCell padding="checkbox">
                      <IconButton size="small">
                        {expandedId === rd.id ? <ExpandMore /> : <ChevronRight />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {rd.bank_name}
                      </Typography>
                      {rd.account_number && (
                        <Typography variant="caption" color="text.secondary">
                          ••••&nbsp;{rd.account_number.slice(-4)}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{rd.nickname || '—'}</TableCell>
                    <TableCell align="right">{fmt(rd.monthly_installment)}/mo</TableCell>
                    <TableCell align="right">{rd.interest_rate}%</TableCell>
                    <TableCell>{rd.start_date}</TableCell>
                    <TableCell>{rd.maturity_date || '—'}</TableCell>
                    <TableCell align="right">{fmt(rd.total_deposited)}</TableCell>
                    <TableCell align="right">
                      <Typography fontWeight="medium">{fmt(rd.current_value)}</Typography>
                    </TableCell>
                    <TableCell align="center">
                      {rd.auto_update && (
                        <Chip
                          label="Auto"
                          color="primary"
                          size="small"
                          icon={<AutorenewOutlined />}
                        />
                      )}
                    </TableCell>
                    <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="Generate Transactions Now">
                        <span>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleGenerate(rd.id)}
                            disabled={generating === rd.id}
                          >
                            {generating === rd.id ? (
                              <CircularProgress size={16} />
                            ) : (
                              <Refresh />
                            )}
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => openEditRd(rd)}>
                          <Edit fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => setDelRd(rd.id)}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>

                  <TableRow>
                    <TableCell colSpan={11} sx={{ p: 0, borderBottom: 0 }}>
                      <Collapse in={expandedId === rd.id} unmountOnExit>
                        <Box
                          sx={{
                            m: 2,
                            border: '1px solid',
                            borderColor: 'divider',
                            borderRadius: 1,
                          }}
                        >
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              p: 1.5,
                              borderBottom: '1px solid',
                              borderColor: 'divider',
                              backgroundColor: 'action.hover',
                            }}
                          >
                            <Typography variant="subtitle2">Transactions</Typography>
                            <Button
                              size="small"
                              startIcon={<Add />}
                              onClick={(e) => {
                                e.stopPropagation();
                                openAddTx(rd.id);
                              }}
                            >
                              Add Transaction
                            </Button>
                          </Box>

                          {txLoading && expandedId === rd.id ? (
                            <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
                              <CircularProgress size={24} />
                            </Box>
                          ) : (txMap[rd.id] || []).length === 0 ? (
                            <Typography color="text.secondary" sx={{ p: 2 }} variant="body2">
                              No transactions yet. Use the Refresh button to generate installments and interest automatically.
                            </Typography>
                          ) : (
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell><strong>Date</strong></TableCell>
                                  <TableCell><strong>Type</strong></TableCell>
                                  <TableCell align="right"><strong>Amount</strong></TableCell>
                                  <TableCell><strong>Description</strong></TableCell>
                                  <TableCell align="center"><strong>Source</strong></TableCell>
                                  <TableCell align="center"><strong>Actions</strong></TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {(txMap[rd.id] || []).map((tx) => (
                                  <TableRow key={tx.id} hover>
                                    <TableCell>{tx.transaction_date}</TableCell>
                                    <TableCell>
                                      <Chip
                                        label={
                                          tx.transaction_type === 'interest'
                                            ? 'Interest'
                                            : 'Installment'
                                        }
                                        size="small"
                                        color={
                                          tx.transaction_type === 'interest' ? 'success' : 'info'
                                        }
                                        variant="outlined"
                                      />
                                    </TableCell>
                                    <TableCell
                                      align="right"
                                      sx={{
                                        color:
                                          tx.transaction_type === 'interest'
                                            ? 'success.main'
                                            : 'text.primary',
                                      }}
                                    >
                                      {fmt(tx.amount)}
                                    </TableCell>
                                    <TableCell>{tx.description || '—'}</TableCell>
                                    <TableCell align="center">
                                      <Chip
                                        label={tx.is_auto_generated ? 'Auto' : 'Manual'}
                                        size="small"
                                        color={tx.is_auto_generated ? 'default' : 'secondary'}
                                        variant="outlined"
                                      />
                                    </TableCell>
                                    <TableCell align="center">
                                      <Tooltip title="Edit">
                                        <IconButton
                                          size="small"
                                          onClick={() => openEditTx(rd.id, tx)}
                                        >
                                          <Edit fontSize="small" />
                                        </IconButton>
                                      </Tooltip>
                                      <Tooltip title="Delete">
                                        <IconButton
                                          size="small"
                                          color="error"
                                          onClick={() =>
                                            setDelTx({ rdId: rd.id, txId: tx.id })
                                          }
                                        >
                                          <Delete fontSize="small" />
                                        </IconButton>
                                      </Tooltip>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit RD Dialog */}
      <Dialog open={rdDlg.open} onClose={closeRdDlg} maxWidth="sm" fullWidth>
        <DialogTitle>
          {rdDlg.mode === 'add' ? 'Add Recurring Deposit' : 'Edit Recurring Deposit'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Bank Name"
                fullWidth
                required
                value={rdDlg.data.bank_name || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({ ...p, data: { ...p.data, bank_name: e.target.value } }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Nickname (optional)"
                fullWidth
                value={rdDlg.data.nickname || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({ ...p, data: { ...p.data, nickname: e.target.value } }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="Portfolio"
                value={rdDlg.data.portfolio_id || ''}
                onChange={(e) => setRdDlg(p => ({ ...p, data: { ...p.data, portfolio_id: e.target.value ? Number(e.target.value) : undefined } }))}
              >
                {portfolios.map((p: any) => (
                  <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Account Number (optional)"
                fullWidth
                value={rdDlg.data.account_number || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({
                    ...p,
                    data: { ...p.data, account_number: e.target.value },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Monthly Installment (₹)"
                fullWidth
                required
                type="number"
                inputProps={{ min: 0, step: 500 }}
                value={rdDlg.data.monthly_installment || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({
                    ...p,
                    data: {
                      ...p.data,
                      monthly_installment: parseFloat(e.target.value) || 0,
                    },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Annual Interest Rate (%)"
                fullWidth
                required
                type="number"
                inputProps={{ min: 0, max: 50, step: 0.01 }}
                value={rdDlg.data.interest_rate || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({
                    ...p,
                    data: { ...p.data, interest_rate: parseFloat(e.target.value) || 0 },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Start Date"
                fullWidth
                required
                type="date"
                InputLabelProps={{ shrink: true }}
                value={rdDlg.data.start_date || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({ ...p, data: { ...p.data, start_date: e.target.value } }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Maturity Date (optional)"
                fullWidth
                type="date"
                InputLabelProps={{ shrink: true }}
                value={rdDlg.data.maturity_date || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({
                    ...p,
                    data: { ...p.data, maturity_date: e.target.value || undefined },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={rdDlg.data.auto_update || false}
                    onChange={(e) =>
                      setRdDlg((p) => ({
                        ...p,
                        data: { ...p.data, auto_update: e.target.checked },
                      }))
                    }
                    color="primary"
                  />
                }
                label="Update Automatically (auto-generate installments and interest on page load)"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes (optional)"
                fullWidth
                multiline
                rows={2}
                value={rdDlg.data.notes || ''}
                onChange={(e) =>
                  setRdDlg((p) => ({ ...p, data: { ...p.data, notes: e.target.value } }))
                }
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeRdDlg}>Cancel</Button>
          <Button onClick={handleSaveRd} variant="contained" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add/Edit Transaction Dialog */}
      <Dialog open={txDlg.open} onClose={closeTxDlg} maxWidth="xs" fullWidth>
        <DialogTitle>
          {txDlg.mode === 'add' ? 'Add Transaction' : 'Edit Transaction'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12}>
              <TextField
                label="Date"
                fullWidth
                required
                type="date"
                InputLabelProps={{ shrink: true }}
                value={txDlg.data.transaction_date || ''}
                onChange={(e) =>
                  setTxDlg((p) => ({
                    ...p,
                    data: { ...p.data, transaction_date: e.target.value },
                  }))
                }
              />
            </Grid>
            {txDlg.mode === 'add' && (
              <Grid item xs={12}>
                <FormControl fullWidth required>
                  <InputLabel>Transaction Type</InputLabel>
                  <Select
                    label="Transaction Type"
                    value={txDlg.data.transaction_type}
                    onChange={(e) =>
                      setTxDlg((p) => ({
                        ...p,
                        data: {
                          ...p.data,
                          transaction_type: e.target.value as 'installment' | 'interest',
                        },
                      }))
                    }
                  >
                    <MenuItem value="installment">Installment</MenuItem>
                    <MenuItem value="interest">Interest</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            )}
            <Grid item xs={12}>
              <TextField
                label="Amount (₹)"
                fullWidth
                required
                type="number"
                inputProps={{ min: 0, step: 0.01 }}
                value={txDlg.data.amount || ''}
                onChange={(e) =>
                  setTxDlg((p) => ({
                    ...p,
                    data: { ...p.data, amount: parseFloat(e.target.value) || 0 },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description (optional)"
                fullWidth
                value={txDlg.data.description || ''}
                onChange={(e) =>
                  setTxDlg((p) => ({
                    ...p,
                    data: { ...p.data, description: e.target.value },
                  }))
                }
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeTxDlg}>Cancel</Button>
          <Button onClick={handleSaveTx} variant="contained" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete RD Confirmation */}
      <Dialog open={!!delRd} onClose={() => setDelRd(null)}>
        <DialogTitle>Delete Recurring Deposit?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will permanently delete the RD and all its transactions. This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDelRd(null)}>Cancel</Button>
          <Button onClick={handleDeleteRd} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Transaction Confirmation */}
      <Dialog open={!!delTx} onClose={() => setDelTx(null)}>
        <DialogTitle>Delete Transaction?</DialogTitle>
        <DialogContent>
          <DialogContentText>Are you sure you want to delete this transaction?</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDelTx(null)}>Cancel</Button>
          <Button onClick={handleDeleteTx} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RecurringDeposit;

// Made with Bob
