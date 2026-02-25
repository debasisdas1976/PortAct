import React, { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  CircularProgress,
} from '@mui/material';
import { LockReset } from '@mui/icons-material';
import { authAPI } from '../services/api';
import AuthLayout from '../components/AuthLayout';

const ForgotPassword: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [expiresInMinutes, setExpiresInMinutes] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await authAPI.forgotPassword(email);
      setSubmitted(true);

      if (data.reset_token) {
        setResetToken(data.reset_token);
        setExpiresInMinutes(data.expires_in_minutes);
      } else {
        // Email not registered — show neutral message (no enumeration)
        setResetToken(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetNavigation = () => {
    if (resetToken) {
      navigate(`/reset-password?token=${encodeURIComponent(resetToken)}`);
    }
  };

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
          Forgot password
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          We'll help you get back into your account
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!submitted ? (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Enter the email address associated with your account and we'll generate a
              reset link for you.
            </Typography>

            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                type="email"
                autoComplete="email"
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
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
                disabled={loading || !email}
              >
                {loading ? <CircularProgress size={24} /> : 'Generate Reset Link'}
              </Button>
            </Box>
          </>
        ) : resetToken ? (
          <>
            <Alert severity="success" sx={{ mb: 3 }}>
              Reset link generated. Click the button below to set a new password.
              This link is valid for <strong>{expiresInMinutes} minutes</strong>.
            </Alert>
            <Button
              fullWidth
              variant="contained"
              size="large"
              startIcon={<LockReset />}
              onClick={handleResetNavigation}
              sx={{ mb: 2, py: 1.5, fontSize: '1rem', borderRadius: 2 }}
            >
              Reset My Password
            </Button>
          </>
        ) : (
          <Alert severity="info" sx={{ mb: 2 }}>
            No account is associated with <strong>{email}</strong>. Please check the
            address or{' '}
            <Link component={RouterLink} to="/register">
              create an account
            </Link>
            .
          </Alert>
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

export default ForgotPassword;
