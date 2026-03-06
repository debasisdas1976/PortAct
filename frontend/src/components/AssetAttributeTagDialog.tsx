import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  MenuItem,
  TextField,
  Typography,
} from '@mui/material';
import {
  Clear as ClearIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { assetAttributesAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { DynamicIcon } from './IconPicker';

interface AttributeValue {
  id: number;
  attribute_id: number;
  label: string;
  color: string | null;
  sort_order: number;
  is_active: boolean;
}

interface Attribute {
  id: number;
  name: string;
  display_label: string;
  icon: string | null;
  values: AttributeValue[];
}

interface Assignment {
  attribute_id: number;
  attribute_value_id: number;
}

interface Props {
  assetId: number | null;
  assetName?: string;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

const AssetAttributeTagDialog: React.FC<Props> = ({ assetId, assetName, open, onClose, onSaved }) => {
  const { notify } = useNotification();
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [selections, setSelections] = useState<Record<number, number | ''>>({}); // attribute_id -> value_id or ''
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && assetId) {
      loadData();
    }
  }, [open, assetId]);

  const loadData = async () => {
    if (!assetId) return;
    try {
      setLoading(true);
      const [attrs, assignments] = await Promise.all([
        assetAttributesAPI.getAll(true),
        assetAttributesAPI.getAssignments(assetId),
      ]);
      setAttributes(attrs);

      // Build selections from existing assignments
      const sel: Record<number, number | ''> = {};
      for (const attr of attrs) {
        const existing = assignments.find((a: any) => a.attribute_id === attr.id);
        sel[attr.id] = existing ? existing.attribute_value_id : '';
      }
      setSelections(sel);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load attributes'));
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (attributeId: number, valueId: number | '') => {
    setSelections({ ...selections, [attributeId]: valueId });
  };

  const handleClear = (attributeId: number) => {
    setSelections({ ...selections, [attributeId]: '' });
  };

  const handleSave = async () => {
    if (!assetId) return;
    try {
      setSaving(true);
      const assignments: Assignment[] = [];
      for (const [attrId, valId] of Object.entries(selections)) {
        if (valId !== '' && valId !== 0) {
          assignments.push({ attribute_id: Number(attrId), attribute_value_id: Number(valId) });
        }
      }
      await assetAttributesAPI.setAssignments(assetId, assignments);
      notify.success('Attributes saved');
      onSaved?.();
      onClose();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save attributes'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Asset Attributes
        {assetName && (
          <Typography variant="body2" color="text.secondary">{assetName}</Typography>
        )}
      </DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : attributes.length === 0 ? (
          <Typography color="text.secondary" sx={{ py: 2 }}>
            No attributes defined. Create attributes in Master Data first.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            {attributes.map((attr) => {
              const activeValues = attr.values.filter((v) => v.is_active);
              const selectedValue = activeValues.find((v) => v.id === selections[attr.id]);
              return (
                <Box key={attr.id}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <DynamicIcon name={attr.icon} fontSize="small" />
                    <Typography variant="subtitle2">{attr.display_label}</Typography>
                    {selectedValue && selectedValue.color && (
                      <Chip
                        label={selectedValue.label}
                        size="small"
                        sx={{ bgcolor: selectedValue.color, color: '#fff', ml: 'auto' }}
                      />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TextField
                      select
                      size="small"
                      fullWidth
                      value={selections[attr.id] ?? ''}
                      onChange={(e) => handleChange(attr.id, e.target.value ? Number(e.target.value) : '')}
                      placeholder="Select a value..."
                    >
                      <MenuItem value="">
                        <em>None</em>
                      </MenuItem>
                      {activeValues.map((v) => (
                        <MenuItem key={v.id} value={v.id}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {v.color && (
                              <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: v.color, flexShrink: 0 }} />
                            )}
                            {v.label}
                          </Box>
                        </MenuItem>
                      ))}
                    </TextField>
                    {selections[attr.id] !== '' && (
                      <IconButton size="small" onClick={() => handleClear(attr.id)} title="Clear">
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    )}
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || loading || attributes.length === 0}
          startIcon={saving ? <CircularProgress size={18} /> : <SaveIcon />}
        >
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AssetAttributeTagDialog;
