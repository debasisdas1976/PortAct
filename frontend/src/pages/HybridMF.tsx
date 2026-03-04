import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Collapse,
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
  Tooltip,
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
  KeyboardArrowUp,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import api, { transactionsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import XirrCard from '../components/XirrCard';
import StockTransactionDialog from '../components/StockTransactionDialog';

interface MFAsset {
  id: number;
  name: string;
  symbol: string;
  isin?: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  total_invested: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percentage: number;
  xirr?: number | null;
  asset_type: string;
  demat_account_id?: number;
  broker_name?: string;
  account_id?: string;
  account_holder_name?: string;
}

interface DematAccount {
  id: number;
  broker_name: string;
  account_id: string;
  account_holder_name?: string;
  nickname?: string;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatNav = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 4 }).format(value);

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const HybridMF: React.FC = () => {
  const [funds, setFunds] = useState<MFAsset[]>([]);
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();

  // Add/Edit dialog
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAsset, setEditingAsset] = useState<MFAsset | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    symbol: '',
    isin: '',
    quantity: 0,
    purchase_price: 0,
    total_invested: 0,
    current_price: 0,
    xirr: null as number | null,
    demat_account_id: '' as number | '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [txDialogOpen, setTxDialogOpen] = useState(false);
  const [txDialogAsset, setTxDialogAsset] = useState<MFAsset | null>(null);
  const [assetTransactions, setAssetTransactions] = useState<Record<number, any[]>>({});
  const [expandedAssets, setExpandedAssets] = useState<Set<number>>(new Set());

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
      const [assetsRes, dematRes] = await Promise.all([
        api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} }),
        api.get('/demat-accounts/'),
      ]);
      const filtered = (assetsRes.data as MFAsset[]).filter(
        (a) => a.asset_type?.toLowerCase() === 'hybrid_mutual_fund'
      );
      setFunds(filtered);

      // Fetch transactions for all funds in parallel
      const txMap: Record<number, any[]> = {};
      const txPromises = filtered.map(async (fund) => {
        try {
          const txns = await transactionsAPI.getAll({ asset_id: fund.id, limit: 500 });
          txMap[fund.id] = txns;
        } catch {
          txMap[fund.id] = [];
        }
      });
      await Promise.all(txPromises);
      setAssetTransactions(txMap);

      const dematList = dematRes.data as DematAccount[];
      setDematAccounts(dematList);
      const labelMap: Record<number, string> = {};
      for (const da of dematList) {
        labelMap[da.id] = buildDematLabel(da);
      }
      setDematLabelMap(labelMap);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [selectedPortfolioId]);

  // ── Add / Edit ──────────────────────────────────────────────────────────
  const handleOpenDialog = (asset?: MFAsset) => {
    if (asset) {
      setEditingAsset(asset);
      setFormData({
        name: asset.name,
        symbol: asset.symbol || '',
        isin: asset.isin || '',
        quantity: asset.quantity,
        purchase_price: asset.purchase_price,
        total_invested: asset.total_invested,
        current_price: asset.current_price,
        xirr: asset.xirr ?? null,
        demat_account_id: asset.demat_account_id || '',
      });
    } else {
      setEditingAsset(null);
      setFormData({ name: '', symbol: '', isin: '', quantity: 0, purchase_price: 0, total_invested: 0, current_price: 0, xirr: null, demat_account_id: '' });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => { setOpenDialog(false); setEditingAsset(null); };

  const handleSubmit = async () => {
    if (!formData.name.trim()) { notify.error('Fund name is required'); return; }
    if (!formData.demat_account_id) { notify.error('Demat account is required'); return; }
    try {
      setSubmitting(true);
      const payload: Record<string, unknown> = {
        asset_type: 'hybrid_mutual_fund',
        name: formData.name.trim(),
        symbol: formData.symbol.trim() || undefined,
        isin: formData.isin.trim() || undefined,
        quantity: formData.quantity,
        purchase_price: formData.purchase_price,
        total_invested: formData.total_invested || formData.quantity * formData.purchase_price,
        current_price: formData.current_price,
        ...(formData.xirr != null ? { xirr: formData.xirr } : {}),
        demat_account_id: formData.demat_account_id,
      };
      if (editingAsset) {
        await api.put(`/assets/${editingAsset.id}`, payload);
        notify.success('Fund updated');
      } else {
        await api.post('/assets/', payload);
        notify.success('Fund added');
      }
      handleCloseDialog();
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save fund'));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Delete ──────────────────────────────────────────────────────────────
  const handleDelete = async (asset: MFAsset) => {
    if (!window.confirm(`Delete ${asset.name}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      notify.success('Fund deleted');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete fund'));
    }
  };

  const handlePriceUpdate = async (assetId: number, assetName: string) => {
    try {
      setUpdatingAssetId(assetId);
      const response = await api.post(`/assets/${assetId}/update-price`, {});
      await fetchData();
      if (response.data?.price_update_failed) {
        notify.error(`Failed to update price for ${assetName}: ${response.data.price_update_error || 'Price source unavailable'}`);
      } else {
        notify.success(`Price updated for ${assetName}`);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to update price for ${assetName}`));
    } finally {
      setUpdatingAssetId(null);
    }
  };

  const getTransactionStatus = (asset: MFAsset) => {
    const txns = assetTransactions[asset.id];
    if (!txns || txns.length === 0) {
      return { status: 'none' as const, icon: <InfoIcon fontSize="small" color="info" />, tooltip: 'No transactions. Click to add.' };
    }
    const buyQty = txns.filter((t: any) => t.transaction_type === 'buy').reduce((s: number, t: any) => s + (t.quantity || 0), 0);
    const sellQty = txns.filter((t: any) => t.transaction_type === 'sell').reduce((s: number, t: any) => s + (t.quantity || 0), 0);
    const netQty = buyQty - sellQty;
    if (Math.abs(netQty - asset.quantity) < 0.0001) {
      return { status: 'match' as const, icon: <CheckCircleIcon fontSize="small" color="success" />, tooltip: 'Transactions match quantity' };
    }
    return { status: 'mismatch' as const, icon: <WarningIcon fontSize="small" color="warning" />, tooltip: `Mismatch: asset ${asset.quantity}, txns ${netQty.toFixed(4)}` };
  };

  const toggleAssetExpand = (assetId: number) => {
    setExpandedAssets(prev => {
      const next = new Set(prev);
      if (next.has(assetId)) next.delete(assetId);
      else next.add(assetId);
      return next;
    });
  };

  const txnTypeColor = (type: string): 'success' | 'error' | 'info' | 'default' => {
    const colors: Record<string, 'success' | 'error' | 'info' | 'default'> = { buy: 'success', sell: 'error', dividend: 'info' };
    return colors[type] || 'default';
  };

  const totalInvested = funds.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = funds.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  const groups: Record<string, MFAsset[]> = {};
  for (const fund of funds) {
    const key = fund.demat_account_id != null
      ? String(fund.demat_account_id)
      : ([fund.broker_name, fund.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(fund);
  }

  const groupLabel = (groupAssets: MFAsset[]) => {
    const first = groupAssets[0];
    if (first.demat_account_id != null && dematLabelMap[first.demat_account_id]) {
      return dematLabelMap[first.demat_account_id];
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
        <Typography variant="h4">Hybrid Mutual Funds</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add Fund
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Funds</Typography>
            <Typography variant="h4">{funds.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Current Value</Typography>
            <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total Invested</Typography>
            <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total P&L</Typography>
            <Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {formatCurrency(totalPnL)}
            </Typography>
            <Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%
            </Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <XirrCard assetType="hybrid_mutual_fund" portfolioId={selectedPortfolioId} />
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Fund</strong></TableCell>
              <TableCell align="right"><strong>Units</strong></TableCell>
              <TableCell align="right"><strong>Avg NAV</strong></TableCell>
              <TableCell align="right"><strong>Current NAV</strong></TableCell>
              <TableCell align="right"><strong>Invested</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
              <TableCell align="right"><strong>XIRR</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {funds.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary">No hybrid mutual fund holdings found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              Object.entries(groups).map(([key, groupFunds]) => {
                const gInvested = groupFunds.reduce((s, a) => s + (a.total_invested || 0), 0);
                const gValue = groupFunds.reduce((s, a) => s + (a.current_value || 0), 0);
                const gPnL = gValue - gInvested;
                return (
                  <React.Fragment key={key}>
                    <TableRow sx={{ bgcolor: 'action.hover', cursor: 'pointer' }} onClick={() => toggleGroup(key)}>
                      <TableCell colSpan={4}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          {collapsedGroups.has(key) ? <KeyboardArrowRight fontSize="small" /> : <KeyboardArrowDown fontSize="small" />}
                          <Box>
                            <Typography variant="subtitle2" fontWeight="bold">{groupLabel(groupFunds)}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {groupFunds.length} fund{groupFunds.length !== 1 ? 's' : ''}
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
                    {!collapsedGroups.has(key) && groupFunds.map((fund) => {
                      const trades = assetTransactions[fund.id] || [];
                      const hasTrades = trades.length > 0;
                      const isExpanded = expandedAssets.has(fund.id);
                      return (
                        <React.Fragment key={fund.id}>
                          <TableRow
                            hover
                            sx={{ cursor: hasTrades ? 'pointer' : 'default', '& > *': { borderBottom: isExpanded ? 'unset' : undefined } }}
                            onClick={() => hasTrades && toggleAssetExpand(fund.id)}
                          >
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                {hasTrades && (
                                  isExpanded ? <KeyboardArrowUp fontSize="small" color="action" /> : <KeyboardArrowDown fontSize="small" color="action" />
                                )}
                                <Box>
                                  <Typography variant="body2" fontWeight="medium">{fund.name}</Typography>
                                  {fund.symbol && <Typography variant="caption" color="text.secondary">{fund.symbol}</Typography>}
                                </Box>
                              </Box>
                            </TableCell>
                            <TableCell align="right">{fund.quantity?.toFixed(4)}</TableCell>
                            <TableCell align="right">{formatNav(fund.purchase_price)}</TableCell>
                            <TableCell align="right">{formatNav(fund.current_price)}</TableCell>
                            <TableCell align="right">{formatCurrency(fund.total_invested)}</TableCell>
                            <TableCell align="right">{formatCurrency(fund.current_value)}</TableCell>
                            <TableCell align="right" sx={{ color: fund.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>
                              {formatCurrency(fund.profit_loss)}
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${fund.profit_loss_percentage >= 0 ? '+' : ''}${fund.profit_loss_percentage?.toFixed(2)}%`}
                                color={fund.profit_loss_percentage >= 0 ? 'success' : 'error'}
                                size="small"
                                icon={fund.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />}
                              />
                            </TableCell>
                            <TableCell align="right">
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                                {fund.xirr != null ? (
                                  <Chip
                                    label={`${fund.xirr >= 0 ? '+' : ''}${fund.xirr.toFixed(2)}%`}
                                    color={fund.xirr >= 0 ? 'success' : 'error'}
                                    size="small"
                                    variant="outlined"
                                  />
                                ) : (
                                  <Typography variant="caption" color="text.secondary">N/A</Typography>
                                )}
                                <Tooltip title={getTransactionStatus(fund).tooltip}>
                                  <IconButton
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setTxDialogAsset(fund);
                                      setTxDialogOpen(true);
                                    }}
                                  >
                                    {getTransactionStatus(fund).icon}
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            </TableCell>
                            <TableCell align="center">
                              <IconButton size="small" color="info" title="Refresh Price" onClick={(e) => { e.stopPropagation(); handlePriceUpdate(fund.id, fund.name); }} disabled={updatingAssetId === fund.id}>
                                {updatingAssetId === fund.id ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
                              </IconButton>
                              <IconButton size="small" color="primary" title="Edit" onClick={(e) => { e.stopPropagation(); handleOpenDialog(fund); }}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="error" title="Delete" onClick={(e) => { e.stopPropagation(); handleDelete(fund); }}>
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                          {hasTrades && (
                            <TableRow>
                              <TableCell colSpan={10} sx={{ py: 0, px: 0 }}>
                                <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                                  <Box sx={{ mx: 4, my: 1 }}>
                                    <Table size="small">
                                      <TableHead>
                                        <TableRow>
                                          <TableCell>Date</TableCell>
                                          <TableCell>Action</TableCell>
                                          <TableCell align="right">Qty</TableCell>
                                          <TableCell align="right">Price/Unit</TableCell>
                                          <TableCell align="right">Amount</TableCell>
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {trades
                                          .slice()
                                          .sort((a: any, b: any) => new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime())
                                          .map((txn: any) => (
                                            <TableRow key={txn.id}>
                                              <TableCell>{new Date(txn.transaction_date).toLocaleDateString('en-IN')}</TableCell>
                                              <TableCell>
                                                <Chip
                                                  label={txn.transaction_type.replace(/_/g, ' ').toUpperCase()}
                                                  color={txnTypeColor(txn.transaction_type)}
                                                  size="small"
                                                />
                                              </TableCell>
                                              <TableCell align="right">{txn.quantity}</TableCell>
                                              <TableCell align="right">{formatCurrency(txn.price_per_unit)}</TableCell>
                                              <TableCell align="right">{formatCurrency(txn.total_amount)}</TableCell>
                                            </TableRow>
                                          ))}
                                      </TableBody>
                                    </Table>
                                  </Box>
                                </Collapse>
                              </TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </React.Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ── Add / Edit Dialog ──────────────────────────────────────────────── */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingAsset ? 'Edit Hybrid Fund' : 'Add Hybrid Fund'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField label="Fund Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} fullWidth required />
            <TextField label="Symbol / AMFI Code" value={formData.symbol} onChange={(e) => setFormData({ ...formData, symbol: e.target.value })} fullWidth />
            <TextField label="ISIN" value={formData.isin} onChange={(e) => setFormData({ ...formData, isin: e.target.value })} fullWidth />
            <TextField label="Units" type="number" value={formData.quantity} onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })} fullWidth />
            <TextField label="Average NAV (Buy)" type="number" value={formData.purchase_price} onChange={(e) => setFormData({ ...formData, purchase_price: parseFloat(e.target.value) || 0 })} fullWidth />
            <TextField label="Total Invested" type="number" value={formData.total_invested} onChange={(e) => setFormData({ ...formData, total_invested: parseFloat(e.target.value) || 0 })} fullWidth helperText="Leave 0 to auto-calculate (Units x Avg NAV)" />
            <TextField label="Current NAV" type="number" value={formData.current_price} onChange={(e) => setFormData({ ...formData, current_price: parseFloat(e.target.value) || 0 })} fullWidth helperText="Will be auto-updated by price scheduler" />
            <TextField label="XIRR (%)" type="number" value={formData.xirr ?? ''} onChange={(e) => setFormData({ ...formData, xirr: e.target.value ? parseFloat(e.target.value) : null })} fullWidth helperText="Auto-calculated from transactions. Enter manually if needed." />
            <TextField
              select
              label="Demat Account"
              value={formData.demat_account_id}
              onChange={(e) => setFormData({ ...formData, demat_account_id: e.target.value ? Number(e.target.value) : '' })}
              fullWidth
              required
              helperText={<>Required. Don't have one? <RouterLink to="/demat-accounts" style={{ color: 'inherit' }}>Create a Demat Account</RouterLink></>}
            >
              {dematAccounts.map((da) => (
                <MenuItem key={da.id} value={da.id}>{buildDematLabel(da)}</MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={submitting || !formData.name.trim() || !formData.demat_account_id}
            startIcon={submitting ? <CircularProgress size={18} /> : editingAsset ? <EditIcon /> : <AddIcon />}>
            {submitting ? 'Saving…' : editingAsset ? 'Update' : 'Add Fund'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Transaction Dialog ─────────────────────────────────────────────── */}
      <StockTransactionDialog
        open={txDialogOpen}
        onClose={() => { setTxDialogOpen(false); setTxDialogAsset(null); }}
        onTransactionsChanged={fetchData}
        stock={txDialogAsset}
      />
    </Box>
  );
};

export default HybridMF;
