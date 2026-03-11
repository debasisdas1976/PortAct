import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  TextField,
  Typography,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Checkbox,
  Tooltip
} from '@mui/material';
import {
  FilterList as FilterIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Add as AddIcon,
  DeleteSweep as DeleteSweepIcon
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { AppDispatch, RootState } from '../store';
import { fetchPortfolios } from '../store/slices/portfolioSlice';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import api from '../services/api';

interface Expense {
  id: number;
  bank_account_id?: number;
  transaction_date: string;
  description: string;
  amount: number;
  transaction_type: string;
  payment_method?: string;
  merchant_name?: string;
  reference_number?: string;
  notes?: string;
  tags?: string;
  category_id?: number;
  category_name?: string;
  category_icon?: string;
  category_color?: string;
  bank_account_name?: string;
  is_categorized: boolean;
}

interface BankAccount {
  id: number;
  bank_name: string;
  nickname?: string;
  account_number: string;
}

interface Category {
  id: number;
  name: string;
  icon?: string;
  color?: string;
  is_income: boolean;
}

const Expenses: React.FC = () => {
  const { notify } = useNotification();
  const dispatch = useDispatch<AppDispatch>();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [uploadPortfolioId, setUploadPortfolioId] = useState<number | ''>('' as number | '');
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [summary, setSummary] = useState({ totalIncome: 0, totalExpense: 0, transactionCount: 0 });
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  // Sorting
  const [orderBy, setOrderBy] = useState<string>('transaction_date');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  
  // Filters
  const [filters, setFilters] = useState({
    bank_account_id: '',
    category_id: '',
    transaction_type: '',
    start_date: '',
    end_date: '',
    search_query: ''
  });

  // Upload dialog
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedBankAccount, setSelectedBankAccount] = useState('');
  const [autoCategorize, setAutoCategorize] = useState(true);

  // Create/Edit expense dialog
  const [expenseDialogOpen, setExpenseDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [expenseForm, setExpenseForm] = useState({
    bank_account_id: '' as number | '',
    transaction_date: new Date().toISOString().split('T')[0],
    transaction_type: 'debit',
    amount: '',
    description: '',
    merchant_name: '',
    category_id: '' as number | '',
    payment_method: '',
    reference_number: '',
    notes: '',
    tags: ''
  });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Multi-select
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    dispatch(fetchPortfolios());
  }, [dispatch]);

  useEffect(() => {
    setSelectedIds(new Set());
    fetchExpenses();
  }, [filters, page, rowsPerPage, orderBy, order, selectedPortfolioId]);

  useEffect(() => {
    fetchSummary();
    fetchBankAccounts();
    fetchCategories();
  }, [filters, selectedPortfolioId]);

  const fetchExpenses = async () => {
    try {
      const params = new URLSearchParams();

      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      if (selectedPortfolioId) {
        params.append('portfolio_id', String(selectedPortfolioId));
      }

      // Add pagination parameters
      params.append('skip', (page * rowsPerPage).toString());
      params.append('limit', rowsPerPage.toString());

      // Add sorting parameters
      params.append('order_by', orderBy);
      params.append('order', order);

      const response = await api.get(`/expenses/?${params.toString()}`);
      
      // Handle new paginated response format
      if (response.data.items) {
        setExpenses(response.data.items);
        setTotalCount(response.data.total);
      } else {
        // Fallback for old format
        setExpenses(response.data);
        setTotalCount(response.data.length);
      }
    } catch (err) {
      setError('Failed to fetch expenses');
    }
  };

  const fetchSummary = async () => {
    try {
      const params = new URLSearchParams();

      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      if (selectedPortfolioId) {
        params.append('portfolio_id', String(selectedPortfolioId));
      }

      const response = await api.get(`/expenses/summary?${params.toString()}`);
      
      // Backend returns: total_credits (income), total_debits (expenses), total_expenses (count)
      setSummary({
        totalIncome: response.data.total_credits || 0,
        totalExpense: response.data.total_debits || 0,
        transactionCount: response.data.total_expenses || 0
      });
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load expense summary'));
    }
  };

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
    setPage(0); // Reset to first page when sorting changes
  };

  const createSortHandler = (property: string) => () => {
    handleRequestSort(property);
  };

  const fetchBankAccounts = async () => {
    try {
      const response = await api.get('/bank-accounts/');
      setBankAccounts(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load bank accounts'));
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await api.get('/expense-categories/');
      setCategories(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load categories'));
    }
  };

  const handleUploadStatement = async () => {
    if (!selectedFile || !selectedBankAccount) {
      setError('Please select a file and bank account');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('bank_account_id', selectedBankAccount);
    formData.append('auto_categorize', autoCategorize.toString());
    if (uploadPortfolioId) {
      formData.append('portfolio_id', String(uploadPortfolioId));
    }

    try {
      const response = await api.post('/bank-statements/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setSuccess(
        `Successfully imported ${response.data.summary.imported} transactions. ` +
        `Categorized: ${response.data.summary.categorized}, ` +
        `Duplicates skipped: ${response.data.summary.duplicates}`
      );
      setUploadDialogOpen(false);
      setSelectedFile(null);
      setSelectedBankAccount('');
      fetchExpenses();
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else if (Array.isArray(errorDetail)) {
        setError(errorDetail.map((e: any) => e.msg).join(', '));
      } else {
        setError('Failed to upload statement');
      }
    } finally {
      setLoading(false);
    }
  };
  const handleCategoryChange = async (expenseId: number, categoryId: number) => {
    try {
      await api.put(`/expenses/${expenseId}`, {
        category_id: categoryId || null,
        is_categorized: categoryId ? true : false
      });
      
      // Refresh expenses to show updated category
      fetchExpenses();
      fetchSummary();
      setSuccess('Category updated successfully');
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setError('Failed to update category');
      setTimeout(() => setError(''), 3000);
    }
  };


  const handleDeleteExpense = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this expense?')) return;

    try {
      await api.delete(`/expenses/${id}`);
      setSuccess('Expense deleted successfully');
      fetchExpenses();
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else if (Array.isArray(errorDetail)) {
        setError(errorDetail.map((e: any) => e.msg).join(', '));
      } else {
        setError('Failed to delete expense');
      }
    }
  };

  const handleToggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleToggleSelectAll = () => {
    if (selectedIds.size === expenses.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(expenses.map(e => e.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedIds.size} transaction(s)?`)) return;

    try {
      const response = await api.post('/expenses/bulk-delete', Array.from(selectedIds));
      setSuccess(`Deleted ${response.data.deleted} transaction(s)`);
      setSelectedIds(new Set());
      fetchExpenses();
      fetchSummary();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to delete transactions'));
    }
  };

  const handleOpenExpenseDialog = (expense?: Expense) => {
    if (expense) {
      setEditingExpense(expense);
      setExpenseForm({
        bank_account_id: expense.bank_account_id || ('' as number | ''),
        transaction_date: expense.transaction_date ? expense.transaction_date.split('T')[0] : new Date().toISOString().split('T')[0],
        transaction_type: expense.transaction_type || 'debit',
        amount: String(expense.amount || ''),
        description: expense.description || '',
        merchant_name: expense.merchant_name || '',
        category_id: expense.category_id || ('' as number | ''),
        payment_method: expense.payment_method || '',
        reference_number: expense.reference_number || '',
        notes: expense.notes || '',
        tags: expense.tags || ''
      });
    } else {
      setEditingExpense(null);
      setExpenseForm({
        bank_account_id: bankAccounts.length === 1 ? bankAccounts[0].id : '' as number | '',
        transaction_date: new Date().toISOString().split('T')[0],
        transaction_type: 'debit',
        amount: '',
        description: '',
        merchant_name: '',
        category_id: '' as number | '',
        payment_method: '',
        reference_number: '',
        notes: '',
        tags: ''
      });
    }
    setExpenseDialogOpen(true);
  };

  const handleCloseExpenseDialog = () => {
    setExpenseDialogOpen(false);
    setEditingExpense(null);
  };

  const handleSaveExpense = async () => {
    if (!expenseForm.bank_account_id || !expenseForm.description || !expenseForm.amount) {
      setError('Bank account, description and amount are required');
      return;
    }

    setLoading(true);
    try {
      const payload: any = {
        bank_account_id: Number(expenseForm.bank_account_id),
        transaction_date: new Date(expenseForm.transaction_date).toISOString(),
        transaction_type: expenseForm.transaction_type,
        amount: parseFloat(expenseForm.amount),
        description: expenseForm.description,
        portfolio_id: selectedPortfolioId || undefined
      };
      if (expenseForm.merchant_name) payload.merchant_name = expenseForm.merchant_name;
      if (expenseForm.category_id) payload.category_id = Number(expenseForm.category_id);
      if (expenseForm.payment_method) payload.payment_method = expenseForm.payment_method;
      if (expenseForm.reference_number) payload.reference_number = expenseForm.reference_number;
      if (expenseForm.notes) payload.notes = expenseForm.notes;
      if (expenseForm.tags) payload.tags = expenseForm.tags;

      if (editingExpense) {
        await api.put(`/expenses/${editingExpense.id}`, payload);
        setSuccess('Expense updated successfully');
      } else {
        await api.post('/expenses/', payload);
        setSuccess('Expense created successfully');
      }
      handleCloseExpenseDialog();
      fetchExpenses();
      fetchSummary();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(getErrorMessage(err, `Failed to ${editingExpense ? 'update' : 'create'} expense`));
      setTimeout(() => setError(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getTransactionTypeColor = (type: string) => {
    switch (type) {
      case 'credit': return 'success';
      case 'debit': return 'error';
      case 'transfer': return 'info';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Expenses</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => handleOpenExpenseDialog()}
          >
            Add Expense
          </Button>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => {
              setUploadPortfolioId(selectedPortfolioId || (portfolios.length === 1 ? portfolios[0].id : '') as any);
              setUploadDialogOpen(true);
            }}
          >
            Upload Statement
          </Button>
          {selectedIds.size > 0 && (
            <Tooltip title={`Delete ${selectedIds.size} selected`}>
              <Button
                variant="contained"
                color="error"
                startIcon={<DeleteSweepIcon />}
                onClick={handleBulkDelete}
              >
                Delete ({selectedIds.size})
              </Button>
            </Tooltip>
          )}
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Income
              </Typography>
              <Typography variant="h5" color="success.main">
                {formatCurrency(summary.totalIncome)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Expenses
              </Typography>
              <Typography variant="h5" color="error.main">
                {formatCurrency(summary.totalExpense)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Net Savings
              </Typography>
              <Typography
                variant="h5"
                color={(summary.totalIncome - summary.totalExpense) >= 0 ? 'success.main' : 'error.main'}
              >
                {formatCurrency(summary.totalIncome - summary.totalExpense)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Transactions
              </Typography>
              <Typography variant="h5">{totalCount}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FilterIcon /> Filters
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Bank Account</InputLabel>
              <Select
                value={filters.bank_account_id}
                label="Bank Account"
                onChange={(e) => setFilters({ ...filters, bank_account_id: e.target.value })}
              >
                <MenuItem value="">All</MenuItem>
                {bankAccounts.map((acc) => (
                  <MenuItem key={acc.id} value={acc.id}>
                    {acc.nickname || `${acc.bank_name} - ${acc.account_number.slice(-4)}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Category</InputLabel>
              <Select
                value={filters.category_id}
                label="Category"
                onChange={(e) => setFilters({ ...filters, category_id: e.target.value })}
              >
                <MenuItem value="">All</MenuItem>
                {categories.map((cat) => (
                  <MenuItem key={cat.id} value={cat.id}>
                    {cat.icon} {cat.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Type</InputLabel>
              <Select
                value={filters.transaction_type}
                label="Type"
                onChange={(e) => setFilters({ ...filters, transaction_type: e.target.value })}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="credit">Income</MenuItem>
                <MenuItem value="debit">Expense</MenuItem>
                <MenuItem value="transfer">Transfer</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              size="small"
              type="date"
              label="Start Date"
              InputLabelProps={{ shrink: true }}
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              size="small"
              type="date"
              label="End Date"
              InputLabelProps={{ shrink: true }}
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              size="small"
              label="Search (description, merchant, reference)"
              value={filters.search_query}
              onChange={(e) => setFilters({ ...filters, search_query: e.target.value })}
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Expenses Table */}
      <TableContainer component={Paper}>
        <Table sx={{ minWidth: 650 }}>
          <TableHead>
            <TableRow sx={{ backgroundColor: 'grey.100' }}>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={selectedIds.size > 0 && selectedIds.size < expenses.length}
                  checked={expenses.length > 0 && selectedIds.size === expenses.length}
                  onChange={handleToggleSelectAll}
                />
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'transaction_date'}
                  direction={orderBy === 'transaction_date' ? order : 'asc'}
                  onClick={createSortHandler('transaction_date')}
                >
                  Date
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'description'}
                  direction={orderBy === 'description' ? order : 'asc'}
                  onClick={createSortHandler('description')}
                >
                  Description
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'merchant_name'}
                  direction={orderBy === 'merchant_name' ? order : 'asc'}
                  onClick={createSortHandler('merchant_name')}
                >
                  Merchant
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'category_name'}
                  direction={orderBy === 'category_name' ? order : 'asc'}
                  onClick={createSortHandler('category_name')}
                >
                  Category
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'bank_account_name'}
                  direction={orderBy === 'bank_account_name' ? order : 'asc'}
                  onClick={createSortHandler('bank_account_name')}
                >
                  Bank Account
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'transaction_type'}
                  direction={orderBy === 'transaction_type' ? order : 'asc'}
                  onClick={createSortHandler('transaction_type')}
                >
                  Type
                </TableSortLabel>
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>
                <TableSortLabel
                  active={orderBy === 'amount'}
                  direction={orderBy === 'amount' ? order : 'asc'}
                  onClick={createSortHandler('amount')}
                >
                  Amount
                </TableSortLabel>
              </TableCell>
              <TableCell align="center" sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {expenses.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                  <Typography color="textSecondary">
                    No transactions found. Upload a bank statement to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              expenses.map((expense) => (
                <TableRow
                  key={expense.id}
                  selected={selectedIds.has(expense.id)}
                  sx={{
                    '&:hover': { backgroundColor: 'grey.50' },
                    '&:last-child td, &:last-child th': { border: 0 }
                  }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedIds.has(expense.id)}
                      onChange={() => handleToggleSelect(expense.id)}
                    />
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {formatDate(expense.transaction_date)}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 300 }}>
                    <Typography variant="body2" noWrap title={expense.description}>
                      {expense.description}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ maxWidth: 150 }}>
                    <Typography variant="body2" noWrap title={expense.merchant_name || '-'}>
                      {expense.merchant_name || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <FormControl size="small" fullWidth sx={{ minWidth: 180 }}>
                      <Select
                        value={expense.category_id || ''}
                        onChange={(e) => handleCategoryChange(expense.id, Number(e.target.value))}
                        displayEmpty
                        renderValue={(value) => {
                          if (!value) return <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><span>❓</span><span>Uncategorized</span></Box>;
                          const cat = categories.find(c => c.id === value);
                          if (cat) return <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><span>{cat.icon || '📁'}</span><span>{cat.name}</span></Box>;
                          return <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><span>📁</span><span>{expense.category_name || 'Unknown'}</span></Box>;
                        }}
                        sx={{
                          '& .MuiSelect-select': {
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1
                          }
                        }}
                      >
                        <MenuItem value="">
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <span>❓</span>
                            <span>Uncategorized</span>
                          </Box>
                        </MenuItem>
                        {categories
                          .filter(cat => {
                            // Always include the currently assigned category so it displays correctly
                            if (expense.category_id && cat.id === expense.category_id) return true;
                            return cat.is_income === (expense.transaction_type === 'credit');
                          })
                          .map((category) => (
                            <MenuItem key={category.id} value={category.id}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <span>{category.icon || '📁'}</span>
                                <span>{category.name}</span>
                              </Box>
                            </MenuItem>
                          ))}
                      </Select>
                    </FormControl>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap>
                      {expense.bank_account_name || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={expense.transaction_type}
                      size="small"
                      color={getTransactionTypeColor(expense.transaction_type)}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        color: expense.transaction_type === 'credit' ? 'success.main' :
                               expense.transaction_type === 'debit' ? 'error.main' : 'text.primary'
                      }}
                    >
                      {expense.transaction_type === 'credit' ? '+' : expense.transaction_type === 'debit' ? '-' : ''}
                      {formatCurrency(expense.amount)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenExpenseDialog(expense)}
                      sx={{ '&:hover': { backgroundColor: 'primary.light', color: 'white' } }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDeleteExpense(expense.id)}
                      sx={{ '&:hover': { backgroundColor: 'error.light', color: 'white' } }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={totalCount}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>

      {/* Create/Edit Expense Dialog */}
      <Dialog open={expenseDialogOpen} onClose={handleCloseExpenseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingExpense ? 'Edit Expense' : 'Add Expense'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <FormControl fullWidth required>
              <InputLabel>Bank Account</InputLabel>
              <Select
                value={expenseForm.bank_account_id}
                label="Bank Account"
                onChange={(e) => setExpenseForm({ ...expenseForm, bank_account_id: e.target.value as number })}
              >
                {bankAccounts.map((acc) => (
                  <MenuItem key={acc.id} value={acc.id}>
                    {acc.nickname || `${acc.bank_name} - ${acc.account_number.slice(-4)}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  required
                  type="date"
                  label="Date"
                  InputLabelProps={{ shrink: true }}
                  value={expenseForm.transaction_date}
                  onChange={(e) => setExpenseForm({ ...expenseForm, transaction_date: e.target.value })}
                />
              </Grid>
              <Grid item xs={6}>
                <FormControl fullWidth required>
                  <InputLabel>Type</InputLabel>
                  <Select
                    value={expenseForm.transaction_type}
                    label="Type"
                    onChange={(e) => setExpenseForm({ ...expenseForm, transaction_type: e.target.value, category_id: '' })}
                  >
                    <MenuItem value="debit">Debit (Expense)</MenuItem>
                    <MenuItem value="credit">Credit (Income)</MenuItem>
                    <MenuItem value="transfer">Transfer</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <TextField
              fullWidth
              required
              type="number"
              label="Amount"
              value={expenseForm.amount}
              onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
              inputProps={{ min: 0, step: '0.01' }}
            />

            <TextField
              fullWidth
              required
              label="Description"
              value={expenseForm.description}
              onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
              placeholder="e.g., Swiggy order, Rent payment"
            />

            <TextField
              fullWidth
              label="Merchant Name"
              value={expenseForm.merchant_name}
              onChange={(e) => setExpenseForm({ ...expenseForm, merchant_name: e.target.value })}
              placeholder="e.g., Swiggy, BigBasket"
            />

            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={expenseForm.category_id}
                label="Category"
                onChange={(e) => setExpenseForm({ ...expenseForm, category_id: e.target.value as number | '' })}
              >
                <MenuItem value="">Auto-detect</MenuItem>
                {categories
                  .filter(cat => cat.is_income === (expenseForm.transaction_type === 'credit'))
                  .map((cat) => (
                    <MenuItem key={cat.id} value={cat.id}>
                      {cat.icon || '📁'} {cat.name}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Payment Method</InputLabel>
              <Select
                value={expenseForm.payment_method}
                label="Payment Method"
                onChange={(e) => setExpenseForm({ ...expenseForm, payment_method: e.target.value })}
              >
                <MenuItem value="">Not specified</MenuItem>
                <MenuItem value="upi">UPI</MenuItem>
                <MenuItem value="debit_card">Debit Card</MenuItem>
                <MenuItem value="credit_card">Credit Card</MenuItem>
                <MenuItem value="net_banking">Net Banking</MenuItem>
                <MenuItem value="cash">Cash</MenuItem>
                <MenuItem value="cheque">Cheque</MenuItem>
                <MenuItem value="wallet">Wallet</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Reference Number"
              value={expenseForm.reference_number}
              onChange={(e) => setExpenseForm({ ...expenseForm, reference_number: e.target.value })}
            />

            <TextField
              fullWidth
              label="Notes"
              multiline
              rows={2}
              value={expenseForm.notes}
              onChange={(e) => setExpenseForm({ ...expenseForm, notes: e.target.value })}
            />

            <TextField
              fullWidth
              label="Tags"
              value={expenseForm.tags}
              onChange={(e) => setExpenseForm({ ...expenseForm, tags: e.target.value })}
              placeholder="Comma-separated tags"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseExpenseDialog}>Cancel</Button>
          <Button
            onClick={handleSaveExpense}
            variant="contained"
            disabled={loading || !expenseForm.bank_account_id || !expenseForm.description || !expenseForm.amount}
          >
            {loading ? 'Saving...' : editingExpense ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Bank Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <Alert severity="info">
              Supported formats: PDF, Excel (.xlsx, .xls)<br />
              Supported banks: ICICI, HDFC, IDFC First, SBI
            </Alert>

            <FormControl fullWidth>
              <InputLabel>Bank Account</InputLabel>
              <Select
                value={selectedBankAccount}
                label="Bank Account"
                onChange={(e) => setSelectedBankAccount(e.target.value)}
              >
                {bankAccounts.map((acc) => (
                  <MenuItem key={acc.id} value={acc.id}>
                    {acc.nickname || `${acc.bank_name} - ${acc.account_number.slice(-4)}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Portfolio</InputLabel>
              <Select
                value={uploadPortfolioId}
                label="Portfolio"
                onChange={(e) => setUploadPortfolioId(e.target.value as number | '')}
              >
                <MenuItem value="">Default Portfolio</MenuItem>
                {portfolios.map((p: any) => (
                  <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="outlined"
              component="label"
              fullWidth
            >
              {selectedFile ? selectedFile.name : 'Choose File'}
              <input
                type="file"
                hidden
                accept=".pdf,.xlsx,.xls"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
            </Button>

            <FormControl fullWidth>
              <InputLabel>Auto-Categorize</InputLabel>
              <Select
                value={autoCategorize ? 'yes' : 'no'}
                label="Auto-Categorize"
                onChange={(e) => setAutoCategorize(e.target.value === 'yes')}
              >
                <MenuItem value="yes">Yes - Automatically categorize expenses</MenuItem>
                <MenuItem value="no">No - Manual categorization</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUploadStatement}
            variant="contained"
            disabled={!selectedFile || !selectedBankAccount || loading}
          >
            {loading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Expenses;

// Made with Bob
