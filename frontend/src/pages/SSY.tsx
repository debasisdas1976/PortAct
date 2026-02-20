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
  ChildCare as SSYIcon,
  Upload as UploadIcon,
  Visibility as ViewIcon
} from '@mui/icons-material';
import axios from 'axios';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface SSYAccount {
  id: number;
  asset_id: number;
  nickname: string;
  account_number: string;
  bank_name: string;
  post_office_name?: string;
  girl_name: string;
  girl_dob: string;
  guardian_name: string;
  opening_date: string;
  maturity_date?: string;
  interest_rate: number;
  current_balance: number;
  total_deposits: number;
  total_interest_earned: number;
  financial_year?: string;
  notes?: string;
}

interface SSYTransaction {
  id: number;
  transaction_date: string;
  transaction_type: string;
  amount: number;
  balance_after_transaction: number;
  description?: string;
  financial_year?: string;
}

interface SSYSummary {
  total_accounts: number;
  total_balance: number;
  total_deposits: number;
  total_interest_earned: number;
  average_interest_rate: number;
}

const SSY: React.FC = () => {
  const [accounts, setAccounts] = useState<SSYAccount[]>([]);
  const [summary, setSummary] = useState<SSYSummary | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [openTransactionDialog, setOpenTransactionDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<SSYAccount | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<SSYAccount | null>(null);
  const [transactions, setTransactions] = useState<SSYTransaction[]>([]);
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState({
    nickname: '',
    account_number: '',
    bank_name: '',
    post_office_name: '',
    girl_name: '',
    girl_dob: new Date().toISOString().split('T')[0],
    guardian_name: '',
    opening_date: new Date().toISOString().split('T')[0],
    maturity_date: '',
    interest_rate: 8.2,
    current_balance: 0,
    total_deposits: 0,
    total_interest_earned: 0,
    financial_year: '',
    notes: ''
  });
  const [transactionFormData, setTransactionFormData] = useState({
    transaction_date: new Date().toISOString().split('T')[0],
    transaction_type: 'deposit',
    amount: 0,
    balance_after_transaction: 0,
    description: '',
    financial_year: ''
  });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPassword, setUploadPassword] = useState('');
  const [uploadAccountId, setUploadAccountId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const { notify } = useNotification();

  const bankOptions = [
    'State Bank of India',
    'HDFC Bank',
    'ICICI Bank',
    'Axis Bank',
    'Punjab National Bank',
    'Bank of Baroda',
    'Canara Bank',
    'Union Bank of India',
    'Indian Bank',
    'Post Office',
    'Other'
  ];

  useEffect(() => {
    fetchAccounts();
    fetchSummary();
  }, []);

  const fetchAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/ssy/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAccounts(response.data);
      // Auto-select first account to enable Transactions tab
      if (response.data.length > 0 && !selectedAccount) {
        setSelectedAccount(response.data[0]);
        fetchAccountTransactions(response.data[0].id);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch SSY accounts'));
    }
  };

  const fetchSummary = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/ssy/summary', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSummary(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch SSY summary'));
    }
  };

  const fetchAccountTransactions = async (accountId: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:8000/api/v1/ssy/${accountId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions(response.data.transactions || []);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch transactions'));
    }
  };

  const handleOpenDialog = (account?: SSYAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        nickname: account.nickname,
        account_number: account.account_number,
        bank_name: account.bank_name,
        post_office_name: account.post_office_name || '',
        girl_name: account.girl_name,
        girl_dob: account.girl_dob,
        guardian_name: account.guardian_name,
        opening_date: account.opening_date,
        maturity_date: account.maturity_date || '',
        interest_rate: account.interest_rate,
        current_balance: account.current_balance,
        total_deposits: account.total_deposits,
        total_interest_earned: account.total_interest_earned,
        financial_year: account.financial_year || '',
        notes: account.notes || ''
      });
    } else {
      setEditingAccount(null);
      setFormData({
        nickname: '',
        account_number: '',
        bank_name: '',
        post_office_name: '',
        girl_name: '',
        girl_dob: new Date().toISOString().split('T')[0],
        guardian_name: '',
        opening_date: new Date().toISOString().split('T')[0],
        maturity_date: '',
        interest_rate: 8.2,
        current_balance: 0,
        total_deposits: 0,
        total_interest_earned: 0,
        financial_year: '',
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
          `http://localhost:8000/api/v1/ssy/${editingAccount.id}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        notify.success('Account updated successfully');
      } else {
        await axios.post(
          'http://localhost:8000/api/v1/ssy/',
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        notify.success('Account added successfully');
      }

      handleCloseDialog();
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save SSY account'));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this SSY account?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`http://localhost:8000/api/v1/ssy/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      notify.success('Account deleted successfully');
      fetchAccounts();
      fetchSummary();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete SSY account'));
    }
  };

  const handleViewTransactions = async (account: SSYAccount) => {
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
      transaction_type: 'deposit',
      amount: 0,
      balance_after_transaction: selectedAccount.current_balance,
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
        `http://localhost:8000/api/v1/ssy/${selectedAccount.id}/transactions`,
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
      notify.error('Please create an SSY account first before uploading a statement');
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
      notify.error('Please select an SSY account');
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
        `http://localhost:8000/api/v1/ssy/${uploadAccountId}/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      notify.success('Statement uploaded successfully');
      handleCloseUploadDialog();
      await fetchAccounts();
      await fetchSummary();

      try {
        const accountResponse = await axios.get(
          `http://localhost:8000/api/v1/ssy/${uploadAccountId}`,
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );

        setSelectedAccount(accountResponse.data);
        setTransactions(accountResponse.data.transactions || []);
        setTabValue(1);
      } catch (err) {
        notify.error(getErrorMessage(err, 'Failed to fetch transactions after upload'));
      }
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
    return new Date(dateString).toLocaleDateString('en-IN');
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          <SSYIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Sukanya Samriddhi Yojana (SSY)
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
            Add SSY Account
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
                  Total Deposits
                </Typography>
                <Typography variant="h4">{formatCurrency(summary.total_deposits)}</Typography>
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
                <TableCell>Account Number</TableCell>
                <TableCell>Bank/Post Office</TableCell>
                <TableCell>Girl's Name</TableCell>
                <TableCell>Guardian</TableCell>
                <TableCell>Opening Date</TableCell>
                <TableCell>Interest Rate</TableCell>
                <TableCell align="right">Current Balance</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell><strong>{account.nickname}</strong></TableCell>
                  <TableCell>{account.account_number}</TableCell>
                  <TableCell>{account.bank_name}</TableCell>
                  <TableCell>{account.girl_name}</TableCell>
                  <TableCell>{account.guardian_name}</TableCell>
                  <TableCell>{formatDate(account.opening_date)}</TableCell>
                  <TableCell>{account.interest_rate}%</TableCell>
                  <TableCell align="right">{formatCurrency(account.current_balance)}</TableCell>
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
                    No SSY accounts found. Add one to get started.
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
              Transactions for {selectedAccount.nickname} ({selectedAccount.account_number})
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
                        label={transaction.transaction_type}
                        color={
                          transaction.transaction_type === 'deposit'
                            ? 'primary'
                            : transaction.transaction_type === 'interest'
                            ? 'success'
                            : transaction.transaction_type === 'maturity'
                            ? 'info'
                            : 'warning'
                        }
                        size="small"
                      />
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
                    <TableCell colSpan={6} align="center">
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
          {editingAccount ? 'Edit SSY Account' : 'Add SSY Account'}
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
                helperText="A friendly name to identify this SSY account"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Account Number"
                value={formData.account_number}
                onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Bank/Post Office"
                value={formData.bank_name}
                onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                required
              >
                {bankOptions.map((bank) => (
                  <MenuItem key={bank} value={bank}>
                    {bank}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Post Office Name (Optional)"
                value={formData.post_office_name}
                onChange={(e) => setFormData({ ...formData, post_office_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Girl's Name"
                value={formData.girl_name}
                onChange={(e) => setFormData({ ...formData, girl_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Girl's Date of Birth"
                value={formData.girl_dob}
                onChange={(e) => setFormData({ ...formData, girl_dob: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Guardian Name"
                value={formData.guardian_name}
                onChange={(e) => setFormData({ ...formData, guardian_name: e.target.value })}
                required
              />
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
                label="Maturity Date (Optional)"
                value={formData.maturity_date}
                onChange={(e) => setFormData({ ...formData, maturity_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
                helperText="Auto-calculated as 21 years from opening"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Interest Rate (%)"
                value={formData.interest_rate}
                onChange={(e) => setFormData({ ...formData, interest_rate: parseFloat(e.target.value) })}
                inputProps={{ step: 0.1, min: 0, max: 100 }}
                required
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
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Total Deposits"
                value={formData.total_deposits}
                onChange={(e) => setFormData({ ...formData, total_deposits: parseFloat(e.target.value) })}
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
              <TextField
                fullWidth
                label="Financial Year"
                value={formData.financial_year}
                onChange={(e) => setFormData({ ...formData, financial_year: e.target.value })}
                placeholder="e.g., 2025-26"
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
                <MenuItem value="deposit">Deposit</MenuItem>
                <MenuItem value="interest">Interest</MenuItem>
                <MenuItem value="withdrawal">Withdrawal</MenuItem>
                <MenuItem value="maturity">Maturity</MenuItem>
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
        <DialogTitle>Upload SSY Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Select the SSY account for this statement
            </Typography>
            <TextField
              fullWidth
              select
              label="SSY Account"
              value={uploadAccountId || ''}
              onChange={(e) => setUploadAccountId(Number(e.target.value))}
              sx={{ mt: 2, mb: 2 }}
              required
            >
              {accounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.account_number} - {account.girl_name}
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

export default SSY;

// Made with Bob