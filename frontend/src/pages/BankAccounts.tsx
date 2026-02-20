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
  Alert,
  InputAdornment,
  CircularProgress,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  AccountBalance as BankIcon,
  CreditCard as CardIcon,
  CloudUpload as UploadIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import axios from 'axios';
import api from '../services/api';

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

  // Add/Edit dialog
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
    is_active: true,
  });

  // Upload dialog
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [uploadAccountId, setUploadAccountId] = useState<number | ''>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadPassword, setUploadPassword] = useState('');
  const [showUploadPassword, setShowUploadPassword] = useState(false);
  const [autoCategorize, setAutoCategorize] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ imported: number; duplicates: number; categorized: number } | null>(null);

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
    { value: 'other', label: 'Other' },
  ];

  const accountTypes = [
    { value: 'savings', label: 'Savings' },
    { value: 'current', label: 'Current' },
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'fixed_deposit', label: 'Fixed Deposit' },
    { value: 'recurring_deposit', label: 'Recurring Deposit' },
  ];

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/bank-accounts/', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAccounts(response.data);
    } catch (err) {
      setError('Failed to fetch bank accounts');
    }
  };

  // ── Add / Edit dialog ──────────────────────────────────────────────────────
  const handleOpenDialog = (account?: BankAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        bank_name: account.bank_name,
        account_type: account.account_type,
        account_number: account.account_number,
        nickname: account.nickname || '',
        current_balance: account.current_balance,
        available_balance: account.current_balance,
        credit_limit: account.credit_limit || 0,
        is_active: account.is_active,
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
        is_active: true,
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
      if (editingAccount) {
        await axios.put(
          `http://localhost:8000/api/v1/bank-accounts/${editingAccount.id}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSuccess('Bank account updated successfully');
      } else {
        await axios.post('http://localhost:8000/api/v1/bank-accounts/', formData, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setSuccess('Bank account created successfully');
      }
      handleCloseDialog();
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else if (Array.isArray(errorDetail)) {
        setError(errorDetail.map((e: any) => `${e.loc?.join('.')}: ${e.msg}`).join(', '));
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
        headers: { Authorization: `Bearer ${token}` },
      });
      setSuccess('Bank account deleted successfully');
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      setError(typeof errorDetail === 'string' ? errorDetail : 'Failed to delete bank account');
    }
  };

  // ── Upload dialog ──────────────────────────────────────────────────────────
  const handleOpenUpload = (account?: BankAccount) => {
    setUploadAccountId(account ? account.id : '');
    setSelectedFile(null);
    setUploadPassword('');
    setAutoCategorize(true);
    setUploadResult(null);
    setError('');
    setOpenUploadDialog(true);
  };

  const handleCloseUpload = () => {
    setOpenUploadDialog(false);
    setUploadResult(null);
    setError('');
  };

  const handleUploadStatement = async () => {
    if (!selectedFile || !uploadAccountId) {
      setError('Please select an account and a statement file');
      return;
    }

    try {
      setUploading(true);
      setError('');

      const formPayload = new FormData();
      formPayload.append('file', selectedFile);
      formPayload.append('bank_account_id', String(uploadAccountId));
      formPayload.append('auto_categorize', String(autoCategorize));
      if (uploadPassword) {
        formPayload.append('password', uploadPassword);
      }

      const response = await api.post('/bank-statements/upload', formPayload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const summary = response.data?.summary;
      setUploadResult({
        imported: summary?.imported ?? 0,
        duplicates: summary?.duplicates ?? 0,
        categorized: summary?.categorized ?? 0,
      });

      // Refresh balances
      fetchAccounts();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to upload statement. Please check the file and password.');
    } finally {
      setUploading(false);
    }
  };

  // ── Helpers ────────────────────────────────────────────────────────────────
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);

  const getAccountTypeIcon = (type: string) =>
    type === 'credit_card' ? <CardIcon /> : <BankIcon />;

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.current_balance, 0);

  const selectedAccountForUpload = accounts.find((a) => a.id === uploadAccountId);
  const needsPassword =
    selectedAccountForUpload?.bank_name === 'state_bank_of_india' ||
    selectedAccountForUpload?.bank_name === 'other';

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Bank Accounts</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<UploadIcon />} onClick={() => handleOpenUpload()}>
            Upload Statement
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
            Add Account
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Total Accounts</Typography>
              <Typography variant="h4">{accounts.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Total Balance</Typography>
              <Typography variant="h4">{formatCurrency(totalBalance)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Active Accounts</Typography>
              <Typography variant="h4">{accounts.filter((a) => a.is_active).length}</Typography>
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
                    {account.bank_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </Box>
                </TableCell>
                <TableCell>{account.account_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</TableCell>
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
                    color="primary"
                    title="Upload statement"
                    onClick={() => handleOpenUpload(account)}
                  >
                    <UploadIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleOpenDialog(account)} color="info">
                    <EditIcon />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(account.id)} color="error">
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ── Add / Edit dialog ──────────────────────────────────────────────── */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingAccount ? 'Edit Bank Account' : 'Add Bank Account'}</DialogTitle>
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
                <MenuItem key={bank.value} value={bank.value}>{bank.label}</MenuItem>
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
                <MenuItem key={type.value} value={type.value}>{type.label}</MenuItem>
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
                setFormData({ ...formData, current_balance: balance, available_balance: balance });
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

            {error && <Alert severity="error">{error}</Alert>}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingAccount ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Upload Statement dialog ────────────────────────────────────────── */}
      <Dialog open={openUploadDialog} onClose={handleCloseUpload} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Bank Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>

            {/* Account selector */}
            <TextField
              select
              label="Bank Account"
              value={uploadAccountId}
              onChange={(e) => setUploadAccountId(Number(e.target.value))}
              fullWidth
              required
            >
              {accounts.map((acc) => (
                <MenuItem key={acc.id} value={acc.id}>
                  {acc.bank_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  {acc.nickname ? ` · ${acc.nickname}` : ''} (****{acc.account_number.slice(-4)})
                </MenuItem>
              ))}
            </TextField>

            {/* File picker */}
            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
              fullWidth
            >
              {selectedFile ? selectedFile.name : 'Select Statement File (.pdf / .xlsx / .xls)'}
              <input
                type="file"
                hidden
                accept=".pdf,.xlsx,.xls"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />
            </Button>

            {/* Password field */}
            <TextField
              label={needsPassword ? 'Statement Password (required for SBI)' : 'Statement Password (if encrypted)'}
              type={showUploadPassword ? 'text' : 'password'}
              value={uploadPassword}
              onChange={(e) => setUploadPassword(e.target.value)}
              fullWidth
              helperText="SBI statements are password-protected (usually DOB in DDMMYYYY format)"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowUploadPassword(!showUploadPassword)} edge="end">
                      {showUploadPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            {/* Auto-categorize toggle */}
            <FormControlLabel
              control={
                <Checkbox
                  checked={autoCategorize}
                  onChange={(e) => setAutoCategorize(e.target.checked)}
                />
              }
              label="Auto-categorize transactions"
            />

            {/* Result summary */}
            {uploadResult && (
              <Alert severity="success">
                <strong>Upload successful!</strong> Imported {uploadResult.imported} transactions
                ({uploadResult.categorized} auto-categorized, {uploadResult.duplicates} duplicates skipped).
              </Alert>
            )}

            {error && <Alert severity="error">{error}</Alert>}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUpload}>
            {uploadResult ? 'Close' : 'Cancel'}
          </Button>
          {!uploadResult && (
            <Button
              onClick={handleUploadStatement}
              variant="contained"
              disabled={uploading || !selectedFile || !uploadAccountId}
              startIcon={uploading ? <CircularProgress size={18} /> : <UploadIcon />}
            >
              {uploading ? 'Uploading…' : 'Upload'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BankAccounts;

// Made with Bob
