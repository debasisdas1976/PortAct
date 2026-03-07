import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Card, CardContent, CircularProgress, Grid, Paper, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, Button, IconButton, Chip,
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
  id: number;
  name: string;
  symbol: string;
  total_invested: number;
  current_value: number;
  asset_type: string;
  notes?: string;
  details?: Record<string, any>;
  xirr?: number | null;
}

const ASSET_TYPE = 'cash';
const PAGE_TITLE = 'Cash In Hand';

const CURRENCIES = [
  { code: 'INR', symbol: '\u20B9', name: 'Indian Rupee' },
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '\u20AC', name: 'Euro' },
  { code: 'GBP', symbol: '\u00A3', name: 'British Pound' },
  { code: 'AED', symbol: 'AED', name: 'UAE Dirham' },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar' },
  { code: 'JPY', symbol: '\u00A5', name: 'Japanese Yen' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc' },
];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatAmount = (amount: number, currencyCode: string) => {
  const curr = CURRENCIES.find(c => c.code === currencyCode);
  return `${curr?.symbol || currencyCode} ${amount.toLocaleString('en-IN')}`;
};

const CashInHand: React.FC = () => {
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
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  }, [selectedPortfolioId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);

  const handleAdd = () => { setEditingId(null); setDialogOpen(true); };
  const handleEdit = (asset: AssetItem) => { setEditingId(asset.id); setDialogOpen(true); };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await assetsAPI.delete(id);
      notify.success('Cash holding deleted successfully');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete'));
    }
  };

  if (loading) {
    return (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}><CircularProgress /></Box>);
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">{PAGE_TITLE}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleAdd}>Add</Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{assets.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Total Value (INR)</Typography>
            <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <Card><CardContent>
            <Typography color="text.secondary" variant="body2">Currencies</Typography>
            <Typography variant="h4">{new Set(assets.map(a => a.details?.currency || a.symbol)).size}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <XirrCard assetType={ASSET_TYPE} portfolioId={selectedPortfolioId} />
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Currency</strong></TableCell>
              <TableCell align="right"><strong>Amount</strong></TableCell>
              <TableCell align="right"><strong>INR Value</strong></TableCell>
              <TableCell align="right"><strong>XIRR</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow><TableCell colSpan={6} align="center"><Typography color="text.secondary">No cash holdings found. Click "Add" to create one.</Typography></TableCell></TableRow>
            ) : (
              assets.map((asset) => {
                const currency = asset.details?.currency || asset.symbol || 'INR';
                const originalAmount = asset.details?.original_amount ?? asset.current_value ?? 0;
                return (
                  <TableRow key={asset.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">{asset.name}</Typography>
                      {asset.notes && <Typography variant="caption" color="text.secondary">{asset.notes}</Typography>}
                    </TableCell>
                    <TableCell><Chip label={currency} size="small" variant="outlined" /></TableCell>
                    <TableCell align="right">{formatAmount(originalAmount, currency)}</TableCell>
                    <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
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
                );
              })
            )}
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

export default CashInHand;
