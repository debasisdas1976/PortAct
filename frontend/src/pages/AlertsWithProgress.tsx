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
  RssFeed,
  OpenInNew,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import {
  fetchAlerts,
  deleteAlert,
  setActiveSession,
  clearActiveSession,
  startSessionPolling,
  stopSessionPolling,
} from '../store/slices/alertsSlice';
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
  error_detail: string | null;
  provider: string | null;
  model: string | null;
}

type SnackbarSeverity = 'success' | 'error' | 'info' | 'warning';

interface SnackbarState {
  open: boolean;
  message: string;
  severity: SnackbarSeverity;
}

const AlertsWithProgress: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    alerts,
    loading,
    error,
    activeSessionId,
    activeProvider,
    lastProgress,
    polling,
  } = useSelector((state: RootState) => state.alerts);

  const progress = lastProgress as NewsProgress | null;
  const fetchingNews = !!(activeSessionId && polling);

  const [tabValue, setTabValue] = useState(0);
  const [fetchingFree, setFetchingFree] = useState(false);
  const [snackbar, setSnackbar] = useState<SnackbarState>({
    open: false,
    message: '',
    severity: 'info',
  });

  // Track previous progress status to show snackbar on completion
  const [prevStatus, setPrevStatus] = useState<string | null>(null);

  useEffect(() => {
    dispatch(fetchAlerts());
  }, [dispatch]);

  // Show snackbar when progress transitions to completed/failed
  useEffect(() => {
    if (!progress) return;
    const status = progress.status;
    if (prevStatus && prevStatus !== status) {
      if (status === 'completed') {
        showSnackbar(
          `Processing complete. ${progress.alerts_created} new alert(s) created.`,
          'success',
        );
      } else if (status === 'failed') {
        showSnackbar(
          progress.error_detail || 'News fetching encountered an error. Please try again.',
          'error',
        );
      }
    }
    setPrevStatus(status);
  }, [progress?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const showSnackbar = (message: string, severity: SnackbarSeverity) => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const handleFetchNews = async () => {
    try {
      const response = await api.post('/alerts/fetch-news');

      // If AI is not available, the backend runs free alerts as fallback
      if (response.data.ai_available === false) {
        showSnackbar(
          response.data.message || 'Running free alerts (RSS, price analysis).',
          'info',
        );
        // Refresh alerts after a short delay to pick up new free alerts
        setTimeout(() => dispatch(fetchAlerts()), 5000);
        return;
      }

      dispatch(setActiveSession({
        sessionId: response.data.session_id,
        provider: response.data.provider
          ? { provider: response.data.provider, model: response.data.model }
          : null,
      }));
      dispatch(startSessionPolling());
      setTabValue(1);
    } catch (err: any) {
      showSnackbar(
        err.response?.data?.detail || 'Failed to start news fetching. Please try again.',
        'error',
      );
    }
  };

  const handleFetchFreeAlerts = async () => {
    setFetchingFree(true);
    try {
      const response = await api.post('/alerts/fetch-free-alerts');
      showSnackbar(
        response.data.message || 'Free alerts are being fetched in the background.',
        'info',
      );
      // Refresh alerts after a delay to pick up new results
      setTimeout(() => {
        dispatch(fetchAlerts());
        setFetchingFree(false);
      }, 5000);
    } catch (err: any) {
      showSnackbar(
        err.response?.data?.detail || 'Failed to fetch free alerts.',
        'error',
      );
      setFetchingFree(false);
    }
  };

  const handleStopFetch = async () => {
    if (!activeSessionId) return;
    try {
      await api.post(`/alerts/cancel/${activeSessionId}`);
      stopSessionPolling();
      dispatch(clearActiveSession());
      showSnackbar('News fetching has been stopped.', 'info');
    } catch (err: any) {
      showSnackbar(
        err.response?.data?.detail || 'Failed to stop news fetching.',
        'error',
      );
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await dispatch(deleteAlert(id)).unwrap();
    } catch (err: any) {
      showSnackbar(
        err?.detail || err || 'Failed to dismiss alert',
        'error',
      );
    }
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
            variant="outlined"
            startIcon={fetchingFree ? <CircularProgress size={20} color="inherit" /> : <RssFeed />}
            onClick={handleFetchFreeAlerts}
            disabled={fetchingFree || fetchingNews}
          >
            {fetchingFree ? 'Fetching…' : 'Free Alerts'}
          </Button>
          <Button
            variant="contained"
            startIcon={fetchingNews ? <CircularProgress size={20} color="inherit" /> : <Refresh />}
            onClick={handleFetchNews}
            disabled={fetchingNews || fetchingFree}
          >
            {fetchingNews ? 'Fetching News…' : 'Fetch Latest News'}
          </Button>
        </Box>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab label={`Alerts (${alerts.length})`} />
          <Tab label="Processing Progress" />
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
                        No alerts at the moment. Click &quot;Fetch Latest News&quot; to check for updates!
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  alerts.map((alert) => {
                    // Extract source tag from title (e.g., "[RSS] Title" → source="RSS", cleanTitle="Title")
                    const sourceMatch = alert.title?.match(/^\[(.+?)\]\s*/);
                    const sourceTag = sourceMatch ? sourceMatch[1] : null;
                    const cleanTitle = sourceMatch ? alert.title.replace(sourceMatch[0], '') : alert.title;
                    const sourceColor = sourceTag === 'RSS' ? 'primary'
                      : sourceTag === 'PRICE_ANALYSIS' ? 'secondary'
                      : sourceTag === 'FINNHUB' ? 'success'
                      : 'default';

                    return (
                    <TableRow key={alert.id}>
                      <TableCell>{getSeverityIcon(alert.severity)}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
                          {sourceTag && (
                            <Chip
                              label={sourceTag === 'PRICE_ANALYSIS' ? 'PRICE' : sourceTag}
                              size="small"
                              variant="outlined"
                              color={sourceColor as any}
                              sx={{ fontSize: '0.65rem', height: 20 }}
                            />
                          )}
                          <Typography variant="body2" fontWeight="medium">
                            {alert.alert_type}
                          </Typography>
                        </Box>
                        {cleanTitle && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                            {cleanTitle}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{alert.message}</Typography>
                        {alert.action_url && alert.action_url.startsWith('http') && (
                          <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                            <a href={alert.action_url} target="_blank" rel="noopener noreferrer"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 2 }}>
                              Read more <OpenInNew sx={{ fontSize: 12 }} />
                            </a>
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {alert.asset_id ? (
                          <Typography variant="body2">#{alert.asset_id}</Typography>
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
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {tabValue === 1 && progress && (
        <Paper sx={{ p: 2 }}>
          {progress.status === 'failed' && progress.error_detail && (
            <MuiAlert severity="error" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Alert processing stopped
              </Typography>
              {progress.error_detail}
            </MuiAlert>
          )}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Box>
                <Typography variant="h6">Processing Assets</Typography>
                {(activeProvider || progress.provider) && (
                  <Typography variant="caption" color="text.secondary">
                    Using {activeProvider?.provider || progress.provider}
                    {(activeProvider?.model || progress.model) && ` (${activeProvider?.model || progress.model})`}
                  </Typography>
                )}
              </Box>
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

      {tabValue === 1 && !progress && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No processing data yet. Click &quot;Fetch Latest News&quot; to start.
          </Typography>
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
