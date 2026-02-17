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
  Alert,
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
import api from '../services/api';

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
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
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

  useEffect(() => {
    fetchStatements();
  }, []);

  const fetchStatements = async () => {
    try {
      setLoading(true);
      const response = await api.get('/statements/');
      setStatements(response.data);
      setError('');
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
        setError(errorDetail.map((e: any) => e.msg).join(', '));
      } else if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else {
        setError('Failed to fetch statements');
      }
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
      setError('Please fill all fields and select a file');
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
      setError('');
      fetchStatements();
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
        setError(errorDetail.map((e: any) => e.msg).join(', '));
      } else if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else {
        setError('Failed to upload statement');
      }
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
      setSuccess(`Statement "${statementToDelete.filename}" deleted successfully`);
      setDeleteDialogOpen(false);
      setStatementToDelete(null);
      fetchStatements();
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'string') {
        setError(errorDetail);
      } else {
        setError('Failed to delete statement');
      }
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
          onClick={() => setUploadDialogOpen(true)}
        >
          Upload Statement
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

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
              label="Institution/Broker"
              value={broker}
              onChange={(e) => setBroker(e.target.value)}
              sx={{ mb: 2 }}
              helperText={
                statementType === 'vested_statement' ? 'Select Vested' :
                statementType === 'indmoney_statement' ? 'Select INDMoney' :
                statementType === 'ppf_statement' ? 'Select bank or post office' :
                statementType === 'ssy_statement' ? 'Select bank or post office' :
                statementType === 'nps_statement' ? 'Select CRA or fund manager' :
                statementType === 'pf_statement' ? 'EPFO or employer name' :
                'Select broker or institution'
              }
            >
              {/* Indian Brokers for stocks/MF */}
              <MenuItem value="zerodha">Zerodha</MenuItem>
              <MenuItem value="icici_direct">ICICI Direct</MenuItem>
              <MenuItem value="groww">Groww</MenuItem>
              <MenuItem value="upstox">Upstox</MenuItem>
              <MenuItem value="angelone">Angel One</MenuItem>
              
              {/* US Stock Brokers */}
              <MenuItem value="vested">Vested (US Stocks)</MenuItem>
              <MenuItem value="indmoney">INDMoney (US Stocks)</MenuItem>
              
              {/* Banks for PPF/SSY */}
              {(statementType === 'ppf_statement' || statementType === 'ssy_statement' || statementType === 'bank_statement') && (
                <>
                  <MenuItem value="sbi">State Bank of India (SBI)</MenuItem>
                  <MenuItem value="hdfc">HDFC Bank</MenuItem>
                  <MenuItem value="icici">ICICI Bank</MenuItem>
                  <MenuItem value="axis">Axis Bank</MenuItem>
                  <MenuItem value="pnb">Punjab National Bank</MenuItem>
                  <MenuItem value="post_office">Post Office</MenuItem>
                </>
              )}
              
              {/* NPS CRA */}
              {statementType === 'nps_statement' && (
                <>
                  <MenuItem value="nsdl_cra">NSDL CRA</MenuItem>
                  <MenuItem value="karvy_cra">Karvy CRA</MenuItem>
                  <MenuItem value="protean_cra">Protean CRA</MenuItem>
                </>
              )}
              
              {/* EPFO for PF */}
              {statementType === 'pf_statement' && (
                <>
                  <MenuItem value="epfo">EPFO (Employees' Provident Fund Organisation)</MenuItem>
                </>
              )}
              
              <MenuItem value="other">Other</MenuItem>
            </TextField>

            <TextField
              select
              fullWidth
              label="Statement Type"
              value={statementType}
              onChange={(e) => setStatementType(e.target.value)}
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
