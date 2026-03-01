import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  Link,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  AccountBalanceWallet,
  CurrencyRupee,
  PieChart,
  Visibility,
  VisibilityOff,
  ArrowBack,
  SelectAll,
  RocketLaunch as GettingStartedIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolioSummary, fetchPortfolios, setSelectedPortfolioId } from '../store/slices/portfolioSlice';
import { fetchAssets } from '../store/slices/assetsSlice';
import PerformanceChart from '../components/charts/PerformanceChart';
import AssetAllocationChart from '../components/charts/AssetAllocationChart';
import api, { assetTypesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

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
  cash_balance: number;
  is_active: boolean;
}

interface CryptoAccount {
  id: number;
  exchange_name: string;
  account_name?: string;
  cash_balance_usd: number;
  cash_balance_inr: number;
  is_active: boolean;
}

interface StatCardProps {
  title: string;
  value: string;
  change?: number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  hideNumbers: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, change, subtitle, icon, color, hideNumbers }) => {
  const isPositive = change !== undefined && change >= 0;
  
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flex: 1 }}>
          <Box>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {hideNumbers ? '••••••' : value}
            </Typography>
            {change !== undefined && (
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                {isPositive ? (
                  <TrendingUp sx={{ color: 'success.main', mr: 0.5 }} />
                ) : (
                  <TrendingDown sx={{ color: 'error.main', mr: 0.5 }} />
                )}
                <Typography
                  variant="body2"
                  sx={{ color: isPositive ? 'success.main' : 'error.main' }}
                >
                  {hideNumbers ? '••••' : `${isPositive ? '+' : ''}${change.toFixed(2)}%`}
                </Typography>
              </Box>
            )}
            {subtitle && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                {hideNumbers ? '••••' : subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              backgroundColor: color,
              borderRadius: 2,
              p: 1.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

// Asset type key → navigation route
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
  crypto: '/crypto-assets',
  fixed_deposit: '/fixed-deposit',
  recurring_deposit: '/recurring-deposit',
  savings_account: '/savings',
  corporate_bond: '/corporate-bond',
  rbi_bond: '/rbi-bond',
  tax_saving_bond: '/tax-saving-bond',
  ppf: '/ppf',
  pf: '/pf',
  nps: '/nps',
  ssy: '/ssy',
  nsc: '/nsc',
  kvp: '/kvp',
  scss: '/scss',
  mis: '/mis',
  gratuity: '/gratuity',
  pension: '/pension',
  insurance_policy: '/insurance',
  reit: '/reits',
  invit: '/invits',
  land: '/land',
  farm_land: '/farm-land',
  house: '/house',
  cash: '/cash-in-hand',
};

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { summary, loading, error, portfolios } = useSelector((state: RootState) => state.portfolio);
  const { notify } = useNotification();
  const { assets } = useSelector((state: RootState) => state.assets);
  const selectedPortfolioId = useSelectedPortfolio();
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankAccountsLoading, setBankAccountsLoading] = useState(false);
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematAccountsLoading, setDematAccountsLoading] = useState(false);
  const [cryptoAccounts, setCryptoAccounts] = useState<CryptoAccount[]>([]);
  const [cryptoAccountsLoading, setCryptoAccountsLoading] = useState(false);
  const [hideNumbers, setHideNumbers] = useState(false);
  const [assetTypeMap, setAssetTypeMap] = useState<Record<string, { category: string; displayLabel: string }>>({});
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [gettingStartedOpen, setGettingStartedOpen] = useState(false);

  const NavLink = ({ to, children }: { to: string; children: React.ReactNode }) => (
    <Link
      component="button"
      variant="body2"
      sx={{ verticalAlign: 'baseline', fontWeight: 600 }}
      onClick={() => { setGettingStartedOpen(false); navigate(to); }}
    >
      {children}
    </Link>
  );

  useEffect(() => {
    const fetchData = async () => {
      try {
        dispatch(fetchPortfolios());
        await dispatch(fetchPortfolioSummary(selectedPortfolioId));
        await dispatch(fetchAssets(selectedPortfolioId));
        await Promise.all([fetchBankAccounts(), fetchDematAccounts(), fetchCryptoAccounts()]);
      } catch (err) {
        notify.error(getErrorMessage(err, 'Failed to load dashboard data'));
      }
    };
    fetchData();
  }, [dispatch, selectedPortfolioId]);

  useEffect(() => {
    const fetchAssetTypeMap = async () => {
      try {
        const data = await assetTypesAPI.getAll();
        const map: Record<string, { category: string; displayLabel: string }> = {};
        data.forEach((at: any) => {
          map[at.name] = { category: at.category, displayLabel: at.display_label };
        });
        setAssetTypeMap(map);
      } catch {
        // Fallback: chart will show "Other" for unmapped types
      }
    };
    fetchAssetTypeMap();
  }, []);

  const fetchBankAccounts = async () => {
    try {
      setBankAccountsLoading(true);
      const response = await api.get('/bank-accounts/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setBankAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
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
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setDematAccountsLoading(false);
    }
  };

  const fetchCryptoAccounts = async () => {
    try {
      setCryptoAccountsLoading(true);
      const response = await api.get('/crypto-accounts/', { params: selectedPortfolioId ? { portfolio_id: selectedPortfolioId } : {} });
      setCryptoAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setCryptoAccountsLoading(false);
    }
  };

  if (loading || bankAccountsLoading || dematAccountsLoading || cryptoAccountsLoading) {
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

  const formatCurrency = (value: number, hide: boolean = false) => {
    if (hide) {
      return '₹ ••••••';
    }
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const toggleHideNumbers = () => {
    setHideNumbers(!hideNumbers);
  };

  // Calculate cash totals
  const totalBankBalance = bankAccounts.reduce((sum, a) => sum + a.current_balance, 0);
  const totalDematCash = dematAccounts.reduce((sum, a) => sum + a.cash_balance, 0);
  const totalCryptoCash = cryptoAccounts.reduce((sum, a) => sum + (a.cash_balance_inr || 0), 0);

  const handlePortfolioCardClick = (portfolioId: number) => {
    dispatch(setSelectedPortfolioId(portfolioId));
  };

  const handleViewAllPortfolios = () => {
    dispatch(setSelectedPortfolioId(null));
  };

  // Build category-based allocation data
  const assetsByCategory: Record<string, { value: number; count: number; invested: number }> = {};
  const assetsByTypeInCategory: Record<string, Record<string, { value: number; count: number; invested: number }>> = {};

  (assets || []).forEach((asset: any) => {
    const type = (asset.asset_type || 'other').toLowerCase();
    const category = assetTypeMap[type]?.category || 'Other';

    if (!assetsByCategory[category]) {
      assetsByCategory[category] = { value: 0, count: 0, invested: 0 };
    }
    assetsByCategory[category].value += asset.current_value || 0;
    assetsByCategory[category].count += 1;
    assetsByCategory[category].invested += asset.total_invested || 0;

    if (!assetsByTypeInCategory[category]) {
      assetsByTypeInCategory[category] = {};
    }
    if (!assetsByTypeInCategory[category][type]) {
      assetsByTypeInCategory[category][type] = { value: 0, count: 0, invested: 0 };
    }
    assetsByTypeInCategory[category][type].value += asset.current_value || 0;
    assetsByTypeInCategory[category][type].count += 1;
    assetsByTypeInCategory[category][type].invested += asset.total_invested || 0;
  });

  // Merge bank account balances into Fixed Income category
  if (totalBankBalance > 0) {
    if (!assetsByCategory['Fixed Income']) {
      assetsByCategory['Fixed Income'] = { value: 0, count: 0, invested: 0 };
    }
    assetsByCategory['Fixed Income'].value += totalBankBalance;
    assetsByCategory['Fixed Income'].invested += totalBankBalance;
  }

  // Merge demat cash into Equity category
  if (totalDematCash > 0) {
    if (!assetsByCategory['Equity']) {
      assetsByCategory['Equity'] = { value: 0, count: 0, invested: 0 };
    }
    assetsByCategory['Equity'].value += totalDematCash;
    assetsByCategory['Equity'].invested += totalDematCash;
  }

  // Merge crypto cash into Crypto category
  if (totalCryptoCash > 0) {
    if (!assetsByCategory['Crypto']) {
      assetsByCategory['Crypto'] = { value: 0, count: 0, invested: 0 };
    }
    assetsByCategory['Crypto'].value += totalCryptoCash;
    assetsByCategory['Crypto'].invested += totalCryptoCash;
  }

  // Get display name for an asset type key
  const getDisplayName = (type: string) => {
    return assetTypeMap[type]?.displayLabel || type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  // Determine current view data based on drill-down state
  const isShowingCategories = !selectedCategory;
  const currentViewData = selectedCategory && assetsByTypeInCategory[selectedCategory]
    ? assetsByTypeInCategory[selectedCategory]
    : assetsByCategory;

  const totalValue = Object.values(currentViewData).reduce((sum, item) => sum + item.value, 0);

  const chartData = Object.entries(currentViewData)
    .map(([key, data]) => ({
      key,
      name: isShowingCategories ? key : getDisplayName(key),
      value: data.value,
    }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value);

  const allocationData = Object.entries(currentViewData)
    .map(([key, data]) => ({
      type: key,
      displayName: isShowingCategories ? key : getDisplayName(key),
      value: data.value,
      count: data.count,
      invested: data.invested,
      percentage: totalValue > 0 ? (data.value / totalValue) * 100 : 0,
      gainLoss: data.value - data.invested,
      gainLossPercentage: data.invested > 0 ? ((data.value - data.invested) / data.invested) * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value);

  const handleCategoryClick = (categoryName: string) => {
    setSelectedCategory(categoryName);
  };

  const handleTypeClick = (typeKey: string) => {
    const route = ASSET_TYPE_ROUTES[typeKey];
    if (route) {
      navigate(route);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Portfolio Dashboard
        </Typography>
        <Tooltip title={hideNumbers ? "Show Numbers" : "Hide Numbers"}>
          <IconButton onClick={toggleHideNumbers} color="primary">
            {hideNumbers ? <Visibility /> : <VisibilityOff />}
          </IconButton>
        </Tooltip>
      </Box>

      <Alert
        severity="info"
        icon={<GettingStartedIcon />}
        action={
          <Button color="inherit" size="small" onClick={() => setGettingStartedOpen(true)}>
            Learn More
          </Button>
        }
        sx={{ mb: 3 }}
      >
        New to PortAct? See how to set up your portfolios and start tracking your assets.
      </Alert>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Value"
            value={formatCurrency((summary?.portfolio_summary?.total_current_value || 0) + totalBankBalance + totalDematCash + totalCryptoCash)}
            change={summary?.portfolio_summary?.total_profit_loss_percentage}
            icon={<AccountBalanceWallet sx={{ color: 'white' }} />}
            color="primary.main"
            hideNumbers={hideNumbers}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Investment"
            value={formatCurrency((summary?.portfolio_summary?.total_invested || 0) + totalBankBalance + totalDematCash + totalCryptoCash)}
            icon={<CurrencyRupee sx={{ color: 'white' }} />}
            color="secondary.main"
            hideNumbers={hideNumbers}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Gain/Loss"
            value={formatCurrency(summary?.portfolio_summary?.total_profit_loss || 0)}
            change={summary?.portfolio_summary?.total_profit_loss_percentage}
            subtitle={summary?.portfolio_summary?.portfolio_xirr != null
              ? `XIRR: ${summary.portfolio_summary.portfolio_xirr >= 0 ? '+' : ''}${summary.portfolio_summary.portfolio_xirr.toFixed(2)}% p.a.`
              : undefined}
            icon={
              (summary?.portfolio_summary?.total_profit_loss || 0) >= 0 ? (
                <TrendingUp sx={{ color: 'white' }} />
              ) : (
                <TrendingDown sx={{ color: 'white' }} />
              )
            }
            color={(summary?.portfolio_summary?.total_profit_loss || 0) >= 0 ? 'success.main' : 'error.main'}
            hideNumbers={hideNumbers}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Assets"
            value={hideNumbers ? '•••' : ((summary?.portfolio_summary?.total_assets || 0) + bankAccounts.length + cryptoAccounts.length).toString()}
            icon={<PieChart sx={{ color: 'white' }} />}
            color="info.main"
            hideNumbers={false}
          />
        </Grid>
      </Grid>

      {/* Portfolio Overview Section */}
      {portfolios.length > 1 && (
        <Paper sx={{ p: 2.5, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              My Portfolios
            </Typography>
            {selectedPortfolioId !== null && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<SelectAll />}
                onClick={handleViewAllPortfolios}
              >
                All Portfolios
              </Button>
            )}
          </Box>

          <Grid container spacing={2}>
            {portfolios.map((p: any) => {
              const pl = (p.total_current_value || 0) - (p.total_invested || 0);
              const plPct = p.total_invested > 0 ? (pl / p.total_invested) * 100 : 0;
              const isSelected = selectedPortfolioId === p.id;
              return (
                <Grid item xs={12} sm={6} md={4} lg={3} key={p.id}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      height: '100%',
                      border: '2px solid',
                      borderColor: isSelected ? 'primary.main' : 'transparent',
                      backgroundColor: isSelected ? 'action.selected' : undefined,
                      transition: 'all 0.2s ease-in-out',
                      '&:hover': {
                        borderColor: isSelected ? 'primary.main' : 'grey.300',
                        boxShadow: 3,
                      },
                    }}
                    onClick={() => handlePortfolioCardClick(p.id)}
                  >
                    <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                        <Typography variant="subtitle2" fontWeight={600} noWrap>
                          {p.name}
                        </Typography>
                        {p.is_default && (
                          <Chip label="Default" size="small" variant="outlined" color="primary" sx={{ height: 20, fontSize: '0.65rem' }} />
                        )}
                      </Box>
                      <Typography variant="h6" fontWeight={700}>
                        {hideNumbers ? '₹ ••••••' : formatCurrency(p.total_current_value || 0)}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                        {pl >= 0 ? (
                          <TrendingUp sx={{ fontSize: 16, color: 'success.main' }} />
                        ) : (
                          <TrendingDown sx={{ fontSize: 16, color: 'error.main' }} />
                        )}
                        <Typography
                          variant="caption"
                          sx={{ color: pl >= 0 ? 'success.main' : 'error.main', fontWeight: 500 }}
                        >
                          {hideNumbers
                            ? '••••'
                            : `${pl >= 0 ? '+' : ''}${formatCurrency(pl)} (${plPct >= 0 ? '+' : ''}${plPct.toFixed(1)}%)`
                          }
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {hideNumbers ? '•••' : `${p.asset_count} asset${p.asset_count !== 1 ? 's' : ''}`}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        </Paper>
      )}

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Portfolio Performance
            </Typography>
            <PerformanceChart hideNumbers={hideNumbers} />
          </Paper>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Asset Allocation
            </Typography>
            <AssetAllocationChart
              data={chartData}
              selectedCategory={selectedCategory}
              onSliceClick={handleCategoryClick}
              onTypeClick={handleTypeClick}
              onBack={() => setSelectedCategory(null)}
            />
          </Paper>
        </Grid>
        
        {/* Asset Allocation Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              {selectedCategory && (
                <IconButton size="small" onClick={() => setSelectedCategory(null)} title="Back to categories">
                  <ArrowBack fontSize="small" />
                </IconButton>
              )}
              <Typography variant="h6">
                {selectedCategory ? `${selectedCategory} — Asset Types` : 'Asset Allocation by Category'}
              </Typography>
              {selectedCategory && (
                <Chip label={selectedCategory} size="small" color="primary" variant="outlined" />
              )}
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>{isShowingCategories ? 'Category' : 'Asset Type'}</strong></TableCell>
                    <TableCell align="right"><strong>Count</strong></TableCell>
                    <TableCell align="right"><strong>Current Value</strong></TableCell>
                    <TableCell align="right"><strong>Invested</strong></TableCell>
                    <TableCell align="right"><strong>Gain/Loss</strong></TableCell>
                    <TableCell align="right"><strong>Returns %</strong></TableCell>
                    <TableCell align="right"><strong>Allocation %</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {allocationData.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography color="text.secondary">
                          No assets found. Upload statements to get started.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    <>
                      {allocationData.map((row) => (
                        <TableRow
                          key={row.type}
                          hover
                          sx={{ cursor: 'pointer' }}
                          onClick={() => {
                            if (isShowingCategories) {
                              handleCategoryClick(row.type);
                            } else {
                              handleTypeClick(row.type);
                            }
                          }}
                        >
                          <TableCell>{row.displayName}</TableCell>
                          <TableCell align="right">{hideNumbers ? '•••' : row.count}</TableCell>
                          <TableCell align="right">{formatCurrency(row.value, hideNumbers)}</TableCell>
                          <TableCell align="right">{formatCurrency(row.invested, hideNumbers)}</TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: row.gainLoss >= 0 ? 'success.main' : 'error.main',
                              fontWeight: 'medium'
                            }}
                          >
                            {formatCurrency(row.gainLoss, hideNumbers)}
                          </TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: row.gainLossPercentage >= 0 ? 'success.main' : 'error.main',
                              fontWeight: 'medium'
                            }}
                          >
                            {hideNumbers ? '••••' : `${row.gainLossPercentage >= 0 ? '+' : ''}${row.gainLossPercentage.toFixed(2)}%`}
                          </TableCell>
                          <TableCell align="right">{hideNumbers ? '••••' : `${row.percentage.toFixed(2)}%`}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow sx={{ backgroundColor: 'action.hover' }}>
                        <TableCell><strong>Total</strong></TableCell>
                        <TableCell align="right"><strong>{hideNumbers ? '•••' : allocationData.reduce((sum, row) => sum + row.count, 0)}</strong></TableCell>
                        <TableCell align="right"><strong>{formatCurrency(totalValue, hideNumbers)}</strong></TableCell>
                        <TableCell align="right">
                          <strong>
                            {formatCurrency(allocationData.reduce((sum, row) => sum + row.invested, 0), hideNumbers)}
                          </strong>
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            color: (totalValue - allocationData.reduce((sum, row) => sum + row.invested, 0)) >= 0
                              ? 'success.main'
                              : 'error.main',
                            fontWeight: 'bold'
                          }}
                        >
                          <strong>
                            {formatCurrency(totalValue - allocationData.reduce((sum, row) => sum + row.invested, 0), hideNumbers)}
                          </strong>
                        </TableCell>
                        <TableCell align="right">
                          <strong>
                            {hideNumbers ? '••••' : (allocationData.reduce((sum, row) => sum + row.invested, 0) > 0
                              ? `${((totalValue - allocationData.reduce((sum, row) => sum + row.invested, 0)) /
                                  allocationData.reduce((sum, row) => sum + row.invested, 0) * 100).toFixed(2)}%`
                              : '0.00%')}
                          </strong>
                        </TableCell>
                        <TableCell align="right"><strong>{hideNumbers ? '••••' : '100.00%'}</strong></TableCell>
                      </TableRow>
                    </>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

      </Grid>

      {/* Getting Started Dialog */}
      <Dialog open={gettingStartedOpen} onClose={() => setGettingStartedOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <GettingStartedIcon color="primary" />
            How to get started
          </Box>
          <IconButton size="small" onClick={() => setGettingStartedOpen(false)}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {([
            <>Open the <NavLink to="/stocks">Assets</NavLink> menu from the left rail and choose the asset type you'd like to track — Stocks, Mutual Funds, PPF, Real Estate, and more.</>,
            <>For broker-linked assets like Stocks and Mutual Funds, head to the <NavLink to="/demat-holdings">Demat Holdings</NavLink> section under Assets and upload your account statement. Supported sources include <strong>NSDL/CDSL CAS</strong> (PDF), <strong>MF Central CAS</strong> (PDF), <strong>Zerodha</strong>, <strong>Groww</strong>, <strong>ICICI Direct</strong> (CSV/XLSX), and <strong>INDmoney</strong> &amp; <strong>Vested</strong> for US stocks. The system will automatically create the accounts and holdings for you.</>,
            <>For other assets such as <NavLink to="/ppf">PPF</NavLink>, <NavLink to="/pension">Pension</NavLink>, or <NavLink to="/house">Real Estate</NavLink>, create them manually by filling in the details on their respective pages.</>,
            <>All asset values are automatically converted to <strong>INR</strong> using live exchange rates — no manual conversion needed.</>,
            <>Once your assets are set up, visit the <NavLink to="/assets">Asset Overview</NavLink> page to see everything in one place, with a consolidated view across all portfolios.</>,
            <>Need to reclassify an asset? On the <NavLink to="/assets">Asset Overview</NavLink> page, click on any asset's type column to change it. For example, correct a Debt Fund that was auto-classified as Equity MF.</>,
            <>You can organize your holdings into multiple <NavLink to="/portfolios">Portfolios</NavLink>. <strong>Note:</strong> stocks within a Demat account are moved together — the entire <NavLink to="/demat-accounts">Demat account</NavLink> must be assigned to the same portfolio.</>,
            <>To move an asset between portfolios, simply edit the asset, change the <strong>Portfolio</strong> dropdown to your target portfolio, and save.</>,
            <>Every asset type has its own management page (accessible from the Assets menu) where you can create, edit, and delete individual holdings.</>,
            <>Track your portfolio performance and discover trends under the <NavLink to="/alerts">Insights</NavLink> section in the left rail.</>,
          ] as React.ReactNode[]).map((content, i, arr) => (
            <Box key={i} sx={{ display: 'flex', gap: 1.5, py: 1.2, borderBottom: i < arr.length - 1 ? '1px solid' : 'none', borderColor: 'divider' }}>
              <Typography
                variant="body2"
                component="span"
                sx={{
                  minWidth: 24,
                  height: 24,
                  borderRadius: '50%',
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  flexShrink: 0,
                  mt: 0.1,
                }}
              >
                {i + 1}
              </Typography>
              <Typography variant="body2" component="span">{content}</Typography>
            </Box>
          ))}
        </DialogContent>
      </Dialog>

    </Box>
  );
};

export default Dashboard;

// Made with Bob
