import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  LinearProgress,
  Box,
} from '@mui/material';
import { logout } from '../store/slices/authSlice';
import { RootState } from '../store';

// Configuration
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds
const WARNING_TIME = 2 * 60 * 1000; // Show warning 2 minutes before timeout
const COUNTDOWN_INTERVAL = 1000; // Update countdown every second

const SessionTimeout: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);
  
  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(0);
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());

  // Clear all timers
  const clearAllTimers = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (warningTimeoutRef.current) {
      clearTimeout(warningTimeoutRef.current);
      warningTimeoutRef.current = null;
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
  }, []);

  // Handle logout
  const handleLogout = useCallback(() => {
    clearAllTimers();
    setShowWarning(false);
    dispatch(logout());
    navigate('/login', { state: { message: 'Your session has expired due to inactivity.' } });
  }, [dispatch, navigate, clearAllTimers]);

  // Start countdown for warning dialog
  const startCountdown = useCallback(() => {
    const warningDuration = WARNING_TIME / 1000; // Convert to seconds
    setCountdown(warningDuration);
    
    countdownIntervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          handleLogout();
          return 0;
        }
        return prev - 1;
      });
    }, COUNTDOWN_INTERVAL);
  }, [handleLogout]);

  // Show warning dialog
  const showWarningDialog = useCallback(() => {
    setShowWarning(true);
    startCountdown();
  }, [startCountdown]);

  // Reset inactivity timer
  const resetTimer = useCallback(() => {
    if (!isAuthenticated) return;

    clearAllTimers();
    setShowWarning(false);
    lastActivityRef.current = Date.now();

    // Set timeout for logout
    timeoutRef.current = setTimeout(() => {
      handleLogout();
    }, INACTIVITY_TIMEOUT);

    // Set timeout for warning
    warningTimeoutRef.current = setTimeout(() => {
      showWarningDialog();
    }, INACTIVITY_TIMEOUT - WARNING_TIME);
  }, [isAuthenticated, clearAllTimers, handleLogout, showWarningDialog]);

  // Handle user activity
  const handleActivity = useCallback(() => {
    // Reset timer on any activity if user is authenticated
    // This ensures the session stays active while user is working
    if (isAuthenticated) {
      const now = Date.now();
      const timeSinceLastActivity = now - lastActivityRef.current;
      
      // Throttle: only reset if more than 5 seconds since last activity
      // This prevents excessive timer resets while still keeping session active
      if (timeSinceLastActivity > 5000) {
        lastActivityRef.current = now;
        
        // If warning is showing, dismiss it and reset
        if (showWarning) {
          setShowWarning(false);
        }
        
        resetTimer();
      }
    }
  }, [isAuthenticated, showWarning, resetTimer]);

  // Handle "Stay Logged In" button
  const handleStayLoggedIn = useCallback(() => {
    resetTimer();
  }, [resetTimer]);

  // Set up activity listeners
  useEffect(() => {
    if (!isAuthenticated) {
      clearAllTimers();
      return;
    }

    // Events that indicate user activity
    const events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
    ];

    // Add event listeners
    events.forEach((event) => {
      document.addEventListener(event, handleActivity, { passive: true });
    });

    // Initialize timer
    resetTimer();

    // Cleanup
    return () => {
      events.forEach((event) => {
        document.removeEventListener(event, handleActivity);
      });
      clearAllTimers();
    };
  }, [isAuthenticated, handleActivity, resetTimer, clearAllTimers]);

  // Format countdown time
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Calculate progress percentage
  const progressPercentage = ((WARNING_TIME / 1000 - countdown) / (WARNING_TIME / 1000)) * 100;

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Dialog
      open={showWarning}
      onClose={(_event, reason) => {
        // Prevent closing by clicking outside or pressing escape
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
          return;
        }
      }}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown
    >
      <DialogTitle>
        Session Timeout Warning
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body1" gutterBottom>
            Your session is about to expire due to inactivity.
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            You will be automatically logged out in:
          </Typography>
          <Typography
            variant="h4"
            color="error"
            sx={{ my: 2, textAlign: 'center', fontWeight: 'bold' }}
          >
            {formatTime(countdown)}
          </Typography>
          <LinearProgress
            variant="determinate"
            value={progressPercentage}
            color="error"
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
        <Typography variant="body2" color="text.secondary">
          Click "Stay Logged In" to continue your session, or "Logout" to end your session now.
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleLogout} color="inherit">
          Logout
        </Button>
        <Button
          onClick={handleStayLoggedIn}
          variant="contained"
          color="primary"
          autoFocus
        >
          Stay Logged In
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SessionTimeout;

// Made with Bob