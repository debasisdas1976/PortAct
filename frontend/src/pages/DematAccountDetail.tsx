import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  KeyboardArrowDown as ExpandIcon,
  KeyboardArrowUp as CollapseIcon,
  Refresh as RefreshIcon,
  TrendingUp,
  TrendingDown,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import api, { brokersAPI, assetTypesAPI, transactionsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';
import StockTransactionDialog from '../components/StockTransactionDialog';

interface DematAccountInfo {
  id: number;
  broker_name: string;
  account_id: string;
  account_market: string;
  account_holder_name?: string;
  demat_account_number?: string;
  cash_balance: number;
  cash_balance_usd?: number;
  currency?: string;
  nickname?: string;
  is_active: boolean;
  asset_count: number;
  total_invested: number;
  current_value: number;
  total_profit_loss: number;
}

interface HoldingAsset {
  id: number;
  name: string;
  symbol?: string;
  isin?: string;
  asset_type: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  total_invested: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percentage: number;
  xirr?: number | null;
  is_active: boolean;
}

interface TradeTransaction {
  id: number;
  asset_id: number;
  asset_name: string;
  asset_type: string;
  transaction_type: string;
  transaction_date: string;
  quantity: number;
  price_per_unit: number;
  total_amount: number;
  fees: number;
  taxes: number;
  description?: string;
}

const txnTypeColor = (type: string): 'success' | 'error' | 'info' | 'primary' | 'warning' | 'default' => {
  const colors: Record<string, 'success' | 'error' | 'info' | 'primary' | 'warning' | 'default'> = {
    buy: 'success',
    sell: 'error',
    dividend: 'info',
    bonus: 'primary',
    split: 'warning',
    interest: 'info',
    deposit: 'success',
    withdrawal: 'error',
  };
  return colors[type] || 'default';
};

// Asset type grouping for tabs
const ASSET_TAB_CONFIG: { label: string; types: string[] }[] = [
  { label: 'Stocks', types: ['stock', 'us_stock', 'esop', 'rsu'] },
  { label: 'Equity MF', types: ['equity_mutual_fund'] },
  { label: 'Debt MF', types: ['debt_mutual_fund'] },
  { label: 'Hybrid MF', types: ['hybrid_mutual_fund'] },
  { label: 'Commodities', types: ['commodity', 'sovereign_gold_bond'] },
  { label: 'Others', types: ['reit', 'invit', 'corporate_bond'] },
];

const COL_COUNT = 13; // number of columns in the holdings table

/** A single asset row with an expandable trades sub-table */
const AssetRow: React.FC<{
  asset: HoldingAsset;
  trades: TradeTransaction[];
  formatCurrency: (n: number) => string;
  updatingAssetId: number | null;
  assetTypes: { value: string; label: string; allowedConversions: string[] | null }[];
  txnStatus: { status: string; icon: React.ReactNode; tooltip: string };
  onRefreshPrice: (asset: HoldingAsset) => void;
  onEdit: (asset: HoldingAsset) => void;
  onDelete: (asset: HoldingAsset) => void;
  onChangeType: (event: React.MouseEvent<HTMLElement>, asset: HoldingAsset) => void;
  onOpenTransactions: (asset: HoldingAsset) => void;
}> = ({ asset, trades, formatCurrency, updatingAssetId, assetTypes, txnStatus, onRefreshPrice, onEdit, onDelete, onChangeType, onOpenTransactions }) => {
  const [open, setOpen] = useState(false);
  const hasTrades = trades.length > 0;

  return (
    <>
      <TableRow
        hover
        sx={{ cursor: hasTrades ? 'pointer' : 'default', '& > *': { borderBottom: open ? 'unset' : undefined } }}
        onClick={() => hasTrades && setOpen(!open)}
      >
        <TableCell sx={{ width: 28, px: 0.5 }}>
          {hasTrades && (
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); setOpen(!open); }}>
              {open ? <CollapseIcon fontSize="small" /> : <ExpandIcon fontSize="small" />}
            </IconButton>
          )}
        </TableCell>
        <TableCell>{asset.name}</TableCell>
        <TableCell>{asset.symbol || '-'}</TableCell>
        <TableCell>
          {(() => {
            const typeData = assetTypes.find(t => t.value === asset.asset_type.toLowerCase());
            const hasConversions = !!typeData?.allowedConversions?.length;
            return (
              <Chip
                label={typeData?.label || asset.asset_type.replace(/_/g, ' ')}
                size="small"
                {...(hasConversions ? {
                  onClick: (e: React.MouseEvent<HTMLElement>) => { e.stopPropagation(); onChangeType(e, asset); },
                } : {})}
                sx={{
                  ...(hasConversions ? { cursor: 'pointer' } : {}),
                }}
              />
            );
          })()}
        </TableCell>
        <TableCell align="right">{asset.quantity}</TableCell>
        <TableCell align="right">{formatCurrency(asset.purchase_price)}</TableCell>
        <TableCell align="right">{formatCurrency(asset.current_price)}</TableCell>
        <TableCell align="right">{formatCurrency(asset.total_invested)}</TableCell>
        <TableCell align="right">{formatCurrency(asset.current_value)}</TableCell>
        <TableCell align="right">
          <Typography color={asset.profit_loss >= 0 ? 'success.main' : 'error.main'} variant="body2">
            {formatCurrency(asset.profit_loss)}
          </Typography>
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
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
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
            <Tooltip title={txnStatus.tooltip}>
              <IconButton
                size="small"
                onClick={(e) => { e.stopPropagation(); onOpenTransactions(asset); }}
              >
                {txnStatus.icon}
              </IconButton>
            </Tooltip>
          </Box>
        </TableCell>
        <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
          <IconButton
            size="small"
            color="info"
            title="Refresh Price"
            disabled={updatingAssetId === asset.id}
            onClick={(e) => { e.stopPropagation(); onRefreshPrice(asset); }}
          >
            {updatingAssetId === asset.id ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
          </IconButton>
          <IconButton
            size="small"
            color="primary"
            title="Edit"
            onClick={(e) => { e.stopPropagation(); onEdit(asset); }}
          >
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            color="error"
            title="Delete"
            onClick={(e) => { e.stopPropagation(); onDelete(asset); }}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </TableCell>
      </TableRow>

      {hasTrades && (
        <TableRow>
          <TableCell colSpan={COL_COUNT} sx={{ py: 0, px: 0 }}>
            <Collapse in={open} timeout="auto" unmountOnExit>
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
                    {trades.map((txn) => (
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
    </>
  );
};

const DematAccountDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { notify } = useNotification();

  const [account, setAccount] = useState<DematAccountInfo | null>(null);
  const [holdings, setHoldings] = useState<HoldingAsset[]>([]);
  const [transactions, setTransactions] = useState<TradeTransaction[]>([]);
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [brokerInfo, setBrokerInfo] = useState<{ label: string; website?: string } | null>(null);
  const [assetTypes, setAssetTypes] = useState<{ value: string; label: string; allowedConversions: string[] | null }[]>([]);

  // Upload dialog state
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statementType, setStatementType] = useState('tradebook_statement');
  const [uploading, setUploading] = useState(false);

  // Asset type change state
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<HoldingAsset | null>(null);

  // Asset action state
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);
  const [editingAsset, setEditingAsset] = useState<HoldingAsset | null>(null);
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: '', symbol: '', isin: '', quantity: 0, purchase_price: 0, current_price: 0,
  });

  // Transaction dialog state
  const [txDialogOpen, setTxDialogOpen] = useState(false);
  const [txDialogAsset, setTxDialogAsset] = useState<HoldingAsset | null>(null);
  const [transactionCounts, setTransactionCounts] = useState<Record<number, { count: number; buyQty: number; sellQty: number }>>({});

  const isUSBroker = account?.account_market === 'INTERNATIONAL';
  const statementTypes = isUSBroker
    ? [
        { value: 'broker_statement', label: 'Broker Statement' },
      ]
    : [
        { value: 'tradebook_statement', label: 'Tradebook Statement' },
        { value: 'broker_statement', label: 'Broker Statement' },
        { value: 'demat_statement', label: 'Demat Statement' },
        { value: 'mutual_fund_statement', label: 'Mutual Fund Statement' },
      ];

  // Group transactions by asset_id for quick lookup
  const tradesByAssetId = useMemo(() => {
    const map: Record<number, TradeTransaction[]> = {};
    for (const txn of transactions) {
      if (!map[txn.asset_id]) map[txn.asset_id] = [];
      map[txn.asset_id].push(txn);
    }
    // Sort each group by date descending
    for (const key of Object.keys(map)) {
      map[Number(key)].sort((a, b) =>
        new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime()
      );
    }
    return map;
  }, [transactions]);

  // Build tabs: only categories that have holdings
  const holdingTabs = useMemo(() =>
    ASSET_TAB_CONFIG
      .map((cfg) => {
        const items = holdings.filter((h) => cfg.types.includes(h.asset_type));
        return items.length > 0 ? { label: cfg.label, items } : null;
      })
      .filter(Boolean) as { label: string; items: HoldingAsset[] }[],
    [holdings]
  );

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  useEffect(() => {
    if (!id) return;
    fetchAccountDetail();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchAccountDetail = async () => {
    try {
      setLoading(true);
      const [accountRes, holdingsRes, transactionsRes, brokersData, assetTypesData] = await Promise.all([
        api.get(`/demat-accounts/${id}`),
        api.get('/assets/', { params: { demat_account_id: id, is_active: true } }),
        api.get(`/demat-accounts/${id}/transactions`),
        brokersAPI.getAll({ is_active: true }),
        assetTypesAPI.getAll({ is_active: true }),
      ]);

      setAccount(accountRes.data);
      const holdingsData = holdingsRes.data as HoldingAsset[];
      setHoldings(holdingsData);
      setTransactions(transactionsRes.data);

      // Fetch transaction summaries for all holdings in parallel
      const txSummary: Record<number, { count: number; buyQty: number; sellQty: number }> = {};
      const txPromises = holdingsData.map(async (asset: HoldingAsset) => {
        try {
          const txns = await transactionsAPI.getAll({ asset_id: asset.id, limit: 500 });
          const buyQty = txns
            .filter((t: any) => t.transaction_type === 'buy')
            .reduce((sum: number, t: any) => sum + (t.quantity || 0), 0);
          const sellQty = txns
            .filter((t: any) => t.transaction_type === 'sell')
            .reduce((sum: number, t: any) => sum + (t.quantity || 0), 0);
          txSummary[asset.id] = { count: txns.length, buyQty, sellQty };
        } catch {
          txSummary[asset.id] = { count: 0, buyQty: 0, sellQty: 0 };
        }
      });
      await Promise.all(txPromises);
      setTransactionCounts(txSummary);
      setAssetTypes(
        Array.isArray(assetTypesData)
          ? assetTypesData.map((t: any) => ({ value: t.name, label: t.display_label, allowedConversions: t.allowed_conversions ?? null }))
          : []
      );

      const brokers = Array.isArray(brokersData) ? brokersData : [];
      const broker = brokers.find((b: any) => b.name === accountRes.data.broker_name);
      if (broker) {
        setBrokerInfo({ label: broker.display_label, website: broker.website });
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load account details'));
    } finally {
      setLoading(false);
    }
  };

  const getTransactionStatus = (asset: HoldingAsset) => {
    const info = transactionCounts[asset.id];
    if (!info || info.count === 0) {
      return { status: 'none' as const, icon: <InfoIcon fontSize="small" color="info" />, tooltip: 'No transactions. Click to add.' };
    }
    const netQty = info.buyQty - info.sellQty;
    if (Math.abs(netQty - asset.quantity) < 0.0001) {
      return { status: 'match' as const, icon: <CheckCircleIcon fontSize="small" color="success" />, tooltip: 'Transactions match quantity' };
    }
    return { status: 'mismatch' as const, icon: <WarningIcon fontSize="small" color="warning" />, tooltip: `Mismatch: asset ${asset.quantity}, txns ${netQty.toFixed(4)}` };
  };

  const handleOpenTransactions = (asset: HoldingAsset) => {
    setTxDialogAsset(asset);
    setTxDialogOpen(true);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUploadStatement = async () => {
    if (!selectedFile || !id) {
      notify.error('Please select a file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('statement_type', statementType);
      formData.append('institution_name', account?.broker_name || '');
      formData.append('demat_account_id', id);

      const response = await api.post('/statements/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setOpenUploadDialog(false);
      setSelectedFile(null);
      setStatementType('tradebook_statement');
      notify.success(response.data?.message || 'Statement uploaded and processed successfully');
      fetchAccountDetail();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement'));
    } finally {
      setUploading(false);
    }
  };

  const handlePriceUpdate = async (asset: HoldingAsset) => {
    try {
      setUpdatingAssetId(asset.id);
      const response = await api.post(`/assets/${asset.id}/update-price`, {});
      await fetchAccountDetail();
      if (response.data?.price_update_failed) {
        notify.error(`Failed to update price for ${asset.symbol || asset.name}: ${response.data.price_update_error || 'Price source unavailable'}`);
      } else {
        notify.success(`Price updated for ${asset.symbol || asset.name}`);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to update price for ${asset.symbol || asset.name}`));
    } finally {
      setUpdatingAssetId(null);
    }
  };

  const handleOpenEditDialog = (asset: HoldingAsset) => {
    setEditingAsset(asset);
    setEditFormData({
      name: asset.name,
      symbol: asset.symbol || '',
      isin: asset.isin || '',
      quantity: asset.quantity,
      purchase_price: asset.purchase_price,
      current_price: asset.current_price,
    });
    setOpenEditDialog(true);
  };

  const handleEditSubmit = async () => {
    if (!editingAsset || !editFormData.name.trim()) {
      notify.error('Asset name is required');
      return;
    }
    try {
      setSubmitting(true);
      await api.put(`/assets/${editingAsset.id}`, {
        name: editFormData.name.trim(),
        symbol: editFormData.symbol.trim() || undefined,
        isin: editFormData.isin.trim() || undefined,
        quantity: editFormData.quantity,
        purchase_price: editFormData.purchase_price,
        total_invested: editFormData.quantity * editFormData.purchase_price,
        current_price: editFormData.current_price,
      });
      notify.success('Asset updated');
      setOpenEditDialog(false);
      setEditingAsset(null);
      fetchAccountDetail();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to update asset'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteAsset = async (asset: HoldingAsset) => {
    if (!window.confirm(`Delete ${asset.symbol || asset.name}?`)) return;
    try {
      await api.delete(`/assets/${asset.id}`);
      notify.success(`${asset.symbol || asset.name} deleted`);
      fetchAccountDetail();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete asset'));
    }
  };

  const handleAssetTypeClick = (event: React.MouseEvent<HTMLElement>, asset: HoldingAsset) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedAsset(asset);
  };

  const handleAssetTypeMenuClose = () => {
    setAnchorEl(null);
    setSelectedAsset(null);
  };

  const handleAssetTypeChange = async (newType: string) => {
    if (!selectedAsset) return;
    handleAssetTypeMenuClose();
    try {
      await api.put(`/assets/${selectedAsset.id}`, { asset_type: newType });
      const newLabel = assetTypes.find(t => t.value === newType)?.label || newType;
      notify.success(`Successfully reclassified ${selectedAsset.symbol || selectedAsset.name} as ${newLabel}`);
      fetchAccountDetail();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to update asset type'));
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!account) {
    return (
      <Box sx={{ p: 3 }}>
        <IconButton onClick={() => navigate('/demat-accounts')}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h6" sx={{ mt: 2 }}>Account not found</Typography>
      </Box>
    );
  }

  const brokerDisplayName = brokerInfo?.label || account.broker_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <IconButton onClick={() => navigate('/demat-accounts')}>
          <ArrowBackIcon />
        </IconButton>
        <CompanyIcon
          website={brokerInfo?.website}
          name={brokerDisplayName}
          size={40}
        />
        <Box>
          <Typography variant="h5">
            {brokerDisplayName} — {account.account_id}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {account.account_holder_name || 'No holder name'}
            {account.nickname ? ` (${account.nickname})` : ''}
            {account.demat_account_number ? ` | DP: ${account.demat_account_number}` : ''}
          </Typography>
        </Box>
        <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => {
              setStatementType(account?.account_market === 'INTERNATIONAL' ? 'broker_statement' : 'tradebook_statement');
              setOpenUploadDialog(true);
            }}
            size="small"
          >
            Upload Statement
          </Button>
          <Chip
            label={account.is_active ? 'Active' : 'Inactive'}
            color={account.is_active ? 'success' : 'default'}
            size="small"
          />
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Holdings</Typography>
              <Typography variant="h4">{holdings.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Current Value</Typography>
              <Typography variant="h4">{formatCurrency(account.current_value)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Total Invested</Typography>
              <Typography variant="h4">{formatCurrency(account.total_invested)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>P&L</Typography>
              <Typography
                variant="h4"
                color={account.total_profit_loss >= 0 ? 'success.main' : 'error.main'}
              >
                {formatCurrency(account.total_profit_loss)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Cash Balance</Typography>
              <Typography variant="h4">
                {account.account_market === 'INTERNATIONAL' && account.cash_balance_usd
                  ? `$${account.cash_balance_usd.toFixed(2)}`
                  : formatCurrency(account.cash_balance)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={tabValue >= holdingTabs.length ? 0 : tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          {holdingTabs.map((tab) => (
            <Tab key={tab.label} label={`${tab.label} (${tab.items.length})`} />
          ))}
        </Tabs>
      </Paper>

      {/* Tab Content — each tab is a holdings table with collapsible trades */}
      {holdingTabs.map((tab, idx) =>
        tabValue === idx ? (
          <TableContainer component={Paper} key={tab.label}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: 28, px: 0.5 }} />
                  <TableCell>Name</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Qty</TableCell>
                  <TableCell align="right">Avg Price</TableCell>
                  <TableCell align="right">Current Price</TableCell>
                  <TableCell align="right">Invested</TableCell>
                  <TableCell align="right">Current Value</TableCell>
                  <TableCell align="right">P&L</TableCell>
                  <TableCell align="right">P&L %</TableCell>
                  <TableCell align="right">XIRR</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tab.items.map((asset) => (
                  <AssetRow
                    key={asset.id}
                    asset={asset}
                    trades={tradesByAssetId[asset.id] || []}
                    formatCurrency={formatCurrency}
                    updatingAssetId={updatingAssetId}
                    assetTypes={assetTypes}
                    txnStatus={getTransactionStatus(asset)}
                    onRefreshPrice={handlePriceUpdate}
                    onEdit={handleOpenEditDialog}
                    onDelete={handleDeleteAsset}
                    onChangeType={handleAssetTypeClick}
                    onOpenTransactions={handleOpenTransactions}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : null
      )}

      {/* Upload Statement Dialog */}
      <Dialog open={openUploadDialog} onClose={() => setOpenUploadDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Demat/Trading Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Broker"
              value={brokerDisplayName}
              fullWidth
              disabled
            />

            <TextField
              select
              label="Statement Type"
              value={statementType}
              onChange={(e) => setStatementType(e.target.value)}
              fullWidth
              required
            >
              {statementTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </TextField>

            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
              fullWidth
            >
              {selectedFile ? selectedFile.name : 'Select File (.CSV / .XLSX / .XLS)'}
              <input
                type="file"
                hidden
                accept=".csv,.xlsx,.xls"
                onChange={handleFileSelect}
              />
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenUploadDialog(false)} disabled={uploading}>
            Cancel
          </Button>
          <Button
            onClick={handleUploadStatement}
            variant="contained"
            disabled={uploading || !selectedFile}
            startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Asset Dialog */}
      <Dialog open={openEditDialog} onClose={() => setOpenEditDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit {editingAsset?.symbol || editingAsset?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={editFormData.name}
              onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Symbol"
              value={editFormData.symbol}
              onChange={(e) => setEditFormData({ ...editFormData, symbol: e.target.value })}
              fullWidth
            />
            <TextField
              label="ISIN"
              value={editFormData.isin}
              onChange={(e) => setEditFormData({ ...editFormData, isin: e.target.value })}
              fullWidth
            />
            <TextField
              label="Quantity"
              type="number"
              value={editFormData.quantity}
              onChange={(e) => setEditFormData({ ...editFormData, quantity: parseFloat(e.target.value) || 0 })}
              fullWidth
            />
            <TextField
              label="Purchase Price"
              type="number"
              value={editFormData.purchase_price}
              onChange={(e) => setEditFormData({ ...editFormData, purchase_price: parseFloat(e.target.value) || 0 })}
              fullWidth
            />
            <TextField
              label="Current Price"
              type="number"
              value={editFormData.current_price}
              onChange={(e) => setEditFormData({ ...editFormData, current_price: parseFloat(e.target.value) || 0 })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenEditDialog(false)}>Cancel</Button>
          <Button
            onClick={handleEditSubmit}
            variant="contained"
            disabled={submitting || !editFormData.name.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : <EditIcon />}
          >
            {submitting ? 'Saving...' : 'Update'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Transaction Dialog */}
      <StockTransactionDialog
        open={txDialogOpen}
        onClose={() => { setTxDialogOpen(false); setTxDialogAsset(null); }}
        onTransactionsChanged={fetchAccountDetail}
        stock={txDialogAsset ? {
          id: txDialogAsset.id,
          name: txDialogAsset.name,
          symbol: txDialogAsset.symbol || txDialogAsset.name,
          quantity: txDialogAsset.quantity,
          current_price: txDialogAsset.current_price,
          current_value: txDialogAsset.current_value,
          xirr: txDialogAsset.xirr,
        } : null}
      />

      {/* Asset Type Change Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleAssetTypeMenuClose}
      >
        {assetTypes
          .filter((type) => {
            const currentType = selectedAsset?.asset_type.toLowerCase();
            if (!currentType) return false;
            const currentTypeData = assetTypes.find(t => t.value === currentType);
            return currentTypeData?.allowedConversions?.includes(type.value) ?? false;
          })
          .map((type) => (
            <MenuItem
              key={type.value}
              onClick={() => handleAssetTypeChange(type.value)}
            >
              {type.label}
            </MenuItem>
          ))}
      </Menu>
    </Box>
  );
};

export default DematAccountDetail;
