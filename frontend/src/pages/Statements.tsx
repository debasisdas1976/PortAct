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
} from '@mui/material';
import {
  Upload,
  CloudUpload,
  AddCircleOutline,
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
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import api, { brokersAPI, banksAPI, cryptoExchangesAPI, institutionsAPI, statementsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
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

// --- Component ---

const Statements: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);

  // Account groups state
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // Simplified upload dialog (existing account)
  const [simpleUploadOpen, setSimpleUploadOpen] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<AccountItem | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Full upload dialog (Add New Account)
  const [fullUploadOpen, setFullUploadOpen] = useState(false);
  const [fullStatementType, setFullStatementType] = useState('');
  const [fullBroker, setFullBroker] = useState('');
  const [fullPassword, setFullPassword] = useState('');
  const [showFullPassword, setShowFullPassword] = useState(false);
  const [fullFile, setFullFile] = useState<File | null>(null);
  const [fullUploading, setFullUploading] = useState(false);
  const [uploadPortfolioId, setUploadPortfolioId] = useState<number | ''>('' as number | '');

  // Master data for full upload dialog
  const [brokersList, setBrokersList] = useState<{ value: string; label: string }[]>([]);
  const [banksList, setBanksList] = useState<{ value: string; label: string }[]>([]);
  const [exchangesList, setExchangesList] = useState<{ value: string; label: string }[]>([]);
  const [npsCraList, setNpsCraList] = useState<{ value: string; label: string }[]>([]);
  const [insuranceList, setInsuranceList] = useState<{ value: string; label: string }[]>([]);

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
      setBrokersList(
        Array.isArray(brokers) ? brokers.map((b: any) => ({ value: b.name, label: b.display_label })) : []
      );
      setBanksList(
        Array.isArray(banks) ? banks.map((b: any) => ({ value: b.name, label: b.display_label })) : []
      );
      setExchangesList(
        Array.isArray(exchanges) ? exchanges.map((e: any) => ({ value: e.name, label: e.display_label })) : []
      );
      setNpsCraList(
        Array.isArray(npsCras) ? npsCras.map((c: any) => ({ value: c.name, label: c.display_label })) : []
      );
      setInsuranceList(
        Array.isArray(insuranceProviders) ? insuranceProviders.map((i: any) => ({ value: i.name, label: i.display_label })) : []
      );
    } catch (err) {
      console.error('Failed to fetch master data for dropdowns', err);
    }
  };

  useEffect(() => {
    fetchAccountGroups();
  }, [fetchAccountGroups]);

  useEffect(() => {
    fetchMasterData();
  }, []);

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
    setUploadPortfolioId(selectedPortfolioId || '');
    setFullUploadOpen(true);
  };

  const handleFullFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setFullFile(event.target.files[0]);
    }
  };

  const handleFullUpload = async () => {
    if (!fullFile || !fullBroker || !fullStatementType) {
      notify.error('Please fill all fields and select a file');
      return;
    }

    try {
      setFullUploading(true);
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
      notify.success(response.data?.message || 'Statement uploaded and account created successfully');
      fetchAccountGroups();
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

  // --- Render ---

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Accounts & Statements</Typography>
        <Button
          variant="contained"
          startIcon={<AddCircleOutline />}
          onClick={openFullUpload}
        >
          Add New Account
        </Button>
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
                accept={uploadTarget?.upload_config.accepts || '.pdf,.csv,.xlsx'}
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
              onChange={(e) => { setFullStatementType(e.target.value); setFullBroker(''); }}
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

            <TextField
              select
              fullWidth
              label="Institution/Broker"
              value={fullBroker}
              onChange={(e) => setFullBroker(e.target.value)}
              sx={{ mb: 2 }}
              helperText={
                !fullStatementType ? 'Select a statement type first' :
                fullStatementType === 'ppf_statement' || fullStatementType === 'ssy_statement' ? 'Select bank or post office' :
                fullStatementType === 'nps_statement' ? 'Select CRA or fund manager' :
                fullStatementType === 'pf_statement' ? 'EPFO or employer name' :
                fullStatementType === 'bank_statement' ? 'Select your bank' :
                fullStatementType === 'insurance_statement' ? 'Select insurance provider' :
                'Select broker or institution'
              }
              disabled={!fullStatementType}
            >
              {['broker_statement', 'mutual_fund_statement', 'demat_statement'].includes(fullStatementType) &&
                brokersList.map((b) => (
                  <MenuItem key={b.value} value={b.value}>{b.label}</MenuItem>
                ))
              }
              {fullStatementType === 'crypto_statement' &&
                exchangesList.map((e) => (
                  <MenuItem key={e.value} value={e.value}>{e.label}</MenuItem>
                ))
              }
              {fullStatementType === 'vested_statement' && (
                <MenuItem value="vested">Vested</MenuItem>
              )}
              {fullStatementType === 'indmoney_statement' && (
                <MenuItem value="indmoney">INDMoney</MenuItem>
              )}
              {['bank_statement', 'ppf_statement', 'ssy_statement'].includes(fullStatementType) &&
                banksList.map((b) => (
                  <MenuItem key={b.value} value={b.value}>{b.label}</MenuItem>
                ))
              }
              {fullStatementType === 'nps_statement' &&
                npsCraList.map((c) => (
                  <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                ))
              }
              {fullStatementType === 'pf_statement' && (
                <MenuItem value="epfo">EPFO (Employees' Provident Fund Organisation)</MenuItem>
              )}
              {fullStatementType === 'insurance_statement' &&
                insuranceList.map((i) => (
                  <MenuItem key={i.value} value={i.value}>{i.label}</MenuItem>
                ))
              }
              <MenuItem value="other">Other</MenuItem>
            </TextField>

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
              <MenuItem value="">Default Portfolio</MenuItem>
              {portfolios.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </TextField>

            <Button
              variant="outlined"
              component="label"
              fullWidth
              startIcon={<Upload />}
              sx={{ mb: 2 }}
            >
              {fullFile ? fullFile.name : 'Select File'}
              <input
                type="file"
                hidden
                accept=".pdf,.csv,.xlsx"
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
            disabled={!fullFile || !fullBroker || !fullStatementType || fullUploading}
          >
            {fullUploading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Statements;
