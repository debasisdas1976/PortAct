import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Chip,
  Tabs,
  Tab,
  CircularProgress,
  MenuItem,
  FormControlLabel,
  Switch
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  AccountBalance as PFIcon,
  Upload as UploadIcon,
  Visibility as ViewIcon
} from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

// Helper function to get user-friendly transaction type label
const getTransactionTypeLabel = (type: string): string => {
  const typeMap: { [key: string]: string } = {
    'deposit': 'Employee Contribution',
    'transfer_in': 'Employer Contribution',
    'interest': 'Employee Interest',
    'dividend': 'Employer Interest',
    'withdrawal': 'Withdrawal',
    'transfer_out': 'Transfer Out',
    // Legacy types (for old data)
    'buy': 'Employee Contribution'
  };
  return typeMap[type] || type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

interface PFAccount {
  id: number;
  asset_id: number;
  nickname: string;
  uan_number: string;
  pf_number?: string;
  account_holder_name: string;
  employer_name: string;
  date_of_joining: string;
  date_of_exit?: string;
  current_balance: number;
  employee_contribution: number;
  employer_contribution: number;
  pension_contribution: number;
  total_interest_earned: number;
  interest_rate: number;
  is_active: boolean;
  notes?: string;
}

interface PFTransaction {
  id: number;
  transaction_date: string;
  transaction_type: string;
  amount: number;
  balance_after_transaction: number;
  contribution_type?: string;
  description?: string;
  financial_year?: string;
}

interface PFSummary {
  total_accounts: number;
  active_accounts: number;
  total_balance: number;
  employee_contribution: number;
  employer_contribution: number;
  pension_contribution: number;
  total_interest_earned: number;
  average_interest_rate: number;
}

const PF: React.FC = () => {
  const [accounts, setAccounts] = useState<PFAccount[]>([]);
  const [summary, setSummary] = useState<PFSummary | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [openTransactionDialog, setOpenTransactionDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<PFAccount | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<PFAccount | null>(null);
  const [transactions, setTransactions] = useState<PFTransaction[]>([]);
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState({
    nickname: '',
    uan_number: '',
    pf_number: '',
    account_holder_name: '',
    employer_name: '',
    date_of_joining: new Date().toISOString().split('T')[0],
    date_of_exit: '',
    interest_rate: 8.25,
    current_balance: 0,
    employee_contribution: 0,
    employer_contribution: 0,
    pension_contribution: 0,
    total_interest_earned: 0,
    is_active: true,
    notes: ''
  });
  const [transactionFormData, setTransactionFormData] = useState({
    transaction_date: new Date().toISOString().split('T')[0],
    transaction_type: 'employee_contribution',
    amount: 0,
    balance_after_transaction: 0,
    contribution_type: 'epf',
    description: '',
    financial_year: ''
  });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPassword, setUploadPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { notify } = useNotification();

  useEffect(() => {
    fetchAccounts();
    fetchSummary();
  }, []);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const response = await api.get('/pf/');
      setAccounts(response.data);
      // Auto-select first account to enable Transactions tab
      if (response.data.length > 0 && !selectedAccount) {
        setSelectedAccount(response.data[0]);
        fetchAccountTransactions(response.data[0].id);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch PF accounts'));
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await api.get('/pf/summary');
      setSummary(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch PF summary'));
    }
  };

  const fetchAccountTransactions = async (accountId: number) => {
    try {
      const response = await api.get(`/pf/${accountId}`);
      setTransactions(response.data.transactions || []);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch transactions'));
    }
  };

  const handleOpenDialog = (account?: PFAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        nickname: account.nickname,
        uan_number: account.uan_number,
        pf_number: account.pf_number || '',
        account_holder_name: account.account_holder_name,
        employer_name: account.employer_name,
        date_of_joining: account.date_of_joining,
        date_of_exit: account.date_of_exit || '',
        interest_rate: account.interest_rate,
        current_balance: account.current_balance,
        employee_contribution: account.employee_contribution,
        employer_contribution: account.employer_contribution,
        pension_contribution: account.pension_contribution,
        total_interest_earned: account.total_interest_earned,
        is_active: account.is_active,
        notes: account.notes || ''
      });
    } else {
      setEditingAccount(null);
      setFormData({
        nickname: '',
        uan_number: '',
        pf_number: '',
        account_holder_name: '',
        employer_name: '',
        date_of_joining: new Date().toISOString().split('T')[0],
        date_of_exit: '',
        interest_rate: 8.25,
        current_balance: 0,
        employee_contribution: 0,
        employer_contribution: 0,
        pension_contribution: 0,
        total_interest_earned: 0,
        is_active: true,
        notes: ''
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingAccount(null);
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);

      if (editingAccount) {
        await api.put(`/pf/${editingAccount.id}`, formData);
        notify.success('Account updated successfully');
      } else {
        await api.post('/pf/', formData);
        notify.success('Account added successfully');
      }

      handleCloseDialog();
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save PF account'));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this PF account?')) {
      return;
    }

    try {
      await api.delete(`/pf/${id}`);
      notify.success('Account deleted successfully');
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete PF account'));
    }
  };

  const handleViewTransactions = async (account: PFAccount) => {
    setSelectedAccount(account);
    await fetchAccountTransactions(account.id);
    setTabValue(1);
  };

  const handleOpenTransactionDialog = () => {
    if (!selectedAccount) {
      notify.error('Please select an account first');
      return;
    }
    setTransactionFormData({
      transaction_date: new Date().toISOString().split('T')[0],
      transaction_type: 'employee_contribution',
      amount: 0,
      balance_after_transaction: selectedAccount.current_balance,
      contribution_type: 'epf',
      description: '',
      financial_year: ''
    });
    setOpenTransactionDialog(true);
  };

  const handleCloseTransactionDialog = () => {
    setOpenTransactionDialog(false);
  };

  const handleSubmitTransaction = async () => {
    if (!selectedAccount) return;

    try {
      setLoading(true);
      await api.post(`/pf/${selectedAccount.id}/transactions`, transactionFormData);
      notify.success('Transaction added successfully');
      handleCloseTransactionDialog();
      fetchAccountTransactions(selectedAccount.id);
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to add transaction'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenUploadDialog = () => {
    setUploadFile(null);
    setUploadPassword('');
    setOpenUploadDialog(true);
  };

  const handleCloseUploadDialog = () => {
    setOpenUploadDialog(false);
    setUploadFile(null);
    setUploadPassword('');
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setUploadFile(event.target.files[0]);
    }
  };

  const handleUploadStatement = async () => {
    if (!uploadFile) {
      notify.error('Please select a file');
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (uploadPassword) {
        formData.append('password', uploadPassword);
      }

      await api.post('/pf/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      notify.success('Statement uploaded successfully');
      handleCloseUploadDialog();
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement'));
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <PFIcon sx={{ fontSize: 40, color: 'primary.main' }} />
          <Typography variant="h4">Provident Fund (PF/EPF)</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={handleOpenUploadDialog}
          >
            Upload Statement
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Account
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Accounts
                </Typography>
                <Typography variant="h4">{summary.total_accounts}</Typography>
                <Typography variant="body2" color="success.main">
                  {summary.active_accounts} Active
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Balance
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.total_balance)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Employee Contribution
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.employee_contribution)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Employer Contribution
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.employer_contribution)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Pension (EPS)
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.pension_contribution)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Interest
                </Typography>
                <Typography variant="h4" color="success.main">
                  {formatCurrency(summary.total_interest_earned)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Accounts" />
          <Tab label="Transactions" disabled={!selectedAccount} />
        </Tabs>
      </Paper>

      {/* Accounts Tab */}
      {tabValue === 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nickname</TableCell>
                <TableCell>UAN</TableCell>
                <TableCell>PF Number</TableCell>
                <TableCell>Employer</TableCell>
                <TableCell>Joining Date</TableCell>
                <TableCell align="right">Balance</TableCell>
                <TableCell align="right">Employee</TableCell>
                <TableCell align="right">Employer</TableCell>
                <TableCell align="right">Pension</TableCell>
                <TableCell align="right">Interest</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell><strong>{account.nickname}</strong></TableCell>
                  <TableCell>{account.uan_number}</TableCell>
                  <TableCell>{account.pf_number || '-'}</TableCell>
                  <TableCell>{account.employer_name}</TableCell>
                  <TableCell>{formatDate(account.date_of_joining)}</TableCell>
                  <TableCell align="right">{formatCurrency(account.current_balance)}</TableCell>
                  <TableCell align="right">{formatCurrency(account.employee_contribution)}</TableCell>
                  <TableCell align="right">{formatCurrency(account.employer_contribution)}</TableCell>
                  <TableCell align="right">{formatCurrency(account.pension_contribution)}</TableCell>
                  <TableCell align="right" sx={{ color: 'success.main' }}>
                    {formatCurrency(account.total_interest_earned)}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={account.is_active ? 'Active' : 'Inactive'}
                      color={account.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <IconButton
                      size="small"
                      onClick={() => handleViewTransactions(account)}
                      title="View Transactions"
                    >
                      <ViewIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(account)}
                      title="Edit"
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(account.id)}
                      title="Delete"
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {accounts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={12} align="center">
                    No PF accounts found. Add one to get started.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Transactions Tab */}
      {tabValue === 1 && selectedAccount && (
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Transactions for {selectedAccount.nickname} (UAN: {selectedAccount.uan_number})
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleOpenTransactionDialog}
            >
              Add Transaction
            </Button>
          </Box>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Contribution</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">Balance After</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Financial Year</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((transaction) => (
                  <TableRow key={transaction.id}>
                    <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                    <TableCell>
                      <Chip
                        label={getTransactionTypeLabel(transaction.transaction_type)}
                        color={
                          transaction.transaction_type === 'deposit' || transaction.transaction_type === 'transfer_in' || transaction.transaction_type === 'buy'
                            ? 'primary'
                            : transaction.transaction_type === 'interest' || transaction.transaction_type === 'dividend'
                            ? 'success'
                            : transaction.transaction_type === 'withdrawal'
                            ? 'error'
                            : 'warning'
                        }
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {transaction.contribution_type ? (
                        <Chip label={transaction.contribution_type.toUpperCase()} size="small" variant="outlined" />
                      ) : '-'}
                    </TableCell>
                    <TableCell align="right">{formatCurrency(transaction.amount)}</TableCell>
                    <TableCell align="right">
                      {formatCurrency(transaction.balance_after_transaction)}
                    </TableCell>
                    <TableCell>{transaction.description || '-'}</TableCell>
                    <TableCell>{transaction.financial_year || '-'}</TableCell>
                  </TableRow>
                ))}
                {transactions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      No transactions found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Add/Edit Account Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>{editingAccount ? 'Edit PF Account' : 'Add PF Account'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Nickname"
                value={formData.nickname}
                onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                required
                helperText="Friendly name to identify this account"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="UAN Number"
                value={formData.uan_number}
                onChange={(e) => setFormData({ ...formData, uan_number: e.target.value })}
                required
                inputProps={{ maxLength: 12 }}
                helperText="12-digit Universal Account Number"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="PF Account Number"
                value={formData.pf_number}
                onChange={(e) => setFormData({ ...formData, pf_number: e.target.value })}
                helperText="Optional PF member ID"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Account Holder Name"
                value={formData.account_holder_name}
                onChange={(e) => setFormData({ ...formData, account_holder_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Employer Name"
                value={formData.employer_name}
                onChange={(e) => setFormData({ ...formData, employer_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Date of Joining"
                value={formData.date_of_joining}
                onChange={(e) => setFormData({ ...formData, date_of_joining: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Date of Exit"
                value={formData.date_of_exit}
                onChange={(e) => setFormData({ ...formData, date_of_exit: e.target.value })}
                InputLabelProps={{ shrink: true }}
                helperText="Leave empty if still employed"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Interest Rate (%)"
                value={formData.interest_rate}
                onChange={(e) => setFormData({ ...formData, interest_rate: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0, max: 100 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Current Balance"
                value={formData.current_balance}
                onChange={(e) => setFormData({ ...formData, current_balance: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Employee Contribution"
                value={formData.employee_contribution}
                onChange={(e) => setFormData({ ...formData, employee_contribution: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Employer Contribution"
                value={formData.employer_contribution}
                onChange={(e) => setFormData({ ...formData, employer_contribution: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Pension (EPS)"
                value={formData.pension_contribution}
                onChange={(e) => setFormData({ ...formData, pension_contribution: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Total Interest Earned"
                value={formData.total_interest_earned}
                onChange={(e) => setFormData({ ...formData, total_interest_earned: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                }
                label="Account Active"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={loading}>
            {loading ? <CircularProgress size={24} /> : editingAccount ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Transaction Dialog */}
      <Dialog open={openTransactionDialog} onClose={handleCloseTransactionDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add Transaction</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="date"
                label="Transaction Date"
                value={transactionFormData.transaction_date}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, transaction_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Transaction Type"
                value={transactionFormData.transaction_type}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, transaction_type: e.target.value })}
                required
              >
                <MenuItem value="employee_contribution">Employee Contribution</MenuItem>
                <MenuItem value="employer_contribution">Employer Contribution</MenuItem>
                <MenuItem value="pension_contribution">Pension Contribution (EPS)</MenuItem>
                <MenuItem value="interest">Interest</MenuItem>
                <MenuItem value="withdrawal">Withdrawal</MenuItem>
                <MenuItem value="transfer">Transfer</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Contribution Type"
                value={transactionFormData.contribution_type}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, contribution_type: e.target.value })}
              >
                <MenuItem value="epf">EPF (Employee Provident Fund)</MenuItem>
                <MenuItem value="eps">EPS (Employee Pension Scheme)</MenuItem>
                <MenuItem value="edli">EDLI (Employee Deposit Linked Insurance)</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="Amount"
                value={transactionFormData.amount}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, amount: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="Balance After Transaction"
                value={transactionFormData.balance_after_transaction}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, balance_after_transaction: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={transactionFormData.description}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Financial Year"
                value={transactionFormData.financial_year}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, financial_year: e.target.value })}
                placeholder="e.g., 2023-24"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseTransactionDialog}>Cancel</Button>
          <Button onClick={handleSubmitTransaction} variant="contained" disabled={loading}>
            {loading ? <CircularProgress size={24} /> : 'Add Transaction'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upload Statement Dialog */}
      <Dialog open={openUploadDialog} onClose={handleCloseUploadDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Upload PF Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Button
              variant="outlined"
              component="label"
              fullWidth
              startIcon={<UploadIcon />}
              sx={{ mb: 2 }}
            >
              {uploadFile ? uploadFile.name : 'Select PDF File'}
              <input
                type="file"
                hidden
                accept=".pdf"
                onChange={handleFileSelect}
              />
            </Button>
            {uploadFile && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Selected: {uploadFile.name} ({(uploadFile.size / 1024).toFixed(2)} KB)
              </Typography>
            )}
            <TextField
              fullWidth
              type="password"
              label="PDF Password (if encrypted)"
              value={uploadPassword}
              onChange={(e) => setUploadPassword(e.target.value)}
              placeholder="Leave empty if not password-protected"
              helperText="Required for password-protected EPFO statements"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUploadDialog}>Cancel</Button>
          <Button
            onClick={handleUploadStatement}
            variant="contained"
            disabled={!uploadFile || loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Upload & Process'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PF;

// Made with Bob
