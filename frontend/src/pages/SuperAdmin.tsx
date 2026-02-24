import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  Box,
  Checkbox,
  Chip,
  CircularProgress,
  FormControl,
  FormGroup,
  FormControlLabel,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Save as SaveIcon,
  Undo as UndoIcon,
  AdminPanelSettings as AdminIcon,
} from '@mui/icons-material';
import { banksAPI, brokersAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import CompanyIcon from '../components/CompanyIcon';

// ── Constants ──────────────────────────────────────────────────────────────────

const ALL_FORMATS = ['pdf', 'csv', 'xlsx', 'xls', 'txt'] as const;

const ACCOUNT_TYPES = [
  { value: 'savings', label: 'Savings' },
  { value: 'current', label: 'Current' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'fixed_deposit', label: 'Fixed Deposit' },
  { value: 'recurring_deposit', label: 'Recurring Deposit' },
] as const;

// ── Types ──────────────────────────────────────────────────────────────────────

interface BankRow {
  id: number;
  name: string;
  display_label: string;
  bank_type: string;
  website: string | null;
  is_active: boolean;
  has_parser: boolean;
  supported_formats: string | null;
}

interface BrokerRow {
  id: number;
  name: string;
  display_label: string;
  broker_type: string;
  supported_markets: string;
  website: string | null;
  is_active: boolean;
  has_parser: boolean;
  supported_formats: string | null;
}

interface AccountTypeConfig {
  has_parser: boolean;
  formats: string[];
}

type BankConfig = Record<string, AccountTypeConfig>;

type BrokerDirtyMap = Record<number, { has_parser?: boolean; supported_formats?: string | null }>;

// ── Config parse / encode ──────────────────────────────────────────────────────

/** Build an empty config with all account types set to no-parser / no-formats. */
const emptyConfig = (): BankConfig => {
  const c: BankConfig = {};
  for (const at of ACCOUNT_TYPES) c[at.value] = { has_parser: false, formats: [] };
  return c;
};

/** Parse the bank's supported_formats field into per-account-type config. */
const parseBankConfig = (supportedFormats: string | null, hasParser: boolean): BankConfig => {
  if (supportedFormats) {
    try {
      const parsed = JSON.parse(supportedFormats);
      if (typeof parsed === 'object' && !Array.isArray(parsed)) {
        // New JSON format
        const config = emptyConfig();
        for (const at of ACCOUNT_TYPES) {
          if (parsed[at.value]) {
            config[at.value] = {
              has_parser: !!parsed[at.value].has_parser,
              formats: parsed[at.value].formats
                ? parsed[at.value].formats.split(',').filter(Boolean)
                : [],
            };
          }
        }
        return config;
      }
    } catch {
      // Not JSON — fall through to legacy handling
    }

    // Legacy flat comma-separated format (e.g. "pdf,csv,xlsx")
    const formats = supportedFormats.split(',').map((s) => s.trim()).filter(Boolean);
    const config = emptyConfig();
    for (const at of ACCOUNT_TYPES) {
      config[at.value] = { has_parser: hasParser, formats: [...formats] };
    }
    return config;
  }

  // No supported_formats value
  if (hasParser) {
    const config = emptyConfig();
    for (const at of ACCOUNT_TYPES) config[at.value].has_parser = true;
    return config;
  }

  return emptyConfig();
};

/** Encode per-account-type config back to bank-level fields for the API. */
const encodeBankConfig = (
  config: BankConfig
): { has_parser: boolean; supported_formats: string | null } => {
  const hasAnyParser = Object.values(config).some((c) => c.has_parser);

  const json: Record<string, any> = {};
  for (const [key, val] of Object.entries(config)) {
    if (val.has_parser || val.formats.length > 0) {
      json[key] = { has_parser: val.has_parser, formats: val.formats.join(',') };
    }
  }

  const supported_formats = Object.keys(json).length > 0 ? JSON.stringify(json) : null;
  return { has_parser: hasAnyParser, supported_formats };
};

// Broker helpers (flat comma-separated, unchanged)
const parseFormats = (val: string | null): string[] => {
  if (!val) return [];
  return val.split(',').map((s) => s.trim()).filter(Boolean);
};

const joinFormats = (arr: string[]): string | null => (arr.length > 0 ? arr.join(',') : null);

// ── Component ──────────────────────────────────────────────────────────────────

const SuperAdmin: React.FC = () => {
  const { notify } = useNotification();
  const [banks, setBanks] = useState<BankRow[]>([]);
  const [brokers, setBrokers] = useState<BrokerRow[]>([]);
  const [loading, setLoading] = useState(true);

  // Bank: per-account-type config state
  const [bankConfigs, setBankConfigs] = useState<Record<number, BankConfig>>({});
  const [originalBankConfigs, setOriginalBankConfigs] = useState<Record<number, BankConfig>>({});
  const [savingBank, setSavingBank] = useState<number | null>(null);

  // Broker: simple dirty-map
  const [brokerDirty, setBrokerDirty] = useState<BrokerDirtyMap>({});
  const [savingBroker, setSavingBroker] = useState<number | null>(null);

  // ── Data loading ─────────────────────────────────────────────────────────────

  const initBankConfigs = useCallback((bankData: BankRow[]) => {
    const configs: Record<number, BankConfig> = {};
    for (const bank of bankData) {
      configs[bank.id] = parseBankConfig(bank.supported_formats, bank.has_parser);
    }
    setBankConfigs(configs);
    setOriginalBankConfigs(JSON.parse(JSON.stringify(configs)));
  }, []);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        setLoading(true);
        const [bankData, brokerData] = await Promise.all([
          banksAPI.getAll(),
          brokersAPI.getAll(),
        ]);
        setBanks(bankData);
        setBrokers(brokerData);
        initBankConfigs(bankData);
        setBrokerDirty({});
      } catch (err) {
        notify.error(getErrorMessage(err, 'Failed to fetch data'));
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Bank helpers ─────────────────────────────────────────────────────────────

  const isBankDirty = (bankId: number) =>
    JSON.stringify(bankConfigs[bankId]) !== JSON.stringify(originalBankConfigs[bankId]);

  const toggleBankParser = (bankId: number, accountType: string) => {
    setBankConfigs((prev) => ({
      ...prev,
      [bankId]: {
        ...prev[bankId],
        [accountType]: {
          ...prev[bankId][accountType],
          has_parser: !prev[bankId][accountType].has_parser,
        },
      },
    }));
  };

  const toggleBankFormat = (bankId: number, accountType: string, format: string) => {
    setBankConfigs((prev) => {
      const current = prev[bankId][accountType].formats;
      const newFormats = current.includes(format)
        ? current.filter((f) => f !== format)
        : [...current, format].sort(
            (a, b) => ALL_FORMATS.indexOf(a as any) - ALL_FORMATS.indexOf(b as any)
          );
      return {
        ...prev,
        [bankId]: {
          ...prev[bankId],
          [accountType]: { ...prev[bankId][accountType], formats: newFormats },
        },
      };
    });
  };

  const resetBank = (bankId: number) => {
    setBankConfigs((prev) => ({
      ...prev,
      [bankId]: JSON.parse(JSON.stringify(originalBankConfigs[bankId])),
    }));
  };

  const saveBank = async (bank: BankRow) => {
    const config = bankConfigs[bank.id];
    const payload = encodeBankConfig(config);
    try {
      setSavingBank(bank.id);
      await banksAPI.update(bank.id, payload);
      notify.success(`Updated ${bank.display_label}`);
      const updated = await banksAPI.getAll();
      setBanks(updated);
      initBankConfigs(updated);
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to update ${bank.display_label}`));
    } finally {
      setSavingBank(null);
    }
  };

  // ── Broker helpers ───────────────────────────────────────────────────────────

  const getBrokerValue = (broker: BrokerRow, field: 'has_parser' | 'supported_formats') => {
    const dirty = brokerDirty[broker.id];
    if (dirty && field in dirty) return dirty[field];
    return broker[field];
  };

  const setBrokerField = (id: number, field: 'has_parser' | 'supported_formats', value: any) => {
    setBrokerDirty((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));
  };

  const isBrokerDirty = (id: number) => !!brokerDirty[id];

  const resetBroker = (id: number) => {
    setBrokerDirty((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const saveBroker = async (broker: BrokerRow) => {
    const dirty = brokerDirty[broker.id];
    if (!dirty) return;
    try {
      setSavingBroker(broker.id);
      await brokersAPI.update(broker.id, dirty);
      notify.success(`Updated ${broker.display_label}`);
      const updated = await brokersAPI.getAll();
      setBrokers(updated);
      resetBroker(broker.id);
    } catch (err) {
      notify.error(getErrorMessage(err, `Failed to update ${broker.display_label}`));
    } finally {
      setSavingBroker(null);
    }
  };

  const toggleBrokerFormat = (
    currentFormats: string | null,
    format: string,
    setter: (field: 'supported_formats', value: string | null) => void
  ) => {
    const arr = parseFormats(currentFormats);
    const idx = arr.indexOf(format);
    if (idx >= 0) arr.splice(idx, 1);
    else arr.push(format);
    const ordered = (ALL_FORMATS as readonly string[]).filter((f) => arr.includes(f));
    setter('supported_formats', joinFormats(ordered));
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const dirtyBankCount = banks.filter((b) => isBankDirty(b.id)).length;
  const dirtyBrokerCount = Object.keys(brokerDirty).length;
  const totalDirty = dirtyBankCount + dirtyBrokerCount;

  const thickBorder = '2px solid';

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <AdminIcon color="warning" />
        <Typography variant="h4">Super Admin</Typography>
        <Chip label="DEV ONLY" color="warning" size="small" sx={{ ml: 1 }} />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage parser availability and supported file formats for Banks and Brokers (Demat Accounts).
        {totalDirty > 0 && (
          <Chip label={`${totalDirty} unsaved`} color="error" size="small" sx={{ ml: 1 }} />
        )}
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        This page is not included in production builds or git. Access it directly via{' '}
        <strong>/super-admin</strong>.
      </Alert>

      {/* ── Banks Section (5 rows per bank) ─────────────────────────────────── */}
      <Typography variant="h5" sx={{ mb: 2 }}>
        Banks
      </Typography>
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ minWidth: 180 }}>
                <strong>Bank</strong>
              </TableCell>
              <TableCell sx={{ minWidth: 130 }}>
                <strong>Account Type</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Has Parser</strong>
              </TableCell>
              {ALL_FORMATS.map((fmt) => (
                <TableCell key={fmt} align="center" sx={{ minWidth: 50 }}>
                  <strong>{fmt.toUpperCase()}</strong>
                </TableCell>
              ))}
              <TableCell align="center" sx={{ minWidth: 80 }}>
                <strong>Actions</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {banks.map((bank) => {
              const config = bankConfigs[bank.id];
              if (!config) return null;
              const dirty = isBankDirty(bank.id);
              const saving = savingBank === bank.id;

              return ACCOUNT_TYPES.map((at, idx) => {
                const atConfig = config[at.value];
                const isLast = idx === ACCOUNT_TYPES.length - 1;
                const borderSx = isLast
                  ? { borderBottom: thickBorder, borderBottomColor: 'divider' }
                  : {};

                return (
                  <TableRow
                    key={`${bank.id}-${at.value}`}
                    sx={dirty ? { bgcolor: 'action.selected' } : undefined}
                  >
                    {/* Bank name — first row only, spans 5 rows */}
                    {idx === 0 && (
                      <TableCell
                        rowSpan={ACCOUNT_TYPES.length}
                        sx={{
                          verticalAlign: 'top',
                          pt: 1.5,
                          borderBottom: thickBorder,
                          borderBottomColor: 'divider',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <CompanyIcon website={bank.website} name={bank.display_label} />
                          <Box>
                            <Typography variant="body2" fontWeight={500}>
                              {bank.display_label}
                            </Typography>
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              fontFamily="monospace"
                            >
                              {bank.name}
                            </Typography>
                            <Box sx={{ mt: 0.5 }}>
                              <Chip
                                label={bank.is_active ? 'Active' : 'Inactive'}
                                color={bank.is_active ? 'success' : 'default'}
                                size="small"
                              />
                            </Box>
                          </Box>
                        </Box>
                      </TableCell>
                    )}

                    {/* Account Type */}
                    <TableCell sx={borderSx}>
                      <Typography variant="body2">{at.label}</Typography>
                    </TableCell>

                    {/* Has Parser */}
                    <TableCell align="center" sx={borderSx}>
                      <Checkbox
                        checked={atConfig.has_parser}
                        onChange={() => toggleBankParser(bank.id, at.value)}
                        size="small"
                      />
                    </TableCell>

                    {/* Format checkboxes */}
                    {ALL_FORMATS.map((fmt) => (
                      <TableCell key={fmt} align="center" sx={borderSx}>
                        <Checkbox
                          checked={atConfig.formats.includes(fmt)}
                          onChange={() => toggleBankFormat(bank.id, at.value, fmt)}
                          size="small"
                        />
                      </TableCell>
                    ))}

                    {/* Actions — first row only, spans 5 rows */}
                    {idx === 0 && (
                      <TableCell
                        rowSpan={ACCOUNT_TYPES.length}
                        align="center"
                        sx={{
                          verticalAlign: 'top',
                          pt: 1.5,
                          borderBottom: thickBorder,
                          borderBottomColor: 'divider',
                        }}
                      >
                        <Tooltip title="Save">
                          <span>
                            <IconButton
                              size="small"
                              color="primary"
                              disabled={!dirty || saving}
                              onClick={() => saveBank(bank)}
                            >
                              {saving ? (
                                <CircularProgress size={18} />
                              ) : (
                                <SaveIcon fontSize="small" />
                              )}
                            </IconButton>
                          </span>
                        </Tooltip>
                        <br />
                        <Tooltip title="Undo changes">
                          <span>
                            <IconButton
                              size="small"
                              color="default"
                              disabled={!dirty}
                              onClick={() => resetBank(bank.id)}
                            >
                              <UndoIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    )}
                  </TableRow>
                );
              });
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ── Brokers Section (1 row per broker, unchanged) ───────────────────── */}
      <Typography variant="h5" sx={{ mb: 2 }}>
        Brokers (Demat Accounts)
      </Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Broker</strong>
              </TableCell>
              <TableCell>
                <strong>Type</strong>
              </TableCell>
              <TableCell>
                <strong>Markets</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Status</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Has Parser</strong>
              </TableCell>
              <TableCell>
                <strong>Supported Formats</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Actions</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {brokers.map((broker) => {
              const hasParser = getBrokerValue(broker, 'has_parser') as boolean;
              const formats = getBrokerValue(broker, 'supported_formats') as string | null;
              const dirty = isBrokerDirty(broker.id);
              const saving = savingBroker === broker.id;

              return (
                <TableRow
                  key={broker.id}
                  hover
                  sx={dirty ? { bgcolor: 'action.selected' } : undefined}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CompanyIcon website={broker.website} name={broker.display_label} />
                      <Box>
                        <Typography variant="body2">{broker.display_label}</Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          fontFamily="monospace"
                        >
                          {broker.name}
                        </Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={broker.broker_type
                        .replace('_', ' ')
                        .replace(/\b\w/g, (c) => c.toUpperCase())}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={broker.supported_markets.replace(/\b\w/g, (c) => c.toUpperCase())}
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
                  <TableCell align="center">
                    <Checkbox
                      checked={hasParser}
                      onChange={(e) => setBrokerField(broker.id, 'has_parser', e.target.checked)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <FormControl component="fieldset">
                      <FormGroup row>
                        {ALL_FORMATS.map((fmt) => (
                          <FormControlLabel
                            key={fmt}
                            control={
                              <Checkbox
                                checked={parseFormats(formats).includes(fmt)}
                                onChange={() =>
                                  toggleBrokerFormat(formats, fmt, (field, val) =>
                                    setBrokerField(broker.id, field, val)
                                  )
                                }
                                size="small"
                              />
                            }
                            label={
                              <Typography variant="caption">{fmt.toUpperCase()}</Typography>
                            }
                            sx={{ mr: 1 }}
                          />
                        ))}
                      </FormGroup>
                    </FormControl>
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Save">
                      <span>
                        <IconButton
                          size="small"
                          color="primary"
                          disabled={!dirty || saving}
                          onClick={() => saveBroker(broker)}
                        >
                          {saving ? (
                            <CircularProgress size={18} />
                          ) : (
                            <SaveIcon fontSize="small" />
                          )}
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Undo changes">
                      <span>
                        <IconButton
                          size="small"
                          color="default"
                          disabled={!dirty}
                          onClick={() => resetBroker(broker.id)}
                        >
                          <UndoIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default SuperAdmin;
