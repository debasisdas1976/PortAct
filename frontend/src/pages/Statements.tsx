import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  IconButton,
  InputAdornment,
  Tooltip,
  TableContainer,
  Collapse,
  Alert,
} from '@mui/material';
import {
  Upload,
  CloudUpload,

  Visibility,
  VisibilityOff,
  KeyboardArrowDown,
  KeyboardArrowRight,
  AccountBalance,
  AccountBalanceWallet,
  CurrencyBitcoin,
  Savings,
  Shield,
  Work,
  ChildCare,
  TrendingUp,
  VolunteerActivism,
  Delete as DeleteIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import api, { brokersAPI, banksAPI, cryptoExchangesAPI, institutionsAPI, statementsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import UnmatchedMFDialog from '../components/UnmatchedMFDialog';
import SupportedInstitutionsSection from '../components/SupportedInstitutionsSection';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

// --- Types ---

interface UploadConfig {
  endpoint: string;
  pre_filled: Record<string, any>;
  fields_needed: string[];
  accepts: string;
}

interface AccountItem {
  account_source: string;
  account_id: number;
  asset_type?: string;
  display_name: string;
  institution_name?: string;
  sub_info?: string;
  last_statement_date?: string | null;
  upload_config: UploadConfig;
}

interface AccountGroup {
  group_type: string;
  display_name: string;
  accounts: AccountItem[];
}

// --- Icon map ---

const groupIcons: Record<string, React.ReactElement> = {
  demat_accounts: <AccountBalance />,
  bank_accounts: <AccountBalanceWallet />,
  crypto_accounts: <CurrencyBitcoin />,
  ppf: <Savings />,
  nps: <VolunteerActivism />,
  pf: <Work />,
  ssy: <ChildCare />,
  insurance: <Shield />,
  mutual_funds: <TrendingUp />,
};

/** Extract displayable format summary from supported_formats (handles JSON or legacy flat). */
const getDisplayFormats = (supportedFormats: string | null): string | null => {
  if (!supportedFormats) return null;
  try {
    const parsed = JSON.parse(supportedFormats);
    if (typeof parsed === 'object' && !Array.isArray(parsed)) {
      const allFormats = new Set<string>();
      for (const val of Object.values(parsed)) {
        if ((val as any).formats) {
          (val as any).formats.split(',').filter(Boolean).forEach((f: string) => allFormats.add(f.toUpperCase()));
        }
      }
      return allFormats.size > 0 ? Array.from(allFormats).join(', ') : null;
    }
  } catch {
    // Not JSON
  }
  return supportedFormats.toUpperCase();
};

/** Get accept string for file picker from supported_formats (handles JSON or legacy flat). */
const getAcceptFromFormats = (supportedFormats: string | null): string | null => {
  if (!supportedFormats) return null;
  try {
    const parsed = JSON.parse(supportedFormats);
    if (typeof parsed === 'object' && !Array.isArray(parsed)) {
      const allFormats = new Set<string>();
      for (const val of Object.values(parsed)) {
        if ((val as any).formats) {
          (val as any).formats.split(',').filter(Boolean).forEach((f: string) => allFormats.add(f));
        }
      }
      return allFormats.size > 0 ? Array.from(allFormats).map((f) => `.${f}`).join(',') : null;
    }
  } catch {
    // Not JSON
  }
  const fmts = supportedFormats.split(',').map((s) => s.trim()).filter(Boolean);
  return fmts.length > 0 ? fmts.map((f) => `.${f}`).join(',') : null;
};

// --- Component ---

const Statements: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);

  // Account groups state
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // Statement history state
  const [statements, setStatements] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Simplified upload dialog (existing account)
  const [simpleUploadOpen, setSimpleUploadOpen] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<AccountItem | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [simpleUploadPortfolioId, setSimpleUploadPortfolioId] = useState<number | ''>('' as number | '');

  // Full upload dialog (Add New Account)
  const [fullUploadOpen, setFullUploadOpen] = useState(false);
  const [fullStatementType, setFullStatementType] = useState('');
  const [fullBroker, setFullBroker] = useState('');
  const [fullPassword, setFullPassword] = useState('');
  const [showFullPassword, setShowFullPassword] = useState(false);
  const [fullFile, setFullFile] = useState<File | null>(null);
  const [fullUploading, setFullUploading] = useState(false);
  const [uploadPortfolioId, setUploadPortfolioId] = useState<number | ''>('' as number | '');

  // Unmatched MF resolution dialog
  const [unmatchedDialogOpen, setUnmatchedDialogOpen] = useState(false);
  const [unmatchedStatementId, setUnmatchedStatementId] = useState<number | null>(null);

  // Master data for full upload dialog
  const [brokersList, setBrokersList] = useState<{ value: string; label: string; has_parser: boolean; supported_formats: string | null }[]>([]);
  const [banksList, setBanksList] = useState<{ value: string; label: string; has_parser: boolean; supported_formats: string | null }[]>([]);
  const [exchangesList, setExchangesList] = useState<{ value: string; label: string; has_parser: boolean; supported_formats: string | null }[]>([]);
  const [npsCraList, setNpsCraList] = useState<{ value: string; label: string; has_parser: boolean; supported_formats: string | null }[]>([]);
  const [insuranceList, setInsuranceList] = useState<{ value: string; label: string; has_parser: boolean; supported_formats: string | null }[]>([]);

  // --- Data fetching ---

  const fetchAccountGroups = useCallback(async () => {
    try {
      setLoading(true);
      const data = await statementsAPI.getPortfolioAccounts(selectedPortfolioId);
      setGroups(data.groups || []);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load accounts'));
    } finally {
      setLoading(false);
    }
  }, [selectedPortfolioId]);

  const fetchMasterData = async () => {
    try {
      const [brokers, banks, exchanges, npsCras, insuranceProviders] = await Promise.all([
        brokersAPI.getAll({ is_active: true }),
        banksAPI.getAll({ is_active: true }),
        cryptoExchangesAPI.getAll({ is_active: true }),
        institutionsAPI.getAll({ is_active: true, category: 'nps_cra' }),
        institutionsAPI.getAll({ is_active: true, category: 'insurance_provider' }),
      ]);
      const mapItem = (item: any) => ({
        value: item.name,
        label: item.display_label,
        has_parser: item.has_parser ?? false,
        supported_formats: item.supported_formats ?? null,
      });
      setBrokersList(Array.isArray(brokers) ? brokers.map(mapItem) : []);
      setBanksList(Array.isArray(banks) ? banks.map(mapItem) : []);
      setExchangesList(Array.isArray(exchanges) ? exchanges.map(mapItem) : []);
      setNpsCraList(Array.isArray(npsCras) ? npsCras.map(mapItem) : []);
      setInsuranceList(Array.isArray(insuranceProviders) ? insuranceProviders.map(mapItem) : []);
    } catch (err) {
      console.error('Failed to fetch master data for dropdowns', err);
    }
  };

  const fetchStatements = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const data = await statementsAPI.getAll();
      setStatements(Array.isArray(data) ? data : []);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to load statement history'));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const handleDeleteStatement = async (statementId: number, filename: string) => {
    if (!window.confirm(`Delete statement "${filename}" and all assets/transactions imported from it?`)) {
      return;
    }
    try {
      await statementsAPI.delete(statementId);
      notify.success('Statement and associated data deleted successfully');
      fetchStatements();
      fetchAccountGroups();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete statement'));
    }
  };

  useEffect(() => {
    fetchAccountGroups();
  }, [fetchAccountGroups]);

  useEffect(() => {
    fetchMasterData();
  }, []);

  useEffect(() => {
    if (showHistory) {
      fetchStatements();
    }
  }, [showHistory, fetchStatements]);

  // --- Group collapse toggle ---

  const toggleGroup = (key: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // --- Simplified upload (existing account) ---

  const openSimplifiedUpload = (account: AccountItem) => {
    setUploadTarget(account);
    setSelectedFile(null);
    setPassword('');
    setShowPassword(false);
    // Default to the currently selected portfolio, or the user's default portfolio
    const defaultPortfolio = portfolios.find((p: any) => p.is_default);
    setSimpleUploadPortfolioId(selectedPortfolioId || defaultPortfolio?.id || '');
    setSimpleUploadOpen(true);
  };

  const handleSimpleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleSimplifiedUpload = async () => {
    if (!selectedFile || !uploadTarget) return;

    const { upload_config } = uploadTarget;
    const formData = new FormData();
    formData.append('file', selectedFile);

    // Add all pre-filled values
    for (const [key, value] of Object.entries(upload_config.pre_filled)) {
      formData.append(key, String(value));
    }

    // Add password if the field is needed and provided
    if (upload_config.fields_needed.includes('password') && password) {
      formData.append('password', password);
    }

    // Add portfolio_id
    if (simpleUploadPortfolioId) {
      formData.append('portfolio_id', String(simpleUploadPortfolioId));
    }

    try {
      setUploading(true);
      const response = await api.post(upload_config.endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      notify.success(response.data?.message || 'Statement uploaded successfully');
      setSimpleUploadOpen(false);
      setSelectedFile(null);
      setPassword('');
      setUploadTarget(null);
      fetchAccountGroups();

      // Check for unmatched mutual funds
      if (response.data?.unmatched_mf_count > 0) {
        setUnmatchedStatementId(response.data.statement_id);
        setUnmatchedDialogOpen(true);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement'));
    } finally {
      setUploading(false);
    }
  };

  // --- Full upload (Add New Account) ---

  const openFullUpload = () => {
    setFullFile(null);
    setFullStatementType('');
    setFullBroker('');
    setFullPassword('');
    setShowFullPassword(false);
    // Default to the currently selected portfolio, or the user's default portfolio
    const defaultPortfolio = portfolios.find((p: any) => p.is_default);
    setUploadPortfolioId(selectedPortfolioId || defaultPortfolio?.id || '');
    setFullUploadOpen(true);
  };

  const handleFullFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setFullFile(event.target.files[0]);
    }
  };

  // Statement types that have dedicated upload endpoints (auto-create accounts)
  const dedicatedUploadEndpoints: Record<string, string> = {
    'pf_statement': '/pf/upload',
    'ssy_statement': '/ssy/upload',
    'ppf_statement': '/ppf/upload',
    'nps_statement': '/nps/upload',
  };

  const handleFullUpload = async () => {
    if (!fullFile || !fullStatementType) {
      notify.error('Please select a statement type and file');
      return;
    }

    const dedicatedEndpoint = dedicatedUploadEndpoints[fullStatementType];

    // For dedicated endpoints, only file and password are needed
    if (!dedicatedEndpoint && !fullBroker) {
      notify.error('Please fill all fields and select a file');
      return;
    }

    try {
      setFullUploading(true);

      if (dedicatedEndpoint) {
        // Use dedicated endpoint — auto-creates account from statement
        const formData = new FormData();
        formData.append('file', fullFile);
        if (fullPassword) {
          formData.append('password', fullPassword);
        }
        if (uploadPortfolioId) {
          formData.append('portfolio_id', String(uploadPortfolioId));
        }

        await api.post(dedicatedEndpoint, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        setFullUploadOpen(false);
        notify.success('Statement processed and account created successfully');
        fetchAccountGroups();
        return;
      }

      // Generic upload for other statement types
      const formData = new FormData();
      formData.append('file', fullFile);
      formData.append('institution_name', fullBroker);
      formData.append('statement_type', fullStatementType);
      if (fullPassword) {
        formData.append('password', fullPassword);
      }
      if (uploadPortfolioId) {
        formData.append('portfolio_id', String(uploadPortfolioId));
      }

      const response = await api.post('/statements/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setFullUploadOpen(false);
      if (response.data?.needs_account_link) {
        notify.warning(
          'Statement processed but some holdings could not be linked to an account. ' +
          'Please check your accounts and link them manually.'
        );
      } else {
        notify.success(response.data?.message || 'Statement uploaded and account created successfully');
      }
      fetchAccountGroups();

      // Check for unmatched mutual funds
      if (response.data?.unmatched_mf_count > 0) {
        setUnmatchedStatementId(response.data.statement_id);
        setUnmatchedDialogOpen(true);
      }
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement'));
      setFullUploadOpen(false);
      fetchAccountGroups();
    } finally {
      setFullUploading(false);
    }
  };

  // --- Helpers ---

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatStatementType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'processed': return 'success';
      case 'processing': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  // --- Render ---

  return (
    <Box>
      {/* ========== Supported Institutions ========== */}
      <SupportedInstitutionsSection />

      {/* Page header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4">Accounts & Statements</Typography>
      </Box>

      {/* Loading state */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Empty state */}
      {!loading && groups.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            No accounts found for this portfolio.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Upload your first statement to create an account and import your holdings.
          </Typography>
          <Button
            variant="outlined"
            startIcon={<CloudUpload />}
            onClick={openFullUpload}
          >
            Upload First Statement
          </Button>
        </Paper>
      )}

      {/* Account groups */}
      {!loading && groups.map((group) => (
        <Paper key={group.group_type} sx={{ mb: 2, overflow: 'hidden' }}>
          {/* Group header */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              p: 2,
              cursor: 'pointer',
              bgcolor: 'action.hover',
              '&:hover': { bgcolor: 'action.selected' },
              userSelect: 'none',
            }}
            onClick={() => toggleGroup(group.group_type)}
          >
            {collapsedGroups.has(group.group_type)
              ? <KeyboardArrowRight sx={{ color: 'text.secondary' }} />
              : <KeyboardArrowDown sx={{ color: 'text.secondary' }} />
            }
            <Box sx={{ ml: 1, mr: 1, display: 'flex', alignItems: 'center', color: 'primary.main' }}>
              {groupIcons[group.group_type] || <AccountBalance />}
            </Box>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {group.display_name}
            </Typography>
            <Chip
              label={group.accounts.length}
              size="small"
              color="primary"
              variant="outlined"
            />
          </Box>

          {/* Account list (when expanded) */}
          {!collapsedGroups.has(group.group_type) && (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Account</TableCell>
                  <TableCell>Details</TableCell>
                  <TableCell>Last Statement</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {group.accounts.map((account) => (
                  <TableRow
                    key={`${account.account_source}-${account.account_id}`}
                    hover
                    sx={{ '&:last-child td': { borderBottom: 0 } }}
                  >
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {account.display_name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {account.sub_info}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(account.last_statement_date)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<CloudUpload />}
                        onClick={() => openSimplifiedUpload(account)}
                      >
                        Upload Statement
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      ))}

      {/* ========== Statement History Section ========== */}
      <Paper sx={{ mb: 2, overflow: 'hidden' }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            p: 2,
            cursor: 'pointer',
            bgcolor: 'action.hover',
            '&:hover': { bgcolor: 'action.selected' },
            userSelect: 'none',
          }}
          onClick={() => setShowHistory(!showHistory)}
        >
          {showHistory
            ? <KeyboardArrowDown sx={{ color: 'text.secondary' }} />
            : <KeyboardArrowRight sx={{ color: 'text.secondary' }} />
          }
          <Box sx={{ ml: 1, mr: 1, display: 'flex', alignItems: 'center', color: 'primary.main' }}>
            <HistoryIcon />
          </Box>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Statement History
          </Typography>
          {statements.length > 0 && (
            <Chip
              label={statements.length}
              size="small"
              color="primary"
              variant="outlined"
            />
          )}
        </Box>

        <Collapse in={showHistory}>
          {historyLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
              <CircularProgress size={28} />
            </Box>
          ) : statements.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography color="text.secondary">
                No statements uploaded yet.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Filename</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Institution</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="center">Assets</TableCell>
                    <TableCell>Uploaded</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {statements.map((stmt: any) => (
                    <TableRow key={stmt.id} hover>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                          {stmt.filename}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatStatementType(stmt.statement_type)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {stmt.institution_name || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={stmt.status}
                          size="small"
                          color={getStatusColor(stmt.status)}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2">
                          {stmt.assets_found || 0}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {formatDate(stmt.uploaded_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Delete statement and all imported data">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteStatement(stmt.id, stmt.filename)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Collapse>
      </Paper>

      {/* ========== Simplified Upload Dialog (existing account) ========== */}
      <Dialog open={simpleUploadOpen} onClose={() => setSimpleUploadOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Upload Statement for {uploadTarget?.display_name}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Button
              variant="outlined"
              component="label"
              fullWidth
              startIcon={<Upload />}
              sx={{ mb: 2 }}
            >
              {selectedFile ? selectedFile.name : 'Select File'}
              <input
                type="file"
                hidden
                accept={uploadTarget?.upload_config.accepts || '.pdf,.csv,.xlsx,.xls'}
                onChange={handleSimpleFileSelect}
              />
            </Button>

            {/* Password field — only when the field is needed and file is a PDF */}
            {uploadTarget?.upload_config.fields_needed.includes('password') &&
             selectedFile?.name.toLowerCase().endsWith('.pdf') && (
              <TextField
                fullWidth
                type={showPassword ? 'text' : 'password'}
                label="PDF Password (if encrypted)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Leave empty if not password-protected"
                helperText="Required for encrypted PDFs (e.g., NSDL CAS, passbook PDFs)"
                sx={{ mb: 2 }}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            )}

            <TextField
              select
              fullWidth
              label="Portfolio"
              value={simpleUploadPortfolioId}
              onChange={(e) => setSimpleUploadPortfolioId(e.target.value ? Number(e.target.value) : '')}
              sx={{ mb: 2 }}
              helperText="Assets from this statement will be assigned to the selected portfolio"
            >
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.name}{p.is_default ? ' (Default)' : ''}
                </MenuItem>
              ))}
            </TextField>

            {selectedFile && (
              <Typography variant="body2" color="text.secondary">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSimpleUploadOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSimplifiedUpload}
            variant="contained"
            disabled={!selectedFile || uploading}
          >
            {uploading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ========== Full Upload Dialog (Add New Account) ========== */}
      <Dialog open={fullUploadOpen} onClose={() => setFullUploadOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Statement for New Account</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <TextField
              select
              fullWidth
              label="Statement Type"
              value={fullStatementType}
              onChange={(e) => { setFullStatementType(e.target.value); setFullBroker(''); setFullFile(null); }}
              sx={{ mb: 2 }}
            >
              <MenuItem value="broker_statement">Broker Statement (Equity/Stocks)</MenuItem>
              <MenuItem value="mutual_fund_statement">Mutual Fund Statement</MenuItem>
              <MenuItem value="demat_statement">Demat Statement (Consolidated)</MenuItem>
              <MenuItem value="vested_statement">Vested Statement (US Stocks)</MenuItem>
              <MenuItem value="indmoney_statement">INDMoney Statement (US Stocks)</MenuItem>
              <MenuItem value="bank_statement">Bank Statement</MenuItem>
              <MenuItem value="ppf_statement">PPF Statement</MenuItem>
              <MenuItem value="ssy_statement">SSY Statement (Sukanya Samriddhi Yojana)</MenuItem>
              <MenuItem value="nps_statement">NPS Statement (National Pension System)</MenuItem>
              <MenuItem value="pf_statement">PF/EPF Statement (Provident Fund)</MenuItem>
              <MenuItem value="crypto_statement">Crypto Statement</MenuItem>
              <MenuItem value="insurance_statement">Insurance Statement</MenuItem>
              <MenuItem value="other">Other</MenuItem>
            </TextField>

            {/* Info alert for statement types with dedicated endpoints */}
            {fullStatementType in dedicatedUploadEndpoints && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Just select the PDF file below. The account will be created automatically from the statement.
              </Alert>
            )}

            {/* Institution/Broker — hidden for types with dedicated endpoints */}
            {!(fullStatementType in dedicatedUploadEndpoints) && (
              <TextField
                select
                fullWidth
                label="Institution/Broker"
                value={fullBroker}
                onChange={(e) => { setFullBroker(e.target.value); setFullFile(null); }}
                sx={{ mb: 2 }}
                helperText={
                  !fullStatementType ? 'Select a statement type first' :
                  fullStatementType === 'ppf_statement' || fullStatementType === 'ssy_statement' ? 'Select bank or post office' :
                  fullStatementType === 'nps_statement' ? 'Select CRA or fund manager' :
                  fullStatementType === 'bank_statement' ? 'Select your bank' :
                  fullStatementType === 'insurance_statement' ? 'Select insurance provider' :
                  'Select broker or institution'
                }
                disabled={!fullStatementType}
              >
                {['broker_statement', 'mutual_fund_statement', 'demat_statement'].includes(fullStatementType) &&
                  brokersList.filter((b) => b.has_parser).map((b) => (
                    <MenuItem key={b.value} value={b.value}>
                      {b.label}
                      {b.supported_formats && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          ({b.supported_formats.toUpperCase()})
                        </Typography>
                      )}
                    </MenuItem>
                  ))
                }
                {fullStatementType === 'crypto_statement' &&
                  exchangesList.filter((e) => e.has_parser).map((e) => (
                    <MenuItem key={e.value} value={e.value}>
                      {e.label}
                      {e.supported_formats && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          ({e.supported_formats.toUpperCase()})
                        </Typography>
                      )}
                    </MenuItem>
                  ))
                }
                {fullStatementType === 'vested_statement' && (
                  <MenuItem value="vested">Vested</MenuItem>
                )}
                {fullStatementType === 'indmoney_statement' && (
                  <MenuItem value="indmoney">INDMoney</MenuItem>
                )}
                {['bank_statement'].includes(fullStatementType) &&
                  banksList.filter((b) => b.has_parser).map((b) => {
                    const fmtDisplay = getDisplayFormats(b.supported_formats);
                    return (
                      <MenuItem key={b.value} value={b.value}>
                        {b.label}
                        {fmtDisplay && (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                            ({fmtDisplay})
                          </Typography>
                        )}
                      </MenuItem>
                    );
                  })
                }
                {['ppf_statement', 'ssy_statement'].includes(fullStatementType) &&
                  banksList.map((b) => (
                    <MenuItem key={b.value} value={b.value}>{b.label}</MenuItem>
                  ))
                }
                {fullStatementType === 'nps_statement' &&
                  npsCraList.map((c) => (
                    <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                  ))
                }
                {fullStatementType === 'insurance_statement' &&
                  insuranceList.map((i) => (
                    <MenuItem key={i.value} value={i.value}>{i.label}</MenuItem>
                  ))
                }
                <MenuItem value="other">Other</MenuItem>
              </TextField>
            )}

            {fullFile && fullFile.name.toLowerCase().endsWith('.pdf') && (
              <TextField
                fullWidth
                type={showFullPassword ? 'text' : 'password'}
                label="PDF Password (if encrypted)"
                value={fullPassword}
                onChange={(e) => setFullPassword(e.target.value)}
                placeholder="Leave empty if not password-protected"
                helperText="Required for NSDL CAS and other encrypted PDFs"
                sx={{ mb: 2 }}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => setShowFullPassword(!showFullPassword)} edge="end">
                        {showFullPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            )}

            <TextField
              select
              fullWidth
              label="Portfolio"
              value={uploadPortfolioId}
              onChange={(e) => setUploadPortfolioId(e.target.value ? Number(e.target.value) : '')}
              sx={{ mb: 2 }}
              helperText="Assets from this statement will be assigned to the selected portfolio"
            >
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.name}{p.is_default ? ' (Default)' : ''}
                </MenuItem>
              ))}
            </TextField>

            <Button
              variant="outlined"
              component="label"
              fullWidth
              startIcon={<Upload />}
              sx={{ mb: 2 }}
            >
              {fullFile ? fullFile.name : (() => {
                // Compute display label from selected institution's formats
                const inst =
                  ['broker_statement', 'mutual_fund_statement', 'demat_statement', 'vested_statement', 'indmoney_statement'].includes(fullStatementType)
                    ? brokersList.find((b) => b.value === fullBroker)
                  : fullStatementType === 'crypto_statement'
                    ? exchangesList.find((e) => e.value === fullBroker)
                  : fullStatementType === 'bank_statement'
                    ? banksList.find((b) => b.value === fullBroker)
                  : null;
                if (inst) {
                  const display = getDisplayFormats(inst.supported_formats);
                  if (display) return `Select File (.${display.replace(/, /g, ' / .')})`;
                }
                return 'Select File';
              })()}
              <input
                type="file"
                hidden
                accept={(() => {
                  const inst =
                    ['broker_statement', 'mutual_fund_statement', 'demat_statement', 'vested_statement', 'indmoney_statement'].includes(fullStatementType)
                      ? brokersList.find((b) => b.value === fullBroker)
                    : fullStatementType === 'crypto_statement'
                      ? exchangesList.find((e) => e.value === fullBroker)
                    : fullStatementType === 'bank_statement'
                      ? banksList.find((b) => b.value === fullBroker)
                    : null;
                  if (inst) {
                    const accept = getAcceptFromFormats(inst.supported_formats);
                    if (accept) return accept;
                  }
                  return '.pdf,.csv,.xlsx,.xls';
                })()}
                onChange={handleFullFileSelect}
              />
            </Button>

            {fullFile && (
              <Typography variant="body2" color="text.secondary">
                Selected: {fullFile.name} ({(fullFile.size / 1024).toFixed(2)} KB)
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFullUploadOpen(false)}>Cancel</Button>
          <Button
            onClick={handleFullUpload}
            variant="contained"
            disabled={
              !fullFile || !fullStatementType || fullUploading ||
              (!(fullStatementType in dedicatedUploadEndpoints) && !fullBroker)
            }
          >
            {fullUploading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Unmatched MF Resolution Dialog */}
      {unmatchedStatementId && (
        <UnmatchedMFDialog
          open={unmatchedDialogOpen}
          onClose={() => setUnmatchedDialogOpen(false)}
          onResolved={() => {
            setUnmatchedDialogOpen(false);
            fetchAccountGroups();
          }}
          statementId={unmatchedStatementId}
        />
      )}
    </Box>
  );
};

export default Statements;
