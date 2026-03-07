import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Button, IconButton,
} from '@mui/material';
import { Add, Edit, Delete, Label as LabelIcon, } from '@mui/icons-material';
import AssetAttributeTagDialog from '../components/AssetAttributeTagDialog';
import GenericAssetEditDialog from '../components/GenericAssetEditDialog';
import { assetsAPI } from '../services/api';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import XirrCard from '../components/XirrCard';

interface AssetItem {
  id: number; name: string; symbol: string; total_invested: number; current_value: number;
  asset_type: string; broker_name?: string; account_id?: string; notes?: string; details?: Record<string, any>;
  xirr?: number | null;
}

const ASSET_TYPE = 'kvp';
const PAGE_TITLE = 'Kisan Vikas Patra (KVP)';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const KVP: React.FC = () => {
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

  const handleAdd = () => { setEditingId(null); setDialogOpen(true); };
  const handleEdit = (asset: AssetItem) => { setEditingId(asset.id); setDialogOpen(true); };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try { await assetsAPI.delete(id); notify.success('Certificate deleted successfully'); fetchData(); }
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
        <Grid item xs={12} sm={6} md><Card><CardContent><Typography color="text.secondary" variant="body2">Certificates</Typography><Typography variant="h4">{assets.length}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md><Card><CardContent><Typography color="text.secondary" variant="body2">Total Invested</Typography><Typography variant="h5">{formatCurrency(totalInvested)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md><Card><CardContent><Typography color="text.secondary" variant="body2">Current Value</Typography><Typography variant="h5">{formatCurrency(totalValue)}</Typography></CardContent></Card></Grid>
        <Grid item xs={12} sm={6} md><XirrCard assetType={ASSET_TYPE} portfolioId={selectedPortfolioId} /></Grid>
      </Grid>
      <TableContainer component={Paper}>
        <Table>
          <TableHead><TableRow>
            <TableCell><strong>Name</strong></TableCell><TableCell><strong>Certificate No.</strong></TableCell>
            <TableCell align="right"><strong>Invested</strong></TableCell><TableCell align="right"><strong>Current Value</strong></TableCell>
            <TableCell align="right"><strong>Interest Rate</strong></TableCell><TableCell><strong>Maturity Date</strong></TableCell>
            <TableCell align="right"><strong>XIRR</strong></TableCell><TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow></TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={8} align="center"><Typography color="text.secondary">No holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : assets.map((asset) => (
              <TableRow key={asset.id} hover>
                <TableCell><Typography variant="body2" fontWeight="medium">{asset.name}</Typography>{asset.broker_name && <Typography variant="caption" color="text.secondary">{asset.broker_name}</Typography>}</TableCell>
                <TableCell>{asset.symbol || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
                <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
                <TableCell align="right">{asset.details?.interest_rate ? `${asset.details.interest_rate}%` : '-'}</TableCell>
                <TableCell>{asset.details?.maturity_date ? new Date(asset.details.maturity_date).toLocaleDateString('en-IN') : '-'}</TableCell>
                <TableCell align="right">
                  {asset.xirr != null ? (
                    <Typography variant="body2" color={asset.xirr >= 0 ? 'success.main' : 'error.main'}>
                      {asset.xirr >= 0 ? '+' : ''}{asset.xirr.toFixed(2)}%
                    </Typography>
                  ) : (
                    <Typography variant="caption" color="text.secondary">N/A</Typography>
                  )}
                </TableCell>
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

export default KVP;
