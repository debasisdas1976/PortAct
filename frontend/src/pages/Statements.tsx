import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
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
  Tooltip,
  InputAdornment,
} from '@mui/material';
import { Upload, CloudUpload, Delete, Visibility, VisibilityOff } from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import api, { brokersAPI, banksAPI, cryptoExchangesAPI, institutionsAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';
import { useSelectedPortfolio } from '../hooks/useSelectedPortfolio';

interface Statement {
  id: number;
  filename: string;
  uploaded_at: string;
  status: string;
  institution_name: string;
  statement_type: string;
  assets_found: number;
  transactions_found: number;
}

const Statements: React.FC = () => {
  const { notify } = useNotification();
  const selectedPortfolioId = useSelectedPortfolio();
  const portfolios = useSelector((state: RootState) => state.portfolio.portfolios);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [statementToDelete, setStatementToDelete] = useState<Statement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [broker, setBroker] = useState('');
  const [statementType, setStatementType] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [uploadPortfolioId, setUploadPortfolioId] = useState<number | ''>('' as number | '');
  const [brokersList, setBrokersList] = useState<{ value: string; label: string }[]>([]);
  const [banksList, setBanksList] = useState<{ value: string; label: string }[]>([]);
  const [exchangesList, setExchangesList] = useState<{ value: string; label: string }[]>([]);
  const [npsCraList, setNpsCraList] = useState<{ value: string; label: string }[]>([]);
  const [insuranceList, setInsuranceList] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    fetchStatements();
    fetchMasterData();
  }, []);

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
      // Non-critical: dropdowns will just be empty; user can still select "other"
      console.error('Failed to fetch master data for dropdowns', err);
    }
  };

  const fetchStatements = async () => {
    try {
      setLoading(true);
      const response = await api.get('/statements/');
      setStatements(response.data);
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to fetch statements'));
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !broker || !statementType) {
      notify.error('Please fill all fields and select a file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('institution_name', broker);
      formData.append('statement_type', statementType);
      if (password) {
        formData.append('password', password);
      }
      if (uploadPortfolioId) {
        formData.append('portfolio_id', String(uploadPortfolioId));
      }

      await api.post('/statements/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadDialogOpen(false);
      setSelectedFile(null);
      setBroker('');
      setStatementType('');
      setPassword('');
      setUploadPortfolioId('');
      notify.success('Statement uploaded successfully');
      fetchStatements();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to upload statement'));
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteClick = (statement: Statement) => {
    setStatementToDelete(statement);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!statementToDelete) return;

    try {
      setDeleting(true);
      await api.delete(`/statements/${statementToDelete.id}`);
      notify.success(`Statement "${statementToDelete.filename}" deleted successfully`);
      setDeleteDialogOpen(false);
      setStatementToDelete(null);
      fetchStatements();
    } catch (err) {
      notify.error(getErrorMessage(err, 'Failed to delete statement'));
    } finally {
      setDeleting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'processed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Statements</Typography>
        <Button
          variant="contained"
          startIcon={<CloudUpload />}
          onClick={() => { setUploadPortfolioId(selectedPortfolioId || ''); setUploadDialogOpen(true); }}
        >
          Upload Statement
        </Button>
      </Box>

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Filename</TableCell>
                <TableCell>Broker</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Upload Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : statements.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary">
                      No statements uploaded yet. Upload your first statement to get started.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                statements.map((statement) => (
                  <TableRow key={statement.id}>
                    <TableCell>{statement.filename}</TableCell>
                    <TableCell>{statement.institution_name || 'N/A'}</TableCell>
                    <TableCell>{statement.statement_type.replace(/_/g, ' ')}</TableCell>
                    <TableCell>{formatDate(statement.uploaded_at)}</TableCell>
                    <TableCell>
                      <Chip
                        label={statement.status}
                        color={getStatusColor(statement.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Delete statement and associated assets">
                        <IconButton
                          color="error"
                          size="small"
                          onClick={() => handleDeleteClick(statement)}
                        >
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Statement</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <TextField
              select
              fullWidth
              label="Statement Type"
              value={statementType}
              onChange={(e) => { setStatementType(e.target.value); setBroker(''); }}
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
              value={broker}
              onChange={(e) => setBroker(e.target.value)}
              sx={{ mb: 2 }}
              helperText={
                !statementType ? 'Select a statement type first' :
                statementType === 'ppf_statement' || statementType === 'ssy_statement' ? 'Select bank or post office' :
                statementType === 'nps_statement' ? 'Select CRA or fund manager' :
                statementType === 'pf_statement' ? 'EPFO or employer name' :
                statementType === 'bank_statement' ? 'Select your bank' :
                statementType === 'insurance_statement' ? 'Select insurance provider' :
                'Select broker or institution'
              }
              disabled={!statementType}
            >
              {/* Brokers — for broker/MF/demat statements */}
              {['broker_statement', 'mutual_fund_statement', 'demat_statement'].includes(statementType) &&
                brokersList.map((b) => (
                  <MenuItem key={b.value} value={b.value}>{b.label}</MenuItem>
                ))
              }

              {/* Crypto exchanges — for crypto statements */}
              {statementType === 'crypto_statement' &&
                exchangesList.map((e) => (
                  <MenuItem key={e.value} value={e.value}>{e.label}</MenuItem>
                ))
              }

              {/* US Stock Brokers */}
              {statementType === 'vested_statement' && (
                <MenuItem value="vested">Vested</MenuItem>
              )}
              {statementType === 'indmoney_statement' && (
                <MenuItem value="indmoney">INDMoney</MenuItem>
              )}

              {/* Banks — for bank/PPF/SSY statements */}
              {['bank_statement', 'ppf_statement', 'ssy_statement'].includes(statementType) &&
                banksList.map((b) => (
                  <MenuItem key={b.value} value={b.value}>{b.label}</MenuItem>
                ))
              }

              {/* NPS CRAs */}
              {statementType === 'nps_statement' &&
                npsCraList.map((c) => (
                  <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                ))
              }

              {/* EPFO for PF */}
              {statementType === 'pf_statement' && (
                <MenuItem value="epfo">EPFO (Employees' Provident Fund Organisation)</MenuItem>
              )}

              {/* Insurance providers */}
              {statementType === 'insurance_statement' &&
                insuranceList.map((i) => (
                  <MenuItem key={i.value} value={i.value}>{i.label}</MenuItem>
                ))
              }

              <MenuItem value="other">Other</MenuItem>
            </TextField>

            {selectedFile && selectedFile.name.toLowerCase().endsWith('.pdf') && (
              <TextField
                fullWidth
                type={showPassword ? 'text' : 'password'}
                label="PDF Password (if encrypted)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Leave empty if not password-protected"
                helperText="Required for NSDL CAS and other encrypted PDFs"
                sx={{ mb: 2 }}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
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
              {selectedFile ? selectedFile.name : 'Select File'}
              <input
                type="file"
                hidden
                accept=".pdf,.csv,.xlsx"
                onChange={handleFileSelect}
              />
            </Button>

            {selectedFile && (
              <Typography variant="body2" color="text.secondary">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpload}
            variant="contained"
            disabled={!selectedFile || !broker || !statementType || uploading}
          >
            {uploading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Statement</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{statementToDelete?.filename}"?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            This will also delete all associated assets and transactions that were created from this statement.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={deleting}
          >
            {deleting ? <CircularProgress size={24} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Statements;

// Made with Bob
