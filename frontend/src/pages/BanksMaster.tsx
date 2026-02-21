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
import { banksAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';

interface Bank {
  id: number;
  name: string;
  display_label: string;
  bank_type: string;
  website: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string | null;
}

const BanksMaster: React.FC = () => {
  const { notify } = useNotification();
  const [banks, setBanks] = useState<Bank[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingBank, setEditingBank] = useState<Bank | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    display_label: '',
    name: '',
    bank_type: 'commercial' as string,
    website: '',
    sort_order: 0,
    is_active: true,
  });

  useEffect(() => {
    fetchBanks();
  }, []);

  const fetchBanks = async () => {
    try {
      setLoading(true);
      const data = await banksAPI.getAll();
      setBanks(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch banks'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (bank?: Bank) => {
    if (bank) {
      setEditingBank(bank);
      setFormData({
        display_label: bank.display_label,
        name: bank.name,
        bank_type: bank.bank_type,
        website: bank.website || '',
        sort_order: bank.sort_order,
        is_active: bank.is_active,
      });
    } else {
      setEditingBank(null);
      setFormData({
        display_label: '',
        name: '',
        bank_type: 'commercial',
        website: '',
        sort_order: 0,
        is_active: true,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingBank(null);
  };

  const handleDisplayLabelChange = (value: string) => {
    const autoName = value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    setFormData({
      ...formData,
      display_label: value,
      name: editingBank ? formData.name : autoName,
    });
  };

  const handleSubmit = async () => {
    if (!formData.display_label.trim()) {
      notify.error('Display label is required');
      return;
    }
    try {
      setSubmitting(true);
      if (editingBank) {
        await banksAPI.update(editingBank.id, {
          display_label: formData.display_label.trim(),
          bank_type: formData.bank_type,
          website: formData.website.trim() || null,
          sort_order: formData.sort_order,
          is_active: formData.is_active,
        });
        notify.success('Bank updated successfully');
      } else {
        await banksAPI.create({
          display_label: formData.display_label.trim(),
          name: formData.name.trim() || undefined,
          bank_type: formData.bank_type,
          website: formData.website.trim() || null,
          sort_order: formData.sort_order,
        });
        notify.success('Bank added successfully');
      }
      handleCloseDialog();
      fetchBanks();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save bank'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (bank: Bank) => {
    if (!window.confirm(`Delete "${bank.display_label}"? This will fail if accounts are linked to it.`)) return;
    try {
      await banksAPI.delete(bank.id);
      notify.success('Bank deleted successfully');
      fetchBanks();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete bank'));
    }
  };

  const totalBanks = banks.length;
  const activeBanks = banks.filter((b) => b.is_active).length;
  const commercialCount = banks.filter((b) => b.bank_type === 'commercial').length;
  const otherTypeCount = banks.filter((b) => b.bank_type !== 'commercial').length;

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
        <Typography variant="h4">Banks</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add Bank
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total</Typography>
              <Typography variant="h4">{totalBanks}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Active</Typography>
              <Typography variant="h4">{activeBanks}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Commercial</Typography>
              <Typography variant="h4">{commercialCount}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Payment / Other</Typography>
              <Typography variant="h4">{otherTypeCount}</Typography>
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
            {banks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No banks found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              banks.map((bank) => (
                <TableRow key={bank.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CompanyIcon website={bank.website} name={bank.display_label} />
                      <Typography variant="body2" fontFamily="monospace">{bank.name}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{bank.display_label}</TableCell>
                  <TableCell>
                    <Chip
                      label={bank.bank_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      color={bank.bank_type === 'commercial' ? 'primary' : 'secondary'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={bank.is_active ? 'Active' : 'Inactive'}
                      color={bank.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">{bank.sort_order}</TableCell>
                  <TableCell align="center">
                    <IconButton size="small" color="primary" onClick={() => handleOpenDialog(bank)} title="Edit">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(bank)} title="Delete">
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
        <DialogTitle>{editingBank ? 'Edit Bank' : 'Add Bank'}</DialogTitle>
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
              disabled={!!editingBank}
              helperText={editingBank ? 'Name cannot be changed after creation' : 'Auto-generated from display label (lowercase, no spaces)'}
              inputProps={{ style: { fontFamily: 'monospace' } }}
            />
            <TextField
              select
              label="Bank Type"
              value={formData.bank_type}
              onChange={(e) => setFormData({ ...formData, bank_type: e.target.value })}
              fullWidth
            >
              <MenuItem value="commercial">Commercial</MenuItem>
              <MenuItem value="payment">Payment</MenuItem>
              <MenuItem value="small_finance">Small Finance</MenuItem>
              <MenuItem value="post_office">Post Office</MenuItem>
            </TextField>
            <TextField
              label="Website Domain"
              value={formData.website}
              onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              fullWidth
              placeholder="e.g. icicibank.com"
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
            {editingBank && (
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
            startIcon={submitting ? <CircularProgress size={18} /> : editingBank ? <EditIcon /> : <AddIcon />}
          >
            {submitting ? 'Saving...' : editingBank ? 'Update' : 'Add Bank'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BanksMaster;
