import React, { createContext, useContext, useState, useCallback } from 'react';
import { Snackbar, Alert, AlertColor } from '@mui/material';

interface Notification {
  message: string;
  severity: AlertColor;
  key: number;
}

interface NotifyMethods {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

interface NotificationContextType {
  notify: NotifyMethods;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export const useNotification = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [, setQueue] = useState<Notification[]>([]);
  const [current, setCurrent] = useState<Notification | null>(null);
  const [open, setOpen] = useState(false);

  const processQueue = useCallback(() => {
    setQueue((prev) => {
      if (prev.length > 0) {
        const [next, ...rest] = prev;
        setCurrent(next);
        setOpen(true);
        return rest;
      }
      return prev;
    });
  }, []);

  const showNotification = useCallback((message: string, severity: AlertColor) => {
    const notification: Notification = { message, severity, key: Date.now() };
    if (!current) {
      setCurrent(notification);
      setOpen(true);
    } else {
      setQueue((prev) => [...prev, notification]);
    }
  }, [current]);

  const handleClose = useCallback((_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') return;
    setOpen(false);
  }, []);

  const handleExited = useCallback(() => {
    setCurrent(null);
    processQueue();
  }, [processQueue]);

  const notify: NotifyMethods = {
    success: useCallback((message: string) => showNotification(message, 'success'), [showNotification]),
    error: useCallback((message: string) => showNotification(message, 'error'), [showNotification]),
    info: useCallback((message: string) => showNotification(message, 'info'), [showNotification]),
    warning: useCallback((message: string) => showNotification(message, 'warning'), [showNotification]),
  };

  const autoHideDuration = current?.severity === 'error' ? 8000 : 5000;

  return (
    <NotificationContext.Provider value={{ notify }}>
      {children}
      <Snackbar
        key={current?.key}
        open={open}
        autoHideDuration={autoHideDuration}
        onClose={handleClose}
        TransitionProps={{ onExited: handleExited }}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleClose}
          severity={current?.severity || 'info'}
          variant="filled"
          sx={{ width: '100%', maxWidth: 600 }}
        >
          {current?.message}
        </Alert>
      </Snackbar>
    </NotificationContext.Provider>
  );
};
