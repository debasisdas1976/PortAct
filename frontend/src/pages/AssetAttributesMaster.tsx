import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
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
  InputAdornment,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { assetAttributesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import IconPicker, { DynamicIcon } from '../components/IconPicker';

interface AttributeValue {
  id: number;
  attribute_id: number;
  label: string;
  color: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

interface Attribute {
  id: number;
  user_id: number;
  name: string;
  display_label: string;
  description: string | null;
  icon: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  values: AttributeValue[];
}

const AssetAttributesMaster: React.FC = () => {
  const { notify } = useNotification();
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Attribute dialog
  const [openAttrDialog, setOpenAttrDialog] = useState(false);
  const [editingAttr, setEditingAttr] = useState<Attribute | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [attrForm, setAttrForm] = useState({
    display_label: '',
    name: '',
    description: '',
    icon: '',
    sort_order: 0,
    is_active: true,
  });
  const [inlineValues, setInlineValues] = useState<Array<{ label: string; color: string; sort_order: number }>>([]);

  // Value dialog
  const [openValDialog, setOpenValDialog] = useState(false);
  const [editingVal, setEditingVal] = useState<AttributeValue | null>(null);
  const [valParentId, setValParentId] = useState<number | null>(null);
  const [valForm, setValForm] = useState({
    label: '',
    color: '',
    sort_order: 0,
    is_active: true,
  });

  useEffect(() => {
    fetchAttributes();
  }, []);

  const fetchAttributes = async () => {
    try {
      setLoading(true);
      const data = await assetAttributesAPI.getAll();
      setAttributes(data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch attributes'));
    } finally {
      setLoading(false);
    }
  };

  // ─── Attribute CRUD ────────────────────────────────────────────────────────

  const handleOpenAttrDialog = (attr?: Attribute) => {
    if (attr) {
      setEditingAttr(attr);
      setAttrForm({
        display_label: attr.display_label,
        name: attr.name,
        description: attr.description || '',
        icon: attr.icon || '',
        sort_order: attr.sort_order,
        is_active: attr.is_active,
      });
      setInlineValues([]);
    } else {
      setEditingAttr(null);
      setAttrForm({ display_label: '', name: '', description: '', icon: '', sort_order: 0, is_active: true });
      setInlineValues([]);
    }
    setOpenAttrDialog(true);
  };

  const handleDisplayLabelChange = (value: string) => {
    const autoName = value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    setAttrForm({
      ...attrForm,
      display_label: value,
      name: editingAttr ? attrForm.name : autoName,
    });
  };

  const handleAddInlineValue = () => {
    setInlineValues([...inlineValues, { label: '', color: '', sort_order: inlineValues.length }]);
  };

  const handleRemoveInlineValue = (index: number) => {
    setInlineValues(inlineValues.filter((_, i) => i !== index));
  };

  const handleInlineValueChange = (index: number, field: string, value: string | number) => {
    const updated = [...inlineValues];
    (updated[index] as any)[field] = value;
    setInlineValues(updated);
  };

  const handleSubmitAttr = async () => {
    if (!attrForm.display_label.trim()) {
      notify.error('Display label is required');
      return;
    }
    try {
      setSubmitting(true);
      if (editingAttr) {
        await assetAttributesAPI.update(editingAttr.id, {
          display_label: attrForm.display_label.trim(),
          description: attrForm.description.trim() || null,
          icon: attrForm.icon || null,
          sort_order: attrForm.sort_order,
          is_active: attrForm.is_active,
        });
        notify.success('Attribute updated successfully');
      } else {
        const validValues = inlineValues.filter((v) => v.label.trim());
        await assetAttributesAPI.create({
          display_label: attrForm.display_label.trim(),
          name: attrForm.name.trim() || undefined,
          description: attrForm.description.trim() || undefined,
          icon: attrForm.icon || undefined,
          sort_order: attrForm.sort_order,
          values: validValues.length
            ? validValues.map((v) => ({ label: v.label.trim(), color: v.color.trim() || undefined, sort_order: v.sort_order }))
            : undefined,
        });
        notify.success('Attribute created successfully');
      }
      setOpenAttrDialog(false);
      setEditingAttr(null);
      fetchAttributes();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save attribute'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteAttr = async (attr: Attribute) => {
    const valueCount = attr.values.length;
    if (!window.confirm(`Delete "${attr.display_label}"? This will also remove its ${valueCount} value(s) and all asset assignments.`)) return;
    try {
      await assetAttributesAPI.delete(attr.id);
      notify.success('Attribute deleted successfully');
      if (expandedId === attr.id) setExpandedId(null);
      fetchAttributes();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete attribute'));
    }
  };

  // ─── Value CRUD ────────────────────────────────────────────────────────────

  const handleOpenValDialog = (attributeId: number, val?: AttributeValue) => {
    setValParentId(attributeId);
    if (val) {
      setEditingVal(val);
      setValForm({ label: val.label, color: val.color || '', sort_order: val.sort_order, is_active: val.is_active });
    } else {
      setEditingVal(null);
      setValForm({ label: '', color: '', sort_order: 0, is_active: true });
    }
    setOpenValDialog(true);
  };

  const handleSubmitVal = async () => {
    if (!valForm.label.trim() || !valParentId) {
      notify.error('Label is required');
      return;
    }
    try {
      setSubmitting(true);
      if (editingVal) {
        await assetAttributesAPI.updateValue(valParentId, editingVal.id, {
          label: valForm.label.trim(),
          color: valForm.color.trim() || null,
          sort_order: valForm.sort_order,
          is_active: valForm.is_active,
        });
        notify.success('Value updated successfully');
      } else {
        await assetAttributesAPI.addValue(valParentId, {
          label: valForm.label.trim(),
          color: valForm.color.trim() || undefined,
          sort_order: valForm.sort_order,
        });
        notify.success('Value added successfully');
      }
      setOpenValDialog(false);
      setEditingVal(null);
      setValParentId(null);
      fetchAttributes();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save value'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteVal = async (attributeId: number, val: AttributeValue) => {
    if (!window.confirm(`Delete value "${val.label}"? Any asset assignments using this value will be removed.`)) return;
    try {
      await assetAttributesAPI.deleteValue(attributeId, val.id);
      notify.success('Value deleted successfully');
      fetchAttributes();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete value'));
    }
  };

  // ─── Computed stats ────────────────────────────────────────────────────────

  const totalAttributes = attributes.length;
  const activeAttributes = attributes.filter((a) => a.is_active).length;
  const totalValues = attributes.reduce((sum, a) => sum + a.values.length, 0);

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
        <Typography variant="h4">Asset Attributes</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenAttrDialog()}>
          Add Attribute
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Attributes</Typography>
              <Typography variant="h4">{totalAttributes}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Active</Typography>
              <Typography variant="h4">{activeAttributes}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Values</Typography>
              <Typography variant="h4">{totalValues}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell width={40} />
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Display Label</strong></TableCell>
              <TableCell><strong>Description</strong></TableCell>
              <TableCell align="center"><strong>Values</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
              <TableCell align="right"><strong>Sort</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {attributes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary" sx={{ py: 2 }}>
                    No attributes defined yet. Click "Add Attribute" to create one.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              attributes.map((attr) => (
                <React.Fragment key={attr.id}>
                  <TableRow hover sx={{ cursor: 'pointer' }} onClick={() => setExpandedId(expandedId === attr.id ? null : attr.id)}>
                    <TableCell>
                      <IconButton size="small">
                        {expandedId === attr.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">{attr.name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <DynamicIcon name={attr.icon} fontSize="small" />
                        {attr.display_label}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 200 }}>
                        {attr.description || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={attr.values.length} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={attr.is_active ? 'Active' : 'Inactive'} color={attr.is_active ? 'success' : 'default'} size="small" />
                    </TableCell>
                    <TableCell align="right">{attr.sort_order}</TableCell>
                    <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                      <IconButton size="small" color="primary" onClick={() => handleOpenAttrDialog(attr)} title="Edit">
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDeleteAttr(attr)} title="Delete">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>

                  {/* Expanded values */}
                  <TableRow>
                    <TableCell colSpan={8} sx={{ py: 0, borderBottom: expandedId === attr.id ? undefined : 'none' }}>
                      <Collapse in={expandedId === attr.id} timeout="auto" unmountOnExit>
                        <Box sx={{ py: 2, pl: 6 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                            <Typography variant="subtitle2" color="text.secondary">Allowed Values</Typography>
                            <Button size="small" startIcon={<AddIcon />} onClick={() => handleOpenValDialog(attr.id)}>
                              Add Value
                            </Button>
                          </Box>
                          {attr.values.length === 0 ? (
                            <Typography variant="body2" color="text.secondary">No values defined yet.</Typography>
                          ) : (
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell><strong>Label</strong></TableCell>
                                  <TableCell><strong>Color</strong></TableCell>
                                  <TableCell align="center"><strong>Status</strong></TableCell>
                                  <TableCell align="right"><strong>Sort</strong></TableCell>
                                  <TableCell align="center"><strong>Actions</strong></TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {attr.values.map((val) => (
                                  <TableRow key={val.id} hover>
                                    <TableCell>
                                      <Chip
                                        label={val.label}
                                        size="small"
                                        sx={val.color ? { bgcolor: val.color, color: '#fff' } : undefined}
                                        variant={val.color ? 'filled' : 'outlined'}
                                      />
                                    </TableCell>
                                    <TableCell>
                                      {val.color ? (
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                          <Box sx={{ width: 16, height: 16, borderRadius: 1, bgcolor: val.color, border: '1px solid rgba(0,0,0,0.12)' }} />
                                          <Typography variant="body2" fontFamily="monospace" fontSize={12}>{val.color}</Typography>
                                        </Box>
                                      ) : '—'}
                                    </TableCell>
                                    <TableCell align="center">
                                      <Chip label={val.is_active ? 'Active' : 'Inactive'} color={val.is_active ? 'success' : 'default'} size="small" />
                                    </TableCell>
                                    <TableCell align="right">{val.sort_order}</TableCell>
                                    <TableCell align="center">
                                      <IconButton size="small" color="primary" onClick={() => handleOpenValDialog(attr.id, val)} title="Edit">
                                        <EditIcon fontSize="small" />
                                      </IconButton>
                                      <IconButton size="small" color="error" onClick={() => handleDeleteVal(attr.id, val)} title="Delete">
                                        <DeleteIcon fontSize="small" />
                                      </IconButton>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ─── Attribute Dialog ──────────────────────────────────────────────── */}
      <Dialog open={openAttrDialog} onClose={() => setOpenAttrDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingAttr ? 'Edit Attribute' : 'Add Attribute'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Display Label"
              value={attrForm.display_label}
              onChange={(e) => handleDisplayLabelChange(e.target.value)}
              fullWidth
              required
              helperText="e.g., Risk Profile, Bucket Strategy"
            />
            <TextField
              label="Name (key)"
              value={attrForm.name}
              onChange={(e) => setAttrForm({ ...attrForm, name: e.target.value })}
              fullWidth
              disabled={!!editingAttr}
              helperText={editingAttr ? 'Name cannot be changed after creation' : 'Auto-generated from display label'}
              inputProps={{ style: { fontFamily: 'monospace' } }}
            />
            <TextField
              label="Description"
              value={attrForm.description}
              onChange={(e) => setAttrForm({ ...attrForm, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <IconPicker
                  value={attrForm.icon}
                  onChange={(iconName) => setAttrForm({ ...attrForm, icon: iconName })}
                  label="Icon"
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Sort Order"
                  type="number"
                  value={attrForm.sort_order}
                  onChange={(e) => setAttrForm({ ...attrForm, sort_order: parseInt(e.target.value) || 0 })}
                  fullWidth
                />
              </Grid>
            </Grid>
            {editingAttr && (
              <FormControlLabel
                control={<Switch checked={attrForm.is_active} onChange={(e) => setAttrForm({ ...attrForm, is_active: e.target.checked })} />}
                label="Active"
              />
            )}

            {/* Inline values (create mode only) */}
            {!editingAttr && (
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2">Initial Values (optional)</Typography>
                  <Button size="small" startIcon={<AddIcon />} onClick={handleAddInlineValue}>Add Value</Button>
                </Box>
                {inlineValues.map((v, i) => (
                  <Box key={i} sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                    <TextField
                      size="small"
                      label="Label"
                      value={v.label}
                      onChange={(e) => handleInlineValueChange(i, 'label', e.target.value)}
                      sx={{ flex: 2 }}
                    />
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1 }}>
                      <input
                        type="color"
                        value={v.color || '#4caf50'}
                        onChange={(e) => handleInlineValueChange(i, 'color', e.target.value)}
                        style={{ width: 32, height: 32, padding: 0, border: '1px solid rgba(0,0,0,0.23)', borderRadius: 4, cursor: 'pointer', background: 'none', flexShrink: 0 }}
                      />
                      <TextField
                        size="small"
                        value={v.color}
                        onChange={(e) => handleInlineValueChange(i, 'color', e.target.value)}
                        placeholder="#hex"
                        sx={{ flex: 1 }}
                      />
                    </Box>
                    <IconButton size="small" color="error" onClick={() => handleRemoveInlineValue(i)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAttrDialog(false)}>Cancel</Button>
          <Button
            onClick={handleSubmitAttr}
            variant="contained"
            disabled={submitting || !attrForm.display_label.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : editingAttr ? <EditIcon /> : <AddIcon />}
          >
            {submitting ? 'Saving...' : editingAttr ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ─── Value Dialog ─────────────────────────────────────────────────── */}
      <Dialog open={openValDialog} onClose={() => setOpenValDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{editingVal ? 'Edit Value' : 'Add Value'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Label"
              value={valForm.label}
              onChange={(e) => setValForm({ ...valForm, label: e.target.value })}
              fullWidth
              required
              helperText="e.g., Low Risk, Growth Bucket"
            />
            <TextField
              label="Color"
              value={valForm.color}
              onChange={(e) => setValForm({ ...valForm, color: e.target.value })}
              fullWidth
              placeholder="#4caf50"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <input
                      type="color"
                      value={valForm.color || '#4caf50'}
                      onChange={(e) => setValForm({ ...valForm, color: e.target.value })}
                      style={{ width: 28, height: 28, padding: 0, border: '1px solid rgba(0,0,0,0.23)', borderRadius: 4, cursor: 'pointer', background: 'none' }}
                    />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Sort Order"
              type="number"
              value={valForm.sort_order}
              onChange={(e) => setValForm({ ...valForm, sort_order: parseInt(e.target.value) || 0 })}
              fullWidth
            />
            {editingVal && (
              <FormControlLabel
                control={<Switch checked={valForm.is_active} onChange={(e) => setValForm({ ...valForm, is_active: e.target.checked })} />}
                label="Active"
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenValDialog(false)}>Cancel</Button>
          <Button
            onClick={handleSubmitVal}
            variant="contained"
            disabled={submitting || !valForm.label.trim()}
            startIcon={submitting ? <CircularProgress size={18} /> : editingVal ? <EditIcon /> : <AddIcon />}
          >
            {submitting ? 'Saving...' : editingVal ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AssetAttributesMaster;
