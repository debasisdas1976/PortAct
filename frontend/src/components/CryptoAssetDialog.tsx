import React, { useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  TextField,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon } from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface CryptoSearchResult {
  id: string;
  symbol: string;
  name: string;
}

export interface CryptoAssetForEdit {
  id: number;
  name: string;
  symbol: string;
  quantity: number;
  purchase_price: number;
  total_invested: number;
  current_price: number;
  xirr?: number | null;
  crypto_account_id?: number;
  details?: { coin_id?: string; currency?: string; price_usd?: number; usd_to_inr_rate?: number };
}

export interface CryptoAccountOption {
  id: number;
  label: string;
}

interface CryptoAssetDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  editingAsset?: CryptoAssetForEdit | null;
  fixedCryptoAccountId?: number;
  cryptoAccounts?: CryptoAccountOption[];
}

const formatINR = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value);

const formatUSD = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);

const CryptoAssetDialog: React.FC<CryptoAssetDialogProps> = ({
  open,
  onClose,
  onSaved,
  editingAsset = null,
  fixedCryptoAccountId,
  cryptoAccounts = [],
}) => {
  const { notify } = useNotification();

  const [formData, setFormData] = useState({
    name: '',
    symbol: '',
    coin_id: '',
    quantity: 0,
    purchase_price: 0,
    total_invested: 0,
    current_price: 0,
    xirr: null as number | null,
    currency: 'INR' as 'USD' | 'INR',
    crypto_account_id: '' as number | '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [cryptoOptions, setCryptoOptions] = useState<CryptoSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [priceInfo, setPriceInfo] = useState<{ usd: number; inr: number; rate: number } | null>(null);

  // Reset form when dialog opens
  const handleEnter = () => {
    if (editingAsset) {
      // DB values are in INR, so default to INR for edit
      setFormData({
        name: editingAsset.name,
        symbol: editingAsset.symbol || '',
        coin_id: editingAsset.details?.coin_id || '',
        quantity: editingAsset.quantity,
        purchase_price: editingAsset.purchase_price,
        total_invested: editingAsset.total_invested,
        current_price: editingAsset.current_price,
        xirr: editingAsset.xirr ?? null,
        currency: 'INR',
        crypto_account_id: editingAsset.crypto_account_id || '',
      });
      // Seed priceInfo from stored details so currency switching works
      const rate = editingAsset.details?.usd_to_inr_rate;
      const priceUsd = editingAsset.details?.price_usd;
      if (rate && priceUsd) {
        setPriceInfo({ usd: priceUsd, inr: priceUsd * rate, rate });
      } else {
        setPriceInfo(null);
      }
    } else {
      setFormData({
        name: '',
        symbol: '',
        coin_id: '',
        quantity: 0,
        purchase_price: 0,
        total_invested: 0,
        current_price: 0,
        xirr: null,
        currency: 'INR',
        crypto_account_id: fixedCryptoAccountId || '',
      });
      setPriceInfo(null);
    }
    setCryptoOptions([]);
  };

  const handleClose = () => {
    onClose();
    setCryptoOptions([]);
    setPriceInfo(null);
  };

  const searchCrypto = async (query: string) => {
    if (!query || query.length < 2) {
      setCryptoOptions([]);
      return;
    }
    setSearchLoading(true);
    try {
      const response = await api.get('/prices/crypto/search', { params: { query, limit: 10 } });
      setCryptoOptions(response.data.results || []);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to search crypto'));
    } finally {
      setSearchLoading(false);
    }
  };

  const fetchCryptoPrice = async (symbol: string) => {
    try {
      const response = await api.get(`/prices/crypto/${symbol}`);
      const { price: priceUsd, price_inr: priceInr, usd_to_inr_rate: rate } = response.data;
      const usd = priceUsd || 0;
      const inr = priceInr || 0;
      setPriceInfo({ usd, inr, rate: rate || (usd > 0 ? inr / usd : 0) });
      return { usd, inr };
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch price'));
      return null;
    }
  };

  const handleCurrencyChange = async (newCurrency: 'USD' | 'INR') => {
    if (newCurrency === formData.currency) return;

    // If we don't have a rate yet, fetch it
    let fetchedRate = priceInfo?.rate;
    if (!fetchedRate) {
      try {
        const response = await api.get('/prices/exchange-rate');
        const r: number | undefined = response.data.usd_to_inr;
        if (r) {
          fetchedRate = r;
          setPriceInfo((prev) => prev ? { ...prev, rate: r } : { usd: 0, inr: 0, rate: r });
        }
      } catch {
        // ignore - just switch label without converting
      }
    }

    if (!fetchedRate) {
      setFormData((prev) => ({ ...prev, currency: newCurrency }));
      return;
    }

    const rate = fetchedRate;
    setFormData((prev) => {
      const convert = newCurrency === 'INR'
        ? (v: number) => v * rate   // USD → INR
        : (v: number) => v / rate;  // INR → USD

      return {
        ...prev,
        currency: newCurrency,
        purchase_price: prev.purchase_price ? convert(prev.purchase_price) : 0,
        current_price: prev.current_price ? convert(prev.current_price) : 0,
        total_invested: prev.total_invested ? convert(prev.total_invested) : 0,
      };
    });
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      notify.error('Crypto name is required');
      return;
    }

    const accountId = fixedCryptoAccountId || formData.crypto_account_id;
    if (!accountId) {
      notify.error('Crypto account is required');
      return;
    }

    try {
      setSubmitting(true);
      const payload: Record<string, unknown> = {
        asset_type: 'crypto',
        name: formData.name.trim(),
        symbol: formData.symbol.trim() || undefined,
        quantity: formData.quantity,
        purchase_price: formData.purchase_price,
        total_invested: formData.total_invested || formData.quantity * formData.purchase_price,
        current_price: formData.current_price,
        ...(formData.xirr != null ? { xirr: formData.xirr } : {}),
        crypto_account_id: accountId,
        details: {
          coin_id: formData.coin_id || undefined,
          currency: formData.currency,
          price_usd: priceInfo?.usd || undefined,
          usd_to_inr_rate: priceInfo?.rate || undefined,
        },
      };

      if (editingAsset) {
        await api.put(`/assets/${editingAsset.id}`, payload);
        notify.success('Crypto asset updated');
      } else {
        await api.post('/assets/', payload);
        notify.success('Crypto asset added');
      }
      handleClose();
      onSaved();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to save crypto asset'));
    } finally {
      setSubmitting(false);
    }
  };

  const showAccountDropdown = !fixedCryptoAccountId && cryptoAccounts.length > 0;
  const currencySymbol = formData.currency === 'INR' ? '₹' : '$';

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      TransitionProps={{ onEnter: handleEnter }}
    >
      <DialogTitle>{editingAsset ? 'Edit Crypto Asset' : 'Add Crypto Asset'}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          {editingAsset ? (
            <>
              <TextField
                label="Crypto Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                fullWidth
                required
              />
              <TextField
                label="Symbol (e.g. BTC)"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                fullWidth
              />
            </>
          ) : (
            <Autocomplete
              options={cryptoOptions}
              getOptionLabel={(option) => `${option.symbol.toUpperCase()} - ${option.name}`}
              loading={searchLoading}
              onInputChange={(_, value) => searchCrypto(value)}
              onChange={async (_, value) => {
                if (value) {
                  setFormData((prev) => ({
                    ...prev,
                    name: value.name,
                    symbol: value.symbol.toUpperCase(),
                    coin_id: value.id,
                  }));
                  const prices = await fetchCryptoPrice(value.symbol);
                  if (prices) {
                    const price = formData.currency === 'INR' ? prices.inr : prices.usd;
                    setFormData((prev) => ({
                      ...prev,
                      current_price: price,
                      purchase_price: prev.purchase_price || price,
                    }));
                  }
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Search Cryptocurrency"
                  placeholder="Type BTC, ETH, etc."
                  required
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {searchLoading ? <CircularProgress size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
            />
          )}

          {priceInfo && (
            <Alert severity="info">
              Current Price: {formatINR(priceInfo.inr || 0)} ({formatUSD(priceInfo.usd || 0)}{priceInfo.rate ? ` at ₹${priceInfo.rate.toFixed(2)}/$` : ''})
            </Alert>
          )}

          <TextField
            select
            label="Currency"
            value={formData.currency}
            onChange={(e) => handleCurrencyChange(e.target.value as 'USD' | 'INR')}
            fullWidth
          >
            <MenuItem value="INR">INR (₹)</MenuItem>
            <MenuItem value="USD">USD ($)</MenuItem>
          </TextField>

          <TextField
            label="Quantity"
            type="number"
            value={formData.quantity}
            onChange={(e) => {
              const qty = parseFloat(e.target.value) || 0;
              setFormData((prev) => ({
                ...prev,
                quantity: qty,
                total_invested: qty * prev.purchase_price,
              }));
            }}
            fullWidth
            required
            inputProps={{ step: '0.000001' }}
          />

          <TextField
            label={`Average Buy Price (${currencySymbol})`}
            type="number"
            value={formData.purchase_price}
            onChange={(e) => {
              const price = parseFloat(e.target.value) || 0;
              setFormData((prev) => ({
                ...prev,
                purchase_price: price,
                total_invested: prev.quantity * price,
              }));
            }}
            fullWidth
            required
          />

          <TextField
            label={`Total Invested (${currencySymbol})`}
            type="number"
            value={formData.total_invested}
            onChange={(e) => setFormData({ ...formData, total_invested: parseFloat(e.target.value) || 0 })}
            fullWidth
            helperText="Auto-calculated (Qty x Avg Price). Override if needed."
          />

          <TextField
            label={`Current Price (${currencySymbol})`}
            type="number"
            value={formData.current_price}
            onChange={(e) => setFormData({ ...formData, current_price: parseFloat(e.target.value) || 0 })}
            fullWidth
            helperText="Auto-updated by price scheduler"
          />

          <TextField label="XIRR (%)" type="number" value={formData.xirr ?? ''} onChange={(e) => setFormData({ ...formData, xirr: e.target.value ? parseFloat(e.target.value) : null })} fullWidth helperText="Auto-calculated from transactions. Enter manually if needed." />

          {showAccountDropdown && (
            <TextField
              select
              label="Crypto Account"
              value={formData.crypto_account_id}
              onChange={(e) =>
                setFormData({ ...formData, crypto_account_id: e.target.value ? Number(e.target.value) : '' })
              }
              fullWidth
              required
              error={!formData.crypto_account_id}
              helperText={!formData.crypto_account_id ? 'Crypto assets must belong to a crypto account' : ''}
            >
              {cryptoAccounts.map((ca) => (
                <MenuItem key={ca.id} value={ca.id}>
                  {ca.label}
                </MenuItem>
              ))}
            </TextField>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={
            submitting ||
            !formData.name.trim() ||
            (!fixedCryptoAccountId && !formData.crypto_account_id)
          }
          startIcon={
            submitting ? <CircularProgress size={18} /> : editingAsset ? <EditIcon /> : <AddIcon />
          }
        >
          {submitting ? 'Saving…' : editingAsset ? 'Update' : 'Add Crypto Asset'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CryptoAssetDialog;
