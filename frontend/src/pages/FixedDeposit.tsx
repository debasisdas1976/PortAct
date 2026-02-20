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
  AccountBalance,
  Add,
  AutorenewOutlined,
  ChevronRight,
  Delete,
  Edit,
  ExpandMore,
  Refresh,
} from '@mui/icons-material';
import api from '../services/api';

interface FDAccount {
  id: number;
  bank_name: string;
  nickname?: string;
  account_number?: string;
  principal_amount: number;
  interest_rate: number;
  interest_type: 'simple' | 'compound';
  compounding_frequency: string;
  start_date: string;
  maturity_date?: string;
  auto_update: boolean;
  notes?: string;
  current_value: number;
  total_interest_earned: number;
}

interface FDTx {
  id: number;
  asset_id: number;
  transaction_date: string;
  amount: number;
  description?: string;
  is_auto_generated: boolean;
}

const EMPTY_FD: Partial<FDAccount> = {
  bank_name: '',
  nickname: '',
  account_number: '',
  principal_amount: 0,
  interest_rate: 0,
  interest_type: 'simple',
  compounding_frequency: 'annually',
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

const FixedDeposit: React.FC = () => {
  const [fds, setFds] = useState<FDAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [txMap, setTxMap] = useState<Record<number, FDTx[]>>({});
  const [txLoading, setTxLoading] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [genMessage, setGenMessage] = useState('');
  const [saving, setSaving] = useState(false);

  const [fdDlg, setFdDlg] = useState<{
    open: boolean;
    mode: 'add' | 'edit';
    data: Partial<FDAccount>;
  }>({ open: false, mode: 'add', data: { ...EMPTY_FD } });

  const [txDlg, setTxDlg] = useState<{
    open: boolean;
    mode: 'add' | 'edit';
    fdId: number;
    data: { id?: number; transaction_date: string; amount: number; description: string };
  }>({
    open: false,
    mode: 'add',
    fdId: 0,
    data: { transaction_date: '', amount: 0, description: '' },
  });

  const [delFd, setDelFd] = useState<number | null>(null);
  const [delTx, setDelTx] = useState<{ fdId: number; txId: number } | null>(null);

  const loadFds = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/fixed-deposits/');
      const data: FDAccount[] = res.data;
      setFds(data);

      const autoAccounts = data.filter((fd) => fd.auto_update);
      for (const fd of autoAccounts) {
        try {
          await api.post(`/fixed-deposits/${fd.id}/generate-interest`);
        } catch {
          // silently skip
        }
      }
      if (autoAccounts.length > 0) {
        const res2 = await api.get('/fixed-deposits/');
        setFds(res2.data);
      }
    } catch {
      setError('Failed to load fixed deposits');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFds();
  }, [loadFds]);

  const loadTransactions = async (fdId: number) => {
    if (txMap[fdId] !== undefined) return;
    setTxLoading(true);
    try {
      const res = await api.get(`/fixed-deposits/${fdId}`);
      setTxMap((prev) => ({ ...prev, [fdId]: res.data.transactions || [] }));
    } catch {
      setError('Failed to load transactions');
    } finally {
      setTxLoading(false);
    }
  };

  const handleExpandRow = async (fdId: number) => {
    if (expandedId === fdId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(fdId);
    await loadTransactions(fdId);
  };

  const handleGenerateInterest = async (fdId: number) => {
    setGenerating(fdId);
    setGenMessage('');
    try {
      const res = await api.post(`/fixed-deposits/${fdId}/generate-interest`);
      const { transactions_created, new_current_value } = res.data;
      setGenMessage(
        transactions_created > 0
          ? `Generated ${transactions_created} interest transaction(s). Current value: ${fmt(new_current_value)}`
          : 'No new interest to generate.'
      );
      const fdRes = await api.get('/fixed-deposits/');
      setFds(fdRes.data);
      const txRes = await api.get(`/fixed-deposits/${fdId}`);
      setTxMap((prev) => ({ ...prev, [fdId]: txRes.data.transactions || [] }));
    } catch {
      setError('Failed to generate interest');
    } finally {
      setGenerating(null);
    }
  };

  const openAddFd = () => setFdDlg({ open: true, mode: 'add', data: { ...EMPTY_FD } });
  const openEditFd = (fd: FDAccount) =>
    setFdDlg({ open: true, mode: 'edit', data: { ...fd } });
  const closeFdDlg = () => setFdDlg((p) => ({ ...p, open: false }));

  const handleSaveFd = async () => {
    setSaving(true);
    try {
      const payload = {
        bank_name: fdDlg.data.bank_name,
        nickname: fdDlg.data.nickname || null,
        account_number: fdDlg.data.account_number || null,
        principal_amount: fdDlg.data.principal_amount,
        interest_rate: fdDlg.data.interest_rate,
        interest_type: fdDlg.data.interest_type,
        compounding_frequency: fdDlg.data.compounding_frequency || 'annually',
        start_date: fdDlg.data.start_date,
        maturity_date: fdDlg.data.maturity_date || null,
        auto_update: fdDlg.data.auto_update || false,
        notes: fdDlg.data.notes || null,
      };
      if (fdDlg.mode === 'add') {
        await api.post('/fixed-deposits/', payload);
      } else {
        await api.put(`/fixed-deposits/${fdDlg.data.id}`, payload);
      }
      closeFdDlg();
      await loadFds();
    } catch {
      setError('Failed to save fixed deposit');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFd = async () => {
    if (!delFd) return;
    try {
      await api.delete(`/fixed-deposits/${delFd}`);
      setDelFd(null);
      if (expandedId === delFd) setExpandedId(null);
      setTxMap((prev) => {
        const n = { ...prev };
        delete n[delFd];
        return n;
      });
      await loadFds();
    } catch {
      setError('Failed to delete fixed deposit');
    }
  };

  const openAddTx = (fdId: number) =>
    setTxDlg({
      open: true,
      mode: 'add',
      fdId,
      data: {
        transaction_date: new Date().toISOString().split('T')[0],
        amount: 0,
        description: '',
      },
    });

  const openEditTx = (fdId: number, tx: FDTx) =>
    setTxDlg({
      open: true,
      mode: 'edit',
      fdId,
      data: {
        id: tx.id,
        transaction_date: tx.transaction_date,
        amount: tx.amount,
        description: tx.description || '',
      },
    });

  const closeTxDlg = () => setTxDlg((p) => ({ ...p, open: false }));

  const handleSaveTx = async () => {
    setSaving(true);
    const { fdId, data, mode } = txDlg;
    try {
      const payload = {
        transaction_date: data.transaction_date,
        amount: data.amount,
        description: data.description || null,
      };
      if (mode === 'add') {
        await api.post(`/fixed-deposits/${fdId}/transactions`, payload);
      } else {
        await api.put(`/fixed-deposits/${fdId}/transactions/${data.id}`, payload);
      }
      closeTxDlg();
      const txRes = await api.get(`/fixed-deposits/${fdId}`);
      setTxMap((prev) => ({ ...prev, [fdId]: txRes.data.transactions || [] }));
      const fdRes = await api.get('/fixed-deposits/');
      setFds(fdRes.data);
    } catch {
      setError('Failed to save transaction');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTx = async () => {
    if (!delTx) return;
    const { fdId, txId } = delTx;
    try {
      await api.delete(`/fixed-deposits/${fdId}/transactions/${txId}`);
      setDelTx(null);
      const txRes = await api.get(`/fixed-deposits/${fdId}`);
      setTxMap((prev) => ({ ...prev, [fdId]: txRes.data.transactions || [] }));
      const fdRes = await api.get('/fixed-deposits/');
      setFds(fdRes.data);
    } catch {
      setError('Failed to delete transaction');
    }
  };

  const totalPrincipal = fds.reduce((s, fd) => s + fd.principal_amount, 0);
  const totalValue = fds.reduce((s, fd) => s + fd.current_value, 0);
  const totalInterest = fds.reduce((s, fd) => s + fd.total_interest_earned, 0);

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
          <AccountBalance color="primary" />
          <Typography variant="h4">Fixed Deposits</Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={openAddFd}>
          Add FD
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {genMessage && (
        <Alert severity="info" sx={{ mb: 2 }} onClose={() => setGenMessage('')}>
          {genMessage}
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        {[
          { label: 'Total FDs', value: String(fds.length) },
          { label: 'Total Principal', value: fmt(totalPrincipal) },
          { label: 'Current Value', value: fmt(totalValue) },
          { label: 'Total Interest Earned', value: fmt(totalInterest) },
        ].map(({ label, value }) => (
          <Grid item xs={12} sm={6} md={3} key={label}>
            <Card>
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
              <TableCell align="right"><strong>Principal</strong></TableCell>
              <TableCell align="right"><strong>Rate</strong></TableCell>
              <TableCell><strong>Type</strong></TableCell>
              <TableCell><strong>Maturity</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>Interest Earned</strong></TableCell>
              <TableCell align="center"><strong>Auto</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {fds.length === 0 ? (
              <TableRow>
                <TableCell colSpan={11} align="center">
                  <Typography color="text.secondary">
                    No fixed deposits found. Click "Add FD" to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              fds.map((fd) => (
                <React.Fragment key={fd.id}>
                  <TableRow
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleExpandRow(fd.id)}
                  >
                    <TableCell padding="checkbox">
                      <IconButton size="small">
                        {expandedId === fd.id ? <ExpandMore /> : <ChevronRight />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {fd.bank_name}
                      </Typography>
                      {fd.account_number && (
                        <Typography variant="caption" color="text.secondary">
                          ••••&nbsp;{fd.account_number.slice(-4)}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{fd.nickname || '—'}</TableCell>
                    <TableCell align="right">{fmt(fd.principal_amount)}</TableCell>
                    <TableCell align="right">{fd.interest_rate}%</TableCell>
                    <TableCell>
                      <Chip
                        label={
                          fd.interest_type === 'compound'
                            ? `Compound (${fd.compounding_frequency.replace('_', ' ')})`
                            : 'Simple'
                        }
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{fd.maturity_date || '—'}</TableCell>
                    <TableCell align="right">
                      <Typography fontWeight="medium">{fmt(fd.current_value)}</Typography>
                    </TableCell>
                    <TableCell align="right" sx={{ color: 'success.main' }}>
                      {fmt(fd.total_interest_earned)}
                    </TableCell>
                    <TableCell align="center">
                      {fd.auto_update && (
                        <Chip
                          label="Auto"
                          color="primary"
                          size="small"
                          icon={<AutorenewOutlined />}
                        />
                      )}
                    </TableCell>
                    <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="Generate Interest Now">
                        <span>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleGenerateInterest(fd.id)}
                            disabled={generating === fd.id}
                          >
                            {generating === fd.id ? (
                              <CircularProgress size={16} />
                            ) : (
                              <Refresh />
                            )}
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => openEditFd(fd)}>
                          <Edit fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => setDelFd(fd.id)}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>

                  <TableRow>
                    <TableCell colSpan={11} sx={{ p: 0, borderBottom: 0 }}>
                      <Collapse in={expandedId === fd.id} unmountOnExit>
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
                            <Typography variant="subtitle2">Interest Transactions</Typography>
                            <Button
                              size="small"
                              startIcon={<Add />}
                              onClick={(e) => {
                                e.stopPropagation();
                                openAddTx(fd.id);
                              }}
                            >
                              Add Transaction
                            </Button>
                          </Box>

                          {txLoading && expandedId === fd.id ? (
                            <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
                              <CircularProgress size={24} />
                            </Box>
                          ) : (txMap[fd.id] || []).length === 0 ? (
                            <Typography color="text.secondary" sx={{ p: 2 }} variant="body2">
                              No transactions yet. Use the Refresh button to generate interest automatically.
                            </Typography>
                          ) : (
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell><strong>Date</strong></TableCell>
                                  <TableCell align="right"><strong>Amount</strong></TableCell>
                                  <TableCell><strong>Description</strong></TableCell>
                                  <TableCell align="center"><strong>Source</strong></TableCell>
                                  <TableCell align="center"><strong>Actions</strong></TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {(txMap[fd.id] || []).map((tx) => (
                                  <TableRow key={tx.id} hover>
                                    <TableCell>{tx.transaction_date}</TableCell>
                                    <TableCell align="right" sx={{ color: 'success.main' }}>
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
                                          onClick={() => openEditTx(fd.id, tx)}
                                        >
                                          <Edit fontSize="small" />
                                        </IconButton>
                                      </Tooltip>
                                      <Tooltip title="Delete">
                                        <IconButton
                                          size="small"
                                          color="error"
                                          onClick={() =>
                                            setDelTx({ fdId: fd.id, txId: tx.id })
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

      {/* Add/Edit FD Dialog */}
      <Dialog open={fdDlg.open} onClose={closeFdDlg} maxWidth="sm" fullWidth>
        <DialogTitle>
          {fdDlg.mode === 'add' ? 'Add Fixed Deposit' : 'Edit Fixed Deposit'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Bank Name"
                fullWidth
                required
                value={fdDlg.data.bank_name || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({ ...p, data: { ...p.data, bank_name: e.target.value } }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Nickname (optional)"
                fullWidth
                value={fdDlg.data.nickname || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({ ...p, data: { ...p.data, nickname: e.target.value } }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Account Number (optional)"
                fullWidth
                value={fdDlg.data.account_number || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({
                    ...p,
                    data: { ...p.data, account_number: e.target.value },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Principal Amount (₹)"
                fullWidth
                required
                type="number"
                inputProps={{ min: 0, step: 1000 }}
                value={fdDlg.data.principal_amount || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({
                    ...p,
                    data: { ...p.data, principal_amount: parseFloat(e.target.value) || 0 },
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
                value={fdDlg.data.interest_rate || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({
                    ...p,
                    data: { ...p.data, interest_rate: parseFloat(e.target.value) || 0 },
                  }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Interest Type</InputLabel>
                <Select
                  label="Interest Type"
                  value={fdDlg.data.interest_type || 'simple'}
                  onChange={(e) =>
                    setFdDlg((p) => ({
                      ...p,
                      data: {
                        ...p.data,
                        interest_type: e.target.value as 'simple' | 'compound',
                      },
                    }))
                  }
                >
                  <MenuItem value="simple">Simple</MenuItem>
                  <MenuItem value="compound">Compound</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            {fdDlg.data.interest_type === 'compound' && (
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Compounding Frequency</InputLabel>
                  <Select
                    label="Compounding Frequency"
                    value={fdDlg.data.compounding_frequency || 'annually'}
                    onChange={(e) =>
                      setFdDlg((p) => ({
                        ...p,
                        data: { ...p.data, compounding_frequency: e.target.value },
                      }))
                    }
                  >
                    <MenuItem value="monthly">Monthly</MenuItem>
                    <MenuItem value="quarterly">Quarterly</MenuItem>
                    <MenuItem value="half_yearly">Half-Yearly</MenuItem>
                    <MenuItem value="annually">Annually</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            )}
            <Grid item xs={12} sm={6}>
              <TextField
                label="Start Date"
                fullWidth
                required
                type="date"
                InputLabelProps={{ shrink: true }}
                value={fdDlg.data.start_date || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({ ...p, data: { ...p.data, start_date: e.target.value } }))
                }
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Maturity Date (optional)"
                fullWidth
                type="date"
                InputLabelProps={{ shrink: true }}
                value={fdDlg.data.maturity_date || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({
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
                    checked={fdDlg.data.auto_update || false}
                    onChange={(e) =>
                      setFdDlg((p) => ({
                        ...p,
                        data: { ...p.data, auto_update: e.target.checked },
                      }))
                    }
                    color="primary"
                  />
                }
                label="Update Automatically (auto-generate interest on page load)"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes (optional)"
                fullWidth
                multiline
                rows={2}
                value={fdDlg.data.notes || ''}
                onChange={(e) =>
                  setFdDlg((p) => ({ ...p, data: { ...p.data, notes: e.target.value } }))
                }
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeFdDlg}>Cancel</Button>
          <Button onClick={handleSaveFd} variant="contained" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add/Edit Transaction Dialog */}
      <Dialog open={txDlg.open} onClose={closeTxDlg} maxWidth="xs" fullWidth>
        <DialogTitle>
          {txDlg.mode === 'add' ? 'Add Interest Transaction' : 'Edit Transaction'}
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
            <Grid item xs={12}>
              <TextField
                label="Interest Amount (₹)"
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

      {/* Delete FD Confirmation */}
      <Dialog open={!!delFd} onClose={() => setDelFd(null)}>
        <DialogTitle>Delete Fixed Deposit?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will permanently delete the FD and all its interest transactions. This cannot be
            undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDelFd(null)}>Cancel</Button>
          <Button onClick={handleDeleteFd} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Transaction Confirmation */}
      <Dialog open={!!delTx} onClose={() => setDelTx(null)}>
        <DialogTitle>Delete Transaction?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this interest transaction?
          </DialogContentText>
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

export default FixedDeposit;

// Made with Bob
