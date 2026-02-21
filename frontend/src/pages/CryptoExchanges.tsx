import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  FormControlLabel,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { cryptoExchangesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';

interface CryptoExchange {
  id: number;
  name: string;
  display_label: string;
  exchange_type: string;
  website: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string | null;
}

const CryptoExchanges: React.FC = () => {
  const { notify } = useNotification();
  const [exchanges, setExchanges] = useState<CryptoExchange[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingExchange, setEditingExchange] = useState<CryptoExchange | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    display_label: '',
    name: '',
    exchange_type: 'exchange' as string,
    website: '',
    sort_order: 0,
    is_active: true,
  });

  useEffect(() => {
    fetchExchanges();
  }, []);

  const fetchExchanges = async () => {
    try {
      setLoading(true);
      const data = await cryptoExchangesAPI.getAll();
      setExchanges(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch crypto exchanges'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (exchange?: CryptoExchange) => {
    if (exchange) {
      setEditingExchange(exchange);
      setFormData({
        display_label: exchange.display_label,
        name: exchange.name,
        exchange_type: exchange.exchange_type,
        website: exchange.website || '',
        sort_order: exchange.sort_order,
        is_active: exchange.is_active,
      });
    } else {
      setEditingExchange(null);
      setFormData({
        display_label: '',
        name: '',
        exchange_type: 'exchange',
        website: '',
        sort_order: 0,
        is_active: true,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingExchange(null);
  };

  const handleDisplayLabelChange = (value: string) => {
    const autoName = value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    setFormData({
      ...formData,
      display_label: value,
      // Only auto-generate name if not editing
      name: editingExchange ? formData.name : autoName,
    });
  };

  const handleSubmit = async () => {
    if (!formData.display_label.trim()) {
      notify.error('Display label is required');
      return;
    }
    try {
      setSubmitting(true);
      if (editingExchange) {
        await cryptoExchangesAPI.update(editingExchange.id, {
          display_label: formData.display_label.trim(),
          exchange_type: formData.exchange_type,
          website: formData.website.trim() || null,
          sort_order: formData.sort_order,
          is_active: formData.is_active,
        });
        notify.success('Exchange updated successfully');
      } else {
        await cryptoExchangesAPI.create({
          display_label: formData.display_label.trim(),
          name: formData.name.trim() || undefined,
          exchange_type: formData.exchange_type,
          website: formData.website.trim() || null,
          sort_order: formData.sort_order,
        });
        notify.success('Exchange added successfully');
      }
      handleCloseDialog();
      fetchExchanges();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save exchange'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (exchange: CryptoExchange) => {
    if (!window.confirm(`Delete "${exchange.display_label}"? This will fail if accounts are linked to it.`)) return;
    try {
      await cryptoExchangesAPI.delete(exchange.id);
      notify.success('Exchange deleted successfully');
      fetchExchanges();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete exchange'));
    }
  };

  const totalExchanges = exchanges.length;
  const activeExchanges = exchanges.filter((e) => e.is_active).length;
  const exchangeCount = exchanges.filter((e) => e.exchange_type === 'exchange').length;
  const walletCount = exchanges.filter((e) => e.exchange_type === 'wallet').length;

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Crypto Exchanges / Wallets</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add Exchange
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total</Typography>
              <Typography variant="h4">{totalExchanges}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Active</Typography>
              <Typography variant="h4">{activeExchanges}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Exchanges</Typography>
              <Typography variant="h4">{exchangeCount}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Wallets</Typography>
              <Typography variant="h4">{walletCount}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Display Label</strong></TableCell>
              <TableCell><strong>Type</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
              <TableCell align="right"><strong>Sort Order</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {exchanges.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No exchanges found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              exchanges.map((exchange) => (
                <TableRow key={exchange.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CompanyIcon website={exchange.website} name={exchange.display_label} />
                      <Typography variant="body2" fontFamily="monospace">{exchange.name}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{exchange.display_label}</TableCell>
                  <TableCell>
                    <Chip
                      label={exchange.exchange_type === 'wallet' ? 'Wallet' : 'Exchange'}
                      color={exchange.exchange_type === 'wallet' ? 'secondary' : 'primary'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={exchange.is_active ? 'Active' : 'Inactive'}
                      color={exchange.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">{exchange.sort_order}</TableCell>
                  <TableCell align="center">
                    <IconButton size="small" color="primary" onClick={() => handleOpenDialog(exchange)} title="Edit">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(exchange)} title="Delete">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingExchange ? 'Edit Exchange' : 'Add Exchange'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Display Label"
              value={formData.display_label}
              onChange={(e) => handleDisplayLabelChange(e.target.value)}
              fullWidth
              required
              helperText="The display name shown in dropdowns"
            />
            <TextField
              label="Name (key)"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              disabled={!!editingExchange}
              helperText={editingExchange ? 'Name cannot be changed after creation' : 'Auto-generated from display label (lowercase, no spaces)'}
              inputProps={{ style: { fontFamily: 'monospace' } }}
            />
            <TextField
              select
              label="Type"
              value={formData.exchange_type}
              onChange={(e) => setFormData({ ...formData, exchange_type: e.target.value })}
              fullWidth
            >
              <MenuItem value="exchange">Exchange</MenuItem>
              <MenuItem value="wallet">Wallet</MenuItem>
            </TextField>
            <TextField
              label="Website Domain"
              value={formData.website}
              onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              fullWidth
              placeholder="e.g. binance.com"
              helperText="Used to fetch the company icon (favicon)"
            />
            <TextField
              label="Sort Order"
              type="number"
              value={formData.sort_order}
              onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
              fullWidth
              helperText="Lower numbers appear first"
            />
            {editingExchange && (
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                }
                label="Active"
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={submitting || !formData.display_label.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : editingExchange ? <EditIcon /> : <AddIcon />}
          >
            {submitting ? 'Saving...' : editingExchange ? 'Update' : 'Add Exchange'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CryptoExchanges;
