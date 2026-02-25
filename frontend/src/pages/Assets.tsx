import React, { useEffect, useState } from 'react';
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
} from '@mui/material';
import { TrendingUp, TrendingDown, KeyboardArrowDown, KeyboardArrowUp, AccountBalance, Refresh, Warning, CheckCircle, CameraAlt, Error as ErrorIcon } from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchAssets } from '../store/slices/assetsSlice';
import api, { assetsAPI, assetTypesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

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
  symbol: string;
  name: string;
  asset_type: string;
  totalQuantity: number;
  totalInvested: number;
  totalCurrentValue: number;
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
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [currentTab, setCurrentTab] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedAsset, setSelectedAsset] = useState<GroupedAsset | null>(null);
  const [updating, setUpdating] = useState(false);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankAccountsLoading, setBankAccountsLoading] = useState(false);
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematAccountsLoading, setDematAccountsLoading] = useState(false);
  const [refreshingPrices, setRefreshingPrices] = useState(false);
  const [updatingAssetId, setUpdatingAssetId] = useState<number | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [assetTypes, setAssetTypes] = useState<{ value: string; label: string; category: string }[]>([]);

  useEffect(() => {
    dispatch(fetchAssets(selectedPortfolioId));
    fetchBankAccounts();
    fetchDematAccounts();
    fetchAssetTypes();
  }, [dispatch, selectedPortfolioId]);

  const fetchAssetTypes = async () => {
    try {
      const data = await assetTypesAPI.getAll({ is_active: true });
      setAssetTypes(
        Array.isArray(data) ? data.map((t: any) => ({ value: t.name, label: t.display_label, category: t.category })) : []
      );
    } catch {
      setAssetTypes([]);
    }
  };

  const handleRefreshPrices = async () => {
    try {
      setRefreshingPrices(true);
      await api.post('/prices/update', {});
      
      notify.success('Price update triggered! Prices will be updated in the background.');

      // Refresh assets after a short delay to show updated prices
      setTimeout(() => {
        dispatch(fetchAssets(selectedPortfolioId));
      }, 3000);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to refresh prices'));
    } finally {
      setRefreshingPrices(false);
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

  const getAssetTypeColor = (type: string) => {
    const colors: { [key: string]: any } = {
      stock: 'primary',
      equity_mutual_fund: 'secondary',
      debt_mutual_fund: 'info',
      bond: 'success',
      commodity: 'warning',
      crypto: 'error',
    };
    return colors[type.toLowerCase()] || 'default';
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
          symbol: asset.symbol,
          name: asset.name,
          asset_type: asset.asset_type,
          totalQuantity: 0,
          totalInvested: 0,
          totalCurrentValue: 0,
          instances: [],
        });
      }

      const group = groups.get(key)!;
      group.totalQuantity += asset.quantity || 0;
      group.totalInvested += asset.total_invested || 0;
      group.totalCurrentValue += asset.current_value || 0;
      group.instances.push(asset);
    });

    return Array.from(groups.values());
  }, [assets]);

  // Group assets by type
  const assetsByType = React.useMemo(() => {
    const types: { [key: string]: GroupedAsset[] } = {
      all: groupedAssets,
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

    return types;
  }, [groupedAssets]);

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


  const renderAssetsTable = (assetsToRender: GroupedAsset[]) => (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell width="40px" />
            <TableCell>Asset</TableCell>
            <TableCell>Type</TableCell>
            <TableCell align="right">Qty</TableCell>
            <TableCell align="right">Current Price</TableCell>
            <TableCell align="right">Invested</TableCell>
            <TableCell align="right">Value</TableCell>
            <TableCell align="right">P&L</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {assetsToRender.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} align="center">
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
              const hideRefreshPrice = ['Other', 'Fixed Income', 'Govt. Schemes'].includes(assetCategory);

              return (
                <React.Fragment key={group.symbol}>
                  {/* Main Row */}
                  <TableRow sx={{
                    '& > *': { borderBottom: hasMultipleInstances && isExpanded ? 'none' : undefined },
                    backgroundColor: missingIsin ? 'rgba(255, 0, 0, 0.05)' : 'inherit'
                  }}>
                    <TableCell>
                      {hasMultipleInstances && (
                        <IconButton size="small" onClick={() => toggleRow(group.symbol)}>
                          {isExpanded ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
                        </IconButton>
                      )}
                    </TableCell>
                    {/* Asset: symbol + name combined */}
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography variant="body2" fontWeight="medium">
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
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getAssetTypeLabel(group.asset_type)}
                        color={getAssetTypeColor(group.asset_type)}
                        size="small"
                        onClick={(e) => handleAssetTypeClick(e, group)}
                        sx={{ cursor: 'pointer' }}
                      />
                    </TableCell>
                    <TableCell align="right">{group.totalQuantity.toFixed(2)}</TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                        {formatCurrency(currentPrice)}
                        {!hideRefreshPrice && (
                          group.instances.some(i => i.price_update_failed) ? (
                            <Tooltip title={group.instances.find(i => i.price_update_failed)?.price_update_error || "Price update failed"} arrow>
                              <ErrorIcon fontSize="small" color="error" />
                            </Tooltip>
                          ) : group.instances.some(i => i.last_price_update) ? (
                            <Tooltip title={`Last updated: ${new Date(group.instances[0].last_price_update!).toLocaleString()}`} arrow>
                              <CheckCircle fontSize="small" color="success" sx={{ opacity: 0.6 }} />
                            </Tooltip>
                          ) : (
                            <Tooltip title="Price never updated - click refresh to update" arrow>
                              <Warning fontSize="small" sx={{ opacity: 0.4, color: 'grey.500' }} />
                            </Tooltip>
                          )
                        )}
                      </Box>
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
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
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
                        {hasMultipleInstances && (
                          <Typography variant="caption" color="text.secondary">Expand</Typography>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Rows - Show individual instances */}
                  {hasMultipleInstances && (
                    <TableRow>
                      <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={9}>
                        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                          <Box sx={{ margin: 2 }}>
                            <Typography variant="h6" gutterBottom component="div">
                              Account Details
                            </Typography>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
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
                                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
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
          </Box>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Value
              </Typography>
              <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Invested
              </Typography>
              <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
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
        <Grid item xs={12} md={3}>
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

      {/* Asset Type Change Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleAssetTypeMenuClose}
      >
        {assetTypes.map((type) => (
          <MenuItem
            key={type.value}
            onClick={() => handleAssetTypeChange(type.value)}
            selected={selectedAsset?.asset_type.toLowerCase() === type.value}
          >
            {type.label}
          </MenuItem>
        ))}
      </Menu>

    </Box>
  );
};

export default Assets;

// Made with Bob
