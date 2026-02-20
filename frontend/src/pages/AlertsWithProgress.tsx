import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert as MuiAlert,
  IconButton,
  Button,
  LinearProgress,
  Tabs,
  Tab,
  Snackbar,
} from '@mui/material';
import {
  Delete,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Refresh,
  HourglassEmpty,
  CheckCircleOutline,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchAlerts, deleteAlert } from '../store/slices/alertsSlice';
import api from '../services/api';

interface AssetProgress {
  asset_id: number;
  asset_name: string;
  asset_symbol: string | null;
  status: string;
  alert_created: boolean;
  alert_message: string | null;
  processed_at: string | null;
  error_message: string | null;
}

interface NewsProgress {
  session_id: string;
  user_id: number;
  total_assets: number;
  processed_assets: number;
  alerts_created: number;
  status: string;
  assets: AssetProgress[];
  started_at: string;
  completed_at: string | null;
}

type SnackbarSeverity = 'success' | 'error' | 'info' | 'warning';

interface SnackbarState {
  open: boolean;
  message: string;
  severity: SnackbarSeverity;
}

const AlertsWithProgress: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { alerts, loading, error } = useSelector((state: RootState) => state.alerts);
  const [fetchingNews, setFetchingNews] = useState(false);
  const [progress, setProgress] = useState<NewsProgress | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [snackbar, setSnackbar] = useState<SnackbarState>({
    open: false,
    message: '',
    severity: 'info',
  });

  useEffect(() => {
    dispatch(fetchAlerts());
  }, [dispatch]);

  // Poll for progress updates
  useEffect(() => {
    if (!sessionId || !fetchingNews) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await api.get(`/alerts/progress/${sessionId}`);
        setProgress(response.data);

        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setFetchingNews(false);
          dispatch(fetchAlerts());
          clearInterval(pollInterval);

          if (response.data.status === 'completed') {
            showSnackbar(
              `Processing complete. ${response.data.alerts_created} new alert(s) created.`,
              'success',
            );
          } else {
            showSnackbar('News fetching encountered an error. Please try again.', 'error');
          }
        }
      } catch (err) {
        // Non-fatal: poll will retry on next tick
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [sessionId, fetchingNews, dispatch]);

  const showSnackbar = (message: string, severity: SnackbarSeverity) => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const handleFetchNews = async () => {
    setFetchingNews(true);
    setProgress(null);
    try {
      const response = await api.post('/alerts/fetch-news?limit=10');
      setSessionId(response.data.session_id);
      setTabValue(1);
    } catch (err: any) {
      showSnackbar(
        err.response?.data?.detail || 'Failed to start news fetching. Please try again.',
        'error',
      );
      setFetchingNews(false);
    }
  };

  const handleStopFetch = async () => {
    if (!sessionId) return;
    try {
      await api.post(`/alerts/cancel/${sessionId}`);
      setFetchingNews(false);
      showSnackbar('News fetching has been stopped.', 'info');
    } catch (err: any) {
      showSnackbar(
        err.response?.data?.detail || 'Failed to stop news fetching.',
        'error',
      );
    }
  };

  const handleDelete = (id: number) => {
    dispatch(deleteAlert(id));
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'warning':
        return <Warning sx={{ color: 'warning.main' }} />;
      default:
        return <CheckCircle sx={{ color: 'info.main' }} />;
    }
  };

  const getSeverityColor = (
    severity: string,
  ): 'error' | 'warning' | 'info' | 'default' => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (assetStatus: string) => {
    switch (assetStatus) {
      case 'pending':
        return <HourglassEmpty sx={{ color: 'text.secondary' }} />;
      case 'processing':
        return <CircularProgress size={20} />;
      case 'completed':
        return <CheckCircleOutline sx={{ color: 'success.main' }} />;
      case 'error':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

  // Find the most recent alert timestamp
  const lastAlertUpdate = React.useMemo(() => {
    if (alerts.length === 0) return null;
    let latest = alerts[0].created_at;
    for (const alert of alerts) {
      if (alert.created_at > latest) latest = alert.created_at;
    }
    return latest;
  }, [alerts]);

  if (loading && !progress) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <MuiAlert severity="error" sx={{ mt: 2 }}>
        {error}
      </MuiAlert>
    );
  }

  const progressPercent =
    progress && progress.total_assets > 0
      ? (progress.processed_assets / progress.total_assets) * 100
      : 0;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Alerts &amp; Notifications</Typography>
          {lastAlertUpdate && (
            <Typography variant="caption" color="text.secondary">
              Last alert: {new Date(lastAlertUpdate).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' })}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {fetchingNews && (
            <Button variant="outlined" color="error" onClick={handleStopFetch}>
              Stop Processing
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={fetchingNews ? <CircularProgress size={20} color="inherit" /> : <Refresh />}
            onClick={handleFetchNews}
            disabled={fetchingNews}
          >
            {fetchingNews ? 'Fetching News…' : 'Fetch Latest News'}
          </Button>
        </Box>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab label={`Alerts (${alerts.length})`} />
          <Tab label="Processing Progress" disabled={!progress} />
        </Tabs>
      </Box>

      {tabValue === 0 && (
        <Paper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell width={50} />
                  <TableCell>Alert Type</TableCell>
                  <TableCell>Message</TableCell>
                  <TableCell>Asset</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell width={80}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {alerts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary">
                        No alerts at the moment. Click "Fetch Latest News" to check for updates!
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  alerts.map((alert) => (
                    <TableRow key={alert.id}>
                      <TableCell>{getSeverityIcon(alert.severity)}</TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {alert.alert_type}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{alert.message}</Typography>
                      </TableCell>
                      <TableCell>
                        {alert.asset ? (
                          <Typography variant="body2">{alert.asset.symbol}</Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">-</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={alert.severity}
                          color={getSeverityColor(alert.severity)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {formatDate(alert.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <IconButton size="small" onClick={() => handleDelete(alert.id)} color="error">
                          <Delete />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {tabValue === 1 && progress && (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="h6">Processing Assets</Typography>
              <Chip
                label={progress.status}
                color={
                  progress.status === 'completed'
                    ? 'success'
                    : progress.status === 'failed'
                    ? 'error'
                    : 'info'
                }
                size="small"
              />
            </Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {progress.processed_assets} of {progress.total_assets} assets processed
              &nbsp;•&nbsp;{progress.alerts_created} alerts created
            </Typography>
            <LinearProgress variant="determinate" value={progressPercent} sx={{ mt: 1 }} />
          </Box>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell width={50}>Status</TableCell>
                  <TableCell>Asset Name</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Alert Status</TableCell>
                  <TableCell>Processed At</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {progress.assets.map((asset) => (
                  <TableRow key={asset.asset_id}>
                    <TableCell>{getStatusIcon(asset.status)}</TableCell>
                    <TableCell>
                      <Typography variant="body2">{asset.asset_name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {asset.asset_symbol || '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {asset.status === 'completed' && (
                        <Chip
                          label={asset.alert_message || 'Processed. No alerts'}
                          color={asset.alert_created ? 'success' : 'default'}
                          size="small"
                          variant={asset.alert_created ? 'filled' : 'outlined'}
                        />
                      )}
                      {asset.status === 'error' && (
                        <Chip label={asset.error_message || 'Error'} color="error" size="small" />
                      )}
                      {asset.status === 'processing' && (
                        <Chip label="Processing…" color="info" size="small" />
                      )}
                      {asset.status === 'pending' && (
                        <Chip label="Pending" color="default" size="small" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {asset.processed_at ? formatDate(asset.processed_at) : '-'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <MuiAlert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
          elevation={6}
          variant="filled"
        >
          {snackbar.message}
        </MuiAlert>
      </Snackbar>
    </Box>
  );
};

export default AlertsWithProgress;
