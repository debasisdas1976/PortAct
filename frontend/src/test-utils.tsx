/**
 * Shared test utilities for rendering components with all required providers.
 * Mirrors the provider tree from index.tsx / App.tsx.
 */
import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';
import { configureStore, EnhancedStore } from '@reduxjs/toolkit';
import authReducer from './store/slices/authSlice';
import portfolioReducer from './store/slices/portfolioSlice';
import assetsReducer from './store/slices/assetsSlice';
import alertsReducer from './store/slices/alertsSlice';
import { NotificationProvider } from './contexts/NotificationContext';

const testTheme = createTheme();

interface ExtendedRenderOptions extends Omit<RenderOptions, 'queries'> {
  preloadedState?: any;
  store?: EnhancedStore;
}

export function renderWithProviders(
  ui: ReactElement,
  {
    preloadedState = {},
    store = configureStore({
      reducer: {
        auth: authReducer,
        portfolio: portfolioReducer,
        assets: assetsReducer,
        alerts: alertsReducer,
      },
      preloadedState,
    }),
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <BrowserRouter>
          <ThemeProvider theme={testTheme}>
            <NotificationProvider>
              {children}
            </NotificationProvider>
          </ThemeProvider>
        </BrowserRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}
