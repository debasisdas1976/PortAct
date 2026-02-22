import React, { useState, useEffect } from 'react';
import {
  Box,
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
  Button,
} from '@mui/material';
import { Edit as EditIcon } from '@mui/icons-material';
import { assetTypesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface AssetType {
  id: number;
  name: string;
  display_label: string;
  category: string;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string | null;
}

const CATEGORIES = [
  'Equity',
  'Fixed Income',
  'Govt. Schemes',
  'Commodities',
  'Crypto',
  'Real Estate',
  'Other',
];

const getCategoryColor = (category: string): 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info' | 'default' => {
  switch (category) {
    case 'Equity': return 'primary';
    case 'Fixed Income': return 'info';
    case 'Govt. Schemes': return 'success';
    case 'Commodities': return 'warning';
    case 'Crypto': return 'secondary';
    case 'Real Estate': return 'error';
    default: return 'default';
  }
};

const AssetTypesMaster: React.FC = () => {
  const { notify } = useNotification();
  const [assetTypes, setAssetTypes] = useState<AssetType[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingItem, setEditingItem] = useState<AssetType | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    display_label: '',
    category: '',
    sort_order: 0,
    is_active: true,
  });

  useEffect(() => {
    fetchAssetTypes();
  }, []);

  const fetchAssetTypes = async () => {
    try {
      setLoading(true);
      const data = await assetTypesAPI.getAll();
      setAssetTypes(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch asset types'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (item: AssetType) => {
    setEditingItem(item);
    setFormData({
      display_label: item.display_label,
      category: item.category,
      sort_order: item.sort_order,
      is_active: item.is_active,
    });
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingItem(null);
  };

  const handleSubmit = async () => {
    if (!editingItem || !formData.display_label.trim() || !formData.category) {
      notify.error('Display label and category are required');
      return;
    }
    try {
      setSubmitting(true);
      await assetTypesAPI.update(editingItem.id, {
        display_label: formData.display_label.trim(),
        category: formData.category,
        sort_order: formData.sort_order,
        is_active: formData.is_active,
      });
      notify.success('Asset type updated successfully');
      handleCloseDialog();
      fetchAssetTypes();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to update asset type'));
    } finally {
      setSubmitting(false);
    }
  };

  const totalTypes = assetTypes.length;
  const activeTypes = assetTypes.filter((t) => t.is_active).length;
  const categoryCounts: Record<string, number> = {};
  assetTypes.forEach((t) => {
    categoryCounts[t.category] = (categoryCounts[t.category] || 0) + 1;
  });

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
        <Typography variant="h4">Asset Types</Typography>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={4} md={2}>
          <Card>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography color="text.secondary" variant="caption">Total</Typography>
              <Typography variant="h5">{totalTypes}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <Card>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography color="text.secondary" variant="caption">Active</Typography>
              <Typography variant="h5">{activeTypes}</Typography>
            </CardContent>
          </Card>
        </Grid>
        {CATEGORIES.filter((c) => categoryCounts[c]).map((cat) => (
          <Grid item xs={6} sm={4} md={2} key={cat}>
            <Card>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Typography color="text.secondary" variant="caption">{cat}</Typography>
                <Typography variant="h5">{categoryCounts[cat]}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>Display Label</strong></TableCell>
              <TableCell><strong>Name (key)</strong></TableCell>
              <TableCell><strong>Category</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
              <TableCell align="right"><strong>Sort Order</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assetTypes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No asset types found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              assetTypes.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.display_label}</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace" color="text.secondary">
                      {item.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={item.category}
                      color={getCategoryColor(item.category)}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={item.is_active ? 'Active' : 'Inactive'}
                      color={item.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">{item.sort_order}</TableCell>
                  <TableCell align="center">
                    <IconButton size="small" color="primary" onClick={() => handleOpenDialog(item)} title="Edit">
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Asset Type</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            {editingItem && (
              <TextField
                label="Name (key)"
                value={editingItem.name}
                fullWidth
                disabled
                helperText="System-defined, cannot be changed"
                inputProps={{ style: { fontFamily: 'monospace' } }}
              />
            )}
            <TextField
              label="Display Label"
              value={formData.display_label}
              onChange={(e) => setFormData({ ...formData, display_label: e.target.value })}
              fullWidth
              required
              helperText="The display name shown across the application"
            />
            <TextField
              select
              label="Category"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              fullWidth
              required
              helperText="Group this asset type under a category"
            >
              {CATEGORIES.map((cat) => (
                <MenuItem key={cat} value={cat}>{cat}</MenuItem>
              ))}
            </TextField>
            <TextField
              label="Sort Order"
              type="number"
              value={formData.sort_order}
              onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
              fullWidth
              helperText="Lower numbers appear first"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              }
              label="Active"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={submitting || !formData.display_label.trim() || !formData.category}
            startIcon={submitting ? <CircularProgress size={18} /> : <EditIcon />}
          >
            {submitting ? 'Saving...' : 'Update'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AssetTypesMaster;
