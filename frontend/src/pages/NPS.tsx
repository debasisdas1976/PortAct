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
  MenuItem
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  AccountBalance as NPSIcon,
  Upload as UploadIcon,
  Visibility as ViewIcon
} from '@mui/icons-material';
import axios from 'axios';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface NPSAccount {
  id: number;
  asset_id: number;
  nickname: string;
  pran_number: string;
  account_holder_name: string;
  sector_type: string;
  tier_type: string;
  opening_date: string;
  date_of_birth: string;
  retirement_age: number;
  current_balance: number;
  total_contributions: number;
  employer_contributions: number;
  total_returns: number;
  scheme_preference?: string;
  fund_manager?: string;
  notes?: string;
}

interface NPSTransaction {
  id: number;
  transaction_date: string;
  transaction_type: string;
  amount: number;
  nav?: number;
  units?: number;
  scheme?: string;
  description?: string;
  financial_year?: string;
}

interface NPSSummary {
  total_accounts: number;
  total_balance: number;
  total_contributions: number;
  employer_contributions: number;
  total_returns: number;
  tier_1_balance: number;
  tier_2_balance: number;
}

const NPS: React.FC = () => {
  const [accounts, setAccounts] = useState<NPSAccount[]>([]);
  const [summary, setSummary] = useState<NPSSummary | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [openTransactionDialog, setOpenTransactionDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<NPSAccount | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<NPSAccount | null>(null);
  const [transactions, setTransactions] = useState<NPSTransaction[]>([]);
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState({
    nickname: '',
    pran_number: '',
    account_holder_name: '',
    sector_type: 'all_citizen',
    tier_type: 'tier_1',
    opening_date: new Date().toISOString().split('T')[0],
    date_of_birth: new Date().toISOString().split('T')[0],
    retirement_age: 60,
    current_balance: 0,
    total_contributions: 0,
    employer_contributions: 0,
    total_returns: 0,
    scheme_preference: '',
    fund_manager: '',
    notes: ''
  });
  const [transactionFormData, setTransactionFormData] = useState({
    transaction_date: new Date().toISOString().split('T')[0],
    transaction_type: 'contribution',
    amount: 0,
    nav: 0,
    units: 0,
    scheme: '',
    description: '',
    financial_year: ''
  });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPassword, setUploadPassword] = useState('');
  const [uploadAccountId, setUploadAccountId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const { notify } = useNotification();

  const fundManagers = [
    'SBI Pension Funds',
    'LIC Pension Fund',
    'UTI Retirement Solutions',
    'ICICI Prudential Pension Fund',
    'HDFC Pension Management',
    'Kotak Mahindra Pension Fund',
    'Aditya Birla Sun Life Pension',
    'Other'
  ];

  useEffect(() => {
    fetchAccounts();
    fetchSummary();
  }, []);

  const fetchAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/nps/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAccounts(response.data);
      // Auto-select first account to enable Transactions tab
      if (response.data.length > 0 && !selectedAccount) {
        setSelectedAccount(response.data[0]);
        fetchAccountTransactions(response.data[0].id);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch NPS accounts'));
    }
  };

  const fetchSummary = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/nps/summary', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSummary(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch NPS summary'));
    }
  };

  const fetchAccountTransactions = async (accountId: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:8000/api/v1/nps/${accountId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions(response.data.transactions || []);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch transactions'));
    }
  };

  const handleOpenDialog = (account?: NPSAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        nickname: account.nickname,
        pran_number: account.pran_number,
        account_holder_name: account.account_holder_name,
        sector_type: account.sector_type,
        tier_type: account.tier_type,
        opening_date: account.opening_date,
        date_of_birth: account.date_of_birth,
        retirement_age: account.retirement_age,
        current_balance: account.current_balance,
        total_contributions: account.total_contributions,
        employer_contributions: account.employer_contributions,
        total_returns: account.total_returns,
        scheme_preference: account.scheme_preference || '',
        fund_manager: account.fund_manager || '',
        notes: account.notes || ''
      });
    } else {
      setEditingAccount(null);
      setFormData({
        nickname: '',
        pran_number: '',
        account_holder_name: '',
        sector_type: 'all_citizen',
        tier_type: 'tier_1',
        opening_date: new Date().toISOString().split('T')[0],
        date_of_birth: new Date().toISOString().split('T')[0],
        retirement_age: 60,
        current_balance: 0,
        total_contributions: 0,
        employer_contributions: 0,
        total_returns: 0,
        scheme_preference: '',
        fund_manager: '',
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
      const token = localStorage.getItem('token');
      
      if (editingAccount) {
        await axios.put(
          `http://localhost:8000/api/v1/nps/${editingAccount.id}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        notify.success('Account updated successfully');
      } else {
        await axios.post(
          'http://localhost:8000/api/v1/nps/',
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        notify.success('Account added successfully');
      }

      handleCloseDialog();
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save NPS account'));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this NPS account?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`http://localhost:8000/api/v1/nps/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      notify.success('Account deleted successfully');
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete NPS account'));
    }
  };

  const handleViewTransactions = async (account: NPSAccount) => {
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
      transaction_type: 'contribution',
      amount: 0,
      nav: 0,
      units: 0,
      scheme: '',
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
      const token = localStorage.getItem('token');
      await axios.post(
        `http://localhost:8000/api/v1/nps/${selectedAccount.id}/transactions`,
        transactionFormData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
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
    if (accounts.length === 0) {
      notify.error('Please create an NPS account first before uploading a statement');
      return;
    }
    setUploadFile(null);
    setUploadPassword('');
    setUploadAccountId(null);
    setOpenUploadDialog(true);
  };

  const handleCloseUploadDialog = () => {
    setOpenUploadDialog(false);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setUploadFile(event.target.files[0]);
    }
  };

  const handleUploadStatement = async () => {
    if (!uploadFile) {
      notify.error('Please select a file to upload');
      return;
    }

    if (!uploadAccountId) {
      notify.error('Please select an NPS account');
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (uploadPassword) {
        formData.append('password', uploadPassword);
      }

      await axios.post(
        `http://localhost:8000/api/v1/nps/${uploadAccountId}/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      notify.success('NPS statement uploaded and processed successfully');
      handleCloseUploadDialog();
      await fetchAccounts();
      await fetchSummary();
      
      try {
        const accountResponse = await axios.get(
          `http://localhost:8000/api/v1/nps/${uploadAccountId}`,
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );
        
        setSelectedAccount(accountResponse.data);
        setTransactions(accountResponse.data.transactions || []);
        setTabValue(1);
      } catch (err) {
        console.error('Failed to fetch transactions after upload');
      }
    } catch (err: any) {
      notify.error(err.response?.data?.detail || 'Failed to upload statement');
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
    return new Date(dateString).toLocaleDateString('en-IN');
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          <NPSIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          National Pension System (NPS)
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={handleOpenUploadDialog}
            sx={{ mr: 1 }}
          >
            Upload Statement
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add NPS Account
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Accounts
                </Typography>
                <Typography variant="h4">{summary.total_accounts}</Typography>
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
                  Tier 1 Balance
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.tier_1_balance)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Tier 2 Balance
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.tier_2_balance)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Contributions
                </Typography>
                <Typography variant="h5">{formatCurrency(summary.total_contributions)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Employer Contributions
                </Typography>
                <Typography variant="h5">{formatCurrency(summary.employer_contributions)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Returns
                </Typography>
                <Typography variant="h5" color="success.main">
                  {formatCurrency(summary.total_returns)}
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
                <TableCell>PRAN Number</TableCell>
                <TableCell>Account Holder</TableCell>
                <TableCell>Tier</TableCell>
                <TableCell>Sector</TableCell>
                <TableCell align="right">Current Balance</TableCell>
                <TableCell align="right">Total Contributions</TableCell>
                <TableCell align="right">Returns</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell><strong>{account.nickname}</strong></TableCell>
                  <TableCell>{account.pran_number}</TableCell>
                  <TableCell>{account.account_holder_name}</TableCell>
                  <TableCell>
                    <Chip 
                      label={account.tier_type === 'tier_1' ? 'Tier 1' : 'Tier 2'} 
                      color={account.tier_type === 'tier_1' ? 'primary' : 'secondary'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{account.sector_type.replace('_', ' ').toUpperCase()}</TableCell>
                  <TableCell align="right">{formatCurrency(account.current_balance)}</TableCell>
                  <TableCell align="right">{formatCurrency(account.total_contributions)}</TableCell>
                  <TableCell align="right" sx={{ color: 'success.main' }}>
                    {formatCurrency(account.total_returns)}
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
                  <TableCell colSpan={9} align="center">
                    No NPS accounts found. Add one to get started.
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
              Transactions for {selectedAccount.nickname} ({selectedAccount.pran_number})
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
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">NAV</TableCell>
                  <TableCell align="right">Units</TableCell>
                  <TableCell>Scheme</TableCell>
                  <TableCell>Description</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((transaction) => (
                  <TableRow key={transaction.id}>
                    <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                    <TableCell>
                      <Chip
                        label={transaction.transaction_type}
                        color={
                          transaction.transaction_type === 'contribution' || transaction.transaction_type === 'employer_contribution'
                            ? 'primary'
                            : transaction.transaction_type === 'returns'
                            ? 'success'
                            : transaction.transaction_type === 'switch'
                            ? 'info'
                            : 'warning'
                        }
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">{formatCurrency(transaction.amount)}</TableCell>
                    <TableCell align="right">{transaction.nav ? `₹${transaction.nav.toFixed(4)}` : '-'}</TableCell>
                    <TableCell align="right">{transaction.units ? transaction.units.toFixed(4) : '-'}</TableCell>
                    <TableCell>{transaction.scheme || '-'}</TableCell>
                    <TableCell>{transaction.description || '-'}</TableCell>
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
        <DialogTitle>
          {editingAccount ? 'Edit NPS Account' : 'Add NPS Account'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Nickname"
                value={formData.nickname}
                onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                required
                helperText="A friendly name to identify this NPS account"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="PRAN Number"
                value={formData.pran_number}
                onChange={(e) => setFormData({ ...formData, pran_number: e.target.value })}
                required
                inputProps={{ maxLength: 12 }}
                helperText="12-digit Permanent Retirement Account Number"
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
                select
                label="Sector Type"
                value={formData.sector_type}
                onChange={(e) => setFormData({ ...formData, sector_type: e.target.value })}
                required
              >
                <MenuItem value="government">Government</MenuItem>
                <MenuItem value="corporate">Corporate</MenuItem>
                <MenuItem value="all_citizen">All Citizen</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Tier Type"
                value={formData.tier_type}
                onChange={(e) => setFormData({ ...formData, tier_type: e.target.value })}
                required
              >
                <MenuItem value="tier_1">Tier 1 (Retirement)</MenuItem>
                <MenuItem value="tier_2">Tier 2 (Voluntary)</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Opening Date"
                value={formData.opening_date}
                onChange={(e) => setFormData({ ...formData, opening_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Date of Birth"
                value={formData.date_of_birth}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Retirement Age"
                value={formData.retirement_age}
                onChange={(e) => setFormData({ ...formData, retirement_age: parseInt(e.target.value) })}
                inputProps={{ min: 18, max: 75 }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Fund Manager"
                value={formData.fund_manager}
                onChange={(e) => setFormData({ ...formData, fund_manager: e.target.value })}
              >
                {fundManagers.map((manager) => (
                  <MenuItem key={manager} value={manager}>
                    {manager}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Current Balance"
                value={formData.current_balance}
                onChange={(e) => setFormData({ ...formData, current_balance: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Total Contributions"
                value={formData.total_contributions}
                onChange={(e) => setFormData({ ...formData, total_contributions: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Employer Contributions"
                value={formData.employer_contributions}
                onChange={(e) => setFormData({ ...formData, employer_contributions: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Total Returns"
                value={formData.total_returns}
                onChange={(e) => setFormData({ ...formData, total_returns: parseFloat(e.target.value) })}
                inputProps={{ step: 0.01, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Scheme Preference"
                value={formData.scheme_preference}
                onChange={(e) => setFormData({ ...formData, scheme_preference: e.target.value })}
                placeholder="e.g., Active, Auto, Conservative"
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
                fullWidth
                select
                label="Transaction Type"
                value={transactionFormData.transaction_type}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, transaction_type: e.target.value })}
                required
              >
                <MenuItem value="contribution">Contribution</MenuItem>
                <MenuItem value="employer_contribution">Employer Contribution</MenuItem>
                <MenuItem value="returns">Returns</MenuItem>
                <MenuItem value="withdrawal">Withdrawal</MenuItem>
                <MenuItem value="switch">Switch</MenuItem>
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
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="NAV (Optional)"
                value={transactionFormData.nav}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, nav: parseFloat(e.target.value) })}
                inputProps={{ step: 0.0001, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Units (Optional)"
                value={transactionFormData.units}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, units: parseFloat(e.target.value) })}
                inputProps={{ step: 0.0001, min: 0 }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Scheme (Optional)"
                value={transactionFormData.scheme}
                onChange={(e) => setTransactionFormData({ ...transactionFormData, scheme: e.target.value })}
                placeholder="e.g., E, C, G, A"
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
                placeholder="e.g., 2025-26"
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
        <DialogTitle>Upload NPS Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Select the NPS account for this statement
            </Typography>
            <TextField
              fullWidth
              select
              label="NPS Account"
              value={uploadAccountId || ''}
              onChange={(e) => setUploadAccountId(Number(e.target.value))}
              sx={{ mt: 2, mb: 2 }}
              required
            >
              {accounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.pran_number} - {account.account_holder_name}
                </MenuItem>
              ))}
            </TextField>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Supported formats: PDF
            </Typography>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              style={{ marginTop: '16px', marginBottom: '16px' }}
            />
            {uploadFile && (
              <Typography variant="body2" color="primary">
                Selected: {uploadFile.name}
              </Typography>
            )}
            <TextField
              fullWidth
              type="password"
              label="Password (if PDF is encrypted)"
              value={uploadPassword}
              onChange={(e) => setUploadPassword(e.target.value)}
              sx={{ mt: 2 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUploadDialog}>Cancel</Button>
          <Button onClick={handleUploadStatement} variant="contained" disabled={loading || !uploadFile || !uploadAccountId}>
            {loading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default NPS;

// Made with Bob