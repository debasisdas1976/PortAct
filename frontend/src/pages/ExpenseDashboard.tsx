import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography,
  Alert,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton
} from '@mui/material';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import axios from 'axios';

interface CategoryData {
  name: string;
  icon: string;
  color: string;
  amount: number;
}

interface MonthlyData {
  month: string;
  year: number;
  month_num: number;
  categories: CategoryData[];
  total: number;
}

interface CategoryTotal {
  id: number | null;
  name: string;
  icon: string;
  color: string;
  total: number;
}

interface DashboardData {
  monthly_data: MonthlyData[];
  category_totals: CategoryTotal[];
  total_expenses: number;
  months_count: number;
}

const ExpenseDashboard: React.FC = () => {
  const selectedPortfolioId = useSelectedPortfolio();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();
  const [viewMode, setViewMode] = useState<'range' | 'single'>('range');
  const [monthsToShow, setMonthsToShow] = useState(6);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);

  useEffect(() => {
    fetchDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monthsToShow, selectedYear, selectedMonth, viewMode, selectedPortfolioId]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');

      let url = 'http://localhost:8000/api/v1/expenses/dashboard/monthly-by-category';
      if (viewMode === 'single') {
        url += `?months=1&year=${selectedYear}&month=${selectedMonth}`;
      } else {
        url += `?months=${monthsToShow}`;
      }
      if (selectedPortfolioId) {
        url += `&portfolio_id=${selectedPortfolioId}`;
      }
      
      const response = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  // Prepare data for stacked bar chart (monthly expenses by category)
  const prepareStackedBarData = () => {
    if (!data) return [];

    return data.monthly_data.map(month => {
      const monthData: any = { month: month.month };
      month.categories.forEach(cat => {
        monthData[cat.name] = cat.amount;
      });
      return monthData;
    });
  };

  // Prepare data for line chart (total monthly expenses trend)
  const prepareLineData = () => {
    if (!data) return [];

    return data.monthly_data.map(month => ({
      month: month.month,
      total: month.total
    }));
  };

  // Prepare data for pie chart (category distribution)
  const preparePieData = () => {
    if (!data) return [];

    return data.category_totals.map(cat => ({
      name: `${cat.icon} ${cat.name}`,
      value: cat.total,
      color: cat.color
    }));
  };

  // Get unique categories for the stacked bar chart
  const getUniqueCategories = () => {
    if (!data) return [];

    const categoriesSet = new Set<string>();
    data.monthly_data.forEach(month => {
      month.categories.forEach(cat => {
        categoriesSet.add(cat.name);
      });
    });
    return Array.from(categoriesSet);
  };

  // Get category color
  const getCategoryColor = (categoryName: string) => {
    if (!data) return '#999999';

    for (const month of data.monthly_data) {
      const cat = month.categories.find(c => c.name === categoryName);
      if (cat) return cat.color;
    }
    return '#999999';
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            {label}
          </Typography>
          {payload.map((entry: any, index: number) => (
            <Typography key={index} variant="body2" sx={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value)}
            </Typography>
          ))}
          <Typography variant="body2" sx={{ fontWeight: 'bold', mt: 1 }}>
            Total: {formatCurrency(payload.reduce((sum: number, entry: any) => sum + entry.value, 0))}
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  const PieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <Paper sx={{ p: 2 }}>
          <Typography variant="body2">
            {payload[0].name}
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            {formatCurrency(payload[0].value)}
          </Typography>
          <Typography variant="caption" color="textSecondary">
            {((payload[0].value / data!.total_expenses) * 100).toFixed(1)}%
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!data || data.monthly_data.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          No expense data available. Upload bank statements to see your expense dashboard.
        </Alert>
      </Box>
    );
  }

  const stackedBarData = prepareStackedBarData();
  const lineData = prepareLineData();
  const pieData = preparePieData();
  const categories = getUniqueCategories();

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4">Expense Dashboard</Typography>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, newMode) => {
              if (newMode !== null) {
                setViewMode(newMode);
              }
            }}
            size="small"
          >
            <ToggleButton value="range">Date Range</ToggleButton>
            <ToggleButton value="single">Single Month</ToggleButton>
          </ToggleButtonGroup>

          {viewMode === 'range' ? (
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Time Period</InputLabel>
              <Select
                value={monthsToShow}
                label="Time Period"
                onChange={(e) => setMonthsToShow(Number(e.target.value))}
                size="small"
              >
                <MenuItem value={3}>Last 3 Months</MenuItem>
                <MenuItem value={6}>Last 6 Months</MenuItem>
                <MenuItem value={12}>Last 12 Months</MenuItem>
                <MenuItem value={24}>Last 24 Months</MenuItem>
              </Select>
            </FormControl>
          ) : (
            <>
              <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Year</InputLabel>
                <Select
                  value={selectedYear}
                  label="Year"
                  onChange={(e) => setSelectedYear(Number(e.target.value))}
                  size="small"
                >
                  {Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - i).map(year => (
                    <MenuItem key={year} value={year}>{year}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl sx={{ minWidth: 140 }}>
                <InputLabel>Month</InputLabel>
                <Select
                  value={selectedMonth}
                  label="Month"
                  onChange={(e) => setSelectedMonth(Number(e.target.value))}
                  size="small"
                >
                  <MenuItem value={1}>January</MenuItem>
                  <MenuItem value={2}>February</MenuItem>
                  <MenuItem value={3}>March</MenuItem>
                  <MenuItem value={4}>April</MenuItem>
                  <MenuItem value={5}>May</MenuItem>
                  <MenuItem value={6}>June</MenuItem>
                  <MenuItem value={7}>July</MenuItem>
                  <MenuItem value={8}>August</MenuItem>
                  <MenuItem value={9}>September</MenuItem>
                  <MenuItem value={10}>October</MenuItem>
                  <MenuItem value={11}>November</MenuItem>
                  <MenuItem value={12}>December</MenuItem>
                </Select>
              </FormControl>
            </>
          )}
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Expenses
              </Typography>
              <Typography variant="h4" color="error.main">
                {formatCurrency(data.total_expenses)}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Over {data.months_count} months
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Average Monthly Expense
              </Typography>
              <Typography variant="h4" color="primary.main">
                {formatCurrency(data.total_expenses / data.months_count)}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Per month
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Top Category
              </Typography>
              <Typography variant="h5">
                {data.category_totals[0]?.icon} {data.category_totals[0]?.name}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {formatCurrency(data.category_totals[0]?.total || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Monthly Expenses Trend */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Monthly Expenses Trend
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={lineData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`} />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#f44336"
              strokeWidth={2}
              name="Total Expenses"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Paper>

      {/* Expenses by Category (Stacked Bar Chart) */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Monthly Expenses by Category
        </Typography>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={stackedBarData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`} />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            {categories.map((category) => (
              <Bar
                key={category}
                dataKey={category}
                stackId="a"
                fill={getCategoryColor(category)}
                name={category}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      {/* Category Distribution */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Category Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Top Categories
            </Typography>
            <Box sx={{ mt: 2 }}>
              {data.category_totals.slice(0, 10).map((category, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 2,
                    pb: 2,
                    borderBottom: index < 9 ? '1px solid #eee' : 'none'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="h6">{category.icon}</Typography>
                    <Box>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        {category.name}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {((category.total / data.total_expenses) * 100).toFixed(1)}% of total
                      </Typography>
                    </Box>
                  </Box>
                  <Typography variant="body1" sx={{ fontWeight: 600, color: category.color }}>
                    {formatCurrency(category.total)}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ExpenseDashboard;

// Made with Bob