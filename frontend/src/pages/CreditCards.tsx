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
  CreditCard as CreditCardIcon,
  Add as AddIcon,
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import api, { banksAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';
import { useSelector } from 'react-redux';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { RootState } from '../store';

interface BankAccount {
  id: number;
  bank_name: string;
  account_type: string;
  account_number: string;
  nickname?: string;
  current_balance: number;
  credit_limit: number;
  available_balance: number;
  is_active: boolean;
}

const formatBankNameFallback = (name: string) =>
  name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const CreditCards: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(true);

  // Add/Edit account dialog state
  const [openAccountDialog, setOpenAccountDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<BankAccount | null>(null);
  const [accountFormData, setAccountFormData] = useState({
    bank_name: '',
    account_type: 'credit_card',
    account_number: '',
    nickname: '',
    current_balance: 0,
    available_balance: 0,
    credit_limit: 0,
    is_active: true,
    portfolio_id: '' as number | '',
  });
  const [accountSubmitting, setAccountSubmitting] = useState(false);

  const [bankNames, setBankNames] = useState<{ value: string; label: string; website?: string }[]>([]);

  // Upload dialog state
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [uploadAccountId, setUploadAccountId] = useState<number | '' | 'new'>('');
  const [newAccountBank, setNewAccountBank] = useState('');
  const [newAccountNumber, setNewAccountNumber] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadPassword, setUploadPassword] = useState('');
  const [showUploadPassword, setShowUploadPassword] = useState(false);
  const [autoCategorize, setAutoCategorize] = useState(true);
  const [newAccountPortfolio, setNewAccountPortfolio] = useState<number | ''>('' as number | '');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ imported: number; duplicates: number; categorized: number } | null>(null);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const response = await api.get('/bank-accounts/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      const filtered = (response.data as BankAccount[]).filter(
        (a) => a.account_type === 'credit_card' && a.is_active
      );
      setAccounts(filtered);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch credit cards'));
    } finally {
      setLoading(false);
    }
  };

  const fetchBankNames = async () => {
    try {
      const data = await banksAPI.getAll({ is_active: true });
      setBankNames(
        Array.isArray(data)
          ? data.map((b: any) => ({ value: b.name, label: b.display_label, website: b.website }))
          : []
      );
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load bank list'));
    }
  };

  useEffect(() => {
    fetchAccounts();
    fetchBankNames();
  }, [selectedPortfolioId]);

  const formatBankName = (name: string) =>
    bankNames.find((b) => b.value === name)?.label || formatBankNameFallback(name);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const totalOutstanding = accounts.reduce((s, a) => s + (a.current_balance || 0), 0);
  const totalCreditLimit = accounts.reduce((s, a) => s + (a.credit_limit || 0), 0);

  // ── Add / Edit account handlers ──────────────────────────────────────────
  const handleOpenAccountDialog = (account?: BankAccount) => {
    if (account) {
      setEditingAccount(account);
      setAccountFormData({
        bank_name: account.bank_name,
        account_type: account.account_type,
        account_number: account.account_number,
        nickname: account.nickname || '',
        current_balance: account.current_balance,
        available_balance: account.available_balance || 0,
        credit_limit: account.credit_limit || 0,
        is_active: account.is_active,
        portfolio_id: (account as any).portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
      });
    } else {
      setEditingAccount(null);
      setAccountFormData({
        bank_name: '',
        account_type: 'credit_card',
        account_number: '',
        nickname: '',
        current_balance: 0,
        available_balance: 0,
        credit_limit: 0,
        is_active: true,
        portfolio_id: selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
      });
    }
    setOpenAccountDialog(true);
  };

  const handleCloseAccountDialog = () => {
    setOpenAccountDialog(false);
    setEditingAccount(null);
  };

  const handleAccountSubmit = async () => {
    if (!accountFormData.account_number.trim()) {
      notify.error('Card number is required');
      return;
    }
    try {
      setAccountSubmitting(true);
      const submitData = { ...accountFormData, portfolio_id: accountFormData.portfolio_id || undefined };
      if (editingAccount) {
        await api.put(`/bank-accounts/${editingAccount.id}`, submitData);
        notify.success('Credit card updated successfully');
      } else {
        await api.post('/bank-accounts/', submitData);
        notify.success('Credit card added successfully');
      }
      handleCloseAccountDialog();
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to ${editingAccount ? 'update' : 'add'} credit card`));
    } finally {
      setAccountSubmitting(false);
    }
  };

  // ── Delete handler ───────────────────────────────────────────────────────
  const handleDelete = async (account: BankAccount) => {
    if (!window.confirm(
      `Delete ${formatBankName(account.bank_name)} (••••${account.account_number.slice(-4)})? ` +
      `All expenses linked to this card will also be permanently deleted. This cannot be undone.`
    )) {
      return;
    }
    try {
      await api.delete(`/bank-accounts/${account.id}`);
      notify.success('Credit card deleted');
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete credit card'));
    }
  };

  // ── Upload handlers ────────────────────────────────────────────────────────
  const handleOpenUpload = (account?: BankAccount) => {
    setUploadAccountId(account ? account.id : '');
    setNewAccountBank('');
    setNewAccountNumber('');
    setNewAccountPortfolio(selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''));
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
    if (!selectedFile) {
      notify.error('Please select a statement file');
      return;
    }

    if (uploadAccountId === 'new' && !newAccountNumber.trim()) {
      notify.error('Please enter the card number for the new credit card');
      return;
    }

    if (!uploadAccountId) {
      notify.error('Please select a card or choose "+ New Card"');
      return;
    }

    try {
      setUploading(true);

      let accountId: number;

      if (uploadAccountId === 'new') {
        // Create the credit card account first
        const createRes = await api.post('/bank-accounts/', {
          bank_name: newAccountBank,
          account_type: 'credit_card',
          account_number: newAccountNumber.trim(),
          current_balance: 0,
          available_balance: 0,
          credit_limit: 0,
          is_active: true,
          portfolio_id: newAccountPortfolio || undefined,
        });
        accountId = createRes.data.id;
        notify.success('Credit card created');
      } else {
        accountId = uploadAccountId as number;
      }

      const formPayload = new FormData();
      formPayload.append('file', selectedFile);
      formPayload.append('bank_account_id', String(accountId));
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

      // Refresh accounts list (picks up new account + updated balances)
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement. Please check the file and password.'));
    } finally {
      setUploading(false);
    }
  };

  const selectedAccountForUpload = uploadAccountId !== 'new' ? accounts.find((a) => a.id === uploadAccountId) : undefined;
  const isSBI = uploadAccountId === 'new'
    ? newAccountBank === 'state_bank_of_india'
    : selectedAccountForUpload?.bank_name === 'state_bank_of_india';

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
          <CreditCardIcon color="primary" />
          <Typography variant="h4">Credit Cards</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<UploadIcon />} onClick={() => handleOpenUpload()}>
            Upload Statement
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenAccountDialog()}>
            Add Credit Card
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Cards</Typography>
              <Typography variant="h4">{accounts.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Outstanding</Typography>
              <Typography variant="h5" color={totalOutstanding > 0 ? 'error.main' : 'text.primary'}>
                {formatCurrency(totalOutstanding)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Credit Limit</Typography>
              <Typography variant="h5">{formatCurrency(totalCreditLimit)}</Typography>
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
              <TableCell><strong>Card No.</strong></TableCell>
              <TableCell align="right"><strong>Credit Limit</strong></TableCell>
              <TableCell align="right"><strong>Outstanding</strong></TableCell>
              <TableCell align="right"><strong>Available</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {accounts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">No credit cards found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              accounts.map((account) => (
                <TableRow key={account.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CompanyIcon
                        website={bankNames.find((b) => b.value === account.bank_name)?.website}
                        name={formatBankName(account.bank_name)}
                      />
                      <Typography variant="body2" fontWeight="medium">
                        {formatBankName(account.bank_name)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{account.nickname || '—'}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      ••••&nbsp;{account.account_number?.slice(-4) || '****'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="medium">{formatCurrency(account.credit_limit || 0)}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="medium" color={account.current_balance > 0 ? 'error.main' : 'text.primary'}>
                      {formatCurrency(account.current_balance)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="medium" color="success.main">
                      {formatCurrency(account.available_balance || 0)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
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
                      title="Edit card"
                      onClick={() => handleOpenAccountDialog(account)}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      title="Delete card"
                      onClick={() => handleDelete(account)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
            {accounts.length > 0 && (
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell colSpan={3}><strong>Total</strong></TableCell>
                <TableCell align="right"><strong>{formatCurrency(totalCreditLimit)}</strong></TableCell>
                <TableCell align="right"><strong>{formatCurrency(totalOutstanding)}</strong></TableCell>
                <TableCell align="right"><strong>{formatCurrency(totalCreditLimit - totalOutstanding)}</strong></TableCell>
                <TableCell /><TableCell />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ── Upload Statement dialog ────────────────────────────────────────── */}
      <Dialog open={openUploadDialog} onClose={handleCloseUpload} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Credit Card Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>

            {/* Account selector */}
            <TextField
              select
              label="Credit Card"
              value={uploadAccountId}
              onChange={(e) => {
                const val = e.target.value;
                setUploadAccountId(val === 'new' ? 'new' : Number(val));
              }}
              fullWidth
              required
            >
              <MenuItem value="new" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                + New Card
              </MenuItem>
              {accounts.map((acc) => (
                <MenuItem key={acc.id} value={acc.id}>
                  {formatBankName(acc.bank_name)}
                  {acc.nickname ? ` · ${acc.nickname}` : ''} (••••{acc.account_number.slice(-4)})
                </MenuItem>
              ))}
            </TextField>

            {/* New account fields – shown when "+ New Card" is selected */}
            {uploadAccountId === 'new' && (
              <>
                <TextField
                  select
                  label="Bank Name"
                  value={newAccountBank}
                  onChange={(e) => setNewAccountBank(e.target.value)}
                  fullWidth
                >
                  {bankNames.map((bank) => (
                    <MenuItem key={bank.value} value={bank.value}>{bank.label}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Card Number"
                  value={newAccountNumber}
                  onChange={(e) => setNewAccountNumber(e.target.value)}
                  fullWidth
                  required
                />
                <TextField
                  select
                  label="Portfolio"
                  value={newAccountPortfolio}
                  onChange={(e) => setNewAccountPortfolio(e.target.value ? Number(e.target.value) : '')}
                  fullWidth
                >
                  {portfolios.map((p: any) => (
                    <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
                  ))}
                </TextField>
              </>
            )}

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
              disabled={uploading || !selectedFile || !uploadAccountId || (uploadAccountId === 'new' && !newAccountNumber.trim())}
              startIcon={uploading ? <CircularProgress size={18} /> : <UploadIcon />}
            >
              {uploading ? 'Uploading…' : 'Upload'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* ── Add / Edit Credit Card dialog ─────────────────────────────── */}
      <Dialog open={openAccountDialog} onClose={handleCloseAccountDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingAccount ? 'Edit Credit Card' : 'Add Credit Card'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Bank Name"
              value={accountFormData.bank_name}
              onChange={(e) => setAccountFormData({ ...accountFormData, bank_name: e.target.value })}
              fullWidth
            >
              {bankNames.map((bank) => (
                <MenuItem key={bank.value} value={bank.value}>{bank.label}</MenuItem>
              ))}
            </TextField>

            <TextField
              label="Card Number"
              value={accountFormData.account_number}
              onChange={(e) => setAccountFormData({ ...accountFormData, account_number: e.target.value })}
              fullWidth
              required
            />

            <TextField
              label="Nickname (Optional)"
              value={accountFormData.nickname}
              onChange={(e) => setAccountFormData({ ...accountFormData, nickname: e.target.value })}
              fullWidth
              helperText="e.g. Amazon Pay Card, Travel Card"
            />

            <TextField
              select
              label="Portfolio"
              value={accountFormData.portfolio_id}
              onChange={(e) => setAccountFormData({ ...accountFormData, portfolio_id: e.target.value ? Number(e.target.value) : '' })}
              fullWidth
            >
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </TextField>

            <TextField
              label="Credit Limit"
              type="number"
              value={accountFormData.credit_limit}
              onChange={(e) => {
                const limit = parseFloat(e.target.value) || 0;
                setAccountFormData({
                  ...accountFormData,
                  credit_limit: limit,
                  available_balance: limit - accountFormData.current_balance,
                });
              }}
              fullWidth
              InputProps={{
                startAdornment: <InputAdornment position="start">₹</InputAdornment>,
              }}
            />

            <TextField
              label="Outstanding Balance"
              type="number"
              value={accountFormData.current_balance}
              onChange={(e) => {
                const balance = parseFloat(e.target.value) || 0;
                setAccountFormData({
                  ...accountFormData,
                  current_balance: balance,
                  available_balance: accountFormData.credit_limit - balance,
                });
              }}
              fullWidth
              InputProps={{
                startAdornment: <InputAdornment position="start">₹</InputAdornment>,
              }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAccountDialog}>Cancel</Button>
          <Button
            onClick={handleAccountSubmit}
            variant="contained"
            disabled={accountSubmitting || !accountFormData.account_number.trim()}
            startIcon={accountSubmitting ? <CircularProgress size={18} /> : editingAccount ? <EditIcon /> : <AddIcon />}
          >
            {accountSubmitting ? 'Saving…' : editingAccount ? 'Update' : 'Add Card'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CreditCards;
