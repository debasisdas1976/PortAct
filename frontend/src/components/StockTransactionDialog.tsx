import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Paper,
  Collapse,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { transactionsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface StockTransactionDialogProps {
  open: boolean;
  onClose: () => void;
  onTransactionsChanged: () => void;
  stock: {
    id: number;
    name: string;
    symbol: string;
    quantity: number;
    current_price: number;
    current_value: number;
    xirr?: number | null;
  } | null;
}

interface TransactionRow {
  id: number;
  transaction_type: string;
  transaction_date: string;
  quantity: number;
  price_per_unit: number;
  total_amount: number;
  fees: number;
  taxes: number;
  description?: string;
  notes?: string;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value);

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

const txnTypeLabel = (type: string) => type.toUpperCase();

const txnTypeColor = (type: string): 'success' | 'error' | 'info' | 'default' => {
  const colors: Record<string, 'success' | 'error' | 'info' | 'default'> = {
    buy: 'success',
    sell: 'error',
    dividend: 'info',
  };
  return colors[type] || 'default';
};

const StockTransactionDialog: React.FC<StockTransactionDialogProps> = ({
  open,
  onClose,
  onTransactionsChanged,
  stock,
}) => {
  const { notify } = useNotification();
  const [transactions, setTransactions] = useState<TransactionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    transaction_type: 'buy',
    transaction_date: new Date().toISOString().slice(0, 10),
    quantity: 0,
    price_per_unit: 0,
    total_amount: 0,
    fees: 0,
    taxes: 0,
    notes: '',
  });

  const resetForm = () => {
    setFormData({
      transaction_type: 'buy',
      transaction_date: new Date().toISOString().slice(0, 10),
      quantity: 0,
      price_per_unit: 0,
      total_amount: 0,
      fees: 0,
      taxes: 0,
      notes: '',
    });
  };

  const fetchTransactions = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    try {
      const data = await transactionsAPI.getAll({ asset_id: stock.id, limit: 500 });
      setTransactions(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load transactions'));
    } finally {
      setLoading(false);
    }
  }, [stock, notify]);

  useEffect(() => {
    if (open && stock) {
      fetchTransactions();
      setShowAddForm(false);
      resetForm();
    }
  }, [open, stock, fetchTransactions]);

  // Tally calculation
  const totalBuyQty = transactions
    .filter((t) => t.transaction_type === 'buy')
    .reduce((sum, t) => sum + (t.quantity || 0), 0);

  const totalSellQty = transactions
    .filter((t) => t.transaction_type === 'sell')
    .reduce((sum, t) => sum + (t.quantity || 0), 0);

  const netTransactionQty = totalBuyQty - totalSellQty;
  const stockQty = stock?.quantity || 0;
  const tallies = transactions.length > 0 && Math.abs(netTransactionQty - stockQty) < 0.0001;
  const hasMismatch = transactions.length > 0 && !tallies;
  const noTransactions = transactions.length === 0;

  // Auto-calc total_amount when quantity or price changes
  const handleFormChange = (field: string, value: string | number) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };
      if (field === 'quantity' || field === 'price_per_unit') {
        const qty = field === 'quantity' ? (Number(value) || 0) : prev.quantity;
        const price = field === 'price_per_unit' ? (Number(value) || 0) : prev.price_per_unit;
        updated.total_amount = Math.round(qty * price * 100) / 100;
      }
      return updated;
    });
  };

  const handleAddTransaction = async () => {
    if (!stock) return;
    if (!formData.transaction_date) {
      notify.error('Transaction date is required');
      return;
    }
    if (formData.quantity <= 0 && formData.transaction_type !== 'dividend') {
      notify.error('Quantity must be greater than 0');
      return;
    }
    if (formData.total_amount <= 0) {
      notify.error('Total amount must be greater than 0');
      return;
    }

    setSubmitting(true);
    try {
      await transactionsAPI.create({
        asset_id: stock.id,
        transaction_type: formData.transaction_type,
        transaction_date: new Date(formData.transaction_date).toISOString(),
        quantity: formData.quantity,
        price_per_unit: formData.price_per_unit,
        total_amount: formData.total_amount,
        fees: formData.fees,
        taxes: formData.taxes,
        notes: formData.notes || undefined,
      });
      notify.success('Transaction added');
      setShowAddForm(false);
      resetForm();
      await fetchTransactions();
      onTransactionsChanged();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to add transaction'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTransaction = async (txId: number) => {
    if (!window.confirm('Delete this transaction? This will recalculate XIRR.')) return;
    try {
      await transactionsAPI.delete(txId);
      notify.success('Transaction deleted');
      await fetchTransactions();
      onTransactionsChanged();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete transaction'));
    }
  };

  if (!stock) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Transactions: {stock.symbol || stock.name}
        {stock.symbol && stock.name !== stock.symbol && (
          <Typography variant="body2" color="text.secondary">{stock.name}</Typography>
        )}
      </DialogTitle>

      <DialogContent dividers>
        {/* Status Section */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
          <Box>
            <Typography variant="caption" color="text.secondary">Stock Qty</Typography>
            <Typography variant="body1" fontWeight="bold">{stockQty.toFixed(4)}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Txn Net Qty</Typography>
            <Typography variant="body1" fontWeight="bold">
              {transactions.length > 0 ? netTransactionQty.toFixed(4) : '—'}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Current Value</Typography>
            <Typography variant="body1" fontWeight="bold">{formatCurrency(stock.current_value)}</Typography>
          </Box>
          {stock.xirr != null && (
            <Box>
              <Typography variant="caption" color="text.secondary">XIRR</Typography>
              <Box>
                <Chip
                  label={`${stock.xirr >= 0 ? '+' : ''}${stock.xirr.toFixed(2)}%`}
                  color={stock.xirr >= 0 ? 'success' : 'error'}
                  size="small"
                />
              </Box>
            </Box>
          )}
        </Box>

        {/* Tally Status Alert */}
        {tallies && (
          <Alert icon={<CheckCircleIcon />} severity="success" sx={{ mb: 2 }}>
            Quantities match. XIRR is calculated from transaction history.
          </Alert>
        )}
        {hasMismatch && (
          <Alert icon={<WarningIcon />} severity="warning" sx={{ mb: 2 }}>
            Quantity mismatch: stock has <strong>{stockQty.toFixed(4)}</strong> shares,
            but transactions net to <strong>{netTransactionQty.toFixed(4)}</strong>.
            {netTransactionQty < stockQty
              ? ` Add ${(stockQty - netTransactionQty).toFixed(4)} more shares via buy transactions.`
              : ` Transactions exceed stock quantity by ${(netTransactionQty - stockQty).toFixed(4)}.`}
          </Alert>
        )}
        {noTransactions && !loading && (
          <Alert icon={<InfoIcon />} severity="info" sx={{ mb: 2 }}>
            No transactions recorded. Add buy transactions to calculate XIRR.
          </Alert>
        )}

        <Divider sx={{ mb: 2 }} />

        {/* Transaction Table */}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        ) : transactions.length > 0 ? (
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Qty</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">Total</TableCell>
                  <TableCell align="right">Fees</TableCell>
                  <TableCell align="right">Taxes</TableCell>
                  <TableCell align="center" width={50}></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((txn) => (
                  <TableRow key={txn.id} hover>
                    <TableCell>{formatDate(txn.transaction_date)}</TableCell>
                    <TableCell>
                      <Chip
                        label={txnTypeLabel(txn.transaction_type)}
                        color={txnTypeColor(txn.transaction_type)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">{txn.quantity?.toFixed(4)}</TableCell>
                    <TableCell align="right">{formatCurrency(txn.price_per_unit)}</TableCell>
                    <TableCell align="right">{formatCurrency(txn.total_amount)}</TableCell>
                    <TableCell align="right">{txn.fees > 0 ? formatCurrency(txn.fees) : '—'}</TableCell>
                    <TableCell align="right">{txn.taxes > 0 ? formatCurrency(txn.taxes) : '—'}</TableCell>
                    <TableCell align="center">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteTransaction(txn.id)}
                        title="Delete transaction"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : !loading ? (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: 'center', py: 2 }}>
            No transactions found for this stock.
          </Typography>
        ) : null}

        {/* Add Transaction Section */}
        <Button
          variant="outlined"
          startIcon={showAddForm ? <ExpandLessIcon /> : <AddIcon />}
          onClick={() => {
            setShowAddForm(!showAddForm);
            if (!showAddForm) resetForm();
          }}
          sx={{ mb: 1 }}
        >
          {showAddForm ? 'Cancel' : 'Add Transaction'}
        </Button>

        <Collapse in={showAddForm}>
          <Paper variant="outlined" sx={{ p: 2, mt: 1 }}>
            <Typography variant="subtitle2" gutterBottom>New Transaction</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  select
                  label="Type"
                  value={formData.transaction_type}
                  onChange={(e) => handleFormChange('transaction_type', e.target.value)}
                  sx={{ minWidth: 140 }}
                >
                  <MenuItem value="buy">Buy</MenuItem>
                  <MenuItem value="sell">Sell</MenuItem>
                  <MenuItem value="dividend">Dividend</MenuItem>
                </TextField>
                <TextField
                  label="Date"
                  type="date"
                  value={formData.transaction_date}
                  onChange={(e) => handleFormChange('transaction_date', e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  required
                  sx={{ flex: 1 }}
                />
              </Box>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="Quantity"
                  type="number"
                  value={formData.quantity || ''}
                  onChange={(e) => handleFormChange('quantity', parseFloat(e.target.value) || 0)}
                  sx={{ flex: 1 }}
                  inputProps={{ min: 0, step: 'any' }}
                />
                <TextField
                  label="Price Per Unit"
                  type="number"
                  value={formData.price_per_unit || ''}
                  onChange={(e) => handleFormChange('price_per_unit', parseFloat(e.target.value) || 0)}
                  sx={{ flex: 1 }}
                  inputProps={{ min: 0, step: 'any' }}
                />
                <TextField
                  label="Total Amount"
                  type="number"
                  value={formData.total_amount || ''}
                  onChange={(e) => handleFormChange('total_amount', parseFloat(e.target.value) || 0)}
                  sx={{ flex: 1 }}
                  inputProps={{ min: 0, step: 'any' }}
                  helperText="Auto-calculated (Qty x Price)"
                />
              </Box>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="Fees"
                  type="number"
                  value={formData.fees || ''}
                  onChange={(e) => handleFormChange('fees', parseFloat(e.target.value) || 0)}
                  sx={{ flex: 1 }}
                  inputProps={{ min: 0, step: 'any' }}
                />
                <TextField
                  label="Taxes"
                  type="number"
                  value={formData.taxes || ''}
                  onChange={(e) => handleFormChange('taxes', parseFloat(e.target.value) || 0)}
                  sx={{ flex: 1 }}
                  inputProps={{ min: 0, step: 'any' }}
                />
                <TextField
                  label="Notes"
                  value={formData.notes}
                  onChange={(e) => handleFormChange('notes', e.target.value)}
                  sx={{ flex: 2 }}
                />
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Button onClick={() => { setShowAddForm(false); resetForm(); }}>Cancel</Button>
                <Button
                  variant="contained"
                  onClick={handleAddTransaction}
                  disabled={submitting}
                  startIcon={submitting ? <CircularProgress size={18} /> : <AddIcon />}
                >
                  {submitting ? 'Adding...' : 'Add Transaction'}
                </Button>
              </Box>
            </Box>
          </Paper>
        </Collapse>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default StockTransactionDialog;
