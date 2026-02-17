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
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  AccountBalance,
  ShowChart,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolioSummary, fetchPortfolioHistory } from '../store/slices/portfolioSlice';
import { fetchAssets } from '../store/slices/assetsSlice';
import PortfolioChart from '../components/charts/PortfolioChart';
import PerformanceChart from '../components/charts/PerformanceChart';
import AssetAllocationChart from '../components/charts/AssetAllocationChart';
import axios from 'axios';

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

interface StatCardProps {
  title: string;
  value: string;
  change?: number;
  icon: React.ReactNode;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, change, icon, color }) => {
  const isPositive = change !== undefined && change >= 0;
  
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {value}
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
                  {isPositive ? '+' : ''}{change.toFixed(2)}%
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
  const { assets } = useSelector((state: RootState) => state.assets);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankAccountsLoading, setBankAccountsLoading] = useState(false);

  useEffect(() => {
    // Fetch all data once when component mounts
    const fetchData = async () => {
      await dispatch(fetchPortfolioSummary());
      await dispatch(fetchPortfolioHistory());
      await dispatch(fetchAssets());
      await fetchBankAccounts();
    };
    fetchData();
  }, [dispatch]);

  const fetchBankAccounts = async () => {
    try {
      setBankAccountsLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/v1/bank-accounts/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBankAccounts(response.data);
    } catch (err) {
      console.error('Failed to fetch bank accounts:', err);
    } finally {
      setBankAccountsLoading(false);
    }
  };

  if (loading || bankAccountsLoading) {
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

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Calculate bank account totals
  const totalBankBalance = bankAccounts.reduce((sum, account) => sum + account.current_balance, 0);

  // Calculate asset allocation data
  const assetsByType = (assets || []).reduce((acc: any, asset: any) => {
    const type = asset.asset_type || 'Other';
    if (!acc[type]) {
      acc[type] = {
        value: 0,
        count: 0,
        invested: 0,
      };
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
      invested: totalBankBalance, // Bank accounts have no gain/loss
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
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Portfolio Dashboard
      </Typography>
      
      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Value"
            value={formatCurrency((summary?.portfolio_summary?.total_current_value || 0) + totalBankBalance)}
            change={summary?.portfolio_summary?.total_profit_loss_percentage}
            icon={<AccountBalance sx={{ color: 'white' }} />}
            color="primary.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Investment"
            value={formatCurrency((summary?.portfolio_summary?.total_invested || 0) + totalBankBalance)}
            icon={<ShowChart sx={{ color: 'white' }} />}
            color="secondary.main"
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
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Assets"
            value={((summary?.portfolio_summary?.total_assets || 0) + bankAccounts.length).toString()}
            icon={<AccountBalance sx={{ color: 'white' }} />}
            color="info.main"
          />
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Portfolio Performance
            </Typography>
            <PerformanceChart />
          </Paper>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3 }}>
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
                          <TableCell align="right">{row.count}</TableCell>
                          <TableCell align="right">{formatCurrency(row.value)}</TableCell>
                          <TableCell align="right">{formatCurrency(row.invested)}</TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: row.gainLoss >= 0 ? 'success.main' : 'error.main',
                              fontWeight: 'medium'
                            }}
                          >
                            {formatCurrency(row.gainLoss)}
                          </TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: row.gainLossPercentage >= 0 ? 'success.main' : 'error.main',
                              fontWeight: 'medium'
                            }}
                          >
                            {row.gainLossPercentage >= 0 ? '+' : ''}{row.gainLossPercentage.toFixed(2)}%
                          </TableCell>
                          <TableCell align="right">{row.percentage.toFixed(2)}%</TableCell>
                        </TableRow>
                      ))}
                      <TableRow sx={{ backgroundColor: 'action.hover' }}>
                        <TableCell><strong>Total</strong></TableCell>
                        <TableCell align="right"><strong>{(assets || []).length}</strong></TableCell>
                        <TableCell align="right"><strong>{formatCurrency(totalValue)}</strong></TableCell>
                        <TableCell align="right">
                          <strong>
                            {formatCurrency(allocationData.reduce((sum, row) => sum + row.invested, 0))}
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
                            {formatCurrency(totalValue - allocationData.reduce((sum, row) => sum + row.invested, 0))}
                          </strong>
                        </TableCell>
                        <TableCell align="right">
                          <strong>
                            {allocationData.reduce((sum, row) => sum + row.invested, 0) > 0
                              ? `${((totalValue - allocationData.reduce((sum, row) => sum + row.invested, 0)) /
                                  allocationData.reduce((sum, row) => sum + row.invested, 0) * 100).toFixed(2)}%`
                              : '0.00%'}
                          </strong>
                        </TableCell>
                        <TableCell align="right"><strong>100.00%</strong></TableCell>
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
