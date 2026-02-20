import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
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
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  AccountBalance,
  ShowChart,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolioSummary } from '../store/slices/portfolioSlice';
import { fetchAssets } from '../store/slices/assetsSlice';
import PortfolioChart from '../components/charts/PortfolioChart';
import PerformanceChart from '../components/charts/PerformanceChart';
import AssetAllocationChart from '../components/charts/AssetAllocationChart';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

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

interface StatCardProps {
  title: string;
  value: string;
  change?: number;
  icon: React.ReactNode;
  color: string;
  hideNumbers: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, change, icon, color, hideNumbers }) => {
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

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { summary, loading, error } = useSelector((state: RootState) => state.portfolio);
  const { notify } = useNotification();
  const { assets } = useSelector((state: RootState) => state.assets);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankAccountsLoading, setBankAccountsLoading] = useState(false);
  const [dematAccounts, setDematAccounts] = useState<DematAccount[]>([]);
  const [dematAccountsLoading, setDematAccountsLoading] = useState(false);
  const [hideNumbers, setHideNumbers] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        await dispatch(fetchPortfolioSummary());
        await dispatch(fetchAssets());
        await Promise.all([fetchBankAccounts(), fetchDematAccounts()]);
      } catch (err) {
        notify.error(getErrorMessage(err, 'Failed to load dashboard data'));
      }
    };
    fetchData();
  }, [dispatch]);

  const fetchBankAccounts = async () => {
    try {
      setBankAccountsLoading(true);
      const response = await api.get('/bank-accounts/');
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
      const response = await api.get('/demat-accounts/');
      setDematAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setDematAccountsLoading(false);
    }
  };

  if (loading || bankAccountsLoading || dematAccountsLoading) {
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

  // Calculate asset allocation data
  const assetsByType = (assets || []).reduce((acc: any, asset: any) => {
    const type = asset.asset_type || 'Other';
    if (!acc[type]) {
      acc[type] = { value: 0, count: 0, invested: 0 };
    }
    acc[type].value += asset.current_value || 0;
    acc[type].count += 1;
    acc[type].invested += asset.total_invested || 0;
    return acc;
  }, {});

  // Add bank accounts as a separate category
  if (bankAccounts.length > 0) {
    assetsByType['Bank Accounts'] = {
      value: totalBankBalance,
      count: bankAccounts.length,
      invested: totalBankBalance,
    };
  }

  // Add demat cash balance as a separate category
  const dematWithCash = dematAccounts.filter(a => a.cash_balance > 0);
  if (dematWithCash.length > 0) {
    assetsByType['Demat Cash'] = {
      value: totalDematCash,
      count: dematWithCash.length,
      invested: totalDematCash,
    };
  }

  const totalValue = Object.values(assetsByType).reduce((sum: number, item: any) => sum + item.value, 0);
  
  const allocationData = Object.entries(assetsByType)
    .map(([type, data]: [string, any]) => ({
      type,
      value: data.value,
      count: data.count,
      invested: data.invested,
      percentage: totalValue > 0 ? (data.value / totalValue) * 100 : 0,
      gainLoss: data.value - data.invested,
      gainLossPercentage: data.invested > 0 ? ((data.value - data.invested) / data.invested) * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value);

  const formatAssetType = (type: string) => {
    // Map specific asset types to their full names
    const assetTypeMap: { [key: string]: string } = {
      'ppf': 'Public Provident Fund',
      'pf': 'Provident Fund',
      'nps': 'National Pension System',
      'ssy': 'Sukanya Samriddhi Yojana',
      'gratuity': 'Gratuity',
      'insurance_policy': 'Insurance',
      'us_stock': 'US Stocks',
      'equity_mutual_fund': 'Equity Mutual Funds',
      'debt_mutual_fund': 'Debt Mutual Funds',
      'fixed_deposit': 'Fixed Deposit',
      'recurring_deposit': 'Recurring Deposit',
      'real_estate': 'Real Estate',
      'savings_account': 'Savings Account',
      'nsc': 'National Savings Certificate',
      'kvp': 'Kisan Vikas Patra',
      'scss': 'Senior Citizens Savings Scheme',
      'mis': 'Monthly Income Scheme',
      'corporate_bond': 'Corporate Bonds',
      'rbi_bond': 'RBI Bonds',
      'tax_saving_bond': 'Tax Saving Bonds',
      'reit': 'REITs',
      'invit': 'InvITs',
      'sovereign_gold_bond': 'Sovereign Gold Bonds',
    };
    
    // Return mapped name if exists, otherwise format the type
    if (assetTypeMap[type.toLowerCase()]) {
      return assetTypeMap[type.toLowerCase()];
    }
    
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
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
      
      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Value"
            value={formatCurrency((summary?.portfolio_summary?.total_current_value || 0) + totalBankBalance + totalDematCash)}
            change={summary?.portfolio_summary?.total_profit_loss_percentage}
            icon={<AccountBalance sx={{ color: 'white' }} />}
            color="primary.main"
            hideNumbers={hideNumbers}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Investment"
            value={formatCurrency((summary?.portfolio_summary?.total_invested || 0) + totalBankBalance + totalDematCash)}
            icon={<ShowChart sx={{ color: 'white' }} />}
            color="secondary.main"
            hideNumbers={hideNumbers}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Gain/Loss"
            value={formatCurrency(summary?.portfolio_summary?.total_profit_loss || 0)}
            change={summary?.portfolio_summary?.total_profit_loss_percentage}
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
            value={hideNumbers ? '•••' : ((summary?.portfolio_summary?.total_assets || 0) + bankAccounts.length).toString()}
            icon={<AccountBalance sx={{ color: 'white' }} />}
            color="info.main"
            hideNumbers={false}
          />
        </Grid>
      </Grid>

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
            <AssetAllocationChart />
          </Paper>
        </Grid>
        
        {/* Asset Allocation Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Asset Allocation Details
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Asset Type</strong></TableCell>
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
                        <TableRow key={row.type}>
                          <TableCell>{formatAssetType(row.type)}</TableCell>
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
                        <TableCell align="right"><strong>{hideNumbers ? '•••' : (assets || []).length}</strong></TableCell>
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

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Portfolio Value Over Time
            </Typography>
            <PortfolioChart />
          </Paper>
        </Grid>
      </Grid>

    </Box>
  );
};

export default Dashboard;

// Made with Bob
