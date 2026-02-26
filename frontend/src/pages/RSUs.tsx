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
  CardGiftcard,
  KeyboardArrowDown,
  KeyboardArrowRight,
} from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface RSUAsset {
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
  demat_account_id?: number;
  broker_name?: string;
  account_id?: string;
  account_holder_name?: string;
  details?: {
    currency?: string;
    company_name?: string;
    grant_date?: string;
    vesting_date?: string;
    fmv_at_grant?: number;
    shares_granted?: number;
    shares_vested?: number;
    price_usd?: number;
    usd_to_inr_rate?: number;
  };
}

interface DematAccount {
  id: number;
  broker_name: string;
  account_id: string;
  account_holder_name?: string;
  nickname?: string;
}

const formatINR = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatUSD = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const RSUs: React.FC = () => {
  const [assets, setAssets] = useState<RSUAsset[]>([]);
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();

  const [openDialog, setOpenDialog] = useState(false);
  const [editingAsset, setEditingAsset] = useState<RSUAsset | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    symbol: '',
    currency: 'INR' as 'INR' | 'USD',
    company_name: '',
    grant_date: '',
    vesting_date: '',
    fmv_at_grant: 0,
    current_price: 0,
    shares_granted: 0,
    shares_vested: 0,
    demat_broker_name: '',
    demat_account_id_input: '',
    demat_account_holder: '',
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
      const [assetsRes, dematRes] = await Promise.all([
        api.get('/assets/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} }),
        api.get('/demat-accounts/'),
      ]);
      const filtered = (assetsRes.data as RSUAsset[]).filter(
        (a) => a.asset_type?.toLowerCase() === 'rsu'
      );
      setAssets(filtered);

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

  const handleOpenDialog = (asset?: RSUAsset) => {
    if (asset) {
      setEditingAsset(asset);
      const linkedDemat = asset.demat_account_id
        ? dematAccounts.find((da) => da.id === asset.demat_account_id)
        : null;
      setFormData({
        name: asset.name,
        symbol: asset.symbol || '',
        currency: (asset.details?.currency as 'INR' | 'USD') || 'INR',
        company_name: asset.details?.company_name || '',
        grant_date: asset.details?.grant_date || '',
        vesting_date: asset.details?.vesting_date || '',
        fmv_at_grant: asset.details?.fmv_at_grant || asset.purchase_price || 0,
        current_price: asset.details?.currency === 'USD' ? (asset.details?.price_usd || 0) : asset.current_price || 0,
        shares_granted: asset.details?.shares_granted || 0,
        shares_vested: asset.details?.shares_vested || asset.quantity || 0,
        demat_broker_name: linkedDemat?.broker_name || asset.broker_name || '',
        demat_account_id_input: linkedDemat?.account_id || asset.account_id || '',
        demat_account_holder: linkedDemat?.account_holder_name || asset.account_holder_name || '',
      });
    } else {
      setEditingAsset(null);
      setFormData({
        name: '', symbol: '', currency: 'INR', company_name: '',
        grant_date: '', vesting_date: '', fmv_at_grant: 0, current_price: 0,
        shares_granted: 0, shares_vested: 0,
        demat_broker_name: '', demat_account_id_input: '', demat_account_holder: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => { setOpenDialog(false); setEditingAsset(null); };

  const findOrCreateDematAccount = async (): Promise<number> => {
    const brokerName = formData.demat_broker_name.trim();
    const accountId = formData.demat_account_id_input.trim();

    // Check if a matching demat account already exists
    const existing = dematAccounts.find(
      (da) => da.broker_name.toLowerCase() === brokerName.toLowerCase() && da.account_id === accountId
    );
    if (existing) return existing.id;

    // Create a new demat account
    const dematPayload: Record<string, unknown> = {
      broker_name: brokerName,
      account_id: accountId,
      account_holder_name: formData.demat_account_holder.trim() || undefined,
      account_market: formData.currency === 'USD' ? 'international' : 'domestic',
      currency: formData.currency,
    };
    const res = await api.post('/demat-accounts/', dematPayload);
    return res.data.id;
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) { notify.error('Stock name is required'); return; }
    if (!formData.demat_broker_name.trim()) { notify.error('Broker name is required'); return; }
    if (!formData.demat_account_id_input.trim()) { notify.error('Account ID is required'); return; }
    try {
      setSubmitting(true);

      // Step 1: find or create the demat account
      const dematAccountId = await findOrCreateDematAccount();

      // Step 2: create/update the RSU asset
      const payload: Record<string, unknown> = {
        asset_type: 'rsu',
        name: formData.name.trim(),
        symbol: formData.symbol.trim() || undefined,
        quantity: formData.shares_vested,
        purchase_price: formData.fmv_at_grant,
        current_price: formData.current_price,
        total_invested: formData.shares_vested * formData.fmv_at_grant,
        demat_account_id: dematAccountId,
        details: {
          currency: formData.currency,
          company_name: formData.company_name.trim() || undefined,
          grant_date: formData.grant_date || undefined,
          vesting_date: formData.vesting_date || undefined,
          fmv_at_grant: formData.fmv_at_grant,
          shares_granted: formData.shares_granted,
          shares_vested: formData.shares_vested,
          ...(formData.currency === 'USD' ? { price_usd: formData.current_price } : {}),
        },
      };
      if (editingAsset) {
        await api.put(`/assets/${editingAsset.id}`, payload);
        notify.success('RSU updated');
      } else {
        await api.post('/assets/', payload);
        notify.success('RSU added');
      }
      handleCloseDialog();
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save RSU'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (asset: RSUAsset) => {
    if (!window.confirm(`Delete ${asset.symbol || asset.name}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      notify.success('RSU deleted');
      fetchData();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete RSU'));
    }
  };

  const totalInvested = assets.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = assets.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  const groups: Record<string, RSUAsset[]> = {};
  for (const asset of assets) {
    const key = asset.demat_account_id != null
      ? String(asset.demat_account_id)
      : ([asset.broker_name, asset.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(asset);
  }

  const groupLabel = (groupAssets: RSUAsset[]) => {
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

  const formatPrice = (value: number, currency?: string) =>
    currency === 'USD' ? formatUSD(value) : formatINR(value);

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
          <CardGiftcard color="primary" />
          <Typography variant="h4">RSUs</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add RSU
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Restricted Stock Units. Values shown in INR. Per-unit prices in native currency.
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Holdings</Typography>
            <Typography variant="h4">{assets.length}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Current Value (INR)</Typography>
            <Typography variant="h5">{formatINR(totalValue)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}><CardContent>
            <Typography color="text.secondary" variant="body2">Total Invested (INR)</Typography>
            <Typography variant="h5">{formatINR(totalInvested)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ display: 'flex' }}>
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
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Stock / Company</strong></TableCell>
              <TableCell align="center"><strong>Ccy</strong></TableCell>
              <TableCell align="right"><strong>Vested / Granted</strong></TableCell>
              <TableCell align="right"><strong>FMV at Grant</strong></TableCell>
              <TableCell align="right"><strong>Current Price</strong></TableCell>
              <TableCell align="right"><strong>Invested (INR)</strong></TableCell>
              <TableCell align="right"><strong>Value (INR)</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary">No RSU holdings found.</Typography>
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
                      <TableCell colSpan={5}>
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
                        <Typography variant="body2" fontWeight="medium">{formatINR(gInvested)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">Value</Typography>
                        <Typography variant="body2" fontWeight="medium">{formatINR(gValue)}</Typography>
                      </TableCell>
                      <TableCell align="right" colSpan={2}>
                        <Typography variant="caption" color="text.secondary">P&L</Typography>
                        <Typography variant="body2" fontWeight="medium" color={gPnL >= 0 ? 'success.main' : 'error.main'}>
                          {formatINR(gPnL)}
                        </Typography>
                      </TableCell>
                      <TableCell />
                    </TableRow>
                    {!collapsedGroups.has(key) && groupAssets.map((asset) => {
                      const ccy = asset.details?.currency || 'INR';
                      const fmv = asset.details?.fmv_at_grant || asset.purchase_price;
                      return (
                        <TableRow key={asset.id} hover>
                          <TableCell>
                            <Typography variant="body2" fontWeight="medium">{asset.symbol || asset.name}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {asset.details?.company_name || asset.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip label={ccy} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell align="right">
                            {asset.details?.shares_vested ?? asset.quantity} / {asset.details?.shares_granted ?? '—'}
                          </TableCell>
                          <TableCell align="right">
                            {formatPrice(fmv, ccy)}
                            {ccy === 'USD' && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                {formatINR(asset.purchase_price)}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {formatINR(asset.current_price)}
                            {ccy === 'USD' && asset.details?.price_usd && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                {formatUSD(asset.details.price_usd)}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">{formatINR(asset.total_invested)}</TableCell>
                          <TableCell align="right">{formatINR(asset.current_value)}</TableCell>
                          <TableCell align="right" sx={{ color: asset.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}>
                            {formatINR(asset.profit_loss)}
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
        <DialogTitle>{editingAsset ? 'Edit RSU' : 'Add RSU'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField label="Stock Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} fullWidth required />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label="Symbol (e.g. GOOGL)" value={formData.symbol} onChange={(e) => setFormData({ ...formData, symbol: e.target.value })} fullWidth />
              <TextField
                select label="Currency" value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value as 'INR' | 'USD' })}
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="INR">INR</MenuItem>
                <MenuItem value="USD">USD</MenuItem>
              </TextField>
            </Box>
            <TextField label="Company Name" value={formData.company_name} onChange={(e) => setFormData({ ...formData, company_name: e.target.value })} fullWidth helperText="Employer granting the RSU" />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label="Grant Date" type="date" value={formData.grant_date} onChange={(e) => setFormData({ ...formData, grant_date: e.target.value })} fullWidth InputLabelProps={{ shrink: true }} />
              <TextField label="Vesting Date" type="date" value={formData.vesting_date} onChange={(e) => setFormData({ ...formData, vesting_date: e.target.value })} fullWidth InputLabelProps={{ shrink: true }} />
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label="Shares Granted" type="number" value={formData.shares_granted} onChange={(e) => setFormData({ ...formData, shares_granted: parseFloat(e.target.value) || 0 })} fullWidth />
              <TextField label="Shares Vested" type="number" value={formData.shares_vested} onChange={(e) => setFormData({ ...formData, shares_vested: parseFloat(e.target.value) || 0 })} fullWidth />
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label={`FMV at Grant (${formData.currency})`} type="number" value={formData.fmv_at_grant} onChange={(e) => setFormData({ ...formData, fmv_at_grant: parseFloat(e.target.value) || 0 })} fullWidth helperText="Fair Market Value at grant date" />
              <TextField label={`Current Price (${formData.currency})`} type="number" value={formData.current_price} onChange={(e) => setFormData({ ...formData, current_price: parseFloat(e.target.value) || 0 })} fullWidth helperText="Update manually" />
            </Box>
            {/* ── Demat Account Information ─────────────────────────────────── */}
            <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1, mb: -1 }}>
              Demat Account Information
            </Typography>
            <TextField label="Broker Name" value={formData.demat_broker_name} onChange={(e) => setFormData({ ...formData, demat_broker_name: e.target.value })} fullWidth required helperText="e.g. Zerodha, Vested, INDmoney" />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label="Account ID / Client ID" value={formData.demat_account_id_input} onChange={(e) => setFormData({ ...formData, demat_account_id_input: e.target.value })} fullWidth required />
              <TextField label="Account Holder Name" value={formData.demat_account_holder} onChange={(e) => setFormData({ ...formData, demat_account_holder: e.target.value })} fullWidth />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={submitting || !formData.name.trim() || !formData.demat_broker_name.trim() || !formData.demat_account_id_input.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : editingAsset ? <EditIcon /> : <AddIcon />}>
            {submitting ? 'Saving…' : editingAsset ? 'Update' : 'Add RSU'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RSUs;

// Made with Bob
