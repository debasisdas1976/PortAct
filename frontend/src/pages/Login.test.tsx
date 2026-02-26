import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import Login from './Login';

// Mock AuthLayout to avoid useMediaQuery/matchMedia issues in jsdom
jest.mock('../components/AuthLayout', () => {
  return ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-layout">{children}</div>
  );
});

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('Login', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders login form with username and password fields', () => {
    renderWithProviders(<Login />);
    expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders sign in button', () => {
    renderWithProviders(<Login />);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders link to register page', () => {
    renderWithProviders(<Login />);
    expect(screen.getByText(/sign up/i)).toBeInTheDocument();
  });

  it('renders link to forgot password', () => {
    renderWithProviders(<Login />);
    expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
  });

  it('renders welcome back heading', () => {
    renderWithProviders(<Login />);
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
  });

  it('displays error message from Redux state', () => {
    renderWithProviders(<Login />, {
      preloadedState: {
        auth: {
          user: null,
          token: null,
          isAuthenticated: false,
          loading: false,
          error: 'Invalid credentials',
        },
      },
    });
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
  });

  it('shows session expired message from query params', () => {
    window.history.pushState({}, '', '/login?session_expired=true');
    renderWithProviders(<Login />);
    expect(screen.getByText(/session has expired/i)).toBeInTheDocument();
  });
});
