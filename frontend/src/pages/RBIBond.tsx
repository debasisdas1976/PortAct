import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Chip, Button, IconButton,
} from '@mui/material';
import { Add, Edit, Delete, TrendingUp, TrendingDown, Label as LabelIcon, } from '@mui/icons-material';
import AssetAttributeTagDialog from '../components/AssetAttributeTagDialog';
import GenericAssetEditDialog from '../components/GenericAssetEditDialog';
import { assetsAPI } from '../services/api';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import XirrCard from '../components/XirrCard';
import DayChangeCard from '../components/DayChangeCard';

interface AssetItem {
  id: number; name: string; symbol: string; isin?: string; quantity: number;
  purchase_price: number; current_price: number; total_invested: number; current_value: number;
  profit_loss: number; profit_loss_percentage: number; xirr?: number | null; asset_type: string;
  broker_name?: string; account_id?: string; notes?: string; details?: Record<string, any>;
}

const ASSET_TYPE = 'rbi_bond';
const PAGE_TITLE = 'RBI Bonds';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const RBIBond: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [tagAssetId, setTagAssetId] = useState<number | null>(null);
  const [tagAssetName, setTagAssetName] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setAssets((res.data as AssetItem[]).filter((a) => a.asset_type?.toLowerCase() === ASSET_TYPE));
    } catch (err) { notify.error(getErrorMessage(err, 'Failed to load data')); } finally { setLoading(false); }
  }, [notify, selectedPortfolioId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const totalInvested = assets.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  const handleAdd = () => { setEditingId(null); setDialogOpen(true); };
  const handleEdit = (asset: AssetItem) => { setEditingId(asset.id); setDialogOpen(true); };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try { await assetsAPI.delete(id); notify.success('Bond deleted successfully'); fetchData(); }
    catch (err) { notify.error(getErrorMessage(err, 'Failed to delete')); }
  };

  if (loading) return (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}><CircularProgress /></Box>);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{PAGE_TITLE}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleAdd}>Add</Button>
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
            <TableCell><strong>Bond</strong></TableCell><TableCell><strong>ISIN</strong></TableCell>
            <TableCell align="right"><strong>Qty</strong></TableCell><TableCell align="right"><strong>Invested</strong></TableCell>
            <TableCell align="right"><strong>Current Value</strong></TableCell><TableCell align="right"><strong>P&L</strong></TableCell>
            <TableCell align="right"><strong>XIRR</strong></TableCell>
            <TableCell align="right"><strong>Coupon Rate</strong></TableCell><TableCell><strong>Maturity</strong></TableCell>
            <TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow></TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={10} align="center"><Typography color="text.secondary">No holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : assets.map((asset) => (
              <TableRow key={asset.id} hover>
                <TableCell><Typography variant="body2" fontWeight="medium">{asset.name}</Typography>{asset.broker_name && <Typography variant="caption" color="text.secondary">{asset.broker_name}</Typography>}</TableCell>
                <TableCell>{asset.isin || asset.symbol || '-'}</TableCell>
                <TableCell align="right">{asset.quantity?.toFixed(2)}</TableCell>
                <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
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
                <TableCell align="right">{asset.details?.interest_rate ? `${asset.details.interest_rate}%` : '-'}</TableCell>
                <TableCell>{asset.details?.maturity_date ? new Date(asset.details.maturity_date).toLocaleDateString('en-IN') : '-'}</TableCell>
                <TableCell align="center">
                  <IconButton size="small" color="secondary" title="Attributes" onClick={() => { setTagAssetId(asset.id); setTagAssetName(asset.name); }}><LabelIcon fontSize="small" /></IconButton>
                  <IconButton size="small" color="primary" onClick={() => handleEdit(asset)} title="Edit"><Edit fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => handleDelete(asset.id, asset.name)} title="Delete"><Delete fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <GenericAssetEditDialog
        open={dialogOpen}
        onClose={() => { setDialogOpen(false); setEditingId(null); }}
        onSaved={fetchData}
        asset={editingId ? assets.find(a => a.id === editingId) || null : null}
        assetType={ASSET_TYPE}
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

export default RBIBond;
