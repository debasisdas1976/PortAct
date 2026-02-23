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
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolios } from '../store/slices/portfolioSlice';
import api, { cryptoExchangesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';
import CryptoAssetDialog from '../components/CryptoAssetDialog';

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
  portfolio_id?: number;
}

interface CryptoExchange {
  id: number;
  name: string;
  display_label: string;
  exchange_type: string;
  website?: string | null;
  is_active: boolean;
  sort_order: number;
}

const CryptoAccounts: React.FC = () => {
  const { notify } = useNotification();
  const dispatch = useDispatch<AppDispatch>();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [accounts, setAccounts] = useState<CryptoAccount[]>([]);
  const [exchanges, setExchanges] = useState<CryptoExchange[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<CryptoAccount | null>(null);
  const [formData, setFormData] = useState({
    exchange_name: '',
    account_id: '',
    account_holder_name: '',
    wallet_address: '',
    cash_balance_usd: 0,
    nickname: '',
    is_active: true,
    portfolio_id: '' as number | '',
  });

  // Asset dialog state
  const [assetDialogOpen, setAssetDialogOpen] = useState(false);
  const [selectedAccountForAsset, setSelectedAccountForAsset] = useState<number | undefined>(undefined);

  useEffect(() => {
    fetchData();
    dispatch(fetchPortfolios());
  }, [dispatch]);

  const fetchData = async () => {
    try {
      const [accountsRes, exchangesData] = await Promise.all([
        api.get('/crypto-accounts/'),
        cryptoExchangesAPI.getAll({ is_active: true }),
      ]);
      setAccounts(accountsRes.data);
      setExchanges(exchangesData);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch data'));
    }
  };

  const getExchange = (name: string) => exchanges.find(e => e.name === name);
  const getExchangeLabel = (name: string) => getExchange(name)?.display_label || name;

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
        is_active: account.is_active,
        portfolio_id: account.portfolio_id || selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : ''),
      });
    } else {
      setEditingAccount(null);
      setFormData({
        exchange_name: exchanges.length > 0 ? exchanges[0].name : '',
        account_id: '',
        account_holder_name: '',
        wallet_address: '',
        cash_balance_usd: 0,
        nickname: '',
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

  const handleOpenAssetDialog = (accountId: number) => {
    setSelectedAccountForAsset(accountId);
    setAssetDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const payload = { ...formData, portfolio_id: formData.portfolio_id || undefined };
      if (editingAccount) {
        await api.put(`/crypto-accounts/${editingAccount.id}`, payload);
        notify.success('Crypto account updated successfully');
      } else {
        await api.post('/crypto-accounts/', payload);
        notify.success('Crypto account added successfully');
      }
      handleCloseDialog();
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save crypto account'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this crypto account? This will also delete all associated assets.')) return;

    try {
      await api.delete(`/crypto-accounts/${id}`);
      notify.success('Crypto account deleted successfully');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete crypto account'));
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
              <TableCell>Exchange/Wallets</TableCell>
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
                    <CompanyIcon
                      website={getExchange(account.exchange_name)?.website}
                      name={getExchangeLabel(account.exchange_name)}
                    />
                    {getExchangeLabel(account.exchange_name)}
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
              label="Exchange/Wallets"
              value={formData.exchange_name}
              onChange={(e) => setFormData({ ...formData, exchange_name: e.target.value })}
              fullWidth
            >
              {exchanges.map((exchange) => (
                <MenuItem key={exchange.name} value={exchange.name}>
                  {exchange.display_label}
                </MenuItem>
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

      {/* Shared Add Asset Dialog */}
      <CryptoAssetDialog
        open={assetDialogOpen}
        onClose={() => { setAssetDialogOpen(false); setSelectedAccountForAsset(undefined); }}
        onSaved={fetchData}
        fixedCryptoAccountId={selectedAccountForAsset}
      />
    </Box>
  );
};

export default CryptoAccounts;
