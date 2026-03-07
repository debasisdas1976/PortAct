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
 Language,
 KeyboardArrowDown,
 KeyboardArrowRight,
 Label as LabelIcon,
} from '@mui/icons-material';
import AssetAttributeTagDialog from '../components/AssetAttributeTagDialog';
import GenericAssetEditDialog from '../components/GenericAssetEditDialog';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import XirrCard from '../components/XirrCard';

interface USStockAsset {
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
  currency?: string;
  demat_account_id?: number;
  broker_name?: string;
  account_id?: string;
  account_holder_name?: string;
  details?: Record<string, any>;
}

interface DematAccount {
  id: number;
  broker_name: string;
  account_id: string;
  account_market?: string;
  account_holder_name?: string;
  nickname?: string;
}

const formatINR = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatUSD = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);

/**
 * Get USD value for a US stock field.
 * - Imported stocks have INR in main columns + USD in details (avg_cost_usd, price_usd).
 * - Manually-added stocks have USD directly in main columns with no details USD field.
 * If the details USD field exists, use it. If not AND avg_cost_usd is also absent
 * (i.e. stock was manually added with USD values), return the raw value as-is.
 * Only divide by rate when we know the main column is INR (avg_cost_usd exists).
 */
const toUSD = (value: number, details: Record<string, any> | undefined, usdField: string): number => {
  const d = details || {};
  if (d[usdField] != null) return d[usdField];
  // If avg_cost_usd exists, the data was imported → main columns are INR → divide by rate
  if (d.avg_cost_usd != null) {
    const rate = d.usd_to_inr_rate;
    if (rate && rate > 0) return value / rate;
  }
  // No avg_cost_usd means manually added → main columns are already USD
  return value;
};

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const USStocks: React.FC = () => {
  const [stocks, setStocks] = useState<USStockAsset[]>([]);
  const [tagAssetId, setTagAssetId] = useState<number | null>(null);
  const [tagAssetName, setTagAssetName] = useState<string>('');
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();

  // Add/Edit dialog
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAsset, setEditingAsset] = useState<USStockAsset | null>(null);
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
      const [assetsRes, dematRes] = await Promise.all([
        api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} }),
        api.get('/demat-accounts/'),
      ]);
      const filtered = (assetsRes.data as USStockAsset[]).filter(
        (a) => a.asset_type?.toLowerCase() === 'us_stock'
      );
      setStocks(filtered);

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
  const handleOpenDialog = (asset?: USStockAsset) => {
    setEditingAsset(asset || null);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => { setOpenDialog(false); setEditingAsset(null); };

  // ── Delete ──────────────────────────────────────────────────────────────
  const handleDelete = async (asset: USStockAsset) => {
    if (!window.confirm(`Delete ${asset.symbol || asset.name}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      notify.success('US stock deleted');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete US stock'));
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

  const totalInvested = stocks.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = stocks.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  const groups: Record<string, USStockAsset[]> = {};
  for (const stock of stocks) {
    const key = stock.demat_account_id != null
      ? String(stock.demat_account_id)
      : ([stock.broker_name, stock.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(stock);
  }

  const groupLabel = (groupAssets: USStockAsset[]) => {
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Language color="primary" />
          <Typography variant="h4">US Stocks</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add US Stock
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Values shown in INR equivalent. Individual prices in USD.
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{stocks.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Current Value (INR)</Typography>
            <Typography variant="h5">{formatINR(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total Invested (INR)</Typography>
            <Typography variant="h5">{formatINR(totalInvested)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total P&L</Typography>
            <Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {formatINR(totalPnL)}
            </Typography>
            <Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
              {totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%
            </Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}>
          <XirrCard assetType="us_stock" portfolioId={selectedPortfolioId} />
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Stock</strong></TableCell>
              <TableCell align="right"><strong>Qty</strong></TableCell>
              <TableCell align="right"><strong>Avg Buy (USD)</strong></TableCell>
              <TableCell align="right"><strong>Current (USD)</strong></TableCell>
              <TableCell align="right"><strong>Invested (INR)</strong></TableCell>
              <TableCell align="right"><strong>Current Value (INR)</strong></TableCell>
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
                  <Typography color="text.secondary">No US stock holdings found.</Typography>
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
                        <Typography variant="body2" fontWeight="medium">{formatINR(gInvested)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">Value</Typography>
                        <Typography variant="body2" fontWeight="medium">{formatINR(gValue)}</Typography>
                      </TableCell>
                      <TableCell align="right" colSpan={3}>
                        <Typography variant="caption" color="text.secondary">P&L</Typography>
                        <Typography variant="body2" fontWeight="medium" color={gPnL >= 0 ? 'success.main' : 'error.main'}>
                          {formatINR(gPnL)}
                        </Typography>
                      </TableCell>
                      <TableCell />
                    </TableRow>
                    {!collapsedGroups.has(key) && groupStocks.map((stock) => (
                      <TableRow key={stock.id} hover>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">{stock.symbol}</Typography>
                          <Typography variant="caption" color="text.secondary">{stock.name}</Typography>
                        </TableCell>
                        <TableCell align="right">{stock.quantity?.toFixed(6)}</TableCell>
                        <TableCell align="right">{formatUSD(toUSD(stock.purchase_price, stock.details, 'avg_cost_usd'))}</TableCell>
                        <TableCell align="right">{formatUSD(toUSD(stock.current_price, stock.details, 'price_usd'))}</TableCell>
                        <TableCell align="right">{formatINR(stock.total_invested)}</TableCell>
                        <TableCell align="right">{formatINR(stock.current_value)}</TableCell>
                        <TableCell align="right" sx={{ color: stock.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>
                          {formatINR(stock.profit_loss)}
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
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small" color="info" title="Refresh Price" onClick={() => handlePriceUpdate(stock.id, stock.symbol || stock.name)} disabled={updatingAssetId === stock.id}>
                            {updatingAssetId === stock.id ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
                          </IconButton>
                                                    <IconButton size="small" color="secondary" title="Attributes" onClick={(e) => { e.stopPropagation(); setTagAssetId(stock.id); setTagAssetName(stock.name); }}>
                            <LabelIcon fontSize="small" />
                          </IconButton>
<IconButton size="small" color="primary" title="Edit" onClick={() => handleOpenDialog(stock)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(stock)}>
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
      <GenericAssetEditDialog
        open={openDialog}
        onClose={handleCloseDialog}
        onSaved={fetchData}
        asset={editingAsset}
        assetType="us_stock"
        dematAccounts={dematAccounts}
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

export default USStocks;

// Made with Bob
