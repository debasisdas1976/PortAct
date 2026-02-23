import React, { useState, useEffect } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';
import { statementsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface Suggestion {
  scheme_code: string;
  isin: string;
  scheme_name: string;
  nav: number;
  score: number;
  amc_name: string;
}

interface UnmatchedMF {
  asset_id: number;
  asset_name: string;
  asset_symbol: string;
  asset_type: string;
  suggestions: Suggestion[];
}

interface UnmatchedMFDialogProps {
  open: boolean;
  onClose: () => void;
  onResolved: () => void;
  statementId: number;
}

const UnmatchedMFDialog: React.FC<UnmatchedMFDialogProps> = ({
  open,
  onClose,
  onResolved,
  statementId,
}) => {
  const { notify } = useNotification();
  const [unmatchedMFs, setUnmatchedMFs] = useState<UnmatchedMF[]>([]);
  const [selections, setSelections] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open && statementId) {
      fetchUnmatchedMFs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, statementId]);

  const fetchUnmatchedMFs = async () => {
    setLoading(true);
    try {
      const data = await statementsAPI.getUnmatchedMFs(statementId);
      setUnmatchedMFs(data.unmatched_mfs || []);

      // Pre-select the highest-scoring suggestion for each MF
      const initialSelections: Record<number, string> = {};
      for (const mf of data.unmatched_mfs || []) {
        if (mf.suggestions && mf.suggestions.length > 0) {
          initialSelections[mf.asset_id] = mf.suggestions[0].isin;
        }
      }
      setSelections(initialSelections);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch unmatched mutual funds'));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectionChange = (assetId: number, isin: string) => {
    setSelections((prev) => {
      const next = { ...prev };
      if (isin === '__skip__') {
        delete next[assetId];
      } else {
        next[assetId] = isin;
      }
      return next;
    });
  };

  const handleResolve = async () => {
    // Build resolutions from selections
    const resolutions: Array<{
      asset_id: number;
      selected_isin: string;
      selected_scheme_name: string;
    }> = [];

    for (const [assetIdStr, isin] of Object.entries(selections)) {
      const assetId = Number(assetIdStr);
      const mf = unmatchedMFs.find((m) => m.asset_id === assetId);
      if (!mf) continue;
      const suggestion = mf.suggestions.find((s) => s.isin === isin);
      if (!suggestion) continue;
      resolutions.push({
        asset_id: assetId,
        selected_isin: suggestion.isin,
        selected_scheme_name: suggestion.scheme_name,
      });
    }

    if (resolutions.length === 0) {
      onClose();
      return;
    }

    setSubmitting(true);
    try {
      const result = await statementsAPI.resolveMFs(statementId, resolutions);
      if (result.resolved_count > 0) {
        notify.success(
          `Resolved ${result.resolved_count} mutual fund(s). Prices will update shortly.`
        );
      }
      if (result.errors && result.errors.length > 0) {
        notify.warning(`Some resolutions failed: ${result.errors.join(', ')}`);
      }
      onResolved();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to resolve mutual funds'));
    } finally {
      setSubmitting(false);
    }
  };

  const selectedCount = Object.keys(selections).length;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Resolve Unmatched Mutual Funds</DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : unmatchedMFs.length === 0 ? (
          <Alert severity="success" sx={{ mt: 1 }}>
            All mutual funds were matched successfully.
          </Alert>
        ) : (
          <>
            <Alert severity="info" sx={{ mb: 2 }}>
              {unmatchedMFs.length} mutual fund(s) could not be automatically matched
              to AMFI data. Please select the correct fund from the suggestions below,
              or skip to resolve later.
            </Alert>

            {unmatchedMFs.map((mf, index) => (
              <Box key={mf.asset_id}>
                {index > 0 && <Divider sx={{ my: 2 }} />}
                <Box sx={{ mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">
                    {mf.asset_name}
                  </Typography>
                  {mf.asset_symbol && (
                    <Typography variant="caption" color="text.secondary">
                      Symbol: {mf.asset_symbol}
                    </Typography>
                  )}
                </Box>

                {mf.suggestions.length === 0 ? (
                  <Alert severity="warning" sx={{ mb: 1 }}>
                    No matching schemes found in AMFI.
                  </Alert>
                ) : (
                  <FormControl fullWidth size="small">
                    <InputLabel>Select matching AMFI scheme</InputLabel>
                    <Select
                      value={selections[mf.asset_id] || '__skip__'}
                      onChange={(e) =>
                        handleSelectionChange(mf.asset_id, e.target.value)
                      }
                      label="Select matching AMFI scheme"
                    >
                      <MenuItem value="__skip__">
                        <em>Skip - resolve later</em>
                      </MenuItem>
                      {mf.suggestions.map((s) => (
                        <MenuItem key={s.isin} value={s.isin}>
                          <Box
                            sx={{
                              display: 'flex',
                              flexDirection: 'column',
                              width: '100%',
                              py: 0.5,
                            }}
                          >
                            <Box
                              sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                                {s.scheme_name}
                              </Typography>
                              <Chip
                                label={`${Math.round(s.score * 100)}%`}
                                size="small"
                                color={s.score >= 0.6 ? 'success' : s.score >= 0.4 ? 'warning' : 'default'}
                                sx={{ ml: 1, minWidth: 48 }}
                              />
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                              {s.amc_name} | ISIN: {s.isin} | NAV: {'\u20B9'}
                              {s.nav.toFixed(2)}
                            </Typography>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              </Box>
            ))}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>
          {unmatchedMFs.length === 0 ? 'Close' : 'Skip All'}
        </Button>
        {unmatchedMFs.length > 0 && (
          <Button
            variant="contained"
            onClick={handleResolve}
            disabled={submitting || selectedCount === 0}
            startIcon={submitting ? <CircularProgress size={18} /> : undefined}
          >
            {submitting
              ? 'Resolving...'
              : `Resolve ${selectedCount} Fund${selectedCount !== 1 ? 's' : ''}`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default UnmatchedMFDialog;
