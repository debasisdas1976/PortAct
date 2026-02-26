import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import App from './App';
import { store } from './store';
import { NotificationProvider } from './contexts/NotificationContext';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976D2',
      light: '#42A5F5',
      dark: '#1565C0',
    },
    secondary: {
      main: '#10B981',
      light: '#34D399',
      dark: '#059669',
    },
    success: {
      main: '#10B981',
      light: '#34D399',
      dark: '#059669',
    },
    error: {
      main: '#EF4444',
      light: '#F87171',
      dark: '#DC2626',
    },
    warning: {
      main: '#F59E0B',
      light: '#FBBF24',
      dark: '#D97706',
    },
    info: {
      main: '#1E88E5',
      light: '#42A5F5',
      dark: '#1565C0',
    },
    background: {
      default: '#F8FAFC',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0F172A',
      secondary: '#64748B',
    },
    divider: '#E2E8F0',
  },
  typography: {
    fontFamily: '"Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", sans-serif',
    h1: { fontSize: '2.25rem', fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.2 },
    h2: { fontSize: '1.875rem', fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.3 },
    h3: { fontSize: '1.5rem', fontWeight: 600, letterSpacing: '-0.02em', lineHeight: 1.35 },
    h4: { fontSize: '1.25rem', fontWeight: 600, letterSpacing: '-0.015em', lineHeight: 1.4 },
    h5: { fontSize: '1.1rem', fontWeight: 600, lineHeight: 1.45 },
    h6: { fontSize: '1rem', fontWeight: 600, lineHeight: 1.5 },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.875rem', lineHeight: 1.6 },
    subtitle1: { fontSize: '0.9375rem', fontWeight: 500, lineHeight: 1.5 },
    subtitle2: { fontSize: '0.8125rem', fontWeight: 500, lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', lineHeight: 1.5, color: '#64748B' },
  },
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
          padding: '8px 18px',
        },
        contained: {
          boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(25,118,210,0.25)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
          border: '1px solid #F1F5F9',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
          },
          transition: 'box-shadow 0.2s ease',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 600,
            color: '#475569',
            backgroundColor: '#F8FAFC',
          },
        },
      },
    },
  },
});

// Global handlers for uncaught errors and unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  event.preventDefault();
});

window.addEventListener('error', (event) => {
  console.error('Uncaught error:', event.error || event.message);
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <NotificationProvider>
            <App />
          </NotificationProvider>
        </ThemeProvider>
      </BrowserRouter>
    </Provider>
  </React.StrictMode>
);

// Made with Bob
