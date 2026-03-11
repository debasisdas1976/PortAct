import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Chip, Button,
  IconButton,
} from '@mui/material';
import { Add, Edit, Delete, Refresh, TrendingUp, TrendingDown, Label as LabelIcon, } from '@mui/icons-material';
import AssetAttributeTagDialog from '../components/AssetAttributeTagDialog';
import GenericAssetEditDialog from '../components/GenericAssetEditDialog';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import XirrCard from '../components/XirrCard';
import DayChangeCard from '../components/DayChangeCard';

interface AssetItem {
  id: number; name: string; symbol: string; quantity: number; purchase_price: number;
  current_price: number; total_invested: number; current_value: number;
  profit_loss: number; profit_loss_percentage: number; xirr?: number | null; asset_type: string;
  demat_account_id?: number; broker_name?: string; account_id?: string;
  account_holder_name?: string; notes?: string;
}
interface DematAccount { id: number; broker_name: string; account_id: string; account_holder_name?: string; nickname?: string; }

const ASSET_TYPE = 'invit';
const PAGE_TITLE = 'InvITs';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const InvITs: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [tagAssetId, setTagAssetId] = useState<number | null>(null);
  const [tagAssetName, setTagAssetName] = useState<string>('');
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetItem | null>(null);
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [assetsRes, dematRes] = await Promise.all([api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} }), api.get('/demat-accounts/')]);
      setAssets((assetsRes.data as AssetItem[]).filter((a) => a.asset_type?.toLowerCase() === ASSET_TYPE));
      const dematList = dematRes.data as DematAccount[];
      setDematAccounts(dematList);
      const labelMap: Record<number, string> = {};
      for (const da of dematList) labelMap[da.id] = buildDematLabel(da);
      setDematLabelMap(labelMap);
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to load data')); } finally { setLoading(false); }
  }, [notify, selectedPortfolioId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const totalInvested = assets.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  const groups: Record<string, AssetItem[]> = {};
  for (const asset of assets) {
    const key = asset.demat_account_id != null ? String(asset.demat_account_id) : ([asset.broker_name, asset.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(asset);
  }
  const groupLabel = (ga: AssetItem[]) => {
    const f = ga[0];
    if (f.demat_account_id != null && dematLabelMap[f.demat_account_id]) return dematLabelMap[f.demat_account_id];
    const parts: string[] = [];
    if (f.broker_name) parts.push(f.broker_name);
    if (f.account_id) parts.push(`(${f.account_id})`);
    if (f.account_holder_name) parts.push(`— ${f.account_holder_name}`);
    return parts.length ? parts.join(' ') : 'Unlinked Holdings';
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

  const handleOpenDialog = (asset?: AssetItem) => {
    setEditingAsset(asset || null);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => { setDialogOpen(false); setEditingAsset(null); };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try { await api.delete(`/assets/${id}`); notify.success('InvIT deleted successfully'); fetchData(); }
    catch (err) { notify.error(getErrorMessage(err, 'Failed to delete')); }
  };

  if (loading) return (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}><CircularProgress /></Box>);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{PAGE_TITLE}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpenDialog()}>Add</Button>
      </Box>
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Holdings</Typography><Typography variant="h4">{assets.length}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Current Value</Typography><Typography variant="h5">{formatCurrency(totalValue)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Total Invested</Typography><Typography variant="h5">{formatCurrency(totalInvested)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}><Card sx={{ width: '100%' }}><CardContent><Typography color="text.secondary" variant="body2">Total P&L</Typography><Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>{formatCurrency(totalPnL)}</Typography><Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>{totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}><DayChangeCard assets={assets} /></Grid>
        <Grid item xs={12} sm={6} md sx={{ display: 'flex' }}><XirrCard assetType={ASSET_TYPE} portfolioId={selectedPortfolioId} /></Grid>
      </Grid>
      <TableContainer component={Paper}>
        <Table>
          <TableHead><TableRow>
            <TableCell><strong>InvIT</strong></TableCell><TableCell align="right"><strong>Qty</strong></TableCell>
            <TableCell align="right"><strong>Avg Buy</strong></TableCell><TableCell align="right"><strong>Current</strong></TableCell>
            <TableCell align="right"><strong>Invested</strong></TableCell><TableCell align="right"><strong>Value</strong></TableCell>
            <TableCell align="right"><strong>P&L</strong></TableCell><TableCell align="right"><strong>P&L %</strong></TableCell>
            <TableCell align="right"><strong>XIRR</strong></TableCell>
            <TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow></TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={10} align="center"><Typography color="text.secondary">No holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : Object.entries(groups).map(([key, ga]) => {
              const gI = ga.reduce((s, a) => s + (a.total_invested || 0), 0);
              const gV = ga.reduce((s, a) => s + (a.current_value || 0), 0);
              const gP = gV - gI;
              return (
                <React.Fragment key={key}>
                  <TableRow sx={{ bgcolor: 'action.hover' }}>
                    <TableCell colSpan={4}><Typography variant="subtitle2" fontWeight="bold">{groupLabel(ga)}</Typography><Typography variant="caption" color="text.secondary">{ga.length} holding{ga.length !== 1 ? 's' : ''}</Typography></TableCell>
                    <TableCell align="right"><Typography variant="caption" color="text.secondary">Invested</Typography><Typography variant="body2" fontWeight="medium">{formatCurrency(gI)}</Typography></TableCell>
                    <TableCell align="right"><Typography variant="caption" color="text.secondary">Value</Typography><Typography variant="body2" fontWeight="medium">{formatCurrency(gV)}</Typography></TableCell>
                    <TableCell align="right" colSpan={4}><Typography variant="caption" color="text.secondary">P&L</Typography><Typography variant="body2" fontWeight="medium" color={gP >= 0 ? 'success.main' : 'error.main'}>{formatCurrency(gP)}</Typography></TableCell>
                  </TableRow>
                  {ga.map((asset) => (
                    <TableRow key={asset.id} hover>
                      <TableCell><Typography variant="body2" fontWeight="medium">{asset.symbol || asset.name}</Typography><Typography variant="caption" color="text.secondary">{asset.name}</Typography></TableCell>
                      <TableCell align="right">{asset.quantity?.toFixed(4)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.purchase_price)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.current_price)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                      <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                      <TableCell align="right" sx={{ color: asset.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>{formatCurrency(asset.profit_loss)}</TableCell>
                      <TableCell align="right"><Chip label={`${asset.profit_loss_percentage >= 0 ? '+' : ''}${asset.profit_loss_percentage?.toFixed(2)}%`} color={asset.profit_loss_percentage >= 0 ? 'success' : 'error'} size="small" icon={asset.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />} /></TableCell>
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
                        <IconButton size="small" color="info" title="Refresh Price" onClick={() => handlePriceUpdate(asset.id, asset.symbol || asset.name)} disabled={updatingAssetId === asset.id}>{updatingAssetId === asset.id ? <CircularProgress size={16} /> : <Refresh fontSize="small" />}</IconButton>
                        <IconButton size="small" color="secondary" title="Attributes" onClick={() => { setTagAssetId(asset.id); setTagAssetName(asset.name); }}><LabelIcon fontSize="small" /></IconButton>
                        <IconButton size="small" color="primary" onClick={() => handleOpenDialog(asset)} title="Edit"><Edit fontSize="small" /></IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDelete(asset.id, asset.name)} title="Delete"><Delete fontSize="small" /></IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <GenericAssetEditDialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        onSaved={fetchData}
        asset={editingAsset}
        assetType="invit"
        dematAccounts={dematAccounts}
        portfolioId={selectedPortfolioId}
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

export default InvITs;
