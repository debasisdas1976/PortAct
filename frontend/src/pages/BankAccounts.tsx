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
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CloudUpload as UploadIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolios } from '../store/slices/portfolioSlice';
import api, { banksAPI } from '../services/api';
import CompanyIcon from '../components/CompanyIcon';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

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

/** Parse a bank's supported_formats (JSON or legacy flat) for a specific account type. */
const getBankAccountTypeConfig = (
  supportedFormats: string | null,
  hasParser: boolean,
  accountType: string
): { has_parser: boolean; formats: string[] } => {
  if (supportedFormats) {
    try {
      const parsed = JSON.parse(supportedFormats);
      if (typeof parsed === 'object' && !Array.isArray(parsed)) {
        const entry = parsed[accountType];
        if (entry) {
          return {
            has_parser: !!entry.has_parser,
            formats: entry.formats ? entry.formats.split(',').filter(Boolean) : [],
          };
        }
        return { has_parser: false, formats: [] };
      }
    } catch {
      // Not JSON — legacy flat format
    }
    const formats = supportedFormats.split(',').map((s: string) => s.trim()).filter(Boolean);
    return { has_parser: hasParser, formats };
  }
  return { has_parser: hasParser, formats: [] };
};

const BankAccounts: React.FC = () => {
  const { notify } = useNotification();
  const dispatch = useDispatch<AppDispatch>();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [accounts, setAccounts] = useState<BankAccount[]>([]);

  // Add/Edit dialog
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<BankAccount | null>(null);
  const [formData, setFormData] = useState({
    bank_name: '',
    account_type: 'savings',
    account_number: '',
    nickname: '',
    current_balance: 0,
    available_balance: 0,
    credit_limit: 0,
    is_active: true,
    portfolio_id: '' as number | '',
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
  const [uploadPortfolioId, setUploadPortfolioId] = useState<number | ''>('' as number | '');

  const [bankNames, setBankNames] = useState<{ value: string; label: string; website?: string; has_parser: boolean; supported_formats: string | null }[]>([]);

  const accountTypes = [
    { value: 'savings', label: 'Savings' },
    { value: 'current', label: 'Current' },
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'fixed_deposit', label: 'Fixed Deposit' },
    { value: 'recurring_deposit', label: 'Recurring Deposit' },
  ];

  useEffect(() => {
    fetchAccounts();
    fetchBankNames();
    dispatch(fetchPortfolios());
  }, [dispatch]);

  const fetchAccounts = async () => {
    try {
      const response = await api.get('/bank-accounts/');
      setAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch bank accounts'));
    }
  };

  const fetchBankNames = async () => {
    try {
      const data = await banksAPI.getAll({ is_active: true });
      setBankNames(
        Array.isArray(data)
          ? data.map((b: any) => ({ value: b.name, label: b.display_label, website: b.website, has_parser: b.has_parser ?? false, supported_formats: b.supported_formats ?? null }))
          : []
      );
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load bank list'));
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
        portfolio_id: (account as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
      });
    } else {
      setEditingAccount(null);
      setFormData({
        bank_name: '',
        account_type: 'savings',
        account_number: '',
        nickname: '',
        current_balance: 0,
        available_balance: 0,
        credit_limit: 0,
        is_active: true,
        portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
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
      const payload = { ...formData, portfolio_id: formData.portfolio_id || undefined };
      if (editingAccount) {
        await api.put(`/bank-accounts/${editingAccount.id}`, payload);
        notify.success('Bank account updated successfully');
      } else {
        await api.post('/bank-accounts/', payload);
        notify.success('Bank account added successfully');
      }
      handleCloseDialog();
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save bank account'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this bank account? All expenses linked to this account will also be permanently deleted.')) return;
    try {
      await api.delete(`/bank-accounts/${id}`);
      notify.success('Bank account deleted successfully');
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete bank account'));
    }
  };

  // ── Upload dialog ──────────────────────────────────────────────────────────
  const handleOpenUpload = (account?: BankAccount) => {
    setUploadAccountId(account ? account.id : '');
    setSelectedFile(null);
    setUploadPassword('');
    setAutoCategorize(true);
    setUploadResult(null);
    setUploadPortfolioId(selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''));
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
      if (uploadPortfolioId) {
        formPayload.append('portfolio_id', String(uploadPortfolioId));
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

  // ── Helpers ────────────────────────────────────────────────────────────────
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);

  const getBankInfo = (bankName: string) => bankNames.find((b) => b.value === bankName);

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.current_balance, 0);

  const selectedAccountForUpload = accounts.find((a) => a.id === uploadAccountId);
  const needsPassword =
    selectedAccountForUpload?.bank_name === 'state_bank_of_india' ||
    selectedAccountForUpload?.bank_name === 'other';

  // Compute accepted formats for the selected account's bank + account type
  const selectedBankInfo = selectedAccountForUpload
    ? bankNames.find((b) => b.value === selectedAccountForUpload.bank_name)
    : null;
  const selectedUploadConfig = selectedBankInfo && selectedAccountForUpload
    ? getBankAccountTypeConfig(selectedBankInfo.supported_formats, selectedBankInfo.has_parser, selectedAccountForUpload.account_type)
    : null;
  const uploadAcceptFormats = selectedUploadConfig?.formats.length
    ? selectedUploadConfig.formats.map((f) => `.${f}`).join(',')
    : '.pdf,.xlsx,.xls,.csv';
  const uploadFormatLabel = selectedUploadConfig?.formats.length
    ? selectedUploadConfig.formats.map((f) => `.${f.toUpperCase()}`).join(' / ')
    : '.PDF / .XLSX / .XLS';

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
                    <CompanyIcon
                      website={getBankInfo(account.bank_name)?.website}
                      name={getBankInfo(account.bank_name)?.label || account.bank_name}
                    />
                    {getBankInfo(account.bank_name)?.label || account.bank_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
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
              select
              label="Portfolio"
              value={formData.portfolio_id}
              onChange={(e) => setFormData({ ...formData, portfolio_id: e.target.value ? Number(e.target.value) : '' })}
              fullWidth
            >
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
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

            {/* Account selector — filtered by per-account-type parser availability */}
            <TextField
              select
              label="Bank Account"
              value={uploadAccountId}
              onChange={(e) => { setUploadAccountId(Number(e.target.value)); setSelectedFile(null); }}
              fullWidth
              required
            >
              {accounts
                .filter((acc) => {
                  const bank = bankNames.find((b) => b.value === acc.bank_name);
                  if (!bank) return false;
                  const cfg = getBankAccountTypeConfig(bank.supported_formats, bank.has_parser, acc.account_type);
                  return cfg.has_parser;
                })
                .map((acc) => {
                  const bank = bankNames.find((b) => b.value === acc.bank_name);
                  const cfg = bank ? getBankAccountTypeConfig(bank.supported_formats, bank.has_parser, acc.account_type) : null;
                  return (
                    <MenuItem key={acc.id} value={acc.id}>
                      <Box>
                        {bank?.label || acc.bank_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                        {acc.nickname ? ` · ${acc.nickname}` : ''} (****{acc.account_number.slice(-4)})
                        {cfg && cfg.formats.length > 0 && (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                            ({cfg.formats.map((f) => f.toUpperCase()).join(', ')})
                          </Typography>
                        )}
                      </Box>
                    </MenuItem>
                  );
                })}
            </TextField>

            {/* Portfolio */}
            <TextField
              select
              label="Portfolio"
              value={uploadPortfolioId}
              onChange={(e) => setUploadPortfolioId(e.target.value ? Number(e.target.value) : '')}
              fullWidth
            >
              <MenuItem value="">Default Portfolio</MenuItem>
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </TextField>

            {/* File picker — accepted formats driven by selected account's config */}
            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
              fullWidth
              disabled={!uploadAccountId}
            >
              {selectedFile ? selectedFile.name : `Select Statement File (${uploadFormatLabel})`}
              <input
                type="file"
                hidden
                accept={uploadAcceptFormats}
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
