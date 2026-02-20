import React, { useEffect, useCallback, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../store/slices/authSlice';
import { RootState } from '../store';

// Session expires after being hidden/away for this long
const HIDDEN_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

const SessionTimeout: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const doLogout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    dispatch(logout());
    navigate('/login', { state: { message: 'Your session has expired due to inactivity.' } });
  }, [dispatch, navigate]);

  // Stable ref so the visibility handler always calls the latest doLogout
  // without the effect needing to re-run (and re-add listeners) when it changes
  const doLogoutRef = useRef(doLogout);
  useEffect(() => {
    doLogoutRef.current = doLogout;
  });

  useEffect(() => {
    if (!isAuthenticated) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      return;
    }

    const startTimer = () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => doLogoutRef.current(), HIDDEN_TIMEOUT_MS);
    };

    const cancelTimer = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Tab switched / window minimised → start countdown
        startTimer();
      } else {
        // User is back → cancel any pending logout
        cancelTimer();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // If somehow mounted while already hidden, start the timer immediately
    if (document.hidden) {
      startTimer();
    }

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      cancelTimer();
    };
  }, [isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  // No UI rendered
  return null;
};

export default SessionTimeout;

// Made with Bob
