import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

const AREA_UNITS = [
  { value: 'sqft', label: 'Sq. Ft.' },
  { value: 'acres', label: 'Acres' },
  { value: 'hectares', label: 'Hectares' },
  { value: 'cents', label: 'Cents' },
  { value: 'guntha', label: 'Guntha' },
];

interface RealEstateProperty {
  id: number;
  user_id: number;
  asset_id: number;
  nickname: string;
  property_type: string;
  location: string;
  city?: string;
  state?: string;
  pincode?: string;
  area: number;
  area_unit: string;
  purchase_price: number;
  current_market_value: number;
  purchase_date: string;
  registration_number?: string;
  loan_outstanding?: number;
  rental_income_monthly?: number;
  is_active: boolean;
  notes?: string;
  profit_loss: number;
  profit_loss_percentage: number;
  created_at: string;
  updated_at?: string;
}

interface RealEstateSummary {
  total_properties: number;
  active_properties: number;
  total_invested: number;
  total_current_value: number;
  total_profit_loss: number;
  total_rental_income_monthly: number;
  properties: RealEstateProperty[];
}

interface RealEstateProps {
  propertyType: string;
  title: string;
}

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  land: 'Land',
  farm_land: 'Farm Land',
  house: 'House',
};

const RealEstate: React.FC<RealEstateProps> = ({ propertyType, title }) => {
  const defaultAreaUnit = propertyType === 'house' ? 'sqft' : 'acres';

  const emptyForm = {
    nickname: '',
    property_type: propertyType,
    location: '',
    city: '',
    state: '',
    pincode: '',
    area: '',
    area_unit: defaultAreaUnit,
    purchase_price: '',
    current_market_value: '',
    purchase_date: '',
    registration_number: '',
    loan_outstanding: '',
    rental_income_monthly: '',
    is_active: true,
    notes: '',
  };

  const { notify } = useNotification();
  const [summary, setSummary] = useState<RealEstateSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [dialogError, setDialogError] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/real-estates/summary?property_type=${propertyType}`);
      setSummary(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyType]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  const getAreaUnitLabel = (unit: string) =>
    AREA_UNITS.find((u) => u.value === unit)?.label || unit;

  const handleOpenAdd = () => {
    setEditingId(null);
    setForm({ ...emptyForm });
    setDialogOpen(true);
  };

  const handleOpenEdit = (prop: RealEstateProperty) => {
    setEditingId(prop.id);
    setForm({
      nickname: prop.nickname,
      property_type: prop.property_type,
      location: prop.location,
      city: prop.city || '',
      state: prop.state || '',
      pincode: prop.pincode || '',
      area: String(prop.area),
      area_unit: prop.area_unit,
      purchase_price: String(prop.purchase_price),
      current_market_value: String(prop.current_market_value),
      purchase_date: prop.purchase_date,
      registration_number: prop.registration_number || '',
      loan_outstanding: prop.loan_outstanding ? String(prop.loan_outstanding) : '',
      rental_income_monthly: prop.rental_income_monthly ? String(prop.rental_income_monthly) : '',
      is_active: prop.is_active,
      notes: prop.notes || '',
    });
    setDialogOpen(true);
  };

  const handleClose = () => {
    setDialogOpen(false);
    setEditingId(null);
  };

  const handleSave = async () => {
    if (!form.nickname || !form.location || !form.area || !form.purchase_price ||
        !form.current_market_value || !form.purchase_date) {
      setDialogError('Please fill in all required fields');
      return;
    }
    setDialogError('');
    const payload: any = {
      nickname: form.nickname,
      property_type: propertyType,
      location: form.location,
      city: form.city || null,
      state: form.state || null,
      pincode: form.pincode || null,
      area: parseFloat(form.area),
      area_unit: form.area_unit,
      purchase_price: parseFloat(form.purchase_price),
      current_market_value: parseFloat(form.current_market_value),
      purchase_date: form.purchase_date,
      registration_number: form.registration_number || null,
      loan_outstanding: form.loan_outstanding ? parseFloat(form.loan_outstanding) : 0,
      rental_income_monthly: form.rental_income_monthly ? parseFloat(form.rental_income_monthly) : 0,
      is_active: form.is_active,
      notes: form.notes || null,
    };
    try {
      setSaving(true);
      if (editingId) {
        await api.put(`/real-estates/${editingId}`, payload);
        notify.success(`${title} property updated successfully`);
      } else {
        await api.post('/real-estates/', payload);
        notify.success(`${title} property added successfully`);
      }
      handleClose();
      fetchData();
    } catch (err: any) {
      setDialogError(err.response?.data?.detail || `Failed to save ${title.toLowerCase()} property. Please try again.`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete property "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/real-estates/${id}`);
      notify.success('Property deleted');
      fetchData();
    } catch (err: any) {
      notify.error(err.response?.data?.detail || 'Failed to delete property');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const properties = summary?.properties || [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">{title} Properties</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleOpenAdd}>
          Add {title}
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {[
          { label: 'Total Properties', value: String(summary?.total_properties || 0) },
          { label: 'Total Invested', value: formatCurrency(summary?.total_invested || 0) },
          { label: 'Current Value', value: formatCurrency(summary?.total_current_value || 0) },
          {
            label: 'Total P/L',
            value: formatCurrency(summary?.total_profit_loss || 0),
            color: (summary?.total_profit_loss || 0) >= 0 ? 'success.main' : 'error.main',
          },
          { label: 'Monthly Rental Income', value: formatCurrency(summary?.total_rental_income_monthly || 0) },
        ].map(({ label, value, color }) => (
          <Grid item xs={12} sm={6} md={2.4} key={label}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" variant="body2">{label}</Typography>
                <Typography variant="h6" sx={color ? { color } : undefined}>{value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Properties Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Location</strong></TableCell>
              <TableCell align="right"><strong>Area</strong></TableCell>
              <TableCell align="right"><strong>Purchase Price</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>P/L</strong></TableCell>
              <TableCell align="right"><strong>Loan</strong></TableCell>
              <TableCell align="right"><strong>Rental/mo</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {properties.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary" sx={{ py: 4 }}>
                    No {title.toLowerCase()} properties yet. Click "Add {title}" to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              properties.map((prop) => (
                <TableRow key={prop.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">{prop.nickname}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{prop.location}</Typography>
                    {prop.city && (
                      <Typography variant="caption" color="text.secondary">
                        {[prop.city, prop.state].filter(Boolean).join(', ')}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {prop.area} {getAreaUnitLabel(prop.area_unit)}
                  </TableCell>
                  <TableCell align="right">{formatCurrency(prop.purchase_price)}</TableCell>
                  <TableCell align="right">{formatCurrency(prop.current_market_value)}</TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      sx={{ color: prop.profit_loss >= 0 ? 'success.main' : 'error.main' }}
                    >
                      {formatCurrency(prop.profit_loss)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      ({prop.profit_loss_percentage >= 0 ? '+' : ''}{prop.profit_loss_percentage.toFixed(1)}%)
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {prop.loan_outstanding ? formatCurrency(prop.loan_outstanding) : '-'}
                  </TableCell>
                  <TableCell align="right">
                    {prop.rental_income_monthly ? formatCurrency(prop.rental_income_monthly) : '-'}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={prop.is_active ? 'Active' : 'Sold'}
                      color={prop.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => handleOpenEdit(prop)}>
                      <Edit fontSize="small" />
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(prop.id, prop.nickname)}>
                      <Delete fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>{editingId ? `Edit ${title} Property` : `Add ${title} Property`}</DialogTitle>
        <DialogContent>
          {dialogError && <Alert severity="error" sx={{ mb: 2 }}>{dialogError}</Alert>}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Property Name"
                fullWidth
                required
                value={form.nickname}
                onChange={(e) => setForm({ ...form, nickname: e.target.value })}
                placeholder={propertyType === 'house' ? 'e.g. 2BHK Koramangala' : 'e.g. Plot in Whitefield'}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Property Type"
                fullWidth
                value={PROPERTY_TYPE_LABELS[propertyType] || propertyType}
                InputProps={{ readOnly: true }}
                disabled
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Location / Address"
                fullWidth
                required
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="City"
                fullWidth
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="State"
                fullWidth
                value={form.state}
                onChange={(e) => setForm({ ...form, state: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Pincode"
                fullWidth
                value={form.pincode}
                onChange={(e) => setForm({ ...form, pincode: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Area"
                fullWidth
                required
                type="number"
                value={form.area}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Area Unit</InputLabel>
                <Select
                  value={form.area_unit}
                  label="Area Unit"
                  onChange={(e) => setForm({ ...form, area_unit: e.target.value })}
                >
                  {AREA_UNITS.map((u) => (
                    <MenuItem key={u.value} value={u.value}>{u.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Purchase Price (₹)"
                fullWidth
                required
                type="number"
                value={form.purchase_price}
                onChange={(e) => setForm({ ...form, purchase_price: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Current Market Value (₹)"
                fullWidth
                required
                type="number"
                value={form.current_market_value}
                onChange={(e) => setForm({ ...form, current_market_value: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Purchase Date"
                fullWidth
                required
                type="date"
                value={form.purchase_date}
                onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Registration Number"
                fullWidth
                value={form.registration_number}
                onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Loan Outstanding (₹)"
                fullWidth
                type="number"
                value={form.loan_outstanding}
                onChange={(e) => setForm({ ...form, loan_outstanding: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Monthly Rental Income (₹)"
                fullWidth
                type="number"
                value={form.rental_income_monthly}
                onChange={(e) => setForm({ ...form, rental_income_monthly: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes"
                fullWidth
                multiline
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                }
                label="Active (uncheck if sold/disposed)"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  );
};

export default RealEstate;
