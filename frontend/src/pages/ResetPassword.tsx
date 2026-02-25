import React, { useState, useEffect } from 'react';
import { Link as RouterLink, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { Visibility, VisibilityOff, CheckCircle } from '@mui/icons-material';
import { authAPI } from '../services/api';
import AuthLayout from '../components/AuthLayout';

const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Validate client-side before submitting
  const passwordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;
  const tooShort = newPassword.length > 0 && newPassword.length < 8;
  const canSubmit = newPassword.length >= 8 && newPassword === confirmPassword && !loading;

  useEffect(() => {
    if (!token) {
      setError('No reset token found. Please request a new password reset link.');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setError(null);
    setLoading(true);

    try {
      await authAPI.resetPassword(token, newPassword);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout>
        <Paper
          elevation={0}
          sx={{
            p: 4,
            borderRadius: 3,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <Typography component="h1" variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Reset Password
          </Typography>
          <Alert severity="error" sx={{ mb: 3 }}>
            No reset token found in the URL. Please request a new password reset link.
          </Alert>
          <Button
            fullWidth
            variant="contained"
            component={RouterLink}
            to="/forgot-password"
            size="large"
            sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
          >
            Request New Link
          </Button>
        </Paper>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <Paper
        elevation={0}
        sx={{
          p: 4,
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Typography component="h1" variant="h5" sx={{ fontWeight: 600, mb: 0.5 }}>
          Set new password
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Choose a strong password for your account
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
            {error.includes('expired') && (
              <>
                {' '}
                <Link component={RouterLink} to="/forgot-password">
                  Request a new one
                </Link>
                .
              </>
            )}
          </Alert>
        )}

        {success ? (
          <>
            <Alert
              icon={<CheckCircle fontSize="inherit" />}
              severity="success"
              sx={{ mb: 3 }}
            >
              Your password has been updated successfully.
            </Alert>
            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={() => navigate('/login')}
              sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
            >
              Go to Sign In
            </Button>
          </>
        ) : (
          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              margin="normal"
              required
              fullWidth
              name="newPassword"
              label="New Password"
              type={showNew ? 'text' : 'password'}
              autoComplete="new-password"
              autoFocus
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={loading}
              error={tooShort}
              helperText={tooShort ? 'Password must be at least 8 characters' : ''}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowNew((v) => !v)} edge="end">
                      {showNew ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              margin="normal"
              required
              fullWidth
              name="confirmPassword"
              label="Confirm Password"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              error={passwordMismatch}
              helperText={passwordMismatch ? 'Passwords do not match' : ''}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowConfirm((v) => !v)} edge="end">
                      {showConfirm ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              sx={{
                mt: 3,
                mb: 2,
                py: 1.5,
                fontSize: '1rem',
                borderRadius: 2,
              }}
              disabled={!canSubmit}
            >
              {loading ? <CircularProgress size={24} /> : 'Update Password'}
            </Button>
          </Box>
        )}

        <Box sx={{ textAlign: 'center', mt: 1 }}>
          <Link component={RouterLink} to="/login" variant="body2">
            Back to Sign In
          </Link>
        </Box>
      </Paper>
    </AuthLayout>
  );
};

export default ResetPassword;
