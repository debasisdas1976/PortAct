import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  IconButton,
  InputAdornment,
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
} from '@mui/material';
import {
  AccountBalance,
  CloudUpload as UploadIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface BankAccount {
  id: number;
  bank_name: string;
  account_type: string;
  account_number: string;
  nickname?: string;
  current_balance: number;
  is_active: boolean;
}

const bankNameMap: Record<string, string> = {
  icici_bank: 'ICICI Bank',
  hdfc_bank: 'HDFC Bank',
  idfc_first_bank: 'IDFC First Bank',
  state_bank_of_india: 'State Bank of India',
  axis_bank: 'Axis Bank',
  kotak_mahindra_bank: 'Kotak Mahindra Bank',
  yes_bank: 'Yes Bank',
  other: 'Other',
};

const formatBankName = (name: string) =>
  bankNameMap[name] || name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const Savings: React.FC = () => {
  const { notify } = useNotification();
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(true);

  // Upload dialog state
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [uploadAccountId, setUploadAccountId] = useState<number | ''>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadPassword, setUploadPassword] = useState('');
  const [showUploadPassword, setShowUploadPassword] = useState(false);
  const [autoCategorize, setAutoCategorize] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ imported: number; duplicates: number; categorized: number } | null>(null);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const response = await api.get('/bank-accounts/');
      const filtered = (response.data as BankAccount[]).filter(
        (a) => a.account_type === 'savings' && a.is_active
      );
      setAccounts(filtered);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch savings accounts'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const totalBalance = accounts.reduce((s, a) => s + (a.current_balance || 0), 0);

  // ── Upload handlers ────────────────────────────────────────────────────────
  const handleOpenUpload = (account?: BankAccount) => {
    setUploadAccountId(account ? account.id : '');
    setSelectedFile(null);
    setUploadPassword('');
    setAutoCategorize(true);
    setUploadResult(null);
    setOpenUploadDialog(true);
  };

  const handleCloseUpload = () => {
    setOpenUploadDialog(false);
    setUploadResult(null);
  };

  const handleUploadStatement = async () => {
    if (!selectedFile || !uploadAccountId) {
      notify.error('Please select an account and a statement file');
      return;
    }

    try {
      setUploading(true);

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
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement. Please check the file and password.'));
    } finally {
      setUploading(false);
    }
  };

  const selectedAccountForUpload = accounts.find((a) => a.id === uploadAccountId);
  const isSBI = selectedAccountForUpload?.bank_name === 'state_bank_of_india';

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AccountBalance color="primary" />
          <Typography variant="h4">Savings Accounts</Typography>
        </Box>
        <Button variant="outlined" startIcon={<UploadIcon />} onClick={() => handleOpenUpload()}>
          Upload Statement
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Accounts</Typography>
              <Typography variant="h4">{accounts.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Balance</Typography>
              <Typography variant="h5">{formatCurrency(totalBalance)}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Bank</strong></TableCell>
              <TableCell><strong>Nickname</strong></TableCell>
              <TableCell><strong>Account No.</strong></TableCell>
              <TableCell align="right"><strong>Balance</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {accounts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No savings accounts found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              accounts.map((account) => (
                <TableRow key={account.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {formatBankName(account.bank_name)}
                    </Typography>
                  </TableCell>
                  <TableCell>{account.nickname || '—'}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      ••••&nbsp;{account.account_number?.slice(-4) || '****'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="medium">{formatCurrency(account.current_balance)}</Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={account.is_active ? 'Active' : 'Inactive'}
                      color={account.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<UploadIcon />}
                      onClick={() => handleOpenUpload(account)}
                    >
                      Upload Statement
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
            {accounts.length > 0 && (
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell colSpan={3}><strong>Total</strong></TableCell>
                <TableCell align="right"><strong>{formatCurrency(totalBalance)}</strong></TableCell>
                <TableCell /><TableCell />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ── Upload Statement dialog ────────────────────────────────────────── */}
      <Dialog open={openUploadDialog} onClose={handleCloseUpload} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Bank Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>

            {/* Account selector */}
            <TextField
              select
              label="Savings Account"
              value={uploadAccountId}
              onChange={(e) => setUploadAccountId(Number(e.target.value))}
              fullWidth
              required
            >
              {accounts.map((acc) => (
                <MenuItem key={acc.id} value={acc.id}>
                  {formatBankName(acc.bank_name)}
                  {acc.nickname ? ` · ${acc.nickname}` : ''} (••••{acc.account_number.slice(-4)})
                </MenuItem>
              ))}
            </TextField>

            {/* File picker */}
            <Button variant="outlined" component="label" startIcon={<UploadIcon />} fullWidth>
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
              label={isSBI ? 'Statement Password (required for SBI)' : 'Statement Password (if encrypted)'}
              type={showUploadPassword ? 'text' : 'password'}
              value={uploadPassword}
              onChange={(e) => setUploadPassword(e.target.value)}
              fullWidth
              helperText={
                isSBI
                  ? 'SBI statements are password-protected — usually your date of birth (DDMMYYYY)'
                  : 'Leave blank if the file is not password-protected'
              }
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

            {/* Result */}
            {uploadResult && (
              <Alert severity="success">
                <strong>Upload successful!</strong> Imported {uploadResult.imported} transactions
                ({uploadResult.categorized} auto-categorized, {uploadResult.duplicates} duplicates skipped).
              </Alert>
            )}

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

export default Savings;

// Made with Bob
