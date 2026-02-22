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
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Star as DefaultIcon,
} from '@mui/icons-material';
import { portfoliosAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../store';
import { fetchPortfolios } from '../store/slices/portfolioSlice';

interface Portfolio {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  asset_count: number;
  total_invested: number;
  total_current_value: number;
}

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

const Portfolios: React.FC = () => {
  const { notify } = useNotification();
  const dispatch = useDispatch<AppDispatch>();
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingPortfolio, setEditingPortfolio] = useState<Portfolio | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const data = await portfoliosAPI.getAll();
      setPortfolios(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch portfolios'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (portfolio?: Portfolio) => {
    if (portfolio) {
      setEditingPortfolio(portfolio);
      setFormData({ name: portfolio.name, description: portfolio.description || '' });
    } else {
      setEditingPortfolio(null);
      setFormData({ name: '', description: '' });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingPortfolio(null);
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      notify.error('Portfolio name is required');
      return;
    }
    try {
      setSubmitting(true);
      if (editingPortfolio) {
        await portfoliosAPI.update(editingPortfolio.id, {
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
        });
        notify.success('Portfolio updated successfully');
      } else {
        await portfoliosAPI.create({
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
        });
        notify.success('Portfolio created successfully');
      }
      handleCloseDialog();
      fetchData();
      dispatch(fetchPortfolios()); // refresh AppBar selector
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save portfolio'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (portfolio: Portfolio) => {
    if (portfolio.is_default) {
      notify.error('Cannot delete the default portfolio');
      return;
    }
    if (!window.confirm(`Delete "${portfolio.name}"? Its assets will be moved to the Default portfolio.`)) return;
    try {
      await portfoliosAPI.delete(portfolio.id);
      notify.success('Portfolio deleted successfully');
      fetchData();
      dispatch(fetchPortfolios());
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete portfolio'));
    }
  };

  const totalPortfolios = portfolios.length;
  const totalAssets = portfolios.reduce((sum, p) => sum + p.asset_count, 0);
  const totalInvested = portfolios.reduce((sum, p) => sum + p.total_invested, 0);
  const totalValue = portfolios.reduce((sum, p) => sum + p.total_current_value, 0);

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
        <Typography variant="h4">Portfolios</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Create Portfolio
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Portfolios</Typography>
              <Typography variant="h4">{totalPortfolios}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Assets</Typography>
              <Typography variant="h4">{totalAssets}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Invested</Typography>
              <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Current Value</Typography>
              <Typography variant="h5" color={totalValue >= totalInvested ? 'success.main' : 'error.main'}>
                {formatCurrency(totalValue)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Description</strong></TableCell>
              <TableCell align="center"><strong>Assets</strong></TableCell>
              <TableCell align="right"><strong>Invested</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {portfolios.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">No portfolios found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              portfolios.map((p) => {
                const pl = p.total_current_value - p.total_invested;
                const plPct = p.total_invested > 0 ? (pl / p.total_invested) * 100 : 0;
                return (
                  <TableRow key={p.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1" fontWeight={500}>{p.name}</Typography>
                        {p.is_default && (
                          <Chip icon={<DefaultIcon />} label="Default" size="small" color="primary" variant="outlined" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {p.description || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">{p.asset_count}</TableCell>
                    <TableCell align="right">{formatCurrency(p.total_invested)}</TableCell>
                    <TableCell align="right">{formatCurrency(p.total_current_value)}</TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        color={pl >= 0 ? 'success.main' : 'error.main'}
                        fontWeight={500}
                      >
                        {pl >= 0 ? '+' : ''}{formatCurrency(pl)} ({plPct >= 0 ? '+' : ''}{plPct.toFixed(1)}%)
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <IconButton size="small" color="primary" onClick={() => handleOpenDialog(p)} title="Edit">
                        <EditIcon fontSize="small" />
                      </IconButton>
                      {!p.is_default && (
                        <IconButton size="small" color="error" onClick={() => handleDelete(p)} title="Delete">
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create/Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingPortfolio ? 'Edit Portfolio' : 'Create Portfolio'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Portfolio Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
              placeholder="e.g. Retirement, Trading, Wife's Portfolio"
            />
            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
              placeholder="Optional description for this portfolio"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={submitting || !formData.name.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : editingPortfolio ? <EditIcon /> : <AddIcon />}
          >
            {submitting ? 'Saving...' : editingPortfolio ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Portfolios;

// Made with Bob
