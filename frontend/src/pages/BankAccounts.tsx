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
  MenuItem,
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
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  AccountBalance as BankIcon,
  CreditCard as CardIcon
} from '@mui/icons-material';
import axios from 'axios';

interface BankAccount {
  id: number;
  bank_name: string;
  account_type: string;
  account_number: string;
  nickname?: string;
  current_balance: number;
  credit_limit?: number;
  is_active: boolean;
}

const BankAccounts: React.FC = () => {
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<BankAccount | null>(null);
  const [formData, setFormData] = useState({
    bank_name: 'icici_bank',
    account_type: 'savings',
    account_number: '',
    nickname: '',
    current_balance: 0,
    available_balance: 0,
    credit_limit: 0,
    is_active: true
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const bankNames = [
    { value: 'icici_bank', label: 'ICICI Bank' },
    { value: 'hdfc_bank', label: 'HDFC Bank' },
    { value: 'idfc_first_bank', label: 'IDFC First Bank' },
    { value: 'state_bank_of_india', label: 'State Bank of India' },
    { value: 'axis_bank', label: 'Axis Bank' },
    { value: 'kotak_mahindra_bank', label: 'Kotak Mahindra Bank' },
    { value: 'yes_bank', label: 'Yes Bank' },
    { value: 'other', label: 'Other' }
  ];
  const accountTypes = [
    { value: 'savings', label: 'Savings' },
    { value: 'current', label: 'Current' },
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'fixed_deposit', label: 'Fixed Deposit' },
    { value: 'recurring_deposit', label: 'Recurring Deposit' }
  ];

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/bank-accounts/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAccounts(response.data);
    } catch (err) {
      setError('Failed to fetch bank accounts');
    }
  };

  const handleOpenDialog = (account?: BankAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        bank_name: account.bank_name,
        account_type: account.account_type,
        account_number: account.account_number,
        nickname: account.nickname || '',
        current_balance: account.current_balance,
        available_balance: account.current_balance, // Default to current balance
        credit_limit: account.credit_limit || 0,
        is_active: account.is_active
      });
    } else {
      setEditingAccount(null);
      setFormData({
        bank_name: 'icici_bank',
        account_type: 'savings',
        account_number: '',
        nickname: '',
        current_balance: 0,
        available_balance: 0,
        credit_limit: 0,
        is_active: true
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingAccount(null);
    setError('');
  };

  const handleSubmit = async () => {
    try {
      const token = localStorage.getItem('token');
      console.log('Submitting bank account:', formData);
      
      if (editingAccount) {
        const response = await axios.put(
          `http://localhost:8000/api/v1/bank-accounts/${editingAccount.id}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        console.log('Update response:', response.data);
        setSuccess('Bank account updated successfully');
      } else {
        const response = await axios.post(
          'http://localhost:8000/api/v1/bank-accounts/',
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        console.log('Create response:', response.data);
        setSuccess('Bank account created successfully');
      }
      handleCloseDialog();
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      console.error('Error submitting bank account:', err);
      console.error('Error response:', err.response);
      console.error('Error detail:', err.response?.data?.detail);
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else if (Array.isArray(errorDetail)) {
        const errorMessages = errorDetail.map((e: any) => {
          if (typeof e === 'string') return e;
          return `${e.loc?.join('.')}: ${e.msg}`;
        }).join(', ');
        setError(errorMessages);
      } else if (errorDetail) {
        setError(JSON.stringify(errorDetail));
      } else {
        setError(`Failed to save bank account: ${err.message}`);
      }
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this bank account?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`http://localhost:8000/api/v1/bank-accounts/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Bank account deleted successfully');
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else if (Array.isArray(errorDetail)) {
        setError(errorDetail.map((e: any) => e.msg).join(', '));
      } else {
        setError('Failed to delete bank account');
      }
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const getAccountTypeIcon = (type: string) => {
    return type === 'CREDIT_CARD' ? <CardIcon /> : <BankIcon />;
  };

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.current_balance, 0);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Bank Accounts</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Add Account
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Accounts
              </Typography>
              <Typography variant="h4">{accounts.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Balance
              </Typography>
              <Typography variant="h4">{formatCurrency(totalBalance)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Accounts
              </Typography>
              <Typography variant="h4">
                {accounts.filter(a => a.is_active).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Bank</TableCell>
              <TableCell>Account Type</TableCell>
              <TableCell>Account Number</TableCell>
              <TableCell>Nickname</TableCell>
              <TableCell align="right">Balance</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {accounts.map((account) => (
              <TableRow key={account.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getAccountTypeIcon(account.account_type)}
                    {account.bank_name.replace('_', ' ')}
                  </Box>
                </TableCell>
                <TableCell>{account.account_type.replace('_', ' ')}</TableCell>
                <TableCell>****{account.account_number.slice(-4)}</TableCell>
                <TableCell>{account.nickname || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(account.current_balance)}</TableCell>
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
                    onClick={() => handleOpenDialog(account)}
                    color="primary"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(account.id)}
                    color="error"
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingAccount ? 'Edit Bank Account' : 'Add Bank Account'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Bank Name"
              value={formData.bank_name}
              onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
              fullWidth
            >
              {bankNames.map((bank) => (
                <MenuItem key={bank.value} value={bank.value}>
                  {bank.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Account Type"
              value={formData.account_type}
              onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              fullWidth
            >
              {accountTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Account Number"
              value={formData.account_number}
              onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
              fullWidth
              required
            />

            <TextField
              label="Nickname (Optional)"
              value={formData.nickname}
              onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
              fullWidth
            />

            <TextField
              label="Current Balance"
              type="number"
              value={formData.current_balance}
              onChange={(e) => {
                const balance = parseFloat(e.target.value) || 0;
                setFormData({
                  ...formData,
                  current_balance: balance,
                  available_balance: balance // Auto-set available balance
                });
              }}
              fullWidth
            />

            {formData.account_type === 'credit_card' && (
              <TextField
                label="Credit Limit"
                type="number"
                value={formData.credit_limit}
                onChange={(e) => setFormData({ ...formData, credit_limit: parseFloat(e.target.value) })}
                fullWidth
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingAccount ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BankAccounts;

// Made with Bob
