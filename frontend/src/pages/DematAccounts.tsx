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
  InputAdornment,
  CircularProgress
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CloudUpload as UploadIcon,
  Visibility,
  VisibilityOff
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import axios from 'axios';
import api, { brokersAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface DematAccount {
  id: number;
  broker_name: string;
  account_id: string;
  account_market: string;
  account_holder_name?: string;
  demat_account_number?: string;
  cash_balance: number;
  cash_balance_usd?: number;
  currency?: string;
  nickname?: string;
  is_active: boolean;
  asset_count?: number;
  total_invested?: number;
  current_value?: number;
  total_profit_loss?: number;
}

const DematAccounts: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [accounts, setAccounts] = useState<DematAccount[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<DematAccount | null>(null);
  const [formData, setFormData] = useState({
    broker_name: '',
    account_market: 'DOMESTIC',
    account_id: '',
    account_holder_name: '',
    demat_account_number: '',
    cash_balance: 0,
    cash_balance_usd: 0,
    nickname: '',
    is_active: true,
    portfolio_id: '' as number | '',
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadBroker, setUploadBroker] = useState('');
  const [statementType, setStatementType] = useState('broker_statement');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadPortfolioId, setUploadPortfolioId] = useState<number | ''>('' as number | '');

  const statementTypes = [
    { value: 'broker_statement', label: 'Broker Statement' },
    { value: 'demat_statement', label: 'Demat Statement' },
    { value: 'mutual_fund_statement', label: 'Mutual Fund Statement' },
    { value: 'vested_statement', label: 'Vested Statement' },
    { value: 'indmoney_statement', label: 'INDmoney Statement' }
  ];

  const [brokerNames, setBrokerNames] = useState<{ value: string; label: string; website?: string }[]>([]);

  useEffect(() => {
    fetchAccounts();
    fetchBrokerNames();
  }, [selectedPortfolioId]);

  const fetchAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const params: any = {};
      if (selectedPortfolioId) params.portfolio_id = selectedPortfolioId;
      const response = await axios.get('http://localhost:8000/api/v1/demat-accounts/', {
        headers: { Authorization: `Bearer ${token}` },
        params
      });
      setAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch demat accounts'));
    }
  };

  const fetchBrokerNames = async () => {
    try {
      const data = await brokersAPI.getAll({ is_active: true });
      setBrokerNames(
        Array.isArray(data)
          ? data.map((b: any) => ({ value: b.name, label: b.display_label, website: b.website }))
          : []
      );
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load broker list'));
    }
  };

  const handleOpenDialog = (account?: DematAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        broker_name: account.broker_name,
        account_market: account.account_market || 'DOMESTIC',
        account_id: account.account_id,
        account_holder_name: account.account_holder_name || '',
        demat_account_number: account.demat_account_number || '',
        cash_balance: account.cash_balance,
        cash_balance_usd: account.cash_balance_usd || 0,
        nickname: account.nickname || '',
        is_active: account.is_active,
        portfolio_id: (account as any).portfolio_id || selectedPortfolioId || '',
      });
    } else {
      setEditingAccount(null);
      setFormData({
        broker_name: '',
        account_market: 'DOMESTIC',
        account_id: '',
        account_holder_name: '',
        demat_account_number: '',
        cash_balance: 0,
        cash_balance_usd: 0,
        nickname: '',
        is_active: true,
        portfolio_id: selectedPortfolioId || '',
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
      const token = localStorage.getItem('token');
      
      // Prepare data based on account market type
      const isInternational = formData.account_market === 'INTERNATIONAL';
      const baseData = { ...formData, portfolio_id: formData.portfolio_id || undefined };
      const submitData = isInternational
        ? { ...baseData, cash_balance: 0 } // Backend will calculate INR from USD
        : { ...baseData, cash_balance_usd: 0 }; // Domestic accounts don't need USD
      
      if (editingAccount) {
        await axios.put(
          `http://localhost:8000/api/v1/demat-accounts/${editingAccount.id}`,
          submitData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        notify.success('Demat account updated successfully');
      } else {
        await axios.post(
          'http://localhost:8000/api/v1/demat-accounts/',
          submitData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        notify.success('Demat account added successfully');
      }
      handleCloseDialog();
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save demat account'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this demat account? This will also delete all associated assets.')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`http://localhost:8000/api/v1/demat-accounts/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      notify.success('Demat account deleted successfully');
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete demat account'));
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUploadStatement = async () => {
    if (!selectedFile || !uploadBroker || !statementType) {
      notify.error('Please fill all fields and select a file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('institution_name', uploadBroker);
      formData.append('statement_type', statementType);
      if (password) {
        formData.append('password', password);
      }
      if (uploadPortfolioId) {
        formData.append('portfolio_id', String(uploadPortfolioId));
      }

      await api.post('/statements/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setOpenUploadDialog(false);
      setSelectedFile(null);
      setUploadBroker('');
      setStatementType('broker_statement');
      setPassword('');
      notify.success('Statement uploaded and processed successfully');
      fetchAccounts();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement'));
    } finally {
      setUploading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const totalCashBalance = accounts.reduce((sum, acc) => sum + acc.cash_balance, 0);
  const totalInvested = accounts.reduce((sum, acc) => sum + (acc.total_invested || 0), 0);
  const totalCurrentValue = accounts.reduce((sum, acc) => sum + (acc.current_value || 0), 0);
  const totalProfitLoss = totalCurrentValue - totalInvested;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Demat/Trading Accounts</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => { setUploadPortfolioId(selectedPortfolioId || ''); setOpenUploadDialog(true); }}
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

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Accounts
              </Typography>
              <Typography variant="h4">{accounts.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Cash Balance
              </Typography>
              <Typography variant="h4">{formatCurrency(totalCashBalance)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Invested
              </Typography>
              <Typography variant="h4">{formatCurrency(totalInvested)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total P&L
              </Typography>
              <Typography 
                variant="h4" 
                color={totalProfitLoss >= 0 ? 'success.main' : 'error.main'}
              >
                {formatCurrency(totalProfitLoss)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Broker</TableCell>
              <TableCell>Account ID</TableCell>
              <TableCell>Holder Name</TableCell>
              <TableCell>Nickname</TableCell>
              <TableCell align="right">Cash Balance</TableCell>
              <TableCell align="right">Holdings Value</TableCell>
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
                      website={brokerNames.find((b) => b.value === account.broker_name)?.website}
                      name={brokerNames.find((b) => b.value === account.broker_name)?.label || account.broker_name}
                    />
                    {brokerNames.find((b) => b.value === account.broker_name)?.label || account.broker_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </Box>
                </TableCell>
                <TableCell>{account.account_id}</TableCell>
                <TableCell>{account.account_holder_name || '-'}</TableCell>
                <TableCell>{account.nickname || '-'}</TableCell>
                <TableCell align="right">
                  {account.account_market === 'INTERNATIONAL' && account.cash_balance_usd ? (
                    <Box>
                      <Typography variant="body2">${account.cash_balance_usd.toFixed(2)}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatCurrency(account.cash_balance)}
                      </Typography>
                    </Box>
                  ) : (
                    formatCurrency(account.cash_balance)
                  )}
                </TableCell>
                <TableCell align="right">
                  {account.current_value ? formatCurrency(account.current_value) : '-'}
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
      {/* Upload Statement Dialog */}
      <Dialog open={openUploadDialog} onClose={() => setOpenUploadDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Demat/Trading Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Broker"
              value={uploadBroker}
              onChange={(e) => {
                const broker = e.target.value;
                setUploadBroker(broker);
                // Auto-set statement type based on broker
                if (broker === 'vested') {
                  setStatementType('vested_statement');
                } else if (broker === 'indmoney') {
                  setStatementType('indmoney_statement');
                } else if (statementType === 'vested_statement' || statementType === 'indmoney_statement') {
                  // Reset to broker_statement if switching from Vested/INDMoney to another broker
                  setStatementType('broker_statement');
                }
              }}
              fullWidth
              required
            >
              {brokerNames.map((broker) => (
                <MenuItem key={broker.value} value={broker.value}>
                  {broker.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Statement Type"
              value={statementType}
              onChange={(e) => setStatementType(e.target.value)}
              fullWidth
              required
              disabled={uploadBroker === 'vested' || uploadBroker === 'indmoney'}
              helperText={
                uploadBroker === 'vested'
                  ? 'Statement type is automatically set for Vested'
                  : uploadBroker === 'indmoney'
                  ? 'Statement type is automatically set for INDMoney'
                  : ''
              }
            >
              {statementTypes
                .filter(type => {
                  // Show only relevant statement types based on broker
                  if (uploadBroker === 'vested') return type.value === 'vested_statement';
                  if (uploadBroker === 'indmoney') return type.value === 'indmoney_statement';
                  // For other brokers, exclude vested and indmoney statement types
                  return type.value !== 'vested_statement' && type.value !== 'indmoney_statement';
                })
                .map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
            </TextField>

            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
              fullWidth
            >
              {selectedFile ? selectedFile.name : 'Select File'}
              <input
                type="file"
                hidden
                accept=".pdf,.xlsx,.xls,.csv"
                onChange={handleFileSelect}
              />
            </Button>

            <TextField
              label="Password (if PDF is encrypted)"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              fullWidth
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              select
              label="Portfolio"
              value={uploadPortfolioId}
              onChange={(e) => setUploadPortfolioId(e.target.value ? Number(e.target.value) : '')}
              fullWidth
              helperText="Assets from this statement will be assigned to the selected portfolio"
            >
              <MenuItem value="">Default Portfolio</MenuItem>
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </TextField>

          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenUploadDialog(false)} disabled={uploading}>
            Cancel
          </Button>
          <Button
            onClick={handleUploadStatement}
            variant="contained" 
            disabled={uploading || !selectedFile}
            startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
      </TableContainer>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingAccount ? 'Edit Demat Account' : 'Add Demat Account'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Broker Name"
              value={formData.broker_name}
              onChange={(e) => setFormData({ ...formData, broker_name: e.target.value })}
              fullWidth
            >
              {brokerNames.map((broker) => (
                <MenuItem key={broker.value} value={broker.value}>
                  {broker.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Account Market"
              value={formData.account_market}
              onChange={(e) => setFormData({ ...formData, account_market: e.target.value })}
              fullWidth
              helperText="Domestic for INR-based trading, International for foreign stock trading (USD)"
            >
              <MenuItem value="DOMESTIC">Domestic (INR)</MenuItem>
              <MenuItem value="INTERNATIONAL">International (USD)</MenuItem>
            </TextField>

            <TextField
              label="Account ID / Client ID"
              value={formData.account_id}
              onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
              fullWidth
              required
            />

            <TextField
              label="Account Holder Name (Optional)"
              value={formData.account_holder_name}
              onChange={(e) => setFormData({ ...formData, account_holder_name: e.target.value })}
              fullWidth
            />

            <TextField
              label="Demat Account Number (Optional)"
              value={formData.demat_account_number}
              onChange={(e) => setFormData({ ...formData, demat_account_number: e.target.value })}
              fullWidth
              helperText="DP ID + Client ID"
            />

            <TextField
              label="Nickname (Optional)"
              value={formData.nickname}
              onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
              fullWidth
            />

            <TextField
              select
              label="Portfolio"
              value={formData.portfolio_id}
              onChange={(e) => setFormData({ ...formData, portfolio_id: e.target.value ? Number(e.target.value) : '' })}
              fullWidth
            >
              <MenuItem value="">None</MenuItem>
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </TextField>

            <TextField
              label={formData.account_market === 'INTERNATIONAL' ? 'Cash Balance (USD)' : 'Cash Balance (INR)'}
              type="number"
              value={
                formData.account_market === 'INTERNATIONAL'
                  ? formData.cash_balance_usd
                  : formData.cash_balance
              }
              onChange={(e) => {
                const value = parseFloat(e.target.value) || 0;
                if (formData.account_market === 'INTERNATIONAL') {
                  setFormData({ ...formData, cash_balance_usd: value, cash_balance: 0 });
                } else {
                  setFormData({ ...formData, cash_balance: value, cash_balance_usd: 0 });
                }
              }}
              fullWidth
              helperText={
                formData.account_market === 'INTERNATIONAL'
                  ? 'Enter amount in USD (will be converted to INR automatically)'
                  : 'Available cash in trading account'
              }
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    {formData.account_market === 'INTERNATIONAL' ? '$' : '₹'}
                  </InputAdornment>
                ),
              }}
            />
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

export default DematAccounts;

// Made with Bob