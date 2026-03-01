import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  TrendingUp,
  TrendingDown,
  KeyboardArrowDown,
  KeyboardArrowRight,
} from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import api, { cryptoExchangesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { getErrorMessage } from '../utils/errorUtils';
import CryptoAssetDialog, { CryptoAccountOption, CryptoAssetForEdit } from '../components/CryptoAssetDialog';

interface CryptoAsset {
  id: number;
  name: string;
  symbol: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  total_invested: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percentage: number;
  xirr?: number | null;
  asset_type: string;
  crypto_account_id?: number;
  broker_name?: string;
  account_id?: string;
  account_holder_name?: string;
  details?: { coin_id?: string; currency?: string };
}

interface CryptoAccount {
  id: number;
  exchange_name: string;
  account_id: string;
  account_holder_name?: string;
  nickname?: string;
}

interface CryptoExchangeItem {
  id: number;
  name: string;
  display_label: string;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const buildCryptoLabel = (ca: CryptoAccount, exchangeMap: Record<string, string>) => {
  const exchangeLabel = exchangeMap[ca.exchange_name] || ca.exchange_name;
  const parts: string[] = [exchangeLabel, `(${ca.account_id})`];
  if (ca.account_holder_name) parts.push(`— ${ca.account_holder_name}`);
  return parts.join(' ');
};

const CryptoAssets: React.FC = () => {
  const [assets, setAssets] = useState<CryptoAsset[]>([]);
  const [cryptoLabelMap, setCryptoLabelMap] = useState<Record<number, string>>({});
  const [cryptoAccountOptions, setCryptoAccountOptions] = useState<CryptoAccountOption[]>([]);
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const [searchParams] = useSearchParams();
  const focusAccountId = searchParams.get('account');

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<CryptoAssetForEdit | null>(null);
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (key: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [assetsRes, cryptoRes, exchangesData] = await Promise.all([
        api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} }),
        api.get('/crypto-accounts/'),
        cryptoExchangesAPI.getAll(),
      ]);
      const filtered = (assetsRes.data as CryptoAsset[]).filter(
        (a) => a.asset_type?.toLowerCase() === 'crypto'
      );
      setAssets(filtered);

      // Build exchange name → display_label map
      const exchangeMap: Record<string, string> = {};
      for (const ex of exchangesData as CryptoExchangeItem[]) {
        exchangeMap[ex.name] = ex.display_label;
      }

      const cryptoList = cryptoRes.data as CryptoAccount[];
      const labelMap: Record<number, string> = {};
      const options: CryptoAccountOption[] = [];
      for (const ca of cryptoList) {
        const label = buildCryptoLabel(ca, exchangeMap);
        labelMap[ca.id] = label;
        options.push({ id: ca.id, label });
      }
      setCryptoLabelMap(labelMap);
      setCryptoAccountOptions(options);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [selectedPortfolioId]);

  // ── Add / Edit ──────────────────────────────────────────────────────────
  const handleOpenDialog = (asset?: CryptoAsset) => {
    if (asset) {
      setEditingAsset({
        id: asset.id,
        name: asset.name,
        symbol: asset.symbol,
        quantity: asset.quantity,
        purchase_price: asset.purchase_price,
        total_invested: asset.total_invested,
        current_price: asset.current_price,
        xirr: asset.xirr ?? null,
        crypto_account_id: asset.crypto_account_id,
        details: asset.details,
      });
    } else {
      setEditingAsset(null);
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingAsset(null);
  };

  // ── Delete ──────────────────────────────────────────────────────────────
  const handleDelete = async (asset: CryptoAsset) => {
    if (!window.confirm(`Delete ${asset.symbol || asset.name}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      notify.success('Crypto asset deleted');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete crypto asset'));
    }
  };

  const handlePriceUpdate = async (assetId: number, assetSymbol: string) => {
    try {
      setUpdatingAssetId(assetId);
      const response = await api.post(`/assets/${assetId}/update-price`, {});
      await fetchData();
      if (response.data?.price_update_failed) {
        notify.error(`Failed to update price for ${assetSymbol}: ${response.data.price_update_error || 'Price source unavailable'}`);
      } else {
        notify.success(`Price updated for ${assetSymbol}`);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to update price for ${assetSymbol}`));
    } finally {
      setUpdatingAssetId(null);
    }
  };

  const totalInvested = assets.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  // Group by crypto_account_id
  const groups: Record<string, CryptoAsset[]> = {};
  for (const asset of assets) {
    const key = asset.crypto_account_id != null
      ? String(asset.crypto_account_id)
      : ([asset.broker_name, asset.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(asset);
  }

  // When navigated from Crypto Accounts with ?account=<id>, collapse all groups except that one
  const groupKeys = Object.keys(groups);
  useEffect(() => {
    if (focusAccountId && groupKeys.length > 0) {
      setCollapsedGroups(new Set(groupKeys.filter(k => k !== focusAccountId)));
    }
  }, [focusAccountId, assets.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const groupLabel = (groupAssets: CryptoAsset[]) => {
    const first = groupAssets[0];
    if (first.crypto_account_id != null && cryptoLabelMap[first.crypto_account_id]) {
      return cryptoLabelMap[first.crypto_account_id];
    }
    const parts: string[] = [];
    if (first.broker_name) parts.push(first.broker_name);
    if (first.account_id) parts.push(`(${first.account_id})`);
    if (first.account_holder_name) parts.push(`— ${first.account_holder_name}`);
    return parts.length ? parts.join(' ') : 'Unlinked Holdings';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Crypto Assets</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add Crypto Asset
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{assets.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Current Value (₹)</Typography>
            <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total Invested (₹)</Typography>
            <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total P&L (₹)</Typography>
            <Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {formatCurrency(totalPnL)}
            </Typography>
            <Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%
            </Typography>
          </CardContent></Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Crypto</strong></TableCell>
              <TableCell align="right"><strong>Qty</strong></TableCell>
              <TableCell align="right"><strong>Avg Buy Price (₹)</strong></TableCell>
              <TableCell align="right"><strong>Current Price (₹)</strong></TableCell>
              <TableCell align="right"><strong>Invested (₹)</strong></TableCell>
              <TableCell align="right"><strong>Current Value (₹)</strong></TableCell>
              <TableCell align="right"><strong>P&L (₹)</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
              <TableCell align="right"><strong>XIRR</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary">No crypto holdings found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              Object.entries(groups).map(([key, groupAssets]) => {
                const gInvested = groupAssets.reduce((s, a) => s + (a.total_invested || 0), 0);
                const gValue = groupAssets.reduce((s, a) => s + (a.current_value || 0), 0);
                const gPnL = gValue - gInvested;
                return (
                  <React.Fragment key={key}>
                    <TableRow sx={{ bgcolor: 'action.hover', cursor: 'pointer' }} onClick={() => toggleGroup(key)}>
                      <TableCell colSpan={4}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          {collapsedGroups.has(key) ? <KeyboardArrowRight fontSize="small" /> : <KeyboardArrowDown fontSize="small" />}
                          <Box>
                            <Typography variant="subtitle2" fontWeight="bold">{groupLabel(groupAssets)}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {groupAssets.length} holding{groupAssets.length !== 1 ? 's' : ''}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">Invested</Typography>
                        <Typography variant="body2" fontWeight="medium">{formatCurrency(gInvested)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">Value</Typography>
                        <Typography variant="body2" fontWeight="medium">{formatCurrency(gValue)}</Typography>
                      </TableCell>
                      <TableCell align="right" colSpan={3}>
                        <Typography variant="caption" color="text.secondary">P&L</Typography>
                        <Typography variant="body2" fontWeight="medium" color={gPnL >= 0 ? 'success.main' : 'error.main'}>
                          {formatCurrency(gPnL)}
                        </Typography>
                      </TableCell>
                      <TableCell />
                    </TableRow>
                    {!collapsedGroups.has(key) && groupAssets.map((asset) => (
                      <TableRow key={asset.id} hover>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">{asset.symbol}</Typography>
                          <Typography variant="caption" color="text.secondary">{asset.name}</Typography>
                        </TableCell>
                        <TableCell align="right">{asset.quantity?.toFixed(6)}</TableCell>
                        <TableCell align="right">{formatCurrency(asset.purchase_price)}</TableCell>
                        <TableCell align="right">{formatCurrency(asset.current_price)}</TableCell>
                        <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                        <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                        <TableCell align="right" sx={{ color: asset.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>
                          {formatCurrency(asset.profit_loss)}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${asset.profit_loss_percentage >= 0 ? '+' : ''}${asset.profit_loss_percentage?.toFixed(2)}%`}
                            color={asset.profit_loss_percentage >= 0 ? 'success' : 'error'}
                            size="small"
                            icon={asset.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />}
                          />
                        </TableCell>
                        <TableCell align="right">
                          {asset.xirr != null ? (
                            <Chip
                              label={`${asset.xirr >= 0 ? '+' : ''}${asset.xirr.toFixed(2)}%`}
                              color={asset.xirr >= 0 ? 'success' : 'error'}
                              size="small"
                              variant="outlined"
                            />
                          ) : (
                            <Typography variant="caption" color="text.secondary">N/A</Typography>
                          )}
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small" color="info" title="Refresh Price" onClick={() => handlePriceUpdate(asset.id, asset.symbol || asset.name)} disabled={updatingAssetId === asset.id}>
                            {updatingAssetId === asset.id ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
                          </IconButton>
                          <IconButton size="small" color="primary" title="Edit" onClick={() => handleOpenDialog(asset)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(asset)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </React.Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <CryptoAssetDialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        onSaved={fetchData}
        editingAsset={editingAsset}
        cryptoAccounts={cryptoAccountOptions}
      />
    </Box>
  );
};

export default CryptoAssets;
