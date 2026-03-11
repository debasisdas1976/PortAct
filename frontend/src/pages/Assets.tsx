import React, { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  Collapse,
  IconButton,
  Tabs,
  Tab,
  Menu,
  MenuItem,
  Button,
  Tooltip,
  TableSortLabel,
  Checkbox,
} from '@mui/material';
import { TrendingUp, TrendingDown, KeyboardArrowDown, KeyboardArrowUp, AccountBalance, Refresh, Warning, CheckCircle, CameraAlt, Error as ErrorIcon, HourglassEmpty, Edit as EditIcon, Delete as DeleteIcon, Label as LabelIcon, Close as CloseIcon } from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchAssets } from '../store/slices/assetsSlice';
import {
  setActiveSession,
  clearActiveSession,
  startPriceRefreshPolling,
  checkActivePriceRefresh,
} from '../store/slices/priceRefreshSlice';
import api, { assetsAPI, assetTypesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { useNavigate } from 'react-router-dom';
import { useAssetActions } from '../hooks/useAssetActions';
import GenericAssetEditDialog from '../components/GenericAssetEditDialog';
import AssetAttributeTagDialog from '../components/AssetAttributeTagDialog';
import CryptoAssetDialog, { type CryptoAccountOption } from '../components/CryptoAssetDialog';
import BulkAttributeAssignDialog from '../components/BulkAttributeAssignDialog';
import DayChangeCard from '../components/DayChangeCard';
import { clampXirr } from '../utils/xirrUtils';

const ASSET_TYPE_ROUTES: Record<string, string> = {
  stock: '/stocks',
  us_stock: '/us-stocks',
  equity_mutual_fund: '/equity-mf',
  hybrid_mutual_fund: '/hybrid-mf',
  debt_mutual_fund: '/debt-funds',
  commodity: '/commodities',
  sovereign_gold_bond: '/sovereign-gold-bonds',
  esop: '/esops',
  rsu: '/rsus',
  reit: '/reits',
  invit: '/invits',
  savings_account: '/savings',
  fixed_deposit: '/fixed-deposit',
  recurring_deposit: '/recurring-deposit',
  corporate_bond: '/corporate-bond',
  rbi_bond: '/rbi-bond',
  tax_saving_bond: '/tax-saving-bond',
  ppf: '/ppf',
  pf: '/pf',
  nps: '/nps',
  ssy: '/ssy',
  gratuity: '/gratuity',
  insurance_policy: '/insurance',
  crypto: '/crypto-assets',
  nsc: '/nsc',
  kvp: '/kvp',
  scss: '/scss',
  mis: '/mis',
  cash: '/cash-in-hand',
  pension: '/pension',
  land: '/land',
  farm_land: '/farm-land',
  house: '/house',
};

const getAssetRoute = (assetType: string): string | undefined => {
  return ASSET_TYPE_ROUTES[assetType];
};

interface Asset {
  id: number;
  symbol: string;
  name: string;
  asset_type: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  total_invested: number;
  current_value: number;
  account_id?: string;
  broker_name?: string;
  account_holder_name?: string;
  price_update_failed?: boolean;
  last_price_update?: string;
  price_update_error?: string;
  api_symbol?: string;
  isin?: string;
  xirr?: number | null;
  details?: Record<string, any>;
}

interface BankAccount {
  id: number;
  bank_name: string;
  account_type: string;
  account_number: string;
  nickname?: string;
  current_balance: number;
  credit_limit?: number;
  is_active: boolean;
}

interface DematAccount {
  id: number;
  broker_name: string;
  account_id: string;
  account_holder_name?: string;
  demat_account_number?: string;
  cash_balance: number;
  cash_balance_usd?: number;
  currency: string;
  nickname?: string;
  is_active: boolean;
}

interface GroupedAsset {
  groupKey: string;
  symbol: string;
  name: string;
  asset_type: string;
  totalQuantity: number;
  totalInvested: number;
  totalCurrentValue: number;
  xirr: number | null;
  dayChangePct: number | null;
  instances: Asset[];
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`asset-tabpanel-${index}`}
      aria-labelledby={`asset-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

// Asset types will be fetched dynamically from the AssetTypeMaster API

const Assets: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { assets, loading, error } = useSelector((state: RootState) => state.assets);
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const navigate = useNavigate();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [currentTab, setCurrentTab] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedAsset, setSelectedAsset] = useState<GroupedAsset | null>(null);
  const [updating, setUpdating] = useState(false);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankAccountsLoading, setBankAccountsLoading] = useState(false);
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematAccountsLoading, setDematAccountsLoading] = useState(false);
  const {
    activeSessionId: priceSessionId,
    lastProgress: priceProgress,
    polling: pricePolling,
  } = useSelector((state: RootState) => state.priceRefresh);
  const refreshingPrices = !!priceSessionId && (pricePolling || priceProgress?.status === 'running');
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [assetTypes, setAssetTypes] = useState<{ value: string; label: string; category: string; allowedConversions: string[] | null }[]>([]);
  const [sortColumn, setSortColumn] = useState<'asset' | 'type' | 'invested' | 'value' | 'dayChange' | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [cryptoAccounts, setCryptoAccounts] = useState<CryptoAccountOption[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<number>>(new Set());
  const [bulkAttrDialogOpen, setBulkAttrDialogOpen] = useState(false);

  // Asset action handlers (edit/delete/attributes)
  const {
    editDialogOpen, editingAsset, editingAssetType, openEditDialog, closeEditDialog,
    cryptoDialogOpen, cryptoEditingAsset, closeCryptoDialog,
    handleDelete,
    tagAssetId, tagAssetName, openAttributes, closeAttributes,
  } = useAssetActions({
    onRefresh: () => dispatch(fetchAssets(selectedPortfolioId)),
    navigate,
  });

  useEffect(() => {
    dispatch(fetchAssets(selectedPortfolioId));
    fetchBankAccounts();
    fetchDematAccounts();
    fetchAssetTypes();
    fetchCryptoAccounts();
    dispatch(checkActivePriceRefresh());
  }, [dispatch, selectedPortfolioId]);

  // Progressive refresh: update asset data periodically during bulk price refresh
  // so that summary cards (Total Value, Gain/Loss, Return, XIRR) update as prices come in
  const lastProgressiveRefreshRef = useRef<number>(0);
  useEffect(() => {
    if (!priceProgress || priceProgress.status !== 'running') return;
    const completedCount = (priceProgress.updated_assets || 0) + (priceProgress.failed_assets || 0);
    if (completedCount === 0) return;
    const now = Date.now();
    // Refresh assets every 6 seconds during bulk price update
    if (now - lastProgressiveRefreshRef.current >= 6000) {
      lastProgressiveRefreshRef.current = now;
      dispatch(fetchAssets(selectedPortfolioId));
    }
  }, [priceProgress]);

  // Handle price refresh completion
  useEffect(() => {
    if (!priceProgress) return undefined;
    const st = priceProgress.status;
    if (st === 'completed' || st === 'failed') {
      dispatch(fetchAssets(selectedPortfolioId));

      const { updated_assets, failed_assets, total_assets } = priceProgress;
      if (failed_assets > 0) {
        notify.success(`Prices updated: ${updated_assets}/${total_assets} succeeded, ${failed_assets} failed`);
      } else {
        notify.success(`All ${updated_assets} asset prices updated successfully!`);
      }

      // Clear session after short delay so user sees final icon states
      const timer = setTimeout(() => {
        dispatch(clearActiveSession());
      }, 3000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [priceProgress?.status]);

  const fetchAssetTypes = async () => {
    try {
      const data = await assetTypesAPI.getAll({ is_active: true });
      setAssetTypes(
        Array.isArray(data) ? data.map((t: any) => ({ value: t.name, label: t.display_label, category: t.category, allowedConversions: t.allowed_conversions ?? null })) : []
      );
    } catch {
      setAssetTypes([]);
    }
  };

  const handleRefreshPrices = async () => {
    try {
      const response = await api.post('/assets/update-all-prices', {});
      const { session_id, status: respStatus } = response.data;

      if (respStatus === 'already_running') {
        dispatch(setActiveSession(session_id));
        dispatch(startPriceRefreshPolling());
        return;
      }

      if (!session_id) {
        notify.info(response.data.message || 'No price-updatable assets found.');
        return;
      }

      dispatch(setActiveSession(session_id));
      dispatch(startPriceRefreshPolling());
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to refresh prices'));
    }
  };

  const handleTakeSnapshot = async () => {
    try {
      setSnapshotLoading(true);
      await api.post('/dashboard/take-snapshot', {});
      
      notify.success('Snapshot created successfully!');

      // Refresh assets after snapshot
      dispatch(fetchAssets(selectedPortfolioId));
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to take snapshot'));
    } finally {
      setSnapshotLoading(false);
    }
  };

  const fetchBankAccounts = async () => {
    try {
      setBankAccountsLoading(true);
      const response = await api.get('/bank-accounts/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setBankAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load bank accounts'));
    } finally {
      setBankAccountsLoading(false);
    }
  };

  const fetchDematAccounts = async () => {
    try {
      setDematAccountsLoading(true);
      const response = await api.get('/demat-accounts/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setDematAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load demat accounts'));
    } finally {
      setDematAccountsLoading(false);
    }
  };

  const fetchCryptoAccounts = async () => {
    try {
      const response = await api.get('/crypto-accounts/');
      setCryptoAccounts(
        (response.data || []).map((ca: any) => ({
          id: ca.id,
          label: `${ca.exchange_name || ca.wallet_name || 'Account'} (${ca.account_id || ca.id})`,
        }))
      );
    } catch {
      setCryptoAccounts([]);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getAssetTypeColor = (type: string): string => {
    const colors: { [key: string]: string } = {
      // Stocks — Blue
      stock: '#1976D2',
      esop: '#1976D2',
      rsu: '#1976D2',
      reit: '#1976D2',
      invit: '#1976D2',
      // US Stocks — Indigo
      us_stock: '#5C6BC0',
      // Equity Mutual Funds — Green
      equity_mutual_fund: '#2E7D32',
      // Debt Mutual Funds — Teal
      debt_mutual_fund: '#00838F',
      // Hybrid Mutual Funds — Purple
      hybrid_mutual_fund: '#7B1FA2',
      // Bonds — Brown
      corporate_bond: '#5D4037',
      rbi_bond: '#5D4037',
      tax_saving_bond: '#5D4037',
      // Banks / FD / RD — Deep Orange
      fixed_deposit: '#E65100',
      recurring_deposit: '#E65100',
      savings_account: '#E65100',
      // Post Office Saving Schemes — Amber
      nsc: '#F9A825',
      kvp: '#F9A825',
      scss: '#F9A825',
      mis: '#F9A825',
      // Retirement Plans — Dark Red
      ppf: '#C62828',
      pf: '#C62828',
      nps: '#C62828',
      ssy: '#C62828',
      gratuity: '#C62828',
      pension: '#C62828',
      // Commodities — Gold/Amber
      commodity: '#FF8F00',
      sovereign_gold_bond: '#FF8F00',
      // Crypto — Pink
      crypto: '#AD1457',
      // Real Estate — Blue Grey
      land: '#546E7A',
      farm_land: '#546E7A',
      house: '#546E7A',
      // Other
      insurance_policy: '#78909C',
      cash: '#78909C',
    };
    return colors[type.toLowerCase()] || '#9E9E9E';
  };

  const getAssetTypeLabel = (type: string) => {
    const assetType = assetTypes.find(t => t.value === type.toLowerCase());
    return assetType ? assetType.label : type;
  };

  // Group assets by symbol (assets without a symbol each form their own group)
  const groupedAssets: GroupedAsset[] = React.useMemo(() => {
    const groups = new Map<string, GroupedAsset>();

    assets.forEach((asset) => {
      // Use symbol when present; fall back to a per-asset unique key so that
      // account-based assets (PF, SSY, NPS, PPF without symbol, etc.) are
      // never collapsed into a single group.
      const key = asset.symbol ? asset.symbol : `__no_symbol_${asset.id}`;
      if (!groups.has(key)) {
        groups.set(key, {
          groupKey: key,
          symbol: asset.symbol,
          name: asset.name,
          asset_type: asset.asset_type,
          totalQuantity: 0,
          totalInvested: 0,
          totalCurrentValue: 0,
          xirr: null,
          dayChangePct: null,
          instances: [],
        });
      }

      const group = groups.get(key)!;
      group.totalQuantity += asset.quantity || 0;
      group.totalInvested += asset.total_invested || 0;
      group.totalCurrentValue += asset.current_value || 0;
      group.instances.push(asset);
    });

    // Compute investment-weighted average XIRR per group
    // Falls back to current_value as weight when total_invested is 0
    groups.forEach((group) => {
      let xirrWeightedSum = 0;
      let xirrWeightTotal = 0;
      group.instances.forEach((inst) => {
        const clamped = clampXirr(inst.xirr);
        if (clamped != null) {
          const weight = (inst.total_invested || 0) > 0
            ? inst.total_invested!
            : (inst.current_value || 0) > 0 ? inst.current_value! : 0;
          if (weight > 0) {
            xirrWeightedSum += clamped * weight;
            xirrWeightTotal += weight;
          }
        }
      });
      group.xirr = xirrWeightTotal > 0 ? xirrWeightedSum / xirrWeightTotal : null;

      // Compute value-weighted average day change % from instances
      let dayChangeWeightedSum = 0;
      let dayChangeWeightTotal = 0;
      group.instances.forEach((inst) => {
        const pct = inst.details?.day_change_pct;
        if (pct != null && inst.current_value > 0) {
          dayChangeWeightedSum += pct * inst.current_value;
          dayChangeWeightTotal += inst.current_value;
        }
      });
      group.dayChangePct = dayChangeWeightTotal > 0 ? dayChangeWeightedSum / dayChangeWeightTotal : null;
    });

    return Array.from(groups.values());
  }, [assets]);

  // Group assets by type, then apply sorting
  const assetsByType = React.useMemo(() => {
    const types: { [key: string]: GroupedAsset[] } = {
      all: [],
      stock: [],
      us_stock: [],
      equity_mutual_fund: [],
      hybrid_mutual_fund: [],
      debt_mutual_fund: [],
      commodity: [],
      crypto: [],
      cash: [],
      other: [],
    };

    groupedAssets.forEach((asset) => {
      const type = asset.asset_type.toLowerCase();
      if (types[type]) {
        types[type].push(asset);
      } else {
        types.other.push(asset);
      }
    });

    types.all = [...groupedAssets];

    if (sortColumn) {
      const dir = sortDirection === 'asc' ? 1 : -1;
      const compareFn = (a: GroupedAsset, b: GroupedAsset): number => {
        switch (sortColumn) {
          case 'asset':
            return dir * (a.symbol || a.name).localeCompare(b.symbol || b.name);
          case 'type': {
            const labelA = assetTypes.find(t => t.value === a.asset_type.toLowerCase())?.label || a.asset_type;
            const labelB = assetTypes.find(t => t.value === b.asset_type.toLowerCase())?.label || b.asset_type;
            return dir * labelA.localeCompare(labelB);
          }
          case 'invested':
            return dir * (a.totalInvested - b.totalInvested);
          case 'value':
            return dir * (a.totalCurrentValue - b.totalCurrentValue);
          case 'dayChange':
            return dir * ((a.dayChangePct ?? 0) - (b.dayChangePct ?? 0));
          default:
            return 0;
        }
      };
      for (const key of Object.keys(types)) {
        types[key] = [...types[key]].sort(compareFn);
      }
    }

    return types;
  }, [groupedAssets, sortColumn, sortDirection, assetTypes]);

  // Calculate summary statistics for current tab
  const getCurrentTabAssets = () => {
    const tabMap = ['all', 'stock', 'us_stock', 'equity_mutual_fund', 'hybrid_mutual_fund', 'debt_mutual_fund', 'commodity', 'crypto', 'cash', 'other', 'bank_accounts'];
    return tabMap[currentTab] === 'bank_accounts' ? [] : assetsByType[tabMap[currentTab]] || [];
  };

  const currentTabAssets = getCurrentTabAssets();
  
  // Calculate bank account totals
  const totalBankBalance = bankAccounts.reduce((sum, account) => sum + account.current_balance, 0);
  const totalDematCash = dematAccounts.reduce((sum, account) => sum + account.cash_balance, 0);

  // Calculate totals based on current tab
  let totalValue = currentTabAssets.reduce((sum, group) => sum + group.totalCurrentValue, 0);
  let totalInvested = currentTabAssets.reduce((sum, group) => sum + group.totalInvested, 0);

  // If on "All" tab (index 0), include bank accounts and demat cash in total value
  if (currentTab === 0) {
    totalValue += totalBankBalance + totalDematCash;
    totalInvested += totalBankBalance + totalDematCash; // No gain/loss on cash
  }

  // If on "Cash" tab (index 8), include bank accounts and demat cash
  if (currentTab === 8) {
    totalValue += totalBankBalance + totalDematCash;
    totalInvested += totalBankBalance + totalDematCash;
  }

  // If on "Bank Accounts" tab (index 10), show only bank account totals
  if (currentTab === 10) {
    totalValue = totalBankBalance;
    totalInvested = totalBankBalance;
  }
  
  const totalGainLoss = totalValue - totalInvested;
  const totalReturnPercentage = totalInvested > 0 ? (totalGainLoss / totalInvested) * 100 : 0;

  // Investment-weighted average XIRR for current tab
  // Falls back to current_value as weight when total_invested is 0
  const aggregateXirr = React.useMemo(() => {
    let xirrWeightedSum = 0;
    let xirrWeightTotal = 0;
    currentTabAssets.forEach((group) => {
      group.instances.forEach((inst) => {
        const clamped = clampXirr(inst.xirr);
        if (clamped != null) {
          const weight = (inst.total_invested || 0) > 0
            ? inst.total_invested!
            : (inst.current_value || 0) > 0 ? inst.current_value! : 0;
          if (weight > 0) {
            xirrWeightedSum += clamped * weight;
            xirrWeightTotal += weight;
          }
        }
      });
    });
    return xirrWeightTotal > 0 ? xirrWeightedSum / xirrWeightTotal : null;
  }, [currentTabAssets]);

  const toggleRow = (symbol: string) => {
    setExpandedRows((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(symbol)) {
        newSet.delete(symbol);
      } else {
        newSet.add(symbol);
      }
      return newSet;
    });
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleSort = (column: 'asset' | 'type' | 'invested' | 'value' | 'dayChange') => {
    if (sortColumn === column) {
      setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const handleAssetTypeClick = (event: React.MouseEvent<HTMLElement>, asset: GroupedAsset) => {
    setAnchorEl(event.currentTarget);
    setSelectedAsset(asset);
  };

  const handleAssetTypeMenuClose = () => {
    setAnchorEl(null);
    setSelectedAsset(null);
  };

  const handleAssetTypeChange = async (newType: string) => {
    if (!selectedAsset) return;

    setUpdating(true);
    handleAssetTypeMenuClose();

    try {
      // Update all instances of this asset
      const updatePromises = selectedAsset.instances.map(instance =>
        assetsAPI.update(instance.id, { asset_type: newType })
      );

      await Promise.all(updatePromises);

      // Refresh assets
      await dispatch(fetchAssets(selectedPortfolioId));

      notify.success(`Successfully reclassified ${selectedAsset.symbol} as ${getAssetTypeLabel(newType)}`);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to update asset type'));
    } finally {
      setUpdating(false);
    }
  };

  const handleManualPriceUpdate = async (assetId: number, assetSymbol: string) => {
    try {
      setUpdatingAssetId(assetId);
      const response = await api.post(`/assets/${assetId}/update-price`, {});

      await dispatch(fetchAssets(selectedPortfolioId));

      // Check if the price update actually succeeded by inspecting the response
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

  const renderCashHoldingsTable = () => (
    <Box>
      {/* Bank Accounts Section */}
      <Typography variant="h6" sx={{ px: 2, pt: 2, pb: 1 }}>
        Bank Accounts
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Bank Name</TableCell>
              <TableCell>Account Type</TableCell>
              <TableCell>Account Number</TableCell>
              <TableCell>Nickname</TableCell>
              <TableCell align="right">Balance</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {bankAccounts.filter(a => a.current_balance > 0).length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary" variant="body2">
                    No bank accounts with a balance found.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              bankAccounts.filter(a => a.current_balance > 0).map((account) => (
                <TableRow key={`bank-${account.id}`}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <AccountBalance fontSize="small" />
                      {account.bank_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {account.account_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </TableCell>
                  <TableCell>****{account.account_number.slice(-4)}</TableCell>
                  <TableCell>{account.nickname || '-'}</TableCell>
                  <TableCell align="right">{formatCurrency(account.current_balance)}</TableCell>
                  <TableCell>
                    <Chip
                      label={account.is_active ? 'Active' : 'Inactive'}
                      color={account.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
            {bankAccounts.filter(a => a.current_balance > 0).length > 0 && (
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell colSpan={4} sx={{ fontWeight: 'bold' }}>Total Bank Balance</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>{formatCurrency(totalBankBalance)}</TableCell>
                <TableCell />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Demat Account Cash Section */}
      <Typography variant="h6" sx={{ px: 2, pt: 3, pb: 1 }}>
        Demat Account Cash
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Broker</TableCell>
              <TableCell>Account ID</TableCell>
              <TableCell>Account Holder</TableCell>
              <TableCell>Nickname</TableCell>
              <TableCell align="right">Cash Balance</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dematAccounts.filter(a => a.cash_balance > 0).length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary" variant="body2">
                    No demat accounts with a cash balance found.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              dematAccounts.filter(a => a.cash_balance > 0).map((account) => (
                <TableRow key={`demat-${account.id}`}>
                  <TableCell>{account.broker_name}</TableCell>
                  <TableCell>{account.account_id}</TableCell>
                  <TableCell>{account.account_holder_name || '-'}</TableCell>
                  <TableCell>{account.nickname || '-'}</TableCell>
                  <TableCell align="right">{formatCurrency(account.cash_balance)}</TableCell>
                  <TableCell>
                    <Chip
                      label={account.is_active ? 'Active' : 'Inactive'}
                      color={account.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
            {dematAccounts.filter(a => a.cash_balance > 0).length > 0 && (
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell colSpan={4} sx={{ fontWeight: 'bold' }}>Total Demat Cash</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>{formatCurrency(totalDematCash)}</TableCell>
                <TableCell />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Cash Assets Section */}
      <Typography variant="h6" sx={{ px: 2, pt: 3, pb: 1 }}>
        Other Cash Assets
      </Typography>
      {renderAssetsTable(assetsByType.cash)}
    </Box>
  );

  const renderBankAccountsTable = () => (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Bank Name</TableCell>
            <TableCell>Account Type</TableCell>
            <TableCell>Account Number</TableCell>
            <TableCell>Nickname</TableCell>
            <TableCell align="right">Current Balance</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {bankAccounts.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} align="center">
                <Typography color="text.secondary">
                  No bank accounts found. Add a bank account to track your balances.
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            bankAccounts.map((account) => (
              <TableRow key={account.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AccountBalance />
                    {account.bank_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Box>
                </TableCell>
                <TableCell>
                  {account.account_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </TableCell>
                <TableCell>****{account.account_number.slice(-4)}</TableCell>
                <TableCell>{account.nickname || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(account.current_balance)}</TableCell>
                <TableCell>
                  <Chip
                    label={account.is_active ? 'Active' : 'Inactive'}
                    color={account.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );


  // ── Selection helpers ──────────────────────────────────────────────
  const getAllAssetIdsInTab = (groups: GroupedAsset[]): number[] =>
    groups.flatMap((g) => g.instances.map((i) => i.id));

  const toggleAssetSelection = (id: number) => {
    setSelectedAssetIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleGroupSelection = (group: GroupedAsset) => {
    setSelectedAssetIds((prev) => {
      const next = new Set(prev);
      const ids = group.instances.map((i) => i.id);
      const allSelected = ids.every((id) => next.has(id));
      if (allSelected) ids.forEach((id) => next.delete(id));
      else ids.forEach((id) => next.add(id));
      return next;
    });
  };

  const toggleSelectAll = (groups: GroupedAsset[]) => {
    const allIds = getAllAssetIdsInTab(groups);
    setSelectedAssetIds((prev) => {
      const allSelected = allIds.every((id) => prev.has(id));
      if (allSelected) {
        const next = new Set(prev);
        allIds.forEach((id) => next.delete(id));
        return next;
      }
      return new Set([...prev, ...allIds]);
    });
  };

  const renderAssetsTable = (assetsToRender: GroupedAsset[]) => {
    const allIds = getAllAssetIdsInTab(assetsToRender);
    const allSelected = allIds.length > 0 && allIds.every((id) => selectedAssetIds.has(id));
    const someSelected = allIds.some((id) => selectedAssetIds.has(id));

    return (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox" width="48px">
              <Checkbox
                size="small"
                checked={allSelected}
                indeterminate={someSelected && !allSelected}
                onChange={() => toggleSelectAll(assetsToRender)}
              />
            </TableCell>
            <TableCell width="40px" />
            <TableCell sortDirection={sortColumn === 'asset' ? sortDirection : false}>
              <TableSortLabel active={sortColumn === 'asset'} direction={sortColumn === 'asset' ? sortDirection : 'asc'} onClick={() => handleSort('asset')}>
                Asset
              </TableSortLabel>
            </TableCell>
            <TableCell sortDirection={sortColumn === 'type' ? sortDirection : false}>
              <TableSortLabel active={sortColumn === 'type'} direction={sortColumn === 'type' ? sortDirection : 'asc'} onClick={() => handleSort('type')}>
                Type
              </TableSortLabel>
            </TableCell>
            <TableCell align="right">Qty</TableCell>
            <TableCell align="right">Current Price</TableCell>
            <TableCell align="right" sortDirection={sortColumn === 'dayChange' ? sortDirection : false}>
              <TableSortLabel active={sortColumn === 'dayChange'} direction={sortColumn === 'dayChange' ? sortDirection : 'asc'} onClick={() => handleSort('dayChange')}>
                Day Change
              </TableSortLabel>
            </TableCell>
            <TableCell align="right" sortDirection={sortColumn === 'invested' ? sortDirection : false}>
              <TableSortLabel active={sortColumn === 'invested'} direction={sortColumn === 'invested' ? sortDirection : 'asc'} onClick={() => handleSort('invested')}>
                Invested
              </TableSortLabel>
            </TableCell>
            <TableCell align="right" sortDirection={sortColumn === 'value' ? sortDirection : false}>
              <TableSortLabel active={sortColumn === 'value'} direction={sortColumn === 'value' ? sortDirection : 'asc'} onClick={() => handleSort('value')}>
                Value
              </TableSortLabel>
            </TableCell>
            <TableCell align="right">P&L</TableCell>
            <TableCell align="right">XIRR</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {assetsToRender.length === 0 ? (
            <TableRow>
              <TableCell colSpan={12} align="center">
                <Typography color="text.secondary">
                  No assets found in this category. Upload a statement to add assets.
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            assetsToRender.map((group) => {
              const gainLoss = group.totalCurrentValue - group.totalInvested;
              const returnPercentage =
                group.totalInvested > 0
                  ? (gainLoss / group.totalInvested) * 100
                  : 0;
              const currentPrice = group.instances[0]?.current_price || 0;
              const isExpanded = expandedRows.has(group.symbol);
              const hasMultipleInstances = group.instances.length > 1;
              const assetType = group.asset_type.toLowerCase();
              const needsIsin = assetType === 'stock' || assetType === 'equity_mutual_fund' || assetType === 'hybrid_mutual_fund' || assetType === 'debt_mutual_fund';
              const missingIsin = needsIsin && !group.instances[0]?.isin;
              const assetCategory = assetTypes.find(t => t.value.toLowerCase() === assetType)?.category || '';
              const hideRefreshPrice = assetType === 'cash' || (['Other', 'Fixed Income', 'Govt. Schemes', 'Retirement Plans', 'Cash'].includes(assetCategory) && assetType !== 'debt_mutual_fund');

              return (
                <React.Fragment key={group.groupKey}>
                  {/* Main Row */}
                  <TableRow sx={{
                    '& > *': { borderBottom: hasMultipleInstances && isExpanded ? 'none' : undefined },
                    backgroundColor: missingIsin ? 'rgba(255, 0, 0, 0.05)' : 'inherit'
                  }}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        size="small"
                        checked={group.instances.every((i) => selectedAssetIds.has(i.id))}
                        indeterminate={group.instances.some((i) => selectedAssetIds.has(i.id)) && !group.instances.every((i) => selectedAssetIds.has(i.id))}
                        onChange={() => toggleGroupSelection(group)}
                      />
                    </TableCell>
                    <TableCell>
                      {hasMultipleInstances && (
                        <IconButton size="small" onClick={() => toggleRow(group.symbol)}>
                          {isExpanded ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
                        </IconButton>
                      )}
                    </TableCell>
                    {/* Asset: symbol + name combined */}
                    <TableCell>
                      <Box
                        sx={{
                          cursor: getAssetRoute(assetType) ? 'pointer' : 'default',
                          '&:hover': getAssetRoute(assetType) ? { '& .asset-symbol': { color: 'primary.main', textDecoration: 'underline' } } : {},
                        }}
                        onClick={() => {
                          const route = getAssetRoute(assetType);
                          if (route) navigate(route);
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Typography className="asset-symbol" variant="body2" fontWeight="medium">
                            {group.symbol}
                          </Typography>
                          {missingIsin && (
                            <Warning color="error" fontSize="small" titleAccess="ISIN Missing" />
                          )}
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {group.name}
                          {hasMultipleInstances && ` · ${group.instances.length} accounts`}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getAssetTypeLabel(group.asset_type)}
                        size="small"
                        {...(assetTypes.find(t => t.value === group.asset_type.toLowerCase())?.allowedConversions?.length ? {
                          onClick: (e: React.MouseEvent<HTMLElement>) => handleAssetTypeClick(e, group),
                        } : {})}
                        sx={{
                          minWidth: 150,
                          justifyContent: 'center',
                          backgroundColor: getAssetTypeColor(group.asset_type),
                          color: '#fff',
                          ...(assetTypes.find(t => t.value === group.asset_type.toLowerCase())?.allowedConversions?.length ? { cursor: 'pointer' } : {}),
                        }}
                      />
                    </TableCell>
                    <TableCell align="right">{group.totalQuantity.toFixed(2)}</TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                        {formatCurrency(currentPrice)}
                        {!hideRefreshPrice && (() => {
                          // Check if a price refresh session is active and find this asset's progress
                          const progressItem = priceProgress?.status === 'running' || (priceProgress && priceSessionId)
                            ? priceProgress.assets?.find((ap: any) =>
                                group.instances.some((inst: any) => inst.id === ap.asset_id)
                              )
                            : null;

                          if (progressItem) {
                            if (progressItem.status === 'pending') {
                              return (
                                <Tooltip title="Waiting for price update..." arrow>
                                  <HourglassEmpty fontSize="small" sx={{ opacity: 0.5, color: 'warning.main' }} />
                                </Tooltip>
                              );
                            }
                            if (progressItem.status === 'processing') {
                              return <CircularProgress size={16} />;
                            }
                            if (progressItem.status === 'error') {
                              return (
                                <Tooltip title={progressItem.error_message || "Price update failed"} arrow>
                                  <ErrorIcon fontSize="small" color="error" />
                                </Tooltip>
                              );
                            }
                            if (progressItem.status === 'completed') {
                              return (
                                <Tooltip title="Price updated just now" arrow>
                                  <CheckCircle fontSize="small" color="success" />
                                </Tooltip>
                              );
                            }
                          }

                          // Default: use DB-persisted state
                          if (group.instances.some(i => i.price_update_failed)) {
                            return (
                              <Tooltip title={group.instances.find(i => i.price_update_failed)?.price_update_error || "Price update failed"} arrow>
                                <ErrorIcon fontSize="small" color="error" />
                              </Tooltip>
                            );
                          }
                          if (group.instances.some(i => i.last_price_update)) {
                            return (
                              <Tooltip title={`Last updated: ${new Date(group.instances[0].last_price_update!).toLocaleString()}`} arrow>
                                <CheckCircle fontSize="small" color="success" sx={{ opacity: 0.6 }} />
                              </Tooltip>
                            );
                          }
                          return (
                            <Tooltip title="Price never updated - click refresh to update" arrow>
                              <Warning fontSize="small" sx={{ opacity: 0.4, color: 'grey.500' }} />
                            </Tooltip>
                          );
                        })()}
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      {group.dayChangePct != null ? (
                        <Typography
                          variant="body2"
                          sx={{
                            color: group.dayChangePct >= 0 ? 'success.main' : 'error.main',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'flex-end',
                            gap: 0.3,
                          }}
                        >
                          {group.dayChangePct >= 0 ? <TrendingUp fontSize="small" /> : <TrendingDown fontSize="small" />}
                          {formatPercentage(group.dayChangePct)}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">—</Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">{formatCurrency(group.totalInvested)}</TableCell>
                    <TableCell align="right">{formatCurrency(group.totalCurrentValue)}</TableCell>
                    {/* P&L: amount + % combined */}
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ color: gainLoss >= 0 ? 'success.main' : 'error.main' }}>
                        {formatCurrency(gainLoss)}
                      </Typography>
                      <Typography variant="caption" sx={{ color: returnPercentage >= 0 ? 'success.main' : 'error.main' }}>
                        {formatPercentage(returnPercentage)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {group.xirr != null ? (
                        <Typography
                          variant="body2"
                          sx={{ color: group.xirr >= 0 ? 'success.main' : 'error.main' }}
                        >
                          {formatPercentage(group.xirr)}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">—</Typography>
                      )}
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', flexWrap: 'nowrap' }}>
                        {!hasMultipleInstances && !hideRefreshPrice && (
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleManualPriceUpdate(group.instances[0].id, group.symbol)}
                            disabled={updatingAssetId === group.instances[0].id}
                            title="Update price"
                          >
                            {updatingAssetId === group.instances[0].id ? (
                              <CircularProgress size={16} />
                            ) : (
                              <Refresh fontSize="small" />
                            )}
                          </IconButton>
                        )}
                        {!hasMultipleInstances && (
                          <>
                            <IconButton size="small" color="secondary" title="Attributes" onClick={() => openAttributes(group.instances[0].id, group.instances[0].name)}>
                              <LabelIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" color="primary" title="Edit" onClick={() => openEditDialog(group.instances[0])}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(group.instances[0])}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </>
                        )}
                        {hasMultipleInstances && (
                          <Typography variant="caption" color="text.secondary">Expand</Typography>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Rows - Show individual instances */}
                  {hasMultipleInstances && (
                    <TableRow>
                      <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={12}>
                        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                          <Box sx={{ margin: 2 }}>
                            <Typography variant="h6" gutterBottom component="div">
                              Account Details
                            </Typography>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell padding="checkbox" />
                                  <TableCell>Account ID</TableCell>
                                  <TableCell>Broker</TableCell>
                                  <TableCell>Account Holder</TableCell>
                                  <TableCell align="right">Quantity</TableCell>
                                  <TableCell align="right">Avg Price</TableCell>
                                  <TableCell align="right">Invested</TableCell>
                                  <TableCell align="right">Current Value</TableCell>
                                  <TableCell align="right">Gain/Loss</TableCell>
                                  <TableCell align="center">Actions</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {group.instances.map((instance) => {
                                  const instanceGainLoss = (instance.current_value || 0) - (instance.total_invested || 0);
                                  return (
                                    <TableRow key={instance.id}>
                                      <TableCell padding="checkbox">
                                        <Checkbox
                                          size="small"
                                          checked={selectedAssetIds.has(instance.id)}
                                          onChange={() => toggleAssetSelection(instance.id)}
                                        />
                                      </TableCell>
                                      <TableCell>
                                        {instance.account_id || 'N/A'}
                                      </TableCell>
                                      <TableCell>
                                        {instance.broker_name || 'N/A'}
                                      </TableCell>
                                      <TableCell>
                                        {instance.account_holder_name || 'N/A'}
                                      </TableCell>
                                      <TableCell align="right">
                                        {instance.quantity?.toFixed(2)}
                                      </TableCell>
                                      <TableCell align="right">
                                        {formatCurrency(instance.purchase_price || 0)}
                                      </TableCell>
                                      <TableCell align="right">
                                        {formatCurrency(instance.total_invested || 0)}
                                      </TableCell>
                                      <TableCell align="right">
                                        {formatCurrency(instance.current_value || 0)}
                                      </TableCell>
                                      <TableCell
                                        align="right"
                                        sx={{ color: instanceGainLoss >= 0 ? 'success.main' : 'error.main' }}
                                      >
                                        {formatCurrency(instanceGainLoss)}
                                      </TableCell>
                                      <TableCell align="center">
                                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', flexWrap: 'nowrap' }}>
                                          {!hideRefreshPrice && (
                                            <IconButton
                                              size="small"
                                              color="primary"
                                              onClick={() => handleManualPriceUpdate(instance.id, instance.symbol)}
                                              disabled={updatingAssetId === instance.id}
                                              title="Update price"
                                            >
                                              {updatingAssetId === instance.id ? (
                                                <CircularProgress size={16} />
                                              ) : (
                                                <Refresh fontSize="small" />
                                              )}
                                            </IconButton>
                                          )}
                                          <IconButton size="small" color="secondary" title="Attributes" onClick={() => openAttributes(instance.id, instance.name)}>
                                            <LabelIcon fontSize="small" />
                                          </IconButton>
                                          <IconButton size="small" color="primary" title="Edit" onClick={() => openEditDialog(instance)}>
                                            <EditIcon fontSize="small" />
                                          </IconButton>
                                          <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(instance)}>
                                            <DeleteIcon fontSize="small" />
                                          </IconButton>
                                        </Box>
                                      </TableCell>
                                    </TableRow>
                                  );
                                })}
                              </TableBody>
                            </Table>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
  };

  // Find the most recent price update timestamp across all assets
  const lastPriceUpdate = React.useMemo(() => {
    let latest: string | null = null;
    for (const asset of assets) {
      if (asset.last_price_update) {
        if (!latest || asset.last_price_update > latest) {
          latest = asset.last_price_update;
        }
      }
    }
    return latest;
  }, [assets]);

  if (loading || updating || bankAccountsLoading || dematAccountsLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Assets</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
          <Button
            variant="outlined"
            startIcon={snapshotLoading ? <CircularProgress size={20} /> : <CameraAlt />}
            onClick={handleTakeSnapshot}
            disabled={snapshotLoading}
          >
            {snapshotLoading ? 'Taking Snapshot...' : 'Take Snapshot'}
          </Button>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.5 }}>
            {lastPriceUpdate && (
              <Typography variant="caption" color="text.secondary" fontWeight="bold">
                Prices last updated: {(() => {
                  const ts = lastPriceUpdate;
                  const hasOffset = /[+-]\d{2}:\d{2}$/.test(ts) || ts.endsWith('Z');
                  const d = hasOffset ? new Date(ts) : new Date(ts + 'Z');
                  return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' });
                })()}
              </Typography>
            )}
            <Button
              variant="outlined"
              startIcon={refreshingPrices ? <CircularProgress size={20} /> : <Refresh />}
              onClick={handleRefreshPrices}
              disabled={refreshingPrices}
            >
              {refreshingPrices ? 'Refreshing...' : 'Refresh Prices'}
            </Button>
            {priceProgress && priceProgress.status === 'running' && (
              <Typography variant="caption" color="primary" fontWeight="bold">
                Updated {priceProgress.updated_assets + priceProgress.failed_assets} of {priceProgress.total_assets} assets
              </Typography>
            )}
          </Box>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Value
              </Typography>
              <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Invested
              </Typography>
              <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Gain/Loss
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography
                  variant="h5"
                  sx={{ color: totalGainLoss >= 0 ? 'success.main' : 'error.main' }}
                >
                  {formatCurrency(totalGainLoss)}
                </Typography>
                {totalGainLoss >= 0 ? (
                  <TrendingUp sx={{ color: 'success.main', ml: 1 }} />
                ) : (
                  <TrendingDown sx={{ color: 'error.main', ml: 1 }} />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Return %
              </Typography>
              <Typography
                variant="h5"
                sx={{ color: totalReturnPercentage >= 0 ? 'success.main' : 'error.main' }}
              >
                {formatPercentage(totalReturnPercentage)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={2}>
          <DayChangeCard assets={currentTabAssets.flatMap(g => g.instances)} />
        </Grid>
        <Grid item xs={6} md={2}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                XIRR
              </Typography>
              <Typography
                variant="h5"
                sx={{ color: aggregateXirr != null ? (aggregateXirr >= 0 ? 'success.main' : 'error.main') : 'text.secondary' }}
              >
                {aggregateXirr != null ? formatPercentage(aggregateXirr) : '—'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Asset Type Tabs */}
      <Paper sx={{ overflow: 'hidden' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={currentTab} onChange={handleTabChange} aria-label="asset type tabs" variant="scrollable" scrollButtons="auto">
            <Tab label={`All (${assetsByType.all.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Stocks (${assetsByType.stock.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`US Stocks (${assetsByType.us_stock.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Equity MF (${assetsByType.equity_mutual_fund.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Hybrid MF (${assetsByType.hybrid_mutual_fund.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Debt MF (${assetsByType.debt_mutual_fund.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Commodities (${assetsByType.commodity.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Crypto (${assetsByType.crypto.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Cash (${bankAccounts.length + dematAccounts.length + assetsByType.cash.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Other (${assetsByType.other.reduce((sum, g) => sum + g.instances.length, 0)})`} />
            <Tab label={`Bank Accounts (${bankAccounts.length})`} />
          </Tabs>
        </Box>

        <TabPanel value={currentTab} index={0}>
          {renderAssetsTable(assetsByType.all)}
        </TabPanel>
        <TabPanel value={currentTab} index={1}>
          {renderAssetsTable(assetsByType.stock)}
        </TabPanel>
        <TabPanel value={currentTab} index={2}>
          {renderAssetsTable(assetsByType.us_stock)}
        </TabPanel>
        <TabPanel value={currentTab} index={3}>
          {renderAssetsTable(assetsByType.equity_mutual_fund)}
        </TabPanel>
        <TabPanel value={currentTab} index={4}>
          {renderAssetsTable(assetsByType.hybrid_mutual_fund)}
        </TabPanel>
        <TabPanel value={currentTab} index={5}>
          {renderAssetsTable(assetsByType.debt_mutual_fund)}
        </TabPanel>
        <TabPanel value={currentTab} index={6}>
          {renderAssetsTable(assetsByType.commodity)}
        </TabPanel>
        <TabPanel value={currentTab} index={7}>
          {renderAssetsTable(assetsByType.crypto)}
        </TabPanel>
        <TabPanel value={currentTab} index={8}>
          {renderCashHoldingsTable()}
        </TabPanel>
        <TabPanel value={currentTab} index={9}>
          {renderAssetsTable(assetsByType.other)}
        </TabPanel>
        <TabPanel value={currentTab} index={10}>
          {renderBankAccountsTable()}
        </TabPanel>
      </Paper>

      {/* Asset Type Change Menu — filtered to allowed conversions */}
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

      {/* ── Asset Action Dialogs ─────────────────────────────────────────── */}
      <GenericAssetEditDialog
        open={editDialogOpen}
        onClose={closeEditDialog}
        onSaved={() => dispatch(fetchAssets(selectedPortfolioId))}
        asset={editingAsset}
        assetType={editingAssetType}
        dematAccounts={dematAccounts}
        bankAccounts={bankAccounts}
        portfolioId={selectedPortfolioId}
      />

      <CryptoAssetDialog
        open={cryptoDialogOpen}
        onClose={closeCryptoDialog}
        onSaved={() => dispatch(fetchAssets(selectedPortfolioId))}
        editingAsset={cryptoEditingAsset}
        cryptoAccounts={cryptoAccounts}
      />

      <AssetAttributeTagDialog
        assetId={tagAssetId}
        assetName={tagAssetName}
        open={tagAssetId !== null}
        onClose={closeAttributes}
      />

      {/* ── Bulk Attribute Assignment ─────────────────────────────────────── */}
      <BulkAttributeAssignDialog
        assetIds={Array.from(selectedAssetIds)}
        open={bulkAttrDialogOpen}
        onClose={() => setBulkAttrDialogOpen(false)}
        onSaved={() => setSelectedAssetIds(new Set())}
      />

      {/* ── Floating Selection Bar ────────────────────────────────────────── */}
      {selectedAssetIds.size > 0 && (
        <Paper
          elevation={6}
          sx={{
            position: 'fixed',
            bottom: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            px: 3,
            py: 1.5,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            borderRadius: 3,
            zIndex: 1300,
          }}
        >
          <Typography variant="body2" fontWeight="medium">
            {selectedAssetIds.size} asset{selectedAssetIds.size > 1 ? 's' : ''} selected
          </Typography>
          <Button
            variant="contained"
            size="small"
            startIcon={<LabelIcon />}
            onClick={() => setBulkAttrDialogOpen(true)}
          >
            Set Attributes
          </Button>
          <IconButton size="small" onClick={() => setSelectedAssetIds(new Set())} title="Clear selection">
            <CloseIcon fontSize="small" />
          </IconButton>
        </Paper>
      )}
    </Box>
  );
};

export default Assets;

// Made with Bob
