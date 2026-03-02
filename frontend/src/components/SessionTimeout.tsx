import React, { useEffect, useCallback, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../store/slices/authSlice';
import { RootState } from '../store';

const DEFAULT_TIMEOUT_MINUTES = 30;

/** Read the configurable timeout from localStorage (synced by Settings page). */
const getTimeoutMs = (): number => {
  const stored = localStorage.getItem('sessionTimeoutMinutes');
  const minutes = stored ? parseInt(stored, 10) : DEFAULT_TIMEOUT_MINUTES;
  return (isNaN(minutes) || minutes < 1 ? DEFAULT_TIMEOUT_MINUTES : minutes) * 60 * 1000;
};

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
      timeoutRef.current = setTimeout(() => doLogoutRef.current(), getTimeoutMs());
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
        // User is back → check if session already expired based on last API activity
        cancelTimer();
        const lastActivity = localStorage.getItem('lastApiActivity');
        if (lastActivity) {
          const elapsed = Date.now() - parseInt(lastActivity, 10);
          if (elapsed > getTimeoutMs()) {
            doLogoutRef.current();
          }
        }
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
