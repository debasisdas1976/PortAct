import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material';
import ErrorBoundary from './ErrorBoundary';

const theme = createTheme();

const renderWithTheme = (ui: React.ReactElement) =>
  render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

// Component that throws on render
const ThrowingComponent: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) throw new Error('Test error');
  return <div data-testid="child">Child content</div>;
};

describe('ErrorBoundary', () => {
  // Suppress console.error for expected errors
  const originalError = console.error;
  beforeAll(() => {
    console.error = jest.fn();
  });
  afterAll(() => {
    console.error = originalError;
  });

  it('renders children when no error', () => {
    renderWithTheme(
      <ErrorBoundary>
        <div data-testid="child">Hello</div>
      </ErrorBoundary>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('renders error fallback when child throws', () => {
    renderWithTheme(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it('renders Try Again button on error', () => {
    renderWithTheme(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('retry button resets error state', () => {
    // Use a mutable flag to control whether the component throws
    let shouldThrow = true;
    const ConditionalThrower = () => {
      if (shouldThrow) throw new Error('Test error');
      return <div data-testid="recovered">Recovered!</div>;
    };

    renderWithTheme(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

    // Fix the error and click Try Again
    shouldThrow = false;
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(screen.getByTestId('recovered')).toBeInTheDocument();
  });
});
