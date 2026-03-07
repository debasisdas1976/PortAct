import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
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

interface Props {
  assetIds: number[];
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

const BulkAttributeAssignDialog: React.FC<Props> = ({ assetIds, open, onClose, onSaved }) => {
  const { notify } = useNotification();
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [selectedAttribute, setSelectedAttribute] = useState<Attribute | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && assetIds.length > 0) {
      setSelectedAttribute(null);
      loadAttributes();
    }
  }, [open, assetIds]);

  const loadAttributes = async () => {
    try {
      setLoading(true);
      const attrs = await assetAttributesAPI.getAll(true);
      setAttributes(attrs);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load attributes'));
    } finally {
      setLoading(false);
    }
  };

  const handleValueClick = async (value: AttributeValue) => {
    if (!selectedAttribute) return;
    try {
      setSaving(true);
      await assetAttributesAPI.setBulkAssignments(assetIds, [
        { attribute_id: selectedAttribute.id, attribute_value_id: value.id },
      ]);
      notify.success(
        `"${selectedAttribute.display_label}: ${value.label}" applied to ${assetIds.length} asset${assetIds.length > 1 ? 's' : ''}`
      );
      onSaved?.();
      onClose();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to apply attribute'));
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setSelectedAttribute(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        {selectedAttribute ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DynamicIcon name={selectedAttribute.icon} fontSize="small" />
            {selectedAttribute.display_label}
          </Box>
        ) : (
          'Set Attribute'
        )}
        <Typography variant="body2" color="text.secondary">
          {assetIds.length} asset{assetIds.length > 1 ? 's' : ''} selected
          {selectedAttribute ? ' — pick a value' : ' — pick an attribute'}
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ px: 0, pb: 0 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : attributes.length === 0 ? (
          <Typography color="text.secondary" sx={{ py: 2, px: 3 }}>
            No attributes defined. Create attributes in Master Data first.
          </Typography>
        ) : !selectedAttribute ? (
          /* Step 1: Pick an attribute */
          <List disablePadding>
            {attributes.map((attr) => (
              <ListItemButton key={attr.id} onClick={() => setSelectedAttribute(attr)}>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <DynamicIcon name={attr.icon} fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={attr.display_label}
                  secondary={`${attr.values.filter((v) => v.is_active).length} values`}
                />
              </ListItemButton>
            ))}
          </List>
        ) : (
          /* Step 2: Pick a value for the chosen attribute */
          <List disablePadding>
            {selectedAttribute.values
              .filter((v) => v.is_active)
              .map((v) => (
                <ListItemButton key={v.id} onClick={() => handleValueClick(v)} disabled={saving}>
                  {v.color && (
                    <ListItemIcon sx={{ minWidth: 28 }}>
                      <Box sx={{ width: 14, height: 14, borderRadius: '50%', bgcolor: v.color }} />
                    </ListItemIcon>
                  )}
                  <ListItemText primary={v.label} />
                  {saving && (
                    <CircularProgress size={18} sx={{ ml: 1 }} />
                  )}
                </ListItemButton>
              ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        {selectedAttribute ? (
          <Button onClick={() => setSelectedAttribute(null)} startIcon={<ArrowBackIcon />}>
            Back
          </Button>
        ) : (
          <Button onClick={handleClose}>Cancel</Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default BulkAttributeAssignDialog;
