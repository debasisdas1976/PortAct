import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  TrendingUp,
  TrendingDown,
  KeyboardArrowDown,
  KeyboardArrowRight,
} from '@mui/icons-material';
import api, { cryptoExchangesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

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
  asset_type: string;
  crypto_account_id?: number;
  broker_name?: string;
  account_id?: string;
  account_holder_name?: string;
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
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);

const buildCryptoLabel = (ca: CryptoAccount, exchangeMap: Record<string, string>) => {
  const exchangeLabel = exchangeMap[ca.exchange_name] || ca.exchange_name;
  const parts: string[] = [exchangeLabel, `(${ca.account_id})`];
  if (ca.account_holder_name) parts.push(`— ${ca.account_holder_name}`);
  return parts.join(' ');
};

const CryptoAssets: React.FC = () => {
  const [assets, setAssets] = useState<CryptoAsset[]>([]);
  const [cryptoAccounts, setCryptoAccounts] = useState<CryptoAccount[]>([]);
  const [cryptoLabelMap, setCryptoLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();

  // Add/Edit dialog
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAsset, setEditingAsset] = useState<CryptoAsset | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    symbol: '',
    quantity: 0,
    purchase_price: 0,
    total_invested: 0,
    current_price: 0,
    crypto_account_id: '' as number | '',
  });
  const [submitting, setSubmitting] = useState(false);
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
        api.get('/assets/'),
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
      setCryptoAccounts(cryptoList);
      const labelMap: Record<number, string> = {};
      for (const ca of cryptoList) {
        labelMap[ca.id] = buildCryptoLabel(ca, exchangeMap);
      }
      setCryptoLabelMap(labelMap);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // ── Add / Edit ──────────────────────────────────────────────────────────
  const handleOpenDialog = (asset?: CryptoAsset) => {
    if (asset) {
      setEditingAsset(asset);
      setFormData({
        name: asset.name,
        symbol: asset.symbol || '',
        quantity: asset.quantity,
        purchase_price: asset.purchase_price,
        total_invested: asset.total_invested,
        current_price: asset.current_price,
        crypto_account_id: asset.crypto_account_id || '',
      });
    } else {
      setEditingAsset(null);
      setFormData({ name: '', symbol: '', quantity: 0, purchase_price: 0, total_invested: 0, current_price: 0, crypto_account_id: '' });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => { setOpenDialog(false); setEditingAsset(null); };

  const handleSubmit = async () => {
    if (!formData.name.trim()) { notify.error('Crypto name is required'); return; }
    try {
      setSubmitting(true);
      const payload: Record<string, unknown> = {
        asset_type: 'crypto',
        name: formData.name.trim(),
        symbol: formData.symbol.trim() || undefined,
        quantity: formData.quantity,
        purchase_price: formData.purchase_price,
        total_invested: formData.total_invested || formData.quantity * formData.purchase_price,
        current_price: formData.current_price,
        crypto_account_id: formData.crypto_account_id || undefined,
      };
      if (editingAsset) {
        await api.put(`/assets/${editingAsset.id}`, payload);
        notify.success('Crypto asset updated');
      } else {
        await api.post('/assets/', payload);
        notify.success('Crypto asset added');
      }
      handleCloseDialog();
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save crypto asset'));
    } finally {
      setSubmitting(false);
    }
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
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{assets.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Current Value (USD)</Typography>
            <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Total Invested (USD)</Typography>
            <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Total P&L (USD)</Typography>
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
              <TableCell align="right"><strong>Avg Buy Price (USD)</strong></TableCell>
              <TableCell align="right"><strong>Current Price (USD)</strong></TableCell>
              <TableCell align="right"><strong>Invested (USD)</strong></TableCell>
              <TableCell align="right"><strong>Current Value (USD)</strong></TableCell>
              <TableCell align="right"><strong>P&L (USD)</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center">
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
                      <TableCell align="right" colSpan={2}>
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
                        <TableCell align="center">
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

      {/* ── Add / Edit Dialog ──────────────────────────────────────────────── */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingAsset ? 'Edit Crypto Asset' : 'Add Crypto Asset'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField label="Crypto Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} fullWidth required />
            <TextField label="Symbol (e.g. BTC)" value={formData.symbol} onChange={(e) => setFormData({ ...formData, symbol: e.target.value })} fullWidth />
            <TextField label="Quantity" type="number" value={formData.quantity} onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })} fullWidth inputProps={{ step: '0.000001' }} />
            <TextField label="Average Buy Price (USD)" type="number" value={formData.purchase_price} onChange={(e) => setFormData({ ...formData, purchase_price: parseFloat(e.target.value) || 0 })} fullWidth />
            <TextField label="Total Invested (USD)" type="number" value={formData.total_invested} onChange={(e) => setFormData({ ...formData, total_invested: parseFloat(e.target.value) || 0 })} fullWidth helperText="Leave 0 to auto-calculate (Qty x Avg Price)" />
            <TextField label="Current Price (USD)" type="number" value={formData.current_price} onChange={(e) => setFormData({ ...formData, current_price: parseFloat(e.target.value) || 0 })} fullWidth helperText="Will be auto-updated by price scheduler" />
            <TextField
              select
              label="Crypto Account (Optional)"
              value={formData.crypto_account_id}
              onChange={(e) => setFormData({ ...formData, crypto_account_id: e.target.value ? Number(e.target.value) : '' })}
              fullWidth
            >
              <MenuItem value="">None</MenuItem>
              {cryptoAccounts.map((ca) => (
                <MenuItem key={ca.id} value={ca.id}>{cryptoLabelMap[ca.id] || `${ca.exchange_name} (${ca.account_id})`}</MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={submitting || !formData.name.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : editingAsset ? <EditIcon /> : <AddIcon />}>
            {submitting ? 'Saving…' : editingAsset ? 'Update' : 'Add Crypto Asset'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CryptoAssets;
