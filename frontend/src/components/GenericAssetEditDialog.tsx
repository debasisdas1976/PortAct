import React, { useEffect, useState, useMemo } from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  MenuItem,
  Radio,
  RadioGroup,
  TextField,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon } from '@mui/icons-material';
import { assetsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { getAssetTypeConfig, type FieldDef } from '../config/assetFieldConfig';

// ── Helpers ─────────────────────────────────────────────────────────────

/**
 * Convert INR-stored value to USD for display.
 * Imported US stocks have INR in main columns + USD in details.
 * Manually-added stocks have USD directly in main columns.
 */
const toUSD = (value: number, details: Record<string, any> | undefined, usdField: string): number => {
  const d = details || {};
  if (d[usdField] != null) return d[usdField];
  if (d.avg_cost_usd != null) {
    const rate = d.usd_to_inr_rate;
    if (rate && rate > 0) return value / rate;
  }
  return value;
};

const buildDematLabel = (da: any) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

// ── Types ───────────────────────────────────────────────────────────────

interface GenericAssetEditDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  asset: any | null;          // null = add mode
  assetType: string;          // determines field config
  dematAccounts?: any[];
  bankAccounts?: any[];
  portfolioId?: number | null;
}

// ── Component ───────────────────────────────────────────────────────────

const GenericAssetEditDialog: React.FC<GenericAssetEditDialogProps> = ({
  open,
  onClose,
  onSaved,
  asset,
  assetType,
  dematAccounts = [],
  bankAccounts = [],
  portfolioId,
}) => {
  const { notify } = useNotification();
  const config = getAssetTypeConfig(assetType);

  const [formData, setFormData] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [dialogError, setDialogError] = useState('');

  // Filter demat accounts for USD asset types
  const filteredDematAccounts = useMemo(() => {
    if (!config) return dematAccounts;
    if (config.filterDematMarket === 'INTERNATIONAL') {
      return dematAccounts.filter((da: any) =>
        da.account_market?.toLowerCase() === 'international' || da.currency === 'USD'
      );
    }
    // For ESOP/RSU with currency field, filter based on selected currency
    if ((assetType === 'esop' || assetType === 'rsu') && formData.currency) {
      if (formData.currency === 'USD') {
        return dematAccounts.filter((da: any) =>
          da.currency === 'USD' || da.account_market?.toLowerCase() === 'international'
        );
      }
      return dematAccounts.filter((da: any) =>
        da.currency === 'INR' || da.account_market?.toLowerCase() === 'domestic' || (!da.currency && !da.account_market)
      );
    }
    return dematAccounts;
  }, [config, dematAccounts, assetType, formData.currency]);

  // Populate form when dialog opens or asset changes
  useEffect(() => {
    if (!open || !config) return;

    const data: Record<string, any> = {};

    if (asset) {
      // Editing: populate from asset
      for (const field of config.fields) {
        if (field.isDetail) {
          data[field.name] = asset.details?.[field.name] ?? '';
        } else if (field.name === 'inr_value') {
          // Cash: inr_value maps to total_invested
          data[field.name] = asset.total_invested ?? '';
        } else {
          data[field.name] = asset[field.name] ?? '';
        }
      }

      // Handle US stock USD conversion
      if (config.currencyInput === 'USD') {
        data.purchase_price = toUSD(asset.purchase_price || 0, asset.details, 'avg_cost_usd');
        const totalInvUsd = asset.details?.avg_cost_usd
          ? asset.details.avg_cost_usd * asset.quantity
          : asset.total_invested;
        data.total_invested = totalInvUsd;
        data.current_price = toUSD(asset.current_price || 0, asset.details, 'price_usd');
      }

      // Handle ESOP: quantity maps to shares_vested, purchase_price to exercise_price
      if (assetType === 'esop') {
        data.shares_vested = asset.details?.shares_vested ?? asset.quantity ?? '';
        data.shares_granted = asset.details?.shares_granted ?? '';
        data.exercise_price = asset.details?.exercise_price ?? asset.purchase_price ?? '';
      }

      // Handle RSU: quantity maps to shares_vested
      if (assetType === 'rsu') {
        data.shares_vested = asset.details?.shares_vested ?? asset.quantity ?? '';
        data.shares_granted = asset.details?.shares_granted ?? '';
        data.fmv_at_grant = asset.details?.fmv_at_grant ?? '';
      }

      // Handle xirr (nullable)
      if ('xirr' in data) {
        data.xirr = asset.xirr ?? '';
      }

      // Account selectors
      if (config.accountType === 'demat') {
        data.demat_account_id = asset.demat_account_id ?? '';
      } else if (config.accountType === 'bank') {
        data.bank_account_id = asset.bank_account_id ?? '';
      }

      // Account ID / broker for SGB and similar
      if (!data.account_id && asset.account_id) data.account_id = asset.account_id;
      if (!data.broker_name && asset.broker_name) data.broker_name = asset.broker_name;
    } else {
      // Adding: set defaults
      for (const field of config.fields) {
        if (field.type === 'number') data[field.name] = '';
        else if (field.name === 'currency') data[field.name] = field.options?.[0]?.value ?? 'INR';
        else data[field.name] = '';
      }
      if (config.accountType === 'demat') data.demat_account_id = '';
      if (config.accountType === 'bank') data.bank_account_id = '';
    }

    data.portfolio_id = portfolioId || '';
    setFormData(data);
    setDialogError('');
  }, [open, asset, assetType, config, portfolioId]);

  if (!config) return null;

  const setField = (name: string, value: any) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // ── Submit ──────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    // Validate required fields
    for (const field of config.fields) {
      if (field.required && !String(formData[field.name] ?? '').trim()) {
        setDialogError(`${field.label} is required`);
        return;
      }
    }
    if (config.accountType === 'demat' && !formData.demat_account_id) {
      setDialogError('Demat account is required');
      return;
    }

    setDialogError('');

    try {
      setSubmitting(true);

      // Build details JSON from detail fields
      const details: Record<string, any> = {};
      for (const field of config.fields) {
        if (field.isDetail && formData[field.name] !== '' && formData[field.name] != null) {
          details[field.name] = field.type === 'number'
            ? parseFloat(formData[field.name]) || 0
            : formData[field.name];
        }
      }

      // Build main payload
      const payload: Record<string, unknown> = {
        asset_type: assetType,
      };

      // Map form fields to payload
      const nameVal = String(formData.name ?? '').trim();
      if (nameVal) payload.name = nameVal;
      const symbolVal = String(formData.symbol ?? '').trim();
      if (symbolVal) payload.symbol = symbolVal;
      const isinVal = String(formData.isin ?? '').trim();
      if (isinVal) payload.isin = isinVal;

      // Numeric main columns
      if (formData.quantity !== '' && formData.quantity != null) {
        payload.quantity = parseFloat(formData.quantity) || 0;
      }
      if (formData.purchase_price !== '' && formData.purchase_price != null) {
        payload.purchase_price = parseFloat(formData.purchase_price) || 0;
      }
      if (formData.current_price !== '' && formData.current_price != null) {
        payload.current_price = parseFloat(formData.current_price) || 0;
      }

      // Total invested
      if (formData.total_invested !== '' && formData.total_invested != null) {
        const ti = parseFloat(formData.total_invested) || 0;
        payload.total_invested = ti || ((payload.quantity as number || 0) * (payload.purchase_price as number || 0));
      } else if (payload.quantity != null && payload.purchase_price != null) {
        payload.total_invested = (payload.quantity as number) * (payload.purchase_price as number);
      }

      // ESOP special mapping
      if (assetType === 'esop') {
        payload.quantity = parseFloat(formData.shares_vested) || 0;
        payload.purchase_price = parseFloat(formData.exercise_price) || 0;
        payload.total_invested = (payload.quantity as number) * (payload.purchase_price as number);
        if (formData.currency === 'USD') {
          details.price_usd = parseFloat(formData.current_price) || 0;
        }
      }

      // RSU special mapping
      if (assetType === 'rsu') {
        payload.quantity = parseFloat(formData.shares_vested) || 0;
        payload.purchase_price = parseFloat(formData.fmv_at_grant) || 0;
        payload.total_invested = (payload.quantity as number) * (payload.purchase_price as number);
        if (formData.currency === 'USD') {
          details.price_usd = parseFloat(formData.current_price) || 0;
        }
      }

      // Cash special mapping
      if (assetType === 'cash') {
        const inrVal = parseFloat(formData.inr_value) || 0;
        payload.quantity = 1;
        payload.purchase_price = inrVal;
        payload.current_price = inrVal;
        payload.total_invested = inrVal;
        payload.symbol = formData.currency || 'INR';
      }

      // Post-office scheme special mapping (total_invested → quantity=1, purchase_price=total_invested)
      if (['nsc', 'kvp', 'scss', 'mis'].includes(assetType)) {
        const invested = parseFloat(formData.total_invested) || 0;
        const currentVal = parseFloat(formData.current_price) || invested;
        payload.quantity = 1;
        payload.purchase_price = invested;
        payload.total_invested = invested;
        payload.current_price = currentVal;
      }

      // XIRR
      const xirrVal = formData.xirr;
      if (xirrVal !== '' && xirrVal != null) {
        payload.xirr = parseFloat(xirrVal);
      }

      // Account
      if (config.accountType === 'demat' && formData.demat_account_id) {
        payload.demat_account_id = formData.demat_account_id;
      }
      if (config.accountType === 'bank' && formData.bank_account_id) {
        payload.bank_account_id = formData.bank_account_id;
      }

      // Broker / account_id (for SGB, bonds)
      if (formData.broker_name && !details.broker_name) {
        payload.broker_name = String(formData.broker_name).trim();
      }
      if (formData.account_id) {
        payload.account_id = String(formData.account_id).trim();
      }

      // Notes
      if (formData.notes) payload.notes = String(formData.notes).trim();

      // Portfolio
      if (formData.portfolio_id) payload.portfolio_id = formData.portfolio_id;

      // Attach details
      if (Object.keys(details).length > 0) {
        // Merge with existing details to preserve fields not in the form
        payload.details = { ...(asset?.details || {}), ...details };
      }

      if (asset) {
        await assetsAPI.update(asset.id, payload);
        notify.success(`${config.label} updated`);
      } else {
        await assetsAPI.create(payload);
        notify.success(`${config.label} added`);
      }

      onClose();
      onSaved();
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to save ${config.label}`));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Render field ────────────────────────────────────────────────────

  const renderField = (field: FieldDef) => {
    const value = formData[field.name] ?? '';

    if (field.type === 'currency_radio') {
      return (
        <Grid item xs={12} sm={field.half ? 6 : 12} key={field.name}>
          <RadioGroup
            row
            value={value || 'INR'}
            onChange={(e) => setField(field.name, e.target.value)}
          >
            {field.options?.map(opt => (
              <FormControlLabel key={opt.value} value={opt.value} control={<Radio size="small" />} label={opt.label} />
            ))}
          </RadioGroup>
        </Grid>
      );
    }

    if (field.type === 'select') {
      return (
        <Grid item xs={12} sm={field.half ? 6 : 12} key={field.name}>
          <TextField
            select
            fullWidth
            label={field.label}
            value={value}
            onChange={(e) => setField(field.name, e.target.value)}
            required={field.required}
            helperText={field.helperText}
          >
            {field.options?.map(opt => (
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
            ))}
          </TextField>
        </Grid>
      );
    }

    if (field.type === 'textarea') {
      return (
        <Grid item xs={12} key={field.name}>
          <TextField
            fullWidth
            multiline
            rows={2}
            label={field.label}
            value={value}
            onChange={(e) => setField(field.name, e.target.value)}
            helperText={field.helperText}
          />
        </Grid>
      );
    }

    if (field.type === 'date') {
      return (
        <Grid item xs={12} sm={field.half ? 6 : 12} key={field.name}>
          <TextField
            fullWidth
            label={field.label}
            type="date"
            value={value}
            onChange={(e) => setField(field.name, e.target.value)}
            InputLabelProps={{ shrink: true }}
            required={field.required}
            helperText={field.helperText}
          />
        </Grid>
      );
    }

    // text or number
    return (
      <Grid item xs={12} sm={field.half ? 6 : 12} key={field.name}>
        <TextField
          fullWidth
          label={field.label}
          type={field.type}
          value={value}
          onChange={(e) => {
            if (field.type === 'number') {
              setField(field.name, e.target.value === '' ? '' : e.target.value);
            } else {
              setField(field.name, e.target.value);
            }
          }}
          required={field.required}
          helperText={field.helperText}
          inputProps={field.type === 'number' ? { step: field.step || 'any', min: 0 } : undefined}
        />
      </Grid>
    );
  };

  // ── Account selector ────────────────────────────────────────────────

  const renderAccountSelector = () => {
    if (config.accountType === 'demat') {
      return (
        <Grid item xs={12}>
          <TextField
            select
            fullWidth
            label="Demat Account"
            value={formData.demat_account_id ?? ''}
            onChange={(e) => setField('demat_account_id', e.target.value ? Number(e.target.value) : '')}
            required
          >
            {filteredDematAccounts.map((da: any) => (
              <MenuItem key={da.id} value={da.id}>{buildDematLabel(da)}</MenuItem>
            ))}
          </TextField>
        </Grid>
      );
    }

    if (config.accountType === 'bank') {
      return (
        <Grid item xs={12}>
          <TextField
            select
            fullWidth
            label="Bank Account"
            value={formData.bank_account_id ?? ''}
            onChange={(e) => setField('bank_account_id', e.target.value ? Number(e.target.value) : '')}
          >
            {bankAccounts.map((ba: any) => (
              <MenuItem key={ba.id} value={ba.id}>
                {ba.bank_name} ({ba.account_number}){ba.nickname ? ` — ${ba.nickname}` : ''}
              </MenuItem>
            ))}
          </TextField>
        </Grid>
      );
    }

    return null;
  };

  const isEditing = !!asset;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEditing ? 'Edit' : 'Add'} {config.label}</DialogTitle>
      <DialogContent>
        {dialogError && <Alert severity="error" sx={{ mb: 2, mt: 1 }}>{dialogError}</Alert>}
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          {config.fields.map(renderField)}
          {renderAccountSelector()}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={submitting}
          startIcon={submitting ? <CircularProgress size={18} /> : isEditing ? <EditIcon /> : <AddIcon />}
        >
          {submitting ? 'Saving…' : isEditing ? 'Update' : `Add ${config.label}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default GenericAssetEditDialog;
