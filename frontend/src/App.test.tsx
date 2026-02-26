import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import App from './App';

// Mock all lazy-loaded pages to avoid dynamic import issues in tests
jest.mock('./pages/Login', () => () => <div data-testid="login-page">Login Page</div>);
jest.mock('./pages/Register', () => () => <div>Register Page</div>);
jest.mock('./pages/ForgotPassword', () => () => <div>Forgot Password</div>);
jest.mock('./pages/ResetPassword', () => () => <div>Reset Password</div>);
jest.mock('./pages/Dashboard', () => () => <div data-testid="dashboard-page">Dashboard</div>);
jest.mock('./components/SessionTimeout', () => () => null);
jest.mock('./components/Layout', () => {
  const { Outlet } = require('react-router-dom');
  return () => <div data-testid="layout"><Outlet /></div>;
});

describe('App', () => {
  it('renders without crashing', () => {
    renderWithProviders(<App />);
    // The app should render something
    expect(document.body).toBeTruthy();
  });

  it('renders login page when not authenticated', async () => {
    window.history.pushState({}, '', '/login');
    renderWithProviders(<App />, {
      preloadedState: {
        auth: { user: null, token: null, isAuthenticated: false, loading: false, error: null },
      },
    });
    const loginPage = await screen.findByTestId('login-page');
    expect(loginPage).toBeInTheDocument();
  });

  it('redirects to login for protected routes when unauthenticated', async () => {
    window.history.pushState({}, '', '/dashboard');
    renderWithProviders(<App />, {
      preloadedState: {
        auth: { user: null, token: null, isAuthenticated: false, loading: false, error: null },
      },
    });
    // Should redirect to login, not show dashboard
    const loginPage = await screen.findByTestId('login-page');
    expect(loginPage).toBeInTheDocument();
  });
});
