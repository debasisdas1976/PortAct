import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Collapse,
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
 Label as LabelIcon,
} from '@mui/icons-material';
import AssetAttributeTagDialog from '../components/AssetAttributeTagDialog';
import GenericAssetEditDialog from '../components/GenericAssetEditDialog';
import api, { transactionsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import XirrCard from '../components/XirrCard';
import DayChangeCard from '../components/DayChangeCard';
import StockTransactionDialog from '../components/StockTransactionDialog';

interface StockAsset {
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

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const Stocks: React.FC = () => {
  const [stocks, setStocks] = useState<StockAsset[]>([]);
  const [tagAssetId, setTagAssetId] = useState<number | null>(null);
  const [tagAssetName, setTagAssetName] = useState<string>('');
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();

  // Add/Edit dialog
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAsset, setEditingAsset] = useState<StockAsset | null>(null);
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [txDialogOpen, setTxDialogOpen] = useState(false);
  const [txDialogStock, setTxDialogStock] = useState<StockAsset | null>(null);
  const [stockTransactions, setStockTransactions] = useState<Record<number, any[]>>({});
  const [expandedStocks, setExpandedStocks] = useState<Set<number>>(new Set());

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
      const filtered = (assetsRes.data as StockAsset[]).filter(
        (a) => a.asset_type?.toLowerCase() === 'stock'
      );
      setStocks(filtered);

      // Fetch transactions for all stocks in parallel
      const txMap: Record<number, any[]> = {};
      const txPromises = filtered.map(async (stock) => {
        try {
          const txns = await transactionsAPI.getAll({ asset_id: stock.id, limit: 500 });
          txMap[stock.id] = txns;
        } catch {
          txMap[stock.id] = [];
        }
      });
      await Promise.all(txPromises);
      setStockTransactions(txMap);

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
  const handleOpenDialog = (asset?: StockAsset) => {
    setEditingAsset(asset || null);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => { setOpenDialog(false); setEditingAsset(null); };

  // ── Delete ──────────────────────────────────────────────────────────────
  const handleDelete = async (asset: StockAsset) => {
    if (!window.confirm(`Delete ${asset.symbol || asset.name}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      notify.success('Stock deleted');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete stock'));
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

  const getTransactionStatus = (stock: StockAsset) => {
    const txns = stockTransactions[stock.id];
    if (!txns || txns.length === 0) {
      return { status: 'none' as const, icon: <InfoIcon fontSize="small" color="info" />, tooltip: 'No transactions. Click to add.' };
    }
    const buyQty = txns.filter((t: any) => t.transaction_type === 'buy').reduce((s: number, t: any) => s + (t.quantity || 0), 0);
    const sellQty = txns.filter((t: any) => t.transaction_type === 'sell').reduce((s: number, t: any) => s + (t.quantity || 0), 0);
    const netQty = buyQty - sellQty;
    if (Math.abs(netQty - stock.quantity) < 0.0001) {
      return { status: 'match' as const, icon: <CheckCircleIcon fontSize="small" color="success" />, tooltip: 'Transactions match quantity' };
    }
    return { status: 'mismatch' as const, icon: <WarningIcon fontSize="small" color="warning" />, tooltip: `Mismatch: stock ${stock.quantity}, txns ${netQty.toFixed(4)}` };
  };

  const toggleStockExpand = (stockId: number) => {
    setExpandedStocks(prev => {
      const next = new Set(prev);
      if (next.has(stockId)) next.delete(stockId);
      else next.add(stockId);
      return next;
    });
  };

  const txnTypeColor = (type: string): 'success' | 'error' | 'info' | 'default' => {
    const colors: Record<string, 'success' | 'error' | 'info' | 'default'> = { buy: 'success', sell: 'error', dividend: 'info' };
    return colors[type] || 'default';
  };

  const totalInvested = stocks.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = stocks.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  // Group by demat_account_id
  const groups: Record<string, StockAsset[]> = {};
  for (const stock of stocks) {
    const key = stock.demat_account_id != null
      ? String(stock.demat_account_id)
      : ([stock.broker_name, stock.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(stock);
  }

  const groupLabel = (groupAssets: StockAsset[]) => {
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
        <Typography variant="h4">Indian Stocks</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add Stock
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3, alignItems: 'stretch' }}>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ flex: 1 }}><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{stocks.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ flex: 1 }}><CardContent>
            <Typography color="text.secondary" variant="body2">Current Value</Typography>
            <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ flex: 1 }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total Invested</Typography>
            <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ flex: 1 }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total P&L</Typography>
            <Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {formatCurrency(totalPnL)} ({totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%)
            </Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <DayChangeCard assets={stocks} />
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <XirrCard assetType="stock" portfolioId={selectedPortfolioId} />
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Stock</strong></TableCell>
              <TableCell align="right"><strong>Qty</strong></TableCell>
              <TableCell align="right"><strong>Avg Buy Price</strong></TableCell>
              <TableCell align="right"><strong>Current Price</strong></TableCell>
              <TableCell align="right"><strong>Invested</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
              <TableCell align="right"><strong>XIRR</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {stocks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary">No Indian stock holdings found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              Object.entries(groups).map(([key, groupStocks]) => {
                const gInvested = groupStocks.reduce((s, a) => s + (a.total_invested || 0), 0);
                const gValue = groupStocks.reduce((s, a) => s + (a.current_value || 0), 0);
                const gPnL = gValue - gInvested;
                return (
                  <React.Fragment key={key}>
                    <TableRow sx={{ bgcolor: 'action.hover', cursor: 'pointer' }} onClick={() => toggleGroup(key)}>
                      <TableCell colSpan={4}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          {collapsedGroups.has(key) ? <KeyboardArrowRight fontSize="small" /> : <KeyboardArrowDown fontSize="small" />}
                          <Box>
                            <Typography variant="subtitle2" fontWeight="bold">{groupLabel(groupStocks)}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {groupStocks.length} holding{groupStocks.length !== 1 ? 's' : ''}
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
                    {!collapsedGroups.has(key) && groupStocks.map((stock) => {
                      const trades = stockTransactions[stock.id] || [];
                      const hasTrades = trades.length > 0;
                      const isExpanded = expandedStocks.has(stock.id);
                      return (
                        <React.Fragment key={stock.id}>
                          <TableRow
                            hover
                            sx={{ cursor: hasTrades ? 'pointer' : 'default', '& > *': { borderBottom: isExpanded ? 'unset' : undefined } }}
                            onClick={() => hasTrades && toggleStockExpand(stock.id)}
                          >
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                {hasTrades && (
                                  isExpanded ? <KeyboardArrowUp fontSize="small" color="action" /> : <KeyboardArrowDown fontSize="small" color="action" />
                                )}
                                <Box>
                                  <Typography variant="body2" fontWeight="medium">{stock.symbol}</Typography>
                                  <Typography variant="caption" color="text.secondary">{stock.name}</Typography>
                                </Box>
                              </Box>
                            </TableCell>
                            <TableCell align="right">{stock.quantity?.toFixed(4)}</TableCell>
                            <TableCell align="right">{formatCurrency(stock.purchase_price)}</TableCell>
                            <TableCell align="right">{formatCurrency(stock.current_price)}</TableCell>
                            <TableCell align="right">{formatCurrency(stock.total_invested)}</TableCell>
                            <TableCell align="right">{formatCurrency(stock.current_value)}</TableCell>
                            <TableCell align="right" sx={{ color: stock.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>
                              {formatCurrency(stock.profit_loss)}
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${stock.profit_loss_percentage >= 0 ? '+' : ''}${stock.profit_loss_percentage?.toFixed(2)}%`}
                                color={stock.profit_loss_percentage >= 0 ? 'success' : 'error'}
                                size="small"
                                icon={stock.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />}
                              />
                            </TableCell>
                            <TableCell align="right">
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                                {stock.xirr != null ? (
                                  <Chip
                                    label={`${stock.xirr >= 0 ? '+' : ''}${stock.xirr.toFixed(2)}%`}
                                    color={stock.xirr >= 0 ? 'success' : 'error'}
                                    size="small"
                                    variant="outlined"
                                  />
                                ) : (
                                  <Typography variant="caption" color="text.secondary">N/A</Typography>
                                )}
                                <Tooltip title={getTransactionStatus(stock).tooltip}>
                                  <IconButton
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setTxDialogStock(stock);
                                      setTxDialogOpen(true);
                                    }}
                                  >
                                    {getTransactionStatus(stock).icon}
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            </TableCell>
                            <TableCell align="center">
                              <IconButton size="small" color="info" title="Refresh Price" onClick={(e) => { e.stopPropagation(); handlePriceUpdate(stock.id, stock.symbol || stock.name); }} disabled={updatingAssetId === stock.id}>
                                {updatingAssetId === stock.id ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
                              </IconButton>
                                                            <IconButton size="small" color="secondary" title="Attributes" onClick={(e) => { e.stopPropagation(); setTagAssetId(stock.id); setTagAssetName(stock.name); }}>
                                <LabelIcon fontSize="small" />
                              </IconButton>
<IconButton size="small" color="primary" title="Edit" onClick={(e) => { e.stopPropagation(); handleOpenDialog(stock); }}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="error" title="Delete" onClick={(e) => { e.stopPropagation(); handleDelete(stock); }}>
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
      <GenericAssetEditDialog
        open={openDialog}
        onClose={handleCloseDialog}
        onSaved={fetchData}
        asset={editingAsset}
        assetType="stock"
        dematAccounts={dematAccounts}
      />

      {/* ── Transaction Dialog ─────────────────────────────────────────────── */}
      <StockTransactionDialog
        open={txDialogOpen}
        onClose={() => { setTxDialogOpen(false); setTxDialogStock(null); }}
        onTransactionsChanged={fetchData}
        stock={txDialogStock}
      />
  
      <AssetAttributeTagDialog
        assetId={tagAssetId}
        assetName={tagAssetName}
        open={tagAssetId !== null}
        onClose={() => setTagAssetId(null)}
      />
    </Box>
  );
};

export default Stocks;

// Made with Bob
