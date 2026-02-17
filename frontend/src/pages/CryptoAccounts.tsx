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
  Autocomplete,
  CircularProgress
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CurrencyBitcoin as CryptoIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface CryptoAccount {
  id: number;
  exchange_name: string;
  account_id: string;
  account_holder_name?: string;
  wallet_address?: string;
  cash_balance_usd: number;
  total_value_usd: number;
  nickname?: string;
  is_active: boolean;
  asset_count?: number;
  total_invested_usd?: number;
  current_value_usd?: number;
  total_profit_loss_usd?: number;
}

interface CryptoSearchResult {
  id: string;
  symbol: string;
  name: string;
}

const CryptoAccounts: React.FC = () => {
  const [accounts, setAccounts] = useState<CryptoAccount[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [openAssetDialog, setOpenAssetDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<CryptoAccount | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    exchange_name: 'binance',
    account_id: '',
    account_holder_name: '',
    wallet_address: '',
    cash_balance_usd: 0,
    nickname: '',
    is_active: true
  });
  
  const [assetForm, setAssetForm] = useState({
    name: '',
    symbol: '',
    coin_id: '',
    quantity: 0,
    purchase_price: 0,
    total_invested: 0
  });
  const [cryptoOptions, setCryptoOptions] = useState<CryptoSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const exchangeNames = [
    { value: 'binance', label: 'Binance' },
    { value: 'coinbase', label: 'Coinbase' },
    { value: 'kraken', label: 'Kraken' },
    { value: 'wazirx', label: 'WazirX' },
    { value: 'coindcx', label: 'CoinDCX' },
    { value: 'zebpay', label: 'ZebPay' },
    { value: 'coinswitch', label: 'CoinSwitch' },
    { value: 'kucoin', label: 'KuCoin' },
    { value: 'bybit', label: 'Bybit' },
    { value: 'okx', label: 'OKX' },
    { value: 'metamask', label: 'MetaMask' },
    { value: 'trust_wallet', label: 'Trust Wallet' },
    { value: 'ledger', label: 'Ledger' },
    { value: 'trezor', label: 'Trezor' },
    { value: 'other', label: 'Other' }
  ];

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/crypto-accounts/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAccounts(response.data);
    } catch (err) {
      setError('Failed to fetch crypto accounts');
    }
  };

  const searchCrypto = async (query: string) => {
    if (!query || query.length < 2) {
      setCryptoOptions([]);
      return;
    }
    
    setSearchLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:8000/api/v1/prices/crypto/search?query=${query}&limit=10`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCryptoOptions(response.data.results || []);
    } catch (err) {
      console.error('Failed to search crypto:', err);
    } finally {
      setSearchLoading(false);
    }
  };

  const fetchCryptoPrice = async (symbol: string) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:8000/api/v1/prices/crypto/${symbol}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCurrentPrice(response.data.price);
      return response.data.price;
    } catch (err) {
      console.error('Failed to fetch price:', err);
      return null;
    }
  };

  const handleOpenDialog = (account?: CryptoAccount) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        exchange_name: account.exchange_name,
        account_id: account.account_id,
        account_holder_name: account.account_holder_name || '',
        wallet_address: account.wallet_address || '',
        cash_balance_usd: account.cash_balance_usd,
        nickname: account.nickname || '',
        is_active: account.is_active
      });
    } else {
      setEditingAccount(null);
      setFormData({
        exchange_name: 'binance',
        account_id: '',
        account_holder_name: '',
        wallet_address: '',
        cash_balance_usd: 0,
        nickname: '',
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

  const handleOpenAssetDialog = (accountId: number) => {
    setSelectedAccount(accountId);
    setAssetForm({
      name: '',
      symbol: '',
      coin_id: '',
      quantity: 0,
      purchase_price: 0,
      total_invested: 0
    });
    setCurrentPrice(null);
    setOpenAssetDialog(true);
  };

  const handleCloseAssetDialog = () => {
    setOpenAssetDialog(false);
    setSelectedAccount(null);
    setCurrentPrice(null);
  };

  const handleSubmit = async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (editingAccount) {
        await axios.put(
          `http://localhost:8000/api/v1/crypto-accounts/${editingAccount.id}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSuccess('Crypto account updated successfully');
      } else {
        await axios.post(
          'http://localhost:8000/api/v1/crypto-accounts/',
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSuccess('Crypto account created successfully');
      }
      handleCloseDialog();
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save crypto account');
    }
  };

  const handleSubmitAsset = async () => {
    if (!selectedAccount) return;
    
    try {
      const token = localStorage.getItem('token');
      const assetData = {
        asset_type: 'crypto',
        name: assetForm.name,
        symbol: assetForm.symbol,
        quantity: assetForm.quantity,
        purchase_price: assetForm.purchase_price,
        current_price: currentPrice || assetForm.purchase_price,
        total_invested: assetForm.total_invested,
        crypto_account_id: selectedAccount,
        details: {
          coin_id: assetForm.coin_id
        }
      };
      
      await axios.post('http://localhost:8000/api/v1/assets/', assetData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Crypto asset added successfully');
      handleCloseAssetDialog();
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add crypto asset');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this crypto account? This will also delete all associated assets.')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`http://localhost:8000/api/v1/crypto-accounts/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Crypto account deleted successfully');
      fetchAccounts();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete crypto account');
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const totalCashBalance = accounts.reduce((sum, acc) => sum + acc.cash_balance_usd, 0);
  const totalInvested = accounts.reduce((sum, acc) => sum + (acc.total_invested_usd || 0), 0);
  const totalCurrentValue = accounts.reduce((sum, acc) => sum + (acc.current_value_usd || 0), 0);
  const totalProfitLoss = totalCurrentValue - totalInvested;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Crypto Accounts</Typography>
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
              <TableCell>Exchange</TableCell>
              <TableCell>Account ID</TableCell>
              <TableCell>Holder Name</TableCell>
              <TableCell>Nickname</TableCell>
              <TableCell align="right">Cash Balance (USD)</TableCell>
              <TableCell align="right">Holdings Value (USD)</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {accounts.map((account) => (
              <TableRow key={account.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CryptoIcon />
                    {exchangeNames.find(e => e.value === account.exchange_name)?.label || account.exchange_name}
                  </Box>
                </TableCell>
                <TableCell>{account.account_id}</TableCell>
                <TableCell>{account.account_holder_name || '-'}</TableCell>
                <TableCell>{account.nickname || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(account.cash_balance_usd)}</TableCell>
                <TableCell align="right">
                  {account.current_value_usd ? formatCurrency(account.current_value_usd) : '-'}
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
                    onClick={() => handleOpenAssetDialog(account.id)}
                    color="primary"
                    title="Add Crypto Asset"
                  >
                    <AddIcon />
                  </IconButton>
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

      {/* Account Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingAccount ? 'Edit' : 'Add'} Crypto Account</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Exchange"
              value={formData.exchange_name}
              onChange={(e) => setFormData({ ...formData, exchange_name: e.target.value })}
              fullWidth
            >
              {exchangeNames.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Account ID / Username"
              value={formData.account_id}
              onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
              required
              fullWidth
            />
            <TextField
              label="Account Holder Name"
              value={formData.account_holder_name}
              onChange={(e) => setFormData({ ...formData, account_holder_name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Wallet Address (Optional)"
              value={formData.wallet_address}
              onChange={(e) => setFormData({ ...formData, wallet_address: e.target.value })}
              fullWidth
            />
            <TextField
              label="Cash Balance (USD)"
              type="number"
              value={formData.cash_balance_usd}
              onChange={(e) => setFormData({ ...formData, cash_balance_usd: parseFloat(e.target.value) || 0 })}
              fullWidth
            />
            <TextField
              label="Nickname (Optional)"
              value={formData.nickname}
              onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
              fullWidth
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

      {/* Add Asset Dialog */}
      <Dialog open={openAssetDialog} onClose={handleCloseAssetDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add Crypto Asset</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <Autocomplete
              options={cryptoOptions}
              getOptionLabel={(option) => `${option.symbol.toUpperCase()} - ${option.name}`}
              loading={searchLoading}
              onInputChange={(_, value) => searchCrypto(value)}
              onChange={async (_, value) => {
                if (value) {
                  setAssetForm({
                    ...assetForm,
                    name: value.name,
                    symbol: value.symbol.toUpperCase(),
                    coin_id: value.id
                  });
                  const price = await fetchCryptoPrice(value.symbol);
                  if (price) {
                    setAssetForm(prev => ({
                      ...prev,
                      purchase_price: price
                    }));
                  }
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Search Cryptocurrency"
                  placeholder="Type BTC, ETH, etc."
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {searchLoading ? <CircularProgress size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
            />
            {currentPrice && (
              <Alert severity="info">
                Current Price: {formatCurrency(currentPrice)}
              </Alert>
            )}
            <TextField
              label="Quantity"
              type="number"
              value={assetForm.quantity}
              onChange={(e) => {
                const qty = parseFloat(e.target.value) || 0;
                setAssetForm({
                  ...assetForm,
                  quantity: qty,
                  total_invested: qty * assetForm.purchase_price
                });
              }}
              required
              fullWidth
            />
            <TextField
              label="Purchase Price (USD)"
              type="number"
              value={assetForm.purchase_price}
              onChange={(e) => {
                const price = parseFloat(e.target.value) || 0;
                setAssetForm({
                  ...assetForm,
                  purchase_price: price,
                  total_invested: assetForm.quantity * price
                });
              }}
              required
              fullWidth
            />
            <TextField
              label="Total Invested (USD)"
              type="number"
              value={assetForm.total_invested}
              InputProps={{ readOnly: true }}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAssetDialog}>Cancel</Button>
          <Button 
            onClick={handleSubmitAsset} 
            variant="contained"
            disabled={!assetForm.symbol || !assetForm.quantity}
          >
            Add Asset
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CryptoAccounts;

// Made with Bob