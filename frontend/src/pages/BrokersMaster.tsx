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
import { brokersAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';

interface Broker {
  id: number;
  name: string;
  display_label: string;
  broker_type: string;
  supported_markets: string;
  website: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string | null;
}

const BrokersMaster: React.FC = () => {
  const { notify } = useNotification();
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingBroker, setEditingBroker] = useState<Broker | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    display_label: '',
    name: '',
    broker_type: 'discount' as string,
    supported_markets: 'domestic' as string,
    website: '',
    sort_order: 0,
    is_active: true,
  });

  useEffect(() => {
    fetchBrokers();
  }, []);

  const fetchBrokers = async () => {
    try {
      setLoading(true);
      const data = await brokersAPI.getAll();
      setBrokers(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch brokers'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (broker?: Broker) => {
    if (broker) {
      setEditingBroker(broker);
      setFormData({
        display_label: broker.display_label,
        name: broker.name,
        broker_type: broker.broker_type,
        supported_markets: broker.supported_markets,
        website: broker.website || '',
        sort_order: broker.sort_order,
        is_active: broker.is_active,
      });
    } else {
      setEditingBroker(null);
      setFormData({
        display_label: '',
        name: '',
        broker_type: 'discount',
        supported_markets: 'domestic',
        website: '',
        sort_order: 0,
        is_active: true,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingBroker(null);
  };

  const handleDisplayLabelChange = (value: string) => {
    const autoName = value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    setFormData({
      ...formData,
      display_label: value,
      name: editingBroker ? formData.name : autoName,
    });
  };

  const handleSubmit = async () => {
    if (!formData.display_label.trim()) {
      notify.error('Display label is required');
      return;
    }
    try {
      setSubmitting(true);
      if (editingBroker) {
        await brokersAPI.update(editingBroker.id, {
          display_label: formData.display_label.trim(),
          broker_type: formData.broker_type,
          supported_markets: formData.supported_markets,
          website: formData.website.trim() || null,
          sort_order: formData.sort_order,
          is_active: formData.is_active,
        });
        notify.success('Broker updated successfully');
      } else {
        await brokersAPI.create({
          display_label: formData.display_label.trim(),
          name: formData.name.trim() || undefined,
          broker_type: formData.broker_type,
          supported_markets: formData.supported_markets,
          website: formData.website.trim() || null,
          sort_order: formData.sort_order,
        });
        notify.success('Broker added successfully');
      }
      handleCloseDialog();
      fetchBrokers();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save broker'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (broker: Broker) => {
    if (!window.confirm(`Delete "${broker.display_label}"? This will fail if accounts are linked to it.`)) return;
    try {
      await brokersAPI.delete(broker.id);
      notify.success('Broker deleted successfully');
      fetchBrokers();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete broker'));
    }
  };

  const totalBrokers = brokers.length;
  const activeBrokers = brokers.filter((b) => b.is_active).length;
  const domesticCount = brokers.filter((b) => b.supported_markets === 'domestic').length;
  const internationalCount = brokers.filter((b) => b.supported_markets === 'international' || b.supported_markets === 'both').length;

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
        <Typography variant="h4">Brokers</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>
          Add Broker
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total</Typography>
              <Typography variant="h4">{totalBrokers}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Active</Typography>
              <Typography variant="h4">{activeBrokers}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Domestic</Typography>
              <Typography variant="h4">{domesticCount}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">International</Typography>
              <Typography variant="h4">{internationalCount}</Typography>
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
              <TableCell><strong>Markets</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
              <TableCell align="right"><strong>Sort Order</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {brokers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">No brokers found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              brokers.map((broker) => (
                <TableRow key={broker.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CompanyIcon website={broker.website} name={broker.display_label} />
                      <Typography variant="body2" fontFamily="monospace">{broker.name}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{broker.display_label}</TableCell>
                  <TableCell>
                    <Chip
                      label={broker.broker_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      color={broker.broker_type === 'discount' ? 'primary' : broker.broker_type === 'full_service' ? 'secondary' : 'warning'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={broker.supported_markets.replace(/\b\w/g, (c) => c.toUpperCase())}
                      color={broker.supported_markets === 'international' ? 'info' : 'default'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={broker.is_active ? 'Active' : 'Inactive'}
                      color={broker.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">{broker.sort_order}</TableCell>
                  <TableCell align="center">
                    <IconButton size="small" color="primary" onClick={() => handleOpenDialog(broker)} title="Edit">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(broker)} title="Delete">
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
        <DialogTitle>{editingBroker ? 'Edit Broker' : 'Add Broker'}</DialogTitle>
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
              disabled={!!editingBroker}
              helperText={editingBroker ? 'Name cannot be changed after creation' : 'Auto-generated from display label (lowercase, no spaces)'}
              inputProps={{ style: { fontFamily: 'monospace' } }}
            />
            <TextField
              select
              label="Broker Type"
              value={formData.broker_type}
              onChange={(e) => setFormData({ ...formData, broker_type: e.target.value })}
              fullWidth
            >
              <MenuItem value="discount">Discount</MenuItem>
              <MenuItem value="full_service">Full Service</MenuItem>
              <MenuItem value="international">International</MenuItem>
            </TextField>
            <TextField
              select
              label="Supported Markets"
              value={formData.supported_markets}
              onChange={(e) => setFormData({ ...formData, supported_markets: e.target.value })}
              fullWidth
            >
              <MenuItem value="domestic">Domestic</MenuItem>
              <MenuItem value="international">International</MenuItem>
              <MenuItem value="both">Both</MenuItem>
            </TextField>
            <TextField
              label="Website Domain"
              value={formData.website}
              onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              fullWidth
              placeholder="e.g. zerodha.com"
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
            {editingBroker && (
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
            startIcon={submitting ? <CircularProgress size={18} /> : editingBroker ? <EditIcon /> : <AddIcon />}
          >
            {submitting ? 'Saving...' : editingBroker ? 'Update' : 'Add Broker'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BrokersMaster;
