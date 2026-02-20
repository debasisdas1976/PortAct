import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import {
  CloudDownload as DownloadIcon,
  CloudUpload as UploadIcon,
  PictureAsPdf as PdfIcon,
} from '@mui/icons-material';
import api from '../services/api';

interface RestoreStats {
  bank_accounts: { imported: number; skipped: number };
  demat_accounts: { imported: number; skipped: number };
  crypto_accounts: { imported: number; skipped: number };
  assets: { imported: number; skipped: number };
  expense_categories: { imported: number; skipped: number };
  expenses: { imported: number; skipped: number };
  transactions: { imported: number; skipped: number };
}

const STAT_LABELS: Record<string, string> = {
  bank_accounts: 'Bank Accounts',
  demat_accounts: 'Demat / Trading Accounts',
  crypto_accounts: 'Crypto Accounts',
  assets: 'Assets',
  expense_categories: 'Expense Categories',
  expenses: 'Expenses',
  transactions: 'Transactions',
};

const PortfolioAdmin: React.FC = () => {
  // Export
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');

  // Restore
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [restoreResult, setRestoreResult] = useState<{ message: string; stats: RestoreStats } | null>(null);
  const [restoreError, setRestoreError] = useState('');

  // PDF
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [pdfError, setPdfError] = useState('');

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleExport = async () => {
    setExporting(true);
    setExportError('');
    try {
      const response = await api.get('/portfolio/export', { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/json' }));
      const a = document.createElement('a');
      a.href = url;
      const cd = response.headers['content-disposition'] || '';
      const match = cd.match(/filename="?([^"]+)"?/);
      a.download = match ? match[1] : 'portfolio_export.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError('Failed to export portfolio. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleRestore = async () => {
    if (!restoreFile) return;
    setRestoring(true);
    setRestoreError('');
    setRestoreResult(null);
    try {
      const form = new FormData();
      form.append('file', restoreFile);
      const response = await api.post('/portfolio/restore', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setRestoreResult({ message: response.data.message, stats: response.data.stats });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setRestoreError(
        typeof detail === 'string' ? detail : 'Failed to restore portfolio. Please check the file.'
      );
    } finally {
      setRestoring(false);
    }
  };

  const handleGeneratePdf = async () => {
    setGeneratingPdf(true);
    setPdfError('');
    try {
      const response = await api.get('/portfolio/statement/pdf', { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      const cd = response.headers['content-disposition'] || '';
      const match = cd.match(/filename="?([^"]+)"?/);
      a.download = match ? match[1] : 'portfolio_statement.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setPdfError('Failed to generate PDF statement. Please try again.');
    } finally {
      setGeneratingPdf(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Portfolio Administration
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Backup your portfolio data, restore from a previous backup, or generate a PDF statement.
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, maxWidth: 720 }}>

        {/* ── Export ─────────────────────────────────────────────────────── */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Download Backup
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Export all your portfolio data (assets, bank accounts, expenses, transactions) as a
              single JSON file that you can save on your computer.
            </Typography>
            {exportError && (
              <Alert severity="error" sx={{ mb: 2 }}>{exportError}</Alert>
            )}
            <Button
              variant="contained"
              startIcon={exporting ? <CircularProgress size={18} color="inherit" /> : <DownloadIcon />}
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? 'Exporting…' : 'Download Portfolio Backup'}
            </Button>
          </CardContent>
        </Card>

        <Divider />

        {/* ── Restore ────────────────────────────────────────────────────── */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Restore from Backup
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload a previously exported JSON backup. Records that already exist will be skipped
              (no duplicates). Only missing records will be imported.
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Button variant="outlined" component="label" startIcon={<UploadIcon />}>
                {restoreFile ? restoreFile.name : 'Select Backup File (.json)'}
                <input
                  type="file"
                  hidden
                  accept=".json"
                  onChange={(e) => {
                    setRestoreFile(e.target.files?.[0] ?? null);
                    setRestoreResult(null);
                    setRestoreError('');
                  }}
                />
              </Button>

              {restoring && <LinearProgress />}

              {restoreError && <Alert severity="error">{restoreError}</Alert>}

              {restoreResult && (
                <Alert severity="success">
                  <Typography variant="body2" fontWeight="bold" sx={{ mb: 1 }}>
                    {restoreResult.message}
                  </Typography>
                  <List dense disablePadding>
                    {Object.entries(restoreResult.stats).map(([key, { imported, skipped }]) => (
                      <ListItem key={key} disableGutters sx={{ py: 0 }}>
                        <ListItemText
                          primary={
                            <Typography variant="body2">
                              <strong>{STAT_LABELS[key] || key}:</strong> {imported} imported,{' '}
                              {skipped} skipped
                            </Typography>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                </Alert>
              )}

              <Button
                variant="contained"
                color="warning"
                startIcon={restoring ? <CircularProgress size={18} color="inherit" /> : <UploadIcon />}
                onClick={handleRestore}
                disabled={restoring || !restoreFile}
              >
                {restoring ? 'Restoring…' : 'Restore Portfolio'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Divider />

        {/* ── PDF statement ───────────────────────────────────────────────── */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Generate PDF Statement
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Download a formatted PDF summary of your entire portfolio — allocation breakdown,
              individual holdings, and bank account balances.
            </Typography>
            {pdfError && (
              <Alert severity="error" sx={{ mb: 2 }}>{pdfError}</Alert>
            )}
            <Button
              variant="contained"
              color="secondary"
              startIcon={generatingPdf ? <CircularProgress size={18} color="inherit" /> : <PdfIcon />}
              onClick={handleGeneratePdf}
              disabled={generatingPdf}
            >
              {generatingPdf ? 'Generating…' : 'Download PDF Statement'}
            </Button>
          </CardContent>
        </Card>

      </Box>
    </Box>
  );
};

export default PortfolioAdmin;

// Made with Bob
