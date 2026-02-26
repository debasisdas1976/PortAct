import React, { useState, useEffect } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
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
import { AppDispatch, RootState } from '../store';
import { register, clearError } from '../store/slices/authSlice';
import AuthLayout from '../components/AuthLayout';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated, loading, error } = useSelector((state: RootState) => state.auth);

  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });

  const [validationError, setValidationError] = useState('');
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setValidationError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setValidationError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setValidationError('Password must be at least 8 characters long');
      return;
    }

    const { confirmPassword, ...registerData } = formData;
    const result = await dispatch(register(registerData));

    if (register.fulfilled.match(result)) {
      setRegistrationSuccess(true);
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
        {registrationSuccess ? (
          <>
            <Typography component="h1" variant="h5" sx={{ fontWeight: 600, mb: 0.5 }}>
              You're all set!
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Your account has been created successfully
            </Typography>

            <Alert severity="success" sx={{ mb: 3 }}>
              You can now sign in with your credentials.
            </Alert>

            <Button
              fullWidth
              variant="contained"
              component={RouterLink}
              to="/login"
              size="large"
              sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2, bgcolor: '#1E293B', '&:hover': { bgcolor: '#0F172A' } }}
            >
              Go to Sign In
            </Button>
          </>
        ) : (
          <>
            <Typography component="h1" variant="h5" sx={{ fontWeight: 600, mb: 0.5 }}>
              Create account
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Start tracking your portfolio today
            </Typography>

            {(error || validationError) && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {validationError || error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="full_name"
                label="Full Name"
                name="full_name"
                autoComplete="name"
                autoFocus
                value={formData.full_name}
                onChange={handleChange}
                disabled={loading}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                value={formData.email}
                onChange={handleChange}
                disabled={loading}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                id="username"
                label="Username"
                name="username"
                autoComplete="username"
                value={formData.username}
                onChange={handleChange}
                disabled={loading}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="new-password"
                value={formData.password}
                onChange={handleChange}
                disabled={loading}
                helperText="Must be at least 8 characters"
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="confirmPassword"
                label="Confirm Password"
                type="password"
                id="confirmPassword"
                autoComplete="new-password"
                value={formData.confirmPassword}
                onChange={handleChange}
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
                  bgcolor: '#1E293B',
                  '&:hover': { bgcolor: '#0F172A' },
                }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : 'Sign Up'}
              </Button>
              <Box sx={{ textAlign: 'center' }}>
                <Link component={RouterLink} to="/login" variant="body2">
                  Already have an account? Sign In
                </Link>
              </Box>
            </Box>
          </>
        )}
      </Paper>
    </AuthLayout>
  );
};

export default Register;

// Made with Bob
