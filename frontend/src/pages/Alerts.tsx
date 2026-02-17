import React, { useEffect } from 'react';
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
} from '@mui/material';
import { Delete, CheckCircle, Warning, Error as ErrorIcon } from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { fetchAlerts, deleteAlert } from '../store/slices/alertsSlice';

const Alerts: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { alerts, loading, error } = useSelector((state: RootState) => state.alerts);

  useEffect(() => {
    dispatch(fetchAlerts());
  }, [dispatch]);

  const handleDelete = (id: number) => {
    dispatch(deleteAlert(id));
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'medium':
        return <Warning sx={{ color: 'warning.main' }} />;
      case 'low':
        return <CheckCircle sx={{ color: 'info.main' }} />;
      default:
        return <CheckCircle sx={{ color: 'info.main' }} />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
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

  if (loading) {
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

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Alerts & Notifications
      </Typography>

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell width={50}></TableCell>
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
                      No alerts at the moment. You're all set!
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
                        <Typography variant="body2" color="text.secondary">
                          -
                        </Typography>
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
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(alert.id)}
                        color="error"
                      >
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
    </Box>
  );
};

export default Alerts;

// Made with Bob
